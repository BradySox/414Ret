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
CATEGORIES: tuple[str, ...] = (
    "factory",
    "power",
    "ware",
    "comms",
    "commandcenter",
    "fuel",
    "oil",
)

# type-name substring (upper-cased) -> Retribution scenery category. The category
# strings must stay in lock-step with
# ``SceneryGroup.group_task_for_scenery_group_category`` (game/scenery_group.py).
# Curated 2026-06-23 from a 282-type CWG discovery scan: only genuine strategic targets,
# dropping agricultural/airfield/decorative models. categorize() returns the FIRST match, so
# the substrings must not cross-claim (e.g. INDUSTRIAL_CONTAINER -> ware, not factory).
CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "factory": ("INDUSTRIAL_EU", "INDUSTRIAL_BALTIC", "CAR_PLANT"),
    "power": (
        "POWERPLANT",
        "COOLING_TOWER",
        "POWER_HUB",
        "POWER_TRANS_LINE",
        "TRANSFORMER_BOOTH",
    ),
    "ware": ("TRAIN_DEPOT", "INDUSTRIAL_CONTAINER", "RAILWAY_PLATFORM"),
    "comms": (
        "NDB_RADIO",
        "GDR_RADIO_TOWER",
        "LATTICE_TOWER",
        "RSBN",
        "RSP-10",
        "VOR_DME",
        "TESLA_RP",
        "AIRBASE_ANTENNA",
        "WEATHER_STATION",
    ),
    "commandcenter": (
        "KASERNE",
        "MILITARY_BUILDING",
        "TANK_HANGAR",
        "KDP",
        "HANGAR_MILLITARY",
        "BARRACK",
    ),
    "fuel": ("FUEL_STORAGE", "GAZ_STATION"),
    "oil": ("OILGAS_REFINERY",),
}

# --- clustering tuning -----------------------------------------------------------------
# Tight fixed-radius complexes: an objective is a seed building plus its nearest unused
# neighbours within RADIUS_CAP, capped at BUILD_CAP. This bounds the blue-circle radius so a
# selection pass can keep objectives from overlapping (the union-find approach chained whole
# districts into one giant pool — see the 28-building bug it caused).
RADIUS_CAP = 120.0  # max neighbour distance from a complex's seed (m)
BUILD_CAP = 8  # max members per objective
RADIUS_MARGIN = (
    20.0  # blue-circle radius = max member distance from centroid + this (m)
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
        """Compute centroid and radius (members are already bounded by ``cluster``)."""
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
    """Form tight complexes: seed at the densest building, take its nearest unused
    neighbours within ``RADIUS_CAP`` (capped at ``BUILD_CAP``), mark them used, repeat. This
    bounds each complex's radius so a selection pass can keep objectives from overlapping.

    If *region_fn* is given, each finalized cluster's ``region`` is set from its centroid —
    the hook the emitter uses for its AO-specific spread rules. Generic consumers omit it.

    Indexed by position (not ``oid``) so duplicate/placeholder ids cluster correctly.
    """
    cell = RADIUS_CAP
    grid: dict[tuple[int, int], list[int]] = defaultdict(list)
    for i, b in enumerate(buildings):
        grid[(int(b.x // cell), int(b.z // cell))].append(i)

    def neighbours(i: int, used: set[int]) -> list[int]:
        b = buildings[i]
        cx, cz = int(b.x // cell), int(b.z // cell)
        out = []
        for di in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for j in grid.get((cx + di, cz + dz), ()):
                    if (
                        j not in used
                        and math.hypot(buildings[j].x - b.x, buildings[j].z - b.z)
                        <= RADIUS_CAP
                    ):
                        out.append(j)
        return out

    empty: set[int] = set()
    order = sorted(
        range(len(buildings)), key=lambda i: len(neighbours(i, empty)), reverse=True
    )
    used: set[int] = set()
    clusters: list[Cluster] = []
    for i in order:
        if i in used:
            continue
        nb = neighbours(i, used)
        nb.sort(
            key=lambda j: math.hypot(
                buildings[j].x - buildings[i].x, buildings[j].z - buildings[i].z
            )
        )
        nb = nb[:BUILD_CAP]
        if not nb:
            continue
        used.update(nb)
        c = Cluster(category, [buildings[j] for j in nb])
        c.finalize()
        if region_fn is not None:
            c.region = region_fn(c.cx, c.cz)
        clusters.append(c)
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
