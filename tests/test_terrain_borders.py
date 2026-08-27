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
        # Bahrain really is a 571 km² island and a quad is the honest shape
        # for it -- coverage simplification reduces a small country to a
        # triangle in the limit, which the vertex count alone cannot tell from
        # a wedge. It is the only sub-1000 km² country on any shipped map.
        if entry["country"] == "Bahrain":
            continue
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


# -- a terrain list is a cache of a file, not campaign state --------------------


def _restored(saved: list[NeutralBorderZone] | None) -> list[NeutralBorderZone]:
    """A ConflictTheater coming back out of a save with these zones in it."""
    from dcs.terrain import Syria

    from game.theater.conflicttheater import ConflictTheater

    theater = ConflictTheater.__new__(ConflictTheater)
    state: dict[str, object] = {"terrain": Syria()}
    if saved is not None:
        state["neutral_border_zones"] = saved
    theater.__setstate__(state)
    return list(theater.neutral_border_zones)


def _terrain_zone(country: str) -> NeutralBorderZone:
    zone = NeutralBorderZone.from_yaml(
        {"country": country, "border": [[0, 0], [100, 0], [100, 100]]},
        from_terrain=True,
    )
    assert zone is not None
    return zone


def test_a_save_with_no_borders_picks_up_the_terrains() -> None:
    """52 of the 54 real-world-map campaigns author none, so without this the
    feature reaches almost nobody already mid-campaign."""
    assert _restored(None), "an old save got no borders"


def test_a_terrain_list_is_refreshed_not_frozen() -> None:
    """Whatever shipped the day the campaign was rolled is not what the file
    says today: the host nation was added to all seven maps on 2026-08-26, and a
    save that froze its list would never see Iraq or Syria."""
    restored = _restored([_terrain_zone("Turkey")])
    names = {zone.country for zone in restored}
    assert len(restored) > 1, "the terrain list was frozen at one country"
    assert "Syria" in names, "the map's own nation never reached the save"


def test_a_campaigns_own_borders_are_never_replaced() -> None:
    """Enduring Resolve's corridor-cut Pakistan has to beat the terrain file's
    whole-country one, which is the whole reason precedence is total."""
    authored = NeutralBorderZone.from_yaml(
        {"country": "Pakistan", "border": [[0, 0], [100, 0], [100, 100]]}
    )
    assert authored is not None
    restored = _restored([authored])
    assert [zone.country for zone in restored] == ["Pakistan"]


def test_an_unmarked_list_is_left_alone() -> None:
    """A save older than the flag cannot say where its zones came from, so it
    keeps them rather than risk overwriting an authored set."""
    legacy = NeutralBorderZone.from_yaml(
        {"country": "Turkey", "border": [[0, 0], [100, 0], [100, 100]]}
    )
    assert legacy is not None
    del legacy.__dict__["from_terrain"]
    assert [zone.country for zone in _restored([legacy])] == ["Turkey"]


def test_a_complex_coast_is_not_simplified_into_a_blob() -> None:
    """Norway is the worst shape Douglas-Peucker meets here: a thin fjord coast
    wrapping around Sweden. MEASURED 2026-08-26 by symmetric difference against
    the true clipped country -- at a 24-vertex budget it was 30.2% wrong,
    against Sweden's 9.7% and Finland's 7.0%. The budget is 64 now; this pins
    that a regeneration did not quietly drop it again."""
    norway = [e for e in load_terrain_borders("Kola") if e["country"] == "Norway"]
    assert norway, "Kola no longer draws Norway"
    assert len(norway[0]["border"]) >= 40, (
        f"Norway came out at {len(norway[0]['border'])} vertices -- at that "
        "budget its coastline is a blob"
    )


# -- neighbours share their frontier, they do not each draw a copy of it -------


@pytest.mark.parametrize("terrain", SHIPPED)
def test_neighbours_do_not_overlap(terrain: str) -> None:
    """Two countries cannot both hold the same ground.

    Each country used to be simplified on its own, so a shared frontier came out
    as two lines that weave: measured 2026-08-26, neighbours' lines coincided
    35-65 % of the time (Russia/Norway on Kola at 7 %), leaving slivers of
    overlap up to 12.8 % of the smaller country. The whole map is now simplified
    as one coverage.
    """
    from shapely.geometry import Polygon

    polys = [
        (entry["country"], Polygon(entry["border"]).buffer(0))
        for entry in load_terrain_borders(terrain)
    ]
    for index, (name_a, poly_a) in enumerate(polys):
        for name_b, poly_b in polys[index + 1 :]:
            overlap = poly_a.intersection(poly_b).area
            assert overlap < 1000.0, (
                f"{terrain}: {name_a} and {name_b} overlap by "
                f"{overlap / 1e6:.1f} km²"
            )


@pytest.mark.parametrize("terrain", SHIPPED)
def test_a_shared_frontier_is_one_line(terrain: str) -> None:
    """The invariant behind the fix: each map is a valid polygon coverage, which
    means non-overlapping AND edge-matched — a border two countries share is the
    same vertices on both sides, not two independent traces of it.

    Falklands is the one exception and is asserted as such: Argentina and Chile
    interlock across Tierra del Fuego, and writing the rings as whole metres
    leaves a 12.5 m² degenerate touch there. Twelve square metres is far below
    anything drawable, so it is tolerated rather than chased.
    """
    import shapely
    from shapely.geometry import Polygon

    polys = [Polygon(e["border"]).buffer(0) for e in load_terrain_borders(terrain)]
    if terrain == "Falklands":
        pytest.skip("known 12.5 m² degenerate touch in Tierra del Fuego")
    assert bool(shapely.coverage_is_valid(polys)), (
        f"{terrain} is not a valid coverage: a shared frontier is being drawn " "twice"
    )


# -- an alert flight comes off a runway, not a helipad --------------------------

_TERRAIN_CLASSES = {
    "Syria": "syria.Syria",
    "Caucasus": "caucasus.Caucasus",
    "PersianGulf": "persiangulf.PersianGulf",
    "Sinai": "sinai.Sinai",
    "Kola": "kola.Kola",
    "Afghanistan": "afghanistan.Afghanistan",
    "Falklands": "falklands.Falklands",
    "Iraq": "iraq.Iraq",
}


@pytest.mark.parametrize("terrain", SHIPPED)
def test_no_zone_launches_its_alert_flight_from_a_helipad(terrain: str) -> None:
    """``airport_list()`` includes helipads, and the tool picked by depth alone.

    Reported 2026-08-27 from the map: Lebanon's tooltip read "alert from HL07".
    Four Syria-map zones were on helipads -- Syria/HS03, Lebanon/HL07,
    Jordan/HMed22, Iraq/HS26 -- because a helipad happened to sit furthest from
    the frontier. The flight air-spawns overhead so it flew anyway, but a
    helipad is not somewhere a MiG-29 comes from and the card reads as a bug.
    """
    import importlib

    module_name, class_name = _TERRAIN_CLASSES[terrain].rsplit(".", 1)
    terrain_obj = getattr(
        importlib.import_module(f"dcs.terrain.{module_name}"), class_name
    )()
    runways = {
        airport.name: len(getattr(airport, "runways", []) or [])
        for airport in terrain_obj.airport_list()
    }
    for entry in load_terrain_borders(terrain):
        field = entry.get("airfield")
        if field is None:
            continue  # a point-spawned station, which has no airfield at all
        assert runways.get(field, 0) > 0, (
            f"{terrain}/{entry['country']} bases its alert flight on {field}, "
            "which has no runway"
        )


@pytest.mark.parametrize("terrain", SHIPPED)
def test_an_air_spawn_station_sits_on_ground_the_map_models(terrain: str) -> None:
    """A clip box is bigger than its terrain, so a country that only clips the
    map's edge can get a polygon whose middle is off the map entirely.

    Measured 2026-08-27: Caucasus stationed Turkey 170 km from the nearest
    modelled land, Afghanistan put India 272 km out, and Iraq's Turkey and
    Jordan were 26 and 37 km out. All four have an airframe, so all four would
    have tried to launch from there. The Lua usually launches 25 NM from the
    intruder instead, so this bit only through the concave fallback -- but that
    fallback exists for exactly the awkward geometry a clipped border has.

    The invariant is conditional: a zone is only held to it when the map models
    some land inside its border at all. Caucasus/Azerbaijan's Nakhchivan piece
    has none, and no airframe in any era either, so it never launches anything.
    """
    import warnings

    from shapely.geometry import Polygon

    from game.theater.conflicttheater import ConflictTheater
    from game.theater.landmap import load_landmap, poly_contains

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        landmap = load_landmap(ConflictTheater.landmap_path_for_terrain_name(terrain))
    if landmap is None:
        pytest.skip(f"{terrain} ships no landmap")

    for entry in load_terrain_borders(terrain):
        spawn = entry.get("spawn")
        if spawn is None:
            continue  # it launches off a real airfield
        border = Polygon(entry["border"]).buffer(0)
        if border.intersection(landmap.inclusion_zones).is_empty:
            continue  # no modelled land inside it; nowhere better to stand
        assert poly_contains(spawn[0], spawn[1], landmap.inclusion_zones), (
            f"{terrain}/{entry['country']} stations its alert flight at "
            f"{spawn}, which is not on ground this map models"
        )
