from __future__ import annotations

from abc import ABC
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from typing import TYPE_CHECKING, TypeVar

from dcs import Point

from game.flightplan import HoldZoneGeometry
from game.theater import MissionTarget, TheaterGroundObject
from game.theater.theatergroup import SceneryUnit
from game.utils import nautical_miles, Speed, feet, meters, KG_TO_LBS
from .flightplan import FlightPlan
from .formation import FormationFlightPlan, FormationLayout
from .ibuilder import IBuilder
from .planningerror import PlanningError
from .waypointbuilder import StrikeTarget, WaypointBuilder
from .. import FlightType
from ..flightwaypoint import FlightWaypoint
from ..flightwaypointtype import FlightWaypointType
from ..refueltasking import RefuelTasking, decide_refuel_tasking

if TYPE_CHECKING:
    from ..flight import Flight


class FormationAttackFlightPlan(FormationFlightPlan, ABC):
    @property
    def package_speed_waypoints(self) -> set[FlightWaypoint]:
        return {
            self.layout.join,
            self.layout.split,
        } | set(self.layout.targets)

    def speed_between_waypoints(self, a: FlightWaypoint, b: FlightWaypoint) -> Speed:
        # FlightWaypoint is only comparable by identity, so adding
        # target_area_waypoint to package_speed_waypoints is useless.
        if b.waypoint_type == FlightWaypointType.TARGET_GROUP_LOC:
            speed = self.package.formation_speed(self.flight.is_helo)
            if speed is None:
                # No other formation flight in the package (e.g. solo escort
                # being edited before the strike is added). Use this flight's
                # own cruise speed as a reasonable fallback.
                speed = self.best_flight_formation_speed
            return speed
        return super().speed_between_waypoints(a, b)

    @property
    def tot_waypoint(self) -> FlightWaypoint:
        return self.layout.targets[0]

    @property
    def target_area_waypoint(self) -> FlightWaypoint:
        return FlightWaypoint(
            "TARGET AREA",
            FlightWaypointType.TARGET_GROUP_LOC,
            self.package.target.position,
            feet(0),
            "RADIO",
        )

    @property
    def travel_time_to_target(self) -> timedelta:
        """The estimated time between the first waypoint and the target."""
        destination = self.tot_waypoint
        total = timedelta()
        for previous_waypoint, waypoint in self.edges():
            if waypoint == self.tot_waypoint:
                # For anything strike-like the TOT waypoint is the *flight's*
                # mission target, but to synchronize with the rest of the
                # package we need to use the travel time to the same position as
                # the others.
                total += self.travel_time_between_waypoints(
                    previous_waypoint, self.target_area_waypoint
                )
                break
            total += self.travel_time_between_waypoints(previous_waypoint, waypoint)
        else:
            raise PlanningError(
                f"Did not find destination waypoint {destination} in "
                f"waypoints for {self.flight}"
            )
        return total

    @property
    def join_time(self) -> datetime:
        travel_time = self.total_time_between_waypoints(
            self.layout.join, self.layout.ingress
        )
        return self.ingress_time - travel_time

    @property
    def split_time(self) -> datetime:
        travel_time_ingress = self.total_time_between_waypoints(
            self.layout.ingress, self.target_area_waypoint
        )
        travel_time_egress = self.total_time_between_waypoints(
            self.target_area_waypoint, self.layout.split
        )
        minutes_at_target = 0.75 * len(self.layout.targets)
        timedelta_at_target = timedelta(minutes=minutes_at_target)
        return (
            self.ingress_time
            + travel_time_ingress
            + timedelta_at_target
            + travel_time_egress
        )

    @property
    def ingress_time(self) -> datetime:
        tot = self.tot
        travel_time = self.total_time_between_waypoints(
            self.layout.ingress, self.target_area_waypoint
        )
        return tot - travel_time

    @property
    def initial_time(self) -> datetime:
        tot = self.tot
        travel_time = self.travel_time_between_waypoints(
            self.layout.initial, self.target_area_waypoint
        )
        return tot - travel_time

    def tot_for_waypoint(self, waypoint: FlightWaypoint) -> datetime | None:
        if waypoint == self.layout.ingress:
            return self.ingress_time
        elif waypoint == self.layout.initial:
            return self.initial_time
        elif waypoint in self.layout.targets:
            return self.tot
        return super().tot_for_waypoint(waypoint)


@dataclass
class FormationAttackLayout(FormationLayout):
    ingress: FlightWaypoint
    targets: list[FlightWaypoint]
    initial: Optional[FlightWaypoint] = None
    lineup: Optional[FlightWaypoint] = None
    #: Pre-vul (ingress-side) refuel point, used when fuel calculations say the flight
    #: can't fight through the vul on internal fuel. The egress-side ``refuel`` field
    #: (inherited) is the post-vul point. At most one is set; see _refuel_tasking.
    refuel_pre: Optional[FlightWaypoint] = None

    def delete_waypoint(self, waypoint: FlightWaypoint) -> bool:
        if waypoint == self.refuel_pre:
            self.refuel_pre = None
            return True
        return super().delete_waypoint(waypoint)

    def iter_waypoints(self) -> Iterator[FlightWaypoint]:
        yield self.departure
        if self.hold:
            yield self.hold
        yield from self.nav_to
        if self.refuel_pre is not None:
            yield self.refuel_pre
        yield self.join
        if self.lineup:
            yield self.lineup
        yield self.ingress
        if self.initial is not None:
            yield self.initial
        yield from self.targets
        yield self.split
        if self.refuel is not None:
            yield self.refuel
        yield from self.nav_from
        yield self.arrival
        if self.divert is not None:
            yield self.divert
        yield self.bullseye
        yield from self.custom_waypoints


FlightPlanT = TypeVar("FlightPlanT", bound=FlightPlan[FormationAttackLayout])
LayoutT = TypeVar("LayoutT", bound=FormationAttackLayout)


class FormationAttackBuilder(IBuilder[FlightPlanT, LayoutT], ABC):
    def _build(
        self,
        ingress_type: FlightWaypointType,
        targets: list[StrikeTarget] | None = None,
    ) -> FormationAttackLayout:
        assert self.package.waypoints is not None
        builder = WaypointBuilder(self.flight, targets)

        target_waypoints = self._target_waypoints(builder, targets)

        hold = None
        if not self.flight.is_helo:
            hold = builder.hold(self._hold_point())
        join_pos = self.package.waypoints.join
        if self.flight.is_helo:
            join_pos = self.package.waypoints.ingress
            join_pos = WaypointBuilder.perturb(join_pos, feet(500))
        join = builder.join(join_pos)
        split = builder.split(self._get_split())
        # Only flights that fuel calculations say can't make the sortie unrefueled get
        # a tanker, sorted to pre-vul (top off on ingress) or post-vul (tank on egress).
        tasking = self._refuel_tasking()
        refuel_pre = None
        refuel = None
        if self.package.waypoints is not None:
            if tasking.refuels_pre_vul:
                refuel_pre = builder.refuel(self.package.waypoints.refuel)
            elif tasking.refuels_post_vul:
                refuel = builder.refuel(self.package.waypoints.refuel)

        ingress = builder.ingress(
            ingress_type, self.package.waypoints.ingress, self.package.target
        )

        initial = None
        if ingress_type == FlightWaypointType.INGRESS_SEAD:
            initial = builder.sead_search(self.package.target)
        elif ingress_type == FlightWaypointType.INGRESS_SEAD_SWEEP:
            initial = builder.sead_sweep(self.package.target)

        lineup = None
        if self.flight.flight_type == FlightType.STRIKE:
            hdg = self.package.target.position.heading_between_point(ingress.position)
            pos = ingress.position.point_from_heading(hdg, nautical_miles(10).meters)
            lineup = builder.nav(pos, builder.get_combat_altitude)

        is_helo = self.flight.is_helo
        ingress_egress_altitude = builder.get_combat_altitude
        use_agl_ingress_egress = is_helo

        # When tanking pre-vul, the ingress nav routes to the tanker first, then on to
        # the join; the refuel point sits on the home-to-join leg so this is a natural
        # detour rather than a backtrack.
        nav_to_end = refuel_pre.position if refuel_pre else join.position
        return FormationAttackLayout(
            departure=builder.takeoff(self.flight.departure),
            hold=hold,
            nav_to=builder.nav_path(
                hold.position if hold else self.flight.departure.position,
                nav_to_end if join else ingress.position,
                ingress_egress_altitude,
                use_agl_ingress_egress,
            ),
            join=join,
            lineup=lineup,
            ingress=ingress,
            initial=initial,
            targets=target_waypoints,
            split=split,
            refuel=refuel,
            refuel_pre=refuel_pre,
            nav_from=builder.nav_path(
                refuel.position if refuel else split.position,
                self.flight.arrival.position,
                ingress_egress_altitude,
                use_agl_ingress_egress,
            ),
            arrival=builder.land(self.flight.arrival),
            divert=builder.divert(self.flight.divert),
            bullseye=builder.bullseye(),
            custom_waypoints=list(),
        )

    def _target_waypoints(
        self, builder: WaypointBuilder, targets: list[StrikeTarget] | None
    ) -> list[FlightWaypoint]:
        # `targets` can be an *empty* list (not just None) -- e.g. a Strike/DEAD/
        # SEAD against an objective whose units are all already destroyed, since
        # strike_targets_for() only lists live units. Fall back to a single
        # target-area waypoint in that case so the layout always has at least one
        # target (tot_waypoint and the timing math index targets[0]).
        if targets:
            return [
                self.target_waypoint(self.flight, builder, target) for target in targets
            ]
        return [
            self.target_area_waypoint(self.flight, self.flight.package.target, builder)
        ]

    def _refuel_tasking(self) -> RefuelTasking:
        """Decide whether this flight needs a tanker and, if so, pre- or post-vul.

        Estimates the sortie fuel burn from the package geometry (ingress transit at
        cruise, the ingress->target->split vul at combat power, egress home at cruise,
        plus the takeoff climb) and compares it against usable internal fuel. Returns
        NONE when no tanker can be planned, the flight is a helo, fuel data is missing,
        or internal fuel covers the sortie. The geometry is approximate -- the burn
        estimate is a planning heuristic that wants an in-game fuel pass to tune.
        """
        fuel = self.flight.unit_type.fuel_consumption
        waypoints = self.package.waypoints
        if fuel is None or self.flight.is_helo or waypoints is None:
            return RefuelTasking.NONE
        if not self.flight.coalition.air_wing.can_auto_plan(FlightType.REFUELING):
            return RefuelTasking.NONE

        def nm(a: Point, b: Point) -> float:
            return meters(a.distance_to_point(b)).nautical_miles

        departure = self.flight.departure.position
        target = self.package.target.position
        arrival = self.flight.arrival.position

        ingress_nm = nm(departure, waypoints.ingress)
        vul_nm = nm(waypoints.ingress, target) + nm(target, waypoints.split)
        egress_nm = nm(waypoints.split, arrival)

        # First ~10 nm of the climb-out burns at the climb rate, the rest of the
        # ingress at cruise, and the vul at combat power.
        climb_nm = min(ingress_nm, 10.0)
        fuel_to_end_of_vul = (
            climb_nm * fuel.climb
            + (ingress_nm - climb_nm) * fuel.cruise
            + vul_nm * fuel.combat
        )
        fuel_vul_to_home = egress_nm * fuel.cruise

        usable_fuel = self.flight.unit_type.max_fuel * KG_TO_LBS - fuel.taxi
        return decide_refuel_tasking(
            usable_fuel, fuel_to_end_of_vul, fuel_vul_to_home, fuel.min_safe
        )

    @property
    def primary_flight_is_air_assault(self) -> bool:
        if self.flight is self.package.primary_flight:
            # Can't call self.package.primary_flight.flight_plan here
            # because the flight-plan wasn't created yet.
            # Calling the fligh_plan property would result in infinite recursion
            # (SOF inserts and CSAR recoveries reuse the air-assault layout, so they
            # count too).
            return self.flight.flight_type in (
                FlightType.AIR_ASSAULT,
                FlightType.SOF,
                FlightType.CSAR,
            )
        else:
            assert self.package.primary_flight is not None
            fp = self.package.primary_flight.flight_plan
            return fp.is_airassault

    @staticmethod
    def strike_targets_for(location: TheaterGroundObject) -> list[StrikeTarget]:
        """One StrikeTarget per individual unit of a ground objective.

        This is the same per-unit list the kneeboard target page renders (with
        coordinates). Mission types whose kneeboard lists targets with
        coordinates (Strike, DEAD, SEAD) pass this to ``_build`` so each listed
        target also gets its own TARGET_POINT waypoint in the aircraft, making it
        trivial to designate with TOO.
        """
        targets: list[StrikeTarget] = []
        for idx, unit in enumerate(location.strike_targets):
            name = unit.name if isinstance(unit, SceneryUnit) else unit.type.id
            targets.append(StrikeTarget(f"{name} #{idx}", unit))
        return targets

    @staticmethod
    def target_waypoint(
        flight: Flight, builder: WaypointBuilder, target: StrikeTarget
    ) -> FlightWaypoint:
        if flight.flight_type in {FlightType.ANTISHIP, FlightType.BAI}:
            return builder.bai_group(target)
        elif flight.flight_type == FlightType.DEAD:
            return builder.dead_point(target)
        elif flight.flight_type in {FlightType.SEAD, FlightType.SEAD_SWEEP}:
            return builder.sead_point(target)
        else:
            return builder.strike_point(target)

    @staticmethod
    def target_area_waypoint(
        flight: Flight, location: MissionTarget, builder: WaypointBuilder
    ) -> FlightWaypoint:
        if flight.flight_type == FlightType.DEAD:
            return builder.dead_area(location)
        elif flight.flight_type == FlightType.SEAD:
            return builder.sead_area(location)
        elif flight.flight_type == FlightType.OCA_AIRCRAFT:
            return builder.oca_strike_area(location)
        elif flight.flight_type == FlightType.ARMED_RECON:
            return builder.armed_recon_area(location)
        elif flight.flight_type == FlightType.TARPS:
            return builder.recon_area(location)
        else:
            return builder.strike_area(location)

    def _hold_point(self) -> Point:
        assert self.package.waypoints is not None
        origin = self.flight.departure.position
        target = self.package.target.position
        join = self.package.waypoints.join
        ip = self.package.waypoints.ingress
        return HoldZoneGeometry(
            target, origin, ip, join, self.coalition, self.theater
        ).find_best_hold_point()

    def _get_split(self) -> Point:
        assert self.package.waypoints is not None
        assert self.package.primary_flight is not None
        split_pos = (
            self.package.primary_flight.arrival.position
            if self.package.primary_flight.is_helo
            else self.package.waypoints.split
        )
        return split_pos
