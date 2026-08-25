"""NeutralBorderZone yaml parsing (§96): malformed campaign data never raises."""

from __future__ import annotations

from game.theater.neutralborder import DEFAULT_SPAWN_ALT_FT, NeutralBorderZone


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


# -- the point-spawn path: a neutral with no airfield anywhere on the map ------
# Every one of the DCS Afghanistan map's 26 airfields is inside Afghanistan, so
# Pakistan, Iran, Turkmenistan, Uzbekistan and Tajikistan have nothing to
# scramble from and fly a standing CAP from a spawn point instead.


def _spawn_entry(**overrides: object) -> dict[str, object]:
    entry = _entry(country="Pakistan", aircraft="MiG-21Bis")
    del entry["airfield"]
    entry["spawn"] = [-375979, 341652]
    entry.update(overrides)
    return entry


def test_spawn_point_zone() -> None:
    zone = NeutralBorderZone.from_yaml(_spawn_entry(spawn_alt_ft=22000))
    assert zone is not None
    assert zone.airfield is None
    assert zone.spawn == (-375979.0, 341652.0)
    assert zone.spawn_alt_ft == 22000
    assert zone.origin_label == "Pakistan border CAP"


def test_spawn_altitude_defaults() -> None:
    zone = NeutralBorderZone.from_yaml(_spawn_entry())
    assert zone is not None
    assert zone.spawn_alt_ft == DEFAULT_SPAWN_ALT_FT


def test_airfield_zone_labels_by_its_field() -> None:
    zone = NeutralBorderZone.from_yaml(_entry())
    assert zone is not None
    assert zone.origin_label == "Rayak"


def test_both_airfield_and_spawn_is_skipped() -> None:
    """Ambiguous origin: refuse rather than silently picking one."""
    assert NeutralBorderZone.from_yaml(_spawn_entry(airfield="Rayak")) is None


def test_neither_airfield_nor_spawn_is_skipped() -> None:
    entry = _entry()
    del entry["airfield"]
    assert NeutralBorderZone.from_yaml(entry) is None


def test_malformed_spawn_is_skipped() -> None:
    assert NeutralBorderZone.from_yaml(_spawn_entry(spawn=[1])) is None
