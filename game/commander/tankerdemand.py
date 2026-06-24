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

from game.utils import Distance, meters, nautical_miles

if TYPE_CHECKING:
    from dcs.mapping import Point
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
