from __future__ import annotations

from datetime import datetime
from typing import Type

from .airassault import AirAssaultLayout
from .airlift import AirliftLayout
from .formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from .tacticaloverlay import TacticalOverlay, TacticalOverlayDisplay, escort_overlay
from .waypointbuilder import WaypointBuilder
from .. import FlightType
from ..packagewaypoints import PackageWaypoints
from ...utils import feet


class EscortFlightPlan(FormationAttackFlightPlan, TacticalOverlayDisplay):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    def tactical_overlay(self) -> TacticalOverlay:
        doctrine = self.flight.coalition.doctrine
        rng = (
            doctrine.sead_escort_engagement_range
            if self.flight.flight_type is FlightType.SEAD_ESCORT
            else doctrine.escort_engagement_range
        )
        # AI escorts skip the ingress/target waypoints (only_for_player) and turn
        # for home at the escort-hold anchor, ~7-9nm short of the target, without
        # loitering. So the honest reach is the join->escort-hold leg, not a
        # corridor all the way to the target and out to split.
        hold = self.layout.initial
        far = hold.position if hold is not None else self.package.target.position
        route = [self.layout.join.position, far]
        return escort_overlay(route=route, engagement_range=rng)

    @property
    def split_time(self) -> datetime:
        # Avoid infinite recursion when this escort flight is itself the primary flight
        # This can happen when only escort flights remain in a package
        if (
            self.package.primary_flight
            and self.package.primary_flight != self.flight
            and self.package.primary_flight.flight_plan
        ):
            return self.package.primary_flight.flight_plan.mission_departure_time
        else:
            return super().split_time


class Builder(FormationAttackBuilder[EscortFlightPlan, FormationAttackLayout]):
    def layout(self) -> FormationAttackLayout:
        non_formation_escort = False
        if self.package.waypoints is None:
            self.package.waypoints = PackageWaypoints.create(
                self.package, self.coalition, dump_debug_info=False
            )
            if self.package.primary_flight:
                departure = self.package.primary_flight.flight_plan.layout.departure
                self.package.waypoints.join = departure.position.lerp(
                    self.package.target.position, 0.2
                )
                non_formation_escort = True

        builder = WaypointBuilder(self.flight)
        ingress, target = builder.escort(
            self.package.waypoints.ingress, self.package.target
        )
        if non_formation_escort:
            target.position = self.package.waypoints.join
        ingress.only_for_player = True
        target.only_for_player = True
        hold = None
        if not (self.flight.is_helo or non_formation_escort):
            hold = builder.hold(self._hold_point())

        join_pos = (
            WaypointBuilder.perturb(self.package.waypoints.ingress, feet(500))
            if self.flight.is_helo
            else self.package.waypoints.join
        )
        join = builder.join(join_pos)

        split = builder.split(self._get_split())

        is_helo = builder.flight.is_helo
        initial = builder.escort_hold(
            target.position if is_helo else self.package.waypoints.initial,
        )

        pf = self.package.primary_flight
        if pf and pf.flight_type in [
            FlightType.AIR_ASSAULT,
            FlightType.TRANSPORT,
        ]:
            layout = pf.flight_plan.layout
            assert isinstance(layout, AirAssaultLayout) or isinstance(
                layout, AirliftLayout
            )
            if isinstance(layout, AirliftLayout):
                ascent = layout.pickup_ascent or layout.drop_off_ascent
                assert ascent is not None
                join = builder.join(ascent.position)
                if layout.pickup and layout.drop_off_ascent:
                    join = builder.join(layout.drop_off_ascent.position)
            split = builder.split(layout.arrival.position)
            if layout.drop_off:
                initial = builder.escort_hold(
                    layout.drop_off.position,
                )

        departure = builder.takeoff(self.flight.departure)
        # Base navs with no tanker detour: used to estimate the sortie fuel burn and as
        # the default routing when no tanker is needed.
        nav_to = builder.nav_path(
            hold.position if hold else departure.position,
            join.position,
            builder.get_cruise_altitude,
        )
        nav_from = builder.nav_path(
            split.position,
            self.flight.arrival.position,
            builder.get_cruise_altitude,
        )
        arrival = builder.land(self.flight.arrival)

        # Walk the real route at the actual per-leg fuel rates to decide whether the
        # escort needs a tanker and, if so, pre- or post-vul.
        combat_speed = {join, split, target}
        route = [departure]
        if hold is not None:
            route.append(hold)
        route.extend(nav_to)
        route.append(join)
        route.append(ingress)
        if initial is not None:
            route.append(initial)
        route.append(target)
        route.append(split)
        route.extend(nav_from)
        route.append(arrival)

        tasking = self._refuel_tasking(route, combat_speed, split)
        refuel_pre = None
        refuel = None
        # Separate ifs (not elif): BOTH tanks pre- and post-vul.
        if tasking.refuels_pre_vul:
            refuel_pre = builder.refuel(
                self.flight.refuel_waypoint_position(self.package.waypoints.refuel)
            )
            nav_to = builder.nav_path(
                hold.position if hold else departure.position,
                refuel_pre.position,
                builder.get_cruise_altitude,
            )
        if tasking.refuels_post_vul:
            refuel = builder.refuel(
                self.flight.refuel_waypoint_position(self.package.waypoints.refuel)
            )
            nav_from = builder.nav_path(
                refuel.position,
                self.flight.arrival.position,
                builder.get_cruise_altitude,
            )

        return FormationAttackLayout(
            departure=departure,
            hold=hold,
            nav_to=nav_to,
            join=join,
            ingress=ingress,
            initial=initial,
            targets=[target],
            split=split,
            refuel=refuel,
            refuel_pre=refuel_pre,
            nav_from=nav_from,
            arrival=arrival,
            divert=builder.divert(self.flight.divert),
            bullseye=builder.bullseye(),
            custom_waypoints=list(),
        )

    def build(self, dump_debug_info: bool = False) -> EscortFlightPlan:
        return EscortFlightPlan(self.flight, self.layout())
