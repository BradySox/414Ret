from __future__ import annotations

from pydantic import BaseModel


class TileSetJs(BaseModel):
    """A locally installed XYZ tile pyramid offered to the map as a base layer.

    Mirrors the ``tileset.json`` sidecar written by ``tools/tile_geotiff.py``.
    ``bounds`` is Leaflet corner order: ``[[south, west], [north, east]]``.
    """

    name: str
    display_name: str
    min_zoom: int
    max_zoom: int
    bounds: list[list[float]]
    attribution: str

    class Config:
        title = "TileSet"
