"""A supply route or shipping lane whose two ends bind ONE control point is rejected.

``add_supply_routes`` maps a path group's first and last waypoint to
``closest_control_point`` independently. A single-waypoint group, or a road drawn back
onto its own field, resolves both ends to the same base -- and the loader then linked
that base to itself.

The self-link is fatal downstream, not cosmetic. ``TransitNetwork.shortest_path_between``
returns an EMPTY list for a base-to-itself query (the reconstruction loop exits before it
appends anything), and ``PendingTransfers.arrange_transport`` indexes ``path[0]``
unguarded -- so any consumer that picks the pair raises ``IndexError`` from
``Game.finish_turn`` and the campaign can no longer pass a turn at all. Measured over the
73 shipped campaigns on 2026-08-24: four carried one (operation_syrian_shield's Palmyra
and Tiyas as convoy routes, operation_allied_sword's FOB Samandag and scenic_route /
scenic_merge's Havadarya as shipping lanes; all four are stray single-point groups).

See docs/dev/414th-features.md §50.
"""

from __future__ import annotations

from typing import Any, Sequence

from dcs.mapping import Point

from game.campaignloader.mizcampaignloader import MizCampaignLoader


def point(x: float, y: float) -> Point:
    return Point(x, y, None)  # type: ignore[arg-type]


class FakeCp:
    def __init__(self, name: str, x: float) -> None:
        self.id = name
        self.name = name
        self.position = point(x, 0)
        self.connected_points: list[Any] = []
        self.convoy_routes: dict[Any, Any] = {}
        self.convoy_spawns: dict[Any, Any] = {}
        self.shipping_lanes: dict[Any, Any] = {}
        self.stances: dict[Any, Any] = {}

    def create_convoy_route(
        self, to: Any, waypoints: Any, spawns: Any
    ) -> None:  # pragma: no cover - exercised via the loader
        if to not in self.connected_points:
            self.connected_points.append(to)
        self.convoy_routes[to] = tuple(waypoints)
        self.convoy_spawns[to] = tuple(spawns)

    def create_shipping_lane(self, to: Any, waypoints: Any) -> None:
        self.shipping_lanes[to] = tuple(waypoints)


class FakeGroup:
    def __init__(self, name: str, xs: Sequence[float]) -> None:
        self.name = name
        self.points = [type("P", (), {"position": point(x, 0)})() for x in xs]


class _FakeTheater:
    def __init__(self, cps: Sequence[FakeCp]) -> None:
        self._cps = list(cps)

    def closest_control_point(self, p: Point, allow_naval: bool = False) -> FakeCp:
        return min(self._cps, key=lambda cp: cp.position.distance_to_point(p))


class LoaderWithPaths(MizCampaignLoader):
    """Only the path groups and the CP lookup matter here, so skip the miz machinery."""

    def __init__(self, cps: Sequence[FakeCp], groups: Sequence[FakeGroup]) -> None:
        self._groups = list(groups)
        self.control_points = {cp.id: cp for cp in cps}  # type: ignore[misc]
        self.theater = _FakeTheater(cps)  # type: ignore[assignment]

    @property
    def front_line_path_groups(self) -> Any:
        return iter(self._groups)

    @property
    def shipping_lane_groups(self) -> Any:
        return iter(self._groups)

    def _construct_cp_spawnpoints(self, endpoint: Point) -> Any:
        return ()


def two_bases() -> list[FakeCp]:
    return [FakeCp("alpha", 0), FakeCp("bravo", 100_000)]


def test_a_single_point_path_group_is_not_a_supply_route() -> None:
    # operation_syrian_shield's 'Suelo-5': one waypoint, so both ends are the same CP.
    cps = two_bases()
    LoaderWithPaths(cps, [FakeGroup("Suelo-5", [500])]).add_supply_routes()

    alpha = cps[0]
    assert alpha.convoy_routes == {}
    assert alpha.connected_points == []


def test_a_road_looping_back_to_its_own_field_is_not_a_supply_route() -> None:
    # Palmyra's 38-waypoint loop: it wanders, but both ends land on Palmyra.
    cps = two_bases()
    LoaderWithPaths(
        cps, [FakeGroup("loop", [500, 20_000, 40_000, 900])]
    ).add_supply_routes()

    assert cps[0].convoy_routes == {}
    assert cps[0].connected_points == []


def test_a_real_road_between_two_bases_still_binds() -> None:
    cps = two_bases()
    alpha, bravo = cps
    LoaderWithPaths(cps, [FakeGroup("road", [500, 50_000, 99_000])]).add_supply_routes()

    assert alpha.convoy_routes.get(bravo) is not None
    assert bravo.convoy_routes.get(alpha) is not None
    assert alpha.connected_points == [bravo]


def test_a_single_point_path_group_is_not_a_shipping_lane() -> None:
    # operation_allied_sword's FOB Samandag and scenic_route's Havadarya.
    cps = two_bases()
    LoaderWithPaths(cps, [FakeGroup("Naval-9", [500])]).add_shipping_lanes()

    assert cps[0].shipping_lanes == {}


def test_a_real_lane_between_two_bases_still_binds() -> None:
    cps = two_bases()
    alpha, bravo = cps
    LoaderWithPaths(cps, [FakeGroup("lane", [500, 99_000])]).add_shipping_lanes()

    assert alpha.shipping_lanes.get(bravo) is not None
    assert bravo.shipping_lanes.get(alpha) is not None
