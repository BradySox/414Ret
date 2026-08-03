"""Tests for "The Wing Grows" -- scheduled squadron arrivals (414th).

The feature holds a campaign-authored squadron out of the air wing until its
turn, then joins and populates it. These drive the real
``promote_due_arrivals`` / ``upcoming_arrivals`` against duck-typed game and
wing objects, plus the real ``SquadronConfig`` parser and the real ``Sitrep``.
"""

from __future__ import annotations

from typing import Any, List, Optional

import pytest

from game.campaignloader.campaignairwingconfig import SquadronConfig
from game.fourteenth.wing_growth import (
    PendingSquadron,
    promote_due_arrivals,
    upcoming_arrivals,
)
from game.sitrep import Sitrep, SideLosses


class FakeSquadron:
    def __init__(self, name: str, aircraft: str = "F-14A", location: str = "Nordholz"):
        self.name = name
        self.aircraft = aircraft
        self.location = location
        self.populated_full: Optional[bool] = None
        self.coalition: Any = None

    def populate_for_turn_0(self, squadrons_start_full: bool) -> None:
        self.populated_full = squadrons_start_full

    def __str__(self) -> str:
        return self.name


class FakeAirWing:
    def __init__(self, started_full: bool = False) -> None:
        self.joined: List[FakeSquadron] = []
        self.pending_arrivals: List[PendingSquadron] = []
        self.squadrons_started_full = started_full

    def add_squadron(self, squadron: FakeSquadron) -> None:
        self.joined.append(squadron)


class FakePlayer:
    def __init__(self, is_blue: bool) -> None:
        self.is_blue = is_blue


class FakeCoalition:
    def __init__(self, is_blue: bool, started_full: bool = False) -> None:
        self.player = FakePlayer(is_blue)
        self.air_wing = FakeAirWing(started_full)


class FakeGame:
    def __init__(self, turn: int, started_full: bool = False) -> None:
        self.turn = turn
        self.blue = FakeCoalition(True, started_full)
        self.red = FakeCoalition(False, started_full)
        self.last_sitrep: Optional[Sitrep] = None


def schedule(
    game: FakeGame,
    turn: int,
    name: str = "VF-154",
    blue: bool = True,
    note: Optional[str] = None,
    aircraft: str = "F-14A",
) -> FakeSquadron:
    coalition = game.blue if blue else game.red
    squadron = FakeSquadron(name, aircraft=aircraft)
    squadron.coalition = coalition
    coalition.air_wing.pending_arrivals.append(
        PendingSquadron(turn=turn, squadron=squadron, note=note)  # type: ignore[arg-type]
    )
    return squadron


# ---------------------------------------------------------------- config parse


def config_data(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {"primary": "BARCAP"}
    data.update(overrides)
    return data


def test_unset_schedule_is_none() -> None:
    """The stock case: no key authored, no schedule, no behavior change."""
    config = SquadronConfig.from_data(config_data())
    assert config.available_from_turn is None
    assert config.arrival_note is None


def test_schedule_is_parsed() -> None:
    config = SquadronConfig.from_data(
        config_data(available_from_turn=5, arrival_note="F 17 Blekinge Wing")
    )
    assert config.available_from_turn == 5
    assert config.arrival_note == "F 17 Blekinge Wing"


@pytest.mark.parametrize("bad", ["4", 4.5, True, [4]])
def test_a_non_integer_schedule_aborts_loudly(bad: Any) -> None:
    """A bad value is an authoring error: raise rather than silently ignore the
    schedule and hand the player a wing that quietly never grows."""
    with pytest.raises(ValueError):
        SquadronConfig.from_data(config_data(available_from_turn=bad))


def test_a_negative_schedule_aborts_loudly() -> None:
    with pytest.raises(ValueError):
        SquadronConfig.from_data(config_data(available_from_turn=-1))


# ------------------------------------------------------------------ promotion


def test_a_squadron_stays_out_of_the_wing_before_its_turn() -> None:
    game = FakeGame(turn=2)
    squadron = schedule(game, turn=4)

    assert promote_due_arrivals(game) == []  # type: ignore[arg-type]
    assert game.blue.air_wing.joined == []
    assert squadron.populated_full is None
    assert len(game.blue.air_wing.pending_arrivals) == 1


def test_a_squadron_joins_on_its_turn_and_is_populated() -> None:
    game = FakeGame(turn=4, started_full=True)
    squadron = schedule(game, turn=4)

    lines = promote_due_arrivals(game)  # type: ignore[arg-type]

    assert game.blue.air_wing.joined == [squadron]
    assert game.blue.air_wing.pending_arrivals == []
    # Populated by the same rule the rest of the wing used at turn 0.
    assert squadron.populated_full is True
    assert len(lines) == 1
    assert "VF-154" in lines[0] and "Nordholz" in lines[0]


def test_an_arrival_populates_by_the_wings_own_start_full_rule() -> None:
    game = FakeGame(turn=4, started_full=False)
    squadron = schedule(game, turn=4)

    promote_due_arrivals(game)  # type: ignore[arg-type]

    assert squadron.populated_full is False


def test_a_late_arrival_still_joins() -> None:
    """A schedule missed while the game was elsewhere (a re-init, a load) is not
    stranded: anything whose turn has passed joins at the next opportunity."""
    game = FakeGame(turn=9)
    squadron = schedule(game, turn=4)

    promote_due_arrivals(game)  # type: ignore[arg-type]

    assert game.blue.air_wing.joined == [squadron]


def test_promotion_is_idempotent_within_a_turn() -> None:
    """initialize_turn runs more than once per turn (base capture, TGO buy/sell),
    so a second pass must not re-join or re-announce."""
    game = FakeGame(turn=4)
    schedule(game, turn=4)

    first = promote_due_arrivals(game)  # type: ignore[arg-type]
    second = promote_due_arrivals(game)  # type: ignore[arg-type]

    assert len(first) == 1
    assert second == []
    assert len(game.blue.air_wing.joined) == 1


def test_only_due_arrivals_are_promoted() -> None:
    game = FakeGame(turn=5)
    early = schedule(game, turn=3, name="HavLLv 31")
    due = schedule(game, turn=5, name="F 17")
    later = schedule(game, turn=9, name="34th BS")

    promote_due_arrivals(game)  # type: ignore[arg-type]

    assert game.blue.air_wing.joined == [early, due]
    assert [a.squadron for a in game.blue.air_wing.pending_arrivals] == [later]


def test_red_arrivals_join_but_are_never_announced() -> None:
    """Code is symmetric so a red schedule works, but the enemy order of battle
    is not the player's to read."""
    game = FakeGame(turn=4)
    red_squadron = schedule(game, turn=4, name="33 GvIAP", blue=False)

    lines = promote_due_arrivals(game)  # type: ignore[arg-type]

    assert game.red.air_wing.joined == [red_squadron]
    assert lines == []


def test_no_schedule_is_a_no_op() -> None:
    game = FakeGame(turn=7)

    assert promote_due_arrivals(game) == []  # type: ignore[arg-type]
    assert game.blue.air_wing.joined == []
    assert game.red.air_wing.joined == []


def test_a_failing_arrival_is_dropped_not_retried_forever() -> None:
    game = FakeGame(turn=4)
    squadron = schedule(game, turn=4)

    def boom(_: bool) -> None:
        raise RuntimeError("no parking, no pilots, no anything")

    squadron.populate_for_turn_0 = boom  # type: ignore[assignment]

    lines = promote_due_arrivals(game)  # type: ignore[arg-type]

    assert lines == []
    assert game.blue.air_wing.pending_arrivals == []


def test_the_note_rides_the_announcement() -> None:
    game = FakeGame(turn=3)
    schedule(game, turn=3, name="HavLLv 31", note="Karjalan Lennosto")

    (line,) = promote_due_arrivals(game)  # type: ignore[arg-type]

    assert "Karjalan Lennosto" in line


# ------------------------------------------------------- the upcoming schedule


def test_upcoming_arrivals_are_sorted_by_turn() -> None:
    """The motivational half: the jet you cannot fly yet is the advert."""
    game = FakeGame(turn=1)
    schedule(game, turn=9, name="34th BS", aircraft="B-1B")
    schedule(game, turn=3, name="HavLLv 31", aircraft="F/A-18C")
    schedule(game, turn=5, name="F 17", aircraft="JAS 39C")

    lines = upcoming_arrivals(game)  # type: ignore[arg-type]

    assert [line.split()[0] for line in lines] == ["HavLLv", "F", "34th"]
    assert "arrives turn 3" in lines[0]


def test_upcoming_arrivals_is_empty_without_a_schedule() -> None:
    assert upcoming_arrivals(FakeGame(turn=1)) == []  # type: ignore[arg-type]


# ------------------------------------------------------------ sitrep surfacing


def quiet_sitrep() -> Sitrep:
    import datetime

    return Sitrep(
        turn=4,
        day=datetime.date(2027, 5, 1),
        friendly=SideLosses(aircraft=0, front_line=0, sites=0),
        enemy=SideLosses(aircraft=0, front_line=0, sites=0),
        captured=[],
        lost=[],
        pilots_recovered=0,
    )


def test_an_arrival_makes_a_quiet_turn_newsworthy() -> None:
    """Unlike the C2/victory lines an arrival is a discrete event, so it should
    surface even on an otherwise quiet turn."""
    sitrep = quiet_sitrep()
    quiet_before = sitrep.is_empty

    sitrep.arrivals.append("VF-154 (F-14A) arrived at Nordholz")

    assert quiet_before, "fixture should start with nothing to report"
    assert sitrep.is_empty is False
    assert sitrep.has_news
    assert any("ARRIVED: VF-154" in line for line in sitrep.kneeboard_lines())


def test_a_sitrep_without_arrivals_is_unchanged() -> None:
    sitrep = quiet_sitrep()
    assert sitrep.arrivals == []
    assert not any("ARRIVED" in line for line in sitrep.kneeboard_lines())


def test_promotion_appends_to_the_sitrep_the_player_is_about_to_read() -> None:
    """The frozen Sitrep's list field is mutated in place, which is what lets the
    turn-initialization hook announce onto the sitrep recorded moments earlier."""
    sitrep = quiet_sitrep()
    game = FakeGame(turn=4)
    game.last_sitrep = sitrep
    schedule(game, turn=4)

    lines = promote_due_arrivals(game)  # type: ignore[arg-type]
    sitrep.arrivals.extend(lines)

    assert len(sitrep.arrivals) == 1
    assert not sitrep.is_empty
