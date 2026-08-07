"""The pre-turn briefing must surface the reasons the campaign already knows.

These drive the real ``build_pre_turn_briefing`` against duck-typed game state.
The point of the feature is that every line comes from state ``finish_turn``
already produced, so the tests assert on *what the player is told* rather than
re-deriving the numbers.
"""

from __future__ import annotations

from typing import Any, List, Optional

import pytest

from game.fourteenth.pre_turn_briefing import (
    BACKGROUND,
    NOTABLE,
    URGENT,
    BriefingItem,
    PreTurnBriefing,
    build_pre_turn_briefing,
)


class FakePoint:
    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x = x
        self.y = y

    def distance_to_point(self, other: "FakePoint") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class FakeControlPoint:
    def __init__(
        self, name: str, captured: Any, x: float = 0.0, y: float = 0.0
    ) -> None:
        self.name = name
        self.captured = captured
        self.position = FakePoint(x, y)
        self.ground_objects: List[Any] = []

    def __str__(self) -> str:
        return self.name


class FakeTgo:
    def __init__(
        self,
        control_point: FakeControlPoint,
        category: str = "aa",
        concealed: bool = False,
        known: bool = True,
        dead: bool = False,
        map_hidden: bool = False,
    ) -> None:
        self.control_point = control_point
        self.category = category
        self.concealed = concealed
        self.map_hidden = map_hidden
        self._known = known
        self._dead = dead

    def known_for(self, viewer: Any = None) -> bool:
        return self._known

    def is_dead(self, viewer: Any = None) -> bool:
        return self._dead


class FakeTheater:
    def __init__(self, control_points: Optional[List[FakeControlPoint]] = None) -> None:
        self.controlpoints = control_points or []

    @property
    def ground_objects(self) -> Any:
        for cp in self.controlpoints:
            yield from cp.ground_objects

    def conflicts(self) -> List[Any]:
        return []


class FakePlayer:
    def __init__(self, is_blue: bool) -> None:
        self.is_blue = is_blue

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, FakePlayer) and other.is_blue == self.is_blue

    def __hash__(self) -> int:
        return hash(self.is_blue)


BLUE = FakePlayer(True)
RED = FakePlayer(False)


class FakeSettings:
    def __init__(self, **kwargs: Any) -> None:
        self.c2_decapitation_effects = kwargs.get("c2_decapitation_effects", False)


class FakeCoalition:
    def __init__(self, player: FakePlayer) -> None:
        self.player = player
        self.air_wing = FakeAirWing()


class FakeAirWing:
    def __init__(self) -> None:
        self.pending_arrivals: List[Any] = []


class FakeGame:
    def __init__(self, turn: int = 4, **kwargs: Any) -> None:
        self.turn = turn
        self.theater = FakeTheater(kwargs.get("control_points"))
        self.settings = FakeSettings(**kwargs)
        self.blue = FakeCoalition(BLUE)
        self.red = FakeCoalition(RED)
        self.last_sitrep: Any = None

    def point_in_world(self, x: float, y: float) -> FakePoint:
        return FakePoint(x, y)


# ------------------------------------------------------------------- plumbing


def test_a_quiet_campaign_produces_an_empty_briefing() -> None:
    briefing = build_pre_turn_briefing(FakeGame())  # type: ignore[arg-type]
    assert briefing.is_empty
    assert briefing.headline() is None
    assert briefing.turn == 4


def test_a_failing_section_never_breaks_the_briefing() -> None:
    """A briefing is not worth breaking a turn over."""
    game = FakeGame()
    del game.theater

    briefing = build_pre_turn_briefing(game)  # type: ignore[arg-type]

    assert isinstance(briefing, PreTurnBriefing)


def test_items_are_ordered_most_pressing_first() -> None:
    briefing = PreTurnBriefing(
        turn=3,
        items=[
            BriefingItem("arrival", "later", BACKGROUND),
            BriefingItem("consequence", "now", URGENT),
            BriefingItem("objective", "soon", NOTABLE),
        ],
    )
    assert [i.text for i in briefing.ordered()] == ["now", "soon", "later"]
    assert briefing.headline() == "now"


def test_by_kind_filters() -> None:
    briefing = PreTurnBriefing(
        turn=1,
        items=[BriefingItem("open_loop", "a"), BriefingItem("arrival", "b")],
    )
    assert [i.text for i in briefing.by_kind("open_loop")] == ["a"]


# --------------------------------------------------------------- open loops


def test_unidentified_contacts_are_counted() -> None:
    red_cp = FakeControlPoint("Haina", RED)
    red_cp.ground_objects = [
        FakeTgo(red_cp, concealed=True, known=False),
        FakeTgo(red_cp, concealed=True, known=False),
    ]
    game = FakeGame(control_points=[red_cp])

    briefing = build_pre_turn_briefing(game)  # type: ignore[arg-type]

    (item,) = briefing.by_kind("open_loop")
    assert "2 suspected contacts still unidentified" in item.text


def test_an_identified_contact_is_not_an_open_loop() -> None:
    red_cp = FakeControlPoint("Haina", RED)
    red_cp.ground_objects = [FakeTgo(red_cp, concealed=True, known=True)]
    game = FakeGame(control_points=[red_cp])

    assert build_pre_turn_briefing(game).by_kind("open_loop") == []  # type: ignore[arg-type]


def test_hidden_ambush_teams_are_never_surfaced() -> None:
    """§50 ambush teams are map_hidden by contract -- telegraphing them would
    undo the whole feature."""
    red_cp = FakeControlPoint("Haina", RED)
    red_cp.ground_objects = [
        FakeTgo(red_cp, concealed=True, known=False, map_hidden=True)
    ]
    game = FakeGame(control_points=[red_cp])

    assert build_pre_turn_briefing(game).by_kind("open_loop") == []  # type: ignore[arg-type]


def test_friendly_and_dead_objects_are_ignored() -> None:
    blue_cp = FakeControlPoint("Fulda", BLUE)
    blue_cp.ground_objects = [FakeTgo(blue_cp, concealed=True, known=False)]
    red_cp = FakeControlPoint("Haina", RED)
    red_cp.ground_objects = [FakeTgo(red_cp, concealed=True, known=False, dead=True)]
    game = FakeGame(control_points=[blue_cp, red_cp])

    assert build_pre_turn_briefing(game).by_kind("open_loop") == []  # type: ignore[arg-type]


def test_a_located_mobile_missile_site_is_an_open_loop() -> None:
    """§49 sites scoot between missions, so finding one is not killing it."""
    red_cp = FakeControlPoint("Wittstock", RED)
    red_cp.ground_objects = [FakeTgo(red_cp, category="missile", known=True)]
    game = FakeGame(control_points=[red_cp])

    (item,) = build_pre_turn_briefing(game).by_kind("open_loop")  # type: ignore[arg-type]
    assert "1 located missile site still alive" in item.text
    assert "scoot" in item.text


# ----------------------------------------------------------------- arrivals


def test_upcoming_arrivals_are_the_anticipation_band() -> None:
    from game.fourteenth.wing_growth import PendingSquadron

    class Sq:
        name = "HavLLv 31"
        aircraft = "F/A-18C"

    game = FakeGame(turn=1)
    game.blue.air_wing.pending_arrivals = [
        PendingSquadron(turn=3, squadron=Sq())  # type: ignore[arg-type]
    ]

    (item,) = build_pre_turn_briefing(game).by_kind("arrival")  # type: ignore[arg-type]

    assert "HavLLv 31" in item.text and "arrives turn 3" in item.text
    assert item.urgency == BACKGROUND


# --------------------------------------------------------------- consequence


def test_c2_damage_is_framed_as_something_you_caused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§52 already measures that killing command posts degrades enemy planning,
    and already renders it -- one turn late. Here it is attributed."""
    import game.fourteenth.c2_decapitation as c2

    monkeypatch.setattr(
        c2, "c2_status_line", lambda g, p: "1/3 command posts operational"
    )
    game = FakeGame(c2_decapitation_effects=True)

    (item,) = build_pre_turn_briefing(game).by_kind("consequence")  # type: ignore[arg-type]

    assert "1/3 command posts operational" in item.text
    assert "because of you" in item.text
    assert item.urgency == NOTABLE


def test_an_intact_enemy_network_says_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No damage claimed, no line -- the card never pads itself."""
    import game.fourteenth.c2_decapitation as c2

    monkeypatch.setattr(c2, "c2_status_line", lambda g, p: None)

    assert build_pre_turn_briefing(FakeGame()).by_kind("consequence") == []  # type: ignore[arg-type]


def test_sections_are_capped() -> None:
    """A long war must not produce an unreadable wall."""
    from game.fourteenth.wing_growth import PendingSquadron

    class Sq:
        def __init__(self, name: str) -> None:
            self.name = name
            self.aircraft = "F/A-18C"

    game = FakeGame(turn=1)
    game.blue.air_wing.pending_arrivals = [
        PendingSquadron(turn=3 + i, squadron=Sq(f"VFA-{i}"))  # type: ignore[arg-type]
        for i in range(10)
    ]

    assert len(build_pre_turn_briefing(game).by_kind("arrival")) <= 4  # type: ignore[arg-type]
