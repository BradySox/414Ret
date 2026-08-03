"""The pre-turn briefing -- reasons to continue, shown *before* the commitment.

Single-player campaigns die at a reproducible place: the player accepts the
mission results and never plays turn 2. One reason is that **the fork already
computes almost every reason to keep flying and points them the wrong way in
time.** ``Sitrep`` (§29) carries named aviators on capture clocks, proof that
bombing the enemy HQ degraded its planning, and live victory progress -- and
renders all of it on the *next* mission's kneeboard, i.e. only after the player
has already committed to the turn it was supposed to motivate.

This module is the read-out pointed the right way. It answers **"why fly
tonight"** from state ``finish_turn`` has already produced, and it is
deliberately a *pure view*: it computes nothing the campaign does not already
know, mutates nothing, and has zero planner coupling (the §3 viewer discipline
-- everything here is BLUE's own picture, and the AI never reads it).

Two things it adds that no existing surface does:

* **The capture clock as a number.** ``downed_pilots.capture_chance`` already
  scales an evader's per-turn capture odds from 10% near the front to 90% deep
  behind it -- the whole "don't fly deep" incentive -- and nothing ever showed
  the player that number. "Every turn you skip is a roll" only lands when the
  roll is stated.
* **Anticipation.** §82's scheduled arrivals are pulled forward as "what is
  coming", because the jet you cannot fly yet is the advert.

Ordering is by urgency, and urgency is deliberate: a named person on a clock
outranks a statistic. See ``docs/dev/design/414th-single-player-loop-notes.md``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from game.game import Game

#: Urgency bands. Higher sorts first, and the UI may highlight anything at or
#: above ``URGENT``. These are presentation weights, not game state.
URGENT = 30
NOTABLE = 20
BACKGROUND = 10

#: Cap per section so a long war cannot produce an unreadable wall.
MAX_PER_SECTION = 4


@dataclass(frozen=True)
class BriefingItem:
    """One reason to fly this turn."""

    #: Stable slug for the UI to group/style on: "rescue", "consequence",
    #: "objective", "arrival", "open_loop".
    kind: str
    text: str
    urgency: int = BACKGROUND


@dataclass(frozen=True)
class PreTurnBriefing:
    """Everything worth knowing *before* committing to the turn."""

    turn: int
    items: List[BriefingItem] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.items

    def by_kind(self, kind: str) -> List[BriefingItem]:
        return [item for item in self.items if item.kind == kind]

    def ordered(self) -> List[BriefingItem]:
        """Most pressing first; stable within a band so the card does not
        reshuffle between renders."""
        return sorted(self.items, key=lambda i: -i.urgency)

    def headline(self) -> Optional[str]:
        """The single most pressing reason, for a one-line summary."""
        ordered = self.ordered()
        return ordered[0].text if ordered else None


def build_pre_turn_briefing(game: "Game") -> PreTurnBriefing:
    """Gather the reasons to fly this turn. Never raises: a section that cannot
    be computed is simply absent, because a briefing is not worth breaking a
    turn over."""
    items: List[BriefingItem] = []
    for section in (
        _rescue_items,
        _consequence_items,
        _objective_items,
        _arrival_items,
        _open_loop_items,
    ):
        try:
            items.extend(section(game)[:MAX_PER_SECTION])
        except Exception:
            logging.exception("Pre-turn briefing section failed: %s", section.__name__)
    return PreTurnBriefing(turn=game.turn, items=items)


# --------------------------------------------------------------- 1. the rescue


def _rescue_items(game: "Game") -> List[BriefingItem]:
    """A named person on a clock you caused -- the strongest hook the fork owns.

    The SITREP already lists evaders and POWs. What it never showed is the
    *odds*: the capture roll is re-run every turn the player does not go, and it
    climbs with how deep the pilot went down.
    """
    from game.fourteenth.downed_pilots import (
        _depth_nm,
        _ledger,
        _nearest_control_point,
        _pilot_label,
        capture_chance,
    )

    items: List[BriefingItem] = []
    for downed in _ledger(game):
        position = game.point_in_world(downed.x, downed.y)
        depth = _depth_nm(game, position)
        chance = capture_chance(depth)
        nearest = _nearest_control_point(game, position)
        where = f" near {nearest.name}" if nearest is not None else ""
        turns = max(game.turn - downed.turn_downed, 0)
        down_for = f"{turns} turn{'s' if turns != 1 else ''} down" if turns else "down"
        items.append(
            BriefingItem(
                kind="rescue",
                text=(
                    f"{_pilot_label(downed)} is evading{where} — {depth:.0f} NM "
                    f"deep, {down_for}. {chance * 100:.0f}% chance he is taken "
                    f"this turn if nobody comes."
                ),
                urgency=URGENT,
            )
        )

    for pow_line in _pow_lines(game):
        items.append(BriefingItem(kind="rescue", text=pow_line, urgency=NOTABLE))
    return items


def _pow_lines(game: "Game") -> List[str]:
    """Held aviators, phrased as the standing debt they are."""
    sitrep = getattr(game, "last_sitrep", None)
    held = list(getattr(sitrep, "pows_held", None) or []) if sitrep else []
    return [f"POW: {line} — retake the field and he comes home." for line in held]


# ---------------------------------------------------------- 2. the consequence


def _consequence_items(game: "Game") -> List[BriefingItem]:
    """Proof that the player's own sorties changed how the enemy fights.

    The honest single-player complaint is "I flew 1 of 25 packages and the war
    moved for reasons I didn't cause". §52 measurably disproves it whenever the
    player has been killing command posts -- and already says so, one turn late.
    """
    from game.fourteenth.c2_decapitation import c2_status_line

    line = c2_status_line(game, game.blue.player)
    if not line:
        return []
    return [
        BriefingItem(
            kind="consequence",
            text=(
                f"Enemy C2 degraded (claimed): {line}. Their planning is worse "
                f"because of you — keep it that way."
            ),
            urgency=NOTABLE,
        )
    ]


# ------------------------------------------------------------ 3. the objective


def _objective_items(game: "Game") -> List[BriefingItem]:
    """A visible finish line. §75 renders this only after the commitment."""
    from game.fourteenth.victory import victory_sitrep_lines

    return [
        BriefingItem(kind="objective", text=line, urgency=NOTABLE)
        for line in victory_sitrep_lines(game, limit=MAX_PER_SECTION)
    ]


# ------------------------------------------------------------- 4. anticipation


def _arrival_items(game: "Game") -> List[BriefingItem]:
    """§82 scheduled arrivals, pulled *forward*.

    The jet you cannot fly yet is the advert -- but only while it is still
    coming, so an arrival that has already landed says nothing here.
    """
    from game.fourteenth.wing_growth import upcoming_arrivals

    return [
        BriefingItem(kind="arrival", text=line, urgency=BACKGROUND)
        for line in upcoming_arrivals(game)
    ]


# --------------------------------------------------------------- 5. open loops


def _open_loop_items(game: "Game") -> List[BriefingItem]:
    """Unfinished business the player personally opened.

    Two cheap, honest counts off the recon-fog model: contacts that have been
    *detected but never identified* (the §3/§79 dashed circles -- each one is
    either a real hidden force or a decoy, and only a sortie tells you which),
    and surviving mobile theatre-missile sites (§49 shoot-and-scoot, so finding
    one is not killing it).
    """
    viewer = game.blue.player
    unidentified = 0
    mobile_missiles = 0
    for tgo in game.theater.ground_objects:
        if tgo.control_point.captured == viewer:
            continue
        if tgo.is_dead(viewer):
            continue
        if getattr(tgo, "map_hidden", False):
            continue
        if getattr(tgo, "concealed", False) and not tgo.known_for(viewer):
            unidentified += 1
        if tgo.category == "missile" and tgo.known_for(viewer):
            mobile_missiles += 1

    items: List[BriefingItem] = []
    if unidentified:
        plural = "s" if unidentified != 1 else ""
        items.append(
            BriefingItem(
                kind="open_loop",
                text=(
                    f"{unidentified} suspected contact{plural} still "
                    f"unidentified — recon is the only way to know which are real."
                ),
                urgency=BACKGROUND,
            )
        )
    if mobile_missiles:
        plural = "s" if mobile_missiles != 1 else ""
        items.append(
            BriefingItem(
                kind="open_loop",
                text=(
                    f"{mobile_missiles} located missile site{plural} still "
                    f"alive — they scoot between missions."
                ),
                urgency=BACKGROUND,
            )
        )
    return items
