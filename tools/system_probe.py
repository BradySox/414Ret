#!/usr/bin/env python3
"""Multi-turn self-play probe for the 414th's campaign systems.

The 2026-07-18 early-systems audit's empirical pass: generate a real campaign
through the engine pipeline (the ``campaign_phase_laydown.py --engine`` recipe),
march N turns with ``pass_turn(no_action=True)`` (the T1 15-turn-probe method),
and sample every early-core system each turn — so "does this system actually
fire, and does engaging with it change anything?" gets numbers instead of a
turn-0 headless check.

Intervention scripts model the player's counter-move so the KEEP/KILL ledger can
compare ignore-cost vs engage-payoff:

  baseline        no interventions — what the war does if the player ignores
                  every system (IED detonations become a flat mandate tax,
                  HVT windows lapse, caches never die...).
  engage          the player fights the systems: IED devices swept every turn,
                  the HVT struck while its window is open, half the insurgent
                  ammo caches killed at ENGAGE_CACHES_TURN (all of them 4 turns
                  later) to exercise the C1 regen throttle.

Interventions mutate through ``TheaterUnit.kill(GameUpdateEvents())`` — the real
kill path (threat-poly invalidation included), not a bare ``alive = False``.

Usage (repo root, the Retribution venv):
    python tools/system_probe.py coin_enduring_resolve --turns 18
    python tools/system_probe.py coin_enduring_resolve --turns 18 --script engage
    python tools/system_probe.py iraq_inherent_resolve --turns 15
    python tools/system_probe.py red_tide --turns 12 --out probes/

Writes one JSONL record per turn to ``--out`` (default ``probe_out/``) as
``<campaign>_<script>.jsonl`` plus a end-of-run summary on stdout. Every sampler
is getattr-guarded: a missing subsystem records ``null``s, never aborts a run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Pin imports to THIS checkout's code (worktree-safe): `python tools/...` puts
# tools/ on sys.path, not the repo root, and the shared venv could otherwise
# resolve `game` from a different checkout — probing stale code silently.
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))
os.chdir(_REPO_ROOT)

CAMP = "resources/campaigns"


def _build_game(yaml_path: str, saved_games: str) -> Any:
    from game import persistency
    from game.campaignloader.campaign import Campaign
    from game.factions import FACTIONS
    from game.settings import Settings
    from game.theater.start_generator import (
        GameGenerator,
        GeneratorSettings,
        ModSettings,
    )

    persistency.setup(saved_games, False, 0)

    campaign = Campaign.from_file(Path(yaml_path))
    theater = campaign.load_theater(campaign.advanced_iads)
    air_wing_config = campaign.load_air_wing_config(theater)
    player = FACTIONS[campaign.recommended_player_faction]
    enemy = FACTIONS[campaign.recommended_enemy_faction]

    settings = Settings()
    if campaign.settings:
        settings.__dict__.update(Settings.deserialize_state_dict(campaign.settings))

    gen_settings = GeneratorSettings(
        start_date=campaign.recommended_start_date or datetime(2000, 1, 1),
        start_time=campaign.recommended_start_time,
        player_budget=campaign.recommended_player_money,
        enemy_budget=campaign.recommended_enemy_money,
        inverted=False,
        advanced_iads=campaign.advanced_iads,
        no_carrier=False,
        no_lha=False,
        no_player_navy=False,
        no_enemy_navy=False,
        tgo_config=campaign.load_ground_forces_config(),
        carrier_config=campaign.load_carrier_config(),
        squadrons_start_full=True,
    )
    generator = GameGenerator(
        player=player,
        enemy=enemy,
        theater=theater,
        air_wing_config=air_wing_config,
        settings=settings,
        generator_settings=gen_settings,
        mod_settings=ModSettings(),
        campaign_name=campaign.name,
    )
    game = generator.generate()
    game.begin_turn_0(squadrons_start_full=True)
    return game


# --------------------------------------------------------------------------
# Samplers. Every accessor is guarded: absent subsystem -> None, never a crash.
# --------------------------------------------------------------------------


def _safe(fn: Any, default: Any = None) -> Any:
    try:
        return fn()
    except Exception:  # noqa: BLE001 -- probes must survive any missing piece
        return default


def _coin_sample(game: Any) -> dict[str, Any]:
    state = getattr(game, "coin_state", None)
    if not isinstance(state, dict):
        return {"present": False}
    hvt = state.get("hvt") if isinstance(state.get("hvt"), dict) else {}
    active = hvt.get("active") if isinstance(hvt.get("active"), dict) else None
    reinf = state.get("reinfiltration")
    reinf_active = None
    if isinstance(reinf, dict) and isinstance(reinf.get("active"), dict):
        ra = reinf["active"]
        reinf_active = {"stage": ra.get("stage"), "target": ra.get("target_cp_id")}
    return {
        "present": True,
        "hvt_active": (
            {"name": active.get("name"), "turns": active.get("turns")}
            if active
            else None
        ),
        "hvt_cooldown": hvt.get("cooldown", 0),
        "hvt_kills_pending": state.get("hvt_kills", 0),
        "ieds": [
            {"kind": i.get("kind"), "armed": i.get("armed", 0)}
            for i in state.get("ieds", [])
            if isinstance(i, dict)
        ],
        "ied_detonations_pending": state.get("ied_detonations", 0),
        "field_cells": len(state.get("field_cells", []) or []),
        "reinfiltration": reinf_active,
    }


def _cache_census(game: Any) -> dict[str, int]:
    """Red ammo-cache TGOs: alive vs dead (the C1 regen throttle's input)."""
    alive = dead = 0
    for cp in game.theater.controlpoints:
        if not cp.captured.is_red:
            continue
        for tgo in cp.connected_objectives:
            if getattr(tgo, "category", None) != "ammo":
                continue
            units = list(getattr(tgo, "units", [])) + list(getattr(tgo, "statics", []))
            if any(getattr(u, "alive", False) for u in units):
                alive += 1
            else:
                dead += 1
    return {"alive": alive, "dead": dead}


def _red_cell_census(game: Any) -> int:
    """Alive red militia TGO units on red CPs — the C1 revival channel's pool.

    Excludes ``coin_spawned`` transients (IED teams, field cells, HVT convoys)
    exactly like the engine's ``_alive_cell_count``, so the census tracks the
    authored garrison the regen refills, not the event spawns.
    """
    count = 0
    for cp in game.theater.controlpoints:
        if not cp.captured.is_red:
            continue
        for tgo in cp.connected_objectives:
            if getattr(tgo, "category", None) != "armor":
                continue
            if getattr(tgo, "coin_spawned", False):
                continue
            count += sum(
                1 for u in getattr(tgo, "units", []) if getattr(u, "alive", False)
            )
    return count


def _will_sample(game: Any) -> dict[str, Any]:
    ledger = getattr(game, "will_ledger", None) or []
    last = ledger[-1] if ledger else None
    return {
        "blue": _safe(lambda: round(game.blue.political_will, 2)),
        "red": _safe(lambda: round(game.red.political_will, 2)),
        "last_blue_moves": list(getattr(last, "blue_moves", ()) or ()) if last else [],
        "last_red_moves": list(getattr(last, "red_moves", ()) or ()) if last else [],
    }


def _sample(game: Any) -> dict[str, Any]:
    from game.fourteenth.coin_hvt import active_hvt_status

    convoys_blue = _safe(lambda: len(list(game.blue.transfers.convoys)), None)
    convoys_red = _safe(lambda: len(list(game.red.transfers.convoys)), None)
    return {
        "turn": game.turn,
        "cps_red": sum(1 for c in game.theater.controlpoints if c.captured.is_red),
        "cps_blue": sum(1 for c in game.theater.controlpoints if c.captured.is_blue),
        "coin": _coin_sample(game),
        "caches": _safe(lambda: _cache_census(game), {}),
        "red_cells": _safe(lambda: _red_cell_census(game)),
        "hvt_status": _safe(lambda: active_hvt_status(game)),
        "will": _will_sample(game),
        "downed_pilots": len(getattr(game, "downed_pilots", []) or []),
        "pows": _safe(lambda: len(game.blue.pending_pow_recoveries), 0),
        "convoys": {"blue": convoys_blue, "red": convoys_red},
        "ambush_pairs": _safe(
            lambda: len(
                (getattr(game, "convoy_ambush_state", None) or {}).get("ambushes", [])
            )
        ),
        "red_base_armor": _safe(
            lambda: sum(
                int(cp.base.total_armor)
                for cp in game.theater.controlpoints
                if cp.captured.is_red
            )
        ),
        "phase": _safe(lambda: getattr(game, "phase_status_line", None)),
        "red_posture": _safe(
            lambda: getattr(game, "red_intent_posture", None)
            and str(game.red_intent_posture)
        ),
        "supply_blue": _safe(
            lambda: round(
                __import__(
                    "game.fourteenth.war_economy", fromlist=["coalition_supply_health"]
                ).coalition_supply_health(game, game.blue),
                3,
            )
        ),
    }


# --------------------------------------------------------------------------
# Interventions -- the player's counter-move, through the real kill path.
# --------------------------------------------------------------------------

ENGAGE_CACHES_TURN = 5


def _kill_tgo(tgo: Any) -> int:
    from game.sim import GameUpdateEvents

    events = GameUpdateEvents()
    killed = 0
    for unit in list(getattr(tgo, "units", [])) + list(getattr(tgo, "statics", [])):
        if getattr(unit, "alive", False):
            _safe(lambda u=unit: u.kill(events))
            killed += 1
    return killed


def _engage(game: Any, log: list[str]) -> None:
    """Sweep IEDs, strike the open-window HVT, kill caches on schedule."""
    state = getattr(game, "coin_state", None)
    if not isinstance(state, dict):
        return
    from game.fourteenth.coin import _tgo_by_id

    # Sweep every live IED/VBIED (the player flying the TARPS+CAS loop).
    for ied in list(state.get("ieds", []) or []):
        tgo = _safe(lambda i=ied: _tgo_by_id(game, i.get("tgo_id")))
        if tgo is not None:
            n = _kill_tgo(tgo)
            log.append(f"T{game.turn}: swept {ied.get('kind')} ({n} units)")

    # Strike the HVT while the window is open.
    hvt = state.get("hvt") if isinstance(state.get("hvt"), dict) else {}
    active = hvt.get("active") if isinstance(hvt.get("active"), dict) else None
    if active:
        tgo = _safe(lambda: _tgo_by_id(game, active.get("tgo_id")))
        if tgo is not None:
            n = _kill_tgo(tgo)
            log.append(f"T{game.turn}: struck HVT {active.get('name')} ({n} units)")

    # The cache campaign: half at ENGAGE_CACHES_TURN, the rest 4 turns later.
    if game.turn in (ENGAGE_CACHES_TURN, ENGAGE_CACHES_TURN + 4):
        targets = []
        for cp in game.theater.controlpoints:
            if not cp.captured.is_red:
                continue
            for tgo in cp.connected_objectives:
                if getattr(tgo, "category", None) == "ammo":
                    units = list(getattr(tgo, "units", [])) + list(
                        getattr(tgo, "statics", [])
                    )
                    if any(getattr(u, "alive", False) for u in units):
                        targets.append(tgo)
        share = targets if game.turn > ENGAGE_CACHES_TURN else targets[::2]
        for tgo in share:
            _kill_tgo(tgo)
        log.append(f"T{game.turn}: killed {len(share)}/{len(targets)} caches")


THROTTLE_KILL_TURN = 3
CAPTURE_TURN = 4
MILITIA_KILL_COUNT = 30


def _kill_militia(game: Any, count: int, log: list[str]) -> None:
    killed = 0
    for cp in game.theater.controlpoints:
        if not cp.captured.is_red:
            continue
        for tgo in cp.connected_objectives:
            if getattr(tgo, "category", None) != "armor":
                continue
            if getattr(tgo, "coin_spawned", False):
                continue
            from game.sim import GameUpdateEvents

            events = GameUpdateEvents()
            for unit in tgo.units:
                if killed >= count:
                    break
                if getattr(unit, "alive", False):
                    _safe(lambda u=unit: u.kill(events))
                    killed += 1
    log.append(f"T{game.turn}: killed {killed} militia units")


def _kill_all_caches(game: Any, log: list[str]) -> None:
    n = 0
    for cp in game.theater.controlpoints:
        if not cp.captured.is_red:
            continue
        for tgo in cp.connected_objectives:
            if getattr(tgo, "category", None) == "ammo":
                n += 1 if _kill_tgo(tgo) else 0
    log.append(f"T{game.turn}: killed {n} caches")


def _throttle_fed(game: Any, log: list[str]) -> None:
    """Militia attrition with the caches ALIVE: regen refills at full rate."""
    if game.turn == THROTTLE_KILL_TURN:
        _kill_militia(game, MILITIA_KILL_COUNT, log)


def _throttle_starved(game: Any, log: list[str]) -> None:
    """The same attrition with every cache DEAD: regen at the 0.25 floor.

    The slope difference between this run and ``throttle_fed`` is the cache
    system's entire gameplay value, measured.
    """
    if game.turn == THROTTLE_KILL_TURN:
        _kill_all_caches(game, log)
        _kill_militia(game, MILITIA_KILL_COUNT, log)


def _capture(game: Any, log: list[str]) -> None:
    """The player takes the stronghold nearest blue and leaves it bare —
    the C1.5 re-infiltration design scenario (conservation gate opens +
    an under-held target exists). Does the flip-back pipeline actually run?

    Uses the ENGINE capture path (``ControlPoint.capture``), not the bare
    ``_coalition`` swap: a real capture depopulates the red garrison/AAA
    TGOs, and ``_garrison_count`` counts every alive vehicle TGO unit — a
    shortcut flip leaves the old defenders standing and reads as "held".
    """
    if game.turn != CAPTURE_TURN:
        return
    blue_cps = [c for c in game.theater.controlpoints if c.captured.is_blue]
    red_cps = [c for c in game.theater.controlpoints if c.captured.is_red]
    if not blue_cps or not red_cps:
        return
    target = min(
        red_cps,
        key=lambda r: min(r.position.distance_to_point(b.position) for b in blue_cps),
    )
    from game.sim import GameUpdateEvents

    try:
        target.capture(game, GameUpdateEvents(), game.blue.player)
        how = "engine capture"
    except Exception as exc:  # noqa: BLE001 -- fall back to the headless swap
        target._coalition = game.blue
        how = f"swap (capture raised: {exc})"
    _safe(lambda: target.base.armor.clear())
    log.append(f"T{game.turn}: captured {target.name} ({how})")


SCRIPTS = {
    "baseline": None,
    "engage": _engage,
    "throttle_fed": _throttle_fed,
    "throttle_starved": _throttle_starved,
    "capture": _capture,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "campaign", help="campaign yaml stem, e.g. coin_enduring_resolve"
    )
    parser.add_argument("--turns", type=int, default=15)
    parser.add_argument("--script", choices=sorted(SCRIPTS), default="baseline")
    parser.add_argument("--out", default="probe_out")
    args = parser.parse_args()

    yaml_path = os.path.join(CAMP, f"{args.campaign}.yaml")
    if not os.path.exists(yaml_path):
        print(f"no such campaign: {yaml_path}", file=sys.stderr)
        return 1

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    saved_games = os.environ.get("PROBE_SAVED_GAMES", str(out_dir / "_saved_games"))
    Path(saved_games).mkdir(parents=True, exist_ok=True)

    print(f"[probe] generating {args.campaign} ...", flush=True)
    game = _build_game(yaml_path, saved_games)
    intervention = SCRIPTS[args.script]
    log: list[str] = []

    out_path = out_dir / f"{args.campaign}_{args.script}.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(_sample(game)) + "\n")
        for i in range(args.turns):
            if intervention is not None:
                intervention(game, log)
            print(f"[probe] pass_turn -> {game.turn + 1}", flush=True)
            game.pass_turn(no_action=True)
            f.write(json.dumps(_sample(game)) + "\n")
            f.flush()

    print(f"[probe] wrote {out_path}")
    for line in log:
        print(f"[probe] {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
