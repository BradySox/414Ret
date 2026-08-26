"""Build a terrain's shipped §96 border file (``resources/borders/<terrain>.yaml``).

Borders are a property of the map, not of a campaign, so they are generated once
per terrain and every campaign on that map gets them. This is what makes §96
reach the 52 real-world-map campaigns that author no borders at all.

The file carries **geometry and an origin, nothing else**. Posture and airframe
come from the dated table at mission-generation time, so one border file is
correct in 1975 and in 2025.

Per country the tool: clips the real boundary to the map, drops sliver pieces,
simplifies to a vertex budget, converts to terrain XY, and picks an origin --
a real map airfield inside the polygon where one exists, otherwise an air-spawn
station at the polygon's representative point.

**Every country on the map is drawn, the map's own nation included.** An
earlier ``--host`` flag left it out on the theory that a border round the
battlefield is noise. That deleted Russia from Kola and Iran from the Persian
Gulf -- the most relevant border on each of those maps -- and left the war
itself as the one region with no line on it. What a country's airspace *means*
is decided at run time from who holds the control points inside it, so the
tool has no business deciding which countries are interesting.

Usage:

    python tools/build_terrain_borders.py afghanistan \\
        --geojson-dir <dir> \\
        --countries Afghanistan Pakistan Iran Turkmenistan Uzbekistan \\
                    Tajikistan India \\
        --clip 24 38 59.5 73

Country land shares per map -- and which ones the eyeball misses -- are measured
in ``docs/dev/design/414th-national-postures-notes.md``. Use that table for the
``--countries`` list; it caught India on Afghanistan and Saudi Arabia on Syria.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from neutral_border_geo import (  # noqa: E402
    TERRAINS,
    country_polygon,
    pieces_of,
    simplify_shared_to_budget,
    to_xy,
)
from shapely.geometry import Point as ShapelyPoint, Polygon, box  # noqa: E402

#: Air-spawn altitude for a country with no airfield inside its own border.
SPAWN_ALT_FT = 20000


def border_lines(ring: list[tuple[float, float]]) -> list[str]:
    """The ring as wrapped yaml flow style.

    One vertex per line is 2,573 lines across the eight shipped maps and reviews
    as noise -- nobody reads a coordinate list, and at 96 vertices a country is
    a page of it. Flow style parses to exactly the same thing and costs a tenth
    of the lines.
    """
    out = ["    border: ["]
    row = "      "
    for index, (x, y) in enumerate(ring):
        pair = f"[{x:.0f}, {y:.0f}]"
        if index < len(ring) - 1:
            pair += ","
        if len(row) + len(pair) > 88 and row.strip():
            out.append(row.rstrip())
            row = "      "
        row += pair + " "
    if row.strip():
        out.append(row.rstrip())
    out.append("    ]")
    return out


def airfield_in(terrain: Any, polygon: Polygon) -> Optional[str]:
    """A real map airfield inside this polygon, if the terrain has one.

    Prefers the one furthest from the border, so an alert flight does not launch
    from a strip that is metres inside its own frontier.
    """
    best: Optional[tuple[float, str]] = None
    for airport in terrain.airport_list():
        latlng = airport.position.latlng()
        point = ShapelyPoint(latlng.lng, latlng.lat)
        if not polygon.contains(point):
            continue
        depth = polygon.exterior.distance(point)
        if best is None or depth > best[0]:
            best = (depth, airport.name)
    return best[1] if best else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("terrain", choices=sorted(TERRAINS))
    parser.add_argument("--geojson-dir", type=Path, required=True)
    parser.add_argument("--countries", nargs="+", required=True)
    parser.add_argument(
        "--clip",
        nargs=4,
        type=float,
        required=True,
        metavar=("LAT_MIN", "LAT_MAX", "LON_MIN", "LON_MAX"),
    )
    parser.add_argument(
        "--max-vertices",
        type=int,
        default=96,
        help="Ring vertex budget, binding the WORST ring on the map -- the whole "
        "map is simplified as one coverage at a single tolerance, because a "
        "shared frontier has to be simplified once to come out the same on both "
        "sides of it. MEASURED 2026-08-26 on Kola: at 96 the frontier match is "
        "89%% (against 35%% when each country was simplified alone), Norway's "
        "shape error is 7%% (against 14.7%%), and the map carries 219 vertices "
        "against 289 -- better on every axis at once, because Visvalingam on a "
        "coverage spends vertices where the shape needs them. The cost of "
        "raising it is F10 markup count: the fill is drawn triangle by "
        "triangle.",
    )
    parser.add_argument(
        "--min-area-km2",
        type=float,
        default=0.0,
        help="Drop landmasses smaller than this. Each surviving piece becomes a "
        "zone with its own alert flight, so an archipelago needs a floor: the "
        "Falklands map otherwise gives Chile five, one of them the 1,439 km² "
        "Cape Horn group. Real territory, but not airspace anyone contests.",
    )
    parser.add_argument("--out", type=Path, default=Path("resources/borders"))
    args = parser.parse_args()

    terrain = TERRAINS[args.terrain]()
    lat_min, lat_max, lon_min, lon_max = args.clip
    clip = box(lon_min, lat_min, lon_max, lat_max)

    lines = [
        f"# §96 border geometry for the {args.terrain} map. GENERATED by",
        "# tools/build_terrain_borders.py -- edit the tool, not this file.",
        "#",
        "# Geometry and an origin only. What each country's airspace MEANS is",
        "# decided at run time from the airbases inside its border, so this file",
        "# is correct on any campaign and in any era; the airframe it scrambles",
        "# comes from resources/borders/national_postures.yaml against the",
        "# campaign's date. A campaign that declares its own",
        "# neutral_border_defense: block overrides this file completely.",
        "#",
        f"# Clip: {lat_min} {lat_max} {lon_min} {lon_max}",
        f"terrain: {args.terrain}",
        "zones:",
    ]

    # Pass 1: clip every country to the map and drop slivers. Nothing is
    # simplified yet -- that has to happen across all of them at once, or each
    # shared frontier comes out drawn twice (see simplify_shared).
    import math

    collected: list[tuple[str, Any]] = []
    for name in args.countries:
        path = args.geojson_dir / f"{name.lower().replace(' ', '_')}.json"
        if not path.exists():
            print(f"  !! {name}: no geojson at {path}", file=sys.stderr)
            continue
        geom = country_polygon(json.loads(path.read_text(encoding="utf-8")))
        parts = pieces_of(geom.intersection(clip))
        if not parts:
            print(f"  -- {name}: nothing on this map, skipped", file=sys.stderr)
            continue
        for piece in parts:
            if args.min_area_km2:
                # Rough but sufficient: one degree of latitude is ~111 km, and
                # one of longitude ~111*cos(lat) at the piece's own latitude.
                lat = math.radians(piece.centroid.y)
                km2 = piece.area * 111.0 * (111.0 * math.cos(lat))
                if km2 < args.min_area_km2:
                    print(
                        f"  -- {name}: dropped a {km2:.0f} km² landmass",
                        file=sys.stderr,
                    )
                    continue
            collected.append((name, piece))

    # Pass 2: one shared coverage, one tolerance, so neighbours agree.
    simplified = simplify_shared_to_budget(collected, args.max_vertices)
    if args.min_area_km2:
        # Again, because rebuilding the coverage can shed a country into extra
        # fragments. Dropping one leaves a gap, which a coverage allows; an
        # overlap or a mismatched edge is what it does not.
        kept = []
        for name, piece in simplified:
            lat = math.radians(piece.centroid.y)
            km2 = piece.area * 111.0 * (111.0 * math.cos(lat))
            if km2 >= args.min_area_km2:
                kept.append((name, piece))
            else:
                print(f"  -- {name}: dropped a {km2:.0f} km² fragment", file=sys.stderr)
        simplified = kept

    written = 0
    seen: dict[str, int] = {}
    totals: dict[str, int] = {}
    for name, _ in simplified:
        totals[name] = totals.get(name, 0) + 1
    for name, piece in simplified:
        seen[name] = seen.get(name, 0) + 1
        ring = [(float(x), float(y)) for x, y in list(piece.exterior.coords)[:-1]]
        ring_xy = to_xy(terrain, ring)
        label = name if totals[name] == 1 else f"{name} (part {seen[name]})"
        lines.append(f"  # {label} — {len(ring_xy)} vertices")
        lines.append(f"  - country: {name}")
        field = airfield_in(terrain, piece)
        if field:
            lines.append(f"    airfield: {field}")
        else:
            rep = piece.representative_point()
            x, y = to_xy(terrain, [(rep.x, rep.y)])[0]
            lines.append(f"    spawn: [{x:.0f}, {y:.0f}]")
            lines.append(f"    spawn_alt_ft: {SPAWN_ALT_FT}")
        lines.extend(border_lines(ring_xy))
        written += 1

    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / f"{args.terrain}.yaml"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {target} ({written} zones)")


if __name__ == "__main__":
    main()
