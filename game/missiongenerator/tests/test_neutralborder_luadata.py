"""Emitter contract for dcsRetribution.neutralBorder (§97)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.luagenerator import LuaData
from game.missiongenerator.neutralborderluadata import (
    NeutralBorderLuaZone,
    populate_neutral_border_lua,
)


def _zone(battery: bool = True) -> NeutralBorderLuaZone:
    return NeutralBorderLuaZone(
        country="Lebanon",
        airfield="Rayak",
        floor_blue_ft=None,
        floor_red_ft=None,
        sam_groups=["NeutralBorder|Lebanon|SA-3|1"] if battery else [],
        red_country_id=34,
        blue_country_id=2,
        border=[(0.0, 0.0), (20000.0, 0.0), (20000.0, 20000.0), (0.0, 20000.0)],
    )


def _emit(enabled: bool, zones: list[Any]) -> str:
    root = LuaData("dcsRetribution")
    game = SimpleNamespace(settings=SimpleNamespace(neutral_border_defense=enabled))
    mission_data = SimpleNamespace(neutral_border_zones=zones)
    populate_neutral_border_lua(root, game, mission_data)  # type: ignore[arg-type]
    return root.create_operations_lua()


def test_emits_the_zone_with_its_battery_ids_and_border() -> None:
    lua = _emit(True, [_zone()])
    assert "neutralBorder" in lua
    assert "Lebanon" in lua
    assert "Rayak" in lua
    assert "NeutralBorder|Lebanon|SA-3|1" in lua
    # No floor emitted at all: this zone grants no safe altitude, and a
    # number in the payload would imply one exists.
    assert "floorBlueFt" not in lua
    assert "floorRedFt" not in lua
    assert "34" in lua and "2" in lua
    assert "20000.0" in lua  # border vertex, one decimal


def test_the_battery_key_is_absent_when_none_was_built() -> None:
    """The plugin drops an enforcing zone with no battery rather than promise a
    defence it cannot deliver, so the absence has to reach it."""
    lua = _emit(True, [_zone(battery=False)])
    assert "samGroups" not in lua


def test_every_battery_reaches_the_plugin() -> None:
    """A country stands one battery per stretch of war-facing frontier, and the
    plugin escalates the whole set together -- so it has to receive all of them,
    not just the first."""
    zone = NeutralBorderLuaZone(
        country="Pakistan",
        airfield=None,
        spawn=(0.0, 0.0),
        sam_groups=[f"NeutralBorder|Pakistan|S-300|{n}" for n in range(1, 5)],
        red_country_id=34,
        blue_country_id=2,
        border=[(0.0, 0.0), (20000.0, 0.0), (20000.0, 20000.0), (0.0, 20000.0)],
    )
    lua = _emit(True, [zone])
    for name in zone.sam_groups:
        assert name in lua


def test_setting_off_emits_nothing() -> None:
    lua = _emit(False, [_zone()])
    assert "neutralBorder" not in lua


def test_no_zones_emits_nothing() -> None:
    lua = _emit(True, [])
    assert "neutralBorder" not in lua


def test_the_label_anchor_reaches_the_plugin() -> None:
    """Without it the F10 map draws a shape with no name on it."""
    zone = _zone()
    lua = _emit(True, [type(zone)(**{**zone.__dict__, "label": (12345.0, -678.0)})])
    assert "labelX" in lua and "12345.0" in lua
    assert "labelZ" in lua and "-678.0" in lua


def test_a_zone_with_no_label_anchor_emits_none() -> None:
    """A degenerate ring has no representative point; the plugin then draws the
    border unlabelled rather than at the map origin."""
    lua = _emit(True, [_zone()])
    assert "labelX" not in lua


# -- the battery has to be there, sized, and deep ------------------------------


def test_the_ladder_gives_a_bigger_country_a_longer_ranged_system() -> None:
    """DM call 2026-09-07: a larger country gets a larger SAM, further back."""
    from datetime import date

    from game.missiongenerator.neutralbordersams import system_for
    from game.utils import nautical_miles

    day = date(2004, 6, 1)
    small = system_for("Freedonia", nautical_miles(10), day)
    large = system_for("Freedonia", nautical_miles(150), day)
    assert (
        large.reach > small.reach
    ), f"{large.name} does not out-range {small.name}, so size buys nothing"


def test_a_system_the_era_cannot_export_is_not_offered() -> None:
    """Checked 2026-09-07 against the 1982 Falklands column, where in-service
    dates rather than export dates handed Argentina a Buk."""
    from datetime import date

    from game.missiongenerator.neutralbordersams import system_for
    from game.utils import nautical_miles

    room = nautical_miles(150)
    assert system_for("Freedonia", room, date(1982, 5, 1)).name == "SA-3"
    assert system_for("Freedonia", room, date(2004, 6, 1)).name == "S-300"


def test_a_western_nation_does_not_get_soviet_kit() -> None:
    """Bloc posture gets Iraq and Russia wrong, so the west list is authored."""
    from datetime import date

    from game.missiongenerator.neutralbordersams import system_for
    from game.utils import nautical_miles

    day = date(2004, 6, 1)
    assert system_for("Israel", nautical_miles(20), day).name == "Hawk"
    assert system_for("Turkey", nautical_miles(150), day).name == "Patriot"
    assert system_for("Iran", nautical_miles(150), day).name == "S-300"


def test_the_site_stands_deep_but_still_covers_its_border() -> None:
    """Depth is what the DM asked for and is also why the swap cannot capture an
    airbase -- the site is not on one. It is capped at the system's own reach so
    the envelope still touches the frontier it defends."""
    from shapely.geometry import Point as ShapelyPoint, Polygon

    from game.theater.neutralborder import NeutralBorderZone

    square = [
        (-100_000.0, -100_000.0),
        (100_000.0, -100_000.0),
        (100_000.0, 100_000.0),
        (-100_000.0, 100_000.0),
    ]
    zone = NeutralBorderZone(country="Nowhere", border=square)
    reach = 20_000.0
    frontier = Polygon(square).exterior

    for site in zone.sam_sites((-99_000.0, 0.0), reach):
        gap = frontier.distance(ShapelyPoint(site))
        assert (
            gap >= reach - 1.0
        ), f"the site sits {gap:.0f} m in, shallower than its reach"
        assert gap <= reach + 1.0, (
            f"the site sits {gap:.0f} m in, deeper than its {reach:.0f} m reach, so "
            "its envelope no longer touches the border it defends"
        )


def test_a_long_border_gets_more_batteries_than_a_short_one() -> None:
    """The count is the whole point of the 2026-09-09 rework: one site covered
    3.5 % of Pakistan's frontier on the Afghanistan map."""
    from game.theater.neutralborder import NeutralBorderZone

    def square_of(half: float) -> NeutralBorderZone:
        return NeutralBorderZone(
            country="Nowhere",
            border=[
                (-half, -half),
                (half, -half),
                (half, half),
                (-half, half),
            ],
        )

    reach = 20_000.0
    small = square_of(30_000.0).sam_sites((0.0, 0.0), reach)
    large = square_of(400_000.0).sam_sites((0.0, 0.0), reach)
    assert len(small) < len(large)
    assert len(small) >= 1


def test_the_count_never_runs_away() -> None:
    """A battery is 4-5 emitting vehicles; an unbounded count would author an
    IADS the campaign never asked for."""
    from game.theater.neutralborder import MAX_SAM_SITES, NeutralBorderZone

    half = 1_000_000.0
    zone = NeutralBorderZone(
        country="Enormous",
        border=[(-half, -half), (half, -half), (half, half), (-half, half)],
    )
    assert len(zone.sam_sites((0.0, 0.0), 10_000.0)) <= MAX_SAM_SITES


def test_only_the_war_facing_frontier_is_manned() -> None:
    """A border 250 NM from every airbase is one no sortie reaches, and a
    battery there is units and RWR clutter spent on nobody."""
    from game.theater.neutralborder import NeutralBorderZone, war_region

    half = 400_000.0
    zone = NeutralBorderZone(
        country="Nowhere",
        border=[(-half, -half), (half, -half), (half, half), (-half, half)],
    )
    reach = 20_000.0
    # Uncapped, or the ceiling hides the difference this is measuring.
    everywhere = zone.sam_sites((-half, 0.0), reach, cap=64)
    # One airbase, hard against the western frontier.
    near_the_west = zone.sam_sites(
        (-half, 0.0), reach, war_region([(-half - 10_000.0, 0.0)]), cap=64
    )
    assert len(near_the_west) < len(everywhere)
    assert all(
        x < 0 for x, _ in near_the_west
    ), "a battery was placed on the far side of the country from the only war"


def test_a_country_always_puts_something_up() -> None:
    """Even one whose whole frontier is map edge, or is far from the war: it
    defends, so it defends with something."""
    from game.theater.neutralborder import NeutralBorderZone, war_region

    half = 100_000.0
    zone = NeutralBorderZone(
        country="Remote",
        border=[(-half, -half), (half, -half), (half, half), (-half, half)],
    )
    sites = zone.sam_sites(
        (0.0, 0.0), 20_000.0, war_region([(9_000_000.0, 9_000_000.0)])
    )
    assert len(sites) == 1


def test_a_zone_with_no_border_keeps_its_authored_origin() -> None:
    from game.theater.neutralborder import NeutralBorderZone

    zone = NeutralBorderZone(country="Unbounded")
    assert zone.sam_sites((5.0, 7.0), 20_000.0) == [(5.0, 7.0)]
    assert zone.interior_room() == 0.0


def test_a_country_with_an_origin_can_defend_without_an_airframe() -> None:
    """Since the patrol was dropped, defending needs only a position. That is a
    WIDENING: 14 zones that were drawn and toothless as fighter bases now hold a
    battery."""
    from datetime import date

    from game.theater.neutralborder import NeutralBorderZone

    day = date(2004, 6, 1)
    assert NeutralBorderZone(country="Turkmenistan", spawn=(0.0, 0.0)).can_defend(day)
    assert not NeutralBorderZone(country="Nowhere").can_defend(day)
