from typing import Any

from game.sortierecord import (
    SORTIE_RECORD_VERSION,
    SortieRecord,
    parse_sortie_records,
)


def _payload(**flights: Any) -> dict[str, Any]:
    return {"version": SORTIE_RECORD_VERSION, "flights": dict(flights)}


def _flight(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "type": "FA-18C_hornet",
        "coalition": 2,
        "first_seen": 60.0,
        "last_seen": 3660.0,
        "track": [
            {"t": 60.0, "x": 0.0, "z": 0.0, "alt": 3000.0, "fuel": 1.0},
            {"t": 1800.0, "x": 3000.0, "z": 4000.0, "alt": 7000.0, "fuel": 0.5},
        ],
        "shots": 2,
        "hits": 1,
        "ejected": False,
    }
    base.update(overrides)
    return base


def test_a_record_round_trips_from_the_lua_shape() -> None:
    (record,) = parse_sortie_records(_payload(**{"Enfield 1-1-1": _flight()}))

    assert record.unit == "Enfield 1-1-1"
    assert record.unit_type == "FA-18C_hornet"
    assert record.coalition == 2
    assert record.shots == 2
    assert record.hits == 1
    assert record.ejected is False
    assert len(record.track) == 2


def test_lua_z_becomes_the_engines_y() -> None:
    """DCS's z is the engine's northing; getting this backwards mirrors tracks."""
    (record,) = parse_sortie_records(_payload(**{"Enfield 1-1-1": _flight()}))

    assert record.track[1].x == 3000.0
    assert record.track[1].y == 4000.0


def test_derived_figures() -> None:
    (record,) = parse_sortie_records(_payload(**{"Enfield 1-1-1": _flight()}))

    assert record.duration == 3600.0
    # 3-4-5 triangle between the two samples.
    assert record.distance_flown == 5000.0
    assert record.fuel_at_end == 0.5
    assert record.peak_altitude == 7000.0


def test_an_empty_track_has_no_derived_figures() -> None:
    (record,) = parse_sortie_records(_payload(**{"Enfield 1-1-1": _flight(track=[])}))

    assert record.distance_flown == 0.0
    assert record.fuel_at_end is None
    assert record.peak_altitude is None


def test_records_are_ordered_by_takeoff() -> None:
    payload = _payload(
        **{
            "Late 1-1-1": _flight(first_seen=900.0),
            "Early 1-1-1": _flight(first_seen=60.0),
        }
    )

    assert [r.unit for r in parse_sortie_records(payload)] == [
        "Early 1-1-1",
        "Late 1-1-1",
    ]


def test_a_missing_channel_is_no_data_not_a_crash() -> None:
    """Pre-feature saves and a disabled recorder both land here."""
    assert parse_sortie_records(None) == ()
    assert parse_sortie_records({}) == ()
    assert parse_sortie_records({"version": 1}) == ()


def test_an_empty_lua_table_serialises_as_a_list() -> None:
    """Lua encodes an empty table as [], which is not a dict."""
    assert parse_sortie_records([]) == ()


def test_a_newer_version_still_reads_the_fields_we_know() -> None:
    payload = _payload(**{"Enfield 1-1-1": _flight()})
    payload["version"] = SORTIE_RECORD_VERSION + 5
    payload["flights"]["Enfield 1-1-1"]["some_future_field"] = {"nested": True}

    (record,) = parse_sortie_records(payload)

    assert record.unit == "Enfield 1-1-1"
    assert record.shots == 2


def test_a_malformed_flight_is_skipped_not_fatal() -> None:
    """One bad entry must never cost the mission its results."""
    payload = _payload(
        **{
            "Good 1-1-1": _flight(),
            "Bad 1-1-1": "not a table",
            "Worse 1-1-1": _flight(coalition="not a number"),
        }
    )

    records = parse_sortie_records(payload)

    assert [r.unit for r in records] == ["Good 1-1-1"]


def test_a_malformed_track_sample_is_skipped_but_the_flight_survives() -> None:
    payload = _payload(
        **{
            "Enfield 1-1-1": _flight(
                track=[
                    {"t": 1.0, "x": 0.0, "z": 0.0, "alt": 0.0, "fuel": 1.0},
                    "junk",
                    {"t": 2.0, "x": "sideways", "z": 0.0},
                ]
            )
        }
    )

    (record,) = parse_sortie_records(payload)

    assert len(record.track) == 1


def test_missing_optional_fields_default_rather_than_raise() -> None:
    (record,) = parse_sortie_records(_payload(**{"Enfield 1-1-1": {}}))

    assert record.unit_type == ""
    assert record.coalition == 0
    assert record.shots == 0
    assert record.track == ()
    assert record.ejected is False


def test_duration_is_never_negative() -> None:
    (record,) = parse_sortie_records(
        _payload(**{"Enfield 1-1-1": _flight(first_seen=500.0, last_seen=100.0)})
    )

    assert record.duration == 0.0


def test_the_record_is_hashable_and_frozen() -> None:
    (record,) = parse_sortie_records(_payload(**{"Enfield 1-1-1": _flight()}))

    assert isinstance(record, SortieRecord)
    assert {record}


def test_sortie_summary_reads_as_a_sentence() -> None:
    from game.sitrep import sortie_summary

    records = parse_sortie_records(
        _payload(
            **{
                "Enfield 1-1-1": _flight(first_seen=0.0, last_seen=3600.0, shots=2),
                "Chevy 1-1-1": _flight(
                    first_seen=0.0, last_seen=1800.0, shots=0, hits=0
                ),
            }
        )
    )

    assert sortie_summary(records) == "2 sorties, 1.5 hours airborne, 2 shots for 1 hit"


def test_sortie_summary_omits_weapons_when_nothing_was_fired() -> None:
    from game.sitrep import sortie_summary

    records = parse_sortie_records(
        _payload(
            **{
                "Enfield 1-1-1": _flight(
                    first_seen=0.0, last_seen=3600.0, shots=0, hits=0
                )
            }
        )
    )

    assert sortie_summary(records) == "1 sortie, 1.0 hours airborne"


def test_sortie_summary_is_silent_with_no_records() -> None:
    from game.sitrep import sortie_summary

    assert sortie_summary(()) is None


def test_the_group_is_carried_and_several_records_can_share_it() -> None:
    """Four humans in one flight are four records with one group name."""
    payload = _payload(
        **{
            f"Enfield 1-1-{n}": _flight(group="Enfield 1-1", player=True)
            for n in range(1, 5)
        }
    )

    records = parse_sortie_records(payload)

    assert len(records) == 4
    assert {r.group for r in records} == {"Enfield 1-1"}
    assert {r.unit for r in records} == {f"Enfield 1-1-{n}" for n in range(1, 5)}
    assert all(r.player for r in records)


def test_the_group_defaults_to_the_unit_when_absent() -> None:
    (record,) = parse_sortie_records(_payload(**{"Lone 1-1": _flight()}))

    assert record.group == "Lone 1-1"


def test_counters_only_records_are_not_counted_as_sorties() -> None:
    """An AI wingman that fired but was never position-sampled is not a sortie.

    Only the group's anchor jet carries a track; counting the rest would inflate
    the figure by the group size.
    """
    from game.sitrep import sortie_summary
    from game.sortierecord import sorties_flown

    # A counters-only record is created by the shot handler, which never sets
    # first_seen/last_seen -- they stay at the recorder's -1 sentinel.
    counters_only = {"first_seen": -1.0, "last_seen": -1.0, "track": []}
    payload = _payload(
        **{
            "Enfield 1-1-1": _flight(first_seen=0.0, last_seen=3600.0, shots=1, hits=1),
            "Enfield 1-1-2": _flight(shots=3, hits=2, **counters_only),
            "Enfield 1-1-3": _flight(shots=0, hits=0, **counters_only),
        }
    )
    records = parse_sortie_records(payload)

    assert all(r.duration == 0.0 for r in records if not r.track)

    assert len(records) == 3
    assert sorties_flown(records) == 1
    # ...but their weapons still count.
    assert sortie_summary(records) == "1 sortie, 1.0 hours airborne, 4 shots for 3 hits"


def test_a_parked_airframe_is_not_a_sortie() -> None:
    """The idle ramp is sampled like a flight; it must not be counted as one.

    `_spawn_unused_for` parks a squadron's untasked airframes as 1-ship
    Completed BARCAP groups. Test 12 (2026-08-20) had 82 of 158 records sitting
    on ramps and the SITREP would have read "145 sorties, 96.7 hours airborne"
    for a mission 46 aircraft flew.
    """
    from game.sitrep import sortie_summary
    from game.sortierecord import sorties_flown

    parked = {
        "first_seen": 30.0,
        "last_seen": 3630.0,
        "shots": 0,
        "hits": 0,
        "track": [
            {"t": 30.0, "x": 4000.0, "z": 9000.0, "alt": 12.0, "fuel": 1.0},
            {"t": 3630.0, "x": 4001.0, "z": 9002.0, "alt": 12.0, "fuel": 1.0},
        ],
    }
    payload = _payload(
        **{
            "Enfield 1-1-1": _flight(),
            "Ramp 1": _flight(**parked),
            "Ramp 2": _flight(**parked),
        }
    )
    records = parse_sortie_records(payload)

    assert len(records) == 3
    assert sorties_flown(records) == 1
    # Its hour on the ramp is not an hour airborne either.
    assert sortie_summary(records) == "1 sortie, 1.0 hours airborne, 2 shots for 1 hit"


def test_a_take_with_no_tracks_at_all_says_nothing() -> None:
    """A periodic (non-final) write carries counters but no tracks."""
    from game.sitrep import sortie_summary

    records = parse_sortie_records(
        _payload(**{"Enfield 1-1-1": _flight(track=[], shots=2)})
    )

    assert sortie_summary(records) is None
