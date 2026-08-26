"""Shipped per-terrain borders (§96): the automagic half.

Borders are a property of the map, so a campaign that authors none still gets
them. 52 of the 54 campaigns on real-world maps author none, which is the whole
reason this exists.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from game.theater.neutralborder import NeutralBorderZone
from game.theater.terrainborders import load_terrain_borders

SHIPPED = ["Afghanistan", "Syria", "Caucasus", "Iraq", "Kola", "PersianGulf"]


@pytest.mark.parametrize("terrain", SHIPPED)
def test_every_shipped_terrain_parses(terrain: str) -> None:
    entries = load_terrain_borders(terrain)
    assert entries, f"{terrain} ships no border zones"
    for entry in entries:
        zone = NeutralBorderZone.from_yaml(entry)
        assert zone is not None, f"{terrain}: {entry.get('country')} failed to parse"
        assert len(zone.border) >= 3
        # Geometry and an origin only -- posture and airframe come from the
        # dated table, so a terrain file must never pin an era-specific value.
        assert zone.aircraft is None, f"{terrain}: {zone.country} pins an airframe"
        assert zone.overflight_override is None
        assert zone.posture_override is None
        assert (zone.airfield is None) != (zone.spawn is None), "exactly one origin"


def test_terrain_name_matching_is_forgiving() -> None:
    """The pydcs terrain name is what callers have; the filename is lowercase."""
    assert load_terrain_borders("Afghanistan") == load_terrain_borders("afghanistan")


def test_a_terrain_with_no_file_is_empty_not_an_error() -> None:
    """Nevada and the Marianas have no foreign border to draw."""
    assert load_terrain_borders("Nevada") == []


def test_an_unreadable_directory_costs_the_borders_not_the_campaign() -> None:
    assert load_terrain_borders("Afghanistan", Path("does/not/exist")) == []


def test_the_host_nation_is_absent() -> None:
    """A border drawn around the whole battlefield is noise."""
    hosts = {
        "Afghanistan": "Afghanistan",
        "Syria": "Syria",
        "Iraq": "Iraq",
    }
    for terrain, host in hosts.items():
        names = {e["country"] for e in load_terrain_borders(terrain)}
        assert host not in names, f"{terrain} draws its own host nation"


def test_afghanistans_neighbours_are_all_there() -> None:
    """India is included on measured land share (1.03 %), which the eyeball
    misses; China's Wakhan strip is off the playable area and is not."""
    names = {e["country"] for e in load_terrain_borders("Afghanistan")}
    assert names == {
        "Pakistan",
        "Iran",
        "Turkmenistan",
        "Uzbekistan",
        "Tajikistan",
        "India",
    }
