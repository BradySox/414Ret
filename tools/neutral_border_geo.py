"""Author campaign ``neutral_border_defense:`` borders from real boundary data (§96).

**The standard (2026-08-24, DM call):** a neutral country's border polygon comes
from real boundary data, never hand-tracing -- and only real-world-georeferenced
maps get the feature (fictional-overlay campaigns are out of scope). Pipeline:
a public-domain country GeoJSON (e.g. Natural Earth or a derivative) ->
shapely simplify to a vertex budget -> ``Point.from_latlng`` -> terrain XY
(the calibrated ``supply_route_geo.py`` machinery, ~1-5 km on Afghanistan) ->
the yaml block pasted into ``resources/campaigns/*.yaml``. The GeoJSON is a
dev-time input read from disk; nothing here runs at campaign or mission time.

Usage:

    python tools/neutral_border_geo.py <country.geojson> --terrain syria \\
        --country Lebanon --airfield Rayak --aircraft MiG-29A \\
        --floor-ft 10000 --sam --max-vertices 56

GeoJSON coordinates are [lon, lat]; DCS terrain XY is pydcs Point.x/.y = DCS
x/z. The polygon's exterior ring is simplified with growing tolerance until it
fits the vertex budget -- a border trigger needs corridor fidelity, not meters.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from dcs.mapping import LatLng, Point
from dcs.terrain.afghanistan import Afghanistan
from dcs.terrain.caucasus import Caucasus
from dcs.terrain.germanycoldwar import GermanyColdWar
from dcs.terrain.iraq import Iraq
from dcs.terrain.kola import Kola
from dcs.terrain.nevada import Nevada
from dcs.terrain.normandy import Normandy
from dcs.terrain.persiangulf import PersianGulf
from dcs.terrain.sinai import Sinai
from dcs.terrain.syria import Syria
from shapely.geometry import Polygon

TERRAINS = {
    "afghanistan": Afghanistan,
    "caucasus": Caucasus,
    "germany": GermanyColdWar,
    "iraq": Iraq,
    "kola": Kola,
    "nevada": Nevada,
    "normandy": Normandy,
    "persiangulf": PersianGulf,
    "sinai": Sinai,
    "syria": Syria,
}


def largest_ring(geometry: dict[str, Any]) -> list[tuple[float, float]]:
    """The exterior ring of the largest polygon, as (lon, lat) pairs.

    Handles Polygon and MultiPolygon; islands and exclaves are dropped -- an
    airspace border wants the mainland ring.
    """
    if geometry["type"] == "Polygon":
        rings = [geometry["coordinates"][0]]
    elif geometry["type"] == "MultiPolygon":
        rings = [poly[0] for poly in geometry["coordinates"]]
    else:
        raise SystemExit(f"Unsupported geometry type: {geometry['type']}")
    largest = max(rings, key=lambda ring: Polygon(ring).area)
    return [(float(lon), float(lat)) for lon, lat in largest]


def simplify_to_budget(
    ring: list[tuple[float, float]], max_vertices: int
) -> list[tuple[float, float]]:
    """Douglas-Peucker with growing tolerance until the ring fits the budget."""
    polygon = Polygon(ring)
    tolerance = 0.001  # degrees, ~100 m
    for _ in range(40):
        simplified = polygon.simplify(tolerance, preserve_topology=True)
        coords = list(simplified.exterior.coords)[:-1]  # drop the closing dup
        if len(coords) <= max_vertices:
            return [(lon, lat) for lon, lat in coords]
        tolerance *= 1.5
    raise SystemExit("Could not simplify the ring to the vertex budget.")


def render(args: argparse.Namespace, verts_xy: list[tuple[float, float]]) -> str:
    lines = [
        "neutral_border_defense:",
        f"  # {args.country} border traced from real boundary data by",
        f"  # tools/neutral_border_geo.py ({len(verts_xy)} vertices).",
        f"  - country: {args.country}",
        f"    airfield: {args.airfield}",
        f"    aircraft: {args.aircraft}",
        f"    floor_ft: {args.floor_ft}",
        f"    sam: {'true' if args.sam else 'false'}",
        "    border:",
    ]
    for x, y in verts_xy:
        lines.append(f"      - [{x:.0f}, {y:.0f}]")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("geojson", type=Path, help="Country boundary GeoJSON")
    parser.add_argument("--terrain", required=True, choices=sorted(TERRAINS))
    parser.add_argument(
        "--country", required=True, help='DCS country name, e.g. "Lebanon"'
    )
    parser.add_argument(
        "--airfield", required=True, help="Map airbase the alert flight uses"
    )
    parser.add_argument(
        "--aircraft", required=True, help='pydcs plane id, e.g. "MiG-29A"'
    )
    parser.add_argument("--floor-ft", type=int, default=10000)
    parser.add_argument("--sam", action="store_true")
    parser.add_argument("--max-vertices", type=int, default=56)
    args = parser.parse_args()

    data = json.loads(args.geojson.read_text(encoding="utf-8"))
    if data.get("type") == "FeatureCollection":
        geometry = data["features"][0]["geometry"]
    elif data.get("type") == "Feature":
        geometry = data["geometry"]
    else:
        geometry = data

    ring = largest_ring(geometry)
    simplified = simplify_to_budget(ring, args.max_vertices)

    terrain = TERRAINS[args.terrain]()
    verts_xy = []
    for lon, lat in simplified:
        p = Point.from_latlng(LatLng(lat, lon), terrain)  # type: ignore[arg-type]
        verts_xy.append((p.x, p.y))

    print(render(args, verts_xy))


if __name__ == "__main__":
    main()
