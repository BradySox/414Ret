"""Decoy suspected-activity zones (§79): budget, per-turn refresh, burn-on-recon.

The advance/burn/budget logic runs against SimpleNamespace fakes with the real
`_spawn_decoy` monkeypatched (as in the COIN advance tests); one test drives the
real `_spawn_decoy` against fakes to lock the unitless + concealed + is_decoy shape
that keeps the AI immune and the circle rendering.
"""

from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any

import pytest

import game.fourteenth.decoy_zones as dz


class _Player:
    def __init__(self, red: bool) -> None:
        self._red = red

    @property
    def is_red(self) -> bool:
        return self._red


class _Point:
    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x = x
        self.y = y

    def point_from_heading(self, heading_deg: float, dist: float) -> "_Point":
        rad = math.radians(heading_deg)
        return _Point(self.x + dist * math.cos(rad), self.y + dist * math.sin(rad))


class _CP:
    def __init__(self, name: str, red: bool = True, front: bool = True) -> None:
        self.name = name
        self._red = red
        self.has_active_frontline = front
        self.position = _Point(0.0, 0.0)
        self.connected_objectives: list[Any] = []

    @property
    def captured(self) -> _Player:
        return _Player(self._red)


class _Tgos:
    def __init__(self) -> None:
        self.d: dict[Any, Any] = {}

    def add(self, tgo_id: Any, tgo: Any) -> None:
        self.d[tgo_id] = tgo

    def remove(self, tgo_id: Any) -> None:
        self.d.pop(tgo_id, None)


def _game(cps: list[_CP], *, on: bool = True, count: int = 4) -> Any:
    game = SimpleNamespace(
        turn=5,
        campaign_name=None,  # no campaign block -> use the setting count
        settings=SimpleNamespace(decoy_zones=on, decoy_zone_count=count),
        theater=SimpleNamespace(
            controlpoints=cps,
            is_on_land=lambda point: True,
            heading_to_conflict_from=lambda point: None,
        ),
        db=SimpleNamespace(tgos=_Tgos()),
        messages=[],
    )
    game.message = lambda title, text="": game.messages.append((title, text))
    return game


def _fake_spawn(monkeypatch: Any) -> list[Any]:
    created: list[Any] = []

    def _spawn(game: Any, red_cp: _CP, point: Any, events: Any) -> Any:
        tgo = SimpleNamespace(
            id=f"decoy{len(created)}",
            is_decoy=True,
            concealed=True,
            discovered_by_player=False,
            control_point=red_cp,
            groups=[],
        )
        red_cp.connected_objectives.append(tgo)
        game.db.tgos.add(tgo.id, tgo)
        created.append(tgo)
        return tgo

    monkeypatch.setattr(dz, "_spawn_decoy", _spawn)
    return created


# --------------------------------------------------------------------------
# The parser + budget resolution
# --------------------------------------------------------------------------


def test_parse_config_reads_budget_and_hints() -> None:
    cfg = dz.parse_decoy_config({"budget": 6, "near_cps": ["Haina", "Wittstock"]})
    assert cfg.budget == 6
    assert cfg.near_cps == ("Haina", "Wittstock")


def test_parse_config_empty_is_no_plan() -> None:
    assert dz.parse_decoy_config(None).budget is None
    assert dz.parse_decoy_config({}).budget is None


def test_parse_config_malformed_raises() -> None:
    with pytest.raises(ValueError):
        dz.parse_decoy_config([1, 2, 3])  # a list, not a mapping
    with pytest.raises(ValueError):
        dz.parse_decoy_config({"near_cps": "Haina"})  # not a list


def test_budget_falls_back_to_the_setting_and_clamps(monkeypatch: Any) -> None:
    monkeypatch.setattr(dz, "config_for", lambda game: dz.DecoyConfig(budget=None))
    assert dz._budget_for(_game([], count=4)) == 4
    # A fat authored/settings budget is clamped to the sanity bound.
    assert dz._budget_for(_game([], count=99)) == dz.MAX_DECOY_BUDGET


def test_config_block_budget_overrides_the_setting(monkeypatch: Any) -> None:
    monkeypatch.setattr(dz, "config_for", lambda game: dz.DecoyConfig(budget=6))
    assert dz._budget_for(_game([], count=4)) == 6


# --------------------------------------------------------------------------
# Placement candidates
# --------------------------------------------------------------------------


def test_candidates_prefer_front_adjacent_red_cps(monkeypatch: Any) -> None:
    monkeypatch.setattr(dz, "config_for", lambda game: dz.DecoyConfig(budget=None))
    front = _CP("Front", red=True, front=True)
    rear = _CP("Rear", red=True, front=False)
    blue = _CP("Blue", red=False, front=True)
    got = dz._candidate_red_cps(_game([front, rear, blue]))
    assert got == [front]  # blue excluded, rear deprioritized


def test_candidates_fall_back_to_any_red_land_when_no_front(monkeypatch: Any) -> None:
    monkeypatch.setattr(dz, "config_for", lambda game: dz.DecoyConfig(budget=None))
    a = _CP("A", red=True, front=False)
    b = _CP("B", red=True, front=False)
    got = dz._candidate_red_cps(_game([a, b]))
    assert set(got) == {a, b}


# --------------------------------------------------------------------------
# The turn loop: gate, top-up, burn, refill
# --------------------------------------------------------------------------


def test_off_switch_is_a_noop(monkeypatch: Any) -> None:
    created = _fake_spawn(monkeypatch)
    game = _game([_CP("Front")], on=False)
    dz.advance_decoy_zones(game, events=None)
    assert created == []


def test_tops_up_to_the_budget(monkeypatch: Any) -> None:
    created = _fake_spawn(monkeypatch)
    game = _game([_CP("Front")], count=4)
    dz.advance_decoy_zones(game, events=None)
    assert len(created) == 4
    assert len(dz._all_decoys(game)) == 4
    # Running again is idempotent -- already at budget, nothing new.
    dz.advance_decoy_zones(game, events=None)
    assert len(created) == 4


def test_burns_reconned_decoys_and_refills(monkeypatch: Any) -> None:
    created = _fake_spawn(monkeypatch)
    game = _game([_CP("Front")], count=4)
    dz.advance_decoy_zones(game, events=None)
    assert len(dz._all_decoys(game)) == 4
    # The player reconned two of them -> discovery flag set at debrief.
    created[0].discovered_by_player = True
    created[1].discovered_by_player = True
    dz.advance_decoy_zones(game, events=None)
    # The two feints are burned (removed) and two fresh ones replace them.
    assert len(dz._all_decoys(game)) == 4
    assert all(not t.discovered_by_player for t in dz._all_decoys(game))
    burns = [m for m in game.messages if "decoy" in m[1].lower()]
    assert len(burns) == 2


def test_budget_clamped_when_the_setting_is_huge(monkeypatch: Any) -> None:
    created = _fake_spawn(monkeypatch)
    game = _game([_CP("Front")], count=999)
    dz.advance_decoy_zones(game, events=None)
    assert len(created) == dz.MAX_DECOY_BUDGET


def test_no_red_cp_is_a_safe_noop(monkeypatch: Any) -> None:
    created = _fake_spawn(monkeypatch)
    game = _game([_CP("Blue", red=False)], count=4)
    dz.advance_decoy_zones(game, events=None)
    assert created == []


def test_decoys_on_a_captured_cp_are_swept_silently(monkeypatch: Any) -> None:
    _fake_spawn(monkeypatch)
    cp = _CP("Front", red=True)
    game = _game([cp], count=4)
    dz.advance_decoy_zones(game, events=None)
    assert len(dz._all_decoys(game)) == 4
    # The host CP flips to blue: its defunct feints are cleaned up without a
    # "decoy" report (the player didn't recon them), and nothing red is left to
    # refill onto.
    cp._red = False
    dz.advance_decoy_zones(game, events=None)
    assert dz._all_decoys(game) == []
    assert not any("decoy" in m[1].lower() for m in game.messages)


# --------------------------------------------------------------------------
# The real spawn: a unitless, concealed, is_decoy marker (AI-immune by construction)
# --------------------------------------------------------------------------


def test_spawn_decoy_is_a_unitless_concealed_marker(monkeypatch: Any) -> None:
    class _FakeTGO:
        def __init__(self, name: str, location: Any, cp: Any, task: Any) -> None:
            self.id = "d1"
            self.name = name
            self.control_point = cp
            self.groups: list[Any] = []  # unitless by construction
            self.concealed = False
            self.is_decoy = False

    monkeypatch.setattr(
        "game.theater.theatergroundobject.VehicleGroupGroundObject", _FakeTGO
    )
    monkeypatch.setattr(
        "game.naming.namegen",
        SimpleNamespace(random_objective_name=lambda: "Feint-1"),
    )
    monkeypatch.setattr(
        "game.theater.PresetLocation",
        lambda name, point, heading: SimpleNamespace(original_name=name),
    )

    cp = _CP("Front")
    game = _game([cp])
    tgo = dz._spawn_decoy(game, cp, cp.position, events=None)  # type: ignore[arg-type]

    assert tgo.concealed is True
    assert tgo.is_decoy is True
    assert tgo.groups == []  # no units -> is_dead() True -> AI skips it for free
    assert tgo in cp.connected_objectives
    assert game.db.tgos.d[tgo.id] is tgo
