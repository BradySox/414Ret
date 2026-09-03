"""§96 border zones: yaml parsing, derived alignment, and per-side transit."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any

from game.theater.neutralborder import (
    BLUE_ALIGNED,
    CONTESTED_ALIGNED,
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
    # The SAM defaults ON. It was authored-only until 2026-08-28, and the
    # terrain files that are now the only source of borders never set it, so no
    # shipped campaign could produce a battery at all -- flown that day, the
    # escalation fired and nothing woke. A campaign may still switch it off.
    assert zone.sam is True
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
    assert zone.enforces_against(theater, True) is False
    assert zone.enforces_against(theater, False) is False


def test_a_red_airfield_inside_makes_it_red_aligned() -> None:
    """Hornet's Nest's Lebanon: red flies four squadrons out of Beirut."""
    zone = _box_zone()
    theater = _theater(_cp(50, 50, red=True))
    assert zone.posture_in(theater) == RED_ALIGNED
    assert zone.enforces_against(theater, True) is False


def test_both_sides_holding_ground_is_contested_not_the_larger_holder() -> None:
    """Able Archer 83: Norway holds Bodo (blue) plus Banak and Kirkenes (red),
    so majority-wins drew the NATO host in enemy red. Both sides being present
    is the front line, not allegiance -- neither hue is true, so neither is
    used."""
    zone = _box_zone()
    theater = _theater(
        _cp(20, 20, red=True), _cp(60, 60, red=True), _cp(80, 80, blue=True)
    )
    assert zone.posture_in(theater) == CONTESTED_ALIGNED
    # And it is nobody's to defend: not §96's, not either QRA's.
    assert zone.enforces_against(theater, True) is False
    assert zone.enforces_against(theater, False) is False


def test_alignment_counts_every_piece_of_the_same_country() -> None:
    """Russia is two zones on the Kola map. Counting per polygon drew Karelia --
    116,420 km2, the largest zone on the map -- as an uninvolved neutral that
    intercepts you, in a campaign where Russia is the enemy."""
    empty = _box_zone(country="Russia")
    held = _box_zone(country="Russia", border=[[200, 200], [300, 200], [300, 300]])
    theater = _theater(_cp(280, 220, red=True))
    theater.neutral_border_zones = [empty, held]
    assert empty.posture_in(theater) == RED_ALIGNED
    assert held.posture_in(theater) == RED_ALIGNED
    assert empty.enforces_against(theater, True) is False


def test_a_lone_zone_needs_no_sibling_list() -> None:
    """posture_in is called on theaters that carry no zone list at all (every
    unit test built before the merge, and any caller holding one zone)."""
    zone = _box_zone()
    assert zone.posture_in(_theater(_cp(50, 50, red=True))) == RED_ALIGNED


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


def _unfloored(**overrides: object) -> NeutralBorderZone:
    """A zone with no authored floor."""
    entry = _spawn_entry(border=[[0, 0], [100, 0], [100, 100], [0, 100]])
    del entry["floor_ft"]
    entry.update(overrides)
    zone = NeutralBorderZone.from_yaml(entry)
    assert zone is not None
    return zone


# -- transit consent is DERIVED FROM THE AIRBASES, like alignment --------------
# DM call, 2026-08-26: "overflight should be derived by airbases in the borders".
# A country you fly from has let you in; one you have no presence in has not.
# The dated posture table used to answer this and no longer does -- it made
# consent a fact about the calendar rather than about the campaign in front of
# you. The research is kept, and still supplies each country's era airframe.


def test_a_country_you_fly_from_lets_you_through() -> None:
    zone = _box_zone()
    theater = _theater(_cp(50, 50, blue=True))
    assert zone.permits(theater, True) is True
    assert zone.permits(theater, False) is False


def test_a_country_the_enemy_flies_from_does_not_let_you_through() -> None:
    zone = _box_zone()
    theater = _theater(_cp(50, 50, red=True))
    assert zone.permits(theater, True) is False
    assert zone.permits(theater, False) is True


def test_a_country_both_sides_use_has_already_let_both_in() -> None:
    zone = _box_zone()
    theater = _theater(_cp(20, 20, blue=True), _cp(60, 60, red=True))
    assert zone.permits(theater, True) is True
    assert zone.permits(theater, False) is True


def test_a_country_neither_side_is_in_refuses_both() -> None:
    """The §96 case: nobody is based there, so nobody has been invited."""
    zone = _box_zone()
    theater = _theater()
    assert zone.permits(theater, True) is False
    assert zone.permits(theater, False) is False
    assert zone.enforces_against(theater, True) is True
    assert zone.enforces_against(theater, False) is True


def test_the_campaigns_override_still_wins_for_both_sides() -> None:
    zone = _box_zone(overflight=True)
    theater = _theater()
    assert zone.permits(theater, True) is True
    assert zone.permits(theater, False) is True
    assert zone.enforces_against(theater, True) is False


def test_a_refusing_override_beats_the_derivation() -> None:
    """Enduring Resolve's Pakistan: the corridor IS the consent, and this
    polygon is the ground either side of it."""
    zone = _box_zone(country="Pakistan", overflight=False)
    theater = _theater(_cp(50, 50, blue=True))
    assert zone.permits(theater, True) is False


def test_the_date_no_longer_changes_anything() -> None:
    """The same map on the same turn reads the same in 1975 and 2025. Sweden and
    Finland were the case that killed the table: it read them `closed` in 1983
    while both sides flew combat sorties off their runways."""
    zone = _box_zone(country="Sweden")
    theater = _theater(_cp(50, 50, blue=True))
    assert zone.permits(theater, True) is True


def test_permitting_neutral_labels_itself_as_open() -> None:
    zone = _box_zone(overflight=True)
    assert zone.origin_label(NEUTRAL, enforced=False) == (
        "neutral — overflight permitted"
    )


# -- a floor is authored only --------------------------------------------------
# "If they are hostile then they are hostile" (DM, 2026-08-25). A floor means
# high transit is tolerated, which is a judgement no fact on the map supports;
# it came from the posture table's `contested` bucket and went with it.


def test_no_floor_unless_the_campaign_states_one() -> None:
    zone = _unfloored(country="Iran")
    assert zone.floor_for(_theater(), True) is None


def test_an_authored_floor_is_honoured() -> None:
    zone = _box_zone(country="Iran", floor_ft=8000)
    assert zone.floor_for(_theater(), True) == 8000


# -- handing permits() a posture is a shortcut, never a second opinion ----------


def test_a_passed_posture_gives_the_same_answer_as_deriving_it() -> None:
    """`permits(theater, side, posture)` exists only so a caller that already
    derived the posture does not pay for it twice -- the map paid twice per zone
    and the generator three times, ~50% of the payload build on every terrain.

    It is a parameter and NOT a cached field on purpose: posture is derived so a
    country flips the turn its airfield changes hands, and a stored one would go
    stale exactly then. This pins that the shortcut cannot drift into a
    different answer, across every posture and both sides.
    """
    cases = {
        NEUTRAL: _theater(_cp(9999, 9999, blue=True)),
        BLUE_ALIGNED: _theater(_cp(50, 50, blue=True)),
        RED_ALIGNED: _theater(_cp(50, 50, red=True)),
        CONTESTED_ALIGNED: _theater(_cp(25, 25, blue=True), _cp(75, 75, red=True)),
    }
    zone = _box_zone()
    for expected, theater in cases.items():
        posture = zone.posture_in(theater)
        assert posture == expected
        for is_blue in (True, False):
            assert zone.permits(theater, is_blue, posture) == zone.permits(
                theater, is_blue
            ), f"{expected}: passing the posture changed the answer"


def test_an_overflight_override_still_wins_when_a_posture_is_passed() -> None:
    """The override is checked before the posture is looked at either way."""
    theater = _theater(_cp(9999, 9999, blue=True))
    for override in (True, False):
        zone = _box_zone(overflight=override)
        posture = zone.posture_in(theater)
        assert zone.permits(theater, True, posture) is override
        assert zone.permits(theater, True) is override


def test_a_campaign_can_still_turn_the_sam_off() -> None:
    """The default flipped on; the authored value has to keep winning."""
    entry = _entry()
    entry["sam"] = False
    zone = NeutralBorderZone.from_yaml(entry)
    assert zone is not None
    assert zone.sam is False
