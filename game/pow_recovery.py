from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

# How many turns a captured pilot is held as a POW before they are moved deep /
# written off (the recovery window). Mirrors the stranded-SOF rescue clock
# (game/scar_rescue.py). Captured pilots come from the Combat SAR enemy-capture
# race (resources/plugins/combatsar): a snatch party that reaches a downed pilot
# before rescue seizes them.
DEFAULT_POW_HOLD_TURNS = 4


@dataclass
class PendingPowRecovery:
    """A pilot captured by an enemy snatch party, held as a POW pending recovery.

    Persisted on the capturing pilot's ``Coalition`` (``pending_pow_recoveries``).
    Each turn the POW survives un-recovered decrements ``turns_remaining``; at zero
    they are moved deep / written off and the entry dropped.

    ``airframe_unit_name`` is the ejected aircraft's DCS unit name -- the same name
    the loss was scored from -- so a successful recovery can spare that aviator at
    debrief, mirroring the Combat SAR rescue path (``combat_sar_rescues``). ``(x,
    y)`` is the DCS vec2 of the capture (x = north, y = east). The POW is held at
    the nearest enemy airfield, resolved lazily into ``holding_cp_id`` the first
    time the recovery objective is surfaced (mirroring ``PendingSofRescue``'s
    ``anchor_cp_id``).
    """

    airframe_unit_name: str
    x: float
    y: float
    turns_remaining: int = DEFAULT_POW_HOLD_TURNS
    holding_cp_id: Optional[UUID] = None


def age_pending_pows(
    pows: list[PendingPowRecovery],
) -> list[PendingPowRecovery]:
    """Advance the POW recovery window by one turn.

    Decrements every POW's ``turns_remaining`` and drops those that reach zero (the
    pilot was held too long and is moved deep / written off). Returns the
    survivors; the caller reassigns its ``pending_pow_recoveries`` to the result.

    This is the *turn-cap* loss condition only. Freeing a POW by capturing the
    enemy airfield that holds them is a recovery condition, handled where the POW
    is recovered (a later phase), not here.
    """
    survivors = []
    for entry in pows:
        entry.turns_remaining -= 1
        if entry.turns_remaining > 0:
            survivors.append(entry)
    return survivors
