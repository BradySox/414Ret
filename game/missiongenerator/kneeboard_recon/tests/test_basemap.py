# game/missiongenerator/kneeboard_recon/tests/test_basemap.py
"""Tests for the basemap façade: tile path, legacy fallback, OFFLINE banner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image
from dcs.terrain.caucasus.caucasus import Caucasus

from game.missiongenerator.kneeboard_recon import basemap
from game.missiongenerator.kneeboard_recon.basemap import (
    DETAIL_THRESHOLD_M,
    render_basemap,
)
from game.missiongenerator.kneeboard_recon.extent import MapExtent
from game.missiongenerator.kneeboard_recon.gif_georef import COVERAGE


@pytest.fixture(scope="module")
def caucasus() -> Caucasus:
    return Caucasus()


def test_render_basemap_returns_tile_image_when_pipeline_succeeds(
    caucasus: Caucasus, tmp_path: Path
) -> None:
    """When render_tiles returns an image, render_basemap returns it unchanged."""
    extent = MapExtent(min_x=0.0, max_x=600.0, min_y=0.0, max_y=600.0, terrain=caucasus)
    sentinel = Image.new("RGB", (400, 400), (12, 34, 56))
    with patch.object(basemap, "render_tiles", return_value=sentinel):
        img = render_basemap(
            extent, page_width=400, page_height=400, cache_dir=tmp_path
        )
    assert img is sentinel


def test_render_basemap_falls_back_to_legacy_when_tiles_unavailable(
    caucasus: Caucasus, tmp_path: Path
) -> None:
    """Legacy renderer runs and OFFLINE banner is stamped on the top row."""
    extent = MapExtent(
        min_x=0.0, max_x=1_000.0, min_y=0.0, max_y=1_000.0, terrain=caucasus
    )
    with patch.object(basemap, "render_tiles", return_value=None):
        img = render_basemap(
            extent, page_width=400, page_height=400, cache_dir=tmp_path
        )
    assert img.size == (400, 400)
    # Banner is rendered across the top: sample a pixel in the middle of the
    # banner band. The banner background red dominates.
    r, g, b = img.getpixel((200, 6))
    assert (
        r > 120 and r > g + 40 and r > b + 40
    ), f"expected red OFFLINE banner at top, got pixel ({r}, {g}, {b})"


def test_render_basemap_legacy_fallback_below_threshold_uses_tan_landmap(
    caucasus: Caucasus, tmp_path: Path
) -> None:
    """Below DETAIL_THRESHOLD_M, fallback uses the tan landmap renderer.

    Sample a pixel below the OFFLINE banner band but above any overlay; it
    should be the tan land colour.
    """
    extent = MapExtent(
        min_x=0.0, max_x=1_000.0, min_y=0.0, max_y=1_000.0, terrain=caucasus
    )
    with patch.object(basemap, "render_tiles", return_value=None):
        img = render_basemap(
            extent, page_width=900, page_height=600, cache_dir=tmp_path
        )
    # The OFFLINE banner is 24 px tall; sample at y=50 which is past it.
    assert img.getpixel((0, 50)) == (224, 213, 191)


# A colour the tan-landmap renderer can never emit, so "did the GIF crop run"
# is answered by looking at the page rather than by trusting a call spy.
_SYNTHETIC_GIF_RGB = (255, 0, 220)


def _synthetic_theater_gif(terrain: Caucasus) -> Image.Image:
    """A stand-in raster at the exact size the coverage table was measured on.

    The size matters: ``coverage_for`` refuses a raster that is not the one
    the rect was measured against, so a convenient 200x200 placeholder now
    exercises the refusal path instead of the crop path.
    """
    return Image.new("RGB", COVERAGE[terrain.name].image_size, _SYNTHETIC_GIF_RGB)


def _extent_inside_caucasus_raster(
    caucasus: Caucasus, span_x: float, span_y: float
) -> MapExtent:
    rect = COVERAGE[caucasus.name].rect
    mid_x = (rect.min_x + rect.max_x) / 2
    mid_y = (rect.min_y + rect.max_y) / 2
    return MapExtent(
        min_x=mid_x - span_x / 2,
        max_x=mid_x + span_x / 2,
        min_y=mid_y - span_y / 2,
        max_y=mid_y + span_y / 2,
        terrain=caucasus,
    )


def test_render_basemap_legacy_fallback_above_threshold_uses_gif_crop(
    caucasus: Caucasus, tmp_path: Path
) -> None:
    """Above DETAIL_THRESHOLD_M the legacy path crops the theater gif.

    Patch ``_load_gif`` so the test does not depend on the GIF file being
    present in the CI environment, and assert the page carries the raster's
    own colour — a prior version only checked ``len(colors) > 5``, which also
    passes on the tan-landmap fallback and so covered nothing.
    """
    extent = _extent_inside_caucasus_raster(caucasus, 30_000.0, 30_000.0)
    # Drop any cached gif from a previous test so the spy actually runs.
    basemap._gif_cache.pop(caucasus.name, None)
    with patch.object(basemap, "render_tiles", return_value=None), patch.object(
        basemap, "_load_gif", return_value=_synthetic_theater_gif(caucasus)
    ) as gif_spy:
        img = render_basemap(
            extent, page_width=920, page_height=600, cache_dir=tmp_path
        )
    gif_spy.assert_called()
    assert img.getpixel((460, 400)) == _SYNTHETIC_GIF_RGB


def test_render_basemap_legacy_fallback_wide_east_west_uses_gif_crop(
    caucasus: Caucasus, tmp_path: Path
) -> None:
    """A corridor short north-south but wide east-west is still a large area
    and must take the GIF crop, not the tan grid. Guards against keying the
    threshold off span_x_m alone."""
    extent = _extent_inside_caucasus_raster(caucasus, 2_000.0, 30_000.0)
    basemap._gif_cache.pop(caucasus.name, None)
    with patch.object(basemap, "render_tiles", return_value=None), patch.object(
        basemap, "_load_gif", return_value=_synthetic_theater_gif(caucasus)
    ) as gif_spy:
        img = render_basemap(
            extent, page_width=920, page_height=600, cache_dir=tmp_path
        )
    gif_spy.assert_called()
    assert img.getpixel((460, 400)) == _SYNTHETIC_GIF_RGB


def test_gif_crop_refused_outside_coverage_falls_back_to_landmap(
    caucasus: Caucasus, tmp_path: Path
) -> None:
    """An extent past the raster's edge must not be stretched to fill the page.

    This is the 2026-08-22 defect: the crop rectangle was clamped to the
    image, so ground the raster never drew was rendered as a stretch of
    whatever sat nearest the edge, with the symbology drawn over it.
    """
    rect = COVERAGE[caucasus.name].rect
    extent = MapExtent(
        min_x=rect.min_x - 60_000.0,
        max_x=rect.min_x - 20_000.0,
        min_y=rect.min_y + 100_000.0,
        max_y=rect.min_y + 140_000.0,
        terrain=caucasus,
    )
    basemap._gif_cache.pop(caucasus.name, None)
    with patch.object(basemap, "render_tiles", return_value=None), patch.object(
        basemap, "_load_gif", return_value=_synthetic_theater_gif(caucasus)
    ):
        img = render_basemap(
            extent, page_width=920, page_height=600, cache_dir=tmp_path
        )
    assert img.getpixel((460, 400)) != _SYNTHETIC_GIF_RGB
    # Sample below the 24 px OFFLINE banner: the landmap renderer's tan.
    assert img.getpixel((0, 50)) == (224, 213, 191)


def test_gif_crop_refused_for_a_raster_that_is_not_the_measured_size(
    caucasus: Caucasus, tmp_path: Path
) -> None:
    """A replaced or resized raster invalidates the rect; refuse, don't scale."""
    extent = _extent_inside_caucasus_raster(caucasus, 30_000.0, 30_000.0)
    wrong_size = Image.new("RGB", (200, 200), _SYNTHETIC_GIF_RGB)
    basemap._gif_cache.pop(caucasus.name, None)
    with patch.object(basemap, "render_tiles", return_value=None), patch.object(
        basemap, "_load_gif", return_value=wrong_size
    ):
        img = render_basemap(
            extent, page_width=920, page_height=600, cache_dir=tmp_path
        )
    assert img.getpixel((460, 400)) != _SYNTHETIC_GIF_RGB


def test_gif_crop_samples_the_right_corner_of_the_raster(
    caucasus: Caucasus, tmp_path: Path
) -> None:
    """The crop reads the pixels the extent actually names.

    Paints one quadrant of a stand-in raster a marker colour and asks for an
    extent wholly inside that quadrant. Getting the marker colour back proves
    the world-to-pixel mapping picked the right rows and columns, which a
    clamped crop of a wrong rect would not.
    """
    rect = COVERAGE[caucasus.name].rect
    width, height = COVERAGE[caucasus.name].image_size
    gif = Image.new("RGB", (width, height), (10, 10, 10))
    marker = (0, 255, 120)
    # Top-left image quadrant = north-west corner of the world rect.
    gif.paste(Image.new("RGB", (width // 2, height // 2), marker), (0, 0))

    quarter_x = (rect.max_x - rect.min_x) / 4
    quarter_y = (rect.max_y - rect.min_y) / 4
    north_west = MapExtent(
        min_x=rect.max_x - quarter_x - 15_000.0,
        max_x=rect.max_x - quarter_x + 15_000.0,
        min_y=rect.min_y + quarter_y - 15_000.0,
        max_y=rect.min_y + quarter_y + 15_000.0,
        terrain=caucasus,
    )
    basemap._gif_cache.pop(caucasus.name, None)
    with patch.object(basemap, "render_tiles", return_value=None), patch.object(
        basemap, "_load_gif", return_value=gif
    ):
        img = render_basemap(
            north_west, page_width=920, page_height=600, cache_dir=tmp_path
        )
    assert img.getpixel((460, 400)) == marker


def test_detail_threshold_is_5km() -> None:
    assert DETAIL_THRESHOLD_M == 5_000.0


def test_landmap_polygons_cached_after_first_load(caucasus: Caucasus) -> None:
    """Repeated calls for the same terrain must not re-read the pickle file."""
    basemap._landmap_cache.pop(caucasus.name, None)
    with patch.object(basemap, "pickle", wraps=basemap.pickle) as spy:
        basemap._landmap_polygons_for_terrain(caucasus)
        basemap._landmap_polygons_for_terrain(caucasus)
        assert spy.load.call_count == 1


def _has_text_pixels(img: Image.Image, text_substr: str) -> bool:
    """Quick proxy: scan the banner band for the expected text by rendering
    a synthetic comparison and asserting close-to-white pixels exist in the
    matching x-range. We don't OCR — pixel sampling is good enough."""
    # Lightweight: count near-white pixels in the banner row. The cap-text
    # banner ("...area too large...") is longer than the default banner,
    # so the count of bright pixels in the banner band differs.
    near_white = 0
    for x in range(img.width):
        r, g, b = img.getpixel((x, 11))
        if r > 220 and g > 220 and b > 220:
            near_white += 1
    return near_white > 0


def test_render_basemap_offline_banner_uses_tile_cap_text(
    caucasus: Caucasus, tmp_path: Path
) -> None:
    """Tile-cap fallback must stamp the tile-cap banner text, not the generic one."""
    from game.missiongenerator.kneeboard_recon import tile_compositor

    extent = MapExtent(
        min_x=0.0, max_x=1_000.0, min_y=0.0, max_y=1_000.0, terrain=caucasus
    )

    def _fail_with_cap(*args: object, **kwargs: object) -> None:
        tile_compositor._set_failure(tile_compositor.FAILURE_TILE_CAP)
        return None

    with patch.object(basemap, "render_tiles", side_effect=_fail_with_cap):
        cap_img = render_basemap(extent, 400, 400, cache_dir=tmp_path)

    def _fail_generic(*args: object, **kwargs: object) -> None:
        tile_compositor._set_failure(tile_compositor.FAILURE_TILE_FETCH)
        return None

    with patch.object(basemap, "render_tiles", side_effect=_fail_generic):
        generic_img = render_basemap(extent, 400, 400, cache_dir=tmp_path)

    # The cap banner text is materially longer than the default; the number
    # of white-text pixels in the banner row therefore differs. This is a
    # cheap proxy for "the two banner strings actually rendered differently"
    # without parsing pixels into glyphs.
    cap_white = sum(
        1
        for x in range(cap_img.width)
        if all(c > 220 for c in cap_img.getpixel((x, 11)))
    )
    generic_white = sum(
        1
        for x in range(generic_img.width)
        if all(c > 220 for c in generic_img.getpixel((x, 11)))
    )
    assert cap_white != generic_white, (
        f"cap-vs-generic banner pixel counts must differ; got cap={cap_white}, "
        f"generic={generic_white}"
    )


def test_banner_text_for_reason_returns_distinct_strings() -> None:
    """Unit guard on the reason → banner mapping (no PIL involvement)."""
    from game.missiongenerator.kneeboard_recon.basemap import (
        _OFFLINE_TEXT_DEFAULT,
        _OFFLINE_TEXT_TILE_CAP,
        _banner_text_for_reason,
    )
    from game.missiongenerator.kneeboard_recon import tile_compositor

    assert (
        _banner_text_for_reason(tile_compositor.FAILURE_TILE_CAP)
        == _OFFLINE_TEXT_TILE_CAP
    )
    assert (
        _banner_text_for_reason(tile_compositor.FAILURE_TILE_FETCH)
        == _OFFLINE_TEXT_DEFAULT
    )
    assert (
        _banner_text_for_reason(tile_compositor.FAILURE_PROJECTION)
        == _OFFLINE_TEXT_DEFAULT
    )
    assert _banner_text_for_reason("") == _OFFLINE_TEXT_DEFAULT
    assert _OFFLINE_TEXT_TILE_CAP != _OFFLINE_TEXT_DEFAULT


# --- _imagery_offset_for: anchor precedence + the regional fallback ---


def test_imagery_offset_anchor_airport_takes_precedence(caucasus: Caucasus) -> None:
    """An airbase page with a measured entry keeps its exact per-airport
    offset; the regional estimate is never consulted."""
    from unittest.mock import MagicMock

    from game.missiongenerator.kneeboard_recon.airport_imagery import (
        AirportImagery,
        TerrainImagery,
    )

    extent = MapExtent(
        min_x=0.0, max_x=1_000.0, min_y=0.0, max_y=1_000.0, terrain=caucasus
    )
    airport = MagicMock()
    airport.id = 23
    record = TerrainImagery(
        terrain="Caucasus",
        by_airport_id={
            "23": AirportImagery(
                name="Senaki",
                imagery_offset_lat=0.003,
                imagery_offset_lng=-0.004,
                runways=(),
                has_offset=True,
            )
        },
    )
    with patch.object(
        basemap.airport_imagery, "load", return_value=record
    ), patch.object(
        basemap.airport_imagery,
        "offset_near",
        side_effect=AssertionError("anchor path must not consult offset_near"),
    ):
        off = basemap._imagery_offset_for(extent, airport)
    assert off == (0.003, -0.004)


def test_imagery_offset_falls_back_to_regional_estimate(caucasus: Caucasus) -> None:
    """Target/corridor pages (no airport anchor) get the nearest-calibrated
    regional offset — previously they rendered with no correction at all."""
    extent = MapExtent(
        min_x=0.0, max_x=1_000.0, min_y=0.0, max_y=1_000.0, terrain=caucasus
    )
    with patch.object(
        basemap.airport_imagery, "offset_near", return_value=(0.01, 0.02)
    ) as offset_near:
        off = basemap._imagery_offset_for(extent, None)
    assert off == (0.01, 0.02)
    name, lat, lng = offset_near.call_args[0]
    assert name == caucasus.name
    # The centre really was projected: a plausible Caucasus lat/lng.
    assert 38.0 < lat < 48.0 and 30.0 < lng < 50.0


def test_imagery_offset_survives_unprojectable_terrain() -> None:
    """A terrain whose projection fails (fakes, exotic terrains) silently
    yields no offset instead of blocking the render."""
    from unittest.mock import MagicMock

    extent = MapExtent(
        min_x=0.0, max_x=1_000.0, min_y=0.0, max_y=1_000.0, terrain=MagicMock()
    )
    assert basemap._imagery_offset_for(extent, None) is None


def test_theater_basemap_uses_the_raster_when_it_covers_the_extent(
    caucasus: Caucasus,
) -> None:
    """The orientation map's backdrop is the shipped raster where it reaches."""
    extent = _extent_inside_caucasus_raster(caucasus, 200_000.0, 200_000.0)
    basemap._gif_cache.pop(caucasus.name, None)
    with patch.object(
        basemap, "_load_gif", return_value=_synthetic_theater_gif(caucasus)
    ):
        img = basemap.render_theater_basemap(extent, 400, 400)
    assert img.size == (400, 400)
    assert img.getpixel((200, 200)) == _SYNTHETIC_GIF_RGB


def test_theater_basemap_falls_back_to_coastlines_when_the_raster_refuses(
    caucasus: Caucasus,
) -> None:
    """Off the raster the page still draws, from world-coordinate polygons."""
    rect = COVERAGE[caucasus.name].rect
    extent = MapExtent(
        min_x=rect.min_x - 300_000.0,
        max_x=rect.min_x - 100_000.0,
        min_y=rect.min_y + 100_000.0,
        max_y=rect.min_y + 300_000.0,
        terrain=caucasus,
    )
    basemap._gif_cache.pop(caucasus.name, None)
    with patch.object(
        basemap, "_load_gif", return_value=_synthetic_theater_gif(caucasus)
    ):
        img = basemap.render_theater_basemap(extent, 400, 400)
    assert img.size == (400, 400)
    colours = {
        img.getpixel((x, y)) for x in range(0, 400, 40) for y in range(0, 400, 40)
    }
    assert _SYNTHETIC_GIF_RGB not in colours
    # render_landmap_basemap paints sea, land fill or its grid line — nothing else.
    assert colours <= {
        basemap._SEA_RGB,
        basemap._LAND_FILL,
        basemap._COAST_RGB,
        basemap._GRID_LINE,
    }


def test_theater_basemap_dims_the_raster_for_a_dark_kneeboard(
    caucasus: Caucasus,
) -> None:
    """No dark variant of the raster exists, so the daylight render is dimmed."""
    extent = _extent_inside_caucasus_raster(caucasus, 200_000.0, 200_000.0)
    basemap._gif_cache.pop(caucasus.name, None)
    with patch.object(
        basemap, "_load_gif", return_value=_synthetic_theater_gif(caucasus)
    ):
        light = basemap.render_theater_basemap(extent, 400, 400, dark=False)
        dark = basemap.render_theater_basemap(extent, 400, 400, dark=True)
    assert sum(dark.getpixel((200, 200))) < sum(light.getpixel((200, 200)))


def test_theater_basemap_never_reaches_for_tiles(caucasus: Caucasus) -> None:
    """This backdrop is offline by construction — it must not hit the network.

    The orientation map is generated for every mission, unlike the recon pages,
    so a tile fetch here would put a network round-trip on the normal path.
    """
    extent = _extent_inside_caucasus_raster(caucasus, 200_000.0, 200_000.0)
    basemap._gif_cache.pop(caucasus.name, None)
    with patch.object(
        basemap, "_load_gif", return_value=_synthetic_theater_gif(caucasus)
    ), patch.object(
        basemap, "render_tiles", side_effect=AssertionError("must not fetch tiles")
    ):
        basemap.render_theater_basemap(extent, 400, 400)
