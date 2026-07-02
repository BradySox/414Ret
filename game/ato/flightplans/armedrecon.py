from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Type

from dcs import Point

from game.theater import ControlPoint
from .formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from .tacticaloverlay import TacticalOverlay, TacticalOverlayDisplay, attack_run_overlay
from .uizonedisplay import UiZone, UiZoneDisplay
from .waypointbuilder import StrikeTarget, WaypointBuilder
from ..flightwaypointtype import FlightWaypointType
from ...utils import nautical_miles

if TYPE_CHECKING:
    from ..flightwaypoint import FlightWaypoint


def _path_length(path: tuple[Point, ...]) -> float:
    return sum(a.distance_to_point(b) for a, b in zip(path, path[1:]))


def _point_along(path: tuple[Point, ...], fraction: float) -> Point:
    """The point ``fraction`` of the way along a road polyline, by distance."""
    remaining = _path_length(path) * fraction
    for a, b in zip(path, path[1:]):
        leg = a.distance_to_point(b)
        if remaining <= leg and leg > 0:
            heading = a.heading_between_point(b)
            return a.point_from_heading(heading, remaining)
        remaining -= leg
    return path[-1]


class ArmedReconFlightPlan(
    FormationAttackFlightPlan, UiZoneDisplay, TacticalOverlayDisplay
):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    def ui_zone(self) -> UiZone:
        # One engagement ring per search point, so a road sweep shows the whole
        # hunted corridor rather than a single circle at the target.
        return UiZone(
            [waypoint.position for waypoint in self.layout.targets],
            nautical_miles(
                self.flight.coalition.game.settings.armed_recon_engagement_range_distance
            ),
        )

    def tactical_overlay(self) -> TacticalOverlay:
        return attack_run_overlay(
            self.layout.ingress.position,
            self.package.target.position,
            self.layout.split.position,
        )


class Builder(FormationAttackBuilder[ArmedReconFlightPlan, FormationAttackLayout]):
    def layout(self) -> FormationAttackLayout:
        return self._build(FlightWaypointType.INGRESS_ARMED_RECON)

    def _target_waypoints(
        self, builder: WaypointBuilder, targets: list[StrikeTarget] | None
    ) -> list[FlightWaypoint]:
        # Convoy hunting: a single point at the target (which for a convoy or a
        # supply-route interdiction is effectively the origin base) makes for a
        # useless plan -- the trucks are strung out along the road. Sweep the
        # hunted route instead: search points at its start, middle, and end,
        # each anchoring an engage zone at runtime.
        track = self._search_track()
        if track:
            return [builder.armed_recon_point(name, point) for name, point in track]
        return super()._target_waypoints(builder, targets)

    def _search_track(self) -> list[tuple[str, Point]]:
        path = self._hunted_route()
        if path is None or len(path) < 2:
            return []
        # Fly the road from the end nearest the package ingress so the sweep
        # flows away from the ingress instead of backtracking.
        assert self.package.waypoints is not None
        ingress = self.package.waypoints.ingress
        if ingress.distance_to_point(path[-1]) < ingress.distance_to_point(path[0]):
            path = tuple(reversed(path))
        return [
            ("SEARCH START", path[0]),
            ("SEARCH MID", _point_along(path, 0.5)),
            ("SEARCH END", path[-1]),
        ]

    def _hunted_route(self) -> Optional[tuple[Point, ...]]:
        """The road polyline this armed recon should sweep, or None.

        A convoy target sweeps its own road (origin to destination). Armed
        recon fragged on a control point (where the right-click supply-route
        interdiction lands) sweeps that point's supply corridor. Any other
        target keeps the classic single-point plan.
        """
        from game.transfers import Convoy

        target = self.package.target
        if isinstance(target, Convoy):
            path = target.origin.convoy_routes.get(target.destination)
            if path is not None and len(path) >= 2:
                return path
            return (target.route_start, target.route_end)
        if isinstance(target, ControlPoint):
            return self._interdiction_route_for(target)
        return None

    @staticmethod
    def _interdiction_route_for(cp: ControlPoint) -> Optional[tuple[Point, ...]]:
        """The convoy route to sweep for armed recon fragged on a control point.

        Enemy trucks drive the target's own supply corridor, so prefer a road to
        a same-owner neighbor (the rear-to-front trail), taking the longest --
        the most hunting ground; fall back to a contested road. A point with no
        road network returns None and keeps the single-point plan.
        """
        same_owner: list[tuple[Point, ...]] = []
        contested: list[tuple[Point, ...]] = []
        for neighbor, path in cp.convoy_routes.items():
            if len(path) < 2:
                continue
            if neighbor.captured == cp.captured:
                same_owner.append(path)
            else:
                contested.append(path)
        pool = same_owner or contested
        if not pool:
            return None
        return max(pool, key=_path_length)

    def build(self, dump_debug_info: bool = False) -> ArmedReconFlightPlan:
        return ArmedReconFlightPlan(self.flight, self.layout())
