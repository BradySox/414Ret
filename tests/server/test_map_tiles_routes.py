"""The /map-tiles routes list and serve locally installed tile pyramids.

Tilesets are plain folders under ``persistency.map_tiles_dir()`` written by
``tools/tile_geotiff.py``; the routes are game-independent, so the tests only
need ``persistency.setup`` pointed at a temp tree.
"""

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from game import persistency
from game.server.maptiles.routes import get_tile, list_tile_sets

META = {
    "displayName": "DCS Caucasus chart",
    "minZoom": 5,
    "maxZoom": 12,
    "bounds": [[40.644, 36.247], [45.613, 45.482]],
    "attribution": "Flappie",
}


@pytest.fixture
def tiles_root(tmp_path: Path) -> Path:
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16880)
    return persistency.map_tiles_dir()


def make_tileset(root: Path, name: str) -> Path:
    tileset = root / name
    tile = tileset / "7" / "78" / "47.png"
    tile.parent.mkdir(parents=True)
    tile.write_bytes(b"\x89PNG fake tile")
    (tileset / "tileset.json").write_text(json.dumps(META))
    return tileset


def test_empty_dir_lists_nothing(tiles_root: Path) -> None:
    assert list_tile_sets() == []


def test_lists_installed_tileset_with_meta(tiles_root: Path) -> None:
    make_tileset(tiles_root, "caucasus_flappie")
    (sets,) = list_tile_sets()
    assert sets.name == "caucasus_flappie"
    assert sets.display_name == "DCS Caucasus chart"
    assert sets.min_zoom == 5
    assert sets.max_zoom == 12
    assert sets.bounds == [[40.644, 36.247], [45.613, 45.482]]
    assert sets.attribution == "Flappie"


def test_malformed_meta_is_skipped_not_fatal(tiles_root: Path) -> None:
    make_tileset(tiles_root, "good_set")
    bad = tiles_root / "bad_set"
    bad.mkdir()
    (bad / "tileset.json").write_text("{ not json")
    missing_keys = tiles_root / "empty_meta"
    missing_keys.mkdir()
    (missing_keys / "tileset.json").write_text("{}")
    names = [s.name for s in list_tile_sets()]
    assert names == ["good_set"]


def test_serves_existing_tile(tiles_root: Path) -> None:
    tileset = make_tileset(tiles_root, "caucasus_flappie")
    response = get_tile("caucasus_flappie", 7, 78, 47)
    assert Path(response.path) == tileset / "7" / "78" / "47.png"
    assert response.media_type == "image/png"


def test_missing_tile_404s(tiles_root: Path) -> None:
    make_tileset(tiles_root, "caucasus_flappie")
    with pytest.raises(HTTPException) as exc:
        get_tile("caucasus_flappie", 7, 78, 48)
    assert exc.value.status_code == 404


def test_traversal_shaped_name_404s(tiles_root: Path) -> None:
    make_tileset(tiles_root, "caucasus_flappie")
    for name in ("..", "a/../b", "a\\b", "set.name"):
        with pytest.raises(HTTPException) as exc:
            get_tile(name, 7, 78, 47)
        assert exc.value.status_code == 404
