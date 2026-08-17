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
    (record,) = parse_sortie_records(_payload(**{"Enfield 1-1": _flight()}))

    assert record.group == "Enfield 1-1"
    assert record.unit_type == "FA-18C_hornet"
    assert record.coalition == 2
    assert record.shots == 2
    assert record.hits == 1
    assert record.ejected is False
    assert len(record.track) == 2


def test_lua_z_becomes_the_engines_y() -> None:
    """DCS's z is the engine's northing; getting this backwards mirrors tracks."""
    (record,) = parse_sortie_records(_payload(**{"Enfield 1-1": _flight()}))

    assert record.track[1].x == 3000.0
    assert record.track[1].y == 4000.0


def test_derived_figures() -> None:
    (record,) = parse_sortie_records(_payload(**{"Enfield 1-1": _flight()}))

    assert record.duration == 3600.0
    # 3-4-5 triangle between the two samples.
    assert record.distance_flown == 5000.0
    assert record.fuel_at_end == 0.5
    assert record.peak_altitude == 7000.0


def test_an_empty_track_has_no_derived_figures() -> None:
    (record,) = parse_sortie_records(_payload(**{"Enfield 1-1": _flight(track=[])}))

    assert record.distance_flown == 0.0
    assert record.fuel_at_end is None
    assert record.peak_altitude is None


def test_records_are_ordered_by_takeoff() -> None:
    payload = _payload(
        **{
            "Late 1-1": _flight(first_seen=900.0),
            "Early 1-1": _flight(first_seen=60.0),
        }
    )

    assert [r.group for r in parse_sortie_records(payload)] == [
        "Early 1-1",
        "Late 1-1",
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
    payload = _payload(**{"Enfield 1-1": _flight()})
    payload["version"] = SORTIE_RECORD_VERSION + 5
    payload["flights"]["Enfield 1-1"]["some_future_field"] = {"nested": True}

    (record,) = parse_sortie_records(payload)

    assert record.group == "Enfield 1-1"
    assert record.shots == 2


def test_a_malformed_flight_is_skipped_not_fatal() -> None:
    """One bad entry must never cost the mission its results."""
    payload = _payload(
        **{
            "Good 1-1": _flight(),
            "Bad 1-1": "not a table",
            "Worse 1-1": _flight(coalition="not a number"),
        }
    )

    records = parse_sortie_records(payload)

    assert [r.group for r in records] == ["Good 1-1"]


def test_a_malformed_track_sample_is_skipped_but_the_flight_survives() -> None:
    payload = _payload(
        **{
            "Enfield 1-1": _flight(
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
    (record,) = parse_sortie_records(_payload(**{"Enfield 1-1": {}}))

    assert record.unit_type == ""
    assert record.coalition == 0
    assert record.shots == 0
    assert record.track == ()
    assert record.ejected is False


def test_duration_is_never_negative() -> None:
    (record,) = parse_sortie_records(
        _payload(**{"Enfield 1-1": _flight(first_seen=500.0, last_seen=100.0)})
    )

    assert record.duration == 0.0


def test_the_record_is_hashable_and_frozen() -> None:
    (record,) = parse_sortie_records(_payload(**{"Enfield 1-1": _flight()}))

    assert isinstance(record, SortieRecord)
    assert {record}


def test_sortie_summary_reads_as_a_sentence() -> None:
    from game.sitrep import sortie_summary

    records = parse_sortie_records(
        _payload(
            **{
                "Enfield 1-1": _flight(first_seen=0.0, last_seen=3600.0, shots=2),
                "Chevy 1-1": _flight(first_seen=0.0, last_seen=1800.0, shots=0, hits=0),
            }
        )
    )

    assert sortie_summary(records) == "2 sorties, 1.5 hours airborne, 2 shots for 1 hit"


def test_sortie_summary_omits_weapons_when_nothing_was_fired() -> None:
    from game.sitrep import sortie_summary

    records = parse_sortie_records(
        _payload(
            **{
                "Enfield 1-1": _flight(
                    first_seen=0.0, last_seen=3600.0, shots=0, hits=0
                )
            }
        )
    )

    assert sortie_summary(records) == "1 sortie, 1.0 hours airborne"


def test_sortie_summary_is_silent_with_no_records() -> None:
    from game.sitrep import sortie_summary

    assert sortie_summary(()) is None
