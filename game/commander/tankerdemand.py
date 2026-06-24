"""Theater-tanker placement from receiver demand (414th).

The stock planner places a theater (shared) tanker at the closest friendly control
point and then front-aware support geometry; receiver ``REFUEL`` waypoints are built
separately, so they can end up 50-80+ NM from the tanker. This module computes where
the tanker is actually *useful* -- the strongest cluster of compatible receiver
demand -- so a post-planning pass can move the orbit there.

Pure geometry/scoring only (no pydcs / planner imports) so it is cheap to unit-test.
The caller extracts the demand from the ATO and applies the result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Sequence

from game.utils import Distance, nautical_miles

if TYPE_CHECKING:
    from dcs.mapping import Point
    from game.coalition import Coalition
    from game.dcs.aircrafttype import AirRefuelType


# Receivers farther apart than this are treated as separate demand clusters, so one
# tanker is scored against the receivers it can realistically serve from a single
# orbit rather than the centroid of the whole map. ~1.5x a long CAP commit bubble.
DEFAULT_CLUSTER_RADIUS = nautical_miles(60)


@dataclass(frozen=True)
class RefuelDemand:
    """One receiving flight's draw on a tanker, at its planned REFUEL waypoint."""

    method: Optional[AirRefuelType]  # boom / probe; None = untagged (any tanker)
    count: int  # aircraft in the receiving flight (the weight)
    position: Point  # the receiver's REFUEL waypoint


def _compatible(
    method: Optional[AirRefuelType], tanker_refuel_types: frozenset[AirRefuelType]
) -> bool:
    """Mirror of ``AircraftType.can_refuel_from`` for the method dimension: permissive
    when either side is untagged, otherwise the boom/probe method must match."""
    if method is None:
        return True
    if not tanker_refuel_types:
        return True
    return method in tanker_refuel_types


def best_tanker_service_point(
    demands: Sequence[RefuelDemand],
    tanker_refuel_types: frozenset[AirRefuelType],
    cluster_radius: Distance = DEFAULT_CLUSTER_RADIUS,
) -> Optional[Point]:
    """The aircraft-count-weighted center of the strongest cluster of *compatible*
    receiver demand, or ``None`` if no compatible receiver wants gas.

    "Compatible" honors the tanker's boom/probe methods (untagged either side is
    permissive), so a boom-only tanker is never scored as serving probe receivers.
    Clusters group receivers within ``cluster_radius`` of each other; the strongest
    cluster (most aircraft) wins and the orbit goes to its weighted centroid.
    """
    compatible = [d for d in demands if _compatible(d.method, tanker_refuel_types)]
    if not compatible:
        return None

    radius_m = cluster_radius.meters
    # Greedy single-link clustering: seed a cluster per receiver, absorb any receiver
    # within radius of the seed. Cheap and order-stable for the small per-turn ATO.
    clusters: list[list[RefuelDemand]] = []
    for d in compatible:
        for cluster in clusters:
            if d.position.distance_to_point(cluster[0].position) <= radius_m:
                cluster.append(d)
                break
        else:
            clusters.append([d])

    def cluster_weight(cluster: list[RefuelDemand]) -> int:
        return sum(d.count for d in cluster)

    best = max(clusters, key=cluster_weight)
    total = cluster_weight(best)
    # Count-weighted centroid of the strongest cluster.
    x = sum(d.position.x * d.count for d in best) / total
    y = sum(d.position.y * d.count for d in best) / total
    return best[0].position.new_in_same_map(x, y)


def theater_refuel_demand(coalition: Coalition) -> list[RefuelDemand]:
    """Receiver demand from the planned ATO: one entry per non-tanker flight that has
    a REFUEL waypoint, at that waypoint, weighted by the flight's aircraft count.

    Flights whose own package carries a tanker (a same-package buddy tanker) are
    excluded -- they refuel in-package, so they are not theater-tanker demand and
    keep their current behavior (per the plan)."""
    from game.ato.flighttype import FlightType
    from game.ato.flightwaypointtype import FlightWaypointType

    demands: list[RefuelDemand] = []
    for package in coalition.ato.packages:
        package_has_tanker = any(
            f.flight_type is FlightType.REFUELING for f in package.flights
        )
        if package_has_tanker:
            continue
        for flight in package.flights:
            if flight.flight_type is FlightType.REFUELING:
                continue
            for waypoint in flight.flight_plan.waypoints:
                if waypoint.waypoint_type is FlightWaypointType.REFUEL:
                    demands.append(
                        RefuelDemand(
                            method=flight.unit_type.air_refuel_type,
                            count=flight.count,
                            position=waypoint.position,
                        )
                    )
    return demands


def reposition_theater_tankers(coalition: Coalition) -> None:
    """Post-planning: move each shared theater tanker onto the strongest cluster of
    compatible receiver demand and rebuild its flight plan.

    A "theater tanker" is a REFUELING flight whose package's primary task is REFUELING
    (i.e. a dedicated tanker package, not a same-package buddy tanker). When a tanker
    has no compatible demand it is left untouched on the legacy front-anchored orbit.
    Run after ``TheaterCommander.plan_missions`` has built the full ATO."""
    from game.ato.flighttype import FlightType

    demands = theater_refuel_demand(coalition)
    if not demands:
        return
    for package in coalition.ato.packages:
        if package.primary_task is not FlightType.REFUELING:
            continue
        for flight in package.flights:
            if flight.flight_type is not FlightType.REFUELING:
                continue
            point = best_tanker_service_point(
                demands, flight.unit_type.tanker_refuel_types
            )
            if point is None:
                continue
            flight.refueling_service_point = point
            flight.recreate_flight_plan()
