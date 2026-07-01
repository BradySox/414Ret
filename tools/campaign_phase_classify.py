#!/usr/bin/env python3
"""Draft a Tier-0 phase arc for every campaign from its turn-0 laydown.

This is the offline reference implementation of the campaign-phase classifier
(docs/dev/design/414th-campaign-phases-notes.md §3.2), run over a static turn-0
snapshot. It reads each campaign's laydown via the --lite path of
campaign_phase_laydown.py (no fork pydcs needed), applies the phase-boundary
rules, and emits the *opening* phase + the projected arc + a "why" string.

A turn-0 snapshot can only classify the opening phase and project the intended
sequence; it does not simulate turn-by-turn advancement. That is exactly what a
"draft phase plan" is. Re-derive with the engine for authoritative IADS/air/front
numbers.

Usage:
    python tools/campaign_phase_classify.py            # all campaigns, markdown table
    python tools/campaign_phase_classify.py --json     # JSON
    python tools/campaign_phase_classify.py black_sea slava_ukraini
"""

from __future__ import annotations

import argparse
import glob
import json
import os

from campaign_phase_laydown import CAMP, _yaml_meta, extract_lite

# --- thresholds (mirror design §3.2; tune here) -----------------------------
ROLLBACK_SAM_FLOOR = (
    3  # < this many enemy long+medium SAM launchers => no IADS rollback
)
AIR_THREAT_FLOOR = (
    8  # enemy fighter airframes that still justify an air-superiority phase
)
PEER_MIN = 12  # both sides need this many fighters before we call it a peer air fight
LONG_CAMPAIGN_NEUTRAL = (
    12  # neutral airfields above which the war is "long" (adds Consolidation)
)


def _era(meta: dict) -> str:
    date = meta.get("recommended_start_date", "") or ""
    year = None
    for tok in date.replace("-", " ").split():
        if tok.isdigit() and len(tok) == 4:
            year = int(tok)
            break
    blob = (
        meta.get("recommended_player_faction", "")
        + " "
        + meta.get("recommended_enemy_faction", "")
    ).lower()
    if year and year < 1946:
        return "wwii"
    if any(k in blob for k in ("vietnam", "nva")):
        return "vietnam"
    if year and year < 1991:
        return "cold_war"
    return "modern"


def classify(meta: dict, lay: dict) -> dict:
    red = lay["sides"]["red"]
    # Engine laydowns band by TGO site (what the DEAD planner actually targets)
    # and their unit counts include radars/support, so the floor gate runs on
    # sites there; lite laydowns only have the keyword-matched unit count.
    if "sam_sites" in red:
        sam = red["sam_sites"]["long"] + red["sam_sites"]["medium"]
    else:
        sam = red["sam_long_medium"]
    oob = lay.get("air_oob", {})
    red_air = oob.get("RED", {})
    blue_air = oob.get("BLUE", {})
    enemy_fighters = red_air.get("fighter", 0)
    friendly_fighters = blue_air.get("fighter", 0)
    air_known = bool(oob) and (
        sum(
            v.get("fighter", 0) + v.get("sead", 0) + v.get("strike", 0)
            for v in oob.values()
        )
        > 0
    )
    peer = (
        air_known
        and enemy_fighters >= PEER_MIN
        and friendly_fighters >= PEER_MIN
        and 0.7 <= (enemy_fighters / max(friendly_fighters, 1)) <= 1.4
    )
    # Engine laydowns assign every CP to a side, so the capturable-pool proxy
    # rides the raw .miz neutral-airfield count they carry as neutral_pool.
    neutral = lay.get("neutral_pool", lay["airfields"].get("NEUTRAL", 0))
    era = _era(meta)

    reasons = [f"enemy L+M SAM={sam}"]
    if air_known:
        reasons.append(f"enemy fighters={enemy_fighters}")
    else:
        reasons.append("enemy air unknown (faction auto-assign)")

    # opening phase
    if sam >= ROLLBACK_SAM_FLOOR:
        opening = "Rollback (IADS)"
        reasons.append("SAM belt present -> DEAD/SEAD rollback")
    elif air_known and enemy_fighters >= AIR_THREAT_FLOOR:
        opening = "Air Superiority (fighter)"
        reasons.append("no SAM belt but real enemy air -> CAP/OCA/sweep, not SEAD")
    elif not air_known:
        opening = "Air Superiority (fighter)"
        reasons.append("SAM < floor + air unknown -> assume faction air, win it first")
    else:
        opening = "Interdiction"
        reasons.append("SAM < floor + weak enemy air -> skip air-superiority phase")

    # projected arc
    if opening.startswith("Interdiction"):
        arc = ["Interdiction", "Offensive"]
    else:
        arc = [opening.split(" (")[0], "Interdiction", "Offensive"]
    if neutral >= LONG_CAMPAIGN_NEUTRAL:
        arc.append("Consolidation")
        reasons.append(f"{neutral} neutral fields -> long war")

    if peer:
        reasons.append(
            "peer air (symmetric fighters) -> 'air won' gates on air+IADS both"
        )

    # Vietnam / era doctrine labels (display only)
    labels = {
        "vietnam": {
            "Rollback": "Iron Hand",
            "Interdiction": "Steel Tiger",
        },
        "wwii": {"Interdiction": "Interdiction", "Offensive": "Breakout"},
    }.get(era, {})
    display = [labels.get(p.split(" (")[0], p) for p in arc]

    return {
        "era": era,
        "opening": opening,
        "arc": arc,
        "arc_display": display,
        "peer_air": peer,
        "why": "; ".join(reasons),
    }


def _resolve(names: list[str]) -> list[str]:
    if not names:
        return sorted(
            os.path.basename(p) for p in glob.glob(os.path.join(CAMP, "*.yaml"))
        )
    return [n if n.endswith(".yaml") else n + ".yaml" for n in names]


def _row(meta: dict, lay: dict, fallback_name: str) -> dict:
    verdict = classify(meta, lay)
    red = lay["sides"]["red"]
    if "sam_sites" in red:
        sam_lm: int | str = (
            f"{red['sam_sites']['long'] + red['sam_sites']['medium']} "
            f"({red['sam_long_medium']}u)"
        )
    else:
        sam_lm = red["sam_long_medium"]
    return {
        "campaign": meta.get("name", fallback_name),
        "theater": meta.get("theater", "?"),
        "date": (
            meta.get("recommended_start_date", "").split()[0]
            if meta.get("recommended_start_date")
            else "?"
        ),
        "enemy_sam_lm": sam_lm,
        "enemy_fighters": lay.get("air_oob", {}).get("RED", {}).get("fighter", 0),
        **verdict,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--json", action="store_true", help="emit JSON instead of a markdown table"
    )
    ap.add_argument(
        "--laydown",
        help="classify from a saved campaign_phase_laydown.py JSON (e.g. an "
        "--engine --all dump) instead of extracting --lite laydowns here",
    )
    ap.add_argument("names", nargs="*", help="campaign yaml stems (default: all)")
    args = ap.parse_args()

    rows = []
    if args.laydown:
        with open(args.laydown, encoding="utf-8") as f:
            dump = json.load(f)
        for stem, entry in sorted(dump.items()):
            if args.names and stem not in [n.removesuffix(".yaml") for n in args.names]:
                continue
            lay = entry.get("laydown", {})
            if "error" in lay:
                rows.append({"campaign": stem, "error": lay["error"]})
                continue
            try:
                rows.append(_row(entry.get("meta", {}), lay, stem))
            except Exception as exc:  # noqa: BLE001
                rows.append({"campaign": stem, "error": f"{type(exc).__name__}: {exc}"})
    else:
        for n in _resolve(args.names):
            y = os.path.join(CAMP, n)
            try:
                meta = _yaml_meta(y)
                lay = extract_lite(os.path.join(CAMP, meta.get("miz", "")), y)
                rows.append(_row(meta, lay, n[:-5]))
            except Exception as exc:  # noqa: BLE001
                rows.append(
                    {"campaign": n[:-5], "error": f"{type(exc).__name__}: {exc}"}
                )

    if args.json:
        print(json.dumps(rows, indent=2, default=str))
        return

    print(
        "| Campaign | Theater | Date | Era | Enemy SAM | Enemy Ftr | Opening | Projected arc | Why |"
    )
    print("|---|---|---|---|--:|--:|---|---|---|")
    for r in sorted(
        rows,
        key=lambda x: (x.get("era", "z"), x.get("theater", ""), x.get("campaign", "")),
    ):
        if "error" in r:
            print(f"| {r['campaign']} | — | — | — | — | — | ERROR | — | {r['error']} |")
            continue
        arc = " -> ".join(r["arc_display"])
        print(
            f"| {r['campaign']} | {r['theater']} | {r['date']} | {r['era']} | "
            f"{r['enemy_sam_lm']} | {r['enemy_fighters']} | {r['opening']} | {arc} | {r['why']} |"
        )


if __name__ == "__main__":
    main()
