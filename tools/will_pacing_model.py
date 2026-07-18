#!/usr/bin/env python3
"""Project a Vietnam campaign's political-will race over its phase arc.

The will economy (``game/fourteenth/political_will.py``) is fed once per flown turn
from the debriefing; its feel is entirely in the *weights*, and the balance pass was
always meant to happen against a played campaign (checklist M1). Flying 16-20 turns to
test one weight change is far too slow a loop, so this tool models the trajectory
offline: given a campaign's ``will:`` weights + ``phases:`` arc and a set of per-turn
**play archetypes** (how hard the player fights each turn), it marches the two meters
turn-by-turn and reports where each side breaks.

It is a *model*, not the engine -- it reimplements the feed arithmetic of
``_blue_moves`` / ``_red_moves`` (the passive term, airframe/POW/ROE/base drains, the
claimed-kill restore; convoy/ground/airframe attrition + ``resolve_regen`` on red) plus
the two model-3 additions this pass introduces: the **escalation tax**
(``blue_will_on_entry``, charged once per phase entry) and the **commitment ceiling**
(the BLUE war-budget multiplier as will falls, shown for context -- it does not feed
will). Real losses vary, so the numbers still want the in-game M1 pass; this just makes
the *starting* numbers defensible instead of guessed, and lets you sweep them yourself.

Standalone by design (pyyaml only, no ``game`` import / no pydcs) -- the
``campaign_phase_classify.py`` precedent. The Vietnam default weights are mirrored from
``political_will.py`` below and cross-checked against the real dataclass by
``tests/fourteenth/test_will_pacing_model.py`` so they can never silently drift.

Usage (from the repo root)::

    python tools/will_pacing_model.py 1968_Yankee_Station
    python tools/will_pacing_model.py 1968_Yankee_Station --turns 24
    python tools/will_pacing_model.py 1968_Yankee_Station --archetype average

Output is a per-archetype turn table + the break verdict, on stdout.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

CAMP = Path("resources/campaigns")

WILL_MAX = 100.0
WILL_MIN = 0.0

# --- Vietnam default feed weights -----------------------------------------------------
# MIRROR of game/fourteenth/political_will.py's WillWeights defaults. A campaign's
# `will: weights:` block overrides these by name. Kept in sync by
# tests/fourteenth/test_will_pacing_model.py (asserts this dict == the real dataclass
# defaults), so a weight added/renamed there fails CI here until this mirror is updated.
DEFAULT_WEIGHTS: dict[str, float] = {
    "blue_airframe_loss": 1.0,
    "blue_heavy_bomber_loss": 6.0,
    "blue_pow_taken": 2.0,
    "blue_pow_held_per_turn": 0.5,
    "blue_pilot_rescued_refund": 0.5,
    "blue_base_lost": 3.0,
    "blue_enemy_air_claimed": 0.25,
    "blue_passive_regen": 0.5,
    "blue_roe_violation": 4.0,
    "blue_ship_lost": 4.0,
    "blue_ied_detonation": 0.0,
    "red_convoy_unit_lost": 1.5,
    "red_ground_unit_lost": 0.25,
    "red_airframe_loss": 0.25,
    "red_base_lost": 3.0,
    "red_passive_regen": 0.75,
    "red_ship_lost": 0.5,
    "red_cache_lost": 0.0,
    "red_hvt_killed": 0.0,
    "red_hvt_escaped": 0.0,
}

# --- commitment ceiling shape (model 3) -----------------------------------------------
# MIRROR of game/fourteenth/commitment_ceiling.py. As BLUE will falls below
# CEILING_FULL_WILL, Congress trims the war budget linearly down to CEILING_FLOOR_MULT
# at will 0. Shown for context (the ceiling does not itself feed will).
CEILING_FULL_WILL = 60.0
CEILING_FLOOR_MULT = 0.5


def budget_multiplier(blue_will: float) -> float:
    if blue_will >= CEILING_FULL_WILL:
        return 1.0
    if blue_will <= WILL_MIN:
        return CEILING_FLOOR_MULT
    frac = blue_will / CEILING_FULL_WILL  # 0..1 across the ramp
    return CEILING_FLOOR_MULT + (1.0 - CEILING_FLOOR_MULT) * frac


# --- per-turn play archetypes ---------------------------------------------------------
@dataclass
class PlayProfile:
    """How hard the player fights each turn (the model's exogenous inputs).

    Fractions are allowed (a value of 1.5 jets/turn = a jet lost every other turn plus
    one). POW *held* is derived (accumulates new captures minus rescues), not set here.
    """

    name: str
    # BLUE drains
    blue_jets_lost: float = 0.0
    blue_bombers_lost: float = 0.0
    blue_pow_new: float = 0.0
    blue_rescues: float = 0.0
    blue_roe_violations: float = 0.0
    blue_bases_lost: float = 0.0
    # BLUE restore
    blue_mig_claims: float = 0.0
    # RED drains
    red_convoy_kills: float = 0.0
    red_ground_kills: float = 0.0
    red_airframe_kills: float = 0.0
    red_bases_lost: float = 0.0


# Three canonical playstyles. Tuned to bracket the design target:
#   elite  -> break Hanoi early (a hard, disciplined trail+ground strangulation)
#   average-> ride the arc to a Linebacker II negotiated win
#   flounder-> Washington's patience breaks first (a losing war of attrition)
ARCHETYPES: dict[str, PlayProfile] = {
    "elite": PlayProfile(
        name="elite",
        blue_jets_lost=0.8,
        blue_bombers_lost=0.05,
        blue_pow_new=0.2,
        blue_rescues=0.4,
        blue_roe_violations=0.0,
        blue_mig_claims=1.2,
        red_convoy_kills=10.0,
        red_ground_kills=9.0,
        red_airframe_kills=1.2,
    ),
    "average": PlayProfile(
        name="average",
        blue_jets_lost=1.5,
        blue_bombers_lost=0.1,
        blue_pow_new=0.4,
        blue_rescues=0.3,
        blue_roe_violations=0.1,
        blue_mig_claims=0.8,
        red_convoy_kills=5.0,
        red_ground_kills=5.0,
        red_airframe_kills=0.7,
    ),
    "flounder": PlayProfile(
        name="flounder",
        blue_jets_lost=2.4,
        blue_bombers_lost=0.15,
        blue_pow_new=0.8,
        blue_rescues=0.15,
        blue_roe_violations=0.3,
        blue_mig_claims=0.4,
        red_convoy_kills=1.5,
        red_ground_kills=2.0,
        red_airframe_kills=0.3,
    ),
}


# --- campaign will/phase inputs -------------------------------------------------------
@dataclass
class PhaseSpec:
    key: str
    name: str
    min_turn: int = 0
    blue_will_on_entry: float = 0.0
    trail_surge: float = 1.0
    resolve_regen: float = 0.0
    ground_offensive: int = 0
    advance_when_blue_will_below: Optional[float] = None


@dataclass
class CampaignWill:
    name: str
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    phases: list[PhaseSpec] = field(default_factory=list)


def load_campaign(stem: str) -> CampaignWill:
    path = CAMP / f"{stem}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    weights = dict(DEFAULT_WEIGHTS)
    will_block = data.get("will") or {}
    for key, value in (will_block.get("weights") or {}).items():
        if key not in weights:
            raise SystemExit(f"{stem}: unknown will weight {key!r} (typo?)")
        weights[key] = float(value)

    phases: list[PhaseSpec] = []
    for entry in data.get("phases") or []:
        tempo = entry.get("red_tempo") or {}
        advance = entry.get("advance_when") or {}
        phases.append(
            PhaseSpec(
                key=str(entry.get("key", "?")),
                name=str(entry.get("name", entry.get("key", "?"))),
                min_turn=int(entry.get("min_turn", 0)),
                blue_will_on_entry=float(entry.get("blue_will_on_entry", 0.0)),
                trail_surge=float(tempo.get("trail_surge", 1.0)),
                resolve_regen=float(tempo.get("resolve_regen", 0.0)),
                ground_offensive=int(tempo.get("ground_offensive", 0)),
                advance_when_blue_will_below=(
                    float(advance["blue_will_below"])
                    if "blue_will_below" in advance
                    else None
                ),
            )
        )
    return CampaignWill(name=data.get("name", stem), weights=weights, phases=phases)


# --- the model ------------------------------------------------------------------------
@dataclass
class TurnRow:
    turn: int
    phase: str
    blue: float
    red: float
    budget_mult: float


def _active_phase_index(
    phases: list[PhaseSpec], turn: int, blue_will: float, entered_index: int
) -> int:
    """Which phase is active this turn (min_turn schedule + blue_will acceleration).

    Mirrors the engine's rule: leave phase i for i+1 once turn >= arc[i+1].min_turn OR
    the current phase's advance_when.blue_will_below is met. Monotonic-forward.
    """
    index = entered_index
    while index + 1 < len(phases):
        nxt = phases[index + 1]
        reached = turn >= nxt.min_turn
        threshold = phases[index].advance_when_blue_will_below
        accelerated = threshold is not None and blue_will <= threshold
        if reached or accelerated:
            index += 1
        else:
            break
    return index


def simulate(camp: CampaignWill, play: PlayProfile, turns: int) -> list[TurnRow]:
    w = camp.weights
    blue = WILL_MAX
    red = WILL_MAX
    pows_held = 0.0
    rows: list[TurnRow] = []
    phase_index = 0
    charged_entry: set[str] = set()

    for turn in range(1, turns + 1):
        phase_index = _active_phase_index(camp.phases, turn, blue, phase_index)
        phase = camp.phases[phase_index] if camp.phases else None

        # --- BLUE (Washington's patience) -------------------------------------------
        blue += w["blue_passive_regen"]  # war weariness (negative) or regen
        # Escalation tax: entering a more-permissive phase costs will, once.
        if (
            phase is not None
            and phase.blue_will_on_entry
            and phase.key not in charged_entry
        ):
            blue += phase.blue_will_on_entry
            charged_entry.add(phase.key)
        blue -= play.blue_jets_lost * w["blue_airframe_loss"]
        blue -= play.blue_bombers_lost * w["blue_heavy_bomber_loss"]
        blue -= play.blue_pow_new * w["blue_pow_taken"]
        pows_held = max(0.0, pows_held + play.blue_pow_new - play.blue_rescues)
        blue -= pows_held * w["blue_pow_held_per_turn"]
        blue += play.blue_rescues * w["blue_pilot_rescued_refund"]
        blue -= play.blue_roe_violations * w["blue_roe_violation"]
        blue -= play.blue_bases_lost * w["blue_base_lost"]
        blue += play.blue_mig_claims * w["blue_enemy_air_claimed"]

        # --- RED (Hanoi's resolve) --------------------------------------------------
        red += w["red_passive_regen"]
        if phase is not None:
            red += phase.resolve_regen  # bombing-halt recovery
        red -= play.red_convoy_kills * w["red_convoy_unit_lost"]
        red -= play.red_ground_kills * w["red_ground_unit_lost"]
        red -= play.red_airframe_kills * w["red_airframe_loss"]
        red -= play.red_bases_lost * w["red_base_lost"]

        blue = max(WILL_MIN, min(WILL_MAX, blue))
        red = max(WILL_MIN, min(WILL_MAX, red))
        rows.append(
            TurnRow(
                turn=turn,
                phase=phase.key if phase else "-",
                blue=blue,
                red=red,
                budget_mult=budget_multiplier(blue),
            )
        )
        if blue <= WILL_MIN or red <= WILL_MIN:
            break
    return rows


def _bar(value: float, width: int = 20) -> str:
    filled = int(round(value / WILL_MAX * width))
    return "#" * filled + "." * (width - filled)


def verdict(rows: list[TurnRow]) -> str:
    last = rows[-1]
    # BLUE-loss precedence on a simultaneous collapse (matches negotiation_verdict).
    if last.blue <= WILL_MIN:
        return f"LOSS turn {last.turn} — Washington orders withdrawal"
    if last.red <= WILL_MIN:
        return f"WIN turn {last.turn} — Hanoi agrees to terms"
    return f"no break by turn {last.turn} (BLUE {last.blue:.0f} / RED {last.red:.0f})"


def print_run(camp: CampaignWill, play: PlayProfile, turns: int) -> None:
    rows = simulate(camp, play, turns)
    print(f"\n=== {camp.name} — archetype: {play.name} ===")
    print(f"{'turn':>4} {'phase':<14} {'BLUE':>5} {'RED':>5} {'$mult':>5}  will")
    for row in rows:
        print(
            f"{row.turn:>4} {row.phase:<14} {row.blue:>5.0f} {row.red:>5.0f} "
            f"{row.budget_mult:>5.2f}  B[{_bar(row.blue)}] R[{_bar(row.red)}]"
        )
    print(f"  -> {verdict(rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", help="campaign yaml stem, e.g. 1968_Yankee_Station")
    parser.add_argument("--turns", type=int, default=24)
    parser.add_argument(
        "--archetype",
        choices=sorted(ARCHETYPES),
        help="run just one archetype (default: all three)",
    )
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="weight=value",
        help="override a will weight for this run (repeatable), e.g. "
        "--set red_convoy_unit_lost=1.0 --set blue_pow_held_per_turn=0.8",
    )
    args = parser.parse_args()

    camp = load_campaign(args.campaign)
    for override in args.set:
        key, _, value = override.partition("=")
        key = key.strip()
        if key not in camp.weights:
            raise SystemExit(f"--set: unknown will weight {key!r}")
        camp.weights[key] = float(value)
    if camp.phases:
        pins = ", ".join(
            f"{p.key}@{p.min_turn}"
            + (f" entry{p.blue_will_on_entry:+g}" if p.blue_will_on_entry else "")
            for p in camp.phases
        )
        print(f"phases: {pins}")
    overrides = {k: v for k, v in camp.weights.items() if v != DEFAULT_WEIGHTS[k]}
    if overrides:
        print(
            "will weight overrides: "
            + ", ".join(f"{k}={v:g}" for k, v in overrides.items())
        )

    names = [args.archetype] if args.archetype else list(ARCHETYPES)
    for name in names:
        print_run(camp, ARCHETYPES[name], args.turns)


if __name__ == "__main__":
    main()


# Re-exported for the drift-guard test (tests/fourteenth/test_will_pacing_model.py).
__all__ = ["DEFAULT_WEIGHTS", "ARCHETYPES", "load_campaign", "simulate", "PlayProfile"]
