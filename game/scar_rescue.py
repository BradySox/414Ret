from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from uuid import UUID

if TYPE_CHECKING:
    from game.game import Game
    from game.theater import Player

# Default number of turns a stranded SOF team waits for a CSAR pickup before it
# is overrun / written off (the "turn cap" loss condition; overrun-by-front is
# the other). Persisted campaign state lives on Coalition.pending_csars.
DEFAULT_SOF_RESCUE_TURNS = 3


@dataclass
class PendingSofRescue:
    """A SOF team stranded by a botched SCAR capture, awaiting a CSAR pickup.

    Persisted on the owning ``Coalition``. Each turn it survives un-rescued
    decrements ``turns_remaining``; at zero (or when the position is overrun by
    the enemy front) the team is written off and the entry dropped. Recovering it
    refunds one bought SOF team to inventory. ``(x, y)`` is the DCS vec2 of the
    stranded team (x = north, y = east), used to place the next-turn CSAR
    objective on the map.

    ``anchor_cp_id`` is the friendly control point the next-turn "downed SOF
    team" objective is attached to (its ``connected_objectives``). Assigned lazily
    the first time the rescue is surfaced (the nearest friendly control point to
    the strand point). It also drives the *overrun* loss condition: if the anchor
    control point is later captured by the enemy, the front has collapsed over the
    team and it is written off. (A raw "nearest control point is enemy" test would
    false-positive immediately, since SOF strand in enemy territory by design.)
    """

    x: float
    y: float
    turns_remaining: int = DEFAULT_SOF_RESCUE_TURNS
    anchor_cp_id: Optional[UUID] = None


def age_pending_rescues(
    rescues: list[PendingSofRescue],
) -> list[PendingSofRescue]:
    """Advance the turn-cap loss condition by one turn.

    Decrements every pending rescue's ``turns_remaining`` and drops those that
    reach zero (the stranded team waited too long and is written off). Returns
    the survivors; the caller reassigns its ``pending_csars`` to the result.

    This is the *turn-cap* loss condition only. The other loss condition -- the
    enemy front overrunning the stranded position -- is handled where each rescue
    is anchored to a friendly control point (a captured anchor == overrun), since
    SOF strand in contested/enemy territory by design and a raw nearest-control-
    point test would false-positive on the turn they strand.
    """
    survivors = []
    for rescue in rescues:
        rescue.turns_remaining -= 1
        if rescue.turns_remaining > 0:
            survivors.append(rescue)
    return survivors


def surviving_rescues(
    game: Game, player: Player, rescues: list[PendingSofRescue]
) -> list[PendingSofRescue]:
    """Apply both end-of-turn loss conditions and return the survivors.

    1. *Turn cap* -- age every rescue (see :func:`age_pending_rescues`).
    2. *Overrun* -- drop any aged-survivor whose anchor control point the enemy
       now holds (or which no longer exists): the front has collapsed over the
       team. A rescue not yet anchored (stranded this turn, surfaced next turn) is
       never overrun, so a fresh strand can't be lost before it is ever offered.
    """
    survivors = []
    for rescue in age_pending_rescues(rescues):
        if rescue.anchor_cp_id is not None:
            try:
                anchor = game.theater.find_control_point_by_id(rescue.anchor_cp_id)
            except KeyError:
                continue  # anchor base is gone entirely -> written off
            if anchor.captured is not player:
                continue  # anchor captured -> the front overran the team
        survivors.append(rescue)
    return survivors
