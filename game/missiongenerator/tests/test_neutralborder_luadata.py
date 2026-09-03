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


def test_the_whole_orbit_clears_the_border_not_just_the_leg() -> None:
    """A racetrack overshoots each end before turning back.

    FLOWN 2026-08-30: the leg was only required to sit inside the border, so
    the patrol crossed into the neighbour by under 10 NM past each end. The
    leg is now fitted inside the border pulled in by a clearance that covers
    the overshoot.
    """
    from game.missiongenerator.neutralbordergenerator import (
        PATROL_CLEARANCES_M,
        PATROL_LEG_NM,
    )
    from game.theater.neutralborder import NeutralBorderZone
    from shapely.geometry import LineString, Polygon

    # 200 x 200 km: room for the full leg and the full clearance.
    square = [
        (-100_000.0, -100_000.0),
        (100_000.0, -100_000.0),
        (100_000.0, 100_000.0),
        (-100_000.0, 100_000.0),
    ]
    zone = NeutralBorderZone(country="Nowhere", border=square)

    centre, end = zone.patrol_orbit(
        (0.0, 0.0), PATROL_LEG_NM.meters, PATROL_CLEARANCES_M
    )
    assert end is not None, "a leg fits in a 200 km square and one was not found"
    gap = Polygon(square).exterior.distance(LineString([centre, end]))
    assert gap >= max(PATROL_CLEARANCES_M) - 1.0, (
        f"the leg sits {gap / 1852:.1f} NM from the border; the overshoot past "
        "its ends would cross out"
    )


def test_a_station_on_the_frontier_is_moved_inland() -> None:
    """Several shipped stations sit on their own border.

    India's is 0.6 NM from it in a zone that could hold 75, so no orbit
    centred there can stay inside whatever its size. The correction is the
    nearest point with room, not a jump to the country's deep interior.
    """
    from game.missiongenerator.neutralbordergenerator import (
        PATROL_CLEARANCES_M,
        PATROL_LEG_NM,
    )
    from game.theater.neutralborder import NeutralBorderZone
    from shapely.geometry import Point as ShapelyPoint, Polygon

    square = [
        (-100_000.0, -100_000.0),
        (100_000.0, -100_000.0),
        (100_000.0, 100_000.0),
        (-100_000.0, 100_000.0),
    ]
    zone = NeutralBorderZone(country="Nowhere", border=square)
    on_the_line = (-99_000.0, 0.0)

    centre, end = zone.patrol_orbit(
        on_the_line, PATROL_LEG_NM.meters, PATROL_CLEARANCES_M
    )
    assert end is not None
    moved = Polygon(square).exterior.distance(ShapelyPoint(centre))
    assert (
        moved >= max(PATROL_CLEARANCES_M) - 1.0
    ), f"the centre is still {moved / 1852:.1f} NM from the border"
    # The smallest correction that works: it stays on the side it was authored.
    assert centre[0] < 0, f"the patrol jumped across the country to {centre}"


def test_a_country_too_small_for_any_cleared_orbit_gets_a_circle() -> None:
    """Bahrain's zone holds a 5 NM inscribed circle and nothing fits it.

    The caller flies a circle there. It still crosses out -- at that size
    nothing does not -- but a one-waypoint racetrack would put the flight in
    the ground, which is the failure this fallback exists to avoid.
    """
    from game.missiongenerator.neutralbordergenerator import (
        PATROL_CLEARANCES_M,
        PATROL_LEG_NM,
    )
    from game.theater.neutralborder import NeutralBorderZone

    # 2 km across: smaller than the tightest clearance tried.
    sliver = [
        (-1_000.0, -1_000.0),
        (1_000.0, -1_000.0),
        (1_000.0, 1_000.0),
        (-1_000.0, 1_000.0),
    ]
    zone = NeutralBorderZone(country="Sliver", border=sliver)

    _, end = zone.patrol_orbit((0.0, 0.0), PATROL_LEG_NM.meters, PATROL_CLEARANCES_M)
    assert end is None


def test_a_zone_with_no_border_polygon_gets_no_racetrack() -> None:
    """A campaign may author a zone with an airfield and no polygon."""
    from game.missiongenerator.neutralbordergenerator import (
        PATROL_CLEARANCES_M,
        PATROL_LEG_NM,
    )
    from game.theater.neutralborder import NeutralBorderZone

    zone = NeutralBorderZone(country="Unbounded")
    centre, end = zone.patrol_orbit(
        (5.0, 7.0), PATROL_LEG_NM.meters, PATROL_CLEARANCES_M
    )
    assert end is None
    assert centre == (5.0, 7.0), "an unbounded zone must not move its station"


def test_the_generated_patrol_has_a_second_waypoint() -> None:
    """The isolated leg maths is not the thing that shipped broken.

    FLOWN 2026-08-29: no leg fitter existed and the generator wrote one
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
