from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from uuid import UUID

if TYPE_CHECKING:
    from game.game import Game
    from game.squadrons.pilot import Pilot
    from game.theater import Player

# How many turns a captured pilot is held as a POW before they are written off
# (the recovery window). Mirrors the stranded-SOF rescue clock
# (game/scar_rescue.py). Captured pilots come from the Combat SAR enemy-capture
# race (resources/plugins/combatsar): a snatch party that reaches a downed pilot
# before rescue seizes them.
DEFAULT_POW_HOLD_TURNS = 4


@dataclass
class PendingPowRecovery:
    """A pilot captured by an enemy snatch party, held as a POW pending recovery.

    Persisted on the capturing pilot's ``Coalition`` (``pending_pow_recoveries``).
    The aviator is **held alive** while a POW: a recovery raid (a surviving CSAR
    flight against the objective) or capturing the holding airfield **frees** them
    (they stay in the squadron); if the recovery clock runs out they are
    **killed** (a permanent loss).

    ``airframe_unit_name`` is the ejected aircraft's DCS unit name -- the same name
    the loss was scored from -- and the key the recovery objective is matched back
    by. ``(x, y)`` is the DCS vec2 of the capture (x = north, y = east). The POW is
    held at the nearest enemy airfield, resolved lazily into ``holding_cp_id`` the
    first time the recovery objective is surfaced. ``pilot`` is the captured
    aviator, held so the campaign can kill them if the POW is abandoned (Optional
    for save-migration safety -- older POW records predate the field).
    """

    airframe_unit_name: str
    x: float
    y: float
    turns_remaining: int = DEFAULT_POW_HOLD_TURNS
    holding_cp_id: Optional[UUID] = None
    pilot: Optional[Pilot] = None


def surviving_pows(
    game: Game, player: Player, pows: list[PendingPowRecovery]
) -> list[PendingPowRecovery]:
    """Advance the POW recovery clock one turn and apply the free / loss outcomes.

    For each held POW, in order:

    1. *Freed* -- if the enemy airfield holding the POW is now friendly (the side
       captured it), the POW walks free: dropped, the aviator survives.
    2. *Abandoned* -- otherwise the recovery clock decrements; at zero the POW was
       held too long and the **aviator is killed** (a permanent loss). Dropped.
    3. Otherwise the POW is kept for another turn.

    Returns the survivors; the caller reassigns its ``pending_pow_recoveries``. An
    in-mission recovery (a CSAR raid) is handled earlier, in
    ``MissionResultsProcessor.commit_pow_recoveries``, so those POWs are already
    gone before this runs.
    """
    survivors = []
    for entry in pows:
        if entry.holding_cp_id is not None:
            try:
                holding = game.theater.find_control_point_by_id(entry.holding_cp_id)
            except KeyError:
                holding = None
            if holding is not None and holding.captured is player:
                continue  # the holding field fell -> the POW is freed, pilot lives
        entry.turns_remaining -= 1
        if entry.turns_remaining > 0:
            survivors.append(entry)
            continue
        # Held past the recovery window -> the aviator is lost for good.
        if entry.pilot is not None and entry.pilot.alive:
            entry.pilot.kill()
    return survivors
