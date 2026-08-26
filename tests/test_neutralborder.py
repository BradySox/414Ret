"""§96 border zones: yaml parsing, derived alignment, and per-side transit."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any

from game.theater.nationalpostures import RU_LED, US_LED
from game.theater.neutralborder import (
    BLUE_ALIGNED,
    DEFAULT_CONTESTED_FLOOR_FT,
    DEFAULT_SPAWN_ALT_FT,
    NEUTRAL,
    RED_ALIGNED,
    NeutralBorderZone,
)

ON = date(2006, 4, 24)


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


# -- parsing -------------------------------------------------------------------


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
    # No floor authored and none derived: a floor is not a universal rule.
    assert zone.floor_ft is None
    assert zone.sam is False
    assert zone.overflight_override is None
    assert zone.posture_override is None


def test_too_few_vertices_is_skipped() -> None:
    assert NeutralBorderZone.from_yaml(_entry(border=[[0, 0], [1, 1]])) is None


def test_missing_country_is_skipped() -> None:
    entry = _entry()
    del entry["country"]
    assert NeutralBorderZone.from_yaml(entry) is None


def test_garbage_border_is_skipped() -> None:
    assert NeutralBorderZone.from_yaml(_entry(border="nonsense")) is None


def test_bad_posture_value_is_skipped() -> None:
    assert NeutralBorderZone.from_yaml(_entry(posture="allied")) is None


def test_both_origins_is_skipped() -> None:
    """Naming an airfield AND a spawn point is ambiguous, so it is refused."""
    assert NeutralBorderZone.from_yaml(_entry(spawn=[1, 2])) is None


def test_a_country_and_a_border_is_enough_to_parse() -> None:
    """The automagic case: whether this zone ever needs an aircraft depends on
    its alignment and the posture table, neither of which exists at parse time,
    so parsing must not demand one."""
    zone = NeutralBorderZone.from_yaml(
        {"country": "Turkmenistan", "border": [[0, 0], [100, 0], [100, 100]]}
    )
    assert zone is not None
    assert zone.aircraft is None and zone.airfield is None and zone.spawn is None


# -- the point-spawn origin ----------------------------------------------------


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


def test_malformed_spawn_is_skipped() -> None:
    assert NeutralBorderZone.from_yaml(_spawn_entry(spawn=[1])) is None


# -- alignment is DERIVED from who holds the airfields inside the border --------
# The DM's rule (2026-08-24): a nation hosting a RED or BLUE airfield is aligned
# with that team; one hosting neither is the neutral. Derived rather than
# authored so it cannot drift from the campaign -- and so a country flips the
# turn its field changes hands.


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


def test_no_airfield_inside_is_neutral() -> None:
    zone = _box_zone()
    assert zone.posture_in(_theater(_cp(9999, 9999, blue=True))) == NEUTRAL


def test_a_blue_airfield_inside_makes_it_blue_aligned() -> None:
    zone = _box_zone()
    theater = _theater(_cp(50, 50, blue=True))
    assert zone.posture_in(theater) == BLUE_ALIGNED
    # Aligned countries are never enforced by §96 -- their own side's QRA does it.
    assert zone.enforces_against(theater, US_LED, ON) is False
    assert zone.enforces_against(theater, RU_LED, ON) is False


def test_a_red_airfield_inside_makes_it_red_aligned() -> None:
    """Hornet's Nest's Lebanon: red flies four squadrons out of Beirut."""
    zone = _box_zone()
    theater = _theater(_cp(50, 50, red=True))
    assert zone.posture_in(theater) == RED_ALIGNED
    assert zone.enforces_against(theater, US_LED, ON) is False


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


# -- transit consent is PER SIDE and comes from the dated table -----------------


def test_override_wins_over_the_table_for_both_sides() -> None:
    zone = _box_zone(overflight=True)
    assert zone.permits(US_LED, ON) is True
    assert zone.permits(RU_LED, ON) is True
    assert zone.enforces_against(_theater(), US_LED, ON) is False


def test_a_refusing_override_enforces_even_where_the_table_permits() -> None:
    """Enduring Resolve's Pakistan: the table reads permissive toward the US in
    2006 and is right, but that consent was for the corridor -- the lane this
    polygon leaves out. The override says what the geometry already means."""
    zone = _box_zone(country="Pakistan", overflight=False)
    assert zone.permits(US_LED, ON) is False
    assert zone.enforces_against(_theater(), US_LED, ON) is True


def test_the_table_decides_when_the_campaign_says_nothing() -> None:
    """Iran 2006: closed toward the US bloc, permissive toward the Russian one."""
    zone = _box_zone(country="Iran")
    assert zone.permits(US_LED, ON) is False
    assert zone.permits(RU_LED, ON) is True
    # It therefore intercepts blue and waves red through.
    assert zone.enforces_against(_theater(), US_LED, ON) is True
    assert zone.enforces_against(_theater(), RU_LED, ON) is False


def test_an_unknown_country_defaults_to_refusing() -> None:
    """The safe default for a border is that it defends."""
    zone = _box_zone(country="Freedonia")
    assert zone.permits(US_LED, ON) is False
    assert zone.permits(RU_LED, ON) is False


def test_permitting_neutral_labels_itself_as_open() -> None:
    zone = _box_zone(overflight=True)
    assert zone.origin_label(NEUTRAL, enforced=False) == (
        "neutral — overflight permitted"
    )


# -- a floor is not a universal rule -------------------------------------------
# "If they are hostile then they are hostile" (DM, 2026-08-25). A floor means
# high transit is tolerated, which only a `contested` country grants. A closed
# or hostile one offers no safe altitude, and inventing one invents a sanctuary.


def _unfloored(**overrides: object) -> NeutralBorderZone:
    """A zone with no authored floor, so the posture decides."""
    entry = _spawn_entry(border=[[0, 0], [100, 0], [100, 100], [0, 100]])
    del entry["floor_ft"]
    entry.update(overrides)
    zone = NeutralBorderZone.from_yaml(entry)
    assert zone is not None
    return zone


def test_a_closed_country_grants_no_safe_altitude() -> None:
    """Iran 2006 is closed toward the US bloc."""
    zone = _unfloored(country="Iran")
    assert zone.floor_for(US_LED, ON) is None


def test_a_contested_country_gets_the_default_floor() -> None:
    """Pakistan reads contested toward the US bloc after Abbottabad."""
    zone = _unfloored(country="Pakistan")
    assert zone.floor_for(US_LED, date(2015, 1, 1)) == DEFAULT_CONTESTED_FLOOR_FT


def test_an_authored_floor_always_wins() -> None:
    zone = _box_zone(country="Iran", floor_ft=8000)
    assert zone.floor_for(US_LED, ON) == 8000


def test_the_floor_is_per_side_like_consent() -> None:
    """A country may tolerate one bloc at height and refuse the other outright."""
    zone = _unfloored(country="Pakistan")
    when = date(2015, 1, 1)
    assert zone.floor_for(US_LED, when) == DEFAULT_CONTESTED_FLOOR_FT
    assert zone.floor_for(RU_LED, when) is None
