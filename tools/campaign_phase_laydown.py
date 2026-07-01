#!/usr/bin/env python3
"""Dump each campaign's turn-0 laydown for campaign-phase inference tuning.

Supports the campaign-phases design (docs/dev/design/414th-campaign-phases-notes.md):
the Tier-0 phase classifier reads live theater state, and its thresholds have to be
validated against real campaign laydowns. This tool produces those laydowns as JSON.

Two modes:

  --engine  (high fidelity, needs the real Retribution venv incl. the pydcs fork)
            Drives the actual GameGenerator -> begin_turn_0 pipeline and reads the
            true control-point / IADS-role / front-line / squadron model.

  --lite    (default; runs anywhere PyPI pydcs is importable, no fork units needed)
            Parses the .miz `mission` + `warehouses` Lua tables directly via
            dcs.lua, without instantiating unit objects. Lower fidelity: ownership
            == the raw DCS airfield coalition, SAM tiers come from a hand-curated
            vanilla-DCS type table, and "front" is inferred from ground centroids.

Usage:
    python tools/campaign_phase_laydown.py black_sea slava_ukraini        # lite
    python tools/campaign_phase_laydown.py --engine khe_sanh_niagara      # full
    python tools/campaign_phase_laydown.py --all                          # every campaign

Run from the repo root. Output is JSON on stdout.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import zipfile

import yaml

CAMP = "resources/campaigns"

# --- air order-of-battle task buckets (for the YAML squadrons block) ---------
_FIGHTER = {"BARCAP", "CAP", "TARCAP", "Fighter sweep", "Escort", "Interception"}
_SEAD = {"SEAD", "DEAD", "SEAD Escort"}
_STRIKE = {
    "Strike",
    "CAS",
    "BAI",
    "Anti-ship",
    "OCA/Aircraft",
    "OCA/Runway",
    "Armed Recon",
    "Anti-ship Strike",
}

# --- vanilla-DCS air-defence tiering (ordered substring match) --------------
# Only used by --lite. The engine mode reads real IadsRole / group tasks instead.
_EWR = ["EWR", "1L13", "55G6", "1L119", "Dog Ear"]
_LONG = [
    "S-300",
    "S-400",
    "Patriot",
    "SA-5",
    "S-200",
    "HQ-9",
    "SAMP",
    "SA-10",
    "SA-12",
    "SA-20",
    "SA-23",
    "KS19",
]
_MEDIUM = [
    "Hawk",
    "Kub",
    "Buk",
    "SA-6",
    "SA-11",
    "NASAMS",
    "SA-2",
    "S-75",
    "SNR",
    "S-125",
    "SA-3",
    "Rapier",
]
_SHORAD = [
    "Strela",
    "Osa",
    "9A33",
    "Tor",
    "9A331",
    "Tunguska",
    "2S6",
    "Gepard",
    "Shilka",
    "ZSU",
    "ZU-23",
    "Igla",
    "Avenger",
    "Chaparral",
    "Linebacker",
    "Roland",
    "9K33",
    "Stinger",
    "Blowpipe",
    "Vulcan",
]


def _tier(type_id: str) -> str | None:
    low = type_id.lower()
    for kw in _EWR:
        if kw.lower() in low:
            return "ewr"
    for kw in _LONG:
        if kw.lower() in low:
            return "long"
    for kw in _MEDIUM:
        if kw.lower() in low:
            return "medium"
    for kw in _SHORAD:
        if kw.lower() in low:
            return "shorad"
    return None


def _centroid(groups: list[dict]) -> tuple[float, float] | None:
    xs = [g.get("x") for g in groups if isinstance(g.get("x"), (int, float))]
    ys = [g.get("y") for g in groups if isinstance(g.get("y"), (int, float))]
    if not xs:
        return None
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _yaml_meta(yaml_path: str) -> dict:
    meta: dict = {}
    keys = (
        "name",
        "theater",
        "recommended_start_date",
        "recommended_player_faction",
        "recommended_enemy_faction",
        "miz",
    )
    with open(yaml_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            for key in keys:
                if line.startswith(key + ":"):
                    meta[key] = line.split(":", 1)[1].strip().strip('"')
    return meta


def _air_oob(yaml_path: str, ownership: dict) -> dict:
    """Enemy/friendly air order of battle from the YAML `squadrons:` block.

    Keyed by control-point id, which for airfields == the DCS airbase id, so we
    attribute each squadron to a side via `ownership` (airbase id -> coalition).
    Named CPs (e.g. "Blue CV" carriers) are attributed by their Blue/Red label.
    Campaigns that omit the block (faction auto-assignment) return zeros — a
    known --lite blind spot the --engine mode closes.
    """
    try:
        data = yaml.safe_load(open(yaml_path, encoding="utf-8", errors="replace"))
    except Exception:  # noqa: BLE001
        return {}
    oob: dict = {}
    for cid, squadrons in (data.get("squadrons", {}) or {}).items():
        try:
            side = ownership.get(int(cid), "NEUTRAL") or "NEUTRAL"
        except (ValueError, TypeError):
            label = str(cid).lower()
            side = "BLUE" if "blue" in label else "RED" if "red" in label else "NEUTRAL"
        bucket = oob.setdefault(
            side, {"fighter": 0, "sead": 0, "strike": 0, "squadrons": 0}
        )
        for entry in squadrons or []:
            bucket["squadrons"] += 1
            task = (entry.get("primary") or "").strip()
            size = entry.get("size", 4)
            if task in _FIGHTER:
                bucket["fighter"] += size
            elif task in _SEAD:
                bucket["sead"] += size
            elif task in _STRIKE:
                bucket["strike"] += size
    return oob


def extract_lite(miz_path: str, yaml_path: str | None = None) -> dict:
    from dcs.lua import loads

    z = zipfile.ZipFile(miz_path)
    mission = loads(z.read("mission").decode("utf-8", "replace"))["mission"]
    warehouses = loads(z.read("warehouses").decode("utf-8", "replace"))["warehouses"]

    own = {"BLUE": 0, "RED": 0, "NEUTRAL": 0}
    ownership: dict = {}
    for _k, v in (warehouses.get("airports", {}) or {}).items():
        c = (v.get("coalition") if isinstance(v, dict) else None) or "NEUTRAL"
        own[c] = own.get(c, 0) + 1
        try:
            ownership[int(_k)] = c
        except (ValueError, TypeError):
            pass

    out: dict = {"mode": "lite", "airfields": own, "sides": {}}
    if yaml_path:
        out["air_oob"] = _air_oob(yaml_path, ownership)
    for side in ("blue", "red"):
        sam = {"long": 0, "medium": 0, "shorad": 0, "ewr": 0}
        veh = ships = statics = 0
        positions: list[dict] = []
        for _ck, cv in (mission["coalition"][side].get("country", {}) or {}).items():
            vg = (
                cv.get("vehicle", {}).get("group", {})
                if isinstance(cv.get("vehicle"), dict)
                else {}
            )
            for _gk, gv in (vg.items() if isinstance(vg, dict) else []):
                veh += 1
                positions.append(gv)
                for _uk, uv in (gv.get("units", {}) or {}).items():
                    t = _tier(uv.get("type", ""))
                    if t:
                        sam[t] += 1
            sg = (
                cv.get("ship", {}).get("group", {})
                if isinstance(cv.get("ship"), dict)
                else {}
            )
            ships += len(sg) if isinstance(sg, dict) else 0
            st = (
                cv.get("static", {}).get("group", {})
                if isinstance(cv.get("static"), dict)
                else {}
            )
            statics += len(st) if isinstance(st, dict) else 0
        out["sides"][side] = {
            "sam": sam,
            "sam_long_medium": sam["long"] + sam["medium"],
            "vehicle_groups": veh,
            "ship_groups": ships,
            "static_groups": statics,
            "ground_centroid": _centroid(positions),
        }
    return out


def extract_engine(yaml_path: str) -> dict:
    """High-fidelity laydown via the real new-game pipeline. Needs the fork pydcs."""
    from datetime import datetime
    from pathlib import Path

    from game import persistency
    from game.campaignloader.campaign import Campaign
    from game.factions import FACTIONS
    from game.settings import Settings
    from game.theater.player import Player
    from game.theater.start_generator import (
        GameGenerator,
        GeneratorSettings,
        ModSettings,
    )
    from game.threatzones import ThreatZones

    persistency.setup(
        str(Path(os.environ.get("PHASE_SAVED_GAMES", "/tmp/rf_saved_games"))), False, 0
    )

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
        squadrons_start_full=False,
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
    game.begin_turn_0(squadrons_start_full=False)

    own = {"BLUE": 0, "RED": 0, "NEUTRAL": 0}
    for cp in game.theater.controlpoints:
        own[cp.captured.name] = own.get(cp.captured.name, 0) + 1

    roles: dict = {"BLUE": {}, "RED": {}}
    for node in game.theater.iads_network.iads_nodes(game):
        side = node.player.name
        role = node.iads_role.name
        roles[side][role] = roles[side].get(role, 0) + 1

    fronts = [
        f"{fl.from_cp.name} <-> {fl.to_cp.name}" for fl in game.theater.conflicts()
    ]

    air: dict = {"BLUE": {}, "RED": {}}
    for pl in (Player.BLUE, Player.RED):
        for sq in game.air_wing_for(pl).iter_squadrons():
            task = sq.primary_task.name if sq.primary_task else "NONE"
            air[pl.name][task] = air[pl.name].get(task, 0) + sq.owned_aircraft

    threat = {}
    for pl in (Player.BLUE, Player.RED):
        try:
            tz = ThreatZones.for_faction(game, pl)
            threat[pl.name] = round(tz.all.area) if tz and tz.all else 0
        except Exception as exc:  # noqa: BLE001
            threat[pl.name] = f"err: {exc}"

    return {
        "mode": "engine",
        "theater": theater.terrain.name,
        "date": str(game.date),
        "airfields": own,
        "iads_roles": roles,
        "front_lines": fronts,
        "air_inventory_by_task": air,
        "threat_zone_area": threat,
    }


def _resolve(names: list[str]) -> list[str]:
    if names == ["--all"] or not names:
        return sorted(
            os.path.basename(p) for p in glob.glob(os.path.join(CAMP, "*.yaml"))
        )
    return [n if n.endswith(".yaml") else n + ".yaml" for n in names]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--engine", action="store_true", help="use the real game pipeline (fork pydcs)"
    )
    ap.add_argument(
        "--all", action="store_true", help="every campaign in resources/campaigns"
    )
    ap.add_argument("names", nargs="*", help="campaign yaml stems (e.g. black_sea)")
    args = ap.parse_args()

    names = _resolve(["--all"] if args.all else args.names)
    results: dict = {}
    for n in names:
        stem = n[:-5]
        y = os.path.join(CAMP, n)
        meta: dict = {}
        try:
            meta = _yaml_meta(y)
            if args.engine:
                lay = extract_engine(y)
            else:
                lay = extract_lite(os.path.join(CAMP, meta.get("miz", "")), y)
        except Exception as exc:  # noqa: BLE001 — keep the batch going
            lay = {"error": f"{type(exc).__name__}: {exc}"}
        results[stem] = {"meta": meta, "laydown": lay}
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
