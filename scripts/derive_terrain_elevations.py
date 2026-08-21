"""Sample terrain elevation at every campaign ground-object position.

Retribution plans a target steerpoint on the deck, and the generated mission, the
DTC cartridge and the kneeboard all write it as ``0``. Whatever the ``RADIO`` /
``altitudeType 2`` flag beside that 0 is meant to mean, the number reaches the jet
as sea level, so a target on high ground gets a steerpoint underground. Writing
the real elevation AMSL removes the ambiguity, and needs a source: nothing in the
tree carries terrain height (``airport_imagery`` covers airfields only, pydcs
ships no heightmap, and the campaign mizzes store 0 for ground route points).

This is that source, scoped to what the fork needs first: the fixed ground objects
each campaign authors. Their positions come from the campaign ``.miz``, so they
are known offline and never move. Front-line, convoy and relocated mobile targets
are NOT covered and keep the old 0.

Output mirrors ``resources/airport_imagery/``: one JSON per terrain, keyed by
grid-rounded terrain XY. Elevations come from Open-Elevation (SRTM, ~5 m), the
same service the airport table falls back to.

SRTM stops at 60 N, and Open-Elevation answers 0 rather than erroring past it, so
a terrain whose every point reads sea level is discarded instead of shipped --
Kola (~68 N) is the map that catches. Its targets keep the old 0 AGL.

    python scripts/derive_terrain_elevations.py                  # every terrain
    python scripts/derive_terrain_elevations.py --terrain PersianGulf
    python scripts/derive_terrain_elevations.py --dry-run        # count only

A DCS-side ``land.getHeight`` dump would be exact rather than ~5 m, and offline;
it needs the DM to run it once per map, which is why this route came first.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable, Optional

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from dcs import Mission  # noqa: E402
from dcs.mapping import Point  # noqa: E402

CAMPAIGNS_DIR = _REPO_ROOT / "resources" / "campaigns"
OUTPUT_DIR = _REPO_ROOT / "resources" / "terrain_elevation"

OPEN_ELEVATION_URL = "https://api.open-elevation.com/api/v1/lookup"

#: Key resolution. A campaign marker is a point, not an area, so this only has to
#: be fine enough that two authored objectives never share a cell; 100 m is well
#: under the spacing of any authored site.
GRID_M = 100

#: Points per POST. Open-Elevation is free and unauthenticated; keep the batches
#: modest and pause between them.
BATCH = 100
PAUSE_S = 1.0
RETRIES = 3


def grid_key(x: float, y: float) -> str:
    return f"{round(x / GRID_M) * GRID_M},{round(y / GRID_M) * GRID_M}"


def campaign_positions(miz: Path) -> tuple[Optional[Any], set[tuple[float, float]]]:
    """Every authored ground/static/ship position in one campaign, and its terrain."""
    mission = Mission()
    try:
        mission.load_file(str(miz))
    except Exception as exc:  # noqa: BLE001 - one bad miz must not stop the sweep
        print(f"  {miz.name}: cannot read ({exc!r}); skipping")
        return None, set()
    positions: set[tuple[float, float]] = set()
    for coalition in mission.coalition.values():
        for country in coalition.countries.values():
            groups = (
                list(country.vehicle_group)
                + list(country.static_group)
                + list(country.ship_group)
            )
            for group in groups:
                for unit in group.units:
                    positions.add((unit.position.x, unit.position.y))
    return mission.terrain, positions


def fetch_elevations(located: list[tuple[str, float, float]]) -> dict[str, float]:
    """Grid key -> metres AMSL, for as many points as the service answers."""
    out: dict[str, float] = {}
    for start in range(0, len(located), BATCH):
        batch = located[start : start + BATCH]
        body = json.dumps(
            {"locations": [{"latitude": la, "longitude": ln} for _, la, ln in batch]}
        ).encode("utf-8")
        request = urllib.request.Request(
            OPEN_ELEVATION_URL,
            data=body,
            headers={"Content-Type": "application/json"},
        )
        for attempt in range(1, RETRIES + 1):
            try:
                with urllib.request.urlopen(request, timeout=90) as response:
                    results = json.load(response).get("results", [])
                for (key, _, _), result in zip(batch, results):
                    elevation = result.get("elevation")
                    if elevation is not None:
                        out[key] = float(elevation)
                break
            except (urllib.error.URLError, ValueError, TimeoutError) as exc:
                if attempt == RETRIES:
                    print(f"    batch at {start} failed after {RETRIES}: {exc!r}")
                else:
                    time.sleep(PAUSE_S * attempt * 2)
        print(f"    {min(start + BATCH, len(located))}/{len(located)}")
        time.sleep(PAUSE_S)
    return out


def write_terrain(terrain_name: str, elevations: dict[str, float]) -> Path:
    """Merge into the terrain's JSON, keeping points an earlier run resolved."""
    path = OUTPUT_DIR / f"{terrain_name.lower()}.json"
    points: dict[str, float] = {}
    if path.exists():
        points = json.loads(path.read_text(encoding="utf-8")).get("points", {})
    points.update(elevations)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "terrain": terrain_name,
                "grid_m": GRID_M,
                "source": "open-elevation (SRTM)",
                "points": dict(sorted(points.items())),
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terrain", help="Only this terrain (pydcs name).")
    parser.add_argument(
        "--dry-run", action="store_true", help="Count points; query nothing."
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    terrains: dict[str, Any] = {}
    positions_by_terrain: dict[str, set[tuple[float, float]]] = {}
    for miz in sorted(CAMPAIGNS_DIR.glob("*.miz")):
        terrain, positions = campaign_positions(miz)
        if terrain is None:
            continue
        if args.terrain and terrain.name.lower() != args.terrain.lower():
            continue
        terrains.setdefault(terrain.name, terrain)
        positions_by_terrain.setdefault(terrain.name, set()).update(positions)
        print(f"  {miz.name}: {len(positions)} positions ({terrain.name})")

    for name, positions in sorted(positions_by_terrain.items()):
        # One query per grid cell, at the cell's own centre rather than at the
        # first unit that landed in it, so the answer is a property of the cell.
        cells: dict[str, tuple[float, float]] = {}
        for x, y in positions:
            key = grid_key(x, y)
            if key not in cells:
                cx, cy = (float(v) for v in key.split(","))
                cells[key] = (cx, cy)
        print(f"{name}: {len(positions)} positions -> {len(cells)} cells")
        if args.dry_run:
            continue
        located = []
        for key, (cx, cy) in cells.items():
            latlng = Point(cx, cy, terrains[name]).latlng()
            located.append((key, latlng.lat, latlng.lng))
        elevations = fetch_elevations(located)
        if elevations and not any(elevations.values()):
            # SRTM covers 60 N to 56 S, and Open-Elevation answers 0 rather than
            # erroring outside it -- so a whole terrain of sea level is no-data,
            # not flat ground. Kola (~68 N) is the map this catches. Writing it
            # would be worse than writing nothing: the consumer would take the 0
            # as a real elevation instead of falling back to 0 AGL.
            print(f"  {name}: every point read 0 (no DEM coverage); not written")
            continue
        path = write_terrain(name, elevations)
        print(f"  wrote {len(elevations)}/{len(cells)} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
