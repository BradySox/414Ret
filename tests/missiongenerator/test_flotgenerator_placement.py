from unittest.mock import MagicMock, patch

from dcs.mapping import Point

from game.dcs.groundunittype import GroundUnitType
from game.ground_forces.ai_ground_planner import CombatGroup, CombatGroupRole
from game.missiongenerator.flotgenerator import FlotGenerator, frontline_offsets
from game.missiongenerator.frontlineconflictdescription import (
    FrontLineConflictDescription,
)
from game.utils import Heading


def _pt(x: float, y: float) -> Point:
    return Point(x, y, None)  # type: ignore[arg-type]


def _grp(role: CombatGroupRole) -> CombatGroup:
    return CombatGroup(role, MagicMock(spec=GroundUnitType), 1)


def test_wedges_evenly_spaced() -> None:
    w1 = _grp(CombatGroupRole.TANK)
    w2 = _grp(CombatGroupRole.TANK)
    offsets = frontline_offsets([w1, w2], 1000)
    assert offsets[id(w1)] == 250.0
    assert offsets[id(w2)] == 750.0


def test_member_shares_anchor_offset() -> None:
    wedge = _grp(CombatGroupRole.TANK)
    shorad = _grp(CombatGroupRole.SHORAD)
    shorad.anchor = wedge
    offsets = frontline_offsets([wedge, shorad], 1000)
    assert offsets[id(shorad)] == offsets[id(wedge)]


def test_unclustered_gets_an_offset() -> None:
    wedge = _grp(CombatGroupRole.TANK)
    arty = _grp(CombatGroupRole.ARTILLERY)
    offsets = frontline_offsets([wedge, arty], 1000)
    assert id(arty) in offsets
    assert 0 <= offsets[id(arty)] <= 1000


class _StripTheater:
    """Fakes a theater where land is a disc of radius `land_depth` around the
    origin, so the perpendicular walk in get_valid_position_for_group stops
    at a controllable, deterministic depth."""

    def __init__(self, land_depth: float) -> None:
        self.land_depth = land_depth

    def is_on_land(self, point: Point) -> bool:
        return point.distance_to_point(_pt(0, 0)) <= self.land_depth


def _flot_generator(conflict: FrontLineConflictDescription) -> FlotGenerator:
    # Full FlotGenerator construction needs a live Mission/Game; the method
    # under test only reads self.conflict, so build a bare instance.
    gen = object.__new__(FlotGenerator)
    gen.conflict = conflict
    return gen


def test_valid_position_prefers_partial_depth_over_stacking_fallback() -> None:
    """Regression test: once ANY perpendicular depth is reached, that point
    must be used rather than the front-axis collapse-prone fallback search
    (the original stacking bug -- see get_valid_position_for_group's
    comments). A rear-echelon group that can only reach 250m of a requested
    2000m depth before running into water should still get its own unique
    (partial-depth) point, not the shared front-axis search result."""
    conflict = FrontLineConflictDescription(
        theater=_StripTheater(land_depth=300),  # type: ignore[arg-type]
        front_line=MagicMock(),
        position=_pt(0, 0),
        heading=Heading.from_degrees(90),
        size=2000,
    )
    gen = _flot_generator(conflict)

    with patch.object(FrontLineConflictDescription, "find_ground_position") as fallback:
        result = gen.get_valid_position_for_group(
            distance_from_frontline=2000,
            spawn_heading=Heading.from_degrees(0),
            along_offset=0,
        )

    fallback.assert_not_called()
    assert round(result.distance_to_point(_pt(0, 0))) == 250


def test_valid_position_falls_back_only_when_completely_blocked() -> None:
    """When the perpendicular step can't move off the front line at all
    (reached_depth == 0), the front-axis fallback search is the only option
    left and should still be used."""
    conflict = FrontLineConflictDescription(
        theater=_StripTheater(land_depth=0),  # type: ignore[arg-type]
        front_line=MagicMock(),
        position=_pt(0, 0),
        heading=Heading.from_degrees(90),
        size=2000,
    )
    gen = _flot_generator(conflict)

    with patch.object(
        FrontLineConflictDescription,
        "find_ground_position",
        return_value=_pt(0, 0),
    ) as fallback:
        result = gen.get_valid_position_for_group(
            distance_from_frontline=2000,
            spawn_heading=Heading.from_degrees(0),
            along_offset=0,
        )

    fallback.assert_called_once()
    assert result == _pt(0, 0)
