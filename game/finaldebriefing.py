"""Pick the debriefing that actually gets committed to the campaign.

The results window holds the last debriefing the poll thread handed it, and used
to commit exactly that. But the poll thread stops at the FIRST ``state.json`` it
sees carrying ``mission_ended`` -- and that can be a stale file left by the
previous mission, because the only guard is an mtime newer than the current
mission's ``.miz``. When it stops early, every kill after that moment is silently
dropped.

Flown 2026-08-16 (session ``c86c58dd``): the watcher logged "Mission end
detected; stopping poll" **two minutes into a 49-minute mission**, and 53 minutes
later the turn committed that two-minute snapshot. A strike on the Tuapse dock
complex landed in between; the buildings were in the final ``state.json`` by name
and the campaign still showed them standing. Rebuilding the debriefing from that
same file reproduces the kills exactly, which is what makes the snapshot -- not
the matching -- the culprit.

So the file on disk when the player accepts the results is the authority, not
whatever the watcher happened to catch. This module owns that choice so it is
type-checked and testable; the Qt window only calls it.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from game.debriefing import Debriefing


def recorded_event_count(debriefing: "Debriefing") -> int:
    """How much the debriefing actually claims happened.

    Only used to compare two readings of the same mission, so it needs to be
    monotonic in "more of the mission has been observed", not meaningful on its
    own.
    """
    state = getattr(debriefing, "state_data", None)
    if state is None:
        return 0
    return (
        len(getattr(state, "killed_aircraft", []) or [])
        + len(getattr(state, "killed_ground_units", []) or [])
        + len(getattr(state, "destroyed_statics", []) or [])
        + len(getattr(state, "base_capture_events", []) or [])
    )


def final_debriefing(
    cached: Optional["Debriefing"],
    reread: Callable[[], "Debriefing"],
) -> Optional["Debriefing"]:
    """The debriefing to commit: a fresh read of state.json when it has more.

    ``cached`` is the last one the poll thread delivered (may be None if the
    watcher never fired at all). ``reread`` re-reads state.json from disk.

    A fresh read that is *smaller* than the cached one is not trusted -- DCS
    rewrites state.json in place, so a read that catches a partial write, or a
    file already replaced by the next mission, must never shrink the result.
    """
    try:
        fresh = reread()
    except Exception:
        logging.exception(
            "Could not re-read state.json when committing results; using the last "
            "polled debriefing. Kills after the last poll may be missing."
        )
        return cached

    if cached is None:
        logging.info(
            "Committing a fresh read of state.json (%d recorded events); the poll "
            "thread never delivered one.",
            recorded_event_count(fresh),
        )
        return fresh

    fresh_count = recorded_event_count(fresh)
    cached_count = recorded_event_count(cached)
    if fresh_count > cached_count:
        logging.warning(
            "state.json on disk carries %d recorded events but the last polled "
            "debriefing had only %d -- committing the fresh read. The mission "
            "outlived the results watcher, which is how late kills used to be "
            "dropped.",
            fresh_count,
            cached_count,
        )
        return fresh
    if fresh_count < cached_count:
        logging.warning(
            "A fresh read of state.json has fewer recorded events (%d) than the "
            "last polled debriefing (%d); keeping the polled one. state.json was "
            "probably mid-write or already replaced.",
            fresh_count,
            cached_count,
        )
        return cached
    return fresh
