"""NeutralBorderZone yaml parsing (§96): malformed campaign data never raises."""

from __future__ import annotations

from game.theater.neutralborder import (
    BLUE_ALIGNED,
    DEFAULT_SPAWN_ALT_FT,
    NEUTRAL,
    RED_ALIGNED,
    NeutralBorderZone,
)


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
    assert zone.origin_label(NEUTRAL) == "Pakistan border CAP"


def test_spawn_altitude_defaults() -> None:
    zone = NeutralBorderZone.from_yaml(_spawn_entry())
    assert zone is not None
    assert zone.spawn_alt_ft == DEFAULT_SPAWN_ALT_FT


def test_airfield_zone_labels_by_its_field() -> None:
    zone = NeutralBorderZone.from_yaml(_entry())
    assert zone is not None
    assert zone.origin_label(NEUTRAL) == "Rayak"


def test_both_airfield_and_spawn_is_skipped() -> None:
    """Ambiguous origin: refuse rather than silently picking one."""
    assert NeutralBorderZone.from_yaml(_spawn_entry(airfield="Rayak")) is None


def test_neither_airfield_nor_spawn_is_skipped() -> None:
    entry = _entry()
    del entry["airfield"]
    assert NeutralBorderZone.from_yaml(entry) is None


def test_malformed_spawn_is_skipped() -> None:
    assert NeutralBorderZone.from_yaml(_spawn_entry(spawn=[1])) is None


# -- alignment is DERIVED from who holds the airfields inside the border -------
# The DM's rule (2026-08-24): a nation hosting a RED or BLUE airfield is aligned
# with that team; one hosting neither is the neutral. Derived rather than
# authored so it cannot drift from the campaign -- and so a country flips the
# turn its field changes hands.

from types import SimpleNamespace
from typing import Any


def _cp(x: float, y: float, blue: bool = False, red: bool = False) -> Any:
    return SimpleNamespace(
        position=SimpleNamespace(x=x, y=y),
        captured=SimpleNamespace(is_blue=blue, is_red=red),
    )


def _theater(*cps: Any) -> Any:
    return SimpleNamespace(controlpoints=list(cps))


def _box_zone(**overrides: object) -> NeutralBorderZone:
    """A 100x100 box at the origin."""
    entry = _spawn_entry(border=[[0, 0], [100, 0], [100, 100], [0, 100]])
    entry.update(overrides)
    zone = NeutralBorderZone.from_yaml(entry)
    assert zone is not None
    return zone


def test_no_airfield_inside_is_neutral_and_enforces() -> None:
    zone = _box_zone()
    theater = _theater(_cp(9999, 9999, blue=True))
    assert zone.posture_in(theater) == NEUTRAL
    assert zone.enforces_in(theater) is True


def test_a_blue_airfield_inside_makes_it_blue_aligned() -> None:
    zone = _box_zone()
    theater = _theater(_cp(50, 50, blue=True))
    assert zone.posture_in(theater) == BLUE_ALIGNED
    # Aligned countries are never enforced by §96 -- their own side's QRA does it.
    assert zone.enforces_in(theater) is False


def test_a_red_airfield_inside_makes_it_red_aligned() -> None:
    """Hornet's Nest's Lebanon: red flies four squadrons out of Beirut."""
    zone = _box_zone()
    theater = _theater(_cp(50, 50, red=True))
    assert zone.posture_in(theater) == RED_ALIGNED
    assert zone.enforces_in(theater) is False


def test_contested_resolves_to_the_larger_holder_not_neutral() -> None:
    zone = _box_zone()
    theater = _theater(
        _cp(20, 20, red=True), _cp(60, 60, red=True), _cp(80, 80, blue=True)
    )
    assert zone.posture_in(theater) == RED_ALIGNED


def test_off_map_spawns_never_align_a_country() -> None:
    """An off-map spawn sits at a map edge and is not territory."""

    class OffMapSpawn(SimpleNamespace):
        pass

    off_map = OffMapSpawn(
        position=SimpleNamespace(x=50, y=50),
        captured=SimpleNamespace(is_blue=True, is_red=False),
    )
    zone = _box_zone()
    assert zone.posture_in(_theater(off_map)) == NEUTRAL


def test_posture_override_wins_over_the_derivation() -> None:
    zone = _box_zone(posture="red")
    assert zone.posture_in(_theater(_cp(50, 50, blue=True))) == RED_ALIGNED


# -- overflight is a SEPARATE fact from alignment ------------------------------
# In 2006 Turkmenistan permitted coalition transit and Iran did not. Both were
# neutral, so alignment cannot be what decides it.


def test_a_permitting_neutral_is_neutral_but_never_enforces() -> None:
    zone = _box_zone(overflight=True)
    theater = _theater()
    assert zone.posture_in(theater) == NEUTRAL
    assert zone.enforces_in(theater) is False
    assert zone.origin_label(NEUTRAL) == "neutral — overflight permitted"


def test_a_permitting_neutral_needs_no_aircraft_or_origin() -> None:
    """This is what lets a country DCS does not model be drawn at all."""
    zone = NeutralBorderZone.from_yaml(
        {
            "country": "Turkmenistan",
            "overflight": True,
            "border": [[0, 0], [100, 0], [100, 100]],
        }
    )
    assert zone is not None
    assert zone.aircraft is None and zone.spawn is None and zone.airfield is None
    assert zone.enforces_in(_theater()) is False


def test_a_refusing_neutral_still_needs_the_means_to_intercept() -> None:
    assert (
        NeutralBorderZone.from_yaml(
            {"country": "Iran", "border": [[0, 0], [100, 0], [100, 100]]}
        )
        is None
    )
