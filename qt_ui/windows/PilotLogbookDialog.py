"""The pilot logbook (§96) — one pilot's career, as a page.

Reads only what `PilotRecord` already carries plus the rank/award data in
`resources/pilot_career.yaml`; it computes nothing and mutates nothing. Careers
are folded in once per turn when mission results are committed, so a logbook
opened mid-planning shows the same numbers as one opened after the debrief.

A record, not a reward. Nothing on this page changes what the pilot may fly.
"""

from __future__ import annotations

import html
from typing import Optional

from PySide6.QtWidgets import QDialog, QLabel, QTextBrowser, QVBoxLayout

from game.fourteenth.career import awards_held, career_lines, rank_for
from game.squadrons.pilot import Pilot, PilotStatus
from game.squadrons.squadron import Squadron


class PilotLogbookDialog(QDialog):
    def __init__(self, pilot: Pilot, squadron: Squadron, parent=None) -> None:
        super().__init__(parent)

        self.pilot = pilot
        self.squadron = squadron

        self.setWindowTitle(f"Logbook — {pilot.name}")
        self.setMinimumSize(420, 380)
        self.resize(520, 560)

        layout = QVBoxLayout()
        self.setLayout(layout)

        heading = QLabel(_heading(pilot, squadron))
        heading.setWordWrap(True)
        layout.addWidget(heading)

        body = QTextBrowser(self)
        body.setHtml(_render(pilot, squadron))
        layout.addWidget(body)


def _country_name(squadron: Squadron) -> Optional[str]:
    return getattr(getattr(squadron, "country", None), "name", None)


def _heading(pilot: Pilot, squadron: Squadron) -> str:
    rank = rank_for(pilot.record, _country_name(squadron))
    name = f"{rank} {pilot.name}" if rank else pilot.name
    return f"{name}\n{squadron.name} — {squadron.aircraft.display_name}"


def _render(pilot: Pilot, squadron: Squadron) -> str:
    record = pilot.record
    # Inline styles rather than the QSS token sheet: QTextBrowser renders with
    # its own limited CSS engine, which the app stylesheet does not reach.
    rows = [
        ("Status", _status_text(pilot)),
        ("Skill", squadron.pilot_skill(pilot).value),
        ("Crewed by", "Player" if pilot.player else "AI"),
    ] + career_lines(record)

    parts = ["<table cellspacing='0' cellpadding='4'>"]
    for label, value in rows:
        parts.append(
            f"<tr><td><b>{html.escape(label)}</b></td>"
            f"<td>{html.escape(value)}</td></tr>"
        )
    parts.append("</table>")

    awards = awards_held(record)
    parts.append("<p><b>Awards</b></p>")
    if awards:
        parts.append("<ul>")
        for award in awards:
            entry = f"<li>{html.escape(award.name)}"
            if award.description:
                entry += f" — {html.escape(award.description)}"
            parts.append(entry + "</li>")
        parts.append("</ul>")
    else:
        parts.append("<p>None yet.</p>")

    if not record.sorties:
        # The empty case is the common one on turn 1 and after loading a save
        # made before the logbook existed, and a page of zeroes with no
        # explanation reads as a broken feature.
        parts.append(
            "<p>No sorties recorded yet. A career starts accumulating the first "
            "time this pilot flies a mission that is generated and flown; a "
            "campaign carried over from an older build starts from zero.</p>"
        )
    return "".join(parts)


def _status_text(pilot: Pilot) -> str:
    if pilot.status is PilotStatus.Recovering and pilot.turns_until_available:
        turns = pilot.turns_until_available
        return f"{pilot.status.value} ({turns} turn{'s' if turns != 1 else ''})"
    return pilot.status.value
