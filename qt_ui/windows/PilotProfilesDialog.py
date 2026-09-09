"""The lifetime Pilot Logbook window (§97).

Opens from the toolbar with no campaign loaded, because that is the whole point
of the feature: the record outlives every save. It is a pure read over
``pilot_profiles.json`` plus one write -- renaming a profile's display name.

Numbers only. Ranks and awards are §96's, and belong to a campaign.
"""

from __future__ import annotations

import html
from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

import qt_ui.uiconstants as CONST
from game.fourteenth.pilot_profile import (
    PilotProfile,
    load_profiles,
    profile_lines,
    rename_profile,
    reset_cache,
)

#: Flights listed on the page. The store keeps far more; a window nobody
#: scrolls past the first screen of does not need to render two thousand rows.
SHOWN_SORTIES = 60


class PilotProfilesDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Pilot Logbook")
        self.setWindowIcon(CONST.ICONS["Hangar"])
        self.setMinimumSize(640, 420)
        self.resize(940, 680)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.header = QLabel()
        self.header.setWordWrap(True)
        layout.addWidget(self.header)

        columns = QHBoxLayout()
        layout.addLayout(columns)

        self.pilot_list = QListWidget()
        self.pilot_list.setMaximumWidth(240)
        self.pilot_list.currentRowChanged.connect(self.on_pilot_changed)
        columns.addWidget(self.pilot_list)

        self.body = QTextBrowser(self)
        columns.addWidget(self.body, stretch=1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.rename_button = QPushButton("Rename")
        self.rename_button.setProperty("style", "start-button")
        self.rename_button.clicked.connect(self.rename_selected)
        buttons.addWidget(self.rename_button)
        layout.addLayout(buttons)

        self.profiles: list[PilotProfile] = []
        self.reload()

    def reload(self, select: Optional[str] = None) -> None:
        # Off disk each time the window opens: a turn processed since the last
        # open has written to the file, and the cache would show yesterday.
        reset_cache()
        self.profiles = sorted(
            load_profiles().values(), key=lambda p: p.minutes, reverse=True
        )
        self.pilot_list.clear()
        for profile in self.profiles:
            self.pilot_list.addItem(QListWidgetItem(profile.name))
        if self.profiles:
            self.header.setText(
                f"{len(self.profiles)} pilot"
                f"{'s' if len(self.profiles) != 1 else ''} on record, across every "
                "campaign. Identified by DCS player name."
            )
            row = 0
            if select is not None:
                for index, profile in enumerate(self.profiles):
                    if profile.key == select:
                        row = index
                        break
            self.pilot_list.setCurrentRow(row)
        else:
            self.header.setText(
                "No flying on record yet. A profile appears the first time you "
                "fly a generated mission and accept the results."
            )
            self.body.setHtml(_empty_page())
        self.rename_button.setEnabled(bool(self.profiles))

    def selected(self) -> Optional[PilotProfile]:
        row = self.pilot_list.currentRow()
        if row < 0 or row >= len(self.profiles):
            return None
        return self.profiles[row]

    def on_pilot_changed(self, _row: int) -> None:
        profile = self.selected()
        if profile is not None:
            self.body.setHtml(_render(profile))

    def rename_selected(self) -> None:
        profile = self.selected()
        if profile is None:
            return
        text, ok = QInputDialog.getText(
            self,
            "Rename pilot",
            f"Display name for {profile.key}:",
            QLineEdit.EchoMode.Normal,
            profile.name,
        )
        if ok:
            # The key is the DCS player name and never moves -- renaming it
            # would orphan the profile from the seat that feeds it.
            rename_profile(profile.key, text)
            self.reload(select=profile.key)


def _empty_page() -> str:
    return (
        "<p>Nothing recorded yet.</p>"
        "<p>Your profile is created the first time a mission you flew is "
        "processed. It is keyed to your DCS player name, so nothing needs "
        "setting up first.</p>"
        "<p>Only slots a human actually occupied are recorded, and only "
        "aircraft that actually flew — a jet left on the ramp logs nothing.</p>"
    )


def _table(rows: list[tuple[str, str]]) -> str:
    parts = ["<table cellspacing='0' cellpadding='4'>"]
    for label, value in rows:
        parts.append(
            f"<tr><td><b>{html.escape(label)}</b></td>"
            f"<td>{html.escape(value)}</td></tr>"
        )
    parts.append("</table>")
    return "".join(parts)


def _render(profile: PilotProfile) -> str:
    # Inline styles rather than the QSS token sheet: QTextBrowser renders with
    # its own limited CSS engine, which the app stylesheet does not reach.
    parts = [f"<h3>{html.escape(profile.name)}</h3>"]
    if profile.display_name and profile.display_name != profile.key:
        parts.append(f"<p><i>DCS player name: {html.escape(profile.key)}</i></p>")
    parts.append(_table(profile_lines(profile)))

    if profile.by_airframe:
        parts.append("<p><b>By aircraft</b></p>")
        parts.append(
            "<table cellspacing='0' cellpadding='4'>"
            "<tr><td><b>Aircraft</b></td><td><b>Sorties</b></td>"
            "<td><b>Hours</b></td><td><b>Kills</b></td></tr>"
        )
        ordered = sorted(
            profile.by_airframe.items(), key=lambda kv: kv[1].minutes, reverse=True
        )
        for name, totals in ordered:
            parts.append(
                f"<tr><td>{html.escape(name)}</td>"
                f"<td>{totals.sorties}</td>"
                f"<td>{totals.hours:.1f}</td>"
                f"<td>{totals.kills}</td></tr>"
            )
        parts.append("</table>")

    if profile.campaigns:
        parts.append(
            "<p><b>Campaigns flown</b><br/>"
            + html.escape(", ".join(profile.campaigns))
            + "</p>"
        )

    parts.append("<p><b>Flights</b></p>")
    if profile.log:
        parts.append(
            "<table cellspacing='0' cellpadding='4'>"
            "<tr><td><b>Date</b></td><td><b>Campaign</b></td><td><b>Aircraft</b></td>"
            "<td><b>Task</b></td><td><b>Time</b></td><td><b>Kills</b></td></tr>"
        )
        for entry in profile.log[:SHOWN_SORTIES]:
            kills = entry.air_kills + entry.ground_kills + entry.naval_kills
            marks = str(kills) if kills else ""
            if entry.ejected:
                marks = (marks + " ejected").strip()
            parts.append(
                f"<tr><td>{html.escape(entry.date)}</td>"
                f"<td>{html.escape(entry.campaign)}</td>"
                f"<td>{html.escape(entry.aircraft)}</td>"
                f"<td>{html.escape(entry.task)}</td>"
                f"<td>{entry.minutes:.0f} min</td>"
                f"<td>{html.escape(marks)}</td></tr>"
            )
        parts.append("</table>")
        if len(profile.log) > SHOWN_SORTIES:
            parts.append(
                f"<p><i>{len(profile.log) - SHOWN_SORTIES} older flights are in "
                "the store but not listed here.</i></p>"
            )
    else:
        parts.append("<p>None recorded.</p>")
    return "".join(parts)
