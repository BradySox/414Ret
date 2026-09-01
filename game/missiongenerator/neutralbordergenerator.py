"""Neutral border defense: the standing patrol and its SAM (§96).

For each ``NeutralBorderZone`` that defends, this builds a live 4-ship fighter
patrol orbiting inside the border under the neutral country, plus a cold
late-activation SA-6 template at the origin — and records the result on
``MissionData.neutral_border_zones`` for the emitter. The ``neutralborder``
plugin clones a template at runtime under the intruder's *opposing* coalition
(``SPAWN:InitCountry``/``InitCoalition``), which is the only way a "neutral" can
legally fire in DCS.

Clones are free, untracked event content by design (the §61 precedent):
``claim_inv`` has no meaning here because no squadron is involved — the neutral
country owns no campaign forces at all. A zone that cannot be built (unknown
aircraft, unknown airfield, spawn error) is skipped with a warning; this feature
must never break mission generation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from dcs import Mission
from dcs.country import Country
from dcs.countries import country_dict
from dcs.mapping import Point
from dcs.task import OrbitAction
from dcs.planes import plane_map
from dcs.task import CAP
from dcs.vehicles import AirDefence

from game.theater.nationalpostures import aircraft_for
from game.theater.neutralborder import NEUTRAL, NeutralBorderZone
from game.utils import feet, nautical_miles
from .neutralborderluadata import NeutralBorderLuaZone

#: Cruise speed for a point-spawned CAP, in km/h (pydcs speed units).
CAP_SPEED_KPH = 750.0

#: Racetrack leg length. Shortened automatically for a country too narrow to
#: hold it, and dropped for a circle when even the shortest leg leaves.
PATROL_LEG_NM = nautical_miles(12)

#: How far inside its own frontier the whole orbit must sit, tried largest
#: first. A DCS racetrack overshoots each end before turning back -- measured
#: under 10 NM at 405 kt -- so 12 covers that with margin. **The last value is a
#: floor, not a fallback**: a country that cannot clear it flies no patrol at
#: all (DM call 2026-08-30). At 8 it drops exactly the three shipped zones
#: smaller than a fighter's turn -- Bahrain and the two Persian Gulf slivers --
#: and keeps the other 49.
PATROL_CLEARANCES_M = tuple(nautical_miles(nm).meters for nm in (12.0, 10.0, 8.0))

#: Aircraft per patrol. DM call 2026-08-29: a neutral's deterrent is numbers,
#: not better missiles -- it keeps the era-correct WVR fit and puts up four, so
#: killing the whole flight and carrying on costs more than one BVR pass.
PATROL_SIZE = 4

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

        # It defends against at least one side, so it needs something to defend
        # with. Missing means it is DRAWN but toothless -- never dropped. Every
        # bordering nation is meant to appear (DM call), and a country that
        # cannot field an interceptor is exactly the case that rule is for: DCS
        # models no Turkmenistan, so its border can only ever be a line.
        if not zone.can_field_an_interceptor(self.game.current_day):
            logging.info(
                "Neutral border: %s would defend its airspace but cannot field an "
                "interceptor (no airframe for this era, or no airfield/spawn "
                "point), so its border is drawn and not enforced.",
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
        # The campaign may name no airframe -- a terrain-shipped border never
        # does -- in which case the era picks one from the posture table.
        aircraft_id = zone.aircraft or aircraft_for(zone.country, self.game.current_day)
        assert aircraft_id is not None  # the caller checked one is available
        aircraft = plane_map.get(aircraft_id)
        if aircraft is None:
            logging.warning(
                "Neutral border: unknown aircraft '%s' — %s skipped.",
                zone.aircraft,
                zone.country,
            )
            return None
        country = self._country(zone.country)
        if country is None:
            logging.warning(
                "Neutral border: unknown country '%s' — zone skipped.", zone.country
            )
            return None

        fighter_name = f"NeutralBorder|{zone.country}|{aircraft_id}"
        spawn_alt_m = feet(zone.spawn_alt_ft).meters
        # A STANDING patrol, airborne from mission start, not a scramble.
        #
        # Flown 2026-08-28/29: a scramble cannot work. Cold on the ramp it took
        # 270 s to get up; from a runway it still launched behind the intruder;
        # and once airborne it could not hold a standoff, because the geometry
        # belongs to whoever is closing -- measured 22.8 NM down to 6.5 NM while
        # still shadowing. A patrol already flying its own border never plays
        # that game: it is visible before you cross, which is the deterrent the
        # feature was always trying to be.
        #
        # It orbits as a TRUE NEUTRAL and so cannot fire (the engine verdict).
        # The plugin swaps its coalition on escalation, which is the only way a
        # neutral ever shoots.
        if airport is not None:
            origin = (airport.position.x, airport.position.y)
        else:
            assert zone.spawn is not None  # the caller checked one origin exists
            origin = (zone.spawn[0], zone.spawn[1])
        # The orbit is fitted first, because the centre can move: a station
        # closer to the frontier than the racetrack overshoots cannot orbit
        # without crossing it, and several are (India's is 0.6 NM from its own
        # border). Flown 2026-08-30 before this: the patrol overflew the
        # neighbour by under 10 NM past each end of its leg.
        centre, leg_end = zone.patrol_orbit(
            origin, PATROL_LEG_NM.meters, PATROL_CLEARANCES_M
        )
        anchor = Point(centre[0], centre[1], self.mission.terrain)
        # A country smaller than the orbit it would have to fly puts none up.
        # DM call 2026-08-30: a patrol that permanently trespasses on its
        # neighbours is worse theatre than no patrol. Three shipped zones are
        # this -- Bahrain, and Oman and Iran's Persian Gulf slivers. They keep
        # their border, their radio calls and their SAM.
        if leg_end is None and not zone.sam:
            logging.info(
                "Neutral border: %s is too small to orbit inside and has no SAM, "
                "so its border is drawn and not enforced.",
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

        patrol_name: str | None = None
        if leg_end is not None:
            patrol_name = fighter_name
            # km/h: pydcs writes speed/3.6 onto the spawned unit records and the
            # first waypoint, so passing m/s spawns the flight stalled (the
            # civilian-traffic lesson).
            group = self.mission.flight_group_inflight(
                country=country,
                name=fighter_name,
                aircraft_type=aircraft,
                position=anchor,
                altitude=int(spawn_alt_m),
                speed=CAP_SPEED_KPH,
                group_size=PATROL_SIZE,
            )
            # A Race-Track orbit flies between its waypoint and the NEXT one, so
            # it needs a second point. Flown 2026-08-29 with one waypoint: all
            # three patrol leaders flew into the ground inside 43 s.
            group.add_waypoint(
                Point(leg_end[0], leg_end[1], self.mission.terrain),
                int(spawn_alt_m),
                speed=int(CAP_SPEED_KPH),
            )
            # km/h, NOT m/s. Every pydcs speed argument is km/h and it divides
            # by 3.6 on write, so a "helpful" conversion here is applied twice.
            # Flown 2026-08-29: /3.6 put 112 kt in the task and every patrol
            # stalled.
            group.points[0].tasks.append(
                OrbitAction(
                    int(spawn_alt_m),
                    int(CAP_SPEED_KPH),
                    OrbitAction.OrbitPattern.RaceTrack,
                )
            )
            group.late_activation = False
            # The clones inherit the template's pylons, so arm it once here. An
            # airframe with no CAP default flies guns-only rather than failing.
            if not group.load_task_default_loadout(CAP):
                logging.info(
                    "Neutral border: %s has no CAP default loadout; guns only.",
                    zone.aircraft,
                )
        else:
            logging.info(
                "Neutral border: %s cannot fly an orbit clear of its own border, "
                "so it defends with its SAM alone.",
                zone.country,
            )

        sam_name: str | None = None
        if zone.sam:
            sam_name = f"NeutralBorder|{zone.country}|SAM"
            sam_position = Point(
                anchor.x + 700,
                anchor.y + 700,
                self.mission.terrain,
            )
            sam_group = self.mission.vehicle_group_platoon(
                country,
                sam_name,
                [
                    AirDefence.Kub_1S91_str,
                    AirDefence.Kub_2P25_ln,
                    AirDefence.Kub_2P25_ln,
                ],
                sam_position,
            )
            sam_group.late_activation = True

        return NeutralBorderLuaZone(
            country=zone.country,
            posture=NEUTRAL,
            overflight_blue=permits_blue,
            overflight_red=permits_red,
            airfield=zone.airfield,
            spawn=zone.spawn,
            spawn_alt_m=spawn_alt_m,
            origin_label=zone.origin_label(NEUTRAL),
            floor_blue_ft=floor_blue,
            floor_red_ft=floor_red,
            fighter_template=patrol_name,
            sam_template=sam_name,
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
