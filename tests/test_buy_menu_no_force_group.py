"""The TGO buy menu survives a coalition with no ForceGroup for the site.

Clicking Buy on a ground object whose owner's armed forces field no group for
the site's role left the force-group selector empty, itemData returning None,
and the dialog crashing with ``AttributeError: 'NoneType' object has no
attribute 'layouts'`` (retribution.log 2026-07-16, via QGroundObjectMenu
buy_group). The dialog must open with an explanatory label instead.

Drives the real QGroundObjectBuyMenu under the offscreen platform; the TGO and
coalition are minimal duck-typed stand-ins because the guard path never touches
the game or the template layout.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

import pytest
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel

from game.theater.theatergroundobject import SamGroundObject
from qt_ui.uiconstants import EVENT_ICONS
from qt_ui.windows.groundobject.QGroundObjectBuyMenu import QGroundObjectBuyMenu


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    assert isinstance(app, QApplication)
    # The dialog sets its window icon from the app-startup icon cache, which a
    # bare test QApplication never fills.
    EVENT_ICONS.setdefault("capture", QPixmap())
    return app


def _tgo_with_empty_armed_forces() -> SamGroundObject:
    # The guard path reads only obj_name and coalition (armed_forces + faction
    # name), so bypass the heavyweight constructor.
    tgo = SamGroundObject.__new__(SamGroundObject)
    tgo.name = "TEST SAM"
    coalition = SimpleNamespace(
        armed_forces=SimpleNamespace(groups_for_tasks=lambda tasks: []),
        faction=SimpleNamespace(name="Testland"),
    )
    tgo.control_point = SimpleNamespace(coalition=coalition)  # type: ignore[assignment]
    return tgo


def test_buy_menu_opens_with_no_force_group(qapp: QApplication) -> None:
    # The guard path never touches the parent widget or the game.
    dialog = QGroundObjectBuyMenu(
        None,  # type: ignore[arg-type]
        _tgo_with_empty_armed_forces(),
        game=None,  # type: ignore[arg-type]
        current_group_value=0,
    )
    labels = [label.text() for label in dialog.findChildren(QLabel)]
    assert any("cannot field" in text for text in labels)
    # No buy UI was built.
    assert not hasattr(dialog, "template_layout")
    dialog.deleteLater()
