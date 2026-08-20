"""Region priorities (§93) — per-control-point blue planning emphasis.

Design: docs/dev/design/414th-region-priorities-notes.md (the upstream-#686 ×
BMS-PAK synthesis). A weight, never a fence: §40's removed ROE zones stay dead —
IGNORED mutes the auto-planner only, a manual package is never blocked. Blue
only by design (seam 7: the enemy planner never reads it). Anchored on control
points because navmesh polygon ids are rebuilt from threat zones every turn.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from game.settings import Settings
    from game.theater.controlpoint import ControlPoint


@unique
class RegionPriority(Enum):
    """The player's planning emphasis for one control point's targets."""

    EMPHASIZED = "emphasized"
    NORMAL = "normal"
    DEPRIORITIZED = "deprioritized"
    IGNORED = "ignored"


#: Distance-equivalent factors for the target sort key: an EMPHASIZED region's
#: targets rank as if at half their range, DEPRIORITIZED as if at double.
#: IGNORED has no factor — the target is dropped from auto-planning entirely.
SORT_FACTOR: dict[RegionPriority, float] = {
    RegionPriority.EMPHASIZED: 0.5,
    RegionPriority.NORMAL: 1.0,
    RegionPriority.DEPRIORITIZED: 2.0,
}


def priority_of(control_point: "ControlPoint") -> RegionPriority:
    """The CP's blue planning priority; NORMAL for pre-§93 saves."""
    return getattr(control_point, "_blue_region_priority", RegionPriority.NORMAL)


def owning_control_point(target: Any) -> Optional["ControlPoint"]:
    """The CP whose region priority governs *target*, or None (exempt).

    A control point governs itself; a TGO is governed by its owning CP. Anything
    else (front lines, convoys, downed pilots) resolves None and is never
    weighted — a rescue must not rank lower for being in a deprioritized region.
    """
    from game.theater.controlpoint import ControlPoint

    if isinstance(target, ControlPoint):
        return target
    owner = getattr(target, "control_point", None)
    if isinstance(owner, ControlPoint):
        return owner
    return None


def planning_factor(
    target: Any, settings: Optional["Settings"], is_blue: bool
) -> Optional[float]:
    """Sort-key factor for one auto-planner target; None means drop it.

    1.0 (identity) whenever the feature is off, the planner is red, or no
    control point governs the target — the gate lives here so every caller
    stays a one-liner. ``settings`` may be None (duck-typed test fakes hold
    partial games); absent means off.
    """
    if not is_blue or not getattr(settings, "region_priorities", False):
        return 1.0
    owner = owning_control_point(target)
    if owner is None:
        return 1.0
    priority = priority_of(owner)
    if priority is RegionPriority.IGNORED:
        return None
    return SORT_FACTOR[priority]
