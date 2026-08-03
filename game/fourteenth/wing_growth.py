"""The Wing Grows -- scheduled mid-campaign squadron arrivals (414th).

A campaign can hold a squadron back and have it show up on a later turn:

    squadrons:
      Nordholz:
        - primary: DEAD
          aircraft: ["[CH] JAS 39C Gripen"]
          available_from_turn: 5
          arrival_note: "F 17 Blekinge Wing, Ronneby"

Why: single-player campaigns die after turn 1, and one reason is that turn 1 is
the best mission *by construction* -- the wing is at maximum strength and every
later turn is a degraded copy of it. A schedule inverts that: the turn-1 wing is
no longer the whole wing you will ever have, so the campaign gains an upward
slope and "the Prowlers arrive turn 6" becomes a reason to play to turn 6. See
``docs/dev/design/414th-wing-growth-notes.md``.

How it works, and why it is small:

* The squadron is **built at turn 0 exactly as today** (same preset selection,
  country pin, callsign overrides, def claiming) and simply held in
  ``AirWing.pending_arrivals`` instead of being added to the wing. One
  construction path, and a schedule that cannot fail later because a preset
  became unavailable.
* ``ControlPoint.squadrons`` is a *derived* property (it filters
  ``air_wing.iter_squadrons()`` on ``squadron.location``), so there is no
  base->squadron list to maintain: the moment a squadron joins the wing it
  appears at its base and ``best_squadrons_for`` can see it. **The planner needs
  no change at all.**
* Everything that walks the wing per turn (``AirWing.reset``,
  ``populate_for_turn_0``, ``end_turn``) iterates ``iter_squadrons()``, so a
  pending squadron is untouched by all of it for free. It is not hidden; it is
  genuinely not in the wing yet.

Promotion runs from ``Game.initialize_turn`` *before* the coalitions initialize,
so an arriving squadron is populated and plannable on its own arrival turn.
Removing from the pending list makes it naturally idempotent under the
re-initialization cases (base capture, TGO buy/sell) that call
``initialize_turn`` more than once per turn.

No setting gates this: a campaign that authors no ``available_from_turn`` has an
empty pending list and byte-identical behaviour.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from game.game import Game
    from game.squadrons.squadron import Squadron


@dataclass
class PendingSquadron:
    """A squadron built at turn 0 but not yet part of the air wing.

    ``turn`` is compared against the raw ``Game.turn`` -- the same number the
    §58 briefing card and the kneeboard print -- so "turn 4" in a campaign yaml
    is the "turn 4" the player reads in the cockpit.
    """

    turn: int
    squadron: "Squadron"
    note: Optional[str] = field(default=None)

    @property
    def arrival_line(self) -> str:
        """The announcement line for this arrival."""
        squadron = self.squadron
        line = f"{squadron.name} ({squadron.aircraft}) arrived at {squadron.location}"
        if self.note:
            line = f"{line} — {self.note}"
        return line


def promote_due_arrivals(game: "Game") -> List[str]:
    """Join every pending squadron whose turn has come to its air wing.

    Returns one announcement line per arrival (both coalitions' arrivals are
    promoted; only the player-coalition lines are returned, since the enemy's
    order of battle is not the player's to read -- see the note's guardrail on
    red schedules).

    Safe to call repeatedly within a turn: a promoted squadron leaves the
    pending list, so a second call in the same turn returns nothing.
    """
    lines: List[str] = []
    for coalition in (game.blue, game.red):
        air_wing = coalition.air_wing
        pending = getattr(air_wing, "pending_arrivals", None)
        if not pending:
            continue

        still_pending: List[PendingSquadron] = []
        for arrival in pending:
            if arrival.turn > game.turn:
                still_pending.append(arrival)
                continue
            if not _join_wing(game, arrival):
                # Something went wrong joining this one; drop it rather than
                # retrying forever. _join_wing has already logged why.
                continue
            if coalition.player.is_blue:
                lines.append(arrival.arrival_line)
        air_wing.pending_arrivals = still_pending

    return lines


def upcoming_arrivals(game: "Game", coalition_is_blue: bool = True) -> List[str]:
    """The still-to-come schedule, for surfacing *ahead* of the arrival turn.

    This is the motivational half: the jet you cannot fly yet is the advert.
    Sorted by turn, then by squadron name so the order is stable.
    """
    coalition = game.blue if coalition_is_blue else game.red
    pending = getattr(coalition.air_wing, "pending_arrivals", None) or []
    ordered = sorted(pending, key=lambda a: (a.turn, str(a.squadron.name)))
    return [
        f"{a.squadron.name} ({a.squadron.aircraft}) — arrives turn {a.turn}"
        for a in ordered
    ]


def _join_wing(game: "Game", arrival: PendingSquadron) -> bool:
    """Add the squadron to its wing and populate it. True when it joined."""
    squadron = arrival.squadron
    air_wing = squadron.coalition.air_wing
    try:
        air_wing.add_squadron(squadron)
        # populate_for_turn_0 is already generic despite its name: it recruits
        # pilots to the limit and, when the campaign starts squadrons full,
        # fills aircraft up to the base's unclaimed parking. Reuse the flag the
        # wing was originally populated with so an arrival matches the rest of
        # the wing instead of inventing its own rule.
        squadron.populate_for_turn_0(_started_full(air_wing))
    except Exception:
        logging.exception(
            "Wing growth: failed to bring %s online at turn %d", squadron, arrival.turn
        )
        return False
    logging.info(
        "Wing growth: %s (%s) joined %s at turn %d",
        squadron.name,
        squadron.aircraft,
        squadron.location,
        arrival.turn,
    )
    return True


def _started_full(air_wing: object) -> bool:
    """Whether this wing's squadrons were populated full at turn 0.

    Recorded by ``AirWing.populate_for_turn_0``; ``getattr`` so a pre-feature
    pickled save (which never recorded it) degrades to the stock default rather
    than raising.
    """
    return bool(getattr(air_wing, "squadrons_started_full", False))
