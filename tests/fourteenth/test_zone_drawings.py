"""ROE zones Path B: the Mission-Editor drawing reader (game/fourteenth/zone_drawings.py).

Round-trips real pydcs drawings through ``dict()`` -> ``load_from_dict`` (the exact path
a campaign ``.miz`` takes on load) and asserts the reader normalizes Circle +
FreeFormPolygon into named ``DrawnZone`` shapes, and skips everything else.
"""

from __future__ import annotations

import pytest
from dcs import Point
from dcs.drawing.drawings import StandardLayer
from dcs.mission import Mission
from dcs.terrain import Caucasus

from game.fourteenth.zone_drawings import DrawnZone, read_zone_drawings


def _round_tripped(mission: Mission) -> Mission:
    """A fresh mission loaded from ``mission``'s serialized drawings table."""
    reloaded = Mission(mission.terrain)
    reloaded.drawings.load_from_dict(mission.drawings.dict())
    return reloaded


def _authored_mission() -> Mission:
    m = Mission(Caucasus())
    layer = m.drawings.get_layer(StandardLayer.Author)

    circle = layer.add_circle(Point(1000.0, 2000.0, m.terrain), 5000.0)
    circle.name = "Ring"

    # A 1000 x 2000 m box drawn with the polygon tool: absolute corners, passed as
    # local offsets from the first vertex (the pydcs convention).
    corners = [
        Point(0.0, 0.0, m.terrain),
        Point(1000.0, 0.0, m.terrain),
        Point(1000.0, 2000.0, m.terrain),
        Point(0.0, 2000.0, m.terrain),
    ]
    anchor = corners[0]
    poly = layer.add_freeform_polygon(anchor, [c - anchor for c in corners])
    poly.name = "Box"

    label = layer.add_text_box(Point(9.0, 9.0, m.terrain), "just a label")
    label.name = "Note"  # a TextBox must be ignored

    ghost = layer.add_freeform_polygon(
        Point(0.0, 0.0, m.terrain),
        [
            Point(0.0, 0.0, m.terrain),
            Point(1.0, 0.0, m.terrain),
            Point(1.0, 1.0, m.terrain),
        ],
    )
    ghost.name = ""  # an unnamed shape can't be referenced, so it's skipped
    return m


def test_reads_circle_and_polygon_by_name() -> None:
    zones = read_zone_drawings(_round_tripped(_authored_mission()))
    assert set(zones) == {"Ring", "Box"}

    ring = zones["Ring"]
    assert ring.kind == "circle"
    assert ring.center_xy == pytest.approx((1000.0, 2000.0))
    assert ring.radius_m == pytest.approx(5000.0)

    box = zones["Box"]
    assert box.kind == "polygon"
    assert len(box.outline_xy) == 4
    assert box.outline_xy[0] == pytest.approx((0.0, 0.0))
    assert box.outline_xy[2] == pytest.approx((1000.0, 2000.0))
    assert box.center_xy == pytest.approx((500.0, 1000.0))


def test_polygon_outline_is_absolute_not_offset() -> None:
    # A polygon anchored away from the origin: the ring must be absolute world coords,
    # not the stored local offsets (position + offset).
    m = Mission(Caucasus())
    layer = m.drawings.get_layer(StandardLayer.Author)
    anchor = Point(50000.0, -30000.0, m.terrain)
    offsets = [
        Point(0.0, 0.0, m.terrain),
        Point(2000.0, 0.0, m.terrain),
        Point(2000.0, 2000.0, m.terrain),
        Point(0.0, 2000.0, m.terrain),
    ]
    poly = layer.add_freeform_polygon(anchor, offsets)
    poly.name = "Lane"

    zone = read_zone_drawings(_round_tripped(m))["Lane"]
    assert zone.outline_xy[0] == pytest.approx((50000.0, -30000.0))
    assert zone.outline_xy[2] == pytest.approx((52000.0, -28000.0))


def test_skips_unsupported_and_degenerate() -> None:
    m = Mission(Caucasus())
    layer = m.drawings.get_layer(StandardLayer.Author)
    # Oval/Rectangle are deliberately unread in v1 (convention unverified); a TextBox
    # is decoration; a 2-vertex polygon is degenerate.
    layer.add_oval(Point(0.0, 0.0, m.terrain), 1000.0, 500.0).name = "Oval"
    layer.add_rectangle(Point(0.0, 0.0, m.terrain), 1000.0, 500.0).name = "Rect"
    thin = layer.add_freeform_polygon(
        Point(0.0, 0.0, m.terrain),
        [Point(0.0, 0.0, m.terrain), Point(1000.0, 0.0, m.terrain)],
    )
    thin.name = "Line"

    assert read_zone_drawings(_round_tripped(m)) == {}


def test_empty_mission_reads_nothing() -> None:
    assert read_zone_drawings(Mission(Caucasus())) == {}


def test_drawnzone_is_hashable_frozen() -> None:
    z = DrawnZone(name="z", kind="circle", center_xy=(0.0, 0.0), radius_m=1.0)
    assert z.name == "z"
    with pytest.raises(Exception):
        z.name = "x"  # type: ignore[misc]
