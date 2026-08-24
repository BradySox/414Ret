"""The bullseye is pinned for the campaign, and never anchored on a boat.

Upstream re-derived both bullseyes from the nearest opposing pair on every
`initialize_turn`, so the point a squadron memorizes moved whenever the front
did -- and on a Marianas save it landed on a red carrier in open water.
"""

from types import SimpleNamespace
from typing import Any, List, Optional

from dcs.mapping import Point

from game.coalition import Coalition
from game.theater.bullseye import MAX_DRIFT, Bullseye
from game.theater.conflicttheater import ConflictTheater
from game.theater.controlpoint import Fob, OffMapSpawn, Player
from game.utils import meters, nautical_miles


def _fob(name: str, x: float, y: float, blue: bool) -> Fob:
    player = Player.BLUE if blue else Player.RED
    cp = Fob(
        name=name,
        at=Point(x, y, None),  # type: ignore[arg-type]
        theater=None,  # type: ignore[arg-type]
        starts_blue=player,
    )
    cp._coalition = SimpleNamespace(player=player)  # type: ignore[assignment]
    return cp


def _offmap(name: str, x: float, y: float, blue: bool) -> OffMapSpawn:
    player = Player.BLUE if blue else Player.RED
    cp = OffMapSpawn(
        name=name,
        position=Point(x, y, None),  # type: ignore[arg-type]
        theater=None,  # type: ignore[arg-type]
        starts_blue=player,
    )
    cp._coalition = SimpleNamespace(player=player)  # type: ignore[assignment]
    return cp


def _fleet(name: str, x: float, y: float, blue: bool) -> Any:
    """A boat, faked down to what the anchor picker reads."""
    player = Player.BLUE if blue else Player.RED
    return SimpleNamespace(
        name=name,
        position=Point(x, y, None),  # type: ignore[arg-type]
        is_fleet=True,
        captured=player,
    )


def _theater(control_points: List[Any]) -> ConflictTheater:
    theater = ConflictTheater.__new__(ConflictTheater)
    theater.controlpoints = control_points
    return theater


def _coalition(bullseye: Optional[Bullseye] = None, pinned: bool = True) -> Coalition:
    coalition = Coalition.__new__(Coalition)
    coalition.bullseye = bullseye or Bullseye(Point(0, 0, None))  # type: ignore[arg-type]
    coalition.bullseye_pinned = pinned and bullseye is not None
    coalition.bullseye_moved_on_turn = None
    coalition.bullseye_anchor_name = None
    return coalition


def _anchor(x: float, name: str = "Anchor") -> Any:
    """A control point, faked down to what ``anchor_bullseye`` reads."""
    return SimpleNamespace(name=name, position=Point(x, 0, None))  # type: ignore[arg-type]


def test_anchors_skip_the_fleet_and_take_the_land_base() -> None:
    boat = _fleet("CVN", 0, 0, blue=True)
    field = _fob("Andersen", 200_000, 0, blue=True)
    red = _fob("Saipan", 210_000, 0, blue=False)

    blue_cp, red_cp = _theater([boat, field, red]).bullseye_anchors()

    assert blue_cp is field
    assert red_cp is red


def test_anchors_skip_the_off_map_spawn() -> None:
    turkey = _offmap("Turkey", 0, 0, blue=True)
    field = _fob("Kutaisi", 200_000, 0, blue=True)
    red = _fob("Khashuri", 210_000, 0, blue=False)

    blue_cp, _ = _theater([turkey, field, red]).bullseye_anchors()

    assert blue_cp is field


def test_a_side_with_only_boats_still_gets_an_anchor() -> None:
    boat = _fleet("CVN", 0, 0, blue=True)
    red = _fob("Saipan", 210_000, 0, blue=False)

    blue_cp, red_cp = _theater([boat, red]).bullseye_anchors()

    assert blue_cp is boat
    assert red_cp is red


def test_closest_opposing_control_points_still_sees_the_fleet() -> None:
    """The conflict description keeps upstream's unfiltered pair."""
    boat = _fleet("CVN", 0, 0, blue=True)
    field = _fob("Andersen", 200_000, 0, blue=True)
    red = _fob("Saipan", 10_000, 0, blue=False)

    blue_cp, _ = _theater([boat, field, red]).closest_opposing_control_points()

    assert blue_cp is boat


def test_first_anchor_of_a_new_campaign_is_a_pin_not_a_move() -> None:
    coalition = _coalition()

    moved = coalition.anchor_bullseye(_anchor(0, "Kutaisi"), turn=0)

    assert not moved
    assert coalition.bullseye_pinned
    assert coalition.bullseye.position.x == 0
    assert coalition.bullseye_moved_on_turn is None
    assert coalition.bullseye_anchor_name == "Kutaisi"


def test_a_pre_pin_save_re_anchors_once_and_says_so() -> None:
    """A save whose bullseye may sit on a boat is not frozen there."""
    boat = Bullseye(Point(0, 0, None))  # type: ignore[arg-type]
    coalition = _coalition(boat, pinned=False)  # unpickled: pin defaults False

    moved = coalition.anchor_bullseye(_anchor(500, "FOB Agrihan"), turn=14)

    assert moved
    assert coalition.bullseye_moved_on_turn == 14
    assert coalition.bullseye_anchor_name == "FOB Agrihan"


def test_a_pre_pin_save_that_re_anchors_in_place_says_nothing() -> None:
    """Every land campaign hits this on the first turn after the update."""
    anchor = _anchor(1234, "King Abdullah II")
    coalition = _coalition(Bullseye(anchor.position), pinned=False)

    moved = coalition.anchor_bullseye(anchor, turn=14)

    assert not moved
    assert coalition.bullseye_pinned
    assert coalition.bullseye_moved_on_turn is None
    assert coalition.bullseye_anchor_name == "King Abdullah II"


def test_a_pinned_bullseye_holds_while_the_candidate_is_close() -> None:
    pinned = Point(0, 0, None)  # type: ignore[arg-type]
    coalition = _coalition(Bullseye(pinned))
    nearly = MAX_DRIFT.meters - 1

    moved = coalition.anchor_bullseye(_anchor(nearly), turn=7)

    assert not moved
    assert coalition.bullseye.position is pinned
    assert coalition.bullseye_moved_on_turn is None


def test_a_pinned_bullseye_moves_once_the_front_has_carried_it_away() -> None:
    coalition = _coalition(Bullseye(Point(0, 0, None)))  # type: ignore[arg-type]
    far = nautical_miles(120).meters

    moved = coalition.anchor_bullseye(_anchor(far), turn=7)

    assert moved
    assert coalition.bullseye.position.x == far
    assert coalition.bullseye_moved_on_turn == 7


def test_drift_is_measured_against_the_threshold() -> None:
    bullseye = Bullseye(Point(0, 0, None))  # type: ignore[arg-type]

    assert not bullseye.drifted_from(Point(meters(1).meters, 0, None))  # type: ignore[arg-type]
    assert bullseye.drifted_from(Point(nautical_miles(81).meters, 0, None))  # type: ignore[arg-type]
