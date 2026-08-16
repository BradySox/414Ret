"""The committed debriefing must be the file on disk, not the watcher's snapshot.

Flown 2026-08-16 (session `c86c58dd`): the poll thread logged "Mission end
detected; stopping poll" two minutes into a 49-minute mission -- it had read a
stale state.json left by the previous mission, which carries `mission_ended`.
Fifty-three minutes later the player accepted the results and the turn committed
that two-minute snapshot. A strike flown in between was in the final state.json
by name and never reached the campaign.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List

import pytest

from game.finaldebriefing import final_debriefing, recorded_event_count


def debriefing(
    aircraft: int = 0,
    ground: int = 0,
    statics: int = 0,
    captures: int = 0,
) -> Any:
    return SimpleNamespace(
        state_data=SimpleNamespace(
            killed_aircraft=["a"] * aircraft,
            killed_ground_units=["g"] * ground,
            destroyed_statics=[{}] * statics,
            base_capture_events=["b"] * captures,
        )
    )


def test_a_fresh_read_with_more_events_wins() -> None:
    """The flown case: the watcher stopped early, the file kept growing."""
    stale = debriefing(aircraft=1, ground=3)
    fresh = debriefing(aircraft=12, ground=217, statics=54)

    assert final_debriefing(stale, lambda: fresh) is fresh


def test_a_shorter_fresh_read_is_not_trusted() -> None:
    """DCS rewrites state.json in place. A read that catches a partial write, or
    a file already replaced by the next mission, must never shrink the result."""
    cached = debriefing(aircraft=12, ground=217)
    truncated = debriefing(aircraft=1)

    assert final_debriefing(cached, lambda: truncated) is cached


def test_an_equal_read_uses_the_fresh_one() -> None:
    cached = debriefing(ground=5)
    fresh = debriefing(ground=5)

    assert final_debriefing(cached, lambda: fresh) is fresh


def test_an_unreadable_file_falls_back_to_the_cached_debriefing() -> None:
    """A missing or malformed state.json must not lose the turn outright."""
    cached = debriefing(ground=5)

    def boom() -> Any:
        raise OSError("state.json is gone")

    assert final_debriefing(cached, boom) is cached


def test_no_cached_debriefing_still_commits_the_file() -> None:
    """The watcher can miss every write (it only fires on an mtime newer than
    the .miz). The file is still the truth."""
    fresh = debriefing(ground=9)

    assert final_debriefing(None, lambda: fresh) is fresh


def test_no_cached_and_unreadable_yields_nothing() -> None:
    def boom() -> Any:
        raise ValueError("bad json")

    assert final_debriefing(None, boom) is None


def test_event_count_covers_every_recorded_category() -> None:
    # If a new category of recorded result is added to StateData without being
    # counted here, a fresh read could look "no bigger" than a stale snapshot
    # and lose exactly the thing that was added.
    assert (
        recorded_event_count(debriefing(aircraft=1, ground=2, statics=3, captures=4))
        == 10
    )
    assert recorded_event_count(SimpleNamespace()) == 0  # type: ignore[arg-type]


def test_the_flown_shape_is_reproduced() -> None:
    """The measured numbers from the flown session.

    The two-minute snapshot carried 4 ground deaths. The state.json on disk when
    the player accepted the results carried 341 dead events and 54 destroyed
    statics, including the three Tuapse dock buildings the strike destroyed.
    """
    snapshot_at_two_minutes = debriefing(ground=4)
    file_at_accept_time = debriefing(ground=341, statics=54)

    committed = final_debriefing(snapshot_at_two_minutes, lambda: file_at_accept_time)

    assert committed is file_at_accept_time
    assert recorded_event_count(committed) > recorded_event_count(
        snapshot_at_two_minutes
    )
