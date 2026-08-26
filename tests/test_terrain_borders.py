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

SHIPPED = [
    "Afghanistan",
    "Syria",
    "Caucasus",
    "Iraq",
    "Kola",
    "PersianGulf",
    "Sinai",
    "Falklands",
]


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


def test_the_map_draws_its_own_nation() -> None:
    """The map's host nation is a country like any other.

    It was excluded until 2026-08-26 on the theory that a border round the
    battlefield is noise. That deleted Russia from Kola and Iran from the
    Persian Gulf -- the most relevant border on each of those maps -- and left
    the war itself as the one region with no line on it. What a country's
    airspace means is decided at run time from who holds the control points
    inside it, so the geometry has no business leaving one out.
    """
    hosts = {
        "Afghanistan": "Afghanistan",
        "Syria": "Syria",
        "Iraq": "Iraq",
        "Sinai": "Egypt",
        "Kola": "Russia",
        "PersianGulf": "Iran",
        "Caucasus": "Georgia",
    }
    for terrain, host in hosts.items():
        names = {e["country"] for e in load_terrain_borders(terrain)}
        assert host in names, f"{terrain} does not draw its own nation"


@pytest.mark.parametrize("terrain", SHIPPED)
def test_no_zone_is_a_clip_artifact(terrain: str) -> None:
    """A clip box wider than the map leaves triangles hanging off its edge.

    Sinai first shipped a 3-vertex Saudi sliver of 1,629 km² at lng 37.0-37.5,
    past the map's own 36.61 — real territory, cut into a meaningless wedge by
    the box rather than by a coastline. Bounding vertices by airfield extent
    cannot catch it (the Afghanistan map reaches empty sea at 24.5°N for the
    carrier), so the test is on the shape: a border simplified from a real
    country keeps its corners, an artifact collapses to a few.
    """
    for entry in load_terrain_borders(terrain):
        border = entry["border"]
        area_km2 = (
            abs(
                sum(
                    border[i][0] * border[(i + 1) % len(border)][1]
                    - border[(i + 1) % len(border)][0] * border[i][1]
                    for i in range(len(border))
                )
            )
            / 2
            / 1e6
        )
        assert not (len(border) < 6 and area_km2 < 5000), (
            f"{terrain}/{entry['country']}: {len(border)} vertices over "
            f"{area_km2:.0f} km² reads as a clip artifact, not a border"
        )


def test_an_archipelago_does_not_become_a_dozen_zones() -> None:
    """Every surviving landmass gets its own alert flight, so Tierra del Fuego
    needs an area floor: unfiltered, Chile alone came out as five zones, one of
    them the 1,439 km² Cape Horn group. Real territory, uncontested airspace."""
    zones = load_terrain_borders("Falklands")
    assert len(zones) <= 8, "the Falklands archipelago was not floored"
    by_country: dict[str, int] = {}
    for entry in zones:
        by_country[entry["country"]] = by_country.get(entry["country"], 0) + 1
    for country, count in by_country.items():
        assert count <= 4, f"{country} fragmented into {count} zones"


def test_afghanistans_neighbours_are_all_there() -> None:
    """India is included on measured land share (1.03 %), which the eyeball
    misses; China's Wakhan strip is off the playable area and is not."""
    names = {e["country"] for e in load_terrain_borders("Afghanistan")}
    assert names == {
        "Afghanistan",
        "Pakistan",
        "Iran",
        "Turkmenistan",
        "Uzbekistan",
        "Tajikistan",
        "India",
    }


def test_syria_is_on_the_iraq_map() -> None:
    """The Iraq map's clip reaches lng 52, and Syria's east runs to 42.4.

    It was missing until 2026-08-26 -- not excluded, just never named in the
    tool's --countries list, which is a silent way to lose a border. Iraq's own
    absence made it invisible: the country next to the hole is hard to miss when
    the hole is not there.
    """
    names = {e["country"] for e in load_terrain_borders("Iraq")}
    assert "Syria" in names


def test_no_kola_zone_reaches_across_northern_norway() -> None:
    """Russia's GeoJSON carries a feature spanning 359.8 deg of longitude in a
    0.87 deg latitude band. Merged in, it became a 75,554 km2 Russian claim over
    Finnmark -- a shape with no land under it, on a map where Norway is a real
    zone of its own. The guard is in tools/neutral_border_geo.py; this pins the
    shipped result, because the artifact is invisible in the yaml.
    """
    from dcs.mapping import Point
    from dcs.terrain import Kola

    terrain = Kola()
    for entry in load_terrain_borders("Kola"):
        if entry["country"] != "Russia":
            continue
        lngs = [Point(x, y, terrain).latlng().lng for x, y in entry["border"]]
        assert (
            max(lngs) - min(lngs) < 25.0
        ), f"Russia zone spans {max(lngs) - min(lngs):.1f} deg of longitude"
