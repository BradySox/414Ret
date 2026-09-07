"""Neutral border defense: the standing SAM battery (§96).

For each ``NeutralBorderZone`` that defends, this stands one live SAM battery
inside the border under the **neutral country** — sized to how much room the
country has, placed as deep as its own reach allows — and records the result on
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
from typing import TYPE_CHECKING

from dcs import Mission
from dcs.country import Country
from dcs.countries import country_dict
from dcs.mapping import Point

from game.theater.neutralborder import NEUTRAL, NeutralBorderZone
from game.utils import meters
from .neutralborderluadata import NeutralBorderLuaZone
from .neutralbordersams import system_for

if TYPE_CHECKING:
    from game import Game

    from .missiondata import MissionData


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
        for zone in zones:
            try:
                built = self._build_zone(zone)
            except Exception:
                logging.warning(
                    "Neutral border: could not build the %s zone; skipped.",
                    zone.country,
                    exc_info=True,
                )
                continue
            if built is not None:
                self.mission_data.neutral_border_zones.append(built)

    def _build_zone(self, zone: NeutralBorderZone) -> NeutralBorderLuaZone | None:
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
        country = self._country(zone.country)
        if country is None:
            logging.warning(
                "Neutral border: unknown country '%s' — zone skipped.", zone.country
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
        site = zone.sam_site(origin, system.reach.meters)
        sam_name = f"NeutralBorder|{zone.country}|{system.name}"
        sam_group = self.mission.vehicle_group_platoon(
            country,
            sam_name,
            list(system.units),
            Point(site[0], site[1], self.mission.terrain),
        )
        # Live, not late-activated: the border must have something in it before
        # you cross. Neutral units do not trigger the airbase auto-capture that
        # a standing belligerent one would, and the site is off the airfield
        # anyway (see NeutralBorderZone.sam_site).
        sam_group.late_activation = False

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
            sam_group=sam_name,
            red_country_id=self.red_country_id,
            blue_country_id=self.blue_country_id,
            border=list(zone.border),
            label=zone.label_point(),
        )

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
