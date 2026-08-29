"""Emitter contract for dcsRetribution.neutralBorder (§96)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.luagenerator import LuaData
from game.missiongenerator.neutralborderluadata import (
    NeutralBorderLuaZone,
    populate_neutral_border_lua,
)


def _zone(sam: bool = True) -> NeutralBorderLuaZone:
    return NeutralBorderLuaZone(
        country="Lebanon",
        airfield="Rayak",
        floor_blue_ft=None,
        floor_red_ft=None,
        fighter_template="NeutralBorder|Lebanon|MiG-29A",
        sam_template="NeutralBorder|Lebanon|SAM" if sam else None,
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


def test_emits_the_zone_with_templates_ids_and_border() -> None:
    lua = _emit(True, [_zone()])
    assert "neutralBorder" in lua
    assert "Lebanon" in lua
    assert "Rayak" in lua
    assert "NeutralBorder|Lebanon|MiG-29A" in lua
    assert "NeutralBorder|Lebanon|SAM" in lua
    # No floor emitted at all: this zone grants no safe altitude, and a
    # number in the payload would imply one exists.
    assert "floorBlueFt" not in lua
    assert "floorRedFt" not in lua
    assert "34" in lua and "2" in lua
    assert "20000.0" in lua  # border vertex, one decimal


def test_sam_key_is_absent_when_no_sam_template() -> None:
    lua = _emit(True, [_zone(sam=False)])
    assert "samTemplate" not in lua
    assert "fighterTemplate" in lua


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


# -- the patrol has to be able to stay in the air ------------------------------


def test_the_orbit_speed_is_written_in_km_h_not_m_s() -> None:
    """Every pydcs speed argument is km/h and it divides by 3.6 on write.

    FLOWN 2026-08-29: the generator "helpfully" converted CAP_SPEED_KPH to m/s
    before handing it to OrbitAction, so the division happened twice and the
    orbit task carried 57.8 m/s -- 112 kt. The F-16A, MiG-29A and Su-30 patrols
    all stalled and crashed within a minute of mission start. Nothing caught it:
    the value is plausible-looking in every file it passes through.
    """
    from dcs.task import OrbitAction

    from game.missiongenerator.neutralbordergenerator import CAP_SPEED_KPH

    speed_ms = OrbitAction(
        6096, int(CAP_SPEED_KPH), OrbitAction.OrbitPattern.RaceTrack
    ).dict()["params"]["speed"]
    knots = speed_ms * 1.94384

    assert knots > 250, (
        f"the orbit task commands {knots:.0f} kt -- a fighter told to hold that "
        "stalls and falls out of the sky"
    )
    assert knots < 700, f"the orbit task commands {knots:.0f} kt, which is not an orbit"


def test_a_racetrack_leg_stays_inside_the_border() -> None:
    """A Race-Track orbit flies between its waypoint and the NEXT one.

    FLOWN 2026-08-29: the patrol had a one-waypoint route, so there was no leg.
    All three leaders -- India's Su-30, Iran's MiG-29A and Pakistan's F-16A --
    flew into the ground within 34-43 s, and the wingmen followed them down to
    1,035-3,791 m before pulling out. Every working racetrack in the same .miz
    had 13-15 route points.
    """
    from game.missiongenerator.neutralbordergenerator import PATROL_LEG_NM
    from game.theater.neutralborder import NeutralBorderZone

    # A 200 x 200 km square: any 25 NM leg from the middle fits.
    square = [
        (-100_000.0, -100_000.0),
        (100_000.0, -100_000.0),
        (100_000.0, 100_000.0),
        (-100_000.0, 100_000.0),
    ]
    zone = NeutralBorderZone(country="Nowhere", border=square)

    end = zone.patrol_leg_end((0.0, 0.0), PATROL_LEG_NM.meters)
    assert end is not None, "a leg fits in a 200 km square and one was not found"
    assert all(abs(v) < 100_000.0 for v in end), f"leg end {end} left the border"


def test_a_country_too_thin_for_a_leg_gets_no_racetrack() -> None:
    """The fallback matters: a circle needs no second point, a racetrack does.

    Without this the thin-country case would ship the exact one-waypoint
    racetrack that put three patrol leaders into the ground.
    """
    from game.missiongenerator.neutralbordergenerator import PATROL_LEG_NM
    from game.theater.neutralborder import NeutralBorderZone

    # 2 km wide. The shortest leg tried is 0.35 x 25 NM = 16 km.
    sliver = [
        (-1_000.0, -1_000.0),
        (1_000.0, -1_000.0),
        (1_000.0, 1_000.0),
        (-1_000.0, 1_000.0),
    ]
    zone = NeutralBorderZone(country="Sliver", border=sliver)

    assert zone.patrol_leg_end((0.0, 0.0), PATROL_LEG_NM.meters) is None


def test_a_zone_with_no_border_polygon_gets_no_racetrack() -> None:
    """A campaign may author a zone with an airfield and no polygon."""
    from game.missiongenerator.neutralbordergenerator import PATROL_LEG_NM
    from game.theater.neutralborder import NeutralBorderZone

    zone = NeutralBorderZone(country="Unbounded")
    assert zone.patrol_leg_end((0.0, 0.0), PATROL_LEG_NM.meters) is None


def test_the_generated_patrol_has_a_second_waypoint() -> None:
    """The isolated leg maths is not the thing that shipped broken.

    FLOWN 2026-08-29: patrol_leg_end did not exist and the generator wrote one
    waypoint, so this is the assertion that would have caught it. Builds the
    real group through the real generator on a real pydcs mission.
    """
    from datetime import date

    from dcs import Mission
    from dcs.coalition import Coalition
    from dcs.task import OrbitAction
    from dcs.terrain import Caucasus

    from game.missiongenerator.neutralbordergenerator import (
        PATROL_SIZE,
        NeutralBorderGenerator,
    )
    from game.theater.neutralborder import NeutralBorderZone

    mission = Mission(terrain=Caucasus())
    mission.coalition["neutrals"] = Coalition("neutrals")
    # A square around the map origin, big enough to hold a 25 NM leg.
    square = [
        (-120_000.0, -120_000.0),
        (120_000.0, -120_000.0),
        (120_000.0, 120_000.0),
        (-120_000.0, 120_000.0),
    ]
    zone = NeutralBorderZone(
        country="Turkey",
        aircraft="F-4E-45MC",
        spawn=(0.0, 0.0),
        border=square,
    )
    theater = SimpleNamespace(neutral_border_zones=[zone], controlpoints=[])
    game = SimpleNamespace(
        settings=SimpleNamespace(neutral_border_defense=True),
        theater=theater,
        current_day=date(2004, 6, 1),
    )
    mission_data = SimpleNamespace(neutral_border_zones=[])
    NeutralBorderGenerator(
        mission, game, mission_data, blue_country_id=2, red_country_id=34  # type: ignore[arg-type]
    ).generate()

    groups = [
        group
        for country in mission.coalition["neutrals"].countries.values()
        for group in country.plane_group
        if group.name.startswith("NeutralBorder|")
    ]
    assert groups, "the patrol was never built"
    patrol = groups[0]
    assert len(patrol.points) == 2, (
        f"the patrol has {len(patrol.points)} route point(s); a Race-Track orbit "
        "flies between its waypoint and the next one, so one point is no leg"
    )
    orbits = [t for t in patrol.points[0].tasks if isinstance(t, OrbitAction)]
    assert orbits, "no orbit task on the patrol"
    assert orbits[0].dict()["params"]["pattern"] == "Race-Track"
    # DM call 2026-08-29: a neutral answers a modern jet with numbers, not with
    # a better missile. Four also breaks SPAWN:InitLimit if its unit cap is set
    # below the template size, which is why the second flight now caps at 0.
    assert len(patrol.units) == PATROL_SIZE
