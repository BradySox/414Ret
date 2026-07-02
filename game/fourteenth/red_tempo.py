"""Vietnam campaign layer W6 -- phase-coupled red tempo.

The campaign-phases arc (W3/W4) drives only BLUE; historically Hanoi *answered*
the arc: bombing halts were logistics windows (trucks moved in daylight), ground
offensives were timed to political moments (Tet '68, the Easter Offensive that
triggered Linebacker), and resolve recovered whenever the bombs stopped. This
module is the thin red-side coupling -- three levers read off the ACTIVE AUTHORED
phase's ``red_tempo:`` block (Tier-0 inferred phases never carry one, so generic
campaigns are untouched). See docs/dev/design/414th-vietnam-red-tempo-notes.md.

* ``trail_surge`` -- multiplies the trail-convoy budget (``vietnam_convoy``) and
  allows a second concurrent column while the phase holds. Interdiction remains
  the counter: a surged trail is more Armed-Recon targets carrying real units.
* ``ground_offensive`` (N turns) -- from phase entry, RED's front stances are
  raised to AGGRESSIVE (never lowered) for N turns, and the trail surges with
  them. The W2b static-front clamp still bounds the movement: the pulse bends
  the line and bleeds BLUE's will, it never sweep-captures a base.
* ``resolve_regen`` -- RED Regime Resolve regained once per turn while the phase
  holds ("just wait out the halt" stops being free for Washington). Gated by
  ``vietnam_political_will``.

All entry points are fully guarded no-ops without an active authored phase, so
the module costs nothing outside the authored Vietnam arcs.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from game import Game
    from game.fourteenth.phases import CampaignPhase

#: The trail surges at least this hard while a ground offensive is running --
#: the Easter Offensive WAS a logistics event before it was a battle.
GROUND_OFFENSIVE_MIN_SURGE = 2.0


def _active_authored_phase(game: "Game") -> Optional["CampaignPhase"]:
    from game.fourteenth.phases import active_phase

    phase = active_phase(game)
    if phase is None or not phase.authored:
        return None
    return phase


def ground_offensive_active(game: "Game") -> bool:
    """True while an authored phase's Tet/Easter pulse window is open.

    The window is ``ground_offensive_turns`` turns from the turn the phase was
    entered (``game.phase_entered_on_turn``, which already persists for the
    phase machinery -- no new state).
    """
    phase = _active_authored_phase(game)
    if phase is None or phase.ground_offensive_turns <= 0:
        return False
    entered = getattr(game, "phase_entered_on_turn", None)
    if entered is None:
        return False
    return entered <= game.turn < entered + phase.ground_offensive_turns


def trail_surge_multiplier(game: "Game") -> float:
    """The trail-convoy budget multiplier for this turn (1.0 = baseline).

    Reads the active authored phase's ``trail_surge``; a live ground-offensive
    window implies at least :data:`GROUND_OFFENSIVE_MIN_SURGE` (the offensive
    rides a logistics surge even if the phase didn't author one).
    """
    phase = _active_authored_phase(game)
    if phase is None:
        return 1.0
    surge = max(1.0, phase.trail_surge)
    if ground_offensive_active(game):
        surge = max(surge, GROUND_OFFENSIVE_MIN_SURGE)
    return surge


def apply_red_tempo(game: "Game") -> None:
    """Apply this turn's red-tempo levers. Idempotent; call from initialize_turn.

    Runs after both coalitions have planned (so the stance raise has the final
    say over the commander's balance-gated stance choice) and before the ground
    war is planned (GroundPlanner reads ``cp.stances``). The convoy half is not
    here -- ``ensure_enemy_trail_convoy`` reads :func:`trail_surge_multiplier`
    itself at finish_turn.
    """
    _apply_ground_offensive(game)
    _apply_resolve_regen(game)


def _apply_ground_offensive(game: "Game") -> None:
    """Raise RED's stance to AGGRESSIVE on every active front during the pulse.

    Raise-only: a commander that already chose ELIMINATION/BREAKTHROUGH (it is
    winning outright) keeps its better stance. Idempotent by construction.
    """
    if not ground_offensive_active(game):
        return
    from game.ground_forces.combat_stance import CombatStance

    passive = (
        None,
        CombatStance.RETREAT,
        CombatStance.DEFENSIVE,
        CombatStance.AMBUSH,
    )
    red = game.red.player
    raised = 0
    for front in game.theater.conflicts():
        red_cp = front.control_point_friendly_to(red)
        blue_cp = front.control_point_hostile_to(red)
        if red_cp.stances.get(blue_cp.id) in passive:
            red_cp.stances[blue_cp.id] = CombatStance.AGGRESSIVE
            raised += 1
    if raised:
        logging.info(
            "Red tempo: ground offensive raised %d front stance(s) to AGGRESSIVE",
            raised,
        )


def _apply_resolve_regen(game: "Game") -> None:
    """Regain Regime Resolve once per turn while the authored phase holds."""
    if not getattr(game.settings, "vietnam_political_will", False):
        return
    phase = _active_authored_phase(game)
    if phase is None or phase.resolve_regen <= 0:
        return
    if game.turn < 1:
        return
    # initialize_turn can run more than once per turn (settings re-init etc.);
    # only the first application each turn counts.
    if getattr(game, "red_tempo_regen_turn", None) == game.turn:
        return
    game.red_tempo_regen_turn = game.turn

    from game.fourteenth.political_will import _clamp

    before = game.red.political_will
    game.red.political_will = _clamp(before + phase.resolve_regen)
    if game.red.political_will > before:
        logging.info(
            "Red tempo: resolve regen %+.1f -> %.1f (%s)",
            phase.resolve_regen,
            game.red.political_will,
            phase.name,
        )
