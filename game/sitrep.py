from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, TYPE_CHECKING, cast

from game.theater.player import Player

if TYPE_CHECKING:
    from game.debriefing import BaseCaptureEvent, Debriefing


@dataclass(frozen=True)
class SideLosses:
    """One side's attrition over a single turn."""

    aircraft: int
    front_line: int
    sites: int

    @property
    def any(self) -> bool:
        return bool(self.aircraft or self.front_line or self.sites)


def _loss_phrase(side: SideLosses) -> str:
    parts: List[str] = []
    if side.aircraft:
        parts.append(f"{side.aircraft} air")
    if side.front_line:
        parts.append(f"{side.front_line} armor")
    if side.sites:
        parts.append(f"{side.sites} site" + ("s" if side.sites != 1 else ""))
    return ", ".join(parts) if parts else "none"


@dataclass(frozen=True)
class Sitrep:
    """A one-turn campaign summary (§29).

    Captured at mission-results commit from the debriefing that is already
    tallied there, stored on the game, and surfaced on the next turn's kneeboard
    cover band. Enemy losses are reported as *claimed* (battle-damage style),
    consistent with the recon-fog model — the campaign already committed the real
    numbers; this is the player-facing read-off.
    """

    turn: int
    day: date
    friendly: SideLosses
    enemy: SideLosses
    captured: List[str]  # control points the player took this turn
    lost: List[str]  # control points the player lost this turn
    pilots_recovered: int  # Combat SAR deliveries home
    #: One line per BLUE aviator held POW, e.g. "Capt Mitchell — held at Mozdok
    #: (2 turns left)" or "… (held)" on an indefinite-hold will campaign. The one
    #: player-facing surface for the "recapture the field / rescue matters" levers.
    #: Absent on pre-POW-visibility pickled sitreps (read via getattr).
    pows_held: List[str] = field(default_factory=list)
    #: One line per BLUE aviator down and still EVADING (the §21 persistent-evader
    #: ledger, 2026-07-10), e.g. "Capt Mitchell — evading near Fulda (2 turns
    #: down)". Deep evaders get found by the turn capture roll -- this line is the
    #: standing prompt to fly the rescue. Absent on pre-feature pickled sitreps
    #: (read via getattr).
    pilots_mia: List[str] = field(default_factory=list)
    #: §52 Feature A: the enemy command-network status ("1/3 command posts
    #: operational") when it is degraded and the feature is on -- the legibility
    #: for "bombing the HQ made red plan worse". None hides the line. Rides along
    #: with real news (never forces a SITREP on a quiet turn). getattr-guarded.
    red_c2_status: Optional[str] = None
    #: §75 custom victory conditions: the live progress digest ("Victory: Enemy air
    #: force below 10% of start (now 62%)"), capped by the recorder. Empty when no
    #: alternate conditions are configured; rides along with real news like the
    #: will band. Absent on pre-feature pickled sitreps (read via getattr).
    victory_lines: List[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        # Deliberately ignores the C2/victory lines: a quiet turn stays quiet even
        # when they're present (they ride along with real news, not news by
        # themselves).
        return not (
            self.friendly.any
            or self.enemy.any
            or self.captured
            or self.lost
            or self.pilots_recovered
            or getattr(self, "pows_held", None)
            or getattr(self, "pilots_mia", None)
        )

    @property
    def has_news(self) -> bool:
        """Whether the app surfaces (web LAST TURN panel, Qt debrief box) show it.

        The same quiet-turn gate the kneeboard band uses (`sitrep_for_kneeboard`),
        so all §29 surfaces agree on what counts as news.
        """
        return not self.is_empty

    @classmethod
    def from_debriefing(
        cls,
        debriefing: Debriefing,
        turn: int,
        day: date,
        pows_held: Optional[List[str]] = None,
        pilots_mia: Optional[List[str]] = None,
        red_c2_status: Optional[str] = None,
        victory_lines: Optional[List[str]] = None,
    ) -> "Sitrep":
        blue = debriefing.loss_counts(Player.BLUE)
        red = debriefing.loss_counts(Player.RED)
        # Use the cached base_captures snapshot (computed when the Debriefing was
        # built, pre-commit) — NOT base_capture_events(), which would re-evaluate
        # ownership after commit_captures has already flipped bases and drop them.
        # getattr+cast sidesteps a mypy has-type quirk on the init-assigned attr.
        captures = cast("List[BaseCaptureEvent]", getattr(debriefing, "base_captures"))
        captured = [
            capture.control_point.name
            for capture in captures
            if capture.captured_by_player == Player.BLUE
        ]
        lost = [
            capture.control_point.name
            for capture in captures
            if capture.captured_by_player == Player.RED
        ]
        return cls(
            turn=turn,
            day=day,
            friendly=SideLosses(blue.aircraft, blue.front_line, blue.ground_objects),
            enemy=SideLosses(red.aircraft, red.front_line, red.ground_objects),
            captured=captured,
            lost=lost,
            pilots_recovered=len(debriefing.state_data.combat_sar_rescues),
            pows_held=list(pows_held or []),
            pilots_mia=list(pilots_mia or []),
            red_c2_status=red_c2_status,
            victory_lines=list(victory_lines or []),
        )

    def kneeboard_lines(self) -> List[str]:
        """The body lines of the kneeboard SITREP band (no header)."""
        lines = [
            f"Friendly losses: {_loss_phrase(self.friendly)}",
            f"Enemy (claimed): {_loss_phrase(self.enemy)}",
        ]
        if self.captured:
            lines.append(f"Captured: {', '.join(self.captured)}")
        if self.lost:
            lines.append(f"Lost: {', '.join(self.lost)}")
        if self.pilots_recovered:
            plural = "s" if self.pilots_recovered != 1 else ""
            lines.append(f"Recovered {self.pilots_recovered} downed pilot{plural}")
        # POWs held (getattr: pre-POW-visibility pickled sitreps lack the field).
        for pow_line in getattr(self, "pows_held", None) or []:
            lines.append(f"POW: {pow_line}")
        # Evaders still down (getattr: pre-feature pickled sitreps lack the field).
        for mia_line in getattr(self, "pilots_mia", None) or []:
            lines.append(f"MIA: {mia_line}")
        # §52: enemy command-network status when degraded (getattr for old saves).
        red_c2 = getattr(self, "red_c2_status", None)
        if red_c2:
            lines.append(f"Enemy C2 degraded (claimed): {red_c2}")
        # §75: the alternate-ending progress digest (getattr for pre-feature
        # pickled sitreps). Already prefixed ("Victory: …" / "Defeat if: …") and
        # capped by the recorder; rides along with real news.
        for victory_line in getattr(self, "victory_lines", None) or []:
            lines.append(victory_line)
        return lines


def sitrep_for_kneeboard(sitrep: Optional[Sitrep], enabled: bool) -> Optional[Sitrep]:
    """The SITREP to render on the kneeboard cover, or None when nothing to show.

    Returns None when the toggle is off, there is no prior turn, or the previous
    turn was quiet (no losses/captures/rescues) — so the cover never prints an
    empty SITREP section. The cover page renders the heading (with the turn) and
    the body itself; see ``Sitrep.kneeboard_lines``.
    """
    if not enabled or sitrep is None or sitrep.is_empty:
        return None
    return sitrep
