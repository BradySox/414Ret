"""COIN roadside-IED lifecycle: spawn on the ratline, clear vs detonate, will feed.

The real TGO spawn is monkeypatched (as in the C1.5 tests); these lock the fuse state
machine, the road-nearest-the-front placement, the concurrent cap, and the mandate feed.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import game.fourteenth.coin_ied as ied


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


class _Unit:
    def __init__(self, alive: bool = True, is_static: bool = False) -> None:
        self.alive = alive
        self.is_static = is_static
        self.is_vehicle = not is_static


class _TGO:
    _counter = 0

    def __init__(self) -> None:
        _TGO._counter += 1
        self.id = f"ied{_TGO._counter}"
        self.category = None
        self.units = [_Unit()]
        self.control_point: Any = None


class _CP:
    def __init__(self, cp_id: int, kind: str, pos: _Point) -> None:
        self.id = cp_id
        self._kind = kind
        self.position = pos
        self.name = f"CP{cp_id}"
        self.connected_objectives: list[Any] = []
        self.convoy_routes: dict[Any, list[Any]] = {}

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


def _game(cps: list[_CP], *, ied_on: bool = True, insurgency: bool = True) -> Any:
    game = SimpleNamespace(
        turn=5,
        settings=SimpleNamespace(coin_ied=ied_on, coin_insurgency=insurgency),
        theater=SimpleNamespace(controlpoints=cps, conflicts=lambda: []),
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
        game.spawn_kwargs = getattr(game, "spawn_kwargs", [])
        game.spawn_kwargs.append(kw)
        return tgo

    monkeypatch.setattr(ied, "spawn_red_ground_at", _spawn)


def _ratline(monkeypatch: Any) -> Any:
    """A blue 'front' base + two red strongholds joined by a red-red road."""
    _fake_spawn(monkeypatch)
    blue = _CP(1, "blue", _Point(0, 0))
    rear = _CP(2, "red", _Point(300_000, 0))
    fwd = _CP(3, "red", _Point(60_000, 0))  # nearer the blue front
    road = [_Point(180_000, 0), _Point(120_000, 0)]
    rear.convoy_routes[fwd] = road
    fwd.convoy_routes[rear] = list(reversed(road))
    return _game([blue, rear, fwd])


def test_off_switch_is_a_noop(monkeypatch: Any) -> None:
    _fake_spawn(monkeypatch)
    game = _game([_CP(1, "red", _Point(0, 0))], ied_on=False)
    ied.advance_roadside_ieds(game, events=None)
    assert game.coin_state.get("ieds", []) == []


def test_plants_up_to_the_cap_on_the_ratline(monkeypatch: Any) -> None:
    game = _ratline(monkeypatch)
    ied.advance_roadside_ieds(game, events=None)
    ieds = game.coin_state["ieds"]
    # Only one red-red road exists, so exactly one IED is planted (cap is 2 but the
    # second has nowhere distinct to go).
    assert len(ieds) == 1
    assert ieds[0]["armed"] == 0
    assert any("IED activity reported" in m[1] for m in game.messages)
    # Road-pinned concealment: the plant stores its road polyline on the TGO so the
    # map's suspected-activity circle slides along the highway, not into the fields.
    tgo = game.db.tgos[ieds[0]["tgo_id"]]
    assert tgo.concealed_route == [(180_000, 0), (120_000, 0)]


def test_detonates_after_the_fuse_and_charges_the_mandate(monkeypatch: Any) -> None:
    game = _ratline(monkeypatch)
    ied.advance_roadside_ieds(game, events=None)  # plant (armed 0)
    # Never cleared: it ages each turn and detonates at FUSE_TURNS.
    for _ in range(ied.FUSE_TURNS):
        ied.advance_roadside_ieds(game, events=None)
    assert ied.consume_ied_detonations(game) == 1
    assert ied.consume_ied_detonations(game) == 0  # cleared
    assert any("detonation" in m[1].lower() for m in game.messages)


def test_clearing_the_ied_avoids_detonation(monkeypatch: Any) -> None:
    game = _ratline(monkeypatch)
    ied.advance_roadside_ieds(game, events=None)  # plant
    tgo_id = game.coin_state["ieds"][0]["tgo_id"]
    tgo = game.db.tgos[tgo_id]
    for unit in tgo.units:
        unit.alive = False  # the player struck it
    ied.advance_roadside_ieds(game, events=None)
    assert ied.consume_ied_detonations(game) == 0  # no detonation
    assert any("cleared" in m[1].lower() for m in game.messages)


def test_replants_after_a_clear(monkeypatch: Any) -> None:
    game = _ratline(monkeypatch)
    ied.advance_roadside_ieds(game, events=None)  # plant #1
    tgo = game.db.tgos[game.coin_state["ieds"][0]["tgo_id"]]
    for unit in tgo.units:
        unit.alive = False
    ied.advance_roadside_ieds(game, events=None)  # clear #1, replant a fresh one
    assert len(game.coin_state["ieds"]) == 1
    assert game.coin_state["ieds"][0]["armed"] == 0


def _two_road_ratline(monkeypatch: Any) -> Any:
    """A blue front base + a forward red stronghold with TWO red-red roads behind it, so
    both IED slots fill (a static device on one road, a mobile VBIED on the other)."""
    _fake_spawn(monkeypatch)
    blue = _CP(1, "blue", _Point(0, 0))
    fwd = _CP(3, "red", _Point(60_000, 0))
    rear_a = _CP(2, "red", _Point(300_000, 0))
    rear_b = _CP(4, "red", _Point(300_000, 60_000))
    road_a = [_Point(180_000, 0)]
    road_b = [_Point(180_000, 30_000)]
    fwd.convoy_routes[rear_a] = list(road_a)
    rear_a.convoy_routes[fwd] = list(road_a)
    fwd.convoy_routes[rear_b] = list(road_b)
    rear_b.convoy_routes[fwd] = list(road_b)
    return _game([blue, fwd, rear_a, rear_b])


def test_alternates_static_ied_and_mobile_vbied(monkeypatch: Any) -> None:
    game = _two_road_ratline(monkeypatch)
    ied.advance_roadside_ieds(game, events=None)
    ieds = game.coin_state["ieds"]
    assert len(ieds) == 2
    # Deterministic alternation: the first plant is a static device, the second a VBIED.
    assert [i["kind"] for i in ieds] == ["ied", "vbied"]
    vbied = next(i for i in ieds if i["kind"] == "vbied")
    assert vbied["target"] == "CP1"  # the nearest (only) blue base
    assert any("VBIED" in m[1] and "intercept" in m[1].lower() for m in game.messages)


def test_static_plant_is_a_manned_emplacement_and_vbied_a_lone_vehicle(
    monkeypatch: Any,
) -> None:
    game = _two_road_ratline(monkeypatch)
    # A faction that fills the security team (the fake game has none).
    monkeypatch.setattr(
        ied, "ied_emplacement_unit_types", lambda g: ["device", "rifle", "rifle"]
    )
    ied.advance_roadside_ieds(game, events=None)
    static_kw, vbied_kw = game.spawn_kwargs
    # The static device spawns with room for the device + its security team; the
    # mobile VBIED is a lone vehicle.
    assert static_kw["max_units"] == ied.IED_EMPLACEMENT_UNITS
    assert vbied_kw["max_units"] == ied.VBIED_UNITS


def test_bare_device_kit_spawns_a_single_unit_not_cycled_copies(
    monkeypatch: Any,
) -> None:
    # A faction with no eligible infantry yields a 1-item kit (just the barrel);
    # the emplacement must then be sized to 1, or _retype_units would cycle the
    # device into three clustered copies.
    game = _ratline(monkeypatch)
    monkeypatch.setattr(ied, "ied_emplacement_unit_types", lambda g: ["device"])
    ied.advance_roadside_ieds(game, events=None)
    assert game.spawn_kwargs[0]["max_units"] == 1


def test_killing_the_device_clears_the_ied_even_if_the_team_survives(
    monkeypatch: Any,
) -> None:
    game = _ratline(monkeypatch)
    ied.advance_roadside_ieds(game, events=None)  # plant (a static device)
    tgo = game.db.tgos[game.coin_state["ieds"][0]["tgo_id"]]
    tgo.units = [
        _Unit(alive=False, is_static=True),  # the device, struck
        _Unit(alive=True),  # the security team, still there
        _Unit(alive=True),
    ]
    ied.advance_roadside_ieds(game, events=None)
    assert ied.consume_ied_detonations(game) == 0
    assert any("cleared" in m[1].lower() for m in game.messages)


def test_killing_the_team_alone_does_not_clear_the_device(monkeypatch: Any) -> None:
    game = _ratline(monkeypatch)
    ied.advance_roadside_ieds(game, events=None)  # plant (a static device)
    tgo = game.db.tgos[game.coin_state["ieds"][0]["tgo_id"]]
    tgo.units = [
        _Unit(alive=True, is_static=True),  # the device, untouched
        _Unit(alive=False),  # the team, killed
        _Unit(alive=False),
    ]
    # The bomb is still emplaced: the fuse keeps ticking to detonation.
    for _ in range(ied.FUSE_TURNS):
        ied.advance_roadside_ieds(game, events=None)
    assert ied.consume_ied_detonations(game) == 1


def test_vbied_has_a_shorter_fuse_than_a_static_ied(monkeypatch: Any) -> None:
    game = _ratline(monkeypatch)
    game.coin_state["ied_planted"] = 1  # force the next plant to be a VBIED
    ied.advance_roadside_ieds(game, events=None)
    assert game.coin_state["ieds"][0]["kind"] == "vbied"
    # A VBIED reaches friendly lines after VBIED_FUSE_TURNS (2), a turn sooner than a
    # buried IED's FUSE_TURNS (3).
    assert ied.VBIED_FUSE_TURNS < ied.FUSE_TURNS
    for _ in range(ied.VBIED_FUSE_TURNS):
        ied.advance_roadside_ieds(game, events=None)
    assert ied.consume_ied_detonations(game) == 1
    assert any("VBIED reached" in m[1] for m in game.messages)
