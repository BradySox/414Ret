"""The What's New window (§92) — recent changes, and what to look for.

Reads ``resources/whatsnew.yaml`` through :mod:`game.fourteenth.whatsnew`. It
takes no ``Game``, because it describes the build rather than the campaign — the
toolbar action is live before a save is opened, unlike Settings/Stats/Notes.
"""

from __future__ import annotations

import html
from typing import Optional, Sequence

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
)

import qt_ui.uiconstants as CONST
from game.fourteenth.whatsnew import WhatsNewEntry, load_whats_new
from game.version import VERSION
from qt_ui.uiconstants import URLS


class QWhatsNewWindow(QDialog):
    def __init__(self, entries: Optional[Sequence[WhatsNewEntry]] = None) -> None:
        super().__init__()

        self.entries = list(load_whats_new() if entries is None else entries)

        self.setWindowTitle("What's New")
        self.setWindowIcon(CONST.ICONS["What's New"])
        self.setMinimumSize(520, 300)
        self.resize(780, 640)

        layout = QVBoxLayout()
        self.setLayout(layout)

        header = QLabel(
            f"The {len(self.entries)} most recent changes in this build ({VERSION}), "
            "newest first."
            if self.entries
            else "No change list shipped with this build."
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        self.body = QTextBrowser(self)
        self.body.setOpenExternalLinks(True)
        self.body.setHtml(_render(self.entries))
        layout.addWidget(self.body)


def _render(entries: Sequence[WhatsNewEntry]) -> str:
    if not entries:
        return (
            "<p>resources/whatsnew.yaml is missing or unreadable, so there is "
            "nothing to show. The rest of the app is unaffected.</p>"
        )
    # A rule between entries, never around them: ten stacked blocks with only
    # margins between them read as one wall of text (the first render did).
    return "<hr/>".join(_render_entry(entry) for entry in entries)


def _render_entry(entry: WhatsNewEntry) -> str:
    # Inline styles rather than the QSS token sheet: QTextBrowser renders its
    # document with its own (limited) CSS engine, which the app stylesheet does
    # not reach into. Keep to what Qt's rich-text subset actually honours.
    parts = [
        '<div style="margin-top:10px; margin-bottom:12px;">',
        f'<p style="font-size:large; font-weight:bold; margin-bottom:2px;">'
        f"{html.escape(entry.title)}</p>",
        f'<p style="margin-top:0px;">{html.escape(entry.change)}</p>',
        "<p><b>Watch for:</b> " f"{html.escape(entry.watch)}</p>",
        f'<p style="font-size:small; color:gray;">'
        f"{html.escape(entry.date)}{_meta(entry)}</p>",
        "</div>",
    ]
    return "".join(parts)


def _meta(entry: WhatsNewEntry) -> str:
    """The date line's trailing detail: the checklist row and a PR link."""
    bits = []
    if entry.row:
        bits.append(f"pass row {html.escape(entry.row)}")
    if entry.pr:
        url = f"{URLS['Repository']}/pull/{html.escape(entry.pr)}"
        bits.append(f'<a href="{url}">#{html.escape(entry.pr)}</a>')
    if not bits:
        return ""
    return " &middot; " + " &middot; ".join(bits)
