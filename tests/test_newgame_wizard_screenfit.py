"""The New Game wizard stays on screen after it grows (qt_ui.windows.newgame).

``ScreenFitFilter`` fits a dialog once, on Show. The New Game wizard is at its
smallest then -- the intro page measures ~500x461 -- and nearly doubles in height
when the theater page loads, keeping the intro page's top-left. The symptom was
the wizard's Next/Cancel row sitting under the taskbar: measured 1409x963 of
frame from y=465 against 1392 px of usable height, 36 px over.

Building the real pages needs a DCS install and a Saved Games folder, so these
subclass ``NewGameWizard`` and skip its ``__init__``: the methods under test are
the real ones, only the pages are absent. Subclassing rather than lifting
``resizeEvent`` onto a bare ``QWizard`` is deliberate -- its zero-argument
``super()`` is bound to ``NewGameWizard`` and segfaults PySide6 on a ``self``
that is not one.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from typing import Any, Iterator

import pytest
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QWizard

from qt_ui.screenfit import fitted_geometry
from qt_ui.windows.newgame.QNewGameWizard import NewGameWizard

# The screen the bug was reported on, in the logical pixels Qt lays out in.
USABLE_1440P = QRect(0, 0, 2560, 1392)


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


class PagelessWizard(NewGameWizard):
    """The real wizard's behaviour without the pages its __init__ builds."""

    def __init__(self) -> None:
        QWizard.__init__(self)
        self._centered = True  # showEvent reads it; centring is not under test


def test_the_measured_overflow_is_a_move_not_a_shrink() -> None:
    # Centred at the intro page's size, then grown to the theater page's.
    grown = QRect(1030, 465, 1409, 963)
    assert not USABLE_1440P.contains(grown), "precondition: this is the bug"

    fitted = fitted_geometry(grown, USABLE_1440P)

    assert USABLE_1440P.contains(fitted)
    assert fitted.size() == grown.size(), "it fits once moved; do not shrink it"
    assert fitted.y() < grown.y()


def test_resize_event_refits_a_wizard_that_grew_after_show(qapp: Any) -> None:
    wizard = PagelessWizard()
    wizard.show()
    try:
        available = wizard.screen().availableGeometry()
        wizard.resize(available.width() // 2, available.height() + 400)
        qapp.processEvents()

        assert available.contains(wizard.frameGeometry())
    finally:
        wizard.close()


def test_refit_does_not_recurse(qapp: Any) -> None:
    # fit_to_available_screen resizes the window, which re-enters resizeEvent.
    calls = 0

    class CountingWizard(PagelessWizard):
        def resizeEvent(self, event: Any) -> None:
            nonlocal calls
            calls += 1
            assert calls < 50, "resize/fit feedback loop"
            super().resizeEvent(event)

    wizard = CountingWizard()
    wizard.show()
    try:
        available = wizard.screen().availableGeometry()
        wizard.resize(available.width() + 800, available.height() + 800)
        qapp.processEvents()

        assert available.contains(wizard.frameGeometry())
    finally:
        wizard.close()


def test_a_wizard_that_fits_is_left_where_the_user_put_it(qapp: Any) -> None:
    wizard = PagelessWizard()
    wizard.show()
    try:
        wizard.move(120, 120)
        qapp.processEvents()
        wizard.resize(400, 300)
        qapp.processEvents()

        assert wizard.pos().toTuple() == (120, 120)
    finally:
        wizard.close()
