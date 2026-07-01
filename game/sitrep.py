from __future__ import annotations

from dataclasses import dataclass
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
    #: Vietnam campaign layer (W1): post-turn Political Will / Regime Resolve
    #: percentages, set only when vietnam_political_will is on. None (and absent on
    #: pre-W1 pickled sitreps -- read via getattr) hides the band line entirely.
    blue_will: Optional[float] = None
    red_will: Optional[float] = None

    @property
    def is_empty(self) -> bool:
        # Deliberately ignores the will fields: a quiet turn stays quiet even when
        # will tracking is on (the will line rides along with real news, it isn't
        # news by itself).
        return not (
            self.friendly.any
            or self.enemy.any
            or self.captured
            or self.lost
            or self.pilots_recovered
        )

    @classmethod
    def from_debriefing(
        cls,
        debriefing: Debriefing,
        turn: int,
        day: date,
        blue_will: Optional[float] = None,
        red_will: Optional[float] = None,
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
            blue_will=blue_will,
            red_will=red_will,
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
        # getattr: pre-W1 pickled sitreps lack the will fields entirely.
        blue_will = getattr(self, "blue_will", None)
        red_will = getattr(self, "red_will", None)
        if blue_will is not None and red_will is not None:
            lines.append(
                f"Political will {blue_will:.0f}% -- enemy resolve {red_will:.0f}% "
                "(est)"
            )
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
