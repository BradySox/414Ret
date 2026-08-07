"""Where the New Game wizard opens.

Qt leaves placement to the window manager unless a window says otherwise, which
parked the wizard off in a corner. These tests drive the real widget under the
offscreen platform.

The wizard is built with ``__new__`` plus a bare ``QWizard.__init__`` on purpose:
its real ``__init__`` loads every campaign off disk and needs the DCS install
paths configured, none of which the placement code touches.
"""

from __future__ import annotations

import os
from typing import Any, Iterator

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qt_app() -> Iterator[object]:
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _wizard(size: tuple[int, int] = (900, 700)) -> Any:
    from PySide6.QtWidgets import QWizard

    from qt_ui.windows.newgame.QNewGameWizard import NewGameWizard

    wizard = NewGameWizard.__new__(NewGameWizard)
    QWizard.__init__(wizard)
    wizard._centered = False
    wizard.resize(*size)
    return wizard


def test_the_wizard_opens_centered(qt_app: object) -> None:
    wizard = _wizard()
    wizard.show()

    available = wizard.screen().availableGeometry()
    frame = wizard.frameGeometry()
    # A couple of pixels of slack: the frame is measured before the window
    # manager has necessarily reported its decorations.
    assert abs(frame.center().x() - available.center().x()) <= 4
    assert abs(frame.center().y() - available.center().y()) <= 4


def test_a_tall_wizard_still_lands_fully_on_screen(qt_app: object) -> None:
    """Centering is against availableGeometry, so the taskbar never eats an edge."""
    from PySide6.QtGui import QGuiApplication

    available = QGuiApplication.primaryScreen().availableGeometry()
    # Nearly the full working area -- the case where centering against the raw
    # screen instead would push the bottom of the window off it.
    wizard = _wizard((available.width() - 40, available.height() - 40))
    wizard.show()

    assert available.contains(wizard.frameGeometry())


def test_reopening_does_not_yank_a_moved_window(qt_app: object) -> None:
    """Centering is first-show only, so a window the user dragged stays put."""
    wizard = _wizard()
    wizard.show()
    wizard.hide()

    wizard.move(7, 9)
    moved = wizard.geometry().topLeft()
    wizard.show()

    assert wizard.geometry().topLeft() == moved
