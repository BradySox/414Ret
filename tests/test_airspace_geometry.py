"""Characterization tests for the AirspaceGeometry facade.

AirspaceGeometry is a behaviour-preserving wrapper over the supportorbit placement
helpers (see ``docs/dev/design/414th-airwar-planner-consolidation-notes.md``). These
tests pin the contract that matters: calling through the service returns *exactly*
what calling the raw helper with the same ``(theater, player, threat_zones)`` trio
returns, so the consolidation cannot silently change planner placement.

They reuse the same duck-typed fakes as ``test_support_orbit.py`` /
``test_forward_barcap.py`` (no real theater construction needed).
"""

from __future__ import annotations

import math
from types import SimpleNamespace

from game.ato.flightplans.airspacegeometry import AirspaceGeometry
from game.ato.flightplans.supportorbit import (
    forward_cap_front_anchor,
    support_orbit_anchor,
)
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


class HalfPlaneThreat:
    """Enemy threat = everything with x > threshold (toward the enemy side)."""

    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def threatened(self, p: FakePoint) -> bool:
        return p.x > self.threshold

    def distance_to_threat(self, p: FakePoint) -> Distance:
        return meters(abs(p.x - self.threshold))

    def closest_boundary(self, p: FakePoint) -> FakePoint:
        return FakePoint(self.threshold, p.y)


class RedSideThreat:
    """Enemy (blue) threat spilling onto the red side: threatened when x < threshold."""

    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def threatened(self, p: FakePoint) -> bool:
        return p.x < self.threshold

    def distance_to_threat(self, p: FakePoint) -> Distance:
        return meters(abs(p.x - self.threshold))

    def closest_boundary(self, p: FakePoint) -> FakePoint:
        return FakePoint(self.threshold, p.y)


def _theater_with_front() -> SimpleNamespace:
    # FLOT at origin; blue west (-x), red east (+x); CPs 100 km either side.
    front = SimpleNamespace(
        position=FakePoint(0.0, 0.0),
        blue_cp=SimpleNamespace(position=FakePoint(-100_000, 0.0)),
        red_cp=SimpleNamespace(position=FakePoint(+100_000, 0.0)),
    )
    return SimpleNamespace(conflicts=lambda: iter([front]), _front=front)


BLUE = SimpleNamespace(is_blue=True)
RED = SimpleNamespace(is_blue=False)


def _assert_same_anchor(a, b) -> None:  # type: ignore[no-untyped-def]
    """Both ``(center, heading)`` tuples (or both ``None``) and equal coordinates."""
    if a is None or b is None:
        assert a is None and b is None
        return
    (ca, ha), (cb, hb) = a, b
    assert (ca.x, ca.y) == (cb.x, cb.y)
    assert ha.degrees == hb.degrees


def test_standoff_anchor_matches_raw_helper() -> None:
    theater = _theater_with_front()
    threat = HalfPlaneThreat(threshold=-30_000)
    buffer = nautical_miles(80)
    target = SimpleNamespace(position=FakePoint(-100_000, 0.0))

    direct = support_orbit_anchor(theater, BLUE, threat, target, buffer)  # type: ignore[arg-type]
    geom = AirspaceGeometry(theater, BLUE, threat)  # type: ignore[arg-type]
    viaservice = geom.standoff_anchor(target, buffer)  # type: ignore[arg-type]
    _assert_same_anchor(direct, viaservice)


def test_standoff_anchor_matches_for_ai_side_and_no_front() -> None:
    # AI (deep) side, plus the no-active-front fallback path.
    theater = _theater_with_front()
    no_front = SimpleNamespace(conflicts=lambda: iter([]))
    threat = RedSideThreat(threshold=+30_000)
    buffer = nautical_miles(70)
    target = SimpleNamespace(position=FakePoint(+100_000, 0.0))

    for thr in (theater, no_front):
        direct = support_orbit_anchor(thr, RED, threat, target, buffer)  # type: ignore[arg-type]
        geom = AirspaceGeometry(thr, RED, threat)  # type: ignore[arg-type]
        viaservice = geom.standoff_anchor(target, buffer)  # type: ignore[arg-type]
        _assert_same_anchor(direct, viaservice)


def test_forward_middle_anchor_matches_raw_helper() -> None:
    theater = _theater_with_front()
    standoff = nautical_miles(38)
    red_cp = theater._front.red_cp

    for threat in (RedSideThreat(threshold=+60_000), RedSideThreat(threshold=-10_000)):
        direct = forward_cap_front_anchor(theater, RED, threat, red_cp, standoff)  # type: ignore[arg-type]
        viaservice = AirspaceGeometry(theater, RED, threat).forward_middle_anchor(  # type: ignore[arg-type]
            red_cp, standoff
        )
        _assert_same_anchor(direct, viaservice)


def test_forward_middle_anchor_returns_none_for_non_front_cp() -> None:
    # The "decline" path (not the friendly front CP) must pass through as None.
    theater = _theater_with_front()
    blue_cp = theater._front.blue_cp  # not RED's front CP
    geometry = AirspaceGeometry(theater, RED, RedSideThreat(threshold=-10_000))  # type: ignore[arg-type]
    assert geometry.forward_middle_anchor(blue_cp, nautical_miles(38)) is None


def test_for_coalition_builds_expected_trio() -> None:
    theater = _theater_with_front()
    threat = HalfPlaneThreat(threshold=-30_000)
    coalition = SimpleNamespace(
        game=SimpleNamespace(theater=theater),
        player=BLUE,
        opponent=SimpleNamespace(threat_zone=threat),
    )
    geometry = AirspaceGeometry.for_coalition(coalition)  # type: ignore[arg-type]
    assert geometry.theater is theater
    assert geometry.player is BLUE
    assert geometry.threat_zones is threat
