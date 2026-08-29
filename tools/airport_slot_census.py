"""Slot census per airport, for the pydcs terrain re-export (design note §9).

The re-export rewrites ``dcs/terrain/<map>/airports.py`` in place, so the numbers it
replaces are gone the moment it runs. Take a baseline BEFORE, compare AFTER::

    python tools/airport_slot_census.py --out before.json
    # ... run the stand-list dump + tools/airport_import.py per terrain ...
    python tools/airport_slot_census.py --compare before.json

Reads pydcs rather than parsing the generated source, so it is immune to formatting
churn in ``airports.py`` and reports exactly what the campaign engine will see.

The direction of a change is what matters. DCS's 2026-08-26 patch says slot counts rose
for large aircraft, so an increase is capacity we were not using and needs no
re-authoring. A DECREASE is the only result that can break a mission, because campaign
``size:`` values are fitted to these counts.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

#: Terrains to census. Every one a shipped campaign uses, plus those pydcs exposes.
TERRAINS = (
    "Caucasus",
    "Syria",
    "PersianGulf",
    "Nevada",
    "Normandy",
    "Sinai",
    "MarianaIslands",
    "MarianasWWII",
    "Afghanistan",
    "Falklands",
    "Kola",
    "GermanyCW",
    "Iraq",
    "TheChannel",
)


def _heavy_fit(slots: Any) -> int:
    """Fixed-wing slots a heavy actually fits, by the v2 dimension test.

    Mirrors the test `QBaseMenu2` shows the player, against the same representative
    heavy (the B-1B), so the census and the base menu can never disagree.
    """
    from dcs.planes import B_1B

    return sum(
        1
        for s in slots
        if getattr(s, "airplanes", False)
        and s.width is not None
        and s.length is not None
        and B_1B.width < s.width
        and B_1B.height < (s.height or 1000)
        and B_1B.length < s.length
    )


def _terrain(name: str) -> Any:
    import dcs.terrain as terrain_module

    cls = getattr(terrain_module, name, None)
    return cls() if cls is not None else None


def census() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in TERRAINS:
        try:
            terrain = _terrain(name)
        except Exception as exc:  # pragma: no cover - terrain not shipped in this pydcs
            out[name] = {"error": str(exc)}
            continue
        if terrain is None:
            continue
        fields: dict[str, Any] = {}
        for airport_name, airport in terrain.airports.items():
            slots = airport.parking_slots
            fields[airport_name] = {
                "slots": len(slots),
                # `large` is the slot_version-1 flag and is False on every airport of
                # every shipped terrain -- v2 maps decide by physical dimensions instead.
                # Counting it as "heavy capacity" reads 0 everywhere and means nothing.
                "large_flag_v1": sum(1 for s in slots if getattr(s, "large", False)),
                "heavy_fit": _heavy_fit(slots),
                "heli": sum(1 for s in slots if getattr(s, "helicopter", False)),
                "shelter": sum(1 for s in slots if getattr(s, "shelter", False)),
                "slot_version": getattr(airport, "slot_version", None),
            }
        out[name] = fields
    return out


def compare(before: dict[str, Any], after: dict[str, Any]) -> int:
    changed = 0
    for terrain in sorted(set(before) | set(after)):
        b, a = before.get(terrain, {}), after.get(terrain, {})
        if not isinstance(b, dict) or not isinstance(a, dict):
            continue
        rows = []
        for field in sorted(set(b) | set(a)):
            bf, af = b.get(field), a.get(field)
            if bf == af:
                continue
            rows.append((field, bf, af))
        if not rows:
            print(f"{terrain}: no change ({len(a)} airfields)")
            continue
        changed += len(rows)
        print(f"\n{terrain}: {len(rows)} airfield(s) changed")
        for field, bf, af in rows:
            if bf is None:
                print(f"  + {field}: new, {af}")
            elif af is None:
                print(f"  - {field}: REMOVED (was {bf})")
            else:
                deltas = [
                    f"{k} {bf.get(k)}->{af.get(k)}"
                    for k in (
                        "slots",
                        "heavy_fit",
                        "heli",
                        "shelter",
                        "slot_version",
                        "large_flag_v1",
                    )
                    if bf.get(k) != af.get(k)
                ]
                drop = af.get("slots", 0) < bf.get("slots", 0)
                print(
                    f"  {'!' if drop else ' '} {field}: {', '.join(deltas)}"
                    + (
                        "   <-- FEWER SLOTS, check campaigns on this field"
                        if drop
                        else ""
                    )
                )
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", help="write a census to this JSON file")
    parser.add_argument(
        "--compare", help="compare the current census against this JSON file"
    )
    args = parser.parse_args()

    current = census()
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(current, handle, indent=1, sort_keys=True)
        total = sum(len(v) for v in current.values() if isinstance(v, dict))
        print(f"wrote {args.out}: {len(current)} terrains, {total} airfields")
        return 0
    if args.compare:
        with open(args.compare, encoding="utf-8") as handle:
            before = json.load(handle)
        changed = compare(before, current)
        print(f"\n{changed} airfield(s) differ.")
        return 0
    for terrain, fields in current.items():
        if isinstance(fields, dict) and fields and "error" not in fields:
            slots = sum(f["slots"] for f in fields.values())
            heavy = sum(f["heavy_fit"] for f in fields.values())
            print(
                f"{terrain:18s} {len(fields):3d} airfields  {slots:5d} slots  "
                f"{heavy:4d} take a heavy"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
