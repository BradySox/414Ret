"""Neutral border defense: the standing SAM battery (§97).

For each ``NeutralBorderZone`` that defends, this stands live SAM batteries
inside the border under the **neutral country** — sized to how much room the
country has, and as many as its war-facing frontier needs — and records them on
``MissionData.neutral_border_zones`` for the emitter. The ``neutralborder``
plugin swaps that group onto the intruder's *opposing* coalition on escalation
(``GROUP:Respawn`` with a rewritten CountryID), which is the only way a
"neutral" can legally fire in DCS.

The fighter patrol this feature used to fly was **dropped 2026-09-07** (DM
call). What it proved carries over: the deterrent has to be there before you
cross, so the battery is live from t=0 rather than late-activated.

A zone that cannot be built (unknown country, no origin, spawn error) is
skipped with a warning; this feature must never break mission generation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from dcs import Mission
from dcs.country import Country
from dcs.countries import country_dict
from dcs.mapping import Point

from game.theater.neutralborder import (
    NEUTRAL,
    NeutralBorderZone,
    map_edge,
    war_region,
)
from game.utils import meters
from .neutralborderluadata import NeutralBorderLuaZone
from .neutralbordersams import system_for

if TYPE_CHECKING:
    from game import Game

    from .missiondata import MissionData


#: Countries DCS has no entry for, and who stands in when one of them fields a
#: battery (DM call 2026-09-09). The stand-in supplies unit skins and nothing
#: else: the group is still named for the real country, the radio call still
#: says it, and the plugin rewrites ``CountryID`` on escalation anyway. Picked
#: for kit, not politics -- the Central Asian states and Armenia field Russian
#: systems, Azerbaijan Turkish and Israeli ones. Each falls through when its
#: first choice is already a belligerent, which Russia is on the Caucasus map.
COUNTRY_STAND_INS: dict[str, tuple[str, ...]] = {
    "Turkmenistan": ("Russia", "Kazakhstan", "Belarus"),
    "Uzbekistan": ("Russia", "Kazakhstan", "Belarus"),
    "Tajikistan": ("Russia", "Kazakhstan", "Belarus"),
    "Kyrgyzstan": ("Russia", "Kazakhstan", "Belarus"),
    "Armenia": ("Russia", "Belarus", "Kazakhstan"),
    "Azerbaijan": ("Turkey", "Kazakhstan", "Belarus"),
}

#: Last resort for a country not in the table at all.
GENERIC_STAND_INS: tuple[str, ...] = (
    "Kazakhstan",
    "Belarus",
    "United Nations Peacekeepers",
)


class NeutralBorderGenerator:
    def __init__(
        self,
        mission: Mission,
        game: "Game",
        mission_data: "MissionData",
        blue_country_id: int,
        red_country_id: int,
    ) -> None:
        self.mission = mission
        self.game = game
        self.mission_data = mission_data
        self.blue_country_id = blue_country_id
        self.red_country_id = red_country_id

    def generate(self) -> None:
        if not getattr(self.game.settings, "neutral_border_defense", False):
            return
        zones = getattr(self.game.theater, "neutral_border_zones", [])
        # Both are the same for every zone and both are expensive: the clip is a
        # union of every polygon on the map, and the war points are read off the
        # whole control-point list.
        clip = map_edge([zone.border for zone in zones])
        approaches = war_region(
            [
                (cp.position.x, cp.position.y)
                for cp in getattr(self.game.theater, "controlpoints", [])
            ]
        )
        for zone in zones:
            try:
                built = self._build_zone(zone, approaches, clip)
            except Exception:
                logging.warning(
                    "Neutral border: could not build the %s zone; skipped.",
                    zone.country,
                    exc_info=True,
                )
                continue
            if built is not None:
                self.mission_data.neutral_border_zones.append(built)

    def _build_zone(
        self,
        zone: NeutralBorderZone,
        approaches: Any,
        clip: Any,
    ) -> NeutralBorderLuaZone | None:
        theater = self.game.theater
        posture = zone.posture_in(theater)
        # Per side: a country hosting one side's fields has let that side in
        # and not the other.
        permits_blue = zone.permits(theater, True, posture)
        permits_red = zone.permits(theater, False, posture)
        # None = no safe altitude, which is what a country out of the war and
        # defending itself actually offers.
        floor_blue = zone.floor_for(theater, True)
        floor_red = zone.floor_for(theater, False)
        enforced = posture == NEUTRAL and not (permits_blue and permits_red)

        if not enforced:
            # An aligned country is not a third party: it spawns nothing here, so
            # it needs no pydcs country and no aircraft. A red-aligned one is
            # defended by §1's QRA instead (see aligned_defense_polygons), which
            # keeps one interception system over that ground rather than two.
            return NeutralBorderLuaZone(
                country=zone.country,
                posture=posture,
                overflight_blue=permits_blue,
                overflight_red=permits_red,
                origin_label=zone.origin_label(posture, enforced=False),
                floor_blue_ft=floor_blue,
                floor_red_ft=floor_red,
                border=list(zone.border),
                label=zone.label_point(),
            )

        # It defends against at least one side, so it needs somewhere to stand a
        # battery. Missing means it is DRAWN but toothless -- never dropped;
        # every bordering nation is meant to appear (DM call). Since the patrol
        # was dropped 2026-09-07 this asks only for a position: a SAM needs no
        # airframe and no runway, so several zones that were toothless as
        # fighter bases now defend.
        if not zone.can_defend(self.game.current_day):
            logging.info(
                "Neutral border: %s would defend its airspace but has no origin "
                "to stand a battery at, so its border is drawn and not enforced.",
                zone.country,
            )
            return NeutralBorderLuaZone(
                country=zone.country,
                posture=posture,
                overflight_blue=True,
                overflight_red=True,
                origin_label=zone.origin_label(posture, enforced=False),
                floor_blue_ft=floor_blue,
                floor_red_ft=floor_red,
                border=list(zone.border),
                label=zone.label_point(),
            )

        airport = None
        if zone.airfield is not None:
            airport = self.mission.terrain.airports.get(zone.airfield)
            if airport is None:
                logging.warning(
                    "Neutral border: airfield '%s' not on this terrain — %s skipped.",
                    zone.airfield,
                    zone.country,
                )
                return None
        country = self._spawn_country(zone.country)
        if country is None:
            logging.warning(
                "Neutral border: no country and no stand-in for '%s' — zone skipped.",
                zone.country,
            )
            return None

        # A STANDING battery, live and NEUTRAL from mission start -- not a
        # template that appears once you have already violated the border.
        #
        # The fighter patrol that used to do this job was dropped 2026-09-07
        # (DM call): scope is the SAM now. Everything the patrol taught still
        # applies to it -- it must be visible before you cross, so it stands up
        # at t=0, and it sits as a TRUE NEUTRAL, which cannot fire (the
        # engine verdict). The plugin swaps its coalition on escalation, which
        # is the only way a neutral ever shoots.
        if airport is not None:
            origin = (airport.position.x, airport.position.y)
        else:
            assert zone.spawn is not None  # the caller checked one origin exists
            origin = (zone.spawn[0], zone.spawn[1])
        # Size the system to the country, then stand it as deep as its own reach
        # allows. DM call 2026-09-07: a larger country gets a larger SAM, further
        # back.
        system = system_for(
            zone.country, meters(zone.interior_room()), self.game.current_day
        )
        # One battery per stretch of war-facing frontier the system can cover.
        # A single site left Pakistan's 2,291 NM border 96 % open (measured
        # 2026-09-09), which is why the count is derived rather than fixed.
        sites = zone.sam_sites(origin, system.reach.meters, approaches, clip)
        sam_names = []
        for index, site in enumerate(sites, start=1):
            sam_name = f"NeutralBorder|{zone.country}|{system.name}|{index}"
            sam_group = self.mission.vehicle_group_platoon(
                country,
                sam_name,
                list(system.units),
                Point(site[0], site[1], self.mission.terrain),
            )
            # Live, not late-activated: the border must have something in it
            # before you cross. Neutral units do not trigger the airbase
            # auto-capture that a standing belligerent one would, and the sites
            # are off the airfield anyway (see NeutralBorderZone.sam_sites).
            sam_group.late_activation = False
            sam_names.append(sam_name)

        return NeutralBorderLuaZone(
            country=zone.country,
            posture=NEUTRAL,
            overflight_blue=permits_blue,
            overflight_red=permits_red,
            airfield=zone.airfield,
            spawn=zone.spawn,
            origin_label=zone.origin_label(NEUTRAL),
            floor_blue_ft=floor_blue,
            floor_red_ft=floor_red,
            sam_groups=sam_names,
            red_country_id=self.red_country_id,
            blue_country_id=self.blue_country_id,
            border=list(zone.border),
            label=zone.label_point(),
        )

    def _spawn_country(self, name: str) -> Country | None:
        """Who the battery spawns under: the country itself, or a stand-in.

        DCS models no Turkmenistan, Uzbekistan, Tajikistan, Armenia or
        Azerbaijan, and those five zones used to be dropped from the mission
        outright -- border undrawn, airspace unenforced. They now borrow a
        neighbour's units (DM call 2026-09-09).
        """
        country = self._country(name)
        if country is not None:
            return country
        for stand_in in COUNTRY_STAND_INS.get(name, ()) + GENERIC_STAND_INS:
            if self._belligerent(stand_in):
                # A country cannot be on two coalitions in one mission.
                continue
            country = self._country(stand_in)
            if country is not None:
                logging.info(
                    "Neutral border: DCS has no %s, so its battery spawns as %s.",
                    name,
                    stand_in,
                )
                return country
        return None

    def _belligerent(self, name: str) -> bool:
        """Already fighting? Then it cannot also stand in as a neutral."""
        for side in ("blue", "red"):
            coalition = self.mission.coalition.get(side)
            if coalition is not None and name in coalition.countries:
                return True
        return False

    def _country(self, name: str) -> Country | None:
        """The named country from the neutrals coalition, registered if needed."""
        neutrals = self.mission.coalition["neutrals"]
        existing = neutrals.countries.get(name)
        if existing is not None:
            return existing
        for country_class in country_dict.values():
            if country_class.name == name:
                country = country_class()
                neutrals.add_country(country)
                return country
        return None
