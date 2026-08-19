"""Transient "overview" reveal toggle for the recon fog-of-war.

The 414th recon fog hides an enemy site's composition and threat/detection
rings, and hides SCAR command posts outright, until the player engages the site
(see ``TheaterGroundObject.visibility_for``). This module adds a single runtime
switch that, while enabled, forces every player-facing fog accessor to resolve
to ground truth — the "show the real picture" overview.

It is deliberately a process-global runtime flag, **never persisted**: loading a
save always starts with the fog intact, so a god-view can't be baked into a
campaign or shared by accident. The flag is flipped from the main window's
"Reveal fog of war" view action; the two fog chokepoints (``known_for`` and
``hidden_on_player_map``, both leaves of ``visibility_for``) consult
``fog_revealed()`` and short to truth when it is on. AI/planner/threat math
already pass ``viewer=None`` and are therefore unaffected either way.

This module intentionally has no project imports so it can be pulled in from
anywhere in the theater layer without risk of an import cycle.
"""

from __future__ import annotations

from contextlib import contextmanager
from enum import Enum, auto
from typing import Iterator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game.theater.player import Player
    from game.theater.theatergroundobject import TheaterGroundObject

_revealed: bool = False


class Visibility(Enum):
    """What a viewer can make of a site.

    Three states rather than two independent booleans, because the booleans
    could contradict each other: a `map_hidden` site that a strike had marked
    discovered read hidden AND known at once. A site you cannot see cannot also
    be a site whose composition you know, and this makes that unrepresentable.
    """

    #: Not on the viewer's map at all -- no marker, not plannable or strikable.
    HIDDEN = auto()
    #: A marker the viewer can see, whose composition they do not know.
    UNKNOWN = auto()
    #: Fully known.
    KNOWN = auto()


def fog_revealed() -> bool:
    """Whether the overview is on (player-facing fog forced to ground truth)."""
    return _revealed


def set_fog_revealed(value: bool) -> None:
    """Enable/disable the overview. Runtime-only; never written to a save."""
    global _revealed
    _revealed = bool(value)


def viewer_sees_truth(viewer: Optional["Player"], owner: "TheaterGroundObject") -> bool:
    """Whether `viewer` is entitled to ground truth about `owner`.

    The clause every fog rule opens with, written once. `viewer=None` is the
    omniscient view the AI, planner and threat math use; the overview forces
    truth for anyone; and a side always sees its own.

    Short-circuits deliberately -- `is_friendly` needs a real viewer, so it must
    not be evaluated when there is none.
    """
    if viewer is None or fog_revealed():
        return True
    return owner.is_friendly(viewer)


@contextmanager
def fog_intact() -> Iterator[None]:
    """Force the real fog for the duration, whatever the overview toggle says.

    The reveal is a *display* overview; anything that bakes fog-gated intel
    into a shared artifact — mission generation's kneeboard threat pages, the
    §74 DTC threat rings — must run inside this, or a host generating with the
    overview ticked hands every client the god-view the module docstring
    promises can never be shared by accident.
    """
    global _revealed
    previous = _revealed
    _revealed = False
    try:
        yield
    finally:
        _revealed = previous


def hidden_from(viewer: "Player", owner: "TheaterGroundObject") -> bool:
    """Whether `viewer` cannot see `owner` on the map at all, overview ignored.

    The gate for anything that picks targets FOR a side automatically -- auto
    raids, the carrier strike, any future fire mission. Naming a site the player
    cannot see hands them a find they were meant to earn, and the reveal that
    follows the strike makes it permanent.

    `fog_intact()` because the overview is a *display* toggle: a host who ticks
    "reveal fog of war" and then passes the turn must get the same targets as one
    who did not. `viewer` is a parameter rather than a default so this module
    keeps its no-project-imports promise.
    """
    with fog_intact():
        return owner.hidden_on_player_map(viewer)
