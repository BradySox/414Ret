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

    blue_delta = _blue_delta(game, debriefing)
    red_delta = _red_delta(game, debriefing)

    blue_before = game.blue.political_will
    red_before = game.red.political_will
    game.blue.political_will = _clamp(blue_before + blue_delta)
    game.red.political_will = _clamp(red_before + red_delta)

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
        f"({blue_delta:+.1f}); Hanoi's resolve {game.red.political_will:.0f}% "
        f"({red_delta:+.1f}).",
    )


def _blue_delta(game: "Game", debriefing: "Debriefing") -> float:
    from game.missiongenerator.vietnamopsluadata import HEAVY_BOMBER_DCS_IDS
    from game.theater import Player

    delta = BLUE_PASSIVE_REGEN

    # Airframe losses, weighted by what fell. by_type keys are AircraftTypes; heavy
    # bombers reuse the §32 Arc Light identification set. getattr+cast sidesteps the
    # mypy has-type quirk on Debriefing's init-assigned attrs (the sitrep.py precedent).
    air_losses = cast("AirLosses", getattr(debriefing, "air_losses"))
    for aircraft_type, count in air_losses.by_type(Player.BLUE).items():
        heavy = aircraft_type.dcs_unit_type.id in HEAVY_BOMBER_DCS_IDS
        delta -= count * (BLUE_HEAVY_BOMBER_LOSS if heavy else BLUE_AIRFRAME_LOSS)

    # Aviators: fresh captures hit now; every POW still held drains a trickle. Runs
    # after commit_pow_recoveries, so a freed aviator stops draining the same turn.
    captures = getattr(debriefing.state_data, "combat_sar_captures", []) or []
    delta -= len(captures) * BLUE_POW_TAKEN
    delta -= len(game.blue.pending_pow_recoveries) * BLUE_POW_HELD_PER_TURN

    # A rescue is a headline: refund part of the airframe cost per pilot saved.
    rescues = getattr(debriefing.state_data, "combat_sar_rescues", []) or []
    delta += len(rescues) * BLUE_PILOT_RESCUED_REFUND

    blue_losses = debriefing.loss_counts(Player.BLUE)
    delta -= blue_losses.bases_lost * BLUE_BASE_LOST

    # ROE violations (W4): kills inside an active restricted zone draw a sharp
    # penalty -- the LBJ-era pilot could break the rules, but Washington answered
    # for it. Zero whenever no authored phase with zones is active.
    from game.fourteenth.phases import count_roe_violations

    violations = count_roe_violations(game, debriefing)
    if violations:
        delta -= violations * BLUE_ROE_VIOLATION
        game.message(
            "ROE violation",
            f"{violations} target(s) destroyed inside a restricted zone this "
            "turn. Washington takes the heat -- political will pays the bill.",
        )

    # Claimed enemy air kills play well at home (claimed, per the recon-fog framing).
    delta += debriefing.loss_counts(Player.RED).aircraft * BLUE_ENEMY_AIR_CLAIMED

    return delta


def _red_delta(game: "Game", debriefing: "Debriefing") -> float:
    from game.theater import Player

    delta = RED_PASSIVE_REGEN

    red_losses = debriefing.loss_counts(Player.RED)
    # The trail is the artery: convoy kills (the §35 real convoys) bite hardest.
    delta -= red_losses.convoy * RED_CONVOY_UNIT_LOST
    delta -= (red_losses.front_line + red_losses.ground_objects) * RED_GROUND_UNIT_LOST
    delta -= red_losses.aircraft * RED_AIRFRAME_LOSS
    delta -= red_losses.bases_lost * RED_BASE_LOST

    return delta


def _clamp(value: float) -> float:
    return max(WILL_MIN, min(WILL_MAX, value))
