"""Every theater has a distinct, readable name for the map list.

The New Game campaign list groups by the campaign's ``theater:`` key, which is a
directory name. That put ``MarianaIslands`` next to ``MarianasWWII`` in the Map
filter -- two maps of the same islands, adjacent, and near-impossible to tell
apart at a glance. The list now labels by ``TheaterLoader.display_name``.

Two of these names were pydcs terrain ids leaking into the UI, ``GermanyCW`` and
``SinaiMap``. Renaming them needed an explicit ``pydcs_name:`` first, because the
loader falls back to ``name`` for the terrain lookup -- rename without it and the
theater raises ``KeyError`` on load instead of just looking wrong.
"""

from __future__ import annotations

from collections import Counter

import pytest

from game.theater.conflicttheater import THEATER_RESOURCE_DIR
from game.theater.theaterloader import TheaterLoader

THEATER_DIRS = sorted(d.name for d in THEATER_RESOURCE_DIR.iterdir() if d.is_dir())


def test_there_are_theaters_to_check() -> None:
    assert len(THEATER_DIRS) >= 14


@pytest.mark.parametrize("theater_dir", THEATER_DIRS)
def test_every_theater_still_loads(theater_dir: str) -> None:
    """Guards the rename: `name` is the terrain lookup unless `pydcs_name` is
    set."""
    assert TheaterLoader(theater_dir).load() is not None


@pytest.mark.parametrize("theater_dir", THEATER_DIRS)
def test_display_name_is_readable(theater_dir: str) -> None:
    name = TheaterLoader(theater_dir).display_name
    assert name and name.strip() == name
    # A name that is only a run-together identifier is what this file exists to
    # prevent. Anything multi-word is fine; a single word must at least be a real
    # word rather than CamelCase or a "Map"/"CW" suffix.
    if " " not in name:
        assert not name.endswith("Map"), f"{theater_dir}: {name!r} is an identifier"
        assert (
            name == name.capitalize() or name.isupper()
        ), f"{theater_dir}: {name!r} looks like a pydcs id, not a display name"


def test_display_names_are_unique() -> None:
    """Two maps sharing a label is the bug this file is about."""
    names = [TheaterLoader(d).display_name for d in THEATER_DIRS]
    dupes = [n for n, count in Counter(names).items() if count > 1]
    assert not dupes, f"theaters share a display name: {dupes}"


def test_the_two_marianas_are_tellable_apart() -> None:
    modern = TheaterLoader("marianaislands").display_name
    wwii = TheaterLoader("marianaswwii").display_name
    assert modern != wwii
    # Not just different -- different enough that neither is a prefix of the
    # other, which is how "MarianaIslands"/"MarianasWWII" defeated the eye.
    assert not wwii.startswith(modern) and not modern.startswith(wwii)


def test_display_name_does_not_load_the_landmap() -> None:
    """It is read for every entry when the map list is built; loading theaters
    there would pull a landmap of up to 2 MB apiece."""
    loader = TheaterLoader("caucasus")
    assert loader.display_name == "Caucasus"
    # A landmap would have been read through this attribute had load() run.
    assert not hasattr(loader, "landmap")
