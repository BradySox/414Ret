"""Restore upstream aircraft task weights (2026-08-09 planner re-convergence, order E).

See the DECIDED block in
docs/dev/design/414th-autoplanner-upstream-divergence-audit.md: default planner
behavior returns to upstream, including the task-weight rebalance
(docs/dev/design/414th-aircraft-task-rebalance-rubric.md). This script reverts the
*magnitudes* while keeping every decided shape:

  - For each resources/units/aircraft/*.yaml that changed since the upstream merge
    base, every task key present in BOTH versions gets upstream's number back.
  - Fork-only keys are untouched (the feature lanes: TARPS, Jamming, Escort Jammer,
    CSAR; plus deliberate additions like the MQ-9's manual-only DEAD).
  - Fork deletions are untouched (Intercept retirement, the F-14s' no-ARM SEAD
    removal, bomber DEAD trims, ...). Nothing is ever re-added.
  - `Intercept:` lines are DELETED wherever one still exists -- the QRA retirement
    missed F-14A-95-GR.yaml and F-100D.yaml.
  - Whole-file keeps: S-3B.yaml (sea-control shape, nothing restored) and
    C-130J-30.yaml (its task set is all fork lanes / decided keeps).
  - Per-task keeps: the EA-18G / EA-6B `SEAD Escort: 400` demotion is wiring of the
    kept Escort Jammer lane (the 2026-07-21 "prefer dedicated jammers as jammers"
    call), so it survives the magnitude restore.

Only the numeric value on a matched task line changes (or the whole line, for
Intercept); byte-exact otherwise, line endings preserved. After writing, every file
is re-parsed with yaml.safe_load and compared against the expected transform of the
original document -- any drift is a hard failure.

Run:  python tools/restore_upstream_task_weights.py          # dry-run report
      python tools/restore_upstream_task_weights.py --write  # apply
"""

from __future__ import annotations

import copy
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

BASELINE = "1a669cac"
AIRCRAFT_DIR = Path("resources/units/aircraft")

# Whole files the decision keeps as-is.
EXCLUDED_FILES = {
    # Sea-control shape: Anti-ship 320 only, nothing else restored.
    "S-3B.yaml",
    # Air Assault / Transport / Jamming / CSAR -- all fork lanes or decided keeps.
    "C-130J-30.yaml",
}

# (file, task) pairs exempt from the restore: magnitudes that are the documented
# wiring of a KEPT feature, not rubric rebalance. Restoring 550/460 here would put
# the dedicated jammers back above the strike fighters (450) for SEAD Escort and
# double-book them out of the kept Escort Jammer lane.
KEEP_TASK_VALUES = {
    ("EA-18G.yaml", "SEAD Escort"),
    ("EA_6B.yaml", "SEAD Escort"),
}

# Retired everywhere: the QRA alert reserve replaced Intercept as the intercept
# model. Any surviving line is deleted outright.
DELETE_TASKS = {"Intercept"}

# Fork-only feature lanes, reported separately from other fork-only additions.
FORK_LANES = {"TARPS", "Jamming", "Escort Jammer", "CSAR"}

TASK_LINE = re.compile(
    r"^(?P<indent>\s+)(?P<name>[A-Za-z][A-Za-z0-9 /&'.()-]*?):"
    r"\s*(?P<value>-?\d+)(?P<suffix>\s*(?:#.*)?)$"
)
TASKS_KEY = re.compile(r"^(?P<indent>\s*)tasks:\s*(#.*)?$")


def parse_tasks(text: str) -> dict[str, int]:
    """Collect task-name -> weight from every `tasks:` mapping in the document."""
    tasks: dict[str, int] = {}
    block_indent: int | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue  # blank/comment lines never enter or exit a block
        key = TASKS_KEY.match(line)
        if key is not None:
            block_indent = len(key.group("indent"))
            continue
        if block_indent is not None:
            indent = len(line) - len(line.lstrip())
            if indent <= block_indent:
                block_indent = None
            else:
                entry = TASK_LINE.match(line)
                if entry is not None:
                    name = entry.group("name")
                    value = int(entry.group("value"))
                    if name in tasks and tasks[name] != value:
                        raise ValueError(f"conflicting duplicate task {name!r}")
                    tasks[name] = value
    return tasks


def upstream_text(path: Path) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{BASELINE}:{path.as_posix()}"],
        capture_output=True,
    )
    if result.returncode != 0:
        return None  # file does not exist at the baseline (fork-added)
    return result.stdout.decode("utf-8")


def changed_files() -> list[Path]:
    out = subprocess.run(
        ["git", "diff", "--name-only", BASELINE, "HEAD", "--", AIRCRAFT_DIR.as_posix()],
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    return [Path(line) for line in out.splitlines() if line.strip()]


def transform_lines(
    raw: bytes, upstream: dict[str, int], name: str
) -> tuple[bytes, list[str], list[str], list[str]]:
    """Apply the restore to one file's bytes.

    Returns (new_bytes, restored, deleted, fork_only) where the lists describe
    each touched or skipped task for the report.
    """
    restored: list[str] = []
    deleted: list[str] = []
    fork_only: list[str] = []
    out: list[bytes] = []
    block_indent: int | None = None
    for line_bytes in raw.splitlines(keepends=True):
        line = line_bytes.decode("utf-8")
        content = line.rstrip("\r\n")
        eol = line[len(content) :]
        stripped = content.strip()
        if not stripped or stripped.startswith("#"):
            out.append(line_bytes)
            continue
        key = TASKS_KEY.match(content)
        if key is not None:
            block_indent = len(key.group("indent"))
            out.append(line_bytes)
            continue
        if block_indent is not None:
            indent = len(content) - len(content.lstrip())
            if indent <= block_indent:
                block_indent = None
            else:
                entry = TASK_LINE.match(content)
                if entry is not None:
                    task = entry.group("name")
                    value = int(entry.group("value"))
                    if task in DELETE_TASKS:
                        deleted.append(f"{task}: {value}")
                        continue  # drop the line entirely
                    if task not in upstream:
                        fork_only.append(f"{task}: {value}")
                    elif (name, task) in KEEP_TASK_VALUES:
                        fork_only.append(f"{task}: {value} (kept, not restored)")
                    elif value != upstream[task]:
                        restored.append(f"{task}: {value} -> {upstream[task]}")
                        new_content = (
                            f"{entry.group('indent')}{task}: {upstream[task]}"
                            f"{entry.group('suffix')}"
                        )
                        out.append((new_content + eol).encode("utf-8"))
                        continue
        out.append(line_bytes)
    return b"".join(out), restored, deleted, fork_only


def expected_document(before: Any, upstream: dict[str, int], name: str) -> Any:
    """The document the transform must produce, derived structurally."""
    doc = copy.deepcopy(before)

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "tasks" and isinstance(value, dict):
                    for task in list(value):
                        if task in DELETE_TASKS:
                            del value[task]
                        elif task in upstream and (name, task) not in KEEP_TASK_VALUES:
                            value[task] = upstream[task]
                else:
                    visit(value)

    visit(doc)
    return doc


def main() -> int:
    write = "--write" in sys.argv[1:]
    restored_files = 0
    restored_total = 0
    deletions_kept: dict[str, list[str]] = {}
    additions_kept: dict[str, list[str]] = {}
    for path in changed_files():
        name = path.name
        if name in EXCLUDED_FILES:
            print(f"SKIP (decided keep): {name}")
            continue
        if not path.exists():
            print(f"SKIP (deleted fork-side): {name}")
            continue
        base = upstream_text(path)
        if base is None:
            print(f"SKIP (fork-added, no upstream): {name}")
            continue
        upstream = parse_tasks(base)
        raw = path.read_bytes()
        new_raw, restored, deleted, fork_only = transform_lines(raw, upstream, name)
        fork_tasks = parse_tasks(raw.decode("utf-8"))
        removed = sorted(
            t for t in upstream if t not in fork_tasks and t not in DELETE_TASKS
        )
        if removed:
            deletions_kept[name] = removed
        if fork_only:
            additions_kept[name] = fork_only
        if new_raw == raw:
            continue
        restored_files += 1
        restored_total += len(restored)
        changes = restored + [f"{d} (deleted)" for d in deleted]
        print(f"{name}: {', '.join(changes)}")
        if write:
            after = yaml.safe_load(new_raw.decode("utf-8"))
            expected = expected_document(
                yaml.safe_load(raw.decode("utf-8")), upstream, name
            )
            if after != expected:
                raise SystemExit(f"{name}: transformed document drifted from expected")
            path.write_bytes(new_raw)

    print()
    print(
        f"{'Wrote' if write else 'Would write'} {restored_files} files, "
        f"{restored_total} weights restored."
    )
    print()
    print("Fork task deletions kept (upstream key absent fork-side, Intercept aside):")
    for name in sorted(deletions_kept):
        print(f"  {name}: {', '.join(deletions_kept[name])}")
    print()
    print("Fork-only keys kept (feature lanes marked *):")
    for name in sorted(additions_kept):
        marked = [
            f"{'*' if entry.split(':')[0] in FORK_LANES else ''}{entry}"
            for entry in additions_kept[name]
        ]
        print(f"  {name}: {', '.join(marked)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
