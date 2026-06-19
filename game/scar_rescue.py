from __future__ import annotations

from dataclasses import dataclass

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
    """

    x: float
    y: float
    turns_remaining: int = DEFAULT_SOF_RESCUE_TURNS


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
