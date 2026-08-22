"""The Package Targets Map has to be readable, not merely drawn.

Flown 2026-08-17 (Syria turn, `retribution_nextturn.miz`): the page put the
whole theater in a middle band with ~390 px of dead page above and below it,
printed "DRAGONFLY" over "CRANE" and "King Abdullah II" over "Muwaffaq Salti"
into unreadable mush, drew a package dot through the middle of "DOLPHIN", and
labelled "H3 Southwest" twice -- once as the package target, once as the
airfield underneath it.

These assert the page's output rather than its internals: every text call is
recorded, so a regression in placement shows up as overlapping boxes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Tuple

import pytest
from PIL import ImageDraw

from game.missiongenerator.kneeboard import PackagesMapPage


@pytest.fixture
def terrain() -> Any:
    from dcs.terrain.syria import Syria

    return Syria()


def render(
    targets: List[Tuple[str, float, float]],
    control_points: List[Tuple[float, float, str, str, str]],
    terrain: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> List[Tuple[str, Tuple[float, float, float, float]]]:
    """Render the page, returning (text, box) for every label actually drawn."""
    drawn: List[Tuple[str, Tuple[float, float, float, float]]] = []
    original = ImageDraw.ImageDraw.text

    def record(self: Any, xy: Any, text: str, *args: Any, **kwargs: Any) -> Any:
        font = kwargs.get("font")
        width = font.getlength(text) if font is not None else 8.0 * len(text)
        drawn.append((text, (xy[0], xy[1], xy[0] + width, xy[1] + 15)))
        return original(self, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", record)
    PackagesMapPage(targets, control_points, terrain, dark_kneeboard=False).write(
        tmp_path / "map.png"
    )
    # The title and the legend line go through the same call; drop them.
    return [d for d in drawn if d[0] not in ("Package Targets Map",) and len(d[0]) < 40]


def overlapping(
    boxes: List[Tuple[str, Tuple[float, float, float, float]]],
) -> List[Tuple[str, str]]:
    bad = []
    for i, (na, a) in enumerate(boxes):
        for nb, b in boxes[i + 1 :]:
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                bad.append((na, nb))
    return bad


def test_clustered_labels_never_print_on_top_of_each_other(
    terrain: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Eight targets inside 12 km. The old rule stepped only downward and gave
    up at the bottom edge WHILE STILL OVERLAPPING, so it drew anyway."""
    # The cluster sits at the SOUTH edge of the extent, which is what made the
    # flown page fail: downward stacking hits the bottom of the map with
    # labels still unplaced, and the old rule then drew them anyway.
    south, base_y = -300000.0, 40000.0
    targets = [("NORTH ANCHOR", -120000.0, base_y)]
    targets += [
        (name, south + 400.0 * i, base_y + 900.0 * i)
        for i, name in enumerate(
            [
                "DRAGONFLY",
                "CRANE",
                "KINGFISHER",
                "PEACOCK",
                "DOLPHIN",
                "FENNEC",
                "BONGO",
                "QUAGGA",
            ]
        )
    ]
    control_points = [
        (south + 900.0, base_y + 1800.0, "enemy", "airbase", "Muwaffaq Salti"),
        (south + 1300.0, base_y + 2400.0, "enemy", "airbase", "King Abdullah II"),
    ]
    drawn = render(targets, control_points, terrain, tmp_path, monkeypatch)

    assert overlapping(drawn) == [], "labels printed on top of each other"


def test_a_target_that_is_also_a_base_is_named_once(
    terrain: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A package aimed at an airfield appears in both lists, and the base pass
    used to print the same name again a few pixels away."""
    targets = [("H3 Southwest", -150000.0, 120000.0)]
    control_points = [
        (-150000.0, 120000.0, "enemy", "airbase", "H3 Southwest"),
        (-260000.0, 20000.0, "friendly", "airbase", "Ben Gurion"),
    ]
    drawn = render(targets, control_points, terrain, tmp_path, monkeypatch)

    names = [text for text, _ in drawn]
    assert names.count("H3 Southwest") == 1, f"drawn twice: {names}"
    assert "Ben Gurion" in names, "unrelated base labels must survive the dedupe"


def test_no_label_is_drawn_over_a_marker(
    terrain: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Markers are seeded into the occupancy set, not just labels: a dot through
    the text is as unreadable as another label through it."""
    targets = [
        ("ALPHA", -180000.0, 40000.0),
        ("BRAVO", -178000.0, 41000.0),
        ("CHARLIE", -176000.0, 42000.0),
    ]
    drawn = render(targets, [], terrain, tmp_path, monkeypatch)
    assert len(drawn) == 3
    assert overlapping(drawn) == []


def test_the_map_fills_the_page(
    terrain: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A wide, short area of interest used to be letterboxed into a middle band.
    The extent grows instead, so the page carries terrain edge to edge."""
    from PIL import Image

    targets = [("WEST", -200000.0, -60000.0), ("EAST", -205000.0, 260000.0)]
    render(targets, [], terrain, tmp_path, monkeypatch)
    image = Image.open(tmp_path / "map.png").convert("RGB")
    width, height = image.size
    background = image.getpixel((4, height - 4))

    # The band 12 px above the bottom margin must be map, not page background.
    row = [image.getpixel((x, height - 30)) for x in range(60, width - 60, 20)]
    assert any(
        pixel != background for pixel in row
    ), "bottom of the page is still blank background"


def render_with_markers(
    targets: List[Tuple[str, float, float]],
    control_points: List[Tuple[float, float, str, str, str]],
    terrain: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Tuple[
    List[Tuple[str, Tuple[float, float, float, float]]], List[Tuple[float, float]]
]:
    """Render, returning the labels drawn AND every marker centre.

    The placement bug this guards is a label landing far from the thing it
    names, which is invisible to a labels-only view: each name is legible on its
    own, and the page is still wrong.
    """
    drawn: List[Tuple[str, Tuple[float, float, float, float]]] = []
    markers: List[Tuple[float, float]] = []
    original_text = ImageDraw.ImageDraw.text
    original_ellipse = ImageDraw.ImageDraw.ellipse

    def record_text(self: Any, xy: Any, text: str, *args: Any, **kwargs: Any) -> Any:
        font = kwargs.get("font")
        width = font.getlength(text) if font is not None else 8.0 * len(text)
        drawn.append((text, (xy[0], xy[1], xy[0] + width, xy[1] + 15)))
        return original_text(self, xy, text, *args, **kwargs)

    def record_ellipse(self: Any, xy: Any, *args: Any, **kwargs: Any) -> Any:
        x0, y0, x1, y1 = xy
        markers.append(((x0 + x1) / 2, (y0 + y1) / 2))
        return original_ellipse(self, xy, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", record_text)
    monkeypatch.setattr(ImageDraw.ImageDraw, "ellipse", record_ellipse)
    PackagesMapPage(targets, control_points, terrain, dark_kneeboard=False).write(
        tmp_path / "map.png"
    )
    labels = [
        d for d in drawn if d[0] not in ("Package Targets Map",) and len(d[0]) < 40
    ]
    return labels, markers


#: A dozen package targets inside ~25 km, the shape a Syria BAI turn actually
#: generates. Flown 2026-08-22: eleven of these names came out stacked in a
#: column clear of every dot, and an airfield name printed over open water.
_DENSE_CLUSTER: List[Tuple[str, float, float]] = [
    ("NUMBAT", -318000.0, 30000.0),
    ("COW", -316500.0, 33500.0),
    ("KOMODO", -321000.0, 28500.0),
    ("BAT", -319500.0, 35500.0),
    ("SHEEP", -324000.0, 31000.0),
    ("CRICKET", -326500.0, 29500.0),
    ("ERMINE", -329500.0, 34000.0),
    ("SABERTOOTH", -333000.0, 30500.0),
    ("HERRING", -335500.0, 33000.0),
    ("STAGHORN", -338000.0, 28000.0),
    ("TURTLE", -341000.0, 31500.0),
    ("TAPIR", -315000.0, 39000.0),
]


#: The bases around the cluster are load-bearing in this fixture: they seed the
#: occupied boxes that push a target's name away from its dot. With no control
#: points every label places on its first try and the case proves nothing.
_SURROUNDING_BASES: List[Tuple[float, float, str, str, str]] = [
    (-311000.0, -3000.0, "friendly", "airbase", "Akrotiri"),
    (-330000.0, 6000.0, "friendly", "airbase", "Ben Gurion"),
    (-334000.0, 4000.0, "friendly", "airbase", "Tel Nof"),
    (-337000.0, 2000.0, "friendly", "airbase", "Hatzor"),
    (-326000.0, -14000.0, "friendly", "carrier", "CVN-73 George Washington"),
    (-318000.0, -8000.0, "friendly", "lha", "LHA-1 Tarawa"),
    (-343000.0, 32000.0, "enemy", "airbase", "King Abdullah II"),
    (-321000.0, 44000.0, "enemy", "airbase", "Muwaffaq Salti"),
    (-317000.0, 37000.0, "enemy", "airbase", "Prince Hassan"),
    (-300000.0, 62000.0, "enemy", "airbase", "H3"),
    (-297000.0, 58000.0, "enemy", "airbase", "H3 Northwest"),
    (-303000.0, 59000.0, "enemy", "airbase", "H3 Southwest"),
    (-294000.0, 52000.0, "enemy", "airbase", "HJ01"),
    (-308000.0, 66000.0, "enemy", "airbase", "Ruwayshid"),
]


def test_a_crowded_label_stays_with_its_marker(
    terrain: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No label may be stranded away from every marker on the page.

    The slot search used to walk to the map edge, so a dense cluster threw its
    names into open terrain where a reader attaches them to whatever they landed
    beside. Bounding the walk is what this pins; a name that cannot be placed
    within reach is dropped instead, which costs the name but never lies.
    """
    labels, markers = render_with_markers(
        _DENSE_CLUSTER, _SURROUNDING_BASES, terrain, tmp_path, monkeypatch
    )
    # Targets are drawn one dot each, in order, before any base dot, so marker i
    # belongs to _DENSE_CLUSTER[i]. Measuring against the NEAREST marker instead
    # would pass trivially: in a cluster this tight some dot is always close, and
    # a name sitting on the wrong dot is exactly the failure.
    assert len(markers) >= len(_DENSE_CLUSTER)
    own = {name: markers[i] for i, (name, _, _) in enumerate(_DENSE_CLUSTER)}
    reach = PackagesMapPage.MAX_LABEL_OFFSET + 40
    stranded = []
    for text, (x0, y0, x1, y1) in labels:
        marker = own.get(text)
        if marker is None:
            continue
        cx, cy = x0, (y0 + y1) / 2
        away = ((cx - marker[0]) ** 2 + (cy - marker[1]) ** 2) ** 0.5
        if away > reach:
            stranded.append((text, round(away)))
    assert not stranded, f"labels stranded from their own marker: {stranded}"


def test_a_crowded_cluster_still_does_not_overprint(
    terrain: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Bounding the search must not reintroduce the overprinting it replaced.
    labels, _ = render_with_markers(
        _DENSE_CLUSTER, _SURROUNDING_BASES, terrain, tmp_path, monkeypatch
    )
    assert overlapping(labels) == []


def _airfields(
    terrain: Any, names: List[str]
) -> List[Tuple[float, float, str, str, str]]:
    return [
        (
            terrain.airports[n].position.x,
            terrain.airports[n].position.y,
            "enemy",
            "airbase",
            terrain.airports[n].name,
        )
        for n in names
    ]


def test_the_map_draws_theater_terrain_where_the_raster_reaches(
    terrain: Any, tmp_path: Path
) -> None:
    """A northern-Syria package gets the shipped raster behind it, not a flat fill.

    Substitutes a flat stand-in raster at the size the coverage table was
    measured on, so the assertion is "the page's backdrop came from the raster"
    rather than anything about the real imagery.
    """
    from PIL import Image
    from unittest.mock import patch

    from game.missiongenerator.kneeboard_recon import basemap
    from game.missiongenerator.kneeboard_recon.gif_georef import COVERAGE

    marker_rgb = (255, 0, 220)
    stand_in = Image.new("RGB", COVERAGE[terrain.name].image_size, marker_rgb)
    basemap._gif_cache.pop(terrain.name, None)
    bases = _airfields(terrain, ["Tabqa", "Aleppo", "Hama", "Minakh"])
    with patch.object(basemap, "_load_gif", return_value=stand_in):
        PackagesMapPage([], bases, terrain, dark_kneeboard=False).write(
            tmp_path / "map.png"
        )
    image = Image.open(tmp_path / "map.png").convert("RGB")
    width, height = image.size
    sampled = [
        image.getpixel((x, y))
        for x in range(60, width - 60, 40)
        for y in range(200, height - 60, 40)
    ]
    assert marker_rgb in sampled, "page backdrop did not come from the theater raster"


def test_the_map_still_draws_where_the_raster_cannot_reach(
    terrain: Any, tmp_path: Path
) -> None:
    """A whole-Syria spread runs into Jordan, off syria.gif.

    The raster refuses rather than stretching, and the page falls back to the
    landmap coastlines — which, unlike the raster, actually draw Cyprus.
    """
    from PIL import Image
    from unittest.mock import patch

    from game.missiongenerator.kneeboard_recon import basemap
    from game.missiongenerator.kneeboard_recon.gif_georef import COVERAGE

    marker_rgb = (255, 0, 220)
    stand_in = Image.new("RGB", COVERAGE[terrain.name].image_size, marker_rgb)
    basemap._gif_cache.pop(terrain.name, None)
    bases = _airfields(terrain, ["Incirlik", "Tabqa", "King Abdullah II", "Akrotiri"])
    with patch.object(basemap, "_load_gif", return_value=stand_in):
        PackagesMapPage([], bases, terrain, dark_kneeboard=False).write(
            tmp_path / "map.png"
        )
    image = Image.open(tmp_path / "map.png").convert("RGB")
    width, height = image.size
    sampled = {
        image.getpixel((x, y))
        for x in range(60, width - 60, 40)
        for y in range(200, height - 60, 40)
    }
    assert marker_rgb not in sampled, "stretched raster used for ground it never drew"
    assert basemap._SEA_RGB in sampled or basemap._LAND_FILL in sampled


#: Three inland Syrian fields whose aspect-padded extent overruns the raster's
#: south edge by 28 km with slack to the north, and which sit east of the
#: Cyprus band so the unrendered hole does not veto the slide. Guarded by
#: test_the_sliding_fixture_actually_slides -- without a real slide the two
#: tests below pass vacuously, which is how they were first written.
SLIDING_FIXTURE = ["Deir ez-Zor", "Khalkhalah", "Wujah Al Hajar"]

#: The same case with enough fields to make label placement non-trivial --
#: a 3-marker page never runs out of room, so it cannot show a label lost to
#: the slide crowding markers toward one edge.
DENSE_SLIDING_FIXTURE = [
    "Deir ez-Zor",
    "Khalkhalah",
    "Wujah Al Hajar",
    "Damascus",
    "Marj Ruhayyil",
    "Sayqal",
    "Palmyra",
    "Tiyas",
    "An Nasiriyah",
    "Al Qusayr",
    "Rene Mouawad",
    "Hama",
    "Abu al-Duhur",
    "Tabqa",
    "Shayrat",
]


def test_the_sliding_fixture_actually_slides(terrain: Any) -> None:
    """Pins the premise of the two tests below."""
    from game.missiongenerator.kneeboard_recon import basemap
    from game.missiongenerator.kneeboard_recon.extent import MapExtent, aspect_correct
    from game.missiongenerator.kneeboard_recon.gif_georef import COVERAGE

    xs = [terrain.airports[n].position.x for n in SLIDING_FIXTURE]
    ys = [terrain.airports[n].position.y for n in SLIDING_FIXTURE]
    pad = 0.08 * max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
    ao = MapExtent(min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad, terrain)
    padded = aspect_correct(ao, 912, 963)
    assert not COVERAGE[terrain.name].can_render(padded), "fixture already fits"
    slid = basemap.align_extent_to_theater_raster(padded, keep_visible=ao)
    assert slid.min_x != padded.min_x, "fixture did not slide"
    assert COVERAGE[terrain.name].can_render(slid), "slide did not rescue it"


def test_backdrop_and_markers_share_one_extent(terrain: Any, tmp_path: Path) -> None:
    """The slide must move the imagery and the symbology together.

    If the raster were rendered for the slid extent while the projector still
    used the unslid one, every marker would sit a slide-width off its ground —
    the exact failure this whole change exists to remove, reintroduced one
    layer up.
    """
    from unittest.mock import patch

    from game.missiongenerator.kneeboard_recon import basemap, projection

    seen: dict[str, Any] = {}
    real_render = basemap.render_theater_basemap
    real_projector = projection.Projector

    def spy_render(extent: Any, w: int, h: int, **kwargs: Any) -> Any:
        seen["backdrop"] = extent
        return real_render(extent, w, h, **kwargs)

    def spy_projector(*args: Any, **kwargs: Any) -> Any:
        seen["projector"] = kwargs.get("extent", args[0] if args else None)
        return real_projector(*args, **kwargs)

    # An extent the raster refuses outright until the slide rescues it.
    bases = _airfields(terrain, SLIDING_FIXTURE)
    with patch.object(basemap, "render_theater_basemap", spy_render), patch.object(
        projection, "Projector", spy_projector
    ):
        PackagesMapPage([], bases, terrain, dark_kneeboard=False).write(
            tmp_path / "map.png"
        )

    assert "backdrop" in seen and "projector" in seen
    b, p = seen["backdrop"], seen["projector"]
    assert (b.min_x, b.max_x, b.min_y, b.max_y) == (
        p.min_x,
        p.max_x,
        p.min_y,
        p.max_y,
    ), "the backdrop and the markers were drawn for different extents"


def test_the_slide_keeps_every_package_on_the_page(
    terrain: Any, tmp_path: Path
) -> None:
    """Sliding trades centring for imagery — never a target off the edge."""
    from unittest.mock import patch

    from game.missiongenerator.kneeboard_recon import basemap

    seen: dict[str, Any] = {}
    real_render = basemap.render_theater_basemap

    def spy_render(extent: Any, w: int, h: int, **kwargs: Any) -> Any:
        seen["extent"] = extent
        return real_render(extent, w, h, **kwargs)

    bases = _airfields(terrain, SLIDING_FIXTURE)
    with patch.object(basemap, "render_theater_basemap", spy_render):
        PackagesMapPage([], bases, terrain, dark_kneeboard=False).write(
            tmp_path / "map.png"
        )
    extent = seen["extent"]
    for x, y, _, _, name in bases:
        assert (
            extent.min_x <= x <= extent.max_x and extent.min_y <= y <= extent.max_y
        ), f"{name} fell off the page"


def test_the_slide_costs_no_labels(
    terrain: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Buying imagery must not cost an airfield name.

    The slide crowds the markers toward one edge, and labels are drawn beside
    their marker, so in principle one could run out of room and be dropped --
    the failure class this page already has history with (41f4b38ca). Measured
    across all six campaigns the slide recovers: no label is lost. This pins it.
    """
    from game.missiongenerator.kneeboard_recon import basemap

    bases = _airfields(terrain, DENSE_SLIDING_FIXTURE)
    wanted = {b[4] for b in bases}

    real = basemap.align_extent_to_theater_raster
    monkeypatch.setattr(basemap, "align_extent_to_theater_raster", lambda e, **kw: e)
    without = {d[0] for d in render([], bases, terrain, tmp_path, monkeypatch)} & wanted
    monkeypatch.setattr(basemap, "align_extent_to_theater_raster", real)
    with_slide = {
        d[0] for d in render([], bases, terrain, tmp_path, monkeypatch)
    } & wanted

    assert not (
        without - with_slide
    ), f"the slide dropped {sorted(without - with_slide)}"
