"""A ground object on a field's runway strip or apron is named at generation.

The shapes are the flown ones: Long Road to H3's Incirlik EWR marker (1,437 m down the
runway axis, 265 m off the centreline, on the south-west taxiway) and Al Qusayr's garrison
armor (293 m off). Both held every AI fixed-wing taxi at their field on 2026-09-16.
"""

from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any

from game.theater.airfieldclearance import (
    RUNWAY_STRIP_HALF_WIDTH_M,
    airfield_clearance_conflicts,
)


def _pt(x: float, y: float) -> Any:
    return SimpleNamespace(x=x, y=y)


def _airfield(name: str, heading: float, slots: list[tuple[float, float]]) -> Any:
    airport = SimpleNamespace(
        position=_pt(0.0, 0.0),
        runways=[SimpleNamespace(heading=heading)],
        parking_slots=[SimpleNamespace(position=_pt(x, y)) for x, y in slots],
    )
    return SimpleNamespace(name=name, airport=airport, connected_objectives=[])


def _tgo(name: str, unit_type: str, *positions: tuple[float, float]) -> Any:
    units = [
        SimpleNamespace(position=_pt(x, y), type=SimpleNamespace(id=unit_type))
        for x, y in positions
    ]
    return SimpleNamespace(name=name, units=units)


def _theater(*cps: Any) -> Any:
    return SimpleNamespace(controlpoints=list(cps))


def _along_perp(heading: float, along: float, perp: float) -> tuple[float, float]:
    h = math.radians(heading)
    dx, dy = math.cos(h), math.sin(h)
    # perp is measured as v.x*dy - v.y*dx, so +perp lies along (dy, -dx)
    return along * dx + perp * dy, along * dy - perp * dx


def test_the_incirlik_ewr_marker_is_named_on_the_runway_strip() -> None:
    field = _airfield("Incirlik", 50.0, [])
    x, y = _along_perp(50.0, -1437.0, 265.0)
    field.connected_objectives.append(_tgo("0041 | OWL (EWR)", "FPS-117", (x, y)))

    found = airfield_clearance_conflicts(_theater(field))

    assert [c.ground_object for c in found] == ["0041 | OWL (EWR)"]
    assert found[0].reason == "runway strip"
    assert found[0].airfield == "Incirlik"
    assert round(found[0].perp_m) == 265 and round(found[0].along_m) == -1437


def test_a_group_clear_of_the_strip_and_the_stands_is_not_named() -> None:
    field = _airfield("Incirlik", 50.0, [(500.0, 900.0)])
    x, y = _along_perp(50.0, -1437.0, RUNWAY_STRIP_HALF_WIDTH_M + 615.0)
    field.connected_objectives.append(_tgo("0041 | OWL (EWR)", "FPS-117", (x, y)))
    # far down the extended centreline, past any threshold
    x2, y2 = _along_perp(50.0, 2600.0, 40.0)
    field.connected_objectives.append(_tgo("0099 | FAR (SAM)", "Hawk", (x2, y2)))

    assert airfield_clearance_conflicts(_theater(field)) == []


def test_a_unit_on_a_stand_is_named_as_apron() -> None:
    field = _airfield("Al Qusayr", 280.0, [(-600.0, 1300.0)])
    field.connected_objectives.append(
        _tgo(
            "0001 | PORPOISE (Armor Group)", "T-55", (-2500.0, 1000.0), (-570.0, 1340.0)
        )
    )

    found = airfield_clearance_conflicts(_theater(field))

    assert len(found) == 1
    assert found[0].reason == "apron"
    assert found[0].unit_type == "T-55"


def test_an_object_owned_by_a_neighbouring_point_still_counts() -> None:
    field = _airfield("Incirlik", 50.0, [])
    neighbour = SimpleNamespace(name="FOB", airport=None, connected_objectives=[])
    x, y = _along_perp(50.0, 200.0, -100.0)
    neighbour.connected_objectives.append(
        _tgo("0007 | STRAY (Armor Group)", "M-1 Abrams", (x, y))
    )

    found = airfield_clearance_conflicts(_theater(field, neighbour))

    assert [(c.airfield, c.ground_object) for c in found] == [
        ("Incirlik", "0007 | STRAY (Armor Group)")
    ]
