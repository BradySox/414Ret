"""C1.5 re-infiltration state machine, eligibility, conservation, and flip.

The real TGO spawn (ForceGroup.generate) and the engine-native ControlPoint.capture
are exercised by a headless probe on the real campaign; these lock the pure pipeline
logic with fakes, monkeypatching the two spawn helpers so a regression can't silently
break the staged-warning contract or the conservation bound.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import game.fourteenth.coin as co
from game.data.units import UnitClass


class _Player:
    def __init__(self, kind: str) -> None:
        self.kind = kind

    @property
    def is_red(self) -> bool:
        return self.kind == "red"

    @property
    def is_blue(self) -> bool:
        return self.kind == "blue"

    @property
    def is_neutral(self) -> bool:
        return self.kind == "neutral"


class _Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def distance_to_point(self, other: "_Point") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def heading_between_point(self, other: "_Point") -> float:
        return 0.0

    def point_from_heading(self, heading: float, dist: float) -> "_Point":
        return _Point(self.x + dist, self.y)


class _Base:
    def __init__(self, armor: int = 0) -> None:
        self.total_armor = armor
        self.commissioned = 0

    def commission_units(self, order: dict[Any, int]) -> None:
        self.commissioned += sum(order.values())


class _UnitType:
    """Hashable stand-in for a GroundUnitType (a commission-order dict key + the
    revival-eligibility read on a cell unit)."""

    unit_class = UnitClass.INFANTRY
    price = 2
    display_name = "Militia"


class _Unit:
    def __init__(self, alive: bool = True) -> None:
        self.alive = alive
        self.is_vehicle = True
        self.unit_type = _UnitType()


class _TGO:
    _counter = 0

    def __init__(self, category: str | None = None, nunits: int = 3) -> None:
        _TGO._counter += 1
        self.id = f"tgo{_TGO._counter}"
        self.category = category
        self.units = [_Unit() for _ in range(nunits)]
        self.groups = [SimpleNamespace(units=list(self.units))]
        self.control_point: Any = None
        self.is_control_point = False


class _CP:
    def __init__(
        self,
        cp_id: int,
        kind: str,
        pos: _Point,
        armor: int = 0,
        squadrons: tuple[Any, ...] = (),
    ) -> None:
        self.id = cp_id
        self._kind = kind
        self.position = pos
        self.connected_objectives: list[Any] = []
        self.base = _Base(armor)
        self.squadrons = list(squadrons)
        self.is_fleet = False
        self.is_carrier = False
        self.name = f"CP{cp_id}"

    @property
    def captured(self) -> _Player:
        return _Player(self._kind)

    @property
    def ground_objects(self) -> list[Any]:
        return list(self.connected_objectives)

    def capture(self, game: Any, events: Any, player: Any) -> None:
        self._kind = "red"  # engine depopulation is irrelevant to the reparent test


class _DB:
    def __init__(self) -> None:
        self.tgos: dict[str, Any] = {}

    def add(self, tgo_id: str, tgo: Any) -> None:
        self.tgos[tgo_id] = tgo

    def remove(self, tgo_id: str) -> None:
        self.tgos.pop(tgo_id, None)


def _game(
    cps: list[_CP], *, reinfil: bool = True, insurgency: bool = True, turn: int = 5
) -> Any:
    unit_type = _UnitType()
    game = SimpleNamespace(
        turn=turn,
        settings=SimpleNamespace(
            coin_reinfiltration=reinfil, coin_insurgency=insurgency
        ),
        theater=SimpleNamespace(
            controlpoints=cps,
            is_on_land=lambda p: True,
            heading_to_conflict_from=lambda p: None,
        ),
        red=SimpleNamespace(
            player=_Player("red"),
            faction=SimpleNamespace(frontline_units=[unit_type]),
            armed_forces=SimpleNamespace(random_group_for_task=lambda t: None),
        ),
        db=_DB(),
        coin_state={},
        messages=[],
    )
    game.message = lambda title, text="": game.messages.append((title, text))
    return game


def _fake_spawns(monkeypatch: Any) -> None:
    """Spawn a fake cell/cache attached to the source CP (so _tgo_by_id finds it)."""

    def spawn(kind: str) -> Any:
        def _spawn(game: Any, source: _CP, target: _CP, *a: Any) -> Any:
            tgo = _TGO(category="ammo" if kind == "cache" else None)
            tgo.control_point = source
            source.connected_objectives.append(tgo)
            game.db.add(tgo.id, tgo)
            return tgo

        return _spawn

    monkeypatch.setattr(co, "_spawn_cell", spawn("cell"))
    monkeypatch.setattr(co, "_spawn_cache", spawn("cache"))


def _ev() -> Any:
    return SimpleNamespace(
        update_tgo=lambda t: None,
        delete_tgo=lambda t: None,
        update_control_point=lambda c: None,
    )


def _seed_turn0(game: Any) -> None:
    """Run the turn-0 anchor pass so cache_total/_red_cp_turn0 exist."""
    game.turn = 0
    co.regenerate_insurgent_cells(game)
    game.turn = 5


def test_off_switch_is_a_noop(monkeypatch: Any) -> None:
    _fake_spawns(monkeypatch)
    src = _CP(1, "red", _Point(0, 0))
    tgt = _CP(2, "blue", _Point(10_000, 0))
    game = _game([src, tgt], reinfil=False)
    _seed_turn0(game)
    co.advance_reinfiltration(game, events=_ev())
    assert game.coin_state.get("reinfiltration", {}).get("active") is None


def test_starts_attempt_on_eligible_target(monkeypatch: Any) -> None:
    _fake_spawns(monkeypatch)
    src = _CP(1, "red", _Point(0, 0))
    tgt = _CP(2, "blue", _Point(10_000, 0), armor=0)
    extra_red = _CP(3, "red", _Point(500_000, 0))  # keeps conservation slack
    game = _game([src, tgt, extra_red])
    _seed_turn0(game)
    # BLUE takes CP3 so red count (1) < turn-0 count (2): infiltration is allowed.
    extra_red._kind = "blue"
    co.advance_reinfiltration(game, events=_ev())
    attempt = game.coin_state["reinfiltration"]["active"]
    assert attempt is not None
    assert attempt["cp_id"] == "2" and attempt["stage"] == 1
    assert any("infiltration reported" in m[1].lower() for m in game.messages)


def test_conservation_bound_blocks_growth(monkeypatch: Any) -> None:
    _fake_spawns(monkeypatch)
    src = _CP(1, "red", _Point(0, 0))
    tgt = _CP(2, "blue", _Point(10_000, 0))
    game = _game([src, tgt])
    _seed_turn0(game)  # red count at turn 0 == 1; still 1 now -> no slack
    co.advance_reinfiltration(game, events=_ev())
    assert game.coin_state["reinfiltration"]["active"] is None


def test_garrisoned_and_out_of_range_targets_are_ineligible(monkeypatch: Any) -> None:
    _fake_spawns(monkeypatch)
    src = _CP(1, "red", _Point(0, 0))
    held = _CP(2, "blue", _Point(10_000, 0), armor=8)  # garrisoned above threshold
    far = _CP(3, "blue", _Point(500_000, 0))  # out of range
    lost = _CP(4, "red", _Point(500_000, 0))
    game = _game([src, held, far, lost])
    _seed_turn0(game)
    lost._kind = "blue"  # frees conservation slack, but no *eligible* target remains
    co.advance_reinfiltration(game, events=_ev())
    assert game.coin_state["reinfiltration"]["active"] is None


def _active_attempt(monkeypatch: Any) -> tuple[Any, _CP, _CP]:
    _fake_spawns(monkeypatch)
    src = _CP(1, "red", _Point(0, 0))
    tgt = _CP(2, "blue", _Point(10_000, 0))
    slack = _CP(3, "red", _Point(500_000, 0))
    game = _game([src, tgt, slack])
    _seed_turn0(game)
    slack._kind = "blue"
    co.advance_reinfiltration(game, events=_ev())  # start (stage 1)
    return game, src, tgt


def test_stage_progression_seeds_cache_then_flips(monkeypatch: Any) -> None:
    game, src, tgt = _active_attempt(monkeypatch)
    ev = _ev()
    # Stage 1 lasts STAGE1_TURNS, then a cache seeds and we enter stage 2.
    for _ in range(co.STAGE1_TURNS):
        co.advance_reinfiltration(game, events=ev)
    attempt = game.coin_state["reinfiltration"]["active"]
    assert attempt["stage"] == 2 and attempt["cache_tgo"] is not None
    # Stage 2 lasts STAGE2_TURNS, then the CP flips to red.
    for _ in range(co.STAGE2_TURNS):
        co.advance_reinfiltration(game, events=ev)
    assert tgt.captured.is_red
    assert game.coin_state["reinfiltration"]["active"] is None
    assert game.coin_state["reinfiltration"]["cooldown"] == co.COOLDOWN_TURNS
    assert tgt.base.commissioned == co.REINFIL_GARRISON
    assert co.consume_reinfiltration_flips(game) == 1
    assert co.consume_reinfiltration_flips(game) == 0  # cleared


def test_killing_the_cell_aborts_with_cooldown(monkeypatch: Any) -> None:
    game, src, tgt = _active_attempt(monkeypatch)
    cell = co._tgo_by_id(game, game.coin_state["reinfiltration"]["active"]["cell_tgo"])
    for unit in cell.units:
        unit.alive = False
    co.advance_reinfiltration(game, events=_ev())
    rf = game.coin_state["reinfiltration"]
    assert rf["active"] is None and rf["cooldown"] == co.COOLDOWN_TURNS


def test_garrisoning_the_target_aborts(monkeypatch: Any) -> None:
    game, src, tgt = _active_attempt(monkeypatch)
    tgt.base.total_armor = 10  # hold it
    co.advance_reinfiltration(game, events=_ev())
    assert game.coin_state["reinfiltration"]["active"] is None


def test_killing_the_cache_reverts_to_stage_one(monkeypatch: Any) -> None:
    game, src, tgt = _active_attempt(monkeypatch)
    ev = _ev()
    for _ in range(co.STAGE1_TURNS):
        co.advance_reinfiltration(game, events=ev)
    attempt = game.coin_state["reinfiltration"]["active"]
    assert attempt["stage"] == 2
    cache = co._tgo_by_id(game, attempt["cache_tgo"])
    for unit in cache.units:
        unit.alive = False
    co.advance_reinfiltration(game, events=ev)
    reverted = game.coin_state["reinfiltration"]["active"]
    assert reverted["stage"] == 1 and reverted["cache_tgo"] is None
