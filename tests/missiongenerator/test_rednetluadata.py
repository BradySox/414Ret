"""Red-net planner + emitter (dcsRetribution.redNet) — §70 C1's config.

Locks the plan the ``rednet`` plugin consumes: alive enemy ``comms``/
``commandcenter`` TGOs transmit, but only ``red_net_max_stations`` of them go
on the air (nearest blue territory, one slot anchored per kind); each net's
frequency is deterministic (same node name -> same spot on the dial every
mission), sits at x.500 MHz, skips GUARD's slot, keeps a 100 kHz guard band
clear of every channel the mission has allocated, reserves that band in the
RadioRegistry, and probes past collisions; the whole plan is gated on
``red_comms_net``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.luagenerator import LuaData, LuaValue
from game.missiongenerator.rednetluadata import (
    DEFAULT_MAX_STATIONS,
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
    at: tuple[float, float] = (1000.0, 2000.0),
) -> Any:
    units = [
        SimpleNamespace(unit_name=unit_name, alive=alive) for unit_name in unit_names
    ]
    return SimpleNamespace(
        category=category,
        groups=[SimpleNamespace(units=units)],
        position=_Point(*at),
        obj_name=name,
        concealed=concealed,
        coin_spawned=coin_spawned,
        map_hidden=map_hidden,
    )


def _game(
    tgos: list[Any],
    *,
    on: bool = True,
    blue_owned: bool = False,
    max_stations: Any = 99,
    blue_at: tuple[float, float] | None = None,
) -> Any:
    cp = SimpleNamespace(
        captured=SimpleNamespace(is_blue=blue_owned),
        ground_objects=tgos,
        name="Haina",
    )
    cps = [cp]
    if blue_at is not None:
        cps.append(
            SimpleNamespace(
                captured=SimpleNamespace(is_blue=True),
                ground_objects=[],
                name="Fulda",
                position=_Point(*blue_at),
            )
        )
    settings = SimpleNamespace(red_comms_net=on, red_net_max_stations=max_stations)
    return SimpleNamespace(
        settings=settings,
        theater=SimpleNamespace(controlpoints=cps),
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


def test_only_a_few_stations_go_on_the_air() -> None:
    # A theater-wide C2 net plus an insurgency is dozens of transmitters; the
    # band is shared with the whole comms plan, so only the cap goes up.
    tgos = [_tgo("comms", [f"u{i}"], name=f"node {i:02d}") for i in range(20)]
    plan = plan_red_net(_game(tgos, max_stations=3), RadioRegistry())
    assert plan is not None
    assert len(plan.nodes) == 3


def test_station_cap_defaults_when_the_setting_is_missing() -> None:
    # Old saves / headless fixtures carry no red_net_max_stations.
    game = _game([_tgo("comms", [f"u{i}"], name=f"node {i}") for i in range(9)])
    game.settings = SimpleNamespace(red_comms_net=True)
    plan = plan_red_net(game, RadioRegistry())
    assert plan is not None
    assert len(plan.nodes) == DEFAULT_MAX_STATIONS


def test_stations_nearest_blue_territory_win_the_slots() -> None:
    near = _tgo("comms", ["u1"], name="near node", at=(0.0, 0.0))
    far = _tgo("comms", ["u2"], name="far node", at=(400_000.0, 0.0))
    game = _game([far, near], max_stations=1, blue_at=(0.0, 5_000.0))
    plan = plan_red_net(game, RadioRegistry())
    assert plan is not None
    assert [node.name for node in plan.nodes] == ["near node"]


def test_a_crowd_of_cells_never_pushes_the_fixed_net_off_the_dial() -> None:
    # Every nearby station is a clandestine cell, the fixed C2 node is deep in
    # the rear -- one slot is still anchored to each kind.
    cells = [
        _tgo(
            "armor",
            [f"c{i}"],
            name=f"cell {i}",
            concealed=True,
            coin_spawned=True,
            at=(float(i * 100), 0.0),
        )
        for i in range(6)
    ]
    fixed = _tgo("comms", ["u1"], name="rear comms", at=(400_000.0, 0.0))
    game = _game(cells + [fixed], max_stations=2, blue_at=(0.0, 5_000.0))
    plan = plan_red_net(game, RadioRegistry())
    assert plan is not None
    kinds = {node.clandestine for node in plan.nodes}
    assert kinds == {True, False}
    assert "rear comms" in {node.name for node in plan.nodes}


def test_a_channel_one_detent_away_is_probed_past() -> None:
    # The half-MHz offset only dodges the whole-MHz inter-flight grid; aircraft
    # radios, ATC, and ATIS allocate on the 25 kHz grid, where x.500 and its
    # neighbours are ordinary slots.
    def one_node_plan(registry: RadioRegistry) -> float:
        game = _game([_tgo("comms", ["u1"], name="Sperenberg comms")])
        info = plan_red_net(game, registry)
        assert info is not None
        return info.nodes[0].freq_mhz

    natural = one_node_plan(RadioRegistry())
    blocked = RadioRegistry()
    blocked.reserve(RadioFrequency(int(natural * 1_000_000) + 25_000))
    assert one_node_plan(blocked) != natural


def test_the_guard_band_is_reserved_around_each_net() -> None:
    plan = plan_red_net(
        _game([_tgo("comms", ["u1"], name="Sperenberg comms")]),
        registry := RadioRegistry(),
    )
    assert plan is not None
    hertz = int(plan.nodes[0].freq_mhz * 1_000_000)
    # Nothing allocated later (ATIS runs after this plan) may land a briefed
    # channel on, or a detent beside, the carrier.
    for offset in (-100_000, -25_000, 0, 25_000, 100_000):
        assert RadioFrequency(hertz + offset) in registry.allocated_channels


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
