"""Tests for SCAR ("Sandy") anchoring its orbit on the King.

``Builder._king_hold_center`` finds the fixed-wing ``COMBAT_SAR`` flight (the C-130
"King") in the package and returns the centre of its hold so Sandy co-orbits it
("escort the King") rather than holding an independent racetrack over the FLOT. It
must ignore the helo ``COMBAT_SAR`` (the Jolly Green pickup) and itself, and return
None when no King is present so the caller falls back to the FLOT centre.
"""

from __future__ import annotations

from typing import Optional

from game.ato import FlightType
from game.ato.flightplans.scar import Builder


class _Pos:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def lerp(self, other: "_Pos", frac: float) -> "_Pos":
        return _Pos(
            self.x + (other.x - self.x) * frac,
            self.y + (other.y - self.y) * frac,
        )


class _Wp:
    def __init__(self, pos: _Pos) -> None:
        self.position = pos


class _Layout:
    def __init__(self, start: _Pos, end: _Pos) -> None:
        self.patrol_start = _Wp(start)
        self.patrol_end = _Wp(end)


class _FlightPlan:
    def __init__(self, layout: _Layout) -> None:
        self.layout = layout


class _Package:
    def __init__(self, flights: list["_Flight"]) -> None:
        self.flights = flights


class _Flight:
    def __init__(
        self,
        flight_type: FlightType,
        is_helo: bool,
        layout: Optional[_Layout] = None,
    ) -> None:
        self.flight_type = flight_type
        self.is_helo = is_helo
        self.flight_plan = _FlightPlan(layout) if layout else None
        self.package: Optional[_Package] = None


def _builder(sandy: _Flight) -> Builder:
    # Bypass IBuilder.__init__ (needs full game scaffolding); the method under test
    # only reads self.flight + self.package (a property -> self.flight.package).
    b = Builder.__new__(Builder)
    b.flight = sandy  # type: ignore[assignment]
    return b


def _wire(flights: list[_Flight]) -> None:
    pkg = _Package(flights)
    for f in flights:
        f.package = pkg


def test_anchors_on_fixed_wing_king() -> None:
    king = _Flight(
        FlightType.COMBAT_SAR, is_helo=False, layout=_Layout(_Pos(0, 0), _Pos(10, 0))
    )
    jolly = _Flight(
        FlightType.COMBAT_SAR, is_helo=True, layout=_Layout(_Pos(99, 99), _Pos(99, 99))
    )
    sandy = _Flight(FlightType.SCAR, is_helo=True)
    _wire([jolly, king, sandy])
    center = _builder(sandy)._king_hold_center()
    assert center is not None
    # Midpoint of the King's racetrack, NOT the Jolly's.
    assert (center.x, center.y) == (5.0, 0.0)


def test_ignores_helo_jolly_green() -> None:
    # Only a helo COMBAT_SAR (Jolly) present -> no fixed-wing King -> None.
    jolly = _Flight(
        FlightType.COMBAT_SAR, is_helo=True, layout=_Layout(_Pos(7, 7), _Pos(7, 7))
    )
    sandy = _Flight(FlightType.SCAR, is_helo=True)
    _wire([jolly, sandy])
    assert _builder(sandy)._king_hold_center() is None


def test_solo_sandy_returns_none() -> None:
    sandy = _Flight(FlightType.SCAR, is_helo=True)
    _wire([sandy])
    assert _builder(sandy)._king_hold_center() is None
