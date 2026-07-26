"""Validate a campaign's authored scenery strike targets before DCS/Retribution sees them.

Scenery strike targets (``BuildingGroundObject``s such as Desert Storm's Saad 16 complex
or Baba Gurgur oil plant) are authored **in the Mission Editor**, not in the campaign
yaml: a **blue circle** zone carrying the objective's category, containing one or more
**white** zones each bound to a real destructible map object.

``SceneryGroup.from_trigger_zones`` (``game/scenery_group.py``) is strict about that
pairing, and its failure mode is nasty: a blue zone with **no white zones inside it**
raises ``SceneryGroupError`` and the **campaign fails to load**. The same is true of a
blue zone whose category is missing or misspelled. Those are easy mistakes to make while
hand-authoring in the ME, and today nothing catches them until New Game blows up.

This script reproduces the loader's pairing rules against a ``.miz`` and reports:

* **ERRORS** — the campaign will fail to load:
    - a blue zone with no properties (no category defined)
    - a blue zone whose category is not in ``NAME_BY_CATEGORY``
    - a blue zone containing zero white zones
* **WARNINGS** — the campaign loads, but the authoring is probably not what was meant:
    - a white zone claimed by no blue zone (authored, then orphaned)
    - a white zone with no ``OBJECT ID`` property (not bound to a real map object, so
      damage to it is never tracked)

Exit status is non-zero when errors are found, so this is usable as a pre-push gate.

Usage::

    python tools/check_scenery_targets.py                        # every campaign miz
    python tools/check_scenery_targets.py resources/campaigns/iraq_desert_storm.miz
    python tools/check_scenery_targets.py --quiet                # errors/warnings only

Deliberately standalone: it imports **pydcs only**, and reads the category list straight
out of ``game/theater/theatergroundobject.py`` with ``ast`` rather than importing the
game package (which drags in shapely, faker and the rest of the runtime stack). The
category list therefore stays single-source-of-truth without the import cost.
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from dcs.mission import Mission
from dcs.triggers import TriggerZone, TriggerZoneCircular, TriggerZoneQuadPoint

REPO_ROOT = Path(__file__).resolve().parent.parent
CAMPAIGN_DIR = REPO_ROOT / "resources" / "campaigns"
#: Source of truth for the valid objective categories.
CATEGORY_SOURCE = REPO_ROOT / "game" / "theater" / "theatergroundobject.py"


def valid_categories() -> set[str]:
    """The keys of ``NAME_BY_CATEGORY``, read without importing the game package."""
    tree = ast.parse(CATEGORY_SOURCE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "NAME_BY_CATEGORY":
                value = node.value
                if not isinstance(value, ast.Dict):
                    break
                return {
                    key.value
                    for key in value.keys
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                }
    raise RuntimeError(f"NAME_BY_CATEGORY not found in {CATEGORY_SOURCE}")


# -- the loader's own predicates, mirrored ------------------------------------------
# Kept byte-for-byte equivalent to SceneryGroup.is_blue/is_white and _point_in_zone so
# this script agrees with the loader rather than approximating it.


def is_blue(zone: TriggerZone) -> bool:
    return zone.color[1] == 0 and zone.color[2] == 0 and zone.color[3] == 1


def is_white(zone: TriggerZone) -> bool:
    return zone.color[1] == 1 and zone.color[2] == 1 and zone.color[3] == 1


def point_in_zone(zone_def: TriggerZone, pos) -> bool:
    if isinstance(zone_def, TriggerZoneCircular):
        return zone_def.position.distance_to_point(pos) < zone_def.radius
    if isinstance(zone_def, TriggerZoneQuadPoint):
        # Mirror of the loader's Polygon(...).point_in_poly, without pulling in shapely:
        # a standard ray-casting test over the quad's vertices.
        verts = zone_def.verticies
        inside = False
        count = len(verts)
        for i in range(count):
            a, b = verts[i], verts[(i + 1) % count]
            if (a.y > pos.y) != (b.y > pos.y):
                x_at = (b.x - a.x) * (pos.y - a.y) / (b.y - a.y) + a.x
                if pos.x < x_at:
                    inside = not inside
        return inside
    return False


def object_id_of(zone: TriggerZone) -> str | None:
    for prop in (zone.properties or {}).values():
        if prop.get("key") == "OBJECT ID":
            value = (prop.get("value") or "").strip()
            return value or None
    return None


def category_of(zone: TriggerZone) -> str | None:
    """The loader reads ``properties[1]["value"]`` — the first authored property."""
    props = zone.properties or {}
    if not props:
        return None
    first = props.get(1)
    if first is None:
        return None
    value = (first.get("value") or "").strip()
    return value.lower() or None


@dataclass
class Report:
    miz: Path
    objectives: list[tuple[str, str, int]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def check(miz: Path, categories: set[str]) -> Report:
    report = Report(miz=miz)
    mission = Mission()
    mission.load_file(str(miz))

    zones: Sequence[TriggerZone] = mission.triggers.zones()
    blue = [z for z in zones if is_blue(z)]
    white = [z for z in zones if is_white(z)]
    unclaimed = list(white)

    for zone_def in blue:
        category = category_of(zone_def)
        if category is None:
            report.errors.append(
                f"blue zone {zone_def.name!r} has no category property "
                f"(loader raises SceneryGroupError: 'Undefined SceneryGroup category')"
            )
            continue
        if category not in categories:
            report.errors.append(
                f"blue zone {zone_def.name!r} has category {category!r}, which is not a "
                f"valid objective category (loader raises SceneryGroupError)"
            )
            continue

        claimed = [z for z in unclaimed if point_in_zone(zone_def, z.position)]
        for zone in claimed:
            unclaimed.remove(zone)

        if not claimed:
            report.errors.append(
                f"blue zone {zone_def.name!r} ({category}) contains no white zones — "
                f"the campaign will FAIL TO LOAD "
                f"(loader raises SceneryGroupError: 'No white triggerzones found')"
            )
            continue

        report.objectives.append((zone_def.name, category, len(claimed)))
        for zone in claimed:
            if object_id_of(zone) is None:
                report.warnings.append(
                    f"white zone {zone.name!r} in {zone_def.name!r} has no OBJECT ID — "
                    f"it is not bound to a map object, so damage is never tracked"
                )

    for zone in unclaimed:
        # A white zone bound to a map object is scenery authoring, so an unclaimed one
        # is a real mistake. A white zone with no OBJECT ID is some other use of a white
        # zone entirely -- CTLD pickup zones are the common case -- and is none of our
        # business.
        if object_id_of(zone) is None:
            continue
        report.warnings.append(
            f"white zone {zone.name!r} is bound to a map object but sits inside no blue "
            f"zone — orphaned authoring (the object is never a strike target)"
        )

    return report


def campaign_mizes() -> Iterator[Path]:
    yield from sorted(CAMPAIGN_DIR.glob("*.miz"))


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "miz",
        nargs="*",
        type=Path,
        help="campaign .miz files to check (default: every campaign in resources/campaigns)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="only print campaigns that have errors or warnings",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    categories = valid_categories()
    targets = list(args.miz) or list(campaign_mizes())

    total_errors = 0
    total_warnings = 0
    total_objectives = 0

    for miz in targets:
        try:
            report = check(miz, categories)
        except Exception as exc:  # a miz we cannot parse is worth reporting, not fatal
            print(f"{miz.name}: SKIPPED ({type(exc).__name__}: {exc})")
            continue

        total_errors += len(report.errors)
        total_warnings += len(report.warnings)
        total_objectives += len(report.objectives)

        interesting = report.errors or report.warnings
        if args.quiet and not interesting:
            continue
        if not report.objectives and not interesting:
            continue

        print(f"\n{miz.name} — {len(report.objectives)} scenery objective(s)")
        for name, category, count in report.objectives:
            print(f"  ok    {name}  [{category}]  {count} object(s)")
        for message in report.errors:
            print(f"  ERROR {message}")
        for message in report.warnings:
            print(f"  warn  {message}")

    print(
        f"\n{len(targets)} campaign(s) checked · {total_objectives} objective(s) · "
        f"{total_errors} error(s) · {total_warnings} warning(s)"
    )
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
