"""Pilot recovery surge (§21 extension) — guards, gate, and package composition.

The full fulfiller build (flight plans, air-start, ASAP TOT) rides the engine's own
machinery (PackageBuilder already air-starts AI COMBAT_SAR); these lock what is ours:
the off-switch/coalition guards, the once-per-pilot surge stamp (including the
same-turn re-plan allowance), the helo-required rule, and the proposed package shape
(required Jolly + optional extras + optional Sandy/King/escort at a PilotRecoveryZone
centred on the evaders).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import game.fourteenth.csar_surge as cs
from game.ato.flighttype import FlightType
from game.commander.missionproposals import EscortType
from game.fourteenth.downed_pilots import DownedPilot


class _Pt:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


def _sqn(*, aircraft: str, helo: bool, owned: int, capable: set[FlightType]) -> Any:
    return SimpleNamespace(
        aircraft=SimpleNamespace(display_name=aircraft, helicopter=helo),
        owned_aircraft=owned,
        capable_of=lambda task, cap=capable: task in cap,
    )


def _jolly(owned: int = 4) -> Any:
    return _sqn(
        aircraft="CH-47F", helo=True, owned=owned, capable={FlightType.COMBAT_SAR}
    )


def _king() -> Any:
    return _sqn(aircraft="C-130", helo=False, owned=2, capable={FlightType.COMBAT_SAR})


def _sandy() -> Any:
    return _sqn(aircraft="A-10C", helo=False, owned=6, capable={FlightType.SCAR})


def _coalition(
    *,
    on: bool = True,
    blue: bool = True,
    squadrons: list[Any],
    evaders: list[DownedPilot],
    turn: int = 3,
    packages: list[Any] | None = None,
) -> Any:
    game = SimpleNamespace(
        settings=SimpleNamespace(combat_sar_surge=on),
        turn=turn,
        downed_pilots=evaders,
        point_in_world=lambda x, y: _Pt(x, y),
        message=lambda *a, **k: None,
        theater=None,
        db=SimpleNamespace(flights=None),
    )
    coalition = SimpleNamespace(
        player=SimpleNamespace(is_blue=blue),
        game=game,
        air_wing=SimpleNamespace(iter_squadrons=lambda: iter(squadrons)),
        ato=SimpleNamespace(packages=packages or [], add_package=lambda p: None),
    )
    return coalition


def _evader(name: str = "F-14 #1", x: float = 100.0, y: float = 200.0) -> DownedPilot:
    return DownedPilot(unit_name=name, x=x, y=y, aircraft="F-14B", turn_downed=2)


def _plan(coal: Any, monkeypatch: Any) -> list[Any]:
    """Run the planner with the fulfiller faked out; returns captured missions."""
    captured: list[Any] = []

    class _FakeFulfiller:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def plan_mission(
            self, mission: Any, mult: int, now: Any, tracer: Any, ignore_range: bool
        ) -> Any:
            captured.append(SimpleNamespace(mission=mission, ignore_range=ignore_range))
            return SimpleNamespace(flights=mission.flights)

    import game.commander.packagefulfiller as pf

    monkeypatch.setattr(pf, "PackageFulfiller", _FakeFulfiller)
    cs.plan_pilot_recovery_surge(coal, None, _Tracer())  # type: ignore[arg-type]
    return captured


class _Tracer:
    def trace(self, name: str) -> Any:
        return self

    def __enter__(self) -> "_Tracer":
        return self

    def __exit__(self, *a: Any) -> None:
        return None


def test_off_switch_and_red_are_noops(monkeypatch: Any) -> None:
    for coal in (
        _coalition(on=False, squadrons=[_jolly()], evaders=[_evader()]),
        _coalition(blue=False, squadrons=[_jolly()], evaders=[_evader()]),
    ):
        assert _plan(coal, monkeypatch) == []


def test_no_evaders_is_a_noop(monkeypatch: Any) -> None:
    coal = _coalition(squadrons=[_jolly()], evaders=[])
    assert _plan(coal, monkeypatch) == []


def test_no_helo_squadron_no_surge_and_no_stamp(monkeypatch: Any) -> None:
    dp = _evader()
    coal = _coalition(squadrons=[_king(), _sandy()], evaders=[dp])
    assert _plan(coal, monkeypatch) == []
    assert dp.surge_turn == 0  # tries again when a helo exists


def test_surge_fires_once_per_pilot(monkeypatch: Any) -> None:
    dp = _evader()
    coal = _coalition(squadrons=[_jolly()], evaders=[dp], turn=3)
    assert len(_plan(coal, monkeypatch)) == 1
    assert dp.surge_turn == 3

    # Same-turn re-plan (ATO reset): the op is re-planned.
    coal2 = _coalition(squadrons=[_jolly()], evaders=[dp], turn=3)
    assert len(_plan(coal2, monkeypatch)) == 1

    # A later turn: stamped, never re-surged.
    coal3 = _coalition(squadrons=[_jolly()], evaders=[dp], turn=4)
    assert _plan(coal3, monkeypatch) == []


def test_existing_csar_flight_suppresses_the_surge(monkeypatch: Any) -> None:
    pkg = SimpleNamespace(flights=[SimpleNamespace(flight_type=FlightType.COMBAT_SAR)])
    coal = _coalition(squadrons=[_jolly()], evaders=[_evader()], packages=[pkg])
    assert _plan(coal, monkeypatch) == []


def test_package_shape_full_wing(monkeypatch: Any) -> None:
    e1, e2 = _evader("a", x=0.0, y=0.0), _evader("b", x=100.0, y=200.0)
    coal = _coalition(squadrons=[_jolly(), _king(), _sandy()], evaders=[e1, e2])
    (call,) = _plan(coal, monkeypatch)
    mission = call.mission
    assert call.ignore_range is True
    assert mission.asap is True

    from game.theater import PilotRecoveryZone

    assert isinstance(mission.location, PilotRecoveryZone)
    assert (mission.location.position.x, mission.location.position.y) == (50.0, 100.0)
    assert "2 downed pilots" in mission.location.name

    tasks = [(f.task, f.optional) for f in mission.flights]
    # Required Jolly, optional second Jolly (2 evaders), optional King, optional
    # Sandy pair, optional A2A escort.
    assert tasks == [
        (FlightType.COMBAT_SAR, False),
        (FlightType.COMBAT_SAR, True),
        (FlightType.COMBAT_SAR, True),
        (FlightType.SCAR, True),
        (FlightType.ESCORT, True),
    ]
    helos = [f for f in mission.flights if f.task is FlightType.COMBAT_SAR]
    assert helos[0].preferred_type.helicopter is True
    assert helos[1].preferred_type.helicopter is True
    assert helos[2].preferred_type.helicopter is False  # the King
    escort = mission.flights[-1]
    assert escort.escort_type is EscortType.AirToAir
    assert e1.surge_turn == 3 and e2.surge_turn == 3


def test_single_evader_names_the_pilot_and_plans_one_jolly(monkeypatch: Any) -> None:
    coal = _coalition(squadrons=[_jolly()], evaders=[_evader()])
    (call,) = _plan(coal, monkeypatch)
    mission = call.mission
    assert "F-14B pilot" in mission.location.name
    helos = [f for f in mission.flights if f.task is FlightType.COMBAT_SAR]
    assert len(helos) == 1 and helos[0].optional is False


def test_pre_field_save_entries_are_eligible(monkeypatch: Any) -> None:
    dp = _evader()
    del dp.__dict__["surge_turn"]  # a pre-field pickled entry
    coal = _coalition(squadrons=[_jolly()], evaders=[dp])
    assert len(_plan(coal, monkeypatch)) == 1
    assert dp.surge_turn == 3
