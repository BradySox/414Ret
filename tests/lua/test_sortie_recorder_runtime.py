"""Headless runtime check for the sortie recorder (seam 1).

Pins the "script errors and the feature silently never starts" invariant plus the
contract Python parses against: one record per flight group keyed by group name,
a downsampled track carrying time/position/altitude/fuel, shot and hit counters,
and a hard cap on track length so a long mission cannot grow state.json without
bound.

The recorder depends on nothing outside vanilla DCS. It must never require
Tacview, which is a paid third-party program.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/base/sortie_recorder.lua"


def _flight(name: str, side: int, x: float = 0.0, z: float = 0.0) -> dict[str, Any]:
    return {
        "name": name,
        "side": side,
        "category": 0,  # AIRPLANE
        "units": [
            {
                "name": name + "-1",
                "type": "FA-18C_hornet",
                "x": x,
                "z": z,
                "alt": 6000,
                "fuel": 0.8,
            }
        ],
    }


def _load(harness: DcsPluginHarness) -> None:
    harness.load_plugin_script(PLUGIN)
    harness.assert_no_lua_errors()


def _records(harness: DcsPluginHarness) -> dict[str, Any]:
    raw = harness.to_python(harness.lua.eval("sortie_records"))
    assert isinstance(raw, dict)
    flights = raw.get("flights") or {}
    assert isinstance(flights, dict)
    return flights


def test_the_script_loads_without_erroring() -> None:
    harness = DcsPluginHarness()
    _load(harness)

    assert harness.to_python(harness.lua.eval("sortie_records.version")) == 1


def test_a_sweep_records_one_entry_per_flight() -> None:
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_flight("Enfield 1-1", side=2, x=100, z=200))
    harness.add_group(_flight("Springfield 1-1", side=1, x=-500, z=900))

    harness.lua.eval("sortie_recorder_sample")()
    harness.assert_no_lua_errors()

    flights = _records(harness)
    assert set(flights) == {"Enfield 1-1", "Springfield 1-1"}


def test_a_record_carries_type_coalition_and_a_track_sample() -> None:
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_flight("Enfield 1-1", side=2, x=100, z=200))

    harness.lua.eval("sortie_recorder_sample")()

    record = _records(harness)["Enfield 1-1"]
    assert record["type"] == "FA-18C_hornet"
    assert record["coalition"] == 2
    track = record["track"]
    assert len(track) == 1
    assert track[0]["x"] == 100
    assert track[0]["z"] == 200
    assert track[0]["alt"] == 6000
    assert track[0]["fuel"] == 0.8


def test_repeated_sweeps_build_a_track() -> None:
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_flight("Enfield 1-1", side=2, x=0, z=0))

    sample = harness.lua.eval("sortie_recorder_sample")
    for step in range(4):
        harness.advance_to(step * 30.0)
        harness.update_unit("Enfield 1-1", {"x": step * 1000.0})
        sample()
    harness.assert_no_lua_errors()

    record = _records(harness)["Enfield 1-1"]
    assert len(record["track"]) == 4
    assert record["first_seen"] == 0.0
    assert record["last_seen"] == 90.0
    # The track follows the aircraft, not the spawn point.
    assert [sample["x"] for sample in record["track"]] == [0.0, 1000.0, 2000.0, 3000.0]


def test_shots_and_hits_are_counted_against_the_firing_group() -> None:
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_flight("Enfield 1-1", side=2))
    harness.add_group(_flight("Springfield 1-1", side=1))

    on_shot = harness.lua.eval("sortie_recorder_on_shot")
    on_hit = harness.lua.eval("sortie_recorder_on_hit")
    shooter = harness.lua.eval('Unit.getByName("Enfield 1-1-1")')
    on_shot(shooter)
    on_shot(shooter)
    on_hit(shooter)
    harness.assert_no_lua_errors()

    flights = _records(harness)
    assert flights["Enfield 1-1"]["shots"] == 2
    assert flights["Enfield 1-1"]["hits"] == 1
    assert "Springfield 1-1" not in flights


def test_an_ejection_is_recorded_on_the_flight() -> None:
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_flight("Enfield 1-1", side=2))

    harness.lua.eval("sortie_recorder_on_ejection")(
        harness.lua.eval('Unit.getByName("Enfield 1-1-1")')
    )
    harness.assert_no_lua_errors()

    assert _records(harness)["Enfield 1-1"]["ejected"] is True


def test_the_track_is_capped_so_state_json_cannot_grow_without_bound() -> None:
    """A three-hour mission must not produce an unbounded table.

    state.json is rewritten every 15 seconds, so an uncapped track costs disk
    and encode time on every write.
    """
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_flight("Enfield 1-1", side=2))

    sample = harness.lua.eval("sortie_recorder_sample")
    for step in range(260):
        harness.advance_to(step * 30.0)
        sample()
    harness.assert_no_lua_errors()

    record = _records(harness)["Enfield 1-1"]
    assert len(record["track"]) == 240
    # The newest sample survives; the oldest were dropped.
    assert record["last_seen"] == 259 * 30.0


def test_a_missing_initiator_is_ignored_rather_than_raising() -> None:
    harness = DcsPluginHarness()
    _load(harness)

    harness.lua.eval("sortie_recorder_on_shot")(None)
    harness.lua.eval("sortie_recorder_on_hit")(None)
    harness.lua.eval("sortie_recorder_on_ejection")(None)
    harness.assert_no_lua_errors()

    assert _records(harness) == {}


def test_a_sweep_with_no_aircraft_is_a_clean_no_op() -> None:
    harness = DcsPluginHarness()
    _load(harness)

    harness.lua.eval("sortie_recorder_sample")()
    harness.assert_no_lua_errors()

    assert _records(harness) == {}


def test_sampling_marks_the_state_dirty_so_it_gets_written() -> None:
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_flight("Enfield 1-1", side=2))

    harness.lua.execute("dirty_state = false")
    harness.lua.eval("sortie_recorder_sample")()

    assert harness.to_python(harness.lua.eval("dirty_state")) is True
