from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from uuid import UUID

if TYPE_CHECKING:
    from game.coalition import Coalition
    from game.game import Game
    from game.squadrons.pilot import Pilot
    from game.theater import Player

# How many turns a captured pilot is held as a POW before they are written off,
# on a campaign WITHOUT the political-will economy. Captured pilots come from the
# Combat SAR enemy-capture race (resources/plugins/combatsar): a snatch party that
# reaches a downed pilot before rescue seizes them. On a will-economy campaign
# (vietnam_political_will) the hold is INDEFINITE instead -- the POW drains will
# every turn until freed or the war ends (the §48 "running sore"), and is only
# resolved by recapturing the holding field, a negotiated win (Homecoming), or a
# withdrawal loss (written off). See ``surviving_pows`` / ``resolve_pows_at_game_end``.
DEFAULT_POW_HOLD_TURNS = 4


@dataclass
class PendingPowRecovery:
    """A pilot captured by an enemy snatch party, held as a POW.

    Persisted on the captured pilot's own ``Coalition``
    (``pending_pow_recoveries``). The aviator is **held alive** while a POW:
    capturing the holding airfield **frees** them (they stay in the squadron);
    if the hold clock runs out they are **killed** (a permanent loss). While
    held, each POW drains political will per turn (the Vietnam will economy's
    ``blue_pow_held_per_turn`` feed).

    The dedicated recovery *raid* (a ``CSAR`` flight against a dynamic
    captured-pilot map objective) was shelved in the 2026-07-03 CSAR rescope --
    capture is a campaign consequence, not a plannable mission. See
    ``docs/dev/design/414th-csar-notes.md``.

    ``airframe_unit_name`` is the ejected aircraft's DCS unit name -- the same
    name the loss was scored from. ``(x, y)`` is the DCS vec2 of the capture
    (x = north, y = east). ``holding_cp_id`` is the enemy control point holding
    the POW, resolved at capture time (``resolve_holding_airfield``); ``pilot``
    is the captured aviator, held so the campaign can kill them if the POW is
    abandoned (both Optional for save-migration safety).
    """

    airframe_unit_name: str
    x: float
    y: float
    turns_remaining: int = DEFAULT_POW_HOLD_TURNS
    holding_cp_id: Optional[UUID] = None
    pilot: Optional[Pilot] = None
    #: Campaign turn the capture happened, stamped at record time. Drives the §51
    #: comms-compromise expiry (the enemy's exploitation of the captured comms plan
    #: is time-limited even when the POW hold is indefinite). Optional for
    #: save-migration safety (older pickled entries predate it).
    captured_turn: Optional[int] = None


def resolve_holding_airfield(
    game: Game, coalition: Coalition, entry: PendingPowRecovery
) -> None:
    """Record the enemy control point holding this POW (nearest to the capture).

    Resolved once, at capture time, so the freed-by-field-capture rule in
    ``surviving_pows`` has a field to watch. A still-enemy stored holding is
    kept; if the enemy holds no base at all the id stays ``None`` (the POW then
    just runs the clock).
    """
    if entry.holding_cp_id is not None:
        try:
            stored = game.theater.find_control_point_by_id(entry.holding_cp_id)
        except KeyError:
            stored = None
        if stored is not None and stored.captured is not coalition.player:
            return
    point = game.point_in_world(entry.x, entry.y)
    enemy = [
        cp for cp in game.theater.controlpoints if cp.captured is not coalition.player
    ]
    if not enemy:
        entry.holding_cp_id = None
        return
    nearest = min(enemy, key=lambda cp: point.distance_to_point(cp.position))
    entry.holding_cp_id = nearest.id


def _write_off(entry: PendingPowRecovery, invulnerable_player_pilots: bool) -> None:
    """Resolve a POW held too long / abandoned at war's end.

    Respects the built-in ``invulnerable_player_pilots`` setting exactly like every
    other kill path: the **player's own** aviator is returned to the squadron
    (repatriated) rather than killed; an AI aviator is a permanent loss.
    """
    pilot = entry.pilot
    if pilot is None:
        return
    if pilot.player and invulnerable_player_pilots:
        pilot.repatriate()
    elif pilot.alive:
        pilot.kill()


def surviving_pows(
    game: Game, player: Player, pows: list[PendingPowRecovery]
) -> list[PendingPowRecovery]:
    """Advance the POW hold one turn and apply the free / loss outcomes.

    For each held POW, in order:

    1. *Freed* -- if the enemy airfield holding the POW is now friendly (the side
       recaptured it), the POW walks free: the aviator is repatriated (back to the
       active roster) and dropped.
    2. *Indefinite hold* -- on a political-will campaign the POW is **never** auto-
       written-off: they are held (draining will every turn -- the §48 running sore)
       until freed or the war ends (``resolve_pows_at_game_end``). Kept.
    3. *Abandoned* -- otherwise the hold clock decrements; at zero the POW is written
       off (killed, or repatriated for an invulnerable player pilot). Dropped.
    4. Otherwise the POW is kept for another turn.

    Returns the survivors; the caller reassigns its ``pending_pow_recoveries``.
    """
    settings = game.settings
    will_economy = bool(getattr(settings, "vietnam_political_will", False))
    invulnerable = bool(getattr(settings, "invulnerable_player_pilots", False))
    survivors = []
    for entry in pows:
        if entry.holding_cp_id is not None:
            try:
                holding = game.theater.find_control_point_by_id(entry.holding_cp_id)
            except KeyError:
                holding = None
            if holding is not None and holding.captured is player:
                if entry.pilot is not None:
                    entry.pilot.repatriate()  # holding field fell -> POW freed
                continue
        if will_economy:
            survivors.append(entry)  # indefinite: resolved only by free / war's end
            continue
        entry.turns_remaining -= 1
        if entry.turns_remaining > 0:
            survivors.append(entry)
            continue
        _write_off(entry, invulnerable)  # held past the window -> written off
    return survivors


def resolve_pows_at_game_end(game: Game, coalition: Coalition, won: bool) -> None:
    """Settle a coalition's held POWs when the campaign ends.

    A **negotiated win** brings everyone home (the Homecoming -- every POW is
    repatriated to the active roster); a **withdrawal loss** writes them off
    (killed, or repatriated for an invulnerable player pilot). Either way the
    recovery list is cleared. No-op when the side holds no POWs.
    """
    invulnerable = bool(getattr(game.settings, "invulnerable_player_pilots", False))
    for entry in coalition.pending_pow_recoveries:
        if won:
            if entry.pilot is not None:
                entry.pilot.repatriate()
        else:
            _write_off(entry, invulnerable)
    coalition.pending_pow_recoveries = []


def purge_pow_objectives(game: Game) -> None:
    """Remove any stale captured-pilot map objectives a pre-rescope save carries.

    The shelved recovery raid used to surface each POW as a dynamic
    ``CapturedPilotGroundObject`` torn down and rebuilt every turn; with the
    builder gone, an old save's leftovers would linger forever. Run at turn
    initialization; a no-op on any post-rescope campaign.
    """
    from game.theater.theatergroundobject import CapturedPilotGroundObject

    for cp in game.theater.controlpoints:
        kept = []
        for tgo in cp.connected_objectives:
            if isinstance(tgo, CapturedPilotGroundObject):
                if tgo.id in game.db.tgos.objects:
                    game.db.tgos.remove(tgo.id)
            else:
                kept.append(tgo)
        cp.connected_objectives = kept
