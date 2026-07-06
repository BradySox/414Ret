"""Comms-jam planner + emitter (dcsRetribution.commsJam) -- §51's config.

Locks the plan the ``commsjam`` plugin consumes: alive enemy ``comms``/
``commandcenter`` TGOs jam; the target list is the blue *briefed* channels
(human-crewed intra-flight first, then blue AWACS, then AI intra-flight) with
GUARD filtered and a hard cap; the JAM BACKUP channel is freshly allocated and
never in the jam list; and the whole plan is gated on ``enemy_comms_jamming``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from game.missiongenerator.commsjamluadata import (
    MAX_JAMMED_FREQUENCIES,
    CommsJamInfo,
    CommsJamJammer,
    plan_comms_jam,
    populate_comms_jam_lua,
)
from game.missiongenerator.luagenerator import LuaData, LuaValue
from game.radio.radios import MHz, RadioFrequency


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
) -> Any:
    units = [
        SimpleNamespace(unit_name=unit_name, alive=alive) for unit_name in unit_names
    ]
    return SimpleNamespace(
        category=category,
        groups=[SimpleNamespace(units=units)],
        position=_Point(1000.0, 2000.0),
        obj_name=name,
    )


def _game(
    tgos: list[Any],
    *,
    on: bool = True,
    blue_owned: bool = False,
    capture_gate: bool = False,
    pows: int = 0,
) -> Any:
    cp = SimpleNamespace(
        captured=SimpleNamespace(is_blue=blue_owned), ground_objects=tgos
    )
    return SimpleNamespace(
        settings=SimpleNamespace(
            enemy_comms_jamming=on, comms_jam_requires_capture=capture_gate
        ),
        theater=SimpleNamespace(controlpoints=[cp]),
        blue=SimpleNamespace(pending_pow_recoveries=[object()] * pows),
    )


def _flight(freq: RadioFrequency, *, blue: bool = True, client: bool = True) -> Any:
    return SimpleNamespace(
        friendly=SimpleNamespace(is_blue=blue),
        client_units=[object()] if client else [],
        intra_flight_channel=freq,
    )


def _awacs(freq: RadioFrequency, *, blue: bool = True) -> Any:
    return SimpleNamespace(blue=SimpleNamespace(is_blue=blue), freq=freq)


def _mission_data(flights: list[Any], awacs: Optional[list[Any]] = None) -> Any:
    return SimpleNamespace(flights=flights, awacs=awacs or [], comms_jam=None)


class _Registry:
    """Fake RadioRegistry: hands out the scripted freqs in order."""

    def __init__(self, freqs: list[RadioFrequency]) -> None:
        self._freqs = list(freqs)

    def alloc_uhf(self) -> RadioFrequency:
        return self._freqs.pop(0)


def test_plan_orders_channels_human_first_and_allocates_a_clean_backup() -> None:
    game = _game([_tgo("comms", ["0012 | Comms Tower"])])
    mission_data = _mission_data(
        [
            _flight(MHz(251), client=False),  # AI flight: listed after the humans
            _flight(MHz(252)),
            _flight(MHz(305), blue=False),  # red flight: never listed
        ],
        awacs=[_awacs(MHz(255)), _awacs(MHz(124), blue=False)],
    )
    plan = plan_comms_jam(game, mission_data, _Registry([MHz(271)]))  # type: ignore[arg-type]
    assert plan is not None
    assert [f.mhz for f in plan.frequencies] == [252.0, 255.0, 251.0]
    assert plan.backup is not None and plan.backup.mhz == 271.0
    assert len(plan.jammers) == 1
    assert plan.jammers[0].unit_names == ["0012 | Comms Tower"]
    assert plan.jammers[0].x == 1000.0 and plan.jammers[0].y == 2000.0


def test_gated_off_by_the_setting() -> None:
    game = _game([_tgo("comms", ["u1"])], on=False)
    mission_data = _mission_data([_flight(MHz(252))])
    assert plan_comms_jam(game, mission_data, _Registry([MHz(271)])) is None  # type: ignore[arg-type]


def test_no_plan_without_an_alive_enemy_c2_node() -> None:
    mission_data = _mission_data([_flight(MHz(252))])
    registry = _Registry([MHz(271)] * 5)
    dead = _game([_tgo("comms", ["u1"], alive=False)])
    blue_owned = _game([_tgo("comms", ["u1"])], blue_owned=True)
    wrong_category = _game([_tgo("aa", ["u1"])])
    assert plan_comms_jam(dead, mission_data, registry) is None  # type: ignore[arg-type]
    assert plan_comms_jam(blue_owned, mission_data, registry) is None  # type: ignore[arg-type]
    assert plan_comms_jam(wrong_category, mission_data, registry) is None  # type: ignore[arg-type]


def test_command_centers_jam_too() -> None:
    game = _game([_tgo("commandcenter", ["0044 | Bunker"], name="CC")])
    mission_data = _mission_data([_flight(MHz(252))])
    plan = plan_comms_jam(game, mission_data, _Registry([MHz(271)]))  # type: ignore[arg-type]
    assert plan is not None and plan.jammers[0].name == "CC"


def test_guard_is_never_jammed_and_the_list_is_capped() -> None:
    game = _game([_tgo("comms", ["u1"])])
    flights = [_flight(MHz(243)), _flight(MHz(121, 500))]
    flights += [_flight(MHz(250 + i)) for i in range(MAX_JAMMED_FREQUENCIES + 3)]
    plan = plan_comms_jam(game, _mission_data(flights), _Registry([MHz(400)]))  # type: ignore[arg-type]
    assert plan is not None
    mhz = [f.mhz for f in plan.frequencies]
    assert 243.0 not in mhz and 121.5 not in mhz
    assert len(mhz) == MAX_JAMMED_FREQUENCIES


def test_backup_reallocates_past_a_jammed_channel() -> None:
    # An exhausted registry can reuse a briefed channel; the planner must not
    # publish a jammed freq as the backup.
    game = _game([_tgo("comms", ["u1"])])
    mission_data = _mission_data([_flight(MHz(252))])
    plan = plan_comms_jam(game, mission_data, _Registry([MHz(252), MHz(271)]))  # type: ignore[arg-type]
    assert plan is not None
    assert plan.backup is not None and plan.backup.mhz == 271.0


def test_intel_gate_flags() -> None:
    mission_data = _mission_data([_flight(MHz(252))])
    tgos = [_tgo("comms", ["u1"])]

    # Gate off: ambient jamming, active whenever a node lives.
    plan = plan_comms_jam(_game(tgos), mission_data, _Registry([MHz(271)]))  # type: ignore[arg-type]
    assert plan is not None
    assert plan.capture_only is False and plan.active_from_start is True

    # Gate on, no POW held: dormant until an in-mission capture.
    plan = plan_comms_jam(
        _game(tgos, capture_gate=True), mission_data, _Registry([MHz(271)])  # type: ignore[arg-type]
    )
    assert plan is not None
    assert plan.capture_only is True and plan.active_from_start is False

    # Gate on, a POW held from an earlier turn: compromised from mission start.
    plan = plan_comms_jam(
        _game(tgos, capture_gate=True, pows=1),
        mission_data,
        _Registry([MHz(271)]),  # type: ignore[arg-type]
    )
    assert plan is not None
    assert plan.capture_only is True and plan.active_from_start is True


def test_no_plan_without_any_blue_channel() -> None:
    game = _game([_tgo("comms", ["u1"])])
    mission_data = _mission_data([_flight(MHz(305), blue=False)])
    assert plan_comms_jam(game, mission_data, _Registry([MHz(271)])) is None  # type: ignore[arg-type]


def test_populate_emits_the_stored_plan() -> None:
    plan = CommsJamInfo(
        jammers=[CommsJamJammer("CC", ["0012 | Tower", "0013 | Mast"], 10.0, 20.0)],
        frequencies=[MHz(252), MHz(30)],
        backup=MHz(271),
    )
    root = LuaData("dcsRetribution")
    populate_comms_jam_lua(root, None, SimpleNamespace(comms_jam=plan))  # type: ignore[arg-type]
    node = root.get_item("commsJam")
    assert node is not None
    jammers = node.get_item("jammers")
    assert isinstance(jammers, LuaData)
    rec = _kv(jammers.objects[0])
    assert rec["name"] == "CC"
    assert rec["units"] == ["0012 | Tower", "0013 | Mast"]
    assert rec["x"] == "10.0" and rec["y"] == "20.0"
    freqs = node.get_item("freqs")
    assert isinstance(freqs, LuaData)
    assert [_kv(f)["mhz"] for f in freqs.objects] == ["252.0", "30.0"]
    assert [_kv(f)["mod"] for f in freqs.objects] == ["AM", "AM"]
    backup = node.get_item("backupMhz")
    assert backup is not None and isinstance(backup.value, LuaValue)
    assert backup.value.value == "271.0"
    capture_only = node.get_item("captureOnly")
    assert capture_only is not None and isinstance(capture_only.value, LuaValue)
    assert capture_only.value.value == "false"
    active = node.get_item("activeFromStart")
    assert active is not None and isinstance(active.value, LuaValue)
    assert active.value.value == "true"


def test_populate_without_a_plan_emits_nothing() -> None:
    root = LuaData("dcsRetribution")
    populate_comms_jam_lua(root, None, SimpleNamespace(comms_jam=None))  # type: ignore[arg-type]
    assert root.get_item("commsJam") is None
