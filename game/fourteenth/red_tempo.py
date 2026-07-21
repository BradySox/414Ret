"""Vietnam campaign layer W6 -- turn-scheduled red tempo (Hanoi answers).

Historically Hanoi *answered* the air war: bombing halts were logistics windows
(trucks moved in daylight), ground offensives were timed to political moments
(Tet '68, the Easter Offensive that triggered Linebacker), and resolve recovered
whenever the bombs stopped. This module is the thin red-side coupling -- three
levers read off a campaign-authored, turn-windowed ``red_tempo:`` schedule (only
campaigns that author one are affected, so generic campaigns are untouched).

The schedule is a top-level campaign ``red_tempo:`` list of windows, each opening
at a ``from_turn``. The window in effect on a given turn is the LAST whose
``from_turn`` has been reached, so the tempo escalates as the war drags on::

    red_tempo:
      - from_turn: 1
        name: Rolling Thunder
        trail_surge: 1.5
      - from_turn: 8
        name: The Bombing Halt
        trail_surge: 2.0
        resolve_regen: 1.5
      - from_turn: 11
        name: Linebacker
        ground_offensive: 3

Levers:

* ``trail_surge`` -- multiplies the trail-convoy budget (``vietnam_convoy``) and
  allows a second concurrent column while the window holds. Interdiction is the
  counter: a surged trail is more Armed-Recon targets carrying real units.
* ``ground_offensive`` (N turns) -- from the window's ``from_turn``, RED's front
  stances are raised to AGGRESSIVE (never lowered) for N turns, and the trail
  surges with them. The W2b static-front clamp still bounds the movement: the
  pulse bends the line and bleeds BLUE's will, it never sweep-captures a base.
* ``resolve_regen`` -- RED Regime Resolve regained once per turn while the window
  holds ("just wait out the halt" stops being free for Washington). Gated by
  ``vietnam_political_will``.

Re-derived from the campaign YAML by name (never pickled); all entry points are
guarded no-ops without an authored schedule, so the module costs nothing outside
the authored campaigns. See docs/dev/design/414th-vietnam-red-tempo-notes.md.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game

#: The trail surges at least this hard while a ground offensive is running --
#: the Easter Offensive WAS a logistics event before it was a battle.
GROUND_OFFENSIVE_MIN_SURGE = 2.0


@dataclass(frozen=True)
class RedTempoWindow:
    """One turn-opened red-tempo window authored on a campaign."""

    from_turn: int
    name: Optional[str]
    trail_surge: float
    ground_offensive_turns: int
    resolve_regen: float

    @property
    def key(self) -> str:
        """A stable label for the announce latch / logs."""
        return self.name or f"turn{self.from_turn}"


#: Parsed schedules keyed by campaign name (re-derived per process, never pickled).
_SCHEDULE_CACHE: dict[str, tuple[RedTempoWindow, ...]] = {}


def parse_red_tempo(raw: object) -> tuple[RedTempoWindow, ...]:
    """Parse a campaign's top-level ``red_tempo:`` list into windows.

    A malformed block raises (authored data is validated at load, like the old
    phases parser); an absent block is simply an empty schedule.
    """
    if not raw:
        return ()
    if not isinstance(raw, list):
        raise ValueError(f"red_tempo: must be a list of windows: {raw!r}")
    windows: list[RedTempoWindow] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError(f"red_tempo: each window must be a mapping: {entry!r}")
        if "from_turn" not in entry:
            raise ValueError(f"red_tempo: window needs from_turn: {entry!r}")
        windows.append(
            RedTempoWindow(
                from_turn=int(entry["from_turn"]),
                name=entry.get("name"),
                trail_surge=float(entry.get("trail_surge", 1.0)),
                ground_offensive_turns=int(entry.get("ground_offensive", 0)),
                resolve_regen=float(entry.get("resolve_regen", 0.0)),
            )
        )
    windows.sort(key=lambda w: w.from_turn)
    return tuple(windows)


def schedule_for(game: "Game") -> tuple[RedTempoWindow, ...]:
    """The campaign's authored red-tempo schedule, or () (cached per process)."""
    name = getattr(game, "campaign_name", None)
    if not name:
        return ()
    if name in _SCHEDULE_CACHE:
        return _SCHEDULE_CACHE[name]
    schedule: tuple[RedTempoWindow, ...] = ()
    try:
        import yaml

        from game.campaignloader.campaign import Campaign

        for path in Campaign.iter_campaign_defs():
            try:
                with path.open(encoding="utf-8") as campaign_file:
                    data = yaml.safe_load(campaign_file)
            except Exception:  # noqa: BLE001 -- one bad yaml must not kill the scan
                continue
            if isinstance(data, dict) and data.get("name") == name:
                schedule = parse_red_tempo(data.get("red_tempo"))
                break
    except Exception:  # noqa: BLE001
        logging.exception("Red tempo: schedule lookup failed for %r", name)
        schedule = ()
    _SCHEDULE_CACHE[name] = schedule
    return schedule


def active_window(game: "Game") -> Optional[RedTempoWindow]:
    """The window in effect this turn -- the last one whose from_turn is reached."""
    turn = getattr(game, "turn", 0)
    active: Optional[RedTempoWindow] = None
    for window in schedule_for(game):
        if window.from_turn <= turn:
            active = window
    return active


def ground_offensive_active(game: "Game") -> bool:
    """True while the active window's Tet/Easter pulse is open.

    The pulse runs ``ground_offensive`` turns from the window's ``from_turn``.
    """
    window = active_window(game)
    if window is None or window.ground_offensive_turns <= 0:
        return False
    turn = getattr(game, "turn", 0)
    return window.from_turn <= turn < window.from_turn + window.ground_offensive_turns


def trail_surge_multiplier(game: "Game") -> float:
    """The trail-convoy budget multiplier for this turn (1.0 = baseline).

    Reads the active window's ``trail_surge``; a live ground-offensive window
    implies at least :data:`GROUND_OFFENSIVE_MIN_SURGE` (the offensive rides a
    logistics surge even if the window didn't author one).
    """
    window = active_window(game)
    if window is None:
        return 1.0
    surge = max(1.0, window.trail_surge)
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
    announce_red_tempo(game)
    _apply_ground_offensive(game)
    _apply_resolve_regen(game)


def _response_text(window: RedTempoWindow) -> Optional[str]:
    """Hanoi's legible counter-move for a window, or None.

    The player *sees* Hanoi answer the escalation instead of only feeling the
    levers. Derived from the levers present, so every authored window with a
    real effect gets a message without a separate authored string.
    """
    parts: list[str] = []
    if window.ground_offensive_turns > 0:
        parts.append(
            f"a general ground offensive presses every front for "
            f"{window.ground_offensive_turns} turns (Tet/Easter)"
        )
    if window.trail_surge >= 2.0:
        parts.append("the Ho Chi Minh Trail runs at surge capacity")
    if window.resolve_regen > 0:
        parts.append("the regime's resolve steadies while the bombs are held")
    if not parts:
        return None
    return "Hanoi answers: " + "; ".join(parts) + "."


def announce_red_tempo(game: "Game") -> None:
    """Message the player once when a window's red-tempo response begins.

    Fires on the *first* turn a window is in effect (keyed on the window, not the
    turn, so it survives re-inits). Transient guard, never pickled.
    """
    window = active_window(game)
    if window is None:
        return
    text = _response_text(window)
    if text is None:
        return
    if getattr(game, "red_tempo_announced_window", None) == window.key:
        return
    game.red_tempo_announced_window = window.key
    game.message("Hanoi's response", text)


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
    """Regain Regime Resolve once per turn while the active window holds."""
    if not getattr(game.settings, "vietnam_political_will", False):
        return
    window = active_window(game)
    if window is None or window.resolve_regen <= 0:
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
    game.red.political_will = _clamp(before + window.resolve_regen)
    if game.red.political_will > before:
        logging.info(
            "Red tempo: resolve regen %+.1f -> %.1f (%s)",
            window.resolve_regen,
            game.red.political_will,
            window.key,
        )
