"""Geometry of the QRA defended-airspace circles (`defense_zone_entries`).

These circles become the dispatcher's Moose accept zones (`SetBorderZone` ->
`DETECTION_BASE:SetAcceptZones`), which is what lets the scramble radius be widened
without letting defenders chase deep into enemy airspace: a raid outside every circle
is invisible to the dispatcher.

Two properties matter and are pinned here:

1. Non-regression -- with `depth == qra_gci_max_radius_nm`, the set of raids that used
   to trigger a GCI (within that radius of *some* base) is exactly the union of the
   circles, so no previously-defended raid becomes invisible.
2. The front is always defended -- a front anchor's circle is grown to reach past its
   own FLOT however far back the anchor sits, which is what rear fields fly toward.
"""

from __future__ import annotations

import uuid

from dcs.mapping import Point

from game.missiongenerator.interceptluadata import (
    FRONT_FORWARD_MARGIN_NM,
    defense_zone_entries,
)
from game.theater import OffMapSpawn, Player
from game.utils import nautical_miles

NM = nautical_miles(1).meters


class _FakeTerrain:
    pass


def _point(x: float, y: float) -> Point:
    return Point(x, y, _FakeTerrain())  # type: ignore[arg-type]


class _FakeCP:
    def __init__(self, name: str, captured: Player, x: float) -> None:
        # ControlPoint.id is a UUID; the anchor-reach map keys on it.
        self.id = uuid.uuid4()
        self.name = name
        self.captured = captured
        self.position = _point(x, 0.0)


class _FakeOffMapSpawn(OffMapSpawn):
    """`captured` is a read-only property on the real class, and the isinstance
    guard fires before it is ever read -- so it is deliberately left unset."""

    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.name = "offmap"
        self.position = _point(0.0, 0.0)


class _FakeFront:
    def __init__(self, blue_cp: _FakeCP, red_cp: _FakeCP, x: float) -> None:
        self.blue_cp = blue_cp
        self.red_cp = red_cp
        self.position = _point(x, 0.0)


class _FakeTheater:
    def __init__(self, cps: list[object], fronts: list[_FakeFront]) -> None:
        self.controlpoints = cps
        self._fronts = fronts

    def conflicts(self) -> list[_FakeFront]:
        return self._fronts


def _zones(theater: _FakeTheater, depth_nm: float) -> dict[str, float]:
    entries = defense_zone_entries(theater, nautical_miles(depth_nm))  # type: ignore[arg-type]
    return {e.name: e.radius_m for e in entries}


def test_rear_cp_gets_exactly_the_configured_depth() -> None:
    rear = _FakeCP("Rear", Player.RED, 0.0)
    theater = _FakeTheater([rear], [])
    radii = _zones(theater, 60)
    assert radii["QRA Defense Rear"] == nautical_miles(60).meters


def test_front_anchor_circle_reaches_past_its_own_flot() -> None:
    # Anchor 100 NM behind the FLOT: depth alone (60 NM) would leave the contested
    # airspace undefended, so rear QRA could never fight over the front.
    red = _FakeCP("Anchor", Player.RED, 0.0)
    blue = _FakeCP("Enemy", Player.BLUE, 200 * NM)
    front = _FakeFront(blue, red, 100 * NM)
    theater = _FakeTheater([red, blue], [front])

    radii = _zones(theater, 60)
    expected = (100 + FRONT_FORWARD_MARGIN_NM) * NM
    assert radii["QRA Defense Anchor"] == expected
    assert radii["QRA Defense Anchor"] > nautical_miles(60).meters


def test_front_anchor_close_to_the_flot_keeps_the_depth_floor() -> None:
    # Red Tide's Haina: 21.4 NM from the FLOT. depth (60) exceeds 21.4 + margin (25),
    # so the floor wins and the circle stays the configured depth.
    red = _FakeCP("Haina", Player.RED, 0.0)
    blue = _FakeCP("Fulda", Player.BLUE, 60 * NM)
    front = _FakeFront(blue, red, 21.4 * NM)
    theater = _FakeTheater([red, blue], [front])

    assert _zones(theater, 60)["QRA Defense Haina"] == nautical_miles(60).meters


def test_a_cp_anchoring_two_fronts_takes_the_farther_reach() -> None:
    red = _FakeCP("Anchor", Player.RED, 0.0)
    blue_a = _FakeCP("A", Player.BLUE, 100 * NM)
    blue_b = _FakeCP("B", Player.BLUE, 300 * NM)
    theater = _FakeTheater(
        [red, blue_a, blue_b],
        [_FakeFront(blue_a, red, 40 * NM), _FakeFront(blue_b, red, 150 * NM)],
    )
    expected = (150 + FRONT_FORWARD_MARGIN_NM) * NM
    assert _zones(theater, 60)["QRA Defense Anchor"] == expected


def test_zones_are_tagged_with_their_owning_coalition() -> None:
    red = _FakeCP("Red", Player.RED, 0.0)
    blue = _FakeCP("Blue", Player.BLUE, 100 * NM)
    theater = _FakeTheater([red, blue], [])
    by_name = {
        e.name: e.coalition
        for e in defense_zone_entries(theater, nautical_miles(60))  # type: ignore[arg-type]
    }
    assert by_name["QRA Defense Red"] == "RED"
    assert by_name["QRA Defense Blue"] == "BLUE"


def test_neutral_and_offmap_control_points_are_not_airspace() -> None:
    red = _FakeCP("Red", Player.RED, 0.0)
    neutral = _FakeCP("Neutral", Player.NEUTRAL, 50 * NM)
    offmap = _FakeOffMapSpawn()
    theater = _FakeTheater([red, neutral, offmap], [])
    names = {e.name for e in defense_zone_entries(theater, nautical_miles(60))}  # type: ignore[arg-type]
    assert names == {"QRA Defense Red"}
