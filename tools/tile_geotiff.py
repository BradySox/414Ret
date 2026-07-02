"""Slice a Web-Mercator GeoTIFF into an XYZ tile pyramid for the client map.

Reads a GeoTIFF already projected in EPSG:3857 (Web Mercator / Pseudo-Mercator
— e.g. Flappie's "accurate DCS Caucasus map"), and writes a standard
``{z}/{x}/{y}.png`` tile tree plus a ``tileset.json`` sidecar describing the
set (display name, zoom range, WGS84 bounds, attribution). The output folder
is what the ``/map-tiles`` server routes expose to the Leaflet client as a
selectable base layer.

Pure Pillow — no GDAL/rasterio dependency. The georeference is taken from the
TIFF's ModelPixelScale + ModelTiepoint tags; anything not tagged as EPSG:3857
is rejected (reprojection is out of scope for this tool).

Usage:
    python tools/tile_geotiff.py "<map.tiff>" "<out_dir>" \
        --display-name "DCS Caucasus chart" --attribution "Flappie v1.0"

The default output resolution ceiling is the finest standard zoom that does
not oversample the source by more than one level; override with --max-zoom.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Iterator, Optional, Tuple

from PIL import Image

# Web Mercator world half-extent in projected metres. The world spans
# [-ORIGIN, ORIGIN] on both axes at every zoom level.
_MERCATOR_ORIGIN = 20037508.342789244
_TILE_PX = 256
_EARTH_RADIUS_M = 6378137.0

# GeoTIFF tag ids.
_TAG_MODEL_PIXEL_SCALE = 33550
_TAG_MODEL_TIEPOINT = 33922
_TAG_GEO_KEY_DIRECTORY = 34735

# GeoKey id for the projected CRS code, and the accepted Web Mercator codes.
_GEOKEY_PROJECTED_CRS = 3072
_WEB_MERCATOR_CODES = {3857, 900913, 3785}


class Georeference:
    """Affine north-up georeference: model = origin + pixel * scale."""

    def __init__(self, x0: float, y0: float, scale_x: float, scale_y: float):
        self.x0 = x0  # mercator X of the left edge of pixel column 0
        self.y0 = y0  # mercator Y of the top edge of pixel row 0
        self.scale_x = scale_x
        self.scale_y = scale_y

    def pixel_for_mercator(self, mx: float, my: float) -> Tuple[float, float]:
        return (mx - self.x0) / self.scale_x, (self.y0 - my) / self.scale_y

    def mercator_bounds(
        self, width: int, height: int
    ) -> Tuple[float, float, float, float]:
        """(west, south, east, north) in mercator metres."""
        return (
            self.x0,
            self.y0 - height * self.scale_y,
            self.x0 + width * self.scale_x,
            self.y0,
        )


def _read_georeference(im: Image.Image) -> Georeference:
    tags = im.tag_v2
    if _TAG_GEO_KEY_DIRECTORY in tags:
        keys = tags[_TAG_GEO_KEY_DIRECTORY]
        # GeoKeyDirectory is a flat list of 4-value records after the header.
        crs: Optional[int] = None
        for i in range(4, len(keys) - 3, 4):
            if keys[i] == _GEOKEY_PROJECTED_CRS:
                crs = int(keys[i + 3])
        if crs is not None and crs not in _WEB_MERCATOR_CODES:
            raise SystemExit(
                f"GeoTIFF is projected as EPSG:{crs}, not Web Mercator "
                "(EPSG:3857); reprojection is out of scope for this tool."
            )
    if _TAG_MODEL_PIXEL_SCALE not in tags or _TAG_MODEL_TIEPOINT not in tags:
        raise SystemExit(
            "GeoTIFF is missing ModelPixelScale/ModelTiepoint tags; cannot "
            "derive the georeference."
        )
    scale_x, scale_y = tags[_TAG_MODEL_PIXEL_SCALE][0], tags[_TAG_MODEL_PIXEL_SCALE][1]
    tie = tags[_TAG_MODEL_TIEPOINT]
    # Tiepoint maps raster (i, j) to model (X, Y); normalize to pixel (0, 0).
    i, j, _, tie_x, tie_y = tie[0], tie[1], tie[2], tie[3], tie[4]
    return Georeference(tie_x - i * scale_x, tie_y + j * scale_y, scale_x, scale_y)


def _mercator_to_lat_lon(mx: float, my: float) -> Tuple[float, float]:
    lon = math.degrees(mx / _EARTH_RADIUS_M)
    lat = math.degrees(2.0 * math.atan(math.exp(my / _EARTH_RADIUS_M)) - math.pi / 2.0)
    return lat, lon


def _zoom_resolution(z: int) -> float:
    """Mercator metres per pixel at zoom ``z``."""
    return 2.0 * _MERCATOR_ORIGIN / (_TILE_PX * (2**z))


def _native_zoom(scale: float) -> int:
    """Finest standard zoom at least as fine as the source resolution."""
    return max(0, math.ceil(math.log2(2.0 * _MERCATOR_ORIGIN / (_TILE_PX * scale))))


def _tile_mercator_bounds(z: int, x: int, y: int) -> Tuple[float, float, float, float]:
    """(west, south, east, north) of tile (z, x, y) in mercator metres."""
    span = 2.0 * _MERCATOR_ORIGIN / (2**z)
    west = -_MERCATOR_ORIGIN + x * span
    north = _MERCATOR_ORIGIN - y * span
    return west, north - span, west + span, north


def _tile_range(
    geo: Georeference, width: int, height: int, z: int
) -> Tuple[range, range]:
    west, south, east, north = geo.mercator_bounds(width, height)
    span = 2.0 * _MERCATOR_ORIGIN / (2**z)
    x0 = int(math.floor((west + _MERCATOR_ORIGIN) / span))
    x1 = int(math.floor((east + _MERCATOR_ORIGIN) / span - 1e-9))
    y0 = int(math.floor((_MERCATOR_ORIGIN - north) / span))
    y1 = int(math.floor((_MERCATOR_ORIGIN - south) / span - 1e-9))
    n = 2**z
    return range(max(0, x0), min(n - 1, x1) + 1), range(max(0, y0), min(n - 1, y1) + 1)


def _render_tile(
    im: Image.Image, geo: Georeference, z: int, x: int, y: int
) -> Optional[Image.Image]:
    """Resample the source onto tile (z, x, y); None if fully outside."""
    west, south, east, north = _tile_mercator_bounds(z, x, y)
    sx0, sy0 = geo.pixel_for_mercator(west, north)
    sx1, sy1 = geo.pixel_for_mercator(east, south)
    # Intersect the source box with the raster.
    cx0, cy0 = max(sx0, 0.0), max(sy0, 0.0)
    cx1, cy1 = min(sx1, float(im.width)), min(sy1, float(im.height))
    if cx1 - cx0 < 1e-9 or cy1 - cy0 < 1e-9:
        return None
    # Where the clipped source box lands within the 256px tile.
    px_per_src_x = _TILE_PX / (sx1 - sx0)
    px_per_src_y = _TILE_PX / (sy1 - sy0)
    dx0 = int(round((cx0 - sx0) * px_per_src_x))
    dy0 = int(round((cy0 - sy0) * px_per_src_y))
    dx1 = int(round((cx1 - sx0) * px_per_src_x))
    dy1 = int(round((cy1 - sy0) * px_per_src_y))
    dw, dh = dx1 - dx0, dy1 - dy0
    if dw < 1 or dh < 1:
        return None
    patch = im.resize((dw, dh), Image.Resampling.LANCZOS, box=(cx0, cy0, cx1, cy1))
    if dw == _TILE_PX and dh == _TILE_PX:
        return patch
    tile = Image.new("RGBA", (_TILE_PX, _TILE_PX), (0, 0, 0, 0))
    tile.paste(patch, (dx0, dy0))
    return tile


def _iter_tiles(
    geo: Georeference, width: int, height: int, min_zoom: int, max_zoom: int
) -> Iterator[Tuple[int, int, int]]:
    for z in range(min_zoom, max_zoom + 1):
        xs, ys = _tile_range(geo, width, height, z)
        for x in xs:
            for y in ys:
                yield z, x, y


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("geotiff", type=Path, help="Source EPSG:3857 GeoTIFF")
    parser.add_argument("out_dir", type=Path, help="Tileset output directory")
    parser.add_argument("--display-name", default=None, help="Base-layer label")
    parser.add_argument("--attribution", default="", help="Leaflet attribution line")
    parser.add_argument("--min-zoom", type=int, default=5)
    parser.add_argument(
        "--max-zoom",
        type=int,
        default=None,
        help="Finest zoom to emit (default: the source's native resolution)",
    )
    args = parser.parse_args()

    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(args.geotiff)
    geo = _read_georeference(im)
    im = im.convert("RGBA")
    max_zoom = args.max_zoom if args.max_zoom is not None else _native_zoom(geo.scale_x)
    min_zoom = min(args.min_zoom, max_zoom)

    west, south, east, north = geo.mercator_bounds(im.width, im.height)
    lat_s, lon_w = _mercator_to_lat_lon(west, south)
    lat_n, lon_e = _mercator_to_lat_lon(east, north)
    total = sum(
        len(xs) * len(ys)
        for z in range(min_zoom, max_zoom + 1)
        for xs, ys in [_tile_range(geo, im.width, im.height, z)]
    )
    print(f"{args.geotiff.name}: {im.width}x{im.height} @ {geo.scale_x:.2f} m/px")
    print(f"zoom {min_zoom}..{max_zoom}, ~{total} tiles -> {args.out_dir}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    done = 0
    start = time.monotonic()
    for z, x, y in _iter_tiles(geo, im.width, im.height, min_zoom, max_zoom):
        tile = _render_tile(im, geo, z, x, y)
        if tile is None:
            continue
        path = args.out_dir / str(z) / str(x) / f"{y}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        tile.save(path, "PNG")
        done += 1
        if done % 500 == 0:
            rate = done / (time.monotonic() - start)
            print(f"  {done}/{total} tiles ({rate:.0f}/s)", flush=True)

    meta = {
        "displayName": args.display_name or args.geotiff.stem,
        "minZoom": min_zoom,
        "maxZoom": max_zoom,
        # Leaflet LatLngBounds corner order: [[south, west], [north, east]].
        "bounds": [[lat_s, lon_w], [lat_n, lon_e]],
        "attribution": args.attribution,
    }
    (args.out_dir / "tileset.json").write_text(json.dumps(meta, indent=2))
    print(f"done: {done} tiles in {time.monotonic() - start:.0f}s")


if __name__ == "__main__":
    sys.exit(main())
