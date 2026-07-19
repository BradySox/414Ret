"""Keep windows inside the screen they open on.

Qt sizes a dialog to its layout's ``sizeHint`` with no upper bound, so a dialog
whose content is taller than the display opens with its title bar above the top
of the screen and its lower controls below the bottom. Nothing in the app was
screen-aware except the main window and the settings dialog, which had grown its
own ad-hoc clamp; the other ~30 dialogs could open at any size their content
asked for. The Edit Flight dialog asks for ~1115 logical px (its tab widget
sizes to the tallest *hidden* tab), which does not fit a 1440p panel at 150%
scaling.

``ScreenFitFilter`` is installed once on the ``QApplication`` and fits every
dialog as it is shown, so this needs no per-dialog wiring and is a no-op for the
dialogs that already fit.

The geometry itself is a pure function (:func:`fitted_geometry`) so it can be
unit-tested without a display.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QEvent, QObject, QRect
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QWidget

#: Breathing room left between a fitted window and the edge of the usable screen
#: area, in logical pixels. Enough that the window frame and its shadow stay
#: clear of the taskbar without visibly shrinking a dialog that nearly fits.
DEFAULT_MARGIN = 24


def fitted_geometry(
    current: QRect, available: QRect, margin: int = DEFAULT_MARGIN
) -> QRect:
    """Return ``current`` shrunk and nudged to sit fully inside ``available``.

    Shrinks first (a window taller than the screen can never be positioned onto
    it), then moves, so the result is always fully contained. ``margin`` is
    dropped when the available area is too small to honour it, which keeps this
    total for tiny screens instead of returning a negative size.
    """
    usable_w = available.width() - 2 * margin
    usable_h = available.height() - 2 * margin
    if usable_w <= 0 or usable_h <= 0:
        # Pathologically small screen: fall back to the raw available area.
        usable_w = available.width()
        usable_h = available.height()

    width = min(current.width(), usable_w)
    height = min(current.height(), usable_h)

    # Clamp the top-left so the whole window is on-screen, preferring to keep the
    # title bar visible (top/left win) when the window still cannot fit.
    x = min(current.x(), available.right() - width + 1)
    y = min(current.y(), available.bottom() - height + 1)
    x = max(x, available.left())
    y = max(y, available.top())
    return QRect(x, y, width, height)


def available_geometry_for(window: QWidget) -> QRect | None:
    """The usable area (screen minus taskbar) of the screen ``window`` is on."""
    screen = window.screen()
    if screen is None:
        screen = QGuiApplication.primaryScreen()
    if screen is None:
        return None
    return screen.availableGeometry()


def fit_to_available_screen(
    window: QWidget,
    margin: int = DEFAULT_MARGIN,
    available: QRect | None = None,
) -> None:
    """Clamp ``window`` so it cannot extend past the screen it is shown on.

    A hard minimum size wins over ``resize`` in Qt, so an over-tall minimum is
    relaxed first -- several dialogs declare minimums (e.g. 1024x768) that
    cannot fit a small or heavily-scaled display at all.

    ``available`` overrides the detected screen area (tests inject a display
    they do not have).
    """
    if available is None:
        available = available_geometry_for(window)
    if available is None:
        return

    target = fitted_geometry(window.frameGeometry(), available, margin)
    if target == window.frameGeometry():
        return

    # Relax a minimum that is itself larger than the screen, or the resize below
    # is silently ignored and the window stays oversized.
    minimum = window.minimumSize()
    if minimum.width() > target.width() or minimum.height() > target.height():
        window.setMinimumSize(
            min(minimum.width(), target.width()),
            min(minimum.height(), target.height()),
        )

    # The frame (title bar + borders) is not part of the client area we resize,
    # so take it out of the budget before resizing.
    frame = window.frameGeometry()
    chrome_w = max(0, frame.width() - window.width())
    chrome_h = max(0, frame.height() - window.height())
    window.resize(max(1, target.width() - chrome_w), max(1, target.height() - chrome_h))
    window.move(target.topLeft())

    # If even the layout's minimum cannot fit, the content will still be clipped.
    # Say so in the log rather than leaving a mystery for the next screenshot.
    needed = window.minimumSizeHint()
    if needed.height() > target.height() or needed.width() > target.width():
        logging.warning(
            "%s cannot fit the available screen area (%dx%d needed, %dx%d "
            "available); its content will be clipped.",
            type(window).__name__,
            needed.width(),
            needed.height(),
            target.width(),
            target.height(),
        )


class ScreenFitFilter(QObject):
    """Application event filter that fits every dialog to its screen on show."""

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if isinstance(watched, QDialog) and event.type() == QEvent.Type.Show:
            # Fit after Qt has applied the dialog's own sizing, but before it is
            # painted, so there is no visible resize.
            fit_to_available_screen(watched)
        # Deliberately NOT `super().eventFilter(watched, event)`. An application-wide
        # filter sees every event in the process, and PySide6 does not guarantee the
        # wrapper it hands back is a QObject -- a QWidgetItem (a QLayoutItem, which
        # is not a QObject at all) has been observed here, and forwarding that to the
        # C++ base signature raises TypeError on every such event. QObject's base
        # implementation does nothing but report "not handled", so say that directly:
        # same behaviour, no round trip through a signature we cannot satisfy.
        # `watched` is typed `object` for the same reason -- the annotation would
        # otherwise be a lie.
        return False
