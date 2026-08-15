"""Living battlespace P1: seat player packages later in the ATO cycle (§89).

The turn's ATO already launches across ~90 minutes; the player just launches at
the front of it. Delaying only the player's startup by a phase-aware pre-roll,
then marching the existing mission simulation to that startup before
generation, puts the rest of the war mid-cycle at spawn -- flights outbound, on
station, and recovering -- with no new spawn machinery.
Design: docs/dev/design/414th-living-battlespace-notes.md (P1).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game
    from game.coalition import Coalition
    from game.settings import Settings

#: Phase curve: minutes of war before the player's startup, by turn number. The
#: first flyable turn keeps its H-hour launch; every turn past the table runs
#: at the settings cap. Strawman values -- open call 1 in the design note.
_EARLY_TURN_PREROLL_MINUTES = {0: 0, 1: 15, 2: 15}


def preroll_minutes(settings: Settings, turn: int) -> int:
    """Minutes of pre-roll this turn, honoring the gate and the cap."""
    if not settings.living_battlespace_preroll:
        return 0
    cap: int = settings.living_battlespace_preroll_cap
    return min(cap, _EARLY_TURN_PREROLL_MINUTES.get(turn, cap))


def pin_player_packages(coalition: Coalition, now: datetime) -> None:
    """Delay each player package so its earliest startup is the pre-roll offset.

    Runs inside ``MissionScheduler.schedule_missions`` after the base TOT pass
    and BEFORE the §69 SEAD windows and the carrier-recovery stagger, so both
    see the pinned player TOTs (a player SEAD's window moves with it; the
    stagger treats player packages as fixed and spaces AI recoveries around
    the new slot). Only ever delays: a package already starting later than the
    offset keeps its schedule, and hand-planned packages are untouched because
    this only runs during auto-planning.
    """
    settings = coalition.game.settings
    # Same duck-typed gate shape as the §69 pass beside this one: the scheduler
    # tests drive schedule_missions with fake games, so the gate must decline
    # before reading anything past the settings object.
    if not getattr(settings, "living_battlespace_preroll", False):
        return
    minutes = preroll_minutes(settings, coalition.game.turn)
    if minutes <= 0:
        return
    desired = now + timedelta(minutes=minutes)
    for package in coalition.ato.packages:
        if not package.has_players:
            continue
        starts = [f.flight_plan.startup_time() for f in package.flights]
        if not starts:
            continue
        delta = desired - min(starts)
        if delta > timedelta():
            package.time_over_target += delta


def auto_preroll_stop_needed(game: Game) -> bool:
    """Whether the launch flow should force a PLAYER_STARTUP fast-forward.

    True when this turn has a pre-roll and a player flight exists to stop on.
    The launch path runs the existing sim fast-forward under a temporary
    PLAYER_STARTUP stop condition when the user's own stop condition
    (DISABLED/MANUAL) would otherwise skip the march and spawn the whole
    pre-roll's worth of war on the ramp.
    """
    if preroll_minutes(game.settings, game.turn) <= 0:
        return False
    return game.ato_has_clients()
