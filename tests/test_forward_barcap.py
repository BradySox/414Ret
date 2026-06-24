"""Tests for the 414th red forward-middle BARCAP anchor placement.

Covers the geometry helper ``forward_cap_front_anchor`` directly (the same
duck-typed-fake style as ``test_support_orbit.py``). The map-scale trigger and the
"rear/base BARCAP unchanged / QRA unchanged" guarantees live in
``TheaterState.from_game`` / the planner and are exercised by the rest of the
planner suite staying green plus the helper declining (returning ``None``) for any
target that is not a friendly front control point.
"""

from __future__ import annotations

import math
from types import SimpleNamespace

from game.ato.flightplans.supportorbit import forward_cap_front_anchor
from game.utils import Distance, meters, nautical_miles


class FakePoint:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def heading_between_point(self, other: "FakePoint") -> float:
        return math.degrees(math.atan2(other.y - self.y, other.x - self.x)) % 360

    def point_from_heading(self, heading: float, distance: float) -> "FakePoint":
        rad = math.radians(heading)
        return FakePoint(
            self.x + math.cos(rad) * distance, self.y + math.sin(rad) * distance
        )

    def distance_to_point(self, other: "FakePoint") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


class NoNearbyThreat:
    """Threat zone far away so only the forward-middle term drives placement."""

    def threatened(self, p: FakePoint) -> bool:
        return False

    def distance_to_threat(self, p: FakePoint) -> Distance:
        return nautical_miles(10_000)


class RedSideThreat:
    """Enemy (blue) threat spilling onto the red side: threatened when x < threshold."""

    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def threatened(self, p: FakePoint) -> bool:
        return p.x < self.threshold

    def distance_to_threat(self, p: FakePoint) -> Distance:
        return meters(abs(p.x - self.threshold))


def _front_and_theater() -> tuple[SimpleNamespace, SimpleNamespace]:
    # FLOT at the origin; blue to the west (-x), red to the east (+x). The CPs are
    # 100 km either side, so the red rear CP is at +100 km.
    front = SimpleNamespace(
        position=FakePoint(0.0, 0.0),
        blue_cp=SimpleNamespace(position=FakePoint(-100_000, 0.0)),
        red_cp=SimpleNamespace(position=FakePoint(+100_000, 0.0)),
    )
    theater = SimpleNamespace(conflicts=lambda: iter([front]))
    return theater, front


RED = SimpleNamespace(is_blue=False)
BLUE = SimpleNamespace(is_blue=True)


def test_forward_middle_is_halfway_between_rear_cp_and_flot() -> None:
    theater, front = _front_and_theater()
    result = forward_cap_front_anchor(
        theater, RED, NoNearbyThreat(), front.red_cp, nautical_miles(38)  # type: ignore[arg-type]
    )
    assert result is not None
    center, _heading = result
    # Rear CP at +100 km, FLOT at 0 -> forward-middle ~ +50 km (red side, forward of
    # the rear CP, behind the FLOT).
    assert center.x == 50_000
    assert 0 < center.x < 100_000  # red side, forward-middle


def test_forward_layer_pulled_clear_of_blue_threat_plus_buffer() -> None:
    theater, front = _front_and_theater()
    standoff = nautical_miles(38)
    # Blue threat reaches to +60 km onto the red side, so the +50 km forward-middle
    # point is exposed and must be pulled back (east) until clear + standoff.
    threat = RedSideThreat(threshold=+60_000)
    result = forward_cap_front_anchor(
        theater, RED, threat, front.red_cp, standoff  # type: ignore[arg-type]
    )
    assert result is not None
    center, _heading = result
    assert not threat.threatened(center)  # type: ignore[arg-type]
    assert threat.distance_to_threat(center).meters >= standoff.meters - 1  # type: ignore[arg-type]
    assert center.x > 50_000  # pushed deeper than the unconstrained forward-middle


def test_declines_for_non_friendly_front_cp() -> None:
    # A red BARCAP target that is NOT the friendly CP on the front (here the blue CP)
    # gets no forward layer -> caller keeps the legacy rear placement.
    theater, front = _front_and_theater()
    result = forward_cap_front_anchor(
        theater, RED, NoNearbyThreat(), front.blue_cp, nautical_miles(38)  # type: ignore[arg-type]
    )
    assert result is None


def test_declines_when_no_active_front() -> None:
    theater = SimpleNamespace(conflicts=lambda: iter([]))
    target = SimpleNamespace(position=FakePoint(+100_000, 0.0))
    result = forward_cap_front_anchor(
        theater, RED, NoNearbyThreat(), target, nautical_miles(38)  # type: ignore[arg-type]
    )
    assert result is None


def test_blue_player_uses_blue_cp_side() -> None:
    # Symmetry: a blue front CP yields a forward-middle on the blue (-x) side.
    theater, front = _front_and_theater()
    result = forward_cap_front_anchor(
        theater, BLUE, NoNearbyThreat(), front.blue_cp, nautical_miles(38)  # type: ignore[arg-type]
    )
    assert result is not None
    center, _heading = result
    assert center.x == -50_000
