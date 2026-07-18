"""Red-net planner + emitter (dcsRetribution.redNet) — §70 C1's config.

Locks the plan the ``rednet`` plugin consumes: alive enemy ``comms``/
``commandcenter`` TGOs transmit; each net's frequency is deterministic (same
node name -> same spot on the dial every mission), sits at x.500 MHz (off the
whole-MHz grid blue channels allocate on), skips GUARD's slot, is reserved in
the mission's RadioRegistry, and probes past collisions; the whole plan is
gated on ``red_comms_net``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.luagenerator import LuaData, LuaValue
from game.missiongenerator.rednetluadata import (
    GUARD_SLOT_MHZ,
    RedNetInfo,
    RedNetNode,
    plan_red_net,
    populate_red_net_lua,
)
from game.radio.radios import RadioFrequency, RadioRegistry


def _kv(item: Any) -> dict[str, Any]:
    vals = item.value
    if isinstance(vals, LuaValue):
        vals = [vals]
    return {v.key: v.value for v in vals}


class _Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


def _tgo(
    category: str,
    unit_names: list[str],
    *,
    alive: bool = True,
    name: str = "C2 node",
    concealed: bool = False,
    coin_spawned: bool = False,
    map_hidden: bool = False,
) -> Any:
    units = [
        SimpleNamespace(unit_name=unit_name, alive=alive) for unit_name in unit_names
    ]
    return SimpleNamespace(
        category=category,
        groups=[SimpleNamespace(units=units)],
        position=_Point(1000.0, 2000.0),
        obj_name=name,
        concealed=concealed,
        coin_spawned=coin_spawned,
        map_hidden=map_hidden,
    )


def _game(tgos: list[Any], *, on: bool = True, blue_owned: bool = False) -> Any:
    cp = SimpleNamespace(
        captured=SimpleNamespace(is_blue=blue_owned),
        ground_objects=tgos,
        name="Haina",
    )
    return SimpleNamespace(
        settings=SimpleNamespace(red_comms_net=on),
        theater=SimpleNamespace(controlpoints=[cp]),
    )


def test_gated_off_by_the_setting() -> None:
    game = _game([_tgo("comms", ["u1"])], on=False)
    assert plan_red_net(game, RadioRegistry()) is None


def test_no_plan_without_an_alive_enemy_c2_node() -> None:
    dead = _game([_tgo("comms", ["u1"], alive=False)])
    blue_owned = _game([_tgo("comms", ["u1"])], blue_owned=True)
    wrong_category = _game([_tgo("aa", ["u1"])])
    assert plan_red_net(dead, RadioRegistry()) is None
    assert plan_red_net(blue_owned, RadioRegistry()) is None
    assert plan_red_net(wrong_category, RadioRegistry()) is None


def test_frequencies_are_offgrid_distinct_guardfree_and_reserved() -> None:
    game = _game(
        [
            _tgo("comms", ["0012 | Tower"], name="Sperenberg comms"),
            _tgo("commandcenter", ["0044 | Bunker"], name="Kastrup CC"),
        ]
    )
    registry = RadioRegistry()
    plan = plan_red_net(game, registry)
    assert plan is not None
    freqs = [node.freq_mhz for node in plan.nodes]
    assert len(freqs) == 2 and len(set(freqs)) == 2
    for mhz in freqs:
        # x.500 MHz: off the whole-MHz grid every blue channel allocates on.
        assert abs(mhz - int(mhz) - 0.5) < 1e-9
        assert int(mhz) != GUARD_SLOT_MHZ
        # Reserved, so a later allocation can never land on the net.
        assert RadioFrequency(int(mhz * 1_000_000)) in registry.allocated_channels


def test_frequencies_are_deterministic_across_missions() -> None:
    def plan() -> list[tuple[str, float]]:
        game = _game(
            [
                _tgo("comms", ["u1"], name="Sperenberg comms"),
                _tgo("commandcenter", ["u2"], name="Kastrup CC"),
            ]
        )
        info = plan_red_net(game, RadioRegistry())
        assert info is not None
        return [(node.name, node.freq_mhz) for node in info.nodes]

    assert plan() == plan()


def test_a_reserved_candidate_is_probed_past() -> None:
    def one_node_plan(registry: RadioRegistry) -> float:
        game = _game([_tgo("comms", ["u1"], name="Sperenberg comms")])
        info = plan_red_net(game, registry)
        assert info is not None
        return info.nodes[0].freq_mhz

    natural = one_node_plan(RadioRegistry())
    blocked = RadioRegistry()
    blocked.reserve(RadioFrequency(int(natural * 1_000_000)))
    probed = one_node_plan(blocked)
    assert probed != natural
    assert abs(probed - int(probed) - 0.5) < 1e-9


def test_coin_cells_transmit_as_clandestine_stations() -> None:
    cell = _tgo(
        "armor",
        ["0071 | Insurgent AK"],
        name="cell 3",
        concealed=True,
        coin_spawned=True,
    )
    game = _game([_tgo("comms", ["u1"], name="Haina comms"), cell])
    plan = plan_red_net(game, RadioRegistry())
    assert plan is not None
    by_name = {node.name: node for node in plan.nodes}
    assert by_name["cell 3"].clandestine is True
    assert by_name["Haina comms"].clandestine is False
    assert by_name["cell 3"].area == "Haina"


def test_concealed_comms_node_keys_the_clandestine_schedule() -> None:
    game = _game([_tgo("comms", ["u1"], name="field TX", concealed=True)])
    plan = plan_red_net(game, RadioRegistry())
    assert plan is not None
    assert plan.nodes[0].clandestine is True


def test_map_hidden_is_never_emitted() -> None:
    # §50 ambush teams (and any defensively map_hidden object) must never
    # transmit -- nothing telegraphs them.
    ambush = _tgo("armor", ["a1"], concealed=True, coin_spawned=True, map_hidden=True)
    hidden_comms = _tgo("comms", ["c1"], map_hidden=True)
    assert plan_red_net(_game([ambush, hidden_comms]), RadioRegistry()) is None


def test_populate_emits_the_stored_plan() -> None:
    plan = RedNetInfo(
        nodes=[
            RedNetNode(
                "CC", ["0012 | Tower", "0013 | Mast"], 10.0, 20.0, 271.5, False, "Haina"
            )
        ]
    )
    root = LuaData("dcsRetribution")
    populate_red_net_lua(root, SimpleNamespace(red_net=plan))  # type: ignore[arg-type]
    node = root.get_item("redNet")
    assert node is not None
    nodes = node.get_item("nodes")
    assert isinstance(nodes, LuaData)
    rec = _kv(nodes.objects[0])
    assert rec["name"] == "CC"
    assert rec["units"] == ["0012 | Tower", "0013 | Mast"]
    assert rec["x"] == "10.0" and rec["y"] == "20.0"
    assert rec["mhz"] == "271.5"
    assert rec["clandestine"] == "false"


def test_populate_without_a_plan_emits_nothing() -> None:
    root = LuaData("dcsRetribution")
    populate_red_net_lua(root, SimpleNamespace(red_net=None))  # type: ignore[arg-type]
    assert root.get_item("redNet") is None
