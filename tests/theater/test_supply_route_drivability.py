"""A supply route is driven, so its waypoints must be on ground that can be driven.

The front line is placed by distance along the convoy-route polyline, so a long
straight leg over terrain vehicles cannot cross puts the fight on a ridge.
`northern_russia`'s Kutaisi/Khashuri route reached the Likhi range in one 41 km
leg and put its own waypoint off drivable ground; measured on turn 1, the front
landed on the ridge and both sides bunched ~15 km apart on opposite edges of it.
The yaml `supply_routes:` override follows the E60/S1 instead.

Guards the override itself and the loader rule that lets one exist: a yaml route
for a pair the miz already defines must REPLACE it, not link the pair twice.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from game import persistency
from game.campaignloader.campaign import Campaign
from game.theater.landmap import poly_contains

#: No leg may be long enough to be a chord across a range rather than a road.
MAX_LEG_M = 15_000

#: The drawn line may clip a corner of an exclusion zone; it may not run through
#: one. Measured at 98% after the override, against 75% before it.
MIN_DRIVABLE_FRACTION = 0.90


@pytest.fixture(scope="module")
def northern_russia() -> Any:
    persistency.setup(tempfile.mkdtemp(), False, 0)
    campaign = Campaign.from_file(Path("resources/campaigns/northern_russia.yaml"))
    return campaign.load_theater(campaign.advanced_iads)


def _route(theater: Any, origin: str, destination: str) -> Any:
    for cp in theater.controlpoints:
        if cp.name != origin:
            continue
        for other, route in cp.convoy_routes.items():
            if other.name == destination:
                return route
    raise AssertionError(f"no convoy route {origin} -> {destination}")


def test_the_yaml_override_replaced_the_miz_path(northern_russia: Any) -> None:
    """22 authored waypoints, not the 8 of the miz group it overrides."""
    route = _route(northern_russia, "Kutaisi", "Khashuri FOB")

    assert len(route) == 22


def test_the_override_did_not_link_the_pair_twice(northern_russia: Any) -> None:
    """`add_supply_routes` and `add_yaml_supply_routes` both ran for this pair.

    The ground planner counts `connected_points` rather than de-duplicating it,
    so a second entry is a second front, not a harmless repeat.
    """
    for cp in northern_russia.controlpoints:
        names = [other.name for other in cp.connected_points]
        assert len(names) == len(set(names)), f"{cp.name} is linked twice: {names}"


def test_every_waypoint_is_on_ground_a_convoy_can_drive(northern_russia: Any) -> None:
    zone = northern_russia.landmap.inclusion_zone_only
    route = _route(northern_russia, "Kutaisi", "Khashuri FOB")

    off = [(p.x, p.y) for p in route if not poly_contains(p.x, p.y, zone)]
    assert not off, f"waypoints off drivable ground: {off}"


def test_no_leg_is_a_straight_line_across_a_mountain_range(
    northern_russia: Any,
) -> None:
    route = _route(northern_russia, "Kutaisi", "Khashuri FOB")

    legs = [a.distance_to_point(b) for a, b in zip(route, route[1:])]
    assert max(legs) <= MAX_LEG_M, f"longest leg is {max(legs) / 1000:.1f} km"


def test_the_drawn_line_follows_drivable_ground(northern_russia: Any) -> None:
    """Waypoints alone are not enough — the front sits between them."""
    zone = northern_russia.landmap.inclusion_zone_only
    route = _route(northern_russia, "Kutaisi", "Khashuri FOB")

    on = total = 0
    for a, b in zip(route, route[1:]):
        steps = max(2, int(a.distance_to_point(b) / 250))
        for i in range(steps + 1):
            fraction = i / steps
            on += poly_contains(
                a.x + (b.x - a.x) * fraction, a.y + (b.y - a.y) * fraction, zone
            )
            total += 1
    assert on / total >= MIN_DRIVABLE_FRACTION, f"only {on / total:.0%} is drivable"
