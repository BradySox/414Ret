# game/missiongenerator/kneeboard_recon/tests/test_gif_georef.py
"""Guards on the theater-raster georeference.

Two jobs. First, keep the coverage rects tied to their provenance: each is
re-derived here from the two reference airports the pre-2021 Qt map used, so a
typo'd metre in the table fails rather than quietly shifting the imagery under
the symbology. Second, pin the counter-evidence — ``Terrain.bounds`` does not
bound the map — so nobody reaches for it again.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pytest
from PIL import Image
from dcs.terrain.terrain import Terrain
from dcs.terrain import Caucasus, Nevada, Normandy, PersianGulf, Syria

from game.missiongenerator.kneeboard_recon.extent import MapExtent
from game.missiongenerator.kneeboard_recon.gif_georef import (
    COVERAGE,
    WorldRect,
    coverage_for,
)

_RESOURCES = Path(__file__).resolve().parents[4] / "resources"

# The georeference authored for these same rasters by the pre-2021 Qt map,
# lifted from ``git show 30f6220c3^:game/theater/conflicttheater.py``. Each
# entry is (terrain, gif filename, (airport, pixel column, pixel row) x2).
# Image coordinates originate top-left: column tracks DCS y (east), row tracks
# DCS x (north, increasing downward).
REFERENCE_POINTS = [
    (Caucasus, "caumap.gif", ("Gelendzhik", 176, 298), ("Batumi", 1307, 1205)),
    (Nevada, "nevada.gif", ("Mina", 252, 295), ("Laughlin", 844, 909)),
    (
        Normandy,
        "normandy.gif",
        ("Needs Oar Point", 515, 329),
        ("Evreux", 2029, 1709),
    ),
    (
        PersianGulf,
        "persiangulf.gif",
        ("Jiroft", 1692, 1343),
        ("Liwa AFB", 358, 3238),
    ),
    (Syria, "syria.gif", ("Eyn Shemer", 564, 1289), ("Tabqa", 1329, 491)),
]


def _rect_from_reference_points(
    terrain: Terrain,
    image_size: Tuple[int, int],
    a: Tuple[str, int, int],
    b: Tuple[str, int, int],
) -> WorldRect:
    """Solve the two-point affine and invert it onto the whole image."""
    width, height = image_size
    name_a, col_a, row_a = a
    name_b, col_b, row_b = b
    pos_a = terrain.airports[name_a].position
    pos_b = terrain.airports[name_b].position
    cols_per_m = (col_b - col_a) / (pos_b.y - pos_a.y)
    rows_per_m = (row_b - row_a) / (pos_b.x - pos_a.x)
    y_at_0 = pos_a.y + (0 - col_a) / cols_per_m
    y_at_w = pos_a.y + (width - col_a) / cols_per_m
    x_at_0 = pos_a.x + (0 - row_a) / rows_per_m
    x_at_h = pos_a.x + (height - row_a) / rows_per_m
    return WorldRect(
        min_x=min(x_at_0, x_at_h),
        max_x=max(x_at_0, x_at_h),
        min_y=min(y_at_0, y_at_w),
        max_y=max(y_at_0, y_at_w),
    )


@pytest.mark.parametrize(
    "terrain_cls,gif_name,ref_a,ref_b",
    REFERENCE_POINTS,
    ids=[spec[0].__name__ for spec in REFERENCE_POINTS],
)
def test_coverage_rect_matches_its_reference_points(
    terrain_cls: type,
    gif_name: str,
    ref_a: Tuple[str, int, int],
    ref_b: Tuple[str, int, int],
) -> None:
    """Every shipped rect re-derives from the airports it was measured on."""
    terrain = terrain_cls()
    coverage = COVERAGE[terrain.name]
    derived = _rect_from_reference_points(terrain, coverage.image_size, ref_a, ref_b)
    for axis in ("min_x", "max_x", "min_y", "max_y"):
        assert getattr(coverage.rect, axis) == pytest.approx(
            getattr(derived, axis), abs=1.0
        ), f"{terrain.name}.{axis} drifted from its reference points"


@pytest.mark.parametrize(
    "terrain_cls,gif_name,ref_a,ref_b",
    REFERENCE_POINTS,
    ids=[spec[0].__name__ for spec in REFERENCE_POINTS],
)
def test_recorded_image_size_matches_the_shipped_raster(
    terrain_cls: type,
    gif_name: str,
    ref_a: Tuple[str, int, int],
    ref_b: Tuple[str, int, int],
) -> None:
    """A rect is only valid for the image it was measured on.

    If this fails the raster was replaced or resized and the coverage must be
    re-measured — not adjusted by eye.
    """
    gif = _RESOURCES / gif_name
    if not gif.exists():
        pytest.skip(f"{gif_name} not present in this checkout")
    with Image.open(gif) as img:
        assert img.size == COVERAGE[terrain_cls().name].image_size


def test_terrain_bounds_does_not_bound_the_map() -> None:
    """Counter-evidence for the whole module. Do not use ``terrain.bounds``.

    Measured 2026-08-22: 24 of Syria's 224 airfields sit outside it, including
    the entire Jordanian corner and the Negev. Kept as a test so that if pydcs
    ever fixes its data this fails and the choice can be revisited on purpose.
    """
    syria = Syria()
    bounds = syria.bounds
    lo_x, hi_x = min(bounds.top, bounds.bottom), max(bounds.top, bounds.bottom)
    lo_y, hi_y = min(bounds.left, bounds.right), max(bounds.left, bounds.right)
    outside = [
        airport.name
        for airport in syria.airports.values()
        if not (
            lo_x <= airport.position.x <= hi_x and lo_y <= airport.position.y <= hi_y
        )
    ]
    assert (
        len(outside) == 24
    ), f"expected 24 Syria airfields outside bounds, got {outside}"
    for name in ("King Abdullah II", "Muwaffaq Salti", "Nevatim", "Hatzerim"):
        assert name in outside

    # pydcs also inverts its own Rectangle contract here (top is meant to be
    # the larger x), so height() is negative and any scale taken from it flips.
    assert bounds.height() < 0


def test_coverage_lookup_refuses_a_resized_raster() -> None:
    """A GIF that is not the measured size gets no georeference at all."""
    caucasus = Caucasus()
    recorded = COVERAGE[caucasus.name].image_size
    assert coverage_for(caucasus, recorded) is not None
    assert coverage_for(caucasus, (recorded[0] + 1, recorded[1])) is None


def test_coverage_lookup_refuses_an_unmeasured_theater() -> None:
    """Sinai ships a raster but has no measured georeference; never guess."""
    from dcs.terrain import Sinai

    sinai = Sinai()
    assert sinai.name not in COVERAGE
    assert coverage_for(sinai, (923, 842)) is None


def _extent_around(terrain: Terrain, x: float, y: float, half: float) -> MapExtent:
    return MapExtent(
        min_x=x - half, max_x=x + half, min_y=y - half, max_y=y + half, terrain=terrain
    )


def test_extent_inside_the_raster_is_accepted() -> None:
    syria = Syria()
    tabqa = syria.airports["Tabqa"].position
    coverage = COVERAGE[syria.name]
    assert coverage.can_render(_extent_around(syria, tabqa.x, tabqa.y, 30_000))


@pytest.mark.parametrize(
    "airfield", ["King Abdullah II", "Muwaffaq Salti", "Nevatim", "Hatzerim", "Marka"]
)
def test_extent_over_ground_the_raster_never_drew_is_refused(airfield: str) -> None:
    """The Jordan/Negev corner is off syria.gif; cropping there would stretch.

    These are real strike targets — the 2026-08-22 Syria BAI turn that
    surfaced this fragged against King Abdullah II.
    """
    syria = Syria()
    pos = syria.airports[airfield].position
    coverage = COVERAGE[syria.name]
    assert not coverage.can_render(_extent_around(syria, pos.x, pos.y, 20_000))


@pytest.mark.parametrize("airfield", ["Akrotiri", "Larnaca", "Paphos", "Ercan"])
def test_extent_over_cyprus_is_refused(airfield: str) -> None:
    """syria.gif draws flat sea over Cyprus even though the island is in frame.

    All 25 Cyprus airfields project onto sea pixels. Imagery that confidently
    shows open water under an airbase is worse than no imagery, so refuse.
    """
    syria = Syria()
    pos = syria.airports[airfield].position
    coverage = COVERAGE[syria.name]
    assert coverage.rect.contains(
        WorldRect(pos.x, pos.x, pos.y, pos.y)
    ), f"{airfield} should be inside the raster frame — the hole is what refuses it"
    assert not coverage.can_render(_extent_around(syria, pos.x, pos.y, 15_000))


def test_extent_straddling_the_raster_edge_is_refused() -> None:
    """Partial coverage still refuses — clamping is what put markers wrong."""
    caucasus = Caucasus()
    rect = COVERAGE[caucasus.name].rect
    straddling = MapExtent(
        min_x=rect.min_x - 40_000,
        max_x=rect.min_x + 40_000,
        min_y=rect.min_y + 100_000,
        max_y=rect.min_y + 200_000,
        terrain=caucasus,
    )
    assert not COVERAGE[caucasus.name].can_render(straddling)


def test_world_rect_intersects_is_symmetric_and_edge_exclusive() -> None:
    a = WorldRect(0, 100, 0, 100)
    b = WorldRect(50, 150, 50, 150)
    assert a.intersects(b) and b.intersects(a)
    touching = WorldRect(100, 200, 0, 100)
    assert not a.intersects(touching), "sharing an edge is not an overlap"


def _syria_extent(min_x: float, max_x: float, min_y: float, max_y: float) -> MapExtent:
    return MapExtent(
        min_x=min_x, max_x=max_x, min_y=min_y, max_y=max_y, terrain=Syria()
    )


def test_slide_recovers_an_extent_that_only_aspect_padding_pushed_off() -> None:
    """Padding is symmetric, so an edge overrun usually has slack opposite it."""
    coverage = COVERAGE["Syria"]
    rect = coverage.rect
    # Hangs 40 km off the south edge, with the whole north half free.
    off = _syria_extent(rect.min_x - 40_000, rect.min_x + 160_000, 100_000, 300_000)
    assert not coverage.can_render(off)
    keep = _syria_extent(rect.min_x + 10_000, rect.min_x + 110_000, 150_000, 250_000)
    slid = coverage.slide_to_cover(off, keep)
    assert slid is not None
    assert coverage.can_render(slid)


def test_slide_never_resizes_the_extent() -> None:
    """Translation only — a resize would change the scale under the markers."""
    coverage = COVERAGE["Syria"]
    rect = coverage.rect
    off = _syria_extent(rect.min_x - 40_000, rect.min_x + 160_000, 100_000, 300_000)
    keep = _syria_extent(rect.min_x + 10_000, rect.min_x + 110_000, 150_000, 250_000)
    slid = coverage.slide_to_cover(off, keep)
    assert slid is not None
    assert slid.span_x_m == pytest.approx(off.span_x_m)
    assert slid.span_y_m == pytest.approx(off.span_y_m)


def test_slide_refuses_when_it_would_push_the_packages_off_the_page() -> None:
    """The area of interest is what the page exists to show; never crop it."""
    coverage = COVERAGE["Syria"]
    rect = coverage.rect
    off = _syria_extent(rect.min_x - 40_000, rect.min_x + 160_000, 100_000, 300_000)
    # A target sitting in the strip that the slide has to give up.
    keep = _syria_extent(rect.min_x - 35_000, rect.min_x + 110_000, 150_000, 250_000)
    assert coverage.slide_to_cover(off, keep) is None


def test_slide_refuses_an_extent_wider_than_the_raster() -> None:
    """A theater-wide spread cannot be slid onto a smaller picture."""
    coverage = COVERAGE["Syria"]
    rect = coverage.rect
    huge = _syria_extent(
        rect.min_x - 200_000,
        rect.max_x + 200_000,
        rect.min_y + 100_000,
        rect.min_y + 300_000,
    )
    assert coverage.slide_to_cover(huge, huge) is None


def test_slide_refuses_when_it_lands_on_ground_the_raster_never_drew() -> None:
    """The hole is re-checked after the slide, not only before it.

    This extent starts clear of Cyprus (its south edge is north of the island)
    and overruns the raster's north edge. Sliding it south to fit drops it onto
    Cyprus, which is still a page of open water under an airbase — so it is
    refused even though the slide itself succeeded. Measured on the shipped
    campaigns, this is exactly why IntotheHornetsNest and WRL_AssaultonDamascus
    stay on the landmap.
    """
    coverage = COVERAGE["Syria"]
    cyprus = coverage.unrendered[0]
    # North of Cyprus and off the raster's north edge.
    off = _syria_extent(150_000, 400_000, -300_000, -150_000)
    assert not any(
        h.intersects(WorldRect(150_000, 400_000, -300_000, -150_000))
        for h in coverage.unrendered
    ), "fixture must start clear of Cyprus"
    assert off.max_x > coverage.rect.max_x, "fixture must overrun the north edge"
    keep = _syria_extent(160_000, 250_000, -280_000, -170_000)
    slid_min_x = coverage.rect.max_x - off.span_x_m
    assert slid_min_x < cyprus.max_x, "fixture must land on Cyprus once slid"
    assert coverage.slide_to_cover(off, keep) is None


def test_slide_leaves_an_already_covered_extent_alone() -> None:
    """No shift when none is needed — the page stays centred on its packages."""
    syria = Syria()
    coverage = COVERAGE["Syria"]
    tabqa = syria.airports["Tabqa"].position
    fits = _syria_extent(
        tabqa.x - 50_000, tabqa.x + 50_000, tabqa.y - 50_000, tabqa.y + 50_000
    )
    assert coverage.can_render(fits)
    slid = coverage.slide_to_cover(fits, fits)
    assert slid is not None
    assert (slid.min_x, slid.max_x, slid.min_y, slid.max_y) == (
        fits.min_x,
        fits.max_x,
        fits.min_y,
        fits.max_y,
    )
