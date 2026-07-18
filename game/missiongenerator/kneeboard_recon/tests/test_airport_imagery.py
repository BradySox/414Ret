"""Tests for the OSM-derived airport imagery loader."""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from game.missiongenerator.kneeboard_recon import airport_imagery
from game.missiongenerator.kneeboard_recon.airport_imagery import (
    AirportImagery,
    RunwayRecord,
    TerrainImagery,
    load,
)


@pytest.fixture(autouse=True)
def _clear_cache_around_each_test() -> Generator[None, None, None]:
    airport_imagery._clear_cache()
    yield
    airport_imagery._clear_cache()


def _write_json(dir_: Path, terrain: str, airports: dict[str, object]) -> Path:
    dir_.mkdir(parents=True, exist_ok=True)
    p = dir_ / f"{terrain.lower()}.json"
    p.write_text(
        json.dumps(
            {
                "terrain": terrain,
                "airports": airports,
            }
        )
    )
    return p


def test_load_returns_none_when_file_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(airport_imagery, "_IMAGERY_DIR", tmp_path)
    assert load("nonexistent") is None


def test_load_parses_caucasus_fixture(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(airport_imagery, "_IMAGERY_DIR", tmp_path)
    _write_json(
        tmp_path,
        "Caucasus",
        {
            "23": {
                "name": "Senaki-Kolkhi",
                "dcs_position": {"lat": 42.2408, "lng": 42.0480},
                "imagery_offset_deg": {"lat": -0.0007, "lng": 0.0026},
                "runways": [
                    {
                        "ref": "09/27",
                        "surface": "concrete",
                        "status": "active",
                        "osm_way_id": 102314714,
                        "length_m": 2348.8,
                        "heading_deg": 274.7,
                        "midpoint": {"lat": 42.24013, "lng": 42.05063},
                        "endpoint_a": {"lat": 42.23925, "lng": 42.06483},
                        "endpoint_b": {"lat": 42.24100, "lng": 42.03643},
                    },
                ],
            }
        },
    )
    record = load("Caucasus")
    assert record is not None
    assert record.terrain == "Caucasus"
    assert "23" in record.by_airport_id

    ap = record.by_airport_id["23"]
    assert ap.name == "Senaki-Kolkhi"
    assert ap.imagery_offset_lat == -0.0007
    assert ap.imagery_offset_lng == 0.0026
    assert len(ap.runways) == 1
    r = ap.runways[0]
    assert r.length_m == 2348.8
    assert r.half_length_m == pytest.approx(1174.4)
    assert r.heading_deg == 274.7
    assert r.status == "active"


def test_load_caches_subsequent_calls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(airport_imagery, "_IMAGERY_DIR", tmp_path)
    _write_json(tmp_path, "Caucasus", {})
    first = load("Caucasus")
    second = load("Caucasus")
    assert first is second  # same object, cached


def test_load_handles_terrain_name_with_spaces(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`The Channel` / `Persian Gulf` -> match `thechannel.json` / `persiangulf.json`."""
    monkeypatch.setattr(airport_imagery, "_IMAGERY_DIR", tmp_path)
    _write_json(tmp_path, "PersianGulf", {})
    record = load("Persian Gulf")
    assert record is not None


def test_for_airport_looks_up_by_id() -> None:
    record = TerrainImagery(
        terrain="Caucasus",
        by_airport_id={
            "23": AirportImagery(
                name="Senaki",
                imagery_offset_lat=0.0,
                imagery_offset_lng=0.0,
                runways=(),
            ),
        },
    )
    airport = MagicMock()
    airport.id = 23
    assert record.for_airport(airport) is not None
    airport.id = 999
    assert record.for_airport(airport) is None


def test_runway_matches_heading_both_ends() -> None:
    r = RunwayRecord(
        ref="09/27",
        surface="concrete",
        status="active",
        osm_way_id=1,
        length_m=2400.0,
        heading_deg=270.0,
        midpoint_lat=42.0,
        midpoint_lng=42.0,
        endpoint_a_lat=42.0,
        endpoint_a_lng=42.0144,
        endpoint_b_lat=42.0,
        endpoint_b_lng=41.9856,
    )
    assert r.matches_heading(270.0)
    assert r.matches_heading(90.0)  # opposite end
    assert r.matches_heading(265.0)  # within tolerance
    assert r.matches_heading(95.0)  # within tolerance, opposite end
    assert not r.matches_heading(180.0)


def test_threshold_for_approach_picks_correct_endpoint() -> None:
    """Endpoint A is east (positive lng), endpoint B is west; runway runs west.

    A landing approach at heading 90 (eastward landing) crosses the
    threshold at the WEST end (endpoint_b). A landing at heading 270
    (westward landing) crosses at the EAST end (endpoint_a).
    """
    r = RunwayRecord(
        ref="09/27",
        surface="concrete",
        status="active",
        osm_way_id=1,
        length_m=2400.0,
        heading_deg=270.0,
        midpoint_lat=42.0,
        midpoint_lng=42.0,
        endpoint_a_lat=42.0,
        endpoint_a_lng=42.0144,
        endpoint_b_lat=42.0,
        endpoint_b_lng=41.9856,
    )
    # heading_deg=270 means direction-from-A-to-B is west, so A is east, B is west.
    # Aircraft landing heading 90 (flying east) -> threshold = WEST end = endpoint_b.
    t_lat, t_lng = r.threshold_for_approach(90.0)
    assert t_lat == 42.0 and t_lng == 41.9856

    # Aircraft landing heading 270 (flying west) -> threshold = EAST end = endpoint_a.
    t_lat, t_lng = r.threshold_for_approach(270.0)
    assert t_lat == 42.0 and t_lng == 42.0144


def test_runway_for_heading_returns_longest_match() -> None:
    paved = RunwayRecord(
        ref="09/27",
        surface="concrete",
        status="active",
        osm_way_id=1,
        length_m=2400.0,
        heading_deg=270.0,
        midpoint_lat=42.0,
        midpoint_lng=42.0,
        endpoint_a_lat=42.0,
        endpoint_a_lng=42.0144,
        endpoint_b_lat=42.0,
        endpoint_b_lng=41.9856,
    )
    short_unpaved = RunwayRecord(
        ref="08/26",
        surface="grass",
        status="abandoned",
        osm_way_id=2,
        length_m=900.0,
        heading_deg=265.0,
        midpoint_lat=42.0,
        midpoint_lng=42.0,
        endpoint_a_lat=42.0,
        endpoint_a_lng=42.0054,
        endpoint_b_lat=42.0,
        endpoint_b_lng=41.9946,
    )
    crossing = RunwayRecord(
        ref="18/36",
        surface="concrete",
        status="active",
        osm_way_id=3,
        length_m=1500.0,
        heading_deg=180.0,
        midpoint_lat=42.0,
        midpoint_lng=42.0,
        endpoint_a_lat=42.00675,
        endpoint_a_lng=42.0,
        endpoint_b_lat=41.99325,
        endpoint_b_lng=42.0,
    )
    ap = AirportImagery(
        name="X",
        imagery_offset_lat=0.0,
        imagery_offset_lng=0.0,
        runways=(paved, short_unpaved, crossing),
    )
    # Heading 270 matches paved and short_unpaved within tolerance; longest wins.
    assert ap.runway_for_heading(270.0) is paved
    # Heading 180 matches only the crossing.
    assert ap.runway_for_heading(180.0) is crossing
    # No runway at this heading.
    assert ap.runway_for_heading(135.0) is None


def test_field_elevation_for_airport_returns_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Helper returns the elevation when the record carries one."""
    record = TerrainImagery(
        terrain="Caucasus",
        by_airport_id={
            "12": AirportImagery(
                name="Anapa",
                imagery_offset_lat=0.0,
                imagery_offset_lng=0.0,
                runways=(),
                elevation_m=42.0,
            ),
        },
    )
    # Patch ``load`` directly: the sibling conftest patches it to always
    # return None for page-render tests, so the helper would otherwise see
    # no record. Re-stub to return our controlled record.
    monkeypatch.setattr(airport_imagery, "load", lambda name: record)
    terrain = MagicMock()
    terrain.name = "Caucasus"
    airport = MagicMock()
    airport.id = 12
    assert airport_imagery.field_elevation_for_airport(terrain, airport) == 42.0


def test_field_elevation_for_airport_returns_none_for_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No record, no entry for this airport, or null elevation → None."""
    terrain = MagicMock()
    terrain.name = "Caucasus"
    airport = MagicMock()
    airport.id = 12

    # No record at all (terrain not shipped).
    monkeypatch.setattr(airport_imagery, "load", lambda name: None)
    assert airport_imagery.field_elevation_for_airport(terrain, airport) is None

    # Record present but no entry for this airport id.
    rec_other = TerrainImagery(
        terrain="Caucasus",
        by_airport_id={
            "99": AirportImagery(
                name="Other",
                imagery_offset_lat=0.0,
                imagery_offset_lng=0.0,
                runways=(),
                elevation_m=10.0,
            ),
        },
    )
    monkeypatch.setattr(airport_imagery, "load", lambda name: rec_other)
    assert airport_imagery.field_elevation_for_airport(terrain, airport) is None

    # Entry present but elevation explicitly null.
    rec_null_elev = TerrainImagery(
        terrain="Caucasus",
        by_airport_id={
            "12": AirportImagery(
                name="Anapa",
                imagery_offset_lat=0.0,
                imagery_offset_lng=0.0,
                runways=(),
                elevation_m=None,
            ),
        },
    )
    monkeypatch.setattr(airport_imagery, "load", lambda name: rec_null_elev)
    assert airport_imagery.field_elevation_for_airport(terrain, airport) is None


def test_field_elevation_for_airport_returns_none_for_none_inputs() -> None:
    """Defensive: helper never raises on None inputs."""
    assert airport_imagery.field_elevation_for_airport(None, MagicMock()) is None
    terrain = MagicMock()
    terrain.name = "Caucasus"
    assert airport_imagery.field_elevation_for_airport(terrain, None) is None


# --- offset_near: the regional offset estimate for un-anchored extents ---


def _measured(
    name: str, lat: float, lng: float, dlat: float, dlng: float
) -> AirportImagery:
    return AirportImagery(
        name=name,
        imagery_offset_lat=dlat,
        imagery_offset_lng=dlng,
        runways=(),
        dcs_lat=lat,
        dcs_lng=lng,
        has_offset=True,
    )


def _record_of(entries: dict[str, AirportImagery]) -> TerrainImagery:
    return TerrainImagery(terrain="X", by_airport_id=entries)


def test_offset_near_medians_the_nearest_measured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _record_of(
        {
            "1": _measured("A", 42.00, 41.00, 0.0010, -0.0002),
            "2": _measured("B", 42.05, 41.00, 0.0012, -0.0001),
            "3": _measured("C", 42.10, 41.00, 0.0009, -0.0003),
            # Farther than the three above — must not join the vote.
            "4": _measured("D", 43.90, 41.00, 0.0300, 0.0100),
        }
    )
    monkeypatch.setattr(airport_imagery, "load", lambda name: record)
    assert airport_imagery.offset_near("X", 42.0, 41.0) == (0.0010, -0.0002)


def test_offset_near_skips_outlier_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    """An offset several km on the ground is a mis-matched OSM airfield, not
    a georeference error — it must not poison the estimate."""
    record = _record_of(
        {
            "1": _measured("A", 42.00, 41.00, 0.0500, 0.0),  # ~5.6 km: junk
            "2": _measured("B", 42.02, 41.00, 0.0010, 0.0),
            "3": _measured("C", 42.04, 41.00, 0.0010, 0.0),
        }
    )
    monkeypatch.setattr(airport_imagery, "load", lambda name: record)
    assert airport_imagery.offset_near("X", 42.0, 41.0) == (0.0010, 0.0)


def test_offset_near_ignores_unmeasured_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Entries without a measured offset block or a known DCS position never
    vote; with only those, there is no estimate."""
    record = _record_of(
        {
            "1": AirportImagery(
                name="NoOffset",
                imagery_offset_lat=0.0,
                imagery_offset_lng=0.0,
                runways=(),
                dcs_lat=42.0,
                dcs_lng=41.0,
                has_offset=False,
            ),
            "2": AirportImagery(
                name="NoPosition",
                imagery_offset_lat=0.001,
                imagery_offset_lng=0.0,
                runways=(),
                has_offset=True,
            ),
        }
    )
    monkeypatch.setattr(airport_imagery, "load", lambda name: record)
    assert airport_imagery.offset_near("X", 42.0, 41.0) is None


def test_offset_near_none_when_nearest_is_too_far(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ~334 km away — beyond the 250 km relevance limit.
    record = _record_of({"1": _measured("A", 45.0, 41.0, 0.001, 0.0)})
    monkeypatch.setattr(airport_imagery, "load", lambda name: record)
    assert airport_imagery.offset_near("X", 42.0, 41.0) is None


def test_offset_near_none_without_dataset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(airport_imagery, "load", lambda name: None)
    assert airport_imagery.offset_near("X", 42.0, 41.0) is None


def test_load_parses_dcs_position_and_measured_flag(tmp_path: Path) -> None:
    """The loader carries dcs_position + the has_offset distinction through,
    so offset_near can tell 'measured as aligned' from 'never measured'."""
    import game.missiongenerator.kneeboard_recon.airport_imagery as ai

    _write_json(
        tmp_path,
        "Caucasus",
        {
            "12": {
                "name": "Anapa",
                "dcs_position": {"lat": 45.0, "lng": 37.3},
                "imagery_offset_deg": {"lat": -0.0028, "lng": -0.0005},
                "runways": [],
            },
            "13": {
                "name": "NoOffsetField",
                "dcs_position": {"lat": 45.1, "lng": 37.4},
                "runways": [],
            },
        },
    )
    original = ai._IMAGERY_DIR
    ai._IMAGERY_DIR = tmp_path
    try:
        record = load("Caucasus")
    finally:
        ai._IMAGERY_DIR = original
    assert record is not None
    anapa = record.by_airport_id["12"]
    assert anapa.has_offset and anapa.dcs_lat == 45.0 and anapa.dcs_lng == 37.3
    assert anapa.imagery_offset_lat == -0.0028
    bare = record.by_airport_id["13"]
    assert not bare.has_offset
    assert bare.dcs_lat == 45.1
