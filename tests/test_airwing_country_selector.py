"""The Air Wing Configuration country selector writes squadron.country live (#627).

Drives the real widget offscreen with a faked squadron: the combo opens on the
squadron's current nation, a selection writes the pydcs Country to the squadron
immediately (the livery-selector pattern), ``set_squadron`` re-points after a
replace-with-preset without writing anything itself, and a country pydcs doesn't
list is shown faithfully instead of misreporting the first list entry.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace
from typing import Any, Iterator, cast

import pytest
from PySide6.QtWidgets import QApplication
from dcs.countries import Greece, USA


@pytest.fixture(scope="module", autouse=True)
def _qt_app() -> Iterator[QApplication]:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    yield app


def _selector(squadron: Any) -> Any:
    from qt_ui.windows.AirWingConfigurationDialog import SquadronCountrySelector

    return SquadronCountrySelector(cast(Any, squadron))


def test_opens_on_the_squadrons_nation_and_writes_live() -> None:
    squadron = SimpleNamespace(country=USA())
    selector = _selector(squadron)
    assert selector.currentText() == "USA"

    selector.setCurrentText("Greece")
    assert squadron.country.id == Greece.id


def test_set_squadron_repoints_after_replace_with_preset() -> None:
    first = SimpleNamespace(country=USA())
    replacement = SimpleNamespace(country=Greece())
    selector = _selector(first)

    selector.set_squadron(replacement)
    assert selector.currentText() == "Greece"
    # The re-sync itself must not write anything...
    assert first.country.name == "USA"
    # ...and later edits land on the replacement, not the discarded squadron.
    selector.setCurrentText("France")
    assert replacement.country.name == "France"
    assert first.country.name == "USA"


def test_unlisted_country_is_shown_faithfully() -> None:
    modded = SimpleNamespace(country=SimpleNamespace(id=999, name="Atlantis"))
    selector = _selector(modded)
    assert selector.currentText() == "Atlantis"
