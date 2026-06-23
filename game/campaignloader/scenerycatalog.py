"""Shared scenery-catalog core: categorize + cluster CWG scenery-dump buildings.

This is the map-agnostic core extracted from the build-time emitter
(``_scenerytools/cwg_scenery_emitter.py``) so that two front-ends share one
clustering implementation:

* the emitter CLI — selects a Red-Tide-specific laydown and writes blue/white
  trigger zones into a ``.miz`` copy (Strategy A);
* the runtime importer (planned) — synthesizes ``SceneryGroup`` objects at
  campaign-gen for any campaign on a scanned map (Strategy B).

Design rationale and the two strategies live in
``docs/dev/design/414th-scenery-import-notes.md``.

Pure stdlib on purpose: no pydcs / Retribution imports, so the emitter (run
standalone) and the importer (run inside the game) can both consume it, and the
logic stays unit-testable without a theater.

Coordinate convention: ``Building.x`` is DCS world X (N/S), ``Building.z`` is DCS
world Z (E/W) — i.e. the scanner dump's ``x``/``z`` columns verbatim. The pydcs
mapping (``Point.x == dump.x``, ``Point.y == dump.z``) is applied by the consumer,
not here.

Emitter swap: replace the emitter's local ``Building``/``Cluster``/``categorize``/
``cluster``/``CATEGORY_PATTERNS`` with imports from this module and pass
``region_fn=region_of`` to :func:`cluster` so its AO region tagging still feeds
``select()``. Nothing else in the emitter changes.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Optional

# Category-ordering used by both front-ends when iterating laydowns.
CATEGORIES: tuple[str, ...] = ("factory", "power", "ware", "comms")

# type-name substring (upper-cased) -> Retribution scenery category. The category
# strings must stay in lock-step with
# ``SceneryGroup.group_task_for_scenery_group_category`` (game/scenery_group.py).
CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "factory": ("INDUSTRIAL",),
    "power": ("TRANSFORMER",),
    "ware": ("WAREHOUSE", "SILO"),
    "comms": ("ANTENNA", "RW_TOWER", "WEATHER"),
}

# --- clustering tuning (generic; AO-specific knobs live in the emitter) --------
CLUSTER_CELL = (
    150.0  # grid cell (m); buildings in touching cells merge into one complex
)
BUILD_CAP = 20  # max members per objective (keep the BUILD_CAP closest to centroid)
RADIUS_MARGIN = (
    30.0  # blue-circle radius = max member distance from centroid + this (m)
)


def categorize(typ: str) -> Optional[str]:
    """Map a dump ``type`` name to a scenery category, or ``None`` to drop it."""
    up = typ.upper()
    for cat, pats in CATEGORY_PATTERNS.items():
        if any(p in up for p in pats):
            return cat
    return None


@dataclass
class Building:
    oid: str
    typ: str
    x: float
    z: float


@dataclass
class Cluster:
    category: str
    members: list[Building]
    cx: float = 0.0
    cz: float = 0.0
    radius: float = 0.0
    # Optional caller-assigned tag (e.g. the emitter's AO region). Generic
    # consumers leave it at the default.
    region: str = "other"

    def finalize(self) -> None:
        """Compute centroid, cap members to the BUILD_CAP closest, set radius."""
        self.cx = sum(b.x for b in self.members) / len(self.members)
        self.cz = sum(b.z for b in self.members) / len(self.members)
        # cap to the BUILD_CAP closest to centroid, then recompute the centroid
        self.members.sort(key=lambda b: (b.x - self.cx) ** 2 + (b.z - self.cz) ** 2)
        if len(self.members) > BUILD_CAP:
            self.members = self.members[:BUILD_CAP]
            self.cx = sum(b.x for b in self.members) / len(self.members)
            self.cz = sum(b.z for b in self.members) / len(self.members)
        self.radius = RADIUS_MARGIN + max(
            math.hypot(b.x - self.cx, b.z - self.cz) for b in self.members
        )

    @property
    def n(self) -> int:
        return len(self.members)


def cluster(
    buildings: list[Building],
    category: str,
    region_fn: Optional[Callable[[float, float], str]] = None,
) -> list[Cluster]:
    """Grid union-find: buildings whose cells touch (8-connectivity) form one complex.

    If *region_fn* is given, each finalized cluster's ``region`` is set from its
    centroid — the hook the emitter uses for its AO-specific spread rules. Generic
    consumers omit it and ignore ``region``.
    """
    cell_of = lambda b: (int(b.x // CLUSTER_CELL), int(b.z // CLUSTER_CELL))
    parent: dict[int, int] = {}

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        parent[find(a)] = find(b)

    cells: dict[tuple[int, int], list[int]] = defaultdict(list)
    for idx, b in enumerate(buildings):
        parent[idx] = idx
        cells[cell_of(b)].append(idx)
    for (cx, cz), idxs in cells.items():
        # union within cell + with the 8 neighbour cells
        for di in (-1, 0, 1):
            for dz in (-1, 0, 1):
                nb = cells.get((cx + di, cz + dz))
                if nb:
                    for j in nb:
                        union(idxs[0], j)
        for j in idxs[1:]:
            union(idxs[0], j)

    groups: dict[int, list[Building]] = defaultdict(list)
    for idx, b in enumerate(buildings):
        groups[find(idx)].append(b)
    clusters = [Cluster(category, m) for m in groups.values()]
    for c in clusters:
        c.finalize()
        if region_fn is not None:
            c.region = region_fn(c.cx, c.cz)
    return clusters


def load_buildings_from_csv(path: str) -> dict[str, list[Building]]:
    """Read a scanner-dump CSV into ``{category: [Building, ...]}`` (uncategorized rows dropped).

    Expects the scanner's columns: ``id, type, life0, x, z, y, lat, lon, mgrs``.
    """
    by_cat: dict[str, list[Building]] = defaultdict(list)
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            cat = categorize(row["type"])
            if cat is None:
                continue
            by_cat[cat].append(
                Building(row["id"], row["type"], float(row["x"]), float(row["z"]))
            )
    return by_cat
