"""§50 convoy escort / ambush -> real blue convoys + real concealed red ambush teams.

Locks the force-model half of the feature: the blue convoy top-up (the symmetric analog of
``ensure_enemy_trail_convoy``), the mid-route ambush seeding (real, concealed red TGOs, with
last turn's despawned first), and the auto-fragged BAI escort package -- plus every guard,
so the feature no-ops rather than inventing free units when a precondition is missing.
"""

from __future__ import annotations

import contextlib
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import game.fourteenth.coin as coin_module
import game.commander.packagefulfiller as packagefulfiller_module
from game.fourteenth.convoy_ambush import (
    AMBUSH_TEAM_SIZE,
    BLUE_CONVOY_BUDGET,
    CONVOY_UNITS,
    _ambush_point,
    _nearest_cp,
    ensure_blue_escort_convoy,
    plan_convoy_escort,
    seed_convoy_ambushes,
)

# ---- fakes -------------------------------------------------------------------------


class _Base:
    def __init__(self, armor: dict[Any, int]) -> None:
        self.armor = dict(armor)

    @property
    def total_armor(self) -> int:
        return sum(self.armor.values())

    def commission_units(self, units: dict[Any, int]) -> None:
        for unit_type, count in units.items():
            self.armor[unit_type] = self.armor.get(unit_type, 0) + count


class _Owner:
    def __init__(self, blue: bool) -> None:
        self.is_blue = blue
        self.is_red = not blue


class _Pos:
    """A 1-D coordinate. ``distance_to_point`` is the real |Δx|, so a CP nearer a point
    reads a smaller distance (the corridor helpers place their reference front at x=0, so
    a CP's distance-to-front is just its own coordinate)."""

    def __init__(self, x: float) -> None:
        self.x = x

    def distance_to_point(self, other: "_Pos") -> float:
        return abs(self.x - other.x)


class _CP:
    def __init__(
        self, name: str, blue: bool, dist: float, armor: dict[Any, int] | None = None
    ) -> None:
        self.name = name
        # For the corridor helpers, "captured" is compared to coalition.player; blue CPs
        # use the shared BLUE_PLAYER sentinel so ``cp.captured == coalition.player`` holds.
        self.captured = _Owner(blue)
        self.position = _Pos(dist)
        self.base = _Base(armor or {})
        self.convoy_routes: dict[Any, Any] = {}


class _Unit:
    def __init__(self, name: str) -> None:
        self.display_name = name
        self.price = 2


class _Transfers:
    def __init__(self, convoys: list[Any] | None = None) -> None:
        self.convoys = convoys or []
        self.created: list[Any] = []

    def new_transfer(self, order: Any, now: Any) -> None:
        self.created.append(order)


def _front() -> Any:
    return SimpleNamespace(position=_Pos(0.0))


BLUE_PLAYER = _Owner(True)


def _blue_coalition(convoys: list[Any] | None = None) -> Any:
    coalition = SimpleNamespace(
        player=BLUE_PLAYER,
        transfers=_Transfers(convoys),
        faction=SimpleNamespace(frontline_units={_Unit("M113"), _Unit("Humvee")}),
    )
    return coalition


def _corridor_game(
    *, on: bool, cps: list[_CP], fronts: list[Any], turn: int = 3
) -> Any:
    # Make blue CPs' captured compare equal to the coalition player sentinel.
    for cp in cps:
        if cp.captured.is_blue:
            cp.captured = BLUE_PLAYER
    return SimpleNamespace(
        settings=SimpleNamespace(convoy_ambush=on),
        turn=turn,
        blue=_blue_coalition(),
        theater=SimpleNamespace(controlpoints=cps, conflicts=lambda: list(fronts)),
        conditions=SimpleNamespace(start_time=datetime(2000, 1, 1)),
    )


# ---- ensure_blue_escort_convoy -----------------------------------------------------


def test_no_convoy_when_setting_off() -> None:
    rear = _CP("rear", True, 200.0, {"tank": 8})
    fwd = _CP("fwd", True, 10.0, {"tank": 2})
    rear.convoy_routes = {fwd: ()}
    fwd.convoy_routes = {rear: ()}
    game = _corridor_game(on=False, cps=[rear, fwd], fronts=[_front()])
    ensure_blue_escort_convoy(game)
    assert game.blue.transfers.created == []


def test_no_convoy_on_turn_zero() -> None:
    rear = _CP("rear", True, 200.0, {"tank": 8})
    fwd = _CP("fwd", True, 10.0, {"tank": 2})
    rear.convoy_routes = {fwd: ()}
    fwd.convoy_routes = {rear: ()}
    game = _corridor_game(on=True, cps=[rear, fwd], fronts=[_front()], turn=0)
    ensure_blue_escort_convoy(game)
    assert game.blue.transfers.created == []


def test_tops_blue_convoys_up_to_budget() -> None:
    rear = _CP("rear", True, 200.0, {"tank": 40})
    fwd = _CP("fwd", True, 10.0, {"tank": 2})
    rear.convoy_routes = {fwd: ()}
    fwd.convoy_routes = {rear: ()}
    game = _corridor_game(on=True, cps=[rear, fwd], fronts=[_front()])
    ensure_blue_escort_convoy(game)
    # A single blue road can only field one distinct corridor, so a fresh map gets one
    # convoy (the second budget slot has no distinct road to spread onto).
    created = game.blue.transfers.created
    assert len(created) == 1
    order = created[0]
    assert order.origin is rear
    assert order.destination is fwd
    assert sum(order.units.values()) == CONVOY_UNITS


def test_blue_budget_full_is_a_noop() -> None:
    rear = _CP("rear", True, 200.0, {"tank": 8})
    fwd = _CP("fwd", True, 10.0, {"tank": 2})
    rear.convoy_routes = {fwd: ()}
    fwd.convoy_routes = {rear: ()}
    game = _corridor_game(on=True, cps=[rear, fwd], fronts=[_front()])
    game.blue.transfers.convoys = ["a", "b"][:BLUE_CONVOY_BUDGET]
    ensure_blue_escort_convoy(game)
    assert game.blue.transfers.created == []


# ---- _ambush_point / _nearest_cp ---------------------------------------------------


def test_ambush_point_is_a_mid_route_waypoint() -> None:
    route = ["origin", "mid1", "mid2", "dest"]
    convoy = SimpleNamespace(
        origin=SimpleNamespace(convoy_route_to=lambda dest: route),
        destination="dest",
    )
    # len 4 -> index 2 ("mid2"): an interior waypoint, never an endpoint.
    assert _ambush_point(convoy) == route[len(route) // 2]


def test_ambush_point_none_for_a_short_road() -> None:
    for route in ([], ["origin", "dest"]):  # no interior waypoint to ambush from
        convoy = SimpleNamespace(
            origin=SimpleNamespace(convoy_route_to=lambda dest, r=route: r),
            destination="dest",
        )
        assert _ambush_point(convoy) is None


def test_ambush_point_swallows_a_broken_convoy() -> None:
    def boom(dest: Any) -> Any:
        raise RuntimeError("no route")

    convoy = SimpleNamespace(
        origin=SimpleNamespace(convoy_route_to=boom), destination="dest"
    )
    assert _ambush_point(convoy) is None


def test_nearest_cp_picks_the_closest() -> None:
    near = _CP("near", False, 5.0)
    far = _CP("far", False, 50.0)
    assert _nearest_cp([far, near], _Pos(0.0)) is near  # type: ignore[list-item]


# ---- seed_convoy_ambushes ----------------------------------------------------------


def _ambush_game(*, on: bool, red_cps: list[_CP], convoys: list[Any]) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(convoy_ambush=on),
        theater=SimpleNamespace(controlpoints=red_cps),
        blue=SimpleNamespace(transfers=SimpleNamespace(convoys=convoys)),
    )


def _route_convoy(name: str, route: list[Any]) -> Any:
    return SimpleNamespace(
        name=name,
        origin=SimpleNamespace(convoy_route_to=lambda dest: route),
        destination="dest",
    )


#: A three-point road whose interior waypoint is a real positioned point, so the seed's
#: ``_nearest_cp`` (which measures CP-to-waypoint distance) has coordinates to work with.
_MID = _Pos(1.0)
_POS_ROUTE = [_Pos(0.0), _MID, _Pos(2.0)]


def test_seed_off_is_a_noop(monkeypatch: Any) -> None:
    game = _ambush_game(on=False, red_cps=[_CP("r", False, 0.0)], convoys=[])
    seed_convoy_ambushes(game, events=None)
    assert not getattr(game, "convoy_ambush_state", {}).get("ambushes")


def test_seed_noop_without_red_cps(monkeypatch: Any) -> None:
    convoy = _route_convoy("C1", ["o", "m", "d"])
    game = _ambush_game(on=True, red_cps=[], convoys=[convoy])
    called: list[Any] = []
    monkeypatch.setattr(
        coin_module, "spawn_red_ground_at", lambda *a, **k: called.append(a)
    )
    seed_convoy_ambushes(game, events=None)
    assert called == []
    assert game.convoy_ambush_state["ambushes"] == []


def test_seed_places_one_ambush_per_convoy(monkeypatch: Any) -> None:
    red = _CP("stronghold", False, 0.0)
    convoy = _route_convoy("Convoy-1", _POS_ROUTE)
    game = _ambush_game(on=True, red_cps=[red], convoys=[convoy])

    spawned: list[dict[str, Any]] = []

    def fake_spawn(
        g: Any, red_cp: Any, point: Any, task: Any, events: Any, **kw: Any
    ) -> Any:
        spawned.append(
            {
                "point": point,
                "max_units": kw.get("max_units"),
                "concealed": kw.get("concealed"),
            }
        )
        return SimpleNamespace(id=f"tgo-{len(spawned)}")

    monkeypatch.setattr(coin_module, "spawn_red_ground_at", fake_spawn)
    seed_convoy_ambushes(game, events="EV")

    assert len(spawned) == 1
    assert spawned[0]["point"] is _MID  # the interior waypoint
    assert spawned[0]["max_units"] == AMBUSH_TEAM_SIZE
    assert spawned[0]["concealed"] is True
    records = game.convoy_ambush_state["ambushes"]
    assert records == [{"tgo_id": "tgo-1", "convoy": "Convoy-1"}]


def test_seed_despawns_last_turns_ambushes_first(monkeypatch: Any) -> None:
    red = _CP("stronghold", False, 0.0)
    convoy = _route_convoy("Convoy-1", _POS_ROUTE)
    game = _ambush_game(on=True, red_cps=[red], convoys=[convoy])
    game.convoy_ambush_state = {"ambushes": [{"tgo_id": "old-1", "convoy": "prev"}]}

    despawned: list[str] = []
    monkeypatch.setattr(
        coin_module, "_tgo_by_id", lambda g, tid: SimpleNamespace(id=tid)
    )
    monkeypatch.setattr(
        coin_module, "_despawn", lambda g, tgo, ev: despawned.append(tgo.id)
    )
    monkeypatch.setattr(
        coin_module,
        "spawn_red_ground_at",
        lambda *a, **k: SimpleNamespace(id="new-1"),
    )
    seed_convoy_ambushes(game, events=None)

    assert despawned == ["old-1"]  # the prior ambush was cleaned up
    assert game.convoy_ambush_state["ambushes"] == [
        {"tgo_id": "new-1", "convoy": "Convoy-1"}
    ]


# ---- plan_convoy_escort ------------------------------------------------------------


class _Tracer:
    @contextlib.contextmanager
    def trace(self, _name: str) -> Any:
        yield


class _Ato:
    def __init__(self) -> None:
        self.packages: list[Any] = []

    def add_package(self, package: Any) -> None:
        self.packages.append(package)


def _escort_coalition(*, blue: bool, on: bool, ambushes: list[Any]) -> Any:
    ato = _Ato()
    game = SimpleNamespace(
        settings=SimpleNamespace(convoy_ambush=on),
        convoy_ambush_state={"ambushes": ambushes},
        theater=SimpleNamespace(),
        db=SimpleNamespace(flights=SimpleNamespace()),
    )
    coalition = SimpleNamespace(
        player=SimpleNamespace(is_blue=blue),
        game=game,
        ato=ato,
    )
    return coalition


def test_escort_noop_when_not_blue() -> None:
    coalition = _escort_coalition(blue=False, on=True, ambushes=[{"tgo_id": "t1"}])
    plan_convoy_escort(coalition, datetime(2000, 1, 1), _Tracer())  # type: ignore[arg-type]
    assert coalition.ato.packages == []


def test_escort_noop_when_off() -> None:
    coalition = _escort_coalition(blue=True, on=False, ambushes=[{"tgo_id": "t1"}])
    plan_convoy_escort(coalition, datetime(2000, 1, 1), _Tracer())  # type: ignore[arg-type]
    assert coalition.ato.packages == []


def test_escort_frags_a_bai_package_per_live_ambush(monkeypatch: Any) -> None:
    coalition = _escort_coalition(blue=True, on=True, ambushes=[{"tgo_id": "t1"}])

    live_tgo = SimpleNamespace(units=[SimpleNamespace(alive=True)])
    monkeypatch.setattr(coin_module, "_tgo_by_id", lambda g, tid: live_tgo)
    import game.fourteenth.phases as phases_module

    monkeypatch.setattr(phases_module, "roe_blocks_target", lambda g, tgo: False)

    proposals: list[Any] = []

    class _Fulfiller:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def plan_mission(self, mission: Any, mult: int, now: Any, tracer: Any) -> Any:
            proposals.append(mission)
            return SimpleNamespace(name="escort-pkg")

    monkeypatch.setattr(packagefulfiller_module, "PackageFulfiller", _Fulfiller)
    plan_convoy_escort(coalition, datetime(2000, 1, 1), _Tracer())  # type: ignore[arg-type]

    assert len(coalition.ato.packages) == 1
    # The proposed mission targets the ambush TGO with a BAI flight.
    from game.ato.flighttype import FlightType

    mission = proposals[0]
    assert mission.location is live_tgo
    assert mission.flights[0].task is FlightType.BAI


def test_escort_skips_a_dead_ambush(monkeypatch: Any) -> None:
    coalition = _escort_coalition(blue=True, on=True, ambushes=[{"tgo_id": "t1"}])
    dead_tgo = SimpleNamespace(units=[SimpleNamespace(alive=False)])
    monkeypatch.setattr(coin_module, "_tgo_by_id", lambda g, tid: dead_tgo)
    import game.fourteenth.phases as phases_module

    monkeypatch.setattr(phases_module, "roe_blocks_target", lambda g, tgo: False)

    class _Fulfiller:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def plan_mission(self, *a: Any, **k: Any) -> Any:  # pragma: no cover
            raise AssertionError("should not plan against a dead ambush")

    monkeypatch.setattr(packagefulfiller_module, "PackageFulfiller", _Fulfiller)
    plan_convoy_escort(coalition, datetime(2000, 1, 1), _Tracer())  # type: ignore[arg-type]
    assert coalition.ato.packages == []


# ---- preseeded campaigns must be able to field the feature ---------------------------
#
# The hard prerequisite the 2026-07-05 flown test exposed: ensure_blue_escort_convoy
# needs a blue->blue road corridor (a supply_routes entry linking two BLUE control
# points) or the whole feature silently no-ops -- no convoy, no ambush, no escort. The
# two COIN campaigns shipped preseeding convoy_ambush: true with an all-red supply
# graph, so the flagship "ambush alley" campaigns could never field an escort convoy.
# This guard loads every campaign that preseeds the setting through the real new-game
# theater path and asserts the corridor exists, so a future laydown edit that drops the
# blue road fails CI instead of silently killing the feature.


def _blue_blue_road_count(theater: Any) -> int:
    roads = set()
    for cp in theater.controlpoints:
        if not cp.starting_coalition.is_blue:
            continue
        for other in cp.convoy_routes.keys():
            if other.starting_coalition.is_blue:
                roads.add(tuple(sorted((cp.name, other.name))))
    return len(roads)


def test_preseeded_campaigns_have_a_blue_to_blue_road(tmp_path: Any) -> None:
    from pathlib import Path

    import yaml

    from game import persistency
    from game.campaignloader.campaign import Campaign

    persistency.setup(str(tmp_path), False, 0)
    campaigns_dir = Path("resources/campaigns")
    preseeded = [
        path
        for path in sorted(campaigns_dir.glob("*.yaml"))
        if yaml.safe_load(path.read_text(encoding="utf-8"))
        .get("settings", {})
        .get("convoy_ambush")
        is True
    ]
    # The four campaigns that ship the feature ON must stay preseeded.
    assert {path.stem for path in preseeded} >= {
        "coin_enduring_resolve",
        "iraq_inherent_resolve",
        "1968_Yankee_Station",
        "red_tide",
    }
    for path in preseeded:
        campaign = Campaign.from_file(path)
        theater = campaign.load_theater(campaign.advanced_iads)
        assert _blue_blue_road_count(theater) >= 1, (
            f"{path.stem} preseeds convoy_ambush but has no blue->blue supply road -- "
            "the escort convoy (and with it the whole ambush/escort loop) will "
            "silently never exist. Author the blue rear corridor (see "
            "tools/supply_route_geo.py) or drop the preseed."
        )
