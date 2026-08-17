"""Whether supply actually reaches a control point, for the ground war.

The per-turn base strength top-up used to apply unconditionally, so ground taken
drained back on a timer regardless of whether anything could reach the base.
See `docs/dev/design/414th-retribution-long-view.md` seam 4, rung A.

Two things here are load-bearing and easy to undo by accident:

- The tiers are about the KIND of route, not whether one exists.
  `TransitNetworkBuilder` links every friendly airfield to every other one as a
  last resort, so "is there a path" is true almost everywhere and a gate built
  on `has_path_between` would do nothing at all.
- A coalition with no rear area anywhere reads SUPPLIED, not ISOLATED. Small
  campaigns where every base is in contact have nothing to model, and starving
  the whole side would be a silent balance change rather than a supply rule.
"""

from __future__ import annotations

from collections import deque
from enum import Enum, auto
from typing import Iterable, TYPE_CHECKING

from game.theater.transitnetwork import TransitConnection, TransitNetwork

if TYPE_CHECKING:
    from game.theater.controlpoint import ControlPoint


class SupplyStatus(Enum):
    """How well a control point is connected to a rear area."""

    #: Reachable from a rear area over roads or shipping.
    SUPPLIED = auto()
    #: Reachable from a rear area, but only by air.
    AIRLIFTED = auto()
    #: Cut off from every rear area the coalition still holds.
    ISOLATED = auto()


#: Fraction of the per-turn strength recovery each status earns. An air bridge
#: sustains a pocket; it does not rebuild a division.
RECOVERY_MULTIPLIER: dict[SupplyStatus, float] = {
    SupplyStatus.SUPPLIED: 1.0,
    SupplyStatus.AIRLIFTED: 0.25,
    SupplyStatus.ISOLATED: 0.0,
}

_GROUND_LINKS = frozenset({TransitConnection.Road, TransitConnection.Shipping})
_ALL_LINKS = frozenset(TransitConnection)


def _reaches_rear(
    origin: ControlPoint,
    network: TransitNetwork,
    link_types: frozenset[TransitConnection],
) -> bool:
    """True if a rear area is reachable from origin across the given link kinds."""
    seen = {origin}
    queue = deque([origin])
    while queue:
        current = queue.popleft()
        for neighbor in network.connections_from(current):
            if neighbor in seen:
                continue
            if network.link_type(current, neighbor) not in link_types:
                continue
            if not neighbor.has_active_frontline:
                return True
            seen.add(neighbor)
            queue.append(neighbor)
    return False


def supply_status(
    control_point: ControlPoint,
    network: TransitNetwork,
    coalition_has_rear: bool,
) -> SupplyStatus:
    """Supply tier for one control point.

    `coalition_has_rear` distinguishes an encircled pocket from a campaign that
    simply has no rear area to be cut off from -- see the module docstring.
    """
    if not control_point.has_active_frontline:
        return SupplyStatus.SUPPLIED
    if _reaches_rear(control_point, network, _GROUND_LINKS):
        return SupplyStatus.SUPPLIED
    if _reaches_rear(control_point, network, _ALL_LINKS):
        return SupplyStatus.AIRLIFTED
    if not coalition_has_rear:
        return SupplyStatus.SUPPLIED
    return SupplyStatus.ISOLATED


def supply_statuses(
    control_points: Iterable[ControlPoint],
    network: TransitNetwork,
) -> dict[ControlPoint, SupplyStatus]:
    """Supply tier for every control point of one coalition."""
    points = list(control_points)
    has_rear = any(not cp.has_active_frontline for cp in points)
    return {cp: supply_status(cp, network, has_rear) for cp in points}
