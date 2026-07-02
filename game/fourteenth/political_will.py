"""Vietnam campaign layer W1+W2: the political-will economy and negotiation ending.

Spec: docs/dev/design/414th-vietnam-political-will-roe-notes.md. One mechanic, two
labels: BLUE tracks **Political Will** (Washington's patience), RED tracks **Regime
Resolve** (Hanoi's capacity to absorb punishment). Both live on
``Coalition.political_will`` (0-100, start 100) and are fed **once per flown turn**
from the ``Debriefing`` the mission-results processor already has -- no new Lua, no
debrief-schema change (the §29 SITREP / §37 reconcile precedent).

W1 landed the observe-only economy (numbers move + SITREP band). W2 attaches the
consequence: ``negotiation_verdict`` backs a branch in ``Game.check_win_loss`` ahead
of the territory checks -- **RED resolve exhausted = WIN** (Hanoi agrees to terms;
you never had to take a base), **BLUE will exhausted = LOSS** (Washington orders
withdrawal, whatever the map says), with BLUE-loss precedence if both break on the
same turn (your patience broke first -- no cheap simultaneous win). Territory victory
stays untouched. Everything is behind the ``vietnam_political_will`` setting -- off
means this module never runs and the branch never fires.

The two sides drain differently (historically honest -- Hanoi absorbed catastrophic
loss ratios; Washington bled from every news cycle):

* **BLUE** drains from airframe losses (heavy bombers cost several times a tactical
  jet), aviators captured (an immediate hit **plus a trickle every turn the POW sits
  in captivity** -- the §15 POW clock becomes economy), and bases lost. Combat SAR
  rescues (§21) soften the blow; claimed enemy air kills and a slow passive
  regeneration restore it.
* **RED** drains mostly from **logistics strangulation** -- trail convoy losses (§35's
  real, tracked convoys) and ground attrition -- and barely from airframe losses.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Optional, cast

if TYPE_CHECKING:
    from game import Game
    from game.debriefing import AirLosses, Debriefing

# --- BLUE (Political Will) feed weights -- design-note §7 starting values; tuned in W2.
BLUE_AIRFRAME_LOSS = 1.0
BLUE_HEAVY_BOMBER_LOSS = 6.0  # a downed B-52 is a national event
BLUE_POW_TAKEN = 2.0  # an aviator captured this turn
BLUE_POW_HELD_PER_TURN = 0.5  # each turn a POW sits in Hanoi
BLUE_PILOT_RESCUED_REFUND = 0.5  # a Combat SAR save softens the airframe blow
BLUE_BASE_LOST = 3.0
BLUE_ENEMY_AIR_CLAIMED = 0.25  # restores: a claimed MiG kill plays well at home
BLUE_PASSIVE_REGEN = 0.5
#: W4 ROE coupling: each kill inside an active restricted zone (see
#: phases.count_roe_violations) is a headline -- the sharp soft-enforcement drain
#: that makes the zones bind the player without hard-blocking them.
BLUE_ROE_VIOLATION = 4.0

# --- RED (Regime Resolve) feed weights. Resolve is hard: airframes barely register;
# the trail is the artery.
RED_CONVOY_UNIT_LOST = 1.5
RED_GROUND_UNIT_LOST = 0.25
RED_AIRFRAME_LOSS = 0.25
RED_BASE_LOST = 3.0
RED_PASSIVE_REGEN = 0.75

WILL_MAX = 100.0
WILL_MIN = 0.0

#: Turns of attribution kept on the game (the sparkline already covers the long
#: trend; the ledger answers "why did it move").
WILL_LEDGER_CAP = 60


@dataclass(frozen=True)
class WillLedgerEntry:
    """One flown turn's will movement with its component attribution.

    The legibility half of the W1 economy: the meters said *that* will moved;
    the ledger says *why* (which feed, how much) -- surfaced on the ribbon meter
    hover, the arc expander, and the SITREP band, and the instrument for the M1
    pacing pass. Moves are ``(label, signed value)`` in feed order; the deltas
    are their sums (pre-clamp, so a floor/ceiling turn still shows its physics).
    Pickled on ``Game.will_ledger`` (capped at :data:`WILL_LEDGER_CAP`).
    """

    turn: int
    blue_delta: float
    red_delta: float
    blue_moves: tuple[tuple[str, float], ...]
    red_moves: tuple[tuple[str, float], ...]


def format_moves(moves: tuple[tuple[str, float], ...], limit: int = 4) -> str:
    """The biggest movers as one line: 'airframes x2 -2.0 · POWs held x3 -1.5'."""
    ranked = sorted(moves, key=lambda move: abs(move[1]), reverse=True)[:limit]
    return " · ".join(f"{label} {value:+.1f}" for label, value in ranked)


def latest_ledger_entry(game: "Game") -> Optional[WillLedgerEntry]:
    """The most recent flown turn's attribution, or None (feature off / turn 0)."""
    ledger = getattr(game, "will_ledger", None) or []
    return ledger[-1] if ledger else None


def ledger_notes(game: "Game") -> tuple[Optional[str], Optional[str]]:
    """Rendered (blue, red) attribution lines for the latest flown turn.

    One short line per side -- '−4.0: heavy bombers x1 down −6.0 · …' -- for the
    ribbon meter hover, the expander, and the SITREP band. (None, None) when the
    ledger is empty (feature off, turn 0, or a pre-feature save).
    """
    entry = latest_ledger_entry(game)
    if entry is None:
        return None, None
    blue = f"{entry.blue_delta:+.1f}: {format_moves(entry.blue_moves, limit=3)}"
    red = f"{entry.red_delta:+.1f}: {format_moves(entry.red_moves, limit=3)}"
    return blue, red


def negotiation_verdict(game: "Game") -> Optional[Literal["win", "loss"]]:
    """The W2 negotiation ending, or None while the war goes on.

    Backs the ``vietnam_political_will``-gated branch in ``Game.check_win_loss``
    (decoupled from ``TurnState`` so this module never imports the game core):

    * BLUE will exhausted -> ``"loss"`` -- Washington orders withdrawal, even with
      the front intact.
    * RED resolve exhausted -> ``"win"`` -- Hanoi agrees to terms; no base capture
      required.

    BLUE-loss takes precedence when both break on the same turn (your patience broke
    first -- a simultaneous collapse is never a cheap win). Returns None with the
    setting off, so non-Vietnam campaigns never touch this path.
    """
    if not getattr(game.settings, "vietnam_political_will", False):
        return None
    if game.blue.political_will <= WILL_MIN:
        return "loss"
    if game.red.political_will <= WILL_MIN:
        return "win"
    return None


def update_political_will(game: "Game", debriefing: "Debriefing") -> None:
    """Feed both sides' will from the turn's debriefing (observe-only in W1).

    Runs once per flown turn from the mission-results processor, after the loss and
    POW steps have committed (so the held-POW trickle reads post-recovery state).
    No-op unless ``vietnam_political_will`` is on. Values clamp to [0, 100]; hitting
    zero ends the war via the negotiation branch in ``Game.check_win_loss`` (W2),
    announced here with era-framed copy on the crossing edge.
    """
    if not getattr(game.settings, "vietnam_political_will", False):
        return

    blue_moves = _blue_moves(game, debriefing)
    red_moves = _red_moves(game, debriefing)
    blue_delta = sum(value for _label, value in blue_moves)
    red_delta = sum(value for _label, value in red_moves)

    blue_before = game.blue.political_will
    red_before = game.red.political_will
    game.blue.political_will = _clamp(blue_before + blue_delta)
    game.red.political_will = _clamp(red_before + red_delta)

    # The attribution ledger: why the numbers moved (meter hover / expander /
    # SITREP). getattr: duck-typed test games and pre-feature saves lack the list.
    ledger = getattr(game, "will_ledger", None)
    if ledger is None:
        ledger = []
        game.will_ledger = ledger
    ledger.append(
        WillLedgerEntry(
            turn=getattr(game, "turn", 0),
            blue_delta=blue_delta,
            red_delta=red_delta,
            blue_moves=tuple(blue_moves),
            red_moves=tuple(red_moves),
        )
    )
    del ledger[:-WILL_LEDGER_CAP]

    # Era-framed exhaustion cues (W2): the generic win/loss dialog fires from
    # check_win_loss; these messages carry the negotiation framing. Crossing-edge
    # only, so a side sitting at zero doesn't repeat the banner every turn.
    if game.blue.political_will <= WILL_MIN < blue_before:
        game.message(
            "Washington orders withdrawal",
            "Political will is exhausted -- the home front has turned. The war "
            "ends on their terms, whatever the map says.",
        )
    if game.red.political_will <= WILL_MIN < red_before:
        game.message(
            "Hanoi agrees to terms",
            "The regime's resolve is broken -- negotiators are en route to "
            "Paris. The pressure campaign has done what the front line never "
            "had to.",
        )

    logging.info(
        "Political will: BLUE %+0.1f -> %.1f, RED %+0.1f -> %.1f",
        blue_delta,
        game.blue.political_will,
        red_delta,
        game.red.political_will,
    )
    game.message(
        "Political will",
        f"Washington's patience {game.blue.political_will:.0f}% "
        f"({blue_delta:+.1f} — {format_moves(tuple(blue_moves), limit=3)}); "
        f"Hanoi's resolve {game.red.political_will:.0f}% "
        f"({red_delta:+.1f} — {format_moves(tuple(red_moves), limit=3)}).",
    )


def _blue_moves(game: "Game", debriefing: "Debriefing") -> list[tuple[str, float]]:
    """BLUE's labeled feed components this turn, in feed order (sum = the delta)."""
    from game.missiongenerator.vietnamopsluadata import HEAVY_BOMBER_DCS_IDS
    from game.theater import Player

    moves: list[tuple[str, float]] = [("passive regen", BLUE_PASSIVE_REGEN)]

    # Airframe losses, weighted by what fell. by_type keys are AircraftTypes; heavy
    # bombers reuse the §32 Arc Light identification set. getattr+cast sidesteps the
    # mypy has-type quirk on Debriefing's init-assigned attrs (the sitrep.py precedent).
    air_losses = cast("AirLosses", getattr(debriefing, "air_losses"))
    heavies = 0
    tactical = 0
    for aircraft_type, count in air_losses.by_type(Player.BLUE).items():
        if aircraft_type.dcs_unit_type.id in HEAVY_BOMBER_DCS_IDS:
            heavies += count
        else:
            tactical += count
    if heavies:
        moves.append(
            (f"heavy bombers x{heavies} down", -heavies * BLUE_HEAVY_BOMBER_LOSS)
        )
    if tactical:
        moves.append((f"airframes x{tactical} lost", -tactical * BLUE_AIRFRAME_LOSS))

    # Aviators: fresh captures hit now; every POW still held drains a trickle. Runs
    # after commit_pow_recoveries, so a freed aviator stops draining the same turn.
    captures = getattr(debriefing.state_data, "combat_sar_captures", []) or []
    if captures:
        moves.append(
            (f"aviators captured x{len(captures)}", -len(captures) * BLUE_POW_TAKEN)
        )
    pows = len(game.blue.pending_pow_recoveries)
    if pows:
        moves.append((f"POWs held x{pows}", -pows * BLUE_POW_HELD_PER_TURN))

    # A rescue is a headline: refund part of the airframe cost per pilot saved.
    rescues = getattr(debriefing.state_data, "combat_sar_rescues", []) or []
    if rescues:
        moves.append(
            (
                f"pilots rescued x{len(rescues)}",
                len(rescues) * BLUE_PILOT_RESCUED_REFUND,
            )
        )

    bases_lost = debriefing.loss_counts(Player.BLUE).bases_lost
    if bases_lost:
        moves.append((f"bases lost x{bases_lost}", -bases_lost * BLUE_BASE_LOST))

    # ROE violations (W4): kills inside an active restricted zone draw a sharp
    # penalty -- the LBJ-era pilot could break the rules, but Washington answered
    # for it. Zero whenever no authored phase with zones is active.
    from game.fourteenth.phases import count_roe_violations

    violations = count_roe_violations(game, debriefing)
    if violations:
        moves.append(
            (f"ROE violations x{violations}", -violations * BLUE_ROE_VIOLATION)
        )
        game.message(
            "ROE violation",
            f"{violations} target(s) destroyed inside a restricted zone this "
            "turn. Washington takes the heat -- political will pays the bill.",
        )

    # Claimed enemy air kills play well at home (claimed, per the recon-fog framing).
    claimed = debriefing.loss_counts(Player.RED).aircraft
    if claimed:
        moves.append(
            (f"claimed MiG kills x{claimed}", claimed * BLUE_ENEMY_AIR_CLAIMED)
        )

    return moves


def _red_moves(game: "Game", debriefing: "Debriefing") -> list[tuple[str, float]]:
    """RED's labeled feed components this turn, in feed order (sum = the delta)."""
    from game.theater import Player

    moves: list[tuple[str, float]] = [("passive regen", RED_PASSIVE_REGEN)]

    red_losses = debriefing.loss_counts(Player.RED)
    # The trail is the artery: convoy kills (the §35 real convoys) bite hardest.
    if red_losses.convoy:
        moves.append(
            (
                f"trail convoys x{red_losses.convoy}",
                -red_losses.convoy * RED_CONVOY_UNIT_LOST,
            )
        )
    ground = red_losses.front_line + red_losses.ground_objects
    if ground:
        moves.append((f"ground attrition x{ground}", -ground * RED_GROUND_UNIT_LOST))
    if red_losses.aircraft:
        moves.append(
            (
                f"airframes x{red_losses.aircraft} lost",
                -red_losses.aircraft * RED_AIRFRAME_LOSS,
            )
        )
    if red_losses.bases_lost:
        moves.append(
            (
                f"bases lost x{red_losses.bases_lost}",
                -red_losses.bases_lost * RED_BASE_LOST,
            )
        )

    return moves


def _clamp(value: float) -> float:
    return max(WILL_MIN, min(WILL_MAX, value))
