from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Sequence, TYPE_CHECKING, cast

from game.sortierecord import SortieRecord, sorties_flown
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
    #: One line per BLUE aviator down and awaiting rescue (upstream #929's CSAR
    #: e.g. "Capt Mitchell — down near Fulda (2 turns left)". A survivor nobody
    #: reaches in time goes MIA for good, so this line is the standing prompt to
    #: fly the rescue. Absent on pre-feature pickled sitreps (read via getattr).
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
    #: Seam 1: what the day's flying actually amounted to, from the sortie
    #: records ("14 sorties, 22.5 hours airborne, 31 shots for 12 hits"). The
    #: first thing the campaign has ever been able to say about a mission that
    #: is not a casualty count. Empty when the recorder produced nothing.
    #: Rides along with real news. Absent on pre-feature pickled sitreps.
    sortie_line: Optional[str] = None

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
            # TODO(reconcile): re-point at PR929's rescued_pilot_ids channel.
            pilots_recovered=0,
            pilots_mia=list(pilots_mia or []),
            red_c2_status=red_c2_status,
            victory_lines=list(victory_lines or []),
            sortie_line=sortie_summary(
                getattr(debriefing.state_data, "sortie_records", ())
            ),
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
        # Seam 1: what the flying amounted to (getattr for old pickled sitreps).
        sortie_line = getattr(self, "sortie_line", None)
        if sortie_line:
            lines.append(sortie_line)
        return lines


def sortie_summary(records: Sequence[SortieRecord]) -> Optional[str]:
    """One line describing the day's flying, or None when there is nothing to say.

    Deliberately aggregate. A per-flight read-off belongs on a page of its own;
    this is the band that rides along with the loss counts.
    """
    airborne = [record for record in records if record.track]
    if not airborne:
        return None
    # Hours come only from records that were position-sampled, matching the
    # sortie count. Weapons come from every record: an AI wingman fires without
    # ever being sampled, and its shots are still the flight's.
    hours = sum(record.duration for record in airborne) / 3600.0
    shots = sum(record.shots for record in records)
    hits = sum(record.hits for record in records)
    sorties = "s" if len(airborne) != 1 else ""
    line = f"{len(airborne)} sortie{sorties}, {hours:.1f} hours airborne"
    if shots:
        fired = "s" if shots != 1 else ""
        struck = "s" if hits != 1 else ""
        line += f", {shots} shot{fired} for {hits} hit{struck}"
    return line


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
