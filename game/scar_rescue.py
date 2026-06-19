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
