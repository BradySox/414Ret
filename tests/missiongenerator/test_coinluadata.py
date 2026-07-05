"""COIN in-mission liveliness emitter (dcsRetribution.coin).

Locks the shape the ``coin`` plugin consumes: a live HVT convoy emits its DCS group
name(s) + centre; each **mobile** VBIED emits its group(s) + position + the nearest
friendly base as a drive target; **static** roadside IEDs are never emitted (they don't
move); dispersed field cells emit as wanderers and the live re-infiltration cell as a
creeper; harassment emits the blue bases inside a stronghold's mortar reach with the
player-spawn fields hard-excluded; and the whole node is gated on ``coin_insurgency``
plus the per-object toggles, so a non-COIN mission carries no ``coin`` node at all.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.coinluadata import populate_coin_lua
from game.missiongenerator.luagenerator import LuaData, LuaValue


def _kv(item: Any) -> dict[str, Any]:
    vals = item.value
    if isinstance(vals, LuaValue):
        vals = [vals]
    return {v.key: v.value for v in vals}


class _Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def distance_to_point(self, other: "_Point") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


def _tgo(tgo_id: str, group_name: str, pos: _Point) -> Any:
    return SimpleNamespace(
        id=tgo_id,
        groups=[SimpleNamespace(group_name=group_name)],
        position=pos,
    )


def _cp(kind: str, pos: _Point, tgos: list[Any], cp_id: str = "cp") -> Any:
    return SimpleNamespace(
        id=cp_id,
        name=cp_id,
        full_name=cp_id,
        captured=SimpleNamespace(is_blue=(kind == "blue"), is_red=(kind == "red")),
        position=pos,
        ground_objects=tgos,
    )


def _game(*, insurgency: bool = True, hvt: bool = True, ied: bool = True) -> Any:
    hvt_tgo = _tgo("hvt1", "0042 | HVT Qari", _Point(100.0, 200.0))
    vbied_tgo = _tgo("vbied1", "0051 | VBIED", _Point(300.0, 400.0))
    static_tgo = _tgo("ied1", "0052 | IED", _Point(500.0, 600.0))
    red = _cp("red", _Point(300.0, 0.0), [hvt_tgo, vbied_tgo, static_tgo])
    blue = _cp("blue", _Point(0.0, 0.0), [])
    return SimpleNamespace(
        settings=SimpleNamespace(
            coin_insurgency=insurgency, coin_hvt=hvt, coin_ied=ied
        ),
        coin_state={
            "hvt": {"active": {"tgo_id": "hvt1", "name": "Qari"}},
            "ieds": [
                {"tgo_id": "ied1", "kind": "ied"},  # static -> never emitted
                {"tgo_id": "vbied1", "kind": "vbied", "target": "Base"},
            ],
        },
        theater=SimpleNamespace(controlpoints=[red, blue]),
    )


def _populate(game: Any) -> LuaData:
    root = LuaData("dcsRetribution")
    populate_coin_lua(root, game, mission_data=None)  # type: ignore[arg-type]
    return root


def test_emits_hvt_convoy_and_mobile_vbied() -> None:
    coin = _populate(_game()).get_item("coin")
    assert coin is not None

    hvt = coin.get_item("hvt")
    assert hvt is not None
    hvt_kv = _kv(hvt)
    assert hvt_kv["groups"] == ["0042 | HVT Qari"]
    assert hvt_kv["x"] == "100.0" and hvt_kv["y"] == "200.0"

    vbieds = coin.get_item("vbieds")
    # LuaData (the array collection) carries the emitted objects; get_item is typed
    # to the LuaItem base, so narrow to reach .objects.
    assert isinstance(vbieds, LuaData)
    # Exactly one mobile VBIED -- the static IED is not a mover, so it isn't emitted.
    assert len(vbieds.objects) == 1
    v = _kv(vbieds.objects[0])
    assert v["groups"] == ["0051 | VBIED"]
    assert v["x"] == "300.0" and v["y"] == "400.0"
    # Drive target is the nearest friendly base (the blue CP at the origin).
    assert v["targetX"] == "0.0" and v["targetY"] == "0.0"


def test_gated_off_when_coin_insurgency_off() -> None:
    assert _populate(_game(insurgency=False)).get_item("coin") is None


def test_hvt_toggle_off_drops_only_the_hvt() -> None:
    coin = _populate(_game(hvt=False)).get_item("coin")
    assert coin is not None
    assert coin.get_item("hvt") is None
    assert coin.get_item("vbieds") is not None


def test_ied_toggle_off_drops_only_the_vbieds() -> None:
    coin = _populate(_game(ied=False)).get_item("coin")
    assert coin is not None
    assert coin.get_item("hvt") is not None
    assert coin.get_item("vbieds") is None


def test_no_movers_emits_no_node() -> None:
    game = _game()
    game.coin_state = {
        "hvt": {"active": None},
        "ieds": [{"tgo_id": "x", "kind": "ied"}],
    }
    assert _populate(game).get_item("coin") is None


# --- cell movers (dispersed wanderers + the re-infiltration creeper) -----------------


def _cell_game(*, dispersed: bool = True, reinfil: bool = True) -> Any:
    cell_tgo = _tgo("cell1", "0060 | Field Cell", _Point(700.0, 800.0))
    infil_tgo = _tgo("infil1", "0061 | Infiltrators", _Point(900.0, 1000.0))
    red = _cp("red", _Point(300.0, 0.0), [cell_tgo, infil_tgo], cp_id="stronghold")
    blue = _cp("blue", _Point(0.0, 0.0), [], cp_id="fob")
    return SimpleNamespace(
        settings=SimpleNamespace(
            coin_insurgency=True,
            coin_dispersed_cells=dispersed,
            coin_reinfiltration=reinfil,
        ),
        coin_state={
            "field_cells": [{"tgo_id": "cell1", "age": 1, "home_id": "stronghold"}],
            "reinfiltration": {
                "cooldown": 0,
                "active": {"cp_id": "fob", "cell_tgo": "infil1", "stage": 1},
            },
        },
        theater=SimpleNamespace(controlpoints=[red, blue]),
    )


def test_emits_wandering_cells_and_the_creeping_infiltrator() -> None:
    coin = _populate(_cell_game()).get_item("coin")
    assert coin is not None

    cells = coin.get_item("cells")
    assert isinstance(cells, LuaData)
    assert len(cells.objects) == 1
    c = _kv(cells.objects[0])
    assert c["groups"] == ["0060 | Field Cell"]
    assert c["x"] == "700.0" and c["y"] == "800.0"

    infil = coin.get_item("infiltrators")
    assert isinstance(infil, LuaData)
    assert len(infil.objects) == 1
    rec = _kv(infil.objects[0])
    assert rec["groups"] == ["0061 | Infiltrators"]
    assert rec["x"] == "900.0" and rec["y"] == "1000.0"
    # Creep target = the base being infiltrated (the blue CP at the origin).
    assert rec["targetX"] == "0.0" and rec["targetY"] == "0.0"


def test_cell_toggles_gate_their_nodes() -> None:
    coin = _populate(_cell_game(dispersed=False)).get_item("coin")
    assert coin is not None
    assert coin.get_item("cells") is None
    assert coin.get_item("infiltrators") is not None

    coin = _populate(_cell_game(reinfil=False)).get_item("coin")
    assert coin is not None
    assert coin.get_item("infiltrators") is None
    assert coin.get_item("cells") is not None


# --- harassment (insurgent indirect fire on forward bases) ---------------------------


def _harass_game(*, harass: bool = True, with_red: bool = True) -> Any:
    from game.theater import ControlPointType

    red = _cp("red", _Point(0.0, 0.0), [], cp_id="Stronghold")
    near_fob = _cp("blue", _Point(20_000.0, 0.0), [], cp_id="FOB Near")
    far_fob = _cp("blue", _Point(300_000.0, 0.0), [], cp_id="FOB Far")
    player_field = _cp("blue", _Point(10_000.0, 0.0), [], cp_id="Player Field")
    for cp in (red, near_fob, far_fob, player_field):
        cp.cptype = ControlPointType.FOB
    cps = [near_fob, far_fob, player_field] + ([red] if with_red else [])

    client_flight = SimpleNamespace(
        client_count=1, departure=player_field, arrival=player_field, divert=None
    )
    coalition = SimpleNamespace(
        ato=SimpleNamespace(packages=[SimpleNamespace(flights=[client_flight])])
    )
    return SimpleNamespace(
        settings=SimpleNamespace(coin_insurgency=True, coin_harassment=harass),
        coin_state={},
        theater=SimpleNamespace(controlpoints=cps),
        coalitions=[coalition],
    )


def test_harassment_emits_bases_in_stronghold_reach_only() -> None:
    coin = _populate(_harass_game()).get_item("coin")
    assert coin is not None
    harass = coin.get_item("harassment")
    assert harass is not None

    bases = harass.get_item("bases")
    assert isinstance(bases, LuaData)
    names = [_kv(b)["name"] for b in bases.objects]
    # Only the near FOB: the far one is out of mortar reach, and the player-spawn
    # field is hard-excluded even though it is nearest the stronghold.
    assert names == ["FOB Near"]

    excluded = harass.get_item("excludedBases")
    assert isinstance(excluded, LuaData)
    excluded_names = set()
    for obj in excluded.objects:
        val = obj.value
        assert isinstance(val, LuaValue)
        excluded_names.add(val.value)
    assert excluded_names == {"Player Field"}


def test_harassment_gated_by_its_toggle_and_by_red_presence() -> None:
    assert _populate(_harass_game(harass=False)).get_item("coin") is None
    # All strongholds cleared -> the fire falls silent (no node at all).
    assert _populate(_harass_game(with_red=False)).get_item("coin") is None
