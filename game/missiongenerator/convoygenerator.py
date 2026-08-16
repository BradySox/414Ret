from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional, Tuple

from dcs import Mission
from dcs.mapping import Point
from dcs.point import PointAction
from dcs.unit import Vehicle
from dcs.unitgroup import VehicleGroup

from game.dcs.groundunittype import GroundUnitType
from game.missiongenerator.groundforcepainter import GroundForcePainter
from game.transfers import Convoy
from game.unitmap import UnitMap
from game.utils import kph

if TYPE_CHECKING:
    from game import Game
    from game.theater.player import Player


#: How far a convoy must start from an airfield's reference point.
#:
#: A DCS airfield's reference point is the position pydcs itself uses for a
#: ``StartType.Runway`` spawn, i.e. the runway. An ``Airfield`` control point's
#: ``position`` *is* that point, so a supply route whose first waypoint was
#: authored at the control point parks the whole convoy on the runway. 1.5 km
#: clears a typical runway half-length plus its aprons while keeping the convoy
#: at the base -- still BAI-targetable and inside the field's defensive umbrella.
AIRFIELD_SPAWN_CLEARANCE_M = 1500.0

#: Never walk a convoy more than this far down its route looking for clear
#: ground; if the whole approach is fouled, leave the spawn where it was
#: authored rather than marching the convoy toward the enemy.
MAX_SPAWN_WALK_M = 5000.0

#: Sampling interval used while walking the route out of the keep-out circle.
SPAWN_WALK_STEP_M = 50.0


@dataclass(frozen=True)
class SpawnPlan:
    """How a convoy is laid out at mission start."""

    #: Where the lead vehicle parks.
    position: Point

    #: The authored spawn chain to lay the rest of the convoy along, if any.
    spawns: Optional[Tuple[Point, ...]]

    #: Whether ``position`` had to be walked clear of the origin's runway. When it
    #: was, the authored start is no longer a waypoint the convoy should drive to.
    cleared: bool


class ConvoyGenerator:
    def __init__(self, mission: Mission, game: Game, unit_map: UnitMap) -> None:
        self.mission = mission
        self.game = game
        self.unit_map = unit_map
        self.count = itertools.count()

    def generate(self) -> None:
        # Reset the count to make generation deterministic.
        if not self.game.settings.perf_disable_convoys:
            used: set[str] = set()
            for coalition in self.game.coalitions:
                for convoy in coalition.transfers.convoys:
                    self.generate_convoy(convoy, used)

    def spawn_position(self, convoy: Convoy) -> Point:
        """Where the convoy's lead vehicle parks at mission start.

        Normally the authored start of the supply route. When that point sits on
        the origin airfield's reference point -- the runway -- walk the authored
        route away from the field until clear, so the convoy does not block
        takeoffs. Falls back to the authored point whenever no clear spot is
        found within :data:`MAX_SPAWN_WALK_M`.
        """
        start = convoy.route_start
        airport = convoy.origin.dcs_airport
        if airport is None:
            return start

        reference = airport.position
        if start.distance_to_point(reference) >= AIRFIELD_SPAWN_CLEARANCE_M:
            return start

        theater = self.game.theater
        walked = 0.0
        last = start
        for waypoint in convoy.origin.convoy_route_to(convoy.destination)[1:]:
            leg = last.distance_to_point(waypoint)
            if leg <= 0:
                continue
            steps = max(1, int(leg / SPAWN_WALK_STEP_M))
            for step in range(1, steps + 1):
                if walked + leg * (step / steps) > MAX_SPAWN_WALK_M:
                    return start
                candidate = last.lerp(waypoint, step / steps)
                if candidate.distance_to_point(
                    reference
                ) >= AIRFIELD_SPAWN_CLEARANCE_M and theater.is_on_land(candidate):
                    logging.debug(
                        "Moved %s spawn %.0fm clear of the %s reference point",
                        convoy.name,
                        candidate.distance_to_point(start),
                        convoy.origin.name,
                    )
                    return candidate
            walked += leg
            last = waypoint
        return start

    def spawn_plan(self, convoy: Convoy) -> SpawnPlan:
        """Where the convoy parks, and whether its authored chain survives.

        An authored spawn chain positions every unit after the lead explicitly;
        moving only the lead would strand it ahead of the rest, so the author's
        placement is respected wholesale -- unless the chain itself begins on the
        runway. It is built by interpolating *from the route's endpoint*, so a
        route authored on the airfield reference point yields a chain whose lead
        vehicle parks on the runway however well the marker was placed. Clearing
        the field wins over honoring the chain.
        """
        spawns = convoy.origin.convoy_spawns.get(convoy.destination)
        position = self.spawn_position(convoy)
        cleared = position.distance_to_point(convoy.route_start) > 0
        if spawns and cleared:
            logging.warning(
                "%s's spawn chain at %s begins on the runway; spawning the convoy "
                "clear of the field instead",
                convoy.name,
                convoy.origin.name,
            )
            return SpawnPlan(position, None, True)
        if spawns:
            return SpawnPlan(convoy.route_start, spawns, False)
        return SpawnPlan(position, None, cleared)

    def generate_convoy(
        self, convoy: Convoy, used: Optional[set[str]] = None
    ) -> VehicleGroup:
        plan = self.spawn_plan(convoy)
        position = plan.position
        spawns_tuple = plan.spawns
        cleared = plan.cleared

        # A campaign saved before the name counters stopped resetting per mission
        # already holds duplicate convoy names; their units then collide in the unit
        # map and generation dies, stranding the save. Suffix the later one so an
        # affected campaign still launches.
        name = convoy.name
        if used is not None:
            suffix = 2
            while name in used:
                name = f"{convoy.name} ({suffix})"
                suffix += 1
            used.add(name)

        group = self._create_mixed_unit_group(
            name,
            position,
            convoy.units,
            convoy.player_owned,
        )
        group.manualHeading = True

        if spawns_tuple:
            spawns = list(spawns_tuple)
            last_unit = group.units[0]
            spawns.pop(0)
            for u in group.units[1:]:
                if spawns:
                    u.position = spawns.pop(0)
                    u.heading = u.position.heading_between_point(last_unit.position)
                    if last_unit.heading == 0:
                        last_unit.heading = u.heading
                    last_unit = u
                else:
                    logging.warning(
                        f"Insufficient convoy spawns at {convoy.origin.name} "
                        f"with destination {convoy.destination.name}, "
                        "convoy may experience issues at mission start"
                    )
                    break

        wpts: List[Point] = []
        route = convoy.origin.convoy_route_to(convoy.destination)
        if self.game.settings.convoys_travel_full_distance:
            # When the spawn was walked clear of the runway, the authored start is
            # the point we just moved away from -- keeping it as the first waypoint
            # would drive the convoy straight back onto it.
            wpts.extend(route[1:] if cleared else route)
        else:
            # convoys_travel_full_distance is disabled, so have the convoy only move the
            # first segment on the route. This option aims to remove long routes for
            # ground vehicles between control points, since the CPU load for pathfinding
            # long routes on DCS can be pretty heavy.
            # Select the first route segment from the origin towards the destination so
            # the convoy spawns at the origin CP. This allows the convoy to be targeted
            # by BAI flights and starts it within the protection umbrella of the CP.
            wpts.append(route[1])

        for wpt in wpts:
            group.add_waypoint(
                wpt,
                speed=kph(40).kph,
                move_formation=PointAction.OnRoad,
            )

        self.make_drivable(group)
        self.unit_map.add_convoy_units(group, convoy)
        return group

    def _create_mixed_unit_group(
        self,
        name: str,
        position: Point,
        units: dict[GroundUnitType, int],
        for_player: Player,
    ) -> VehicleGroup:
        unit_types = list(units.items())
        main_unit_type, main_unit_count = unit_types[0]

        faction = self.game.coalition_for(for_player).faction
        country = self.mission.country(faction.country.name)

        group = self.mission.vehicle_group(
            country,
            name,
            main_unit_type.dcs_unit_type,
            position=position,
            group_size=main_unit_count,
            move_formation=PointAction.OnRoad,
        )

        unit_name_counter = itertools.count(main_unit_count + 1)
        # pydcs spreads units out by 20 in the Y axis by default. Pick up where it left
        # off.
        y = itertools.count(position.y + main_unit_count * 20, 20)
        for unit_type, count in unit_types[1:]:
            for i in range(count):
                v = self.mission.vehicle(
                    f"{name} Unit #{next(unit_name_counter)}", unit_type.dcs_unit_type
                )
                v.position.x = position.x
                v.position.y = next(y)
                v.heading = 0
                GroundForcePainter(faction, v).apply_livery()
                group.add_unit(v)

        return group

    @staticmethod
    def make_drivable(group: VehicleGroup) -> None:
        for v in group.units:
            if isinstance(v, Vehicle):
                v.player_can_drive = True
