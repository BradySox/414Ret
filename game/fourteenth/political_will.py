"""Vietnam campaign layer W1: the political-will economy (observe-only).

Spec: docs/dev/design/414th-vietnam-political-will-roe-notes.md. One mechanic, two
labels: BLUE tracks **Political Will** (Washington's patience), RED tracks **Regime
Resolve** (Hanoi's capacity to absorb punishment). Both live on
``Coalition.political_will`` (0-100, start 100) and are fed **once per flown turn**
from the ``Debriefing`` the mission-results processor already has -- no new Lua, no
debrief-schema change (the §29 SITREP / §37 reconcile precedent).

W1 is **observe-only**: the numbers move and surface (SITREP band, info log) but gate
nothing. The W2 increment adds the negotiation win/loss branch in ``check_win_loss``
(break Hanoi's resolve before Washington's patience breaks). Everything is behind the
``vietnam_political_will`` setting -- off means this module never runs.

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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game
    from game.debriefing import Debriefing

# --- BLUE (Political Will) feed weights -- design-note §7 starting values; tuned in W2.
BLUE_AIRFRAME_LOSS = 1.0
BLUE_HEAVY_BOMBER_LOSS = 6.0  # a downed B-52 is a national event
BLUE_POW_TAKEN = 2.0  # an aviator captured this turn
BLUE_POW_HELD_PER_TURN = 0.5  # each turn a POW sits in Hanoi
BLUE_PILOT_RESCUED_REFUND = 0.5  # a Combat SAR save softens the airframe blow
BLUE_BASE_LOST = 3.0
BLUE_ENEMY_AIR_CLAIMED = 0.25  # restores: a claimed MiG kill plays well at home
BLUE_PASSIVE_REGEN = 0.5

# --- RED (Regime Resolve) feed weights. Resolve is hard: airframes barely register;
# the trail is the artery.
RED_CONVOY_UNIT_LOST = 1.5
RED_GROUND_UNIT_LOST = 0.25
RED_AIRFRAME_LOSS = 0.25
RED_BASE_LOST = 3.0
RED_PASSIVE_REGEN = 0.75

WILL_MAX = 100.0
WILL_MIN = 0.0


def update_political_will(game: "Game", debriefing: "Debriefing") -> None:
    """Feed both sides' will from the turn's debriefing (observe-only in W1).

    Runs once per flown turn from the mission-results processor, after the loss and
    POW steps have committed (so the held-POW trickle reads post-recovery state).
    No-op unless ``vietnam_political_will`` is on. Values clamp to [0, 100]; W1
    attaches no consequence to either bound.
    """
    if not getattr(game.settings, "vietnam_political_will", False):
        return

    blue_delta = _blue_delta(game, debriefing)
    red_delta = _red_delta(game, debriefing)

    game.blue.political_will = _clamp(game.blue.political_will + blue_delta)
    game.red.political_will = _clamp(game.red.political_will + red_delta)

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
    # bombers reuse the §32 Arc Light identification set.
    for aircraft_type, count in debriefing.air_losses.by_type(Player.BLUE).items():
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
