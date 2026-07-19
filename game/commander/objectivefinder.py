from __future__ import annotations

import itertools
import math
import operator
import random
from collections.abc import Iterable, Iterator
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
from game.ground_forces.ai_ground_planner import reserve_armor_for
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

# Implicit air-threat a control point carries simply by anchoring an active front
# line, expressed in the same "proximity-weighted fighter count" units as the
# airbase contributions in air_threat_score. Calibrated so a front-line sector
# with no nearby enemy airbase lands mid-range and earns roughly half the
# threat-weighted BARCAP bonus; tune if fronts feel over/under-defended.
FRONT_LINE_AIR_THREAT = 4.0


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
        return self._targets_by_range(self.enemy_ships())

    def _targets_by_range(
        self, targets: Iterable[MissionTargetType]
    ) -> Iterator[MissionTargetType]:
        target_ranges: list[tuple[MissionTargetType, float]] = []
        for target in targets:
            ranges: list[float] = []
            for cp in self.friendly_control_points():
                ranges.append(target.distance_to(cp))
            target_ranges.append((target, min(ranges)))

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
                ) and not self.game.settings.plugin_option("mantisiads"):
                    # Prevent strike targets on IADS Buildings when the IADS engine
                    # (MANTIS) is disabled as they do not serve any purpose
                    continue

                if ground_object.is_dead():
                    continue
                if ground_object.name in found_targets:
                    continue
                ranges: list[float] = []
                for friendly_cp in self.friendly_control_points():
                    ranges.append(ground_object.distance_to(friendly_cp))
                targets.append((ground_object, min(ranges)))
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
        yield from self._targets_by_range(candidates)

    def front_lines(self) -> Iterator[FrontLine]:
        """Iterates over all active front lines in the theater."""
        yield from self.game.theater.conflicts()

    def vulnerable_control_points(self) -> Iterator[ControlPoint]:
        """Iterates over friendly CPs that should be defended with BARCAP.

        A control point is defended if it either has an enemy CP within
        ``airbase_threat_range`` (proximity to an enemy airfield) *or* it anchors
        an active front line. The latter establishes a forward defensive CAP line
        along the edge of friendly territory so coverage reaches raids inbound to
        rear income points, not just bases that happen to sit near an enemy
        airfield.
        """
        # §55 P2 (seam 3): RED's posture biases opfor_autoplanner_aggressiveness --
        # SURGE commits more bases to offense, CONSOLIDATE defends everything. Equal to
        # the raw setting for blue and for a stock red (see effective_aggressiveness).
        from game.fourteenth.red_intent import effective_aggressiveness

        aggressiveness = effective_aggressiveness(self.game)
        for cp in self.friendly_control_points():
            if isinstance(cp, OffMapSpawn):
                # Off-map spawn locations don't need protection.
                continue
            if isinstance(cp, NavalControlPoint):
                yield cp  # always consider CVN/LHA as vulnerable
                continue
            airbase_threat_range = self.game.settings.airbase_threat_range
            # OPFOR aggressiveness is the ratio of threat that OPFOR ignores
            # (0 = consider all threats / defend everything, 100 = ignore all
            # threats / commit fully offensive), matching the label and
            # PackagePlanningTask._get_weighted_threat_range. So a higher value
            # makes OPFOR *more* likely to abandon a base/front for offense.
            #
            # A CP that anchors an active front is NEVER abandoned. Aggressiveness
            # means "strip the rear to push forward"; stripping the *front* to push
            # forward is incoherent, and it used to leave the FLOT completely
            # uncovered -- on a single-front theater the roll deleted the only CAP
            # over the front (Red Tide: Haina, the sole front anchor, abandoned on
            # ~1 turn in 5, and it is the theater's most threat-weighted orbit).
            # Rear CPs still roll, so the lever keeps its intended meaning.
            plan_offensively = (
                self.is_player.is_red
                and not cp.has_active_frontline
                and self._offensive_roll(cp) <= aggressiveness
            )
            if plan_offensively:
                # Treat the airfield threat range as zero so this CP isn't
                # considered vulnerable; OPFOR commits its fighters offensively
                # instead of defending here.
                airbase_threat_range = 0
            if cp.has_active_frontline:
                # Forward defensive CAP line: this CP borders enemy territory.
                yield cp
                continue
            airfields_in_proximity = self.closest_airfields_to(cp)
            airfields_in_threat_range = (
                airfields_in_proximity.operational_airfields_within(
                    nautical_miles(airbase_threat_range)
                )
            )
            for airfield in airfields_in_threat_range:
                if not airfield.is_friendly(self.is_player):
                    yield cp
                    break

    def _offensive_roll(self, cp: ControlPoint) -> int:
        """A 1-100 OPFOR offensive-posture roll, stable per (turn, control point).

        Seeding the roll per turn and control point keeps a CP's defend/abandon
        decision consistent across every planning pass within a turn -- the
        planner re-evaluates ``vulnerable_control_points`` repeatedly, and an
        unseeded re-roll made red's posture flicker (a base defended one pass,
        abandoned the next) and incoherent across neighbouring CPs on the same
        front. It still varies turn to turn because the turn is in the seed.
        """
        return random.Random(f"barcap_offensive:{self.game.turn}:{cp.name}").randint(
            1, 100
        )

    def air_threat_score(self, cp: ControlPoint) -> float:
        """A rough measure of the enemy air threat to a friendly control point.

        Sums over enemy operational airfields within ``airbase_threat_range``,
        each contribution weighted by proximity (closer = higher) times the
        number of *air-to-air-capable* aircraft present (more fighters = higher).
        A control point that anchors an active front line also gets a fixed floor
        (``FRONT_LINE_AIR_THREAT``) because a contested front is dangerous
        airspace in its own right -- otherwise a front-line sector with no nearby
        enemy airbase would score 0 and never earn extra BARCAP waves, leaving the
        forward-CAP-line and threat-weighting features decoupled. Used to scale
        how many BARCAP waves a defended CP receives so contested sectors get more
        coverage than quiet flanks.

        Only A2A-tasked types are counted (not bombers/tankers/transports), so a
        base packed with non-fighters doesn't read as a huge air threat and steal
        waves from a sector actually facing fighters.
        """
        threat_range = nautical_miles(self.game.settings.airbase_threat_range)
        if threat_range.meters <= 0:
            return 0.0
        parking_type = ParkingType(fixed_wing=True, fixed_wing_stol=True)
        score = FRONT_LINE_AIR_THREAT if cp.has_active_frontline else 0.0
        for airfield in self.closest_airfields_to(cp).operational_airfields_within(
            threat_range
        ):
            if airfield.is_friendly(self.is_player):
                continue
            distance = meters(airfield.distance_to(cp))
            proximity = max(0.0, 1.0 - distance.meters / threat_range.meters)
            present = airfield.allocated_aircraft(parking_type).present
            fighters = sum(
                count
                for aircraft_type, count in present.items()
                if aircraft_type.capable_of(FlightType.BARCAP)
                or aircraft_type.capable_of(FlightType.TARCAP)
            )
            score += proximity * fighters
        return score

    def normalized_air_threat(self, cp: ControlPoint) -> float:
        """``air_threat_score(cp)`` relative to the theater's hottest friendly
        sector, clamped to ``[0, 1]``.

        Where the volume path normalizes against the *random*
        ``vulnerable_control_points()`` set (it only ever needs the max of that
        set), this normalizes against every friendly control point so it is
        deterministic and safe to call from flight-plan building:
        ``air_threat_score`` itself rolls no dice and the friendly-CP set is
        fixed within a turn, so the same orbit factor comes out no matter how
        many times the builder re-runs. Returns ``0.0`` when no friendly sector
        faces any measurable air threat, which keeps quiet-theater BARCAP
        placement byte-for-byte identical to the legacy uniform spread.
        """
        score = self.air_threat_score(cp)
        if score <= 0.0:
            return 0.0
        max_score = max(
            (self.air_threat_score(c) for c in self.friendly_control_points()),
            default=0.0,
        )
        if max_score <= 0.0:
            return 0.0
        return min(1.0, score / max_score)

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
        return self._targets_by_range(airfields)

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

    @staticmethod
    def closest_airfields_to(location: MissionTarget) -> ClosestAirfields:
        """Returns the closest airfields to the given location."""
        return ObjectiveDistanceCache.get_closest_airfields(location)
