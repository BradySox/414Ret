from __future__ import annotations

import itertools
import math
import operator
from collections.abc import Iterable, Iterator
from random import randint
from typing import TYPE_CHECKING, TypeVar

from game.ato.closestairfields import ClosestAirfields, ObjectiveDistanceCache
from game.ato.flighttype import FlightType
from game.theater import (
    Airfield,
    ControlPoint,
    Fob,
    FrontLine,
    MissionTarget,
    OffMapSpawn,
    ParkingType,
    NavalControlPoint,
    Player,
)
from game.retlab.region_priorities import planning_factor
from game.ground_forces.ai_ground_planner import reserve_armor_for
from game.squadrons.downedpilot import DownedPilot
from game.theater.theatergroundobject import (
    BuildingGroundObject,
    IadsGroundObject,
    MotorpoolGroundObject,
    NavalGroundObject,
    IadsBuildingGroundObject,
)
from game.utils import meters, nautical_miles

if TYPE_CHECKING:
    from game import Game
    from game.transfers import CargoShip, Convoy

MissionTargetType = TypeVar("MissionTargetType", bound=MissionTarget)

#: How far behind the nearest friendly control point an air-assault objective may
#: sit. Bounds the operation itself, so it does not move with the staging field or
#: the airframe's legs. See ObjectiveFinder._within_air_assault_reach.
AIR_ASSAULT_MAX_REACH = nautical_miles(100)


class ObjectiveFinder:
    """Identifies potential objectives for the mission planner."""

    def __init__(self, game: Game, is_player: Player) -> None:
        self.game = game
        self.is_player = is_player

    def enemy_air_defenses(self) -> Iterator[IadsGroundObject]:
        """Iterates over all enemy SAM sites."""
        for cp in self.enemy_control_points():
            for ground_object in cp.ground_objects:
                if ground_object.is_dead():
                    continue

                if isinstance(ground_object, IadsGroundObject):
                    yield ground_object

    def enemy_ships(self) -> Iterator[NavalGroundObject]:
        for cp in self.enemy_control_points():
            for ground_object in cp.ground_objects:
                if not isinstance(ground_object, NavalGroundObject):
                    continue

                if ground_object.is_dead():
                    continue

                yield ground_object

    def threatening_ships(self) -> Iterator[NavalGroundObject]:
        """Iterates over enemy ships near friendly control points.

        Groups are sorted by their closest proximity to any friendly control
        point (airfield or fleet).
        """
        return self._targets_by_range(self.enemy_ships(), weighted=True)

    def _targets_by_range(
        self, targets: Iterable[MissionTargetType], *, weighted: bool = False
    ) -> Iterator[MissionTargetType]:
        target_ranges: list[tuple[MissionTargetType, float]] = []
        for target in targets:
            factor = 1.0
            if weighted:
                # §93 region priorities: weight offensive target choice by the
                # owning CP's priority; None (IGNORED) drops the target from
                # auto-planning only. Identity when off, red, or CP-less.
                maybe_factor = planning_factor(
                    target, self.game.settings, self.is_player.is_blue
                )
                if maybe_factor is None:
                    continue
                factor = maybe_factor
            ranges: list[float] = []
            for cp in self.friendly_control_points():
                ranges.append(target.distance_to(cp))
            target_ranges.append((target, min(ranges) * factor))

        target_ranges = sorted(target_ranges, key=operator.itemgetter(1))
        for target, _range in target_ranges:
            yield target

    def strike_targets(self) -> Iterator[BuildingGroundObject]:
        """Iterates over enemy strike targets.

        Targets are sorted by their closest proximity to any friendly control
        point (airfield or fleet).
        """
        targets: list[tuple[BuildingGroundObject, float]] = []
        # Building objectives are made of several individual TGOs (one per
        # building).
        found_targets: set[str] = set()
        for enemy_cp in self.enemy_control_points():
            for ground_object in enemy_cp.ground_objects:
                # TODO: Reuse ground_object.mission_types.
                # The mission types for ground objects are currently not
                # accurate because we include things like strike and BAI for all
                # targets since they have different planning behavior (waypoint
                # generation is better for players with strike when the targets
                # are stationary, AI behavior against weaker air defenses is
                # better with BAI), so that's not a useful filter. Once we have
                # better control over planning profiles and target dependent
                # loadouts we can clean this up.
                if not isinstance(ground_object, BuildingGroundObject):
                    # Other group types (like ships, SAMs, battle positions, etc) have better
                    # suited mission types like anti-ship, DEAD, and BAI.
                    continue

                if isinstance(enemy_cp, Fob) and ground_object.is_control_point:
                    # This is the FOB structure itself. Can't be repaired or
                    # targeted by the player, so shouldn't be targetable by the
                    # AI.
                    continue

                if isinstance(
                    ground_object, IadsBuildingGroundObject
                ) and not self.game.settings.plugin_option("skynetiads"):
                    # Prevent strike targets on IADS Buildings when skynet features
                    # are disabled as they do not serve any purpose
                    continue

                if ground_object.is_dead():
                    continue
                if ground_object.name in found_targets:
                    continue
                # §93 region priorities (same weighting as _targets_by_range;
                # this iterator carries its own sort for the multi-TGO dedup).
                factor = planning_factor(
                    ground_object, self.game.settings, self.is_player.is_blue
                )
                if factor is None:
                    continue
                ranges: list[float] = []
                for friendly_cp in self.friendly_control_points():
                    ranges.append(ground_object.distance_to(friendly_cp))
                targets.append((ground_object, min(ranges) * factor))
                found_targets.add(ground_object.name)
        targets = sorted(targets, key=operator.itemgetter(1))
        for target, _range in targets:
            yield target

    def motorpool_targets(self) -> Iterator[MotorpoolGroundObject]:
        """Iterates over enemy motorpool depots worth striking this turn.

        A motorpool is a target only when it will actually render reserve armor,
        so membership is gated on the live reserve pool (``reserve_armor_for``)
        plus the motorpool being enabled with a positive spawn cap. Unlike
        :meth:`strike_targets`, ``is_dead`` is intentionally *not* used: the
        motorpool's groups are repopulated each mission *after* planning runs, so
        ``is_dead`` (which reads ``alive_unit_count``) reflects a stale render
        while the reserve pool is the current source of truth.

        Targets are sorted by proximity to friendly control points, matching the
        behavior of :meth:`strike_targets`.
        """
        settings = self.game.settings
        if not settings.motorpool_enabled or settings.motorpool_spawn_cap <= 0:
            return
        candidates: list[MotorpoolGroundObject] = []
        for enemy_cp in self.enemy_control_points():
            if not reserve_armor_for(enemy_cp):
                continue
            for ground_object in enemy_cp.ground_objects:
                if isinstance(ground_object, MotorpoolGroundObject):
                    candidates.append(ground_object)
        yield from self._targets_by_range(candidates, weighted=True)

    def downed_pilots(self) -> Iterator[DownedPilot]:
        """Iterates over friendly downed pilots awaiting CSAR.

        Ordered by proximity to friendly control points so the closest-to-base
        pilots (the ones a rescue can most plausibly reach) are planned first.
        """
        settings = self.game.settings
        csar_on = (
            settings.csar_enabled
            if self.is_player.is_blue
            else settings.csar_enabled_red
        )
        if not csar_on:
            return
        coalition = self.game.coalition_for(self.is_player)
        yield from self._targets_by_range(list(coalition.downed_pilots))

    def front_lines(self) -> Iterator[FrontLine]:
        """Iterates over all active front lines in the theater."""
        yield from self.game.theater.conflicts()

    def vulnerable_control_points(self) -> Iterator[ControlPoint]:
        """Iterates over friendly CPs that are vulnerable to enemy CPs.

        Vulnerability is defined as any enemy CP within threat range of the
        CP.
        """
        for cp in self.friendly_control_points():
            if isinstance(cp, OffMapSpawn):
                # Off-map spawn locations don't need protection.
                continue
            if isinstance(cp, NavalControlPoint):
                yield cp  # always consider CVN/LHA as vulnerable
                continue
            airfields_in_proximity = self.closest_airfields_to(cp)
            airbase_threat_range = self.game.settings.airbase_threat_range
            if (
                self.is_player.is_red
                and randint(1, 100)
                < self.game.settings.opfor_autoplanner_aggressiveness
            ):
                # Chance that the airfield threat range will be evaluated as zero,
                # causing the OPFOR autoplanner to plan offensively
                airbase_threat_range = 0
            airfields_in_threat_range = (
                airfields_in_proximity.operational_airfields_within(
                    nautical_miles(airbase_threat_range)
                )
            )
            for airfield in airfields_in_threat_range:
                if not airfield.is_friendly(self.is_player):
                    yield cp

    def oca_targets(self, min_aircraft: int) -> Iterator[ControlPoint]:
        parking_type = ParkingType()
        parking_type.include_rotary_wing = True
        parking_type.include_fixed_wing = True
        parking_type.include_fixed_wing_stol = True

        airfields = []
        for control_point in self.enemy_control_points():
            if not isinstance(control_point, Airfield) and not isinstance(
                control_point, Fob
            ):
                continue
            if (
                control_point.allocated_aircraft(parking_type).total_present
                >= min_aircraft
            ):
                airfields.append(control_point)
        return self._targets_by_range(airfields, weighted=True)

    def convoys(self) -> Iterator[Convoy]:
        if self.game.settings.perf_disable_convoys:
            return
        for front_line in self.front_lines():
            yield from self.game.coalition_for(
                self.is_player
            ).transfers.convoys.travelling_to(
                front_line.control_point_hostile_to(self.is_player)
            )

    def cargo_ships(self) -> Iterator[CargoShip]:
        for front_line in self.front_lines():
            yield from self.game.coalition_for(
                self.is_player
            ).transfers.cargo_ships.travelling_to(
                front_line.control_point_hostile_to(self.is_player)
            )

    def friendly_control_points(self) -> Iterator[ControlPoint]:
        """Iterates over all friendly control points."""
        return (
            c for c in self.game.theater.controlpoints if c.is_friendly(self.is_player)
        )

    def farthest_friendly_control_point(self) -> ControlPoint:
        """Finds the friendly control point that is farthest from any threats."""
        threat_zones = self.game.threat_zone_for(self.is_player.opponent)

        farthest = None
        max_distance = meters(0)
        for cp in self.friendly_control_points():
            if isinstance(cp, OffMapSpawn):
                continue
            distance = threat_zones.distance_to_threat(cp.position)
            if distance > max_distance:
                farthest = cp
                max_distance = distance

        if farthest is None:
            raise RuntimeError("Found no friendly control points. You probably lost.")
        return farthest

    def _land_support_candidates(self) -> Iterator[ControlPoint]:
        """Friendly control points a support orbit may be anchored ashore on.

        ``is_fleet``, not ``is_carrier``: ``Lha`` never overrides ``is_carrier``,
        so the old filter let an LHA through as a land anchor. Test 36 put the
        "land" AWACS on LHA-1 Tarawa, 3.29 NM from CVN-71, and the carrier's one
        E-2C squadron flew two overlapping racetracks 14.9 NM apart.
        """
        for cp in self.friendly_control_points():
            if isinstance(cp, OffMapSpawn) or cp.is_fleet:
                continue
            yield cp

    def _support_anchor_rank(
        self, cp: ControlPoint, *, forward: bool
    ) -> tuple[int, float]:
        """Sort key for a support anchor; lowest wins.

        ``distance_to_threat`` is unsigned -- distance to the nearest zone edge,
        which inside the zone is how DEEP the field sits, not how far clear. The
        old pick treated the two alike, so with every field threatened "farthest
        from threats" chose the one deepest inside the enemy zone. An unthreatened
        field always beats a threatened one; among threatened fields none is safe,
        so the shallowest wins whichever way the caller leans.
        """
        threat_zones = self.game.threat_zone_for(self.is_player.opponent)
        distance = threat_zones.distance_to_threat(cp.position).meters
        if threat_zones.threatened(cp.position):
            return 1, distance
        return 0, distance if forward else -distance

    def _support_hosting_anchor(
        self, task: FlightType, *, forward: bool
    ) -> ControlPoint | None:
        """The land CP hosting a usable `task` squadron, rear or forward.

        Shared by the AEW&C and tanker anchors. A support orbit is laid out relative
        to whatever this returns, and the squadron that flies it is chosen
        separately, so an anchor picked without asking where those aircraft actually
        live sends them across the theater to orbit beside a field they did not come
        from. A threatened host is used only when EVERY land field is threatened --
        test 36 had all four blue fields inside red's zone and skipped Incirlik, whose
        E-3A sat untasked. While any field is clear the old behaviour stands: the
        threatened host is skipped and the caller falls back to the clear field. That
        fallback is not guaranteed a clear orbit either -- a field 13 NM from the zone
        lays its orbit inside it -- so the rule only changes the case the old code got
        worst. None when nothing qualifies.
        """
        threat_zones = self.game.threat_zone_for(self.is_player.opponent)
        candidates = list(self._land_support_candidates())
        every_field_threatened = all(
            threat_zones.threatened(cp.position) for cp in candidates
        )
        hosts = [
            cp
            for cp in candidates
            if (every_field_threatened or not threat_zones.threatened(cp.position))
            and any(
                squadron.capable_of(task) and squadron.untasked_aircraft > 0
                for squadron in cp.squadrons
            )
        ]
        if not hosts:
            return None
        return min(hosts, key=lambda cp: self._support_anchor_rank(cp, forward=forward))

    def _land_support_fallback(self, *, forward: bool) -> ControlPoint | None:
        """The stock rear or forward pick, restricted to land. None if there is none.

        What an anchor falls back to when no land field hosts the squadron. The old
        fallbacks were the generic nearest/farthest-CP picks, which filter nothing
        but off-map spawns and so could hand back a ship. A wing with no land field
        returns None and gets its per-carrier stations only, instead of a phantom
        land station planted on one of its own boats. An off-map spawn is not a
        station either, so a tanker based only off-map still gets none -- as before.
        """
        candidates = list(self._land_support_candidates())
        if not candidates:
            return None
        return min(
            candidates, key=lambda cp: self._support_anchor_rank(cp, forward=forward)
        )

    def _aewc_hosting_anchor(self, *, forward: bool) -> ControlPoint | None:
        return self._support_hosting_anchor(FlightType.AEWC, forward=forward)

    def tanker_land_anchor(self) -> ControlPoint | None:
        """The land tanker station: the most forward field that hosts a tanker.

        The stock pick is the CP nearest the enemy and asks nothing about basing,
        so on a flown Caucasus turn the station landed on a sector HQ with the
        KC-135 **103 NM** away and a carrier A-6E dragged **226 NM** to reach it
        (test.retribution turn 2, 2026-08-19). Forward like the stock pick, but
        among the fields that can actually put a tanker there; the most forward
        land field when none can, and None when there is no land field at all.
        """
        return self._support_hosting_anchor(
            FlightType.REFUELING, forward=True
        ) or self._land_support_fallback(forward=True)

    def aewc_land_anchor(self) -> ControlPoint | None:
        """The rear-safe land AEW&C anchor, biased to a field that hosts an AWACS.

        The orbit is laid out relative to this CP, so a pick made purely on
        distance-from-threat can strand the wing's only AWACS across the theater:
        the flown Sinai plan took a rear field 1.1 NM safer than the one the single
        E-3A actually flew from, and sent it 245 NM to orbit beside a third field
        (brady.retribution, 2026-08-17). Falls back to the rearmost land field when
        none hosts an AEW&C squadron, and to None when there is no land field, so an
        all-carrier wing gets its per-carrier orbits and no phantom land one.
        """
        return self._aewc_hosting_anchor(forward=False) or self._land_support_fallback(
            forward=False
        )

    def forward_aewc_land_anchor(self) -> ControlPoint | None:
        """The front-less land AEW&C anchor: the most forward field hosting an AWACS.

        With no front line the orbit holds at its target, so the rear pick parks the
        AWACS out of the war and the stock answer is instead the CP nearest the
        enemy. That pick asked nothing about basing: on a front-less Syria turn it
        took Ben Gurion, which hosts no AWACS, while the wing's only land E-3A sat
        at Akrotiri **164 NM away** and flew that each way to reach the orbit
        (test 9, 2026-08-18). Same rule as the rear anchor, forward instead of back.
        """
        return self._aewc_hosting_anchor(forward=True) or self._land_support_fallback(
            forward=True
        )

    def closest_friendly_control_point(self) -> ControlPoint:
        """Finds the friendly control point that is closest to any threats."""
        threat_zones = self.game.threat_zone_for(self.is_player.opponent)

        closest = None
        min_distance = meters(math.inf)
        for cp in self.friendly_control_points():
            if isinstance(cp, OffMapSpawn):
                continue
            distance = threat_zones.distance_to_threat(cp.position)
            if distance < min_distance:
                closest = cp
                min_distance = distance

        if closest is None:
            raise RuntimeError("Found no friendly control points. You probably lost.")
        return closest

    def friendly_naval_control_points(self) -> Iterator[ControlPoint]:
        return (cp for cp in self.friendly_control_points() if cp.is_fleet)

    def enemy_control_points(self) -> Iterator[ControlPoint]:
        """Iterates over all enemy control points."""
        return (
            c
            for c in self.game.theater.controlpoints
            if not c.is_friendly(self.is_player) and c.captured != Player.NEUTRAL
        )

    def prioritized_points(self) -> list[ControlPoint]:
        prioritized = []
        capturable_later = []
        isolated = []
        for cp in self.game.theater.control_points_for(self.is_player.opponent):
            if cp.is_isolated:
                isolated.append(cp)
                continue
            if cp.has_active_frontline:
                prioritized.append(cp)
            else:
                capturable_later.append(cp)
        prioritized.extend(self._targets_by_range(capturable_later))
        prioritized.extend(self._targets_by_range(isolated))
        return prioritized

    def air_assault_targets(self) -> list[ControlPoint]:
        """Returns control points suitable for air assault missions, including neutral bases."""
        prioritized = []
        capturable_later = []
        isolated = []

        combined_control_points = itertools.chain(
            self.game.theater.control_points_for(self.is_player.opponent),
            self.game.theater.control_points_for(Player.NEUTRAL),
        )

        for cp in combined_control_points:
            if not self._within_air_assault_reach(cp):
                continue
            if cp.is_isolated:
                isolated.append(cp)
                continue
            if cp.has_active_frontline:
                prioritized.append(cp)
            else:
                capturable_later.append(cp)
        prioritized.extend(self._targets_by_range(capturable_later))
        prioritized.extend(self._targets_by_range(isolated))
        return prioritized

    def _within_air_assault_reach(self, cp: ControlPoint) -> bool:
        """Is this objective close enough to our own lines to air-assault?

        Measured to the nearest friendly control point, not to the staging field,
        so the answer does not change with whichever base happens to launch it.

        Without this, a long-legged transport volunteers for objectives on the far
        side of the theatre: an Afghanistan turn-2 ATO fragged C-130s from Bagram
        against Kandahar (269 NM) and FOB Zeebrugge (261 NM), both ~180 NM behind
        the nearest friendly base. Helicopters were never able to reach that far,
        so the flat list only became a problem once fixed-wing became eligible.
        """
        friendly = list(self.friendly_control_points())
        if not friendly:
            return False
        nearest = min(cp.distance_to(other) for other in friendly)
        return nearest <= AIR_ASSAULT_MAX_REACH.meters

    @staticmethod
    def closest_airfields_to(location: MissionTarget) -> ClosestAirfields:
        """Returns the closest airfields to the given location."""
        return ObjectiveDistanceCache.get_closest_airfields(location)
