"""Auto-planned convoy mining (§57 Phase 3) — guard + selection logic.

Locks the pure guards/selection so a regression can't silently frag (or fail to frag) a mining
sortie: the off-switches, the coalition gate, the mining-squadron pick (capable + stocked +
carries the dispenser loadout), the enemy-convoy pick, the loadout-forcing, and the
already-planned guard. The full PackageFulfiller build against a real convoy is fly/engine-probe
territory; here it is monkeypatched.
"""

from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace
from typing import Any

import game.fourteenth.convoy_mining as cm
from game.ato.flighttype import FlightType


def _sqn(aircraft: str, owned: int, capable: set[FlightType]) -> Any:
    return SimpleNamespace(
        aircraft=SimpleNamespace(display_name=aircraft),
        owned_aircraft=owned,
        capable_of=lambda task, cap=capable: task in cap,
    )


def _coalition(
    *,
    on: bool = True,
    persist: bool = True,
    blue: bool = True,
    squadrons: list[Any] | None = None,
    convoys: list[Any] | None = None,
    packages: list[Any] | None = None,
) -> Any:
    return SimpleNamespace(
        player=SimpleNamespace(is_blue=blue),
        game=SimpleNamespace(
            settings=SimpleNamespace(
                auto_plan_minefields=on, air_droppable_minefields=persist
            ),
            red=SimpleNamespace(transfers=SimpleNamespace(convoys=convoys or [])),
            theater=SimpleNamespace(),
            db=SimpleNamespace(flights=None),
        ),
        air_wing=SimpleNamespace(iter_squadrons=lambda: iter(squadrons or [])),
        ato=SimpleNamespace(packages=packages or []),
    )


def _tracer() -> Any:
    return SimpleNamespace(trace=lambda _name: nullcontext())


def _run(coal: Any) -> list[Any]:
    added: list[Any] = []
    coal.ato.add_package = added.append
    cm.plan_convoy_mining(coal, None, _tracer())  # type: ignore[arg-type]
    return added


def test_off_switch_is_a_noop() -> None:
    assert _run(_coalition(on=False, squadrons=[], convoys=[])) == []


def test_persistence_off_is_a_noop() -> None:
    assert _run(_coalition(persist=False, squadrons=[], convoys=[])) == []


def test_red_coalition_is_a_noop() -> None:
    assert _run(_coalition(blue=False, squadrons=[], convoys=[])) == []


def test_no_mining_squadron_is_a_noop() -> None:
    # A wing with no CBU-99 aircraft: _mining_squadron finds nothing (empty here).
    assert (
        _run(_coalition(squadrons=[], convoys=[SimpleNamespace(name="c", size=4)]))
        == []
    )


def test_no_convoy_is_a_noop(monkeypatch: Any) -> None:
    monkeypatch.setattr(cm, "_has_mine_loadout", lambda a: True)
    coal = _coalition(squadrons=[_sqn("F/A-18C", 6, {FlightType.BAI})], convoys=[])
    assert _run(coal) == []


def test_mining_squadron_picks_capable_stocked_with_loadout(monkeypatch: Any) -> None:
    monkeypatch.setattr(cm, "_has_mine_loadout", lambda a: a.display_name == "F/A-18C")
    hornet_big = _sqn("F/A-18C", 6, {FlightType.BAI})
    hornet_small = _sqn("F/A-18C", 2, {FlightType.BAI})
    empty = _sqn("F/A-18C", 0, {FlightType.BAI})
    a10 = _sqn(
        "A-10C", 8, {FlightType.BAI}
    )  # capable + stocked but no dispenser loadout
    not_bai = _sqn("F/A-18C", 9, {FlightType.CAS})  # has loadout but can't fly BAI
    coal = _coalition(squadrons=[hornet_small, empty, a10, not_bai, hornet_big])
    picked = cm._mining_squadron(coal)
    assert picked is hornet_big  # biggest BAI-capable dispenser squadron


def test_enemy_convoy_picks_a_live_column() -> None:
    dead = SimpleNamespace(name="empty", size=0)
    live = SimpleNamespace(name="RED-Convoy", size=6)
    game = SimpleNamespace(
        red=SimpleNamespace(transfers=SimpleNamespace(convoys=[dead, live]))
    )
    assert cm._enemy_convoy(game) is live  # type: ignore[arg-type]
    empty_game = SimpleNamespace(
        red=SimpleNamespace(transfers=SimpleNamespace(convoys=[dead]))
    )
    assert cm._enemy_convoy(empty_game) is None  # type: ignore[arg-type]


def test_arm_dispensers_forces_the_loadout_on_members(monkeypatch: Any) -> None:
    aircraft = SimpleNamespace(display_name="F/A-18C")
    monkeypatch.setattr(
        cm, "_mine_loadout", lambda a: SimpleNamespace(name=cm.MINE_LOADOUT_NAME)
    )
    members = [
        SimpleNamespace(loadout=None, use_custom_loadout=False),
        SimpleNamespace(loadout=None, use_custom_loadout=False),
    ]
    other = SimpleNamespace(loadout="keep", use_custom_loadout=False)
    mine_flight = SimpleNamespace(
        unit_type=aircraft, iter_members=lambda: iter(members)
    )
    other_flight = SimpleNamespace(  # different aircraft -> left alone
        unit_type=SimpleNamespace(display_name="A-10C"),
        iter_members=lambda: iter([other]),
    )
    package = SimpleNamespace(flights=[mine_flight, other_flight])
    assert cm._arm_dispensers(package, aircraft) is True  # type: ignore[arg-type]
    for member in members:
        assert member.loadout.name == cm.MINE_LOADOUT_NAME
        assert member.use_custom_loadout is True
    assert other.loadout == "keep"  # the A-10 flight untouched


def test_already_planned_detects_a_mine_flight() -> None:
    def _flight(loadout_name: str) -> Any:
        member = SimpleNamespace(loadout=SimpleNamespace(name=loadout_name))
        return SimpleNamespace(iter_members=lambda m=member: iter([m]))

    mined = _coalition(
        packages=[SimpleNamespace(flights=[_flight(cm.MINE_LOADOUT_NAME)])]
    )
    plain = _coalition(packages=[SimpleNamespace(flights=[_flight("Retribution BAI")])])
    assert cm._already_planned(mined) is True
    assert cm._already_planned(plain) is False


def test_frags_and_arms_the_dispenser(monkeypatch: Any) -> None:
    aircraft = SimpleNamespace(display_name="F/A-18C")
    sqn = _sqn("F/A-18C", 6, {FlightType.BAI})
    sqn.aircraft = aircraft
    convoy = SimpleNamespace(name="RED-Convoy", size=6)
    members = [SimpleNamespace(loadout=None, use_custom_loadout=False)]
    flight = SimpleNamespace(unit_type=aircraft, iter_members=lambda: iter(members))
    package = SimpleNamespace(flights=[flight])

    monkeypatch.setattr(cm, "_has_mine_loadout", lambda a: True)
    monkeypatch.setattr(
        cm, "_mine_loadout", lambda a: SimpleNamespace(name=cm.MINE_LOADOUT_NAME)
    )
    import game.commander.packagefulfiller as pf

    class _Fulfiller:
        def __init__(self, *args: Any) -> None:
            pass

        def plan_mission(self, *args: Any, **kwargs: Any) -> Any:
            return package

    monkeypatch.setattr(pf, "PackageFulfiller", _Fulfiller)

    coal = _coalition(squadrons=[sqn], convoys=[convoy])
    added = _run(coal)
    assert added == [package]
    assert members[0].loadout.name == cm.MINE_LOADOUT_NAME
    assert members[0].use_custom_loadout is True
