"""COIN dispersed-cell lifecycle: seed the countryside, hunt vs coalesce (cache revive).

The real TGO spawn is monkeypatched (as in the C1.5/IED/HVT tests); these lock the
open-field placement, the maturity clock, the attrite path, and the coalesce-revives-a-
dead-cache hook (the feature's distinct effect).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import game.fourteenth.coin_dispersed as fc


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


class _UnitType:
    unit_class = None
    price = 999  # not whitelist-eligible, so it never counts toward the cell anchor


class _Unit:
    def __init__(self, alive: bool = True) -> None:
        self.alive = alive
        self.is_vehicle = True
        self.unit_type = _UnitType()


class _TGO:
    _counter = 0

    def __init__(
        self, category: str | None = None, alive: bool = True, nunits: int = 2
    ) -> None:
        _TGO._counter += 1
        self.id = f"fc{_TGO._counter}"
        self.category = category
        self.units = [_Unit(alive) for _ in range(nunits)]
        self.control_point: Any = None


class _CP:
    def __init__(self, cp_id: int, kind: str, pos: _Point) -> None:
        self.id = cp_id
        self._kind = kind
        self.position = pos
        self.name = f"CP{cp_id}"
        self.connected_objectives: list[Any] = []
        self.base = SimpleNamespace(total_armor=0)

    @property
    def captured(self) -> _Player:
        return _Player(self._kind)

    @property
    def ground_objects(self) -> list[Any]:
        return list(self.connected_objectives)


class _DB:
    def __init__(self) -> None:
        self.tgos: dict[str, Any] = {}

    def add(self, tgo_id: str, tgo: Any) -> None:
        self.tgos[tgo_id] = tgo

    def remove(self, tgo_id: str) -> None:
        self.tgos.pop(tgo_id, None)


def _game(cps: list[_CP], *, on: bool = True, insurgency: bool = True) -> Any:
    game = SimpleNamespace(
        turn=5,
        settings=SimpleNamespace(coin_dispersed_cells=on, coin_insurgency=insurgency),
        theater=SimpleNamespace(
            controlpoints=cps, conflicts=lambda: [], is_on_land=lambda p: True
        ),
        db=_DB(),
        coin_state={},
        messages=[],
    )
    game.message = lambda title, text="": game.messages.append((title, text))
    return game


def _fake_spawn(monkeypatch: Any) -> None:
    def _spawn(
        game: Any, red_cp: _CP, point: Any, task: Any, events: Any, **kw: Any
    ) -> Any:
        tgo = _TGO()
        tgo.control_point = red_cp
        red_cp.connected_objectives.append(tgo)
        game.db.add(tgo.id, tgo)
        return tgo

    monkeypatch.setattr(fc, "spawn_red_ground_at", _spawn)


def _theater(monkeypatch: Any) -> tuple[Any, _CP]:
    """A blue base + one red stronghold far apart, so the mid-line field point clears
    every CP by > MIN_FIELD_DIST_M. Returns (game, stronghold)."""
    _fake_spawn(monkeypatch)
    blue = _CP(1, "blue", _Point(0, 0))
    red = _CP(2, "red", _Point(200_000, 0))
    return _game([blue, red]), red


def test_off_switch_is_a_noop(monkeypatch: Any) -> None:
    _fake_spawn(monkeypatch)
    game = _game([_CP(1, "red", _Point(0, 0))], on=False)
    fc.advance_dispersed_cells(game, events=None)
    assert game.coin_state.get("field_cells", []) == []


def test_seeds_cells_in_the_open_field(monkeypatch: Any) -> None:
    game, red = _theater(monkeypatch)
    fc.advance_dispersed_cells(game, events=None)
    cells = game.coin_state["field_cells"]
    # One red<->blue pairing, so one distinct site (the cap is higher but there's one).
    assert len(cells) == 1
    assert cells[0]["age"] == 0 and cells[0]["home_id"] == "2"
    assert any("countryside near CP2" in m[1] for m in game.messages)


def test_hunting_a_cell_attrites_it_with_no_coalesce(monkeypatch: Any) -> None:
    game, red = _theater(monkeypatch)
    # Give the stronghold a dead cache that a coalesce WOULD revive, to prove a kill
    # denies it.
    cache = _TGO(category="ammo", alive=False)
    red.connected_objectives.append(cache)
    fc.advance_dispersed_cells(game, events=None)  # seed
    cell_tgo = game.db.tgos[game.coin_state["field_cells"][0]["tgo_id"]]
    for unit in cell_tgo.units:
        unit.alive = False  # the player struck it
    fc.advance_dispersed_cells(game, events=None)  # detect the kill
    assert not any(u.alive for u in cache.units)  # cache stays dead (resupply denied)
    assert any("eliminated" in m[1].lower() for m in game.messages)


def test_ignored_cell_coalesces_and_revives_a_dead_cache(monkeypatch: Any) -> None:
    game, red = _theater(monkeypatch)
    cache = _TGO(category="ammo", alive=False)
    red.connected_objectives.append(cache)
    fc.advance_dispersed_cells(game, events=None)  # seed (age 0)
    for _ in range(fc.MATURE_TURNS):
        fc.advance_dispersed_cells(game, events=None)  # never hunted -> matures
    assert all(u.alive for u in cache.units)  # the dead cache is back online
    assert any("supply cache is back" in m[1].lower() for m in game.messages)


def test_coalesce_without_a_dead_cache_reinforces_or_melts(monkeypatch: Any) -> None:
    game, red = _theater(monkeypatch)
    # No dead cache and no dead militia -> the cell just melts in (no crash, no growth).
    fc.advance_dispersed_cells(game, events=None)  # seed
    for _ in range(fc.MATURE_TURNS):
        fc.advance_dispersed_cells(game, events=None)
    assert any("melted into CP2" in m[1] for m in game.messages)
