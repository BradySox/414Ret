"""COIN HVT lifecycle: surface near the front, kill vs escape, momentum feed.

The real TGO spawn is monkeypatched (as in the C1.5/IED tests); these lock the window
state machine, the nearest-front stronghold pick, the kill credit, and the escape path.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import game.fourteenth.coin_hvt as hvt


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

    def point_from_heading(self, heading: float, dist: float) -> "_Point":
        return _Point(self.x + dist, self.y)


class _Unit:
    def __init__(self, alive: bool = True) -> None:
        self.alive = alive
        self.is_vehicle = True


class _TGO:
    _counter = 0

    def __init__(self) -> None:
        _TGO._counter += 1
        self.id = f"hvt{_TGO._counter}"
        self.category = None
        self.units = [_Unit()]
        self.control_point: Any = None
        self.name = ""


class _CP:
    def __init__(self, cp_id: int, kind: str, pos: _Point) -> None:
        self.id = cp_id
        self._kind = kind
        self.position = pos
        self.name = f"CP{cp_id}"
        self.connected_objectives: list[Any] = []

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


def _game(cps: list[_CP], *, hvt_on: bool = True, insurgency: bool = True) -> Any:
    game = SimpleNamespace(
        turn=5,
        settings=SimpleNamespace(coin_hvt=hvt_on, coin_insurgency=insurgency),
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

    monkeypatch.setattr(hvt, "spawn_red_ground_at", _spawn)


def _theater(monkeypatch: Any) -> Any:
    _fake_spawn(monkeypatch)
    blue = _CP(1, "blue", _Point(0, 0))
    near = _CP(2, "red", _Point(50_000, 0))  # nearest the blue front
    far = _CP(3, "red", _Point(300_000, 0))
    return _game([blue, near, far])


def test_off_switch_is_a_noop(monkeypatch: Any) -> None:
    _fake_spawn(monkeypatch)
    game = _game([_CP(1, "red", _Point(0, 0))], hvt_on=False)
    hvt.advance_hvt(game, events=None)
    assert game.coin_state.get("hvt", {}).get("active") is None


def test_surfaces_at_the_stronghold_nearest_the_front(monkeypatch: Any) -> None:
    game = _theater(monkeypatch)
    hvt.advance_hvt(game, events=None)
    active = game.coin_state["hvt"]["active"]
    assert active is not None
    assert active["turns"] == 0 and active["name"]
    # The spawned TGO is attached to CP2 (nearest the blue front), not CP3.
    tgo = game.db.tgos[active["tgo_id"]]
    assert tgo.control_point.id == 2
    assert tgo.name.startswith("HVT ")
    assert any("on the move near CP2" in m[1] for m in game.messages)


def test_kill_credits_a_momentum_blow(monkeypatch: Any) -> None:
    game = _theater(monkeypatch)
    hvt.advance_hvt(game, events=None)  # surface
    tgo = game.db.tgos[game.coin_state["hvt"]["active"]["tgo_id"]]
    for unit in tgo.units:
        unit.alive = False  # the player struck him
    hvt.advance_hvt(game, events=None)  # detect the kill
    assert hvt.consume_hvt_kills(game) == 1
    assert hvt.consume_hvt_kills(game) == 0  # cleared
    assert game.coin_state["hvt"]["active"] is None
    assert game.coin_state["hvt"]["cooldown"] == hvt.HVT_COOLDOWN_TURNS
    assert any("eliminated" in m[1].lower() for m in game.messages)


def test_vanished_tgo_is_not_a_kill(monkeypatch: Any) -> None:
    """A dangling record (the TGO removed by some other path while the host stays
    red) clears the window silently -- never a credited decapitation."""
    game = _theater(monkeypatch)
    hvt.advance_hvt(game, events=None)  # surface at CP2
    active = game.coin_state["hvt"]["active"]
    host = next(cp for cp in game.theater.controlpoints if cp.id == 2)
    host.connected_objectives.clear()  # the TGO vanishes; the stronghold stays red
    game.db.remove(active["tgo_id"])
    hvt.advance_hvt(game, events=None)
    assert hvt.consume_hvt_kills(game) == 0  # no phantom momentum blow
    assert game.coin_state["hvt"]["active"] is None
    assert game.coin_state["hvt"]["cooldown"] == hvt.HVT_COOLDOWN_TURNS
    assert not any("eliminated" in m[1].lower() for m in game.messages)


def test_escapes_when_the_window_closes_without_a_kill(monkeypatch: Any) -> None:
    game = _theater(monkeypatch)
    hvt.advance_hvt(game, events=None)  # surface (turns 0)
    for _ in range(hvt.HVT_WINDOW_TURNS):
        hvt.advance_hvt(game, events=None)  # never killed -> ages out
    assert hvt.consume_hvt_kills(game) == 0  # no momentum blow for a miss
    assert game.coin_state["hvt"]["active"] is None
    assert any("gone to ground" in m[1].lower() for m in game.messages)


def test_cooldown_gates_the_next_hvt(monkeypatch: Any) -> None:
    game = _theater(monkeypatch)
    hvt.advance_hvt(game, events=None)  # surface
    tgo = game.db.tgos[game.coin_state["hvt"]["active"]["tgo_id"]]
    for unit in tgo.units:
        unit.alive = False
    hvt.advance_hvt(game, events=None)  # kill -> cooldown set
    assert game.coin_state["hvt"]["cooldown"] == hvt.HVT_COOLDOWN_TURNS
    for _ in range(hvt.HVT_COOLDOWN_TURNS):
        hvt.advance_hvt(game, events=None)  # burns the cooldown, no new HVT yet
        assert game.coin_state["hvt"]["active"] is None
    hvt.advance_hvt(game, events=None)  # cooldown spent -> a new HVT surfaces
    assert game.coin_state["hvt"]["active"] is not None


def test_stronghold_capture_is_not_a_decapitation(monkeypatch: Any) -> None:
    """A blue capture of the host stronghold clears the HVT TGO -- that is a
    base-fall consequence (already priced via red_base_lost), never a kill."""
    game = _theater(monkeypatch)
    hvt.advance_hvt(game, events=None)  # surface at CP2
    active = game.coin_state["hvt"]["active"]
    host = next(cp for cp in game.theater.controlpoints if cp.id == 2)
    host._kind = "blue"  # the stronghold fell
    # The capture also cleared the convoy TGO (depopulate_uncapturable_tgos).
    game.db.remove(active["tgo_id"])
    host.connected_objectives.clear()
    hvt.advance_hvt(game, events=None)
    assert hvt.consume_hvt_kills(game) == 0  # no momentum blow
    assert game.coin_state["hvt"]["active"] is None
    assert any("slipped away" in m[1].lower() for m in game.messages)


def test_toggle_off_despawns_the_active_hvt(monkeypatch: Any) -> None:
    game = _theater(monkeypatch)
    hvt.advance_hvt(game, events=None)  # surface
    active = game.coin_state["hvt"]["active"]
    assert active is not None
    game.settings.coin_hvt = False
    hvt.advance_hvt(game, events=None)
    assert game.coin_state["hvt"]["active"] is None
    # Despawned, not stranded: no CP still carries the convoy TGO.
    host = next(cp for cp in game.theater.controlpoints if cp.id == 2)
    assert all(t.id != active["tgo_id"] for t in host.connected_objectives)
