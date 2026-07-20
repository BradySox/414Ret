"""Diff a real pydcs export against the ``pydcs_extensions`` registrations.

**Why (2026-07-20, the upstream #881/#886 review exchange):** Druss99's bar for mod
support is the wiki's export process -- DCS itself loads the mods and dumps its live
unit database via `pydcs_export.lua
<https://github.com/dcs-retribution/pydcs/blob/retribution/tools/pydcs_export.lua>`_,
and the generated ``ships.py`` / ``vehicles.py`` / ``planes.py`` classes are the
ground truth a ``pydcs_extensions`` entry should match. The export can only run on a
machine with DCS + the mods installed, so this tool is the other half: point it at
the export output folder and it compares every registered unit field-for-field,
emitting a paste-ready verdict for the PR thread.

The desktop runbook (one DCS launch covers every installed mod):

1. Download ``pydcs_export.lua`` (link above) somewhere convenient.
2. Edit its ``export_path`` line to an existing folder (e.g. ``D:\\dcs-export\\``).
3. Append one line at the end of ``DCS World\\MissionEditor\\modules\\me_mission.lua``:
   ``base.dofile("C:\\path\\to\\pydcs_export.lua")``
4. Launch DCS with the mods enabled. It sits at ~10% loading while writing (normal;
   only worry past ~5 min). The ``*.py`` files land in the export folder.
5. REMOVE the ``me_mission.lua`` line afterward (it re-runs on every editor load, and
   DCS updates/repairs will fight over the edit).
6. ``python tools\\verify_mod_export.py D:\\dcs-export --extension vietnamwarvessels
   --markdown`` (and again with ``--extension iranmilitaryassetspack``).

Comparison semantics: units join on their literal ``id`` (the DCS type string --
class names differ between the exporter and the extensions). Fields declared by BOTH
sides must match; fields only one side declares are listed informationally (the
export emits many attributes an extension legitimately omits, and an extension field
the export lacks falls back to the ``UnitType`` default at runtime either way).
Pylon/task tables are nested structures the exporter alone owns and are out of scope
here -- for pylon-carrying aircraft the export IS the authority; eyeball those
directly. Pure stdlib (``ast``) on both sides, so it runs without pydcs installed and
never imports mod code.
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

EXPORT_FILENAMES = ("ships.py", "vehicles.py", "planes.py", "helicopters.py")

REPO_ROOT = Path(__file__).resolve().parent.parent
EXTENSIONS_ROOT = REPO_ROOT / "pydcs_extensions"


@dataclass
class UnitEntry:
    unit_id: str
    class_name: str
    source: Path
    fields: dict[str, Any] = field(default_factory=dict)


def literal_fields(class_node: ast.ClassDef) -> dict[str, Any]:
    """Top-level ``name = <literal>`` assignments of a class body.

    Nested classes (pylon tables) and non-constant values (task lists, pylons sets)
    are skipped -- they are exporter-only structures with no extension counterpart.
    """
    fields: dict[str, Any] = {}
    for node in class_node.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        if isinstance(node.value, ast.Constant):
            fields[target.id] = node.value.value
    return fields


def collect_units(path: Path) -> list[UnitEntry]:
    """Every module-level class in ``path`` carrying a literal string ``id``."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        print(f"WARNING: cannot parse {path}: {exc}", file=sys.stderr)
        return []
    units = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        fields = literal_fields(node)
        unit_id = fields.get("id")
        if isinstance(unit_id, str):
            units.append(UnitEntry(unit_id, node.name, path, fields))
    return units


def export_files_from(paths: list[Path]) -> list[Path]:
    files = []
    for path in paths:
        if path.is_dir():
            files.extend(
                path / name for name in EXPORT_FILENAMES if (path / name).is_file()
            )
        elif path.is_file():
            files.append(path)
        else:
            sys.exit(f"error: export path does not exist: {path}")
    if not files:
        sys.exit(
            "error: no export files found -- expected one of "
            f"{', '.join(EXPORT_FILENAMES)} (did the pydcs_export.lua run finish?)"
        )
    return files


def extension_files(only: list[str]) -> list[Path]:
    if only:
        roots = []
        for name in only:
            root = EXTENSIONS_ROOT / name
            if not root.is_dir():
                sys.exit(f"error: no such extension package: {root}")
            roots.append(root)
    else:
        roots = [EXTENSIONS_ROOT]
    return sorted(f for root in roots for f in root.rglob("*.py"))


@dataclass
class Verdict:
    entry: UnitEntry
    export: Optional[UnitEntry]
    mismatches: list[tuple[str, Any, Any]]
    extension_only: list[str]
    export_only: list[str]

    @property
    def ok(self) -> bool:
        return self.export is not None and not self.mismatches


def compare(entry: UnitEntry, export: Optional[UnitEntry]) -> Verdict:
    if export is None:
        return Verdict(entry, None, [], [], [])
    mismatches = []
    shared = sorted(entry.fields.keys() & export.fields.keys())
    for name in shared:
        if entry.fields[name] != export.fields[name]:
            mismatches.append((name, entry.fields[name], export.fields[name]))
    return Verdict(
        entry,
        export,
        mismatches,
        sorted(entry.fields.keys() - export.fields.keys()),
        sorted(export.fields.keys() - entry.fields.keys()),
    )


def render(verdicts: list[Verdict], markdown: bool, verbose: bool) -> str:
    lines = []
    ok = [v for v in verdicts if v.ok]
    missing = [v for v in verdicts if v.export is None]
    bad = [v for v in verdicts if v.export is not None and v.mismatches]
    if markdown:
        lines.append("### pydcs export verification")
        lines.append("")
    for v in bad:
        detail = "; ".join(
            f"`{name}`: extension `{ours!r}` != export `{theirs!r}`"
            for name, ours, theirs in v.mismatches
        )
        lines.append(f"- MISMATCH `{v.entry.unit_id}` -- {detail}")
    for v in missing:
        lines.append(
            f"- NOT IN EXPORT `{v.entry.unit_id}` ({v.entry.source.name}) -- "
            "mod not enabled for the export run?"
        )
    for v in ok:
        assert v.export is not None
        shared = len(v.entry.fields.keys() & v.export.fields.keys())
        line = f"- OK `{v.entry.unit_id}` -- {shared} shared fields match"
        if verbose and (v.extension_only or v.export_only):
            extras = []
            if v.extension_only:
                extras.append(f"extension-only: {', '.join(v.extension_only)}")
            if v.export_only:
                extras.append(f"export-only: {', '.join(v.export_only)}")
            line += f" ({'; '.join(extras)})"
        lines.append(line)
    lines.append("")
    lines.append(
        f"{len(ok)} match / {len(bad)} mismatch / {len(missing)} not in export "
        f"(of {len(verdicts)} registered units checked)"
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare pydcs_export.lua output against pydcs_extensions "
            "registrations. See the module docstring for the export runbook."
        )
    )
    parser.add_argument(
        "export_paths",
        nargs="+",
        type=Path,
        help="export folder (containing ships.py etc.) or individual export files",
    )
    parser.add_argument(
        "--extension",
        action="append",
        default=[],
        metavar="NAME",
        help="restrict to pydcs_extensions/<NAME> (repeatable); default: all",
    )
    parser.add_argument(
        "--units",
        default="",
        metavar="ID,ID",
        help="restrict to these comma-separated unit ids",
    )
    parser.add_argument(
        "--markdown", action="store_true", help="emit a PR-pasteable block"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="also list one-sided fields on matching units",
    )
    args = parser.parse_args()

    exported: dict[str, UnitEntry] = {}
    for path in export_files_from(args.export_paths):
        for unit in collect_units(path):
            exported[unit.unit_id] = unit

    wanted = {u.strip() for u in args.units.split(",") if u.strip()}
    verdicts = []
    seen: set[str] = set()
    for path in extension_files(args.extension):
        for unit in collect_units(path):
            if wanted and unit.unit_id not in wanted:
                continue
            if unit.unit_id in seen:
                continue
            seen.add(unit.unit_id)
            # An unfiltered sweep only reports units the export actually saw --
            # most packs will not be installed for any given run. A filtered run
            # is a claim that the mod WAS loaded, so absences are reportable.
            export = exported.get(unit.unit_id)
            if export is None and not (args.extension or wanted):
                continue
            verdicts.append(compare(unit, export))

    if not verdicts:
        sys.exit("error: no registered units matched the requested scope")
    print(render(verdicts, args.markdown, args.verbose))
    return 0 if all(v.ok for v in verdicts) else 1


if __name__ == "__main__":
    sys.exit(main())
