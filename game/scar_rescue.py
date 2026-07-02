"""SAVE-COMPAT TOMBSTONES for the retired SOF capture economy.

The SCAR commander-capture loop (buy a SOF team, fly a C-130 insert, capture the
enemy commander, recover a stranded team) was dormant since the armor-hunt
plugin was deleted (#266) and its dead code was removed on 2026-07-01. Only two
things remain here:

* :class:`PendingSofRescue` -- old saves may carry pickled instances on
  ``Coalition.pending_csars``; the class must exist for those to unpickle.
  ``Coalition.__setstate__`` drops the list immediately after load.
* :func:`purge_legacy_sof_state` -- sweeps any stale "downed SOF team"
  objectives an old save still carries out of the theater.

The live features that survived the retirement live elsewhere: the command-post
intel fog (``scar_command_post_intel``, ``theatergroundobject.known_for``) and
the Combat SAR capture -> POW -> recovery-raid loop (``game/pow_recovery.py`` /
``game/pow_objectives.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from uuid import UUID

if TYPE_CHECKING:
    from game.game import Game


@dataclass
class PendingSofRescue:
    """Tombstone: a stranded SOF team from the retired capture economy.

    Kept only so pre-retirement saves unpickle; never created anew.
    """

    x: float
    y: float
    turns_remaining: int = 3
    anchor_cp_id: Optional[UUID] = None


def purge_legacy_sof_state(game: Game) -> None:
    """Remove any stale downed-SOF objectives a pre-retirement save carries.

    The loop's dynamic "downed SOF team" objectives used to be torn down and
    rebuilt every turn; with the builder gone, an old save's leftovers would
    linger forever. Run at turn initialization; a no-op on any post-retirement
    campaign.
    """
    from game.theater.theatergroundobject import DownedSofGroundObject

    for cp in game.theater.controlpoints:
        kept = []
        for tgo in cp.connected_objectives:
            if isinstance(tgo, DownedSofGroundObject):
                if tgo.id in game.db.tgos.objects:
                    game.db.tgos.remove(tgo.id)
            else:
                kept.append(tgo)
        cp.connected_objectives = kept
