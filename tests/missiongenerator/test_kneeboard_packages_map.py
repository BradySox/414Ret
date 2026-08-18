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
