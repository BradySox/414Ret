"""Serves locally installed map-tile pyramids to the client map.

Tilesets live under ``persistency.map_tiles_dir()`` (one folder per set:
``<name>/{z}/{x}/{y}.png`` plus a ``tileset.json`` sidecar) and are produced
offline by ``tools/tile_geotiff.py``. They are purely local content — never
bundled with the app — so the listing endpoint is how the client discovers
whether any extra base layers exist at all. Game-independent: no campaign
needs to be loaded.
"""

from __future__ import annotations

import json
import logging
import re

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from game import persistency
from .models import TileSetJs

logger = logging.getLogger(__name__)

router: APIRouter = APIRouter(prefix="/map-tiles")

# Tileset folder names are path components in tile URLs; restricting them to
# this alphabet is what makes the {name} path parameter traversal-safe.
_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


@router.get("/", operation_id="list_map_tile_sets", response_model=list[TileSetJs])
def list_tile_sets() -> list[TileSetJs]:
    sets = []
    for meta_path in sorted(persistency.map_tiles_dir().glob("*/tileset.json")):
        name = meta_path.parent.name
        if not _NAME_RE.match(name):
            logger.warning("Ignoring map tileset with unusable name: %s", name)
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            sets.append(
                TileSetJs(
                    name=name,
                    display_name=str(meta.get("displayName") or name),
                    min_zoom=int(meta["minZoom"]),
                    max_zoom=int(meta["maxZoom"]),
                    bounds=[[float(c) for c in corner] for corner in meta["bounds"]],
                    attribution=str(meta.get("attribution", "")),
                )
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.warning("Ignoring malformed map tileset %s: %s", name, exc)
    return sets


@router.get(
    "/{name}/{z}/{x}/{y}.png",
    operation_id="get_map_tile",
    response_class=FileResponse,
)
def get_tile(name: str, z: int, x: int, y: int) -> FileResponse:
    # z/x/y are typed ints, and the name alphabet excludes path separators and
    # dots, so no component can escape the tileset root.
    if not _NAME_RE.match(name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    path = persistency.map_tiles_dir() / name / str(z) / str(x) / f"{y}.png"
    if not path.is_file():
        # Normal for tiles outside the pyramid's coverage; Leaflet just leaves
        # that cell empty.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return FileResponse(path, media_type="image/png")
