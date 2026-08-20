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


#: Target categories grouped into the families the player actually thinks in.
#: Per-CATEGORY control was rejected as 20 combo rows on one page; the fine grain
#: lives on the per-target override instead, which is where "not THAT factory"
#: belongs anyway. `fob` is absent on purpose -- that TGO is the FOB structure and
#: is never targetable.
TARGET_FAMILIES: dict[str, tuple[str, ...]] = {
    "Air defense": ("aa", "ewr"),
    "Command and control": ("commandcenter", "comms"),
    "Infrastructure": (
        "factory",
        "power",
        "oil",
        "fuel",
        "derrick",
        "ware",
        "village",
        "allycamp",
        "farp",
        "ww2bunker",
    ),
    "Logistics": ("ammo", "motorpool"),
    "Armor": ("armor",),
    "Naval": ("ship", "coastal"),
    "Missile sites": ("missile",),
}

_FAMILY_BY_CATEGORY: dict[str, str] = {
    category: family
    for family, categories in TARGET_FAMILIES.items()
    for category in categories
}


def family_of(target: Any) -> Optional[str]:
    """The target family *target* belongs to, or None if nothing governs it."""
    return _FAMILY_BY_CATEGORY.get(getattr(target, "category", None) or "")


def family_priority(family: str, settings: Optional["Settings"]) -> RegionPriority:
    """The player's priority for one target family; NORMAL when unset."""
    stored = getattr(settings, "blue_target_family_priorities", None) or {}
    try:
        return RegionPriority(stored.get(family, RegionPriority.NORMAL.value))
    except ValueError:
        return RegionPriority.NORMAL


def priority_of(control_point: "ControlPoint") -> RegionPriority:
    """The CP's blue planning priority; NORMAL for pre-§93 saves."""
    return getattr(control_point, "_blue_region_priority", RegionPriority.NORMAL)


def priority_for_target(target: Any) -> Optional[RegionPriority]:
    """The place-priority governing *target*: its own override, else its CP's.

    None means nothing governs it (front lines, convoys, downed pilots) and it is
    never weighted -- a rescue must not rank lower for being in a quiet region.

    The override deliberately beats the control point in BOTH directions, so a
    single target inside an IGNORED base can be marked NORMAL and still be planned.
    That is the whole point of a per-target setting; without it the override could
    only ever subtract.
    """
    from game.theater.controlpoint import ControlPoint

    if not isinstance(target, ControlPoint):
        own = getattr(target, "_blue_region_priority", None)
        if own is not None:
            return own
    owner = owning_control_point(target)
    if owner is None:
        return None
    return priority_of(owner)


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

    # Kind first, and it is absolute: an IGNORED family means no target of that
    # kind anywhere, and no per-target override reopens it. Place is where the
    # override lives.
    family = family_of(target)
    if family is not None:
        kind = family_priority(family, settings)
        if kind is RegionPriority.IGNORED:
            return None
    else:
        kind = RegionPriority.NORMAL

    place = priority_for_target(target)
    if place is None:
        return 1.0
    if place is RegionPriority.IGNORED:
        return None
    return SORT_FACTOR[place] * SORT_FACTOR[kind]


def auto_planning_skips(target: Any, state: Any) -> bool:
    """True when the auto-planner must not propose a package against *target*.

    For targeting sites that read a `TheaterState` list which is ALSO threat data --
    `enemy_ships` feeds `_rebuild_threat_zones`, so filtering the list itself would
    route blue over a carrier it had been told to ignore. Gate the tasking, never
    the threat picture.
    """
    context = getattr(state, "context", None)
    coalition = getattr(context, "coalition", None)
    player = getattr(coalition, "player", None)
    is_blue = bool(getattr(player, "is_blue", False))
    settings = getattr(context, "settings", None)
    return planning_factor(target, settings, is_blue) is None
