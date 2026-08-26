"""Author campaign ``neutral_border_defense:`` borders from real boundary data (§96).

**The standard (2026-08-24, DM call):** a neutral country's border polygon comes
from real boundary data, never hand-tracing -- and only real-world-georeferenced
maps get the feature (fictional-overlay campaigns are out of scope). Pipeline:
a public-domain country GeoJSON -> clip to the map area -> optional corridor cut
-> shapely simplify to a vertex budget -> ``Point.from_latlng`` -> terrain XY ->
the yaml block pasted into ``resources/campaigns/*.yaml``. The GeoJSON is a
dev-time input read from disk; nothing here runs at campaign or mission time.

Three things matter beyond the basic trace:

**Clip to the map.** A country's real outline is mostly off any given DCS map --
Iran's runs to the Persian Gulf, hundreds of km outside Afghanistan's terrain.
Un-clipped, the vertex budget is spent on coastline nobody can fly to. Always
pass ``--clip``.

**Cut the corridor.** ``--corridor-lon`` subtracts a north-south lane, which
turns one country into the two walls of a flight corridor. This is how the
Afghanistan campaign models the OEF "boulevard": carrier aircraft coming north
out of the Arabian Sea have a lane through Pakistan and get intercepted if they
wander out of it. Each surviving piece is emitted as its own zone.

**Spawn point vs airfield.** ``--airfield`` for a neutral whose airbase is on
the map. ``--auto-spawn`` for one whose is not (every Afghanistan neighbour):
each piece gets an air-spawn point at its own representative point, guaranteed
inside that piece's territory.

Usage:

    # Lebanon: it has a field on the Syria map.
    python tools/neutral_border_geo.py lebanon.json --terrain syria \\
        --country Lebanon --airfield Rayak --aircraft MiG-29A --sam

    # Pakistan: no field on the Afghanistan map, and a corridor cut for the
    # carrier route north.
    python tools/neutral_border_geo.py pakistan.json --terrain afghanistan \\
        --country Pakistan --aircraft MiG-21Bis --auto-spawn \\
        --clip 24 36.5 60 72 --corridor-lon 64.3 66.3

GeoJSON coordinates are [lon, lat]; DCS terrain XY is pydcs Point.x/.y = DCS
x/z. Rings are simplified with growing tolerance until they fit the budget --
a border trigger needs corridor fidelity, not meters.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional

from dcs.mapping import LatLng, Point
from dcs.terrain.afghanistan import Afghanistan
from dcs.terrain.caucasus import Caucasus
from dcs.terrain.falklands import Falklands
from dcs.terrain.germanycoldwar import GermanyColdWar
from dcs.terrain.iraq import Iraq
from dcs.terrain.kola import Kola
from dcs.terrain.nevada import Nevada
from dcs.terrain.normandy import Normandy
from dcs.terrain.persiangulf import PersianGulf
from dcs.terrain.sinai import Sinai
from dcs.terrain.syria import Syria
from shapely.geometry import MultiPolygon, Polygon, box
from shapely.ops import polygonize, unary_union

TERRAINS = {
    "afghanistan": Afghanistan,
    "caucasus": Caucasus,
    "falklands": Falklands,
    "germany": GermanyColdWar,
    "iraq": Iraq,
    "kola": Kola,
    "nevada": Nevada,
    "normandy": Normandy,
    "persiangulf": PersianGulf,
    "sinai": Sinai,
    "syria": Syria,
}

#: A clipped piece smaller than this (square degrees) is a sliver the author
#: never meant -- a coastal speck or a border artifact -- and is dropped.
MIN_PIECE_AREA = 0.05


def one_geometry(geometry: dict[str, Any]) -> Polygon | MultiPolygon:
    if geometry["type"] == "Polygon":
        return Polygon(
            geometry["coordinates"][0],
            holes=geometry["coordinates"][1:] or None,
        )
    if geometry["type"] == "MultiPolygon":
        return MultiPolygon(
            [(poly[0], poly[1:] or None) for poly in geometry["coordinates"]]
        )
    raise SystemExit(f"Unsupported geometry type: {geometry['type']}")


#: A source feature this much wider than it is tall is a wrap-around artifact
#: rather than land. Russia's file carries one spanning 359.8 deg of longitude
#: in a 0.87 deg latitude band; merged in, it becomes a fake 75,554 km2 Russian
#: claim across northern Norway on the Kola map. Russia's real mainland feature
#: also spans the globe -- Chukotka crosses the antimeridian -- but is 36.6 deg
#: tall, so the ratio is the test and the width is not.
MAX_FEATURE_ASPECT = 100.0


def is_wraparound_artifact(geom: Any) -> bool:
    """Is this source feature a degenerate longitude band rather than land?"""
    if geom.is_empty:
        return True
    min_x, min_y, max_x, max_y = geom.bounds
    height = max_y - min_y
    if height <= 0:
        return True
    return (max_x - min_x) / height > MAX_FEATURE_ASPECT


def country_polygon(data: dict[str, Any]) -> Polygon | MultiPolygon:
    """The whole country from a GeoJSON file, every feature merged.

    **Read every feature, never just the first.** These files split a country
    into one feature per landmass -- Denmark is 64, Russia 320, Germany 39 --
    and taking ``features[0]`` silently yields a fragment: Denmark's first
    feature does not contain Copenhagen, so the "border" would have been one
    island. It cost nothing to get wrong and would have been near-impossible to
    spot on a map you had never seen drawn correctly.
    """
    if data.get("type") == "FeatureCollection":
        parts = [one_geometry(f["geometry"]) for f in data["features"]]
    elif data.get("type") == "Feature":
        parts = [one_geometry(data["geometry"])]
    else:
        parts = [one_geometry(data)]
    parts = [part for part in parts if not is_wraparound_artifact(part)]
    # Repair before merging. Some published rings self-intersect (Saudi Arabia
    # has one on the Kuwaiti border) and unary_union raises a TopologyException
    # on them outright -- a zero-width buffer is the standard fix and leaves a
    # valid ring untouched.
    repaired = []
    for part in parts:
        repaired.append(part if part.is_valid else part.buffer(0))
    merged = unary_union(repaired)
    if not merged.is_valid:
        merged = merged.buffer(0)
    if isinstance(merged, (Polygon, MultiPolygon)):
        return merged
    raise SystemExit("Merged geometry is not polygonal.")


def pieces_of(geom: Polygon | MultiPolygon) -> list[Polygon]:
    """Non-sliver polygon pieces, largest first."""
    parts = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    kept = [p for p in parts if not p.is_empty and p.area >= MIN_PIECE_AREA]
    return sorted(kept, key=lambda p: p.area, reverse=True)


def simplify_to_budget(poly: Polygon, max_vertices: int) -> list[tuple[float, float]]:
    """Douglas-Peucker with growing tolerance until the ring fits the budget."""
    tolerance = 0.001  # degrees, ~100 m
    for _ in range(50):
        simplified = poly.simplify(tolerance, preserve_topology=True)
        if not simplified.is_empty:
            coords = list(simplified.exterior.coords)[:-1]  # drop the closing dup
            if len(coords) <= max_vertices:
                return [(float(lon), float(lat)) for lon, lat in coords]
        tolerance *= 1.5
    raise SystemExit("Could not simplify a ring to the vertex budget.")


#: Grid the country outlines are snapped to before they are noded, in degrees.
#: ~100 m at these latitudes: below any border's real precision, and above the
#: few-metre disagreement between two source files tracing the same frontier.
SNAP_DEGREES = 0.001

#: Where the tolerance search gives up. Several degrees is already coarser than
#: any border on any DCS map, so past here a ring that has not shrunk is at a
#: floor the algorithm cannot get under, not one more tolerance would fix.
MAX_TOLERANCE_DEGREES = 5.0


def _components(geom: Any) -> list[Polygon]:
    """Every polygon in a geometry, largest first. Empty in, empty out."""
    if geom.is_empty:
        return []
    parts = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    return sorted(
        (p for p in parts if not p.is_empty), key=lambda p: p.area, reverse=True
    )


def as_coverage(pieces: list[tuple[str, Polygon]]) -> list[tuple[str, Polygon]]:
    """Rebuild overlapping country polygons as a valid, edge-matched coverage.

    Clipped country outlines from different source files overlap slightly and
    their shared frontiers do not share vertices, so they are not a coverage and
    cannot be simplified as one. Unioning the boundaries nodes them; polygonize
    turns that arrangement into faces that tile it exactly; each face goes to the
    first country that contains it, so an overlap is awarded once rather than
    twice.
    """
    import shapely

    # Snap to a common grid FIRST. Two source files trace the same frontier a
    # few metres apart, and nodding that raw leaves a chain of hairline slivers
    # -- each of which becomes its own face, and coverage_simplify floors every
    # face at a triangle. Armenia came out of the Caucasus build as ~32 faces
    # with a 97-vertex floor it could never simplify under. At 100 m the slivers
    # collapse and the frontier becomes one shared arc, which is the point.
    snapped: list[tuple[str, Polygon]] = []
    for name, piece in pieces:
        # Snapping can pinch a narrow neck apart (Norway's coast does exactly
        # this), so a piece may come back as several. Keep them all -- an island
        # dropped here is territory the map stops defending.
        fixed = shapely.set_precision(piece, SNAP_DEGREES)
        snapped.extend((name, part) for part in _components(fixed))
    boundaries = unary_union([piece.exterior for _, piece in snapped])
    faces = [face for face in polygonize(boundaries) if not face.is_empty]
    pieces = snapped
    claimed: list[list[Polygon]] = [[] for _ in pieces]
    for face in faces:
        point = face.representative_point()
        for index, (_, piece) in enumerate(pieces):
            if piece.contains(point):
                claimed[index].append(face)
                break
    out: list[tuple[str, Polygon]] = []
    for (name, piece), mine in zip(pieces, claimed):
        merged = unary_union(mine) if mine else piece
        # Every component, never just the largest: dropping one leaves the
        # neighbour that shared its edge matched against nothing, which is what
        # made the Falklands coverage invalid where Argentina and Chile
        # interlock across Tierra del Fuego.
        out.extend((name, part) for part in _components(merged))
    return out


def simplify_shared(
    pieces: list[tuple[str, Polygon]], tolerance: float
) -> list[tuple[str, Polygon]]:
    """Simplify a whole map's countries as ONE coverage.

    Simplifying each country on its own leaves every shared frontier drawn
    twice, because Douglas-Peucker keeps different vertices on each side's copy
    of it. MEASURED 2026-08-26: neighbours' lines coincided only 35-65 % of the
    time, and Russia/Norway on Kola at 7 % -- two lines weaving along one
    border, with slivers between them.

    ``shapely.coverage_simplify`` exists for exactly this: it simplifies shared
    edges once and hands both sides the same result, so neighbours agree by
    construction and the overlaps go with the gaps. It requires a valid
    coverage, which ``as_coverage`` builds first.
    """
    import shapely

    coverage = as_coverage(pieces)
    simplified = shapely.coverage_simplify([poly for _, poly in coverage], tolerance)
    out: list[tuple[str, Polygon]] = []
    for (name, original), geom in zip(coverage, simplified):
        if geom.is_empty:
            geom = original
        out.extend((name, part) for part in _components(geom))
    return out


def simplify_shared_to_budget(
    pieces: list[tuple[str, Polygon]], max_vertices: int
) -> list[tuple[str, Polygon]]:
    """``simplify_shared`` at the tightest tolerance that fits every ring.

    One tolerance for the whole map, not one per country -- a shared arc has to
    be simplified once to come out the same on both sides of it, which is the
    entire point. The budget therefore binds the *worst* ring on the map.

    **The budget is a target, not a guarantee.** A landlocked country whose every
    edge is shared has a floor no tolerance gets under: Armenia on the Caucasus
    map settles at ~98 vertices however hard it is pushed, because each arc it
    shares with Georgia, Turkey and Azerbaijan bottoms out separately. Stopping
    at the plateau is right -- erroring there would refuse to build a map over a
    ring nothing can shrink.
    """
    tolerance = 0.0001
    best: Optional[list[tuple[str, Polygon]]] = None
    best_worst: Optional[int] = None
    for _ in range(60):
        result = simplify_shared(pieces, tolerance)
        worst = _worst_ring(result)
        if worst <= max_vertices:
            return result
        if best_worst is None or worst < best_worst:
            best, best_worst = result, worst
        if tolerance > MAX_TOLERANCE_DEGREES:
            break
        tolerance *= 1.4
    assert best is not None
    return best


def _worst_ring(result: list[tuple[str, Polygon]]) -> int:
    return max(
        (len(poly.exterior.coords) - 1) for _, poly in result if not poly.is_empty
    )


def to_xy(
    terrain: object, ring: list[tuple[float, float]]
) -> list[tuple[float, float]]:
    out = []
    for lon, lat in ring:
        p = Point.from_latlng(LatLng(lat, lon), terrain)  # type: ignore[arg-type]
        out.append((p.x, p.y))
    return out


def render_zone(
    args: argparse.Namespace,
    label: str,
    ring_xy: list[tuple[float, float]],
    spawn_xy: tuple[float, float] | None,
) -> list[str]:
    lines = [
        f"  # {label} -- real boundary data via tools/neutral_border_geo.py "
        f"({len(ring_xy)} vertices).",
        f"  - country: {args.country}",
    ]
    if args.overflight:
        # Permits transit: drawn and never enforced, so it spawns nothing and
        # needs no aircraft, origin, floor or SAM.
        lines.append("    overflight: true")
    else:
        if args.airfield:
            lines.append(f"    airfield: {args.airfield}")
        else:
            assert spawn_xy is not None
            lines.append(f"    spawn: [{spawn_xy[0]:.0f}, {spawn_xy[1]:.0f}]")
            lines.append(f"    spawn_alt_ft: {args.spawn_alt_ft}")
        lines.append(f"    aircraft: {args.aircraft}")
        lines.append(f"    floor_ft: {args.floor_ft}")
        lines.append(f"    sam: {'true' if args.sam else 'false'}")
    lines.append("    border:")
    for x, y in ring_xy:
        lines.append(f"      - [{x:.0f}, {y:.0f}]")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("geojson", type=Path, help="Country boundary GeoJSON")
    parser.add_argument("--terrain", required=True, choices=sorted(TERRAINS))
    parser.add_argument(
        "--country", required=True, help='DCS country name, e.g. "Pakistan"'
    )
    parser.add_argument(
        "--airfield", help="Map airbase the alert flight uses (omit for --auto-spawn)"
    )
    parser.add_argument(
        "--auto-spawn",
        action="store_true",
        help="Air-spawn each piece's CAP at its own representative point",
    )
    parser.add_argument("--spawn-alt-ft", type=int, default=20000)
    parser.add_argument(
        "--aircraft", help='pydcs plane id, e.g. "MiG-21Bis" (not for --overflight)'
    )
    parser.add_argument(
        "--overflight",
        action="store_true",
        help="This neutral permits transit: drawn, never enforced, spawns nothing "
        "(and so needs no pydcs country -- the only way to draw a nation DCS "
        "does not model, e.g. Turkmenistan)",
    )
    parser.add_argument("--floor-ft", type=int, default=10000)
    parser.add_argument("--sam", action="store_true")
    parser.add_argument("--max-vertices", type=int, default=56)
    parser.add_argument(
        "--clip",
        nargs=4,
        type=float,
        metavar=("LAT_MIN", "LAT_MAX", "LON_MIN", "LON_MAX"),
        help="Clip the country to the map area. Effectively mandatory.",
    )
    parser.add_argument(
        "--corridor-lon",
        nargs=2,
        type=float,
        metavar=("LON_MIN", "LON_MAX"),
        help="Subtract a north-south lane, leaving the corridor's two walls",
    )
    args = parser.parse_args()

    if args.overflight:
        if args.airfield or args.auto_spawn or args.aircraft:
            raise SystemExit(
                "--overflight spawns nothing: drop --airfield/--auto-spawn/--aircraft."
            )
    else:
        if bool(args.airfield) == bool(args.auto_spawn):
            raise SystemExit("Pass exactly one of --airfield or --auto-spawn.")
        if not args.aircraft:
            raise SystemExit("A neutral that refuses transit needs --aircraft.")

    data = json.loads(args.geojson.read_text(encoding="utf-8"))
    geom: Polygon | MultiPolygon = country_polygon(data)

    if args.clip:
        lat_min, lat_max, lon_min, lon_max = args.clip
        geom = geom.intersection(box(lon_min, lat_min, lon_max, lat_max))
    if args.corridor_lon:
        c_min, c_max = args.corridor_lon
        # The lane is cut full-height; the clip above already bounds it.
        geom = geom.difference(box(c_min, -90, c_max, 90))

    parts = pieces_of(geom)
    if not parts:
        raise SystemExit("Nothing left after clipping — check --clip / --corridor-lon.")

    terrain = TERRAINS[args.terrain]()
    out: list[str] = ["neutral_border_defense:"]
    for index, piece in enumerate(parts):
        ring = simplify_to_budget(piece, args.max_vertices)
        ring_xy = to_xy(terrain, ring)
        spawn_xy = None
        if args.auto_spawn and not args.overflight:
            rep = piece.representative_point()
            spawn_xy = to_xy(terrain, [(rep.x, rep.y)])[0]
        label = args.country
        if len(parts) > 1:
            # Only a corridor cut makes the pieces *walls of a corridor*. A
            # country can also land in several pieces just from the clip (the
            # Tajikistan case), and calling those "of the corridor" is a lie.
            side = "west" if piece.centroid.x < geom.centroid.x else "east"
            qualifier = "of the corridor" if args.corridor_lon else "part"
            label = f"{args.country} ({side} {qualifier})"
        out.extend(render_zone(args, label, ring_xy, spawn_xy))
        if index != len(parts) - 1:
            out.append("")

    print("\n".join(out))


if __name__ == "__main__":
    main()
