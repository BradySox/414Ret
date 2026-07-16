"""Tests for front-anchored support (AEW&C / tanker) orbit placement."""

from __future__ import annotations

import math
from types import SimpleNamespace

from game.ato.flightplans.supportorbit import support_orbit_anchor
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


class NoNearbyThreat:
    """Threat zone far away so only the front-standoff term drives placement."""

    def threatened(self, p: FakePoint) -> bool:
        return False

    def distance_to_threat(self, p: FakePoint) -> Distance:
        return nautical_miles(10_000)

    def closest_boundary(self, p: FakePoint) -> FakePoint:
        return FakePoint(p.x, p.y)


def _theater_with_front() -> tuple[SimpleNamespace, SimpleNamespace]:
    # FLOT centered at origin; blue to the west (-x), red to the east (+x).
    front = SimpleNamespace(
        position=FakePoint(0.0, 0.0),
        blue_cp=SimpleNamespace(position=FakePoint(-100_000, 0.0)),
        red_cp=SimpleNamespace(position=FakePoint(+100_000, 0.0)),
    )
    return SimpleNamespace(conflicts=lambda: iter([front])), front


def test_blue_support_sits_on_blue_side_clear_of_threat() -> None:
    theater, _ = _theater_with_front()
    # Enemy (red) threat spills 30 km onto the blue side of the FLOT.
    threat = HalfPlaneThreat(threshold=-30_000)
    buffer = nautical_miles(80)
    target = SimpleNamespace(position=FakePoint(-100_000, 0.0))

    center, _heading = support_orbit_anchor(
        theater, SimpleNamespace(is_blue=True), threat, target, buffer  # type: ignore[arg-type]
    )

    assert center.x < 0  # blue (friendly) side of the FLOT
    assert abs(center.y) < 1  # centered laterally on the front
    assert not threat.threatened(center)  # type: ignore[arg-type]
    assert threat.distance_to_threat(center).meters >= buffer.meters - 1  # type: ignore[arg-type]


def test_red_support_sits_on_red_side_clear_of_threat() -> None:
    theater, _ = _theater_with_front()

    # Enemy (blue) threat spills onto the red side: threatened when x < +30 km.
    class RedSideThreat(HalfPlaneThreat):
        def threatened(self, p: FakePoint) -> bool:
            return p.x < self.threshold

    threat = RedSideThreat(threshold=+30_000)
    buffer = nautical_miles(70)
    target = SimpleNamespace(position=FakePoint(+100_000, 0.0))

    center, _heading = support_orbit_anchor(
        theater, SimpleNamespace(is_blue=False), threat, target, buffer  # type: ignore[arg-type]
    )

    assert center.x > 0  # red (friendly) side of the FLOT
    assert abs(center.y) < 1
    assert not threat.threatened(center)  # type: ignore[arg-type]
    assert threat.distance_to_threat(center).meters >= buffer.meters - 1  # type: ignore[arg-type]


def test_ai_support_sits_deeper_than_player() -> None:
    # With no nearby threat, depth is driven purely by the front-standoff term:
    # blue holds forward at 1x the buffer, red holds deep at the AI factor.
    from game.ato.flightplans.supportorbit import AI_SUPPORT_DEPTH_FACTOR

    theater, _ = _theater_with_front()
    threat = NoNearbyThreat()
    buffer = nautical_miles(40)

    blue_tgt = SimpleNamespace(position=FakePoint(-100_000, 0.0))
    red_tgt = SimpleNamespace(position=FakePoint(100_000, 0.0))
    blue_center, _ = support_orbit_anchor(
        theater, SimpleNamespace(is_blue=True), threat, blue_tgt, buffer  # type: ignore[arg-type]
    )
    red_center, _ = support_orbit_anchor(
        theater, SimpleNamespace(is_blue=False), threat, red_tgt, buffer  # type: ignore[arg-type]
    )

    blue_behind = abs(blue_center.x)  # distance from FLOT (origin) toward blue
    red_behind = abs(red_center.x)  # distance from FLOT toward red
    assert blue_behind == nautical_miles(40).meters
    assert red_behind == nautical_miles(40 * AI_SUPPORT_DEPTH_FACTOR).meters
    assert red_behind > blue_behind


def test_carrier_target_holds_on_the_fleet() -> None:
    # A carrier-tasked support orbit (E-2C / carrier tanker) must stay with the
    # boat instead of marching up to the land FLOT. Front is centered at the
    # origin; the carrier is 300 km south of it.
    theater, _ = _theater_with_front()
    threat = NoNearbyThreat()
    buffer = nautical_miles(80)
    carrier = SimpleNamespace(position=FakePoint(0.0, -300_000.0), is_carrier=True)

    center, _heading = support_orbit_anchor(
        theater, SimpleNamespace(is_blue=True), threat, carrier, buffer  # type: ignore[arg-type]
    )

    # Anchored on the carrier, not pulled toward the front.
    assert center.distance_to_point(carrier.position) < 1
    assert (
        center.distance_to_point(FakePoint(0.0, 0.0))  # type: ignore[arg-type]
        > nautical_miles(100).meters
    )


def test_fleet_target_also_holds_on_the_fleet() -> None:
    # is_fleet (a non-carrier boat) triggers the same hold-with-the-task-force
    # behavior as is_carrier.
    theater, _ = _theater_with_front()
    threat = NoNearbyThreat()
    buffer = nautical_miles(80)
    fleet = SimpleNamespace(position=FakePoint(0.0, -300_000.0), is_fleet=True)

    center, _heading = support_orbit_anchor(
        theater, SimpleNamespace(is_blue=False), threat, fleet, buffer  # type: ignore[arg-type]
    )

    # No AI deep-hold march either -- it stays on the boat.
    assert center.distance_to_point(fleet.position) < 1


def test_no_front_falls_back_to_target_anchor() -> None:
    # No active front: anchor on the target, stood off from the threat boundary.
    theater = SimpleNamespace(conflicts=lambda: iter([]))
    threat = HalfPlaneThreat(threshold=-30_000)
    buffer = nautical_miles(80)
    target = SimpleNamespace(position=FakePoint(-100_000, 0.0))

    center, _heading = support_orbit_anchor(
        theater, SimpleNamespace(is_blue=True), threat, target, buffer  # type: ignore[arg-type]
    )

    # Target is already clear; it should not be dragged into the threat.
    assert not threat.threatened(center)  # type: ignore[arg-type]
    # And only the threat floor applies -- exactly buffer from the boundary,
    # never the extra depth march (there is no FLOT to be "behind").
    assert (
        abs(threat.distance_to_threat(center).meters - buffer.meters) < 1  # type: ignore[arg-type]
    )


def test_no_front_ai_holds_at_anchor_instead_of_deep_march() -> None:
    # The Scenic Route bug: a front-less naval map (blue = carriers only) sent
    # the red A-50 2.5 x buffer AWAY from the fleet on top of an anchor already
    # farthest from it. With no front there is no "behind the FLOT": an anchor
    # already clear of the threat by the buffer must not move at all,
    # regardless of the AI depth factor.
    theater = SimpleNamespace(conflicts=lambda: iter([]))
    # Enemy fleet threat far to the east; the red anchor field sits 200 km
    # clear of it -- well beyond the 80 NM buffer.
    threat = HalfPlaneThreat(threshold=+200_000)
    buffer = nautical_miles(80)
    target = SimpleNamespace(position=FakePoint(0.0, 0.0))

    center, toward_enemy = support_orbit_anchor(
        theater, SimpleNamespace(is_blue=False), threat, target, buffer  # type: ignore[arg-type]
    )

    assert center.distance_to_point(target.position) < 1
    # The racetrack still faces the enemy threat.
    assert abs(toward_enemy.degrees - 0.0) < 1


def test_no_front_ai_still_pushed_clear_of_threat() -> None:
    # No front + an anchor INSIDE the enemy fleet's threat ring: the threat
    # floor still applies (get clear, then add the buffer) -- skipping the
    # depth march must never leave the orbit inside the threat.
    theater = SimpleNamespace(conflicts=lambda: iter([]))
    threat = HalfPlaneThreat(threshold=-50_000)  # threatened when x > -50 km
    buffer = nautical_miles(40)
    target = SimpleNamespace(position=FakePoint(0.0, 0.0))  # inside the threat

    center, _heading = support_orbit_anchor(
        theater, SimpleNamespace(is_blue=False), threat, target, buffer  # type: ignore[arg-type]
    )

    assert not threat.threatened(center)  # type: ignore[arg-type]
    assert threat.distance_to_threat(center).meters >= buffer.meters - 1  # type: ignore[arg-type]
