"""Headless runtime check for the sortie recorder (seam 1).

Pins the "script errors and the feature silently never starts" invariant plus the
contract Python parses against: one record per AIRCRAFT keyed by unit name and
carrying its group, a downsampled track with time/position/altitude/fuel, shot
and hit counters, and a cap on track length.

Two of these exist because the first version was wrong:

* Records used to be keyed by group and sample `units[1]`. `getUnits()` returns
  only the living units, so the lead dying moved the track onto a wingman and
  counted the jump as distance flown. Every human slot is now sampled; AI groups
  hold one anchor jet until it dies.
* The track used to ride on every write. `state.json` is rewritten every 15 s, so
  a 60v60 track set meant ~1 MB of `json:encode` on the sim thread, 480 times.
  It now rides only on the final write.

The recorder depends on nothing outside vanilla DCS. It must never require
Tacview, which is a paid third-party program.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/base/sortie_recorder.lua"


def _unit(name: str, **overrides: Any) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "name": name,
        "type": "FA-18C_hornet",
        "x": 0.0,
        "z": 0.0,
        "alt": 6000,
        "fuel": 0.8,
    }
    spec.update(overrides)
    return spec


def _flight(name: str, side: int, units: list[dict[str, Any]]) -> dict[str, Any]:
    return {"name": name, "side": side, "category": 0, "units": units}


def _ai_pair(name: str, side: int = 2) -> dict[str, Any]:
    return _flight(name, side, [_unit(f"{name}-1"), _unit(f"{name}-2")])


def _weapon(harness: DcsPluginHarness, name: str) -> Any:
    """A weapon the recorder can key on, so a hit matches back to its shot.

    Only getName is exercised -- that is the whole contract the recorder needs.
    """
    return harness.lua.eval(
        "function(n) return { getName = function(self) return n end } end"
    )(name)


def _load(harness: DcsPluginHarness) -> None:
    harness.load_plugin_script(PLUGIN)
    harness.assert_no_lua_errors()


def _records(harness: DcsPluginHarness) -> dict[str, Any]:
    raw = harness.to_python(harness.lua.eval("sortie_records"))
    assert isinstance(raw, dict)
    flights = raw.get("flights") or {}
    assert isinstance(flights, dict)
    return flights


def _sample(harness: DcsPluginHarness) -> None:
    harness.lua.eval("sortie_recorder_sample")()
    harness.assert_no_lua_errors()


def test_the_script_loads_without_erroring() -> None:
    harness = DcsPluginHarness()
    _load(harness)

    assert harness.to_python(harness.lua.eval("sortie_records.version")) == 1


def test_an_ai_pair_produces_one_track() -> None:
    """Formation wingmen fly the lead's track; paying per-unit buys nothing."""
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_ai_pair("Enfield 1-1"))

    _sample(harness)

    flights = _records(harness)
    assert set(flights) == {"Enfield 1-1-1"}
    assert flights["Enfield 1-1-1"]["group"] == "Enfield 1-1"
    assert flights["Enfield 1-1-1"]["player"] is False


def test_every_human_in_one_group_gets_its_own_track() -> None:
    """Four humans in a group do not fly the same track."""
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(
        _flight(
            "Enfield 1-1",
            2,
            [_unit(f"Enfield 1-1-{n}", playerName=f"Pilot{n}") for n in range(1, 5)],
        )
    )

    _sample(harness)

    flights = _records(harness)
    assert set(flights) == {f"Enfield 1-1-{n}" for n in range(1, 5)}
    assert all(record["player"] is True for record in flights.values())
    assert all(record["group"] == "Enfield 1-1" for record in flights.values())


def test_humans_and_ai_in_the_same_group_are_both_covered() -> None:
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(
        _flight(
            "Enfield 1-1",
            2,
            [
                _unit("Enfield 1-1-1"),
                _unit("Enfield 1-1-2", playerName="Maverick"),
                _unit("Enfield 1-1-3"),
            ],
        )
    )

    _sample(harness)

    flights = _records(harness)
    # The human, plus one anchor for the AI half.
    assert flights["Enfield 1-1-2"]["player"] is True
    assert len(flights) == 2


def test_the_track_never_jumps_when_the_lead_dies() -> None:
    """The bug this keying exists to prevent.

    Keyed by group and sampling `units[1]`, the lead dying moved the track onto
    the wingman's position and counted the jump as distance flown.
    """
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(
        _flight(
            "Enfield 1-1",
            2,
            [
                _unit("Enfield 1-1-1", x=0.0),
                _unit("Enfield 1-1-2", x=500_000.0),
            ],
        )
    )

    harness.advance_to(0.0)
    _sample(harness)
    # The lead is destroyed; getUnits now returns the wingman at index 1.
    harness.update_unit("Enfield 1-1", {"exists": False}, unit_index=1)
    harness.advance_to(30.0)
    _sample(harness)

    flights = _records(harness)
    lead = flights["Enfield 1-1-1"]
    # The lead's own track holds its own positions only -- no teleport.
    assert all(sample["x"] == 0.0 for sample in lead["track"])
    # The wingman, if it became the anchor, is a separate record with its own
    # first_seen. It never contaminates the lead's.
    for unit_name, record in flights.items():
        if unit_name != "Enfield 1-1-1":
            assert all(sample["x"] == 500_000.0 for sample in record["track"])


def test_the_anchor_is_held_rather_than_read_off_an_index() -> None:
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_ai_pair("Enfield 1-1"))

    for step in range(3):
        harness.advance_to(step * 30.0)
        _sample(harness)

    # Still exactly one AI record after several sweeps.
    assert set(_records(harness)) == {"Enfield 1-1-1"}


def test_a_record_carries_type_coalition_and_a_track_sample() -> None:
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_flight("Enfield 1-1", 2, [_unit("Enfield 1-1-1", x=100, z=200)]))

    _sample(harness)

    record = _records(harness)["Enfield 1-1-1"]
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
    harness.add_group(_flight("Enfield 1-1", 2, [_unit("Enfield 1-1-1")]))

    for step in range(4):
        harness.advance_to(step * 30.0)
        harness.update_unit("Enfield 1-1", {"x": step * 1000.0})
        _sample(harness)

    record = _records(harness)["Enfield 1-1-1"]
    assert len(record["track"]) == 4
    assert record["first_seen"] == 0.0
    assert record["last_seen"] == 90.0
    assert [s["x"] for s in record["track"]] == [0.0, 1000.0, 2000.0, 3000.0]


def test_shots_and_hits_are_counted_against_the_firing_aircraft() -> None:
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_ai_pair("Enfield 1-1"))
    harness.add_group(_ai_pair("Springfield 1-1", side=1))

    on_shot = harness.lua.eval("sortie_recorder_on_shot")
    on_hit = harness.lua.eval("sortie_recorder_on_hit")
    wingman = harness.lua.eval('Unit.getByName("Enfield 1-1-2")')
    first = _weapon(harness, "AIM-120C #1")
    second = _weapon(harness, "AIM-120C #2")
    on_shot(wingman, first)
    on_shot(wingman, second)
    on_hit(wingman, first)
    harness.assert_no_lua_errors()

    flights = _records(harness)
    # The wingman is never position-sampled, but its weapons still count and it
    # carries its group so the flight's totals add up.
    assert flights["Enfield 1-1-2"]["shots"] == 2
    assert flights["Enfield 1-1-2"]["hits"] == 1
    assert flights["Enfield 1-1-2"]["group"] == "Enfield 1-1"
    # An empty Lua table converts to {}, not [].
    assert not flights["Enfield 1-1-2"]["track"]
    assert "Springfield 1-1-1" not in flights


def test_a_ground_unit_that_shoots_never_becomes_a_flight() -> None:
    # Test 7 (2026-08-17): every AAA piece and Avenger that fired at the package
    # landed in `flights`, because the shot handler took whatever DCS named as
    # the initiator. §91 is a record of FLIGHTS.
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(
        {
            "name": "0006 | GORILLA (AAA)",
            "side": 1,
            "category": 2,
            "units": [_unit("0046 | ZSU-57-2", type="ZSU_57_2")],
        }
    )

    harness.lua.eval("sortie_recorder_on_shot")(
        harness.lua.eval('Unit.getByName("0046 | ZSU-57-2")')
    )
    harness.assert_no_lua_errors()

    assert "0046 | ZSU-57-2" not in _records(harness)


def test_an_unnamed_initiator_never_becomes_a_flight() -> None:
    # A shell reaches the hit handler as the initiator and its getName is "",
    # so every cannon round in the mission collided into one "" record.
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(
        _flight("Shells", 1, [_unit("", type="weapons.shells.Rh202_20_HE")])
    )

    harness.lua.eval("sortie_recorder_on_hit")(harness.lua.eval('Unit.getByName("")'))
    harness.assert_no_lua_errors()

    assert "" not in _records(harness)


def test_a_submunition_impact_is_not_a_hit() -> None:
    # The test 8 defect: DCS raises one SHOT for the weapon released and one HIT per
    # IMPACTING object, and a cluster weapon's bomblets are different objects. Two
    # CBU-105 releases scored 68 "hits" and the SITREP read 106 shots for 381.
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_ai_pair("Enfield 1-1"))
    lead = harness.lua.eval('Unit.getByName("Enfield 1-1-1")')

    harness.lua.eval("sortie_recorder_on_shot")(lead, _weapon(harness, "CBU-105"))
    for i in range(10):
        harness.lua.eval("sortie_recorder_on_hit")(
            lead, _weapon(harness, f"BLU-108 #{i}")
        )
    harness.assert_no_lua_errors()

    record = _records(harness)["Enfield 1-1-1"]
    assert record["shots"] == 1
    assert record["hits"] == 0


def test_only_the_first_impact_of_a_weapon_counts() -> None:
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_ai_pair("Enfield 1-1"))
    lead = harness.lua.eval('Unit.getByName("Enfield 1-1-1")')
    bomb = _weapon(harness, "Mk-84")

    harness.lua.eval("sortie_recorder_on_shot")(lead, bomb)
    harness.lua.eval("sortie_recorder_on_hit")(lead, bomb)
    harness.lua.eval("sortie_recorder_on_hit")(lead, bomb)
    harness.assert_no_lua_errors()

    record = _records(harness)["Enfield 1-1-1"]
    assert record["shots"] == 1
    assert record["hits"] == 1


def test_hits_never_exceed_shots() -> None:
    # The invariant the SITREP line depends on -- it renders as "N shots for M hits",
    # which only reads as a hit rate if M cannot exceed N.
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_ai_pair("Enfield 1-1"))
    lead = harness.lua.eval('Unit.getByName("Enfield 1-1-1")')

    shot, hit = (
        harness.lua.eval("sortie_recorder_on_shot"),
        harness.lua.eval("sortie_recorder_on_hit"),
    )
    rocket = _weapon(harness, "S-8 pod")
    shot(lead, rocket)
    for _ in range(30):
        hit(lead, rocket)
    hit(lead, None)  # a gun round: no shot event exists for it
    hit(lead, _weapon(harness, "stray"))  # a weapon fired before the recorder started
    harness.assert_no_lua_errors()

    record = _records(harness)["Enfield 1-1-1"]
    assert record["hits"] <= record["shots"]
    assert (record["shots"], record["hits"]) == (1, 1)


def test_an_ejection_is_recorded_on_the_aircraft() -> None:
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_ai_pair("Enfield 1-1"))

    harness.lua.eval("sortie_recorder_on_ejection")(
        harness.lua.eval('Unit.getByName("Enfield 1-1-1")')
    )
    harness.assert_no_lua_errors()

    assert _records(harness)["Enfield 1-1-1"]["ejected"] is True


def test_the_track_covers_four_hours_then_drops_its_oldest() -> None:
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_flight("Enfield 1-1", 2, [_unit("Enfield 1-1-1")]))

    for step in range(500):
        harness.advance_to(step * 30.0)
        _sample(harness)
    harness.assert_no_lua_errors()

    record = _records(harness)["Enfield 1-1-1"]
    assert len(record["track"]) == 480  # 4 hours at 30 s
    assert record["last_seen"] == 499 * 30.0


def test_the_periodic_payload_carries_counters_but_no_track() -> None:
    """state.json is rewritten every 15 s; the track is far too costly to encode.

    A 60v60 track set is ~1 MB, and 480 writes over two hours would put half a
    gigabyte of json:encode on the sim thread.
    """
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_flight("Enfield 1-1", 2, [_unit("Enfield 1-1-1")]))
    for step in range(5):
        harness.advance_to(step * 30.0)
        _sample(harness)
    harness.lua.eval("sortie_recorder_on_shot")(
        harness.lua.eval('Unit.getByName("Enfield 1-1-1")')
    )

    light = harness.to_python(harness.lua.eval("sortie_recorder_payload")(False))
    record = light["flights"]["Enfield 1-1-1"]

    assert not record["track"]
    assert record["shots"] == 1
    assert record["first_seen"] == 0.0
    assert record["last_seen"] == 120.0
    assert record["group"] == "Enfield 1-1"


def test_the_final_payload_carries_the_track() -> None:
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_flight("Enfield 1-1", 2, [_unit("Enfield 1-1-1")]))
    for step in range(5):
        harness.advance_to(step * 30.0)
        _sample(harness)

    final = harness.to_python(harness.lua.eval("sortie_recorder_payload")(True))

    assert len(final["flights"]["Enfield 1-1-1"]["track"]) == 5


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

    _sample(harness)

    assert _records(harness) == {}


def test_sampling_marks_the_state_dirty_so_it_gets_written() -> None:
    harness = DcsPluginHarness()
    _load(harness)
    harness.add_group(_ai_pair("Enfield 1-1"))

    harness.lua.execute("dirty_state = false")
    _sample(harness)

    assert harness.to_python(harness.lua.eval("dirty_state")) is True
