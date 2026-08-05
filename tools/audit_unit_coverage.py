"""Report which installed DCS units the fork cannot actually use.

A DCS vehicle or ship is usable by Retribution only if it has a definition yaml at
``resources/units/<ground_units|ships>/<dcs id>.yaml``. That yaml is what makes it a
``GroundUnitType`` / ``ShipUnitType``, which is what puts it in
``Faction.accessible_units``, which is what ``Faction.has_access_to_dcs_type`` gates
every layout slot and faction roster on. Without one the unit is installed, known to
the engine, and completely unreachable -- and nothing warns you.

That is not hypothetical: it is how every DCS refueller stayed unusable for the whole
life of the fork (see features doc §85). ``resources/units`` grows by hand, DCS and the
mod packs grow on their own schedule, and the gap between them is invisible.

This is a *coverage* report, not a correctness one. For checking that a registered
unit's VALUES still match the live install, use ``tools/verify_mod_export.py`` against
a fresh ``pydcs_export.lua`` dump.

Scope note: the list is pydcs's ``vehicle_map`` / ``ship_map`` **with the fork's
``pydcs_extensions`` loaded**, so every mod pack the fork registers is included. A mod
that is installed but has no ``pydcs_extensions`` entry is invisible here -- that is a
different gap, and the fix is an extension module, not a unit yaml.

Usage::

    python tools/audit_unit_coverage.py              # summary + unregistered, by role
    python tools/audit_unit_coverage.py --csv out.csv  # full matrix
    python tools/audit_unit_coverage.py --role "Command & control"
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

GROUND_DIR = Path("resources/units/ground_units")
SHIP_DIR = Path("resources/units/ships")

# Role buckets, matched against the DCS display name first, then the id. Purely a
# reporting aid -- these are not UnitClasses and nothing downstream reads them.
ROLE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("Refueller / fuel", r"refuel|tanker|fuel|atz|atmz|tz-22"),
    ("Power / generator", r"power station|generator|\bgpu\b|apa-|epp"),
    (
        "Command & control",
        r"\bcp\b|command|\bc2\b|control|hq |headquart|kung|skp|pbu|gci",
    ),
    (
        "EW / jamming / comms",
        r"jam|\bew\b|elint|sigint|comms|communication|radio|spoof|decoy",
    ),
    ("Radar / sensor", r"radar|\bsr\b|\btr\b|search|track|acquisition|\bstr\b"),
    (
        "Support truck / cargo",
        r"truck|cargo|kamaz|ural|gaz|zil|kraz|maz|m35|hemtt|mtvr|bedford|blitz|cckw"
        r"|tractor|forklift|crane|lift",
    ),
    (
        "Engineering / recovery",
        r"engineer|bridge|recovery|repair|bulldozer|excavat|dozer|sapper",
    ),
    ("Medical", r"ambulance|medic|hospital"),
    (
        "Civilian / scenery",
        r"civil|bus|\bcar\b|van\b|trolley|locomotive|coach|wagon|tram|bicycle|passenger",
    ),
    ("Air defence", r"sam |manpad|aaa|flak|zsu|shilka|stinger|igla|launcher|\bln\b"),
    (
        "Armor / combat",
        r"\btank\b|mbt|apc|ifv|btr|bmp|\bt-\d|leopard|abrams|challenger|artillery"
        r"|mlrs|howitz|mortar",
    ),
    ("Infantry", r"infantry|soldier|rifle|paratroop|sniper|rpg"),
)
UNCLASSIFIED = "Other / unclassified"


def bucket(name: str, uid: str) -> str:
    hay = f"{name} {uid}".lower()
    for label, pattern in ROLE_PATTERNS:
        if re.search(pattern, hay):
            return label
    return UNCLASSIFIED


def _audit(mapping: dict[str, Any], directory: Path, kind: str) -> list[dict[str, Any]]:
    rows = []
    for uid, cls in sorted(mapping.items()):
        display = getattr(cls, "name", "") or uid
        rows.append(
            {
                "kind": kind,
                "id": uid,
                "name": display,
                "pydcs_class": cls.__qualname__.split(".")[0],
                "role": bucket(display, uid),
                "registered": (directory / f"{uid}.yaml").is_file(),
            }
        )
    return rows


def collect() -> list[dict[str, Any]]:
    """Load the engine's view of the world and diff it against resources/units."""
    from game import persistency

    # Layout/preset loading reads the DCS saved-game folder; point it at a temp dir
    # so this runs standalone. Importing `game` is also what pulls in the fork's
    # pydcs_extensions, which is why mod units appear below.
    persistency.setup(tempfile.mkdtemp(), False, 0)

    from dcs.ships import ship_map
    from dcs.vehicles import vehicle_map

    return _audit(vehicle_map, GROUND_DIR, "vehicle") + _audit(
        ship_map, SHIP_DIR, "ship"
    )


def _print_summary(rows: Iterable[dict[str, Any]]) -> None:
    agg: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        entry = agg[row["role"]]
        entry[0] += 1
        if not row["registered"]:
            entry[1] += 1
    print(f"{'ROLE':26} {'TOTAL':>6} {'MISSING':>8} {'% USABLE':>9}")
    for role, (total, missing) in sorted(agg.items(), key=lambda kv: -kv[1][1]):
        print(
            f"{role:26} {total:6} {missing:8} {100 * (total - missing) / total:8.0f}%"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, help="write the full matrix to this path")
    parser.add_argument("--role", help="only list unregistered units in this role")
    args = parser.parse_args()

    rows = collect()
    missing = [r for r in rows if not r["registered"]]

    print(f"pydcs knows {len(rows)} placeable units; {len(missing)} have NO yaml\n")
    _print_summary(rows)

    by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in missing:
        by_role[row["role"]].append(row)

    for label in [name for name, _ in ROLE_PATTERNS] + [UNCLASSIFIED]:
        if args.role and label != args.role:
            continue
        items = by_role.get(label)
        if not items:
            continue
        print(f"\n### {label} — {len(items)} unregistered")
        for row in items:
            print(f"    {row['id']:34} {row['name'][:46]:48} [{row['pydcs_class']}]")

    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nfull matrix -> {args.csv}")


if __name__ == "__main__":
    main()
