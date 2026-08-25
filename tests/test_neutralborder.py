"""NeutralBorderZone yaml parsing (§96): malformed campaign data never raises."""

from __future__ import annotations

from game.theater.neutralborder import NeutralBorderZone


def _entry(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "country": "Lebanon",
        "airfield": "Rayak",
        "aircraft": "MiG-29A",
        "floor_ft": 12000,
        "sam": True,
        "border": [[0, 0], [20000, 0], [20000, 20000]],
    }
    entry.update(overrides)
    return entry


def test_happy_path() -> None:
    zone = NeutralBorderZone.from_yaml(_entry())
    assert zone is not None
    assert zone.country == "Lebanon"
    assert zone.airfield == "Rayak"
    assert zone.aircraft == "MiG-29A"
    assert zone.floor_ft == 12000
    assert zone.sam is True
    assert zone.border == [(0.0, 0.0), (20000.0, 0.0), (20000.0, 20000.0)]


def test_defaults() -> None:
    entry = _entry()
    del entry["floor_ft"]
    del entry["sam"]
    zone = NeutralBorderZone.from_yaml(entry)
    assert zone is not None
    assert zone.floor_ft == 10000
    assert zone.sam is False


def test_too_few_vertices_is_skipped() -> None:
    assert NeutralBorderZone.from_yaml(_entry(border=[[0, 0], [1, 1]])) is None


def test_missing_required_key_is_skipped() -> None:
    entry = _entry()
    del entry["airfield"]
    assert NeutralBorderZone.from_yaml(entry) is None


def test_garbage_border_is_skipped() -> None:
    assert NeutralBorderZone.from_yaml(_entry(border="nonsense")) is None
