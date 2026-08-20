"""The What's New window (§92) renders the feed and survives an empty one.

Drives the real dialog offscreen. It takes no ``Game`` on purpose -- the toolbar
action is live before a save is opened -- so the only thing that can break it is
the data, which is what these cover: every entry reaches the document, a title
carrying markup is escaped rather than injected, and an empty feed produces a
window instead of a traceback.

``load_icons`` is called for real, so a typo'd icon path fails here rather than
raising KeyError out of the toolbar at runtime.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from typing import Iterator

import pytest
from PySide6.QtWidgets import QApplication

import qt_ui.uiconstants as CONST
from game.fourteenth.whatsnew import WhatsNewEntry
from qt_ui.liberation_theme import DEFAULT_THEME_INDEX, set_theme_index


@pytest.fixture(scope="module", autouse=True)
def _qt_app() -> Iterator[QApplication]:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    # set_theme_index rather than liberation_theme.init(): init() also writes the
    # user's theme preferences file, which a test has no business touching.
    set_theme_index(DEFAULT_THEME_INDEX)
    CONST.load_icons()
    yield app


def _window(entries: list[WhatsNewEntry]) -> object:
    """Build the dialog. Keep the returned reference alive while reading its
    document -- PySide6 deletes the C++ children as soon as the Python dialog is
    collected, which is the same reason the app holds self.whats_new_dialog."""
    from qt_ui.windows.whatsnew.QWhatsNewWindow import QWhatsNewWindow

    return QWhatsNewWindow(entries)


def _entry(**overrides: str) -> WhatsNewEntry:
    fields = {
        "date": "2026-08-19",
        "title": "A thing changed",
        "change": "It changed like this.",
        "watch": "Look for it doing the new thing.",
    }
    fields.update(overrides)
    return WhatsNewEntry(**fields)


def test_the_icon_key_the_toolbar_asks_for_exists() -> None:
    assert "What's New" in CONST.ICONS


def test_every_entry_reaches_the_document() -> None:
    entries = [
        _entry(title="First change", watch="Watch the first"),
        _entry(date="2026-08-18", title="Second change", watch="Watch the second"),
    ]
    window = _window(entries)
    text = window.body.toPlainText()  # type: ignore[attr-defined]
    for entry in entries:
        assert entry.title in text
        assert entry.change in text
        assert entry.watch in text
    assert "Watch for:" in text


def test_the_row_and_pr_are_surfaced() -> None:
    window = _window([_entry(row="B39", pr="906")])
    plain = window.body.toPlainText()  # type: ignore[attr-defined]
    html = window.body.toHtml()  # type: ignore[attr-defined]
    assert "pass row B39" in plain
    assert "#906" in plain
    assert "/pull/906" in html


def test_an_entry_without_a_row_or_pr_renders_cleanly() -> None:
    window = _window([_entry()])
    plain = window.body.toPlainText()  # type: ignore[attr-defined]
    assert "pass row" not in plain
    assert "·" not in plain


def test_markup_in_the_data_is_escaped_not_injected() -> None:
    window = _window([_entry(title="<b>not bold</b>")])
    assert "<b>not bold</b>" in window.body.toPlainText()  # type: ignore[attr-defined]


def test_an_empty_feed_is_a_window_not_a_crash() -> None:
    window = _window([])
    text = window.body.toPlainText()  # type: ignore[attr-defined]
    assert "nothing to show" in text
