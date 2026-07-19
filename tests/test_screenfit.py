"""Dialogs are clamped to the screen they open on (``qt_ui.screenfit``).

Qt sizes a dialog to its content with no upper bound, so a tall one opened with
its title bar above the top of the display -- the flown symptom was the Edit
Flight dialog (~1115 logical px of tab content) on a 1440p panel at 150%
scaling, which leaves ~928 usable px.

The geometry is a pure function so the interesting cases need no display; the Qt
half drives a real oversized ``QDialog`` offscreen to prove the clamp survives a
hard minimum size (several dialogs declare minimums larger than a small screen).
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from typing import Any, Iterator

import pytest
from PySide6.QtCore import QRect

from qt_ui.screenfit import DEFAULT_MARGIN, fit_to_available_screen, fitted_geometry

# A 1440p panel at 150% scaling, minus the taskbar: the display the bug was
# reported on, in the logical pixels Qt lays out in.
SCALED_1440P = QRect(0, 0, 1706, 928)


# --- pure geometry -------------------------------------------------------------------


def test_oversized_window_is_shrunk_to_fit() -> None:
    # The Edit Flight dialog's pre-fix height.
    fitted = fitted_geometry(QRect(0, -100, 1000, 1115), SCALED_1440P, margin=24)
    assert fitted.height() == 928 - 48
    assert SCALED_1440P.contains(fitted)


def test_window_above_the_screen_top_is_pulled_down() -> None:
    # The reported symptom: the title bar sat off the top of the display.
    fitted = fitted_geometry(QRect(300, -187, 1000, 900), SCALED_1440P, margin=24)
    assert fitted.top() >= SCALED_1440P.top()
    assert SCALED_1440P.contains(fitted)


def test_window_that_already_fits_is_untouched() -> None:
    original = QRect(100, 100, 800, 600)
    assert fitted_geometry(original, SCALED_1440P, margin=24) == original


def test_window_overhanging_the_bottom_is_moved_up_not_shrunk() -> None:
    # Tall-but-fitting content should keep its size; only its position moves.
    fitted = fitted_geometry(QRect(0, 700, 800, 600), SCALED_1440P, margin=24)
    assert fitted.height() == 600
    assert SCALED_1440P.contains(fitted)


def test_second_monitor_offsets_are_respected() -> None:
    # A left-hand monitor lives at negative x; the fit must land on *that*
    # screen, not snap back to the primary at the origin.
    left_monitor = QRect(-2560, 3, 1706, 928)
    fitted = fitted_geometry(QRect(-2000, -400, 1000, 1200), left_monitor, margin=24)
    assert left_monitor.contains(fitted)
    assert fitted.left() < 0


def test_margin_is_dropped_rather_than_inverting_on_a_tiny_screen() -> None:
    tiny = QRect(0, 0, 40, 30)
    fitted = fitted_geometry(QRect(0, 0, 900, 900), tiny, margin=DEFAULT_MARGIN)
    assert fitted.width() > 0 and fitted.height() > 0
    assert tiny.contains(fitted)


# --- Qt: the clamp fires on a real dialog --------------------------------------------


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def test_hard_minimum_size_is_relaxed_so_the_clamp_can_apply(qapp: Any) -> None:
    # A minimum size beats resize() in Qt, so a dialog declaring a minimum
    # bigger than the screen (AirWingConfigurationDialog asks for 1024x768,
    # which cannot fit 1080p at 150%) stays oversized unless the minimum is
    # relaxed first.
    from PySide6.QtWidgets import QDialog

    dialog = QDialog()
    dialog.setMinimumSize(1024, 768)
    dialog.resize(1024, 768)

    available = QRect(0, 0, 1280, 672)  # 1080p at 150%, minus the taskbar
    fit_to_available_screen(dialog, margin=24, available=available)

    # Without the relaxation the dialog would still report its 768 minimum and
    # the resize below it would be silently ignored.
    assert dialog.minimumHeight() <= available.height()
    assert dialog.height() <= available.height()


def test_dialog_that_already_fits_is_left_alone(qapp: Any) -> None:
    from PySide6.QtWidgets import QDialog

    dialog = QDialog()
    dialog.resize(600, 400)
    dialog.move(50, 50)
    before = dialog.geometry()

    fit_to_available_screen(dialog, margin=24, available=QRect(0, 0, 1706, 928))

    assert dialog.geometry() == before
