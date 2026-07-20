"""The Air Wing Configuration country selector writes squadron.country live (#627).

Drives the real widget offscreen with a faked squadron: the combo opens on the
squadron's current nation, a selection writes the pydcs Country to the squadron
immediately (the livery-selector pattern), ``set_squadron`` re-points after a
replace-with-preset without writing anything itself, and a country pydcs doesn't
list is shown faithfully instead of misreporting the first list entry.

The list is trimmed to the airframe's operator nations (see
game/dcs/operatorcountries.py): a Hornet squadron no longer offers the Third
Reich, the faction's own country is always present, and an airframe with no
operator data (a mod) falls back to the full list.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace
from typing import Any, Iterator, cast

import pytest
from PySide6.QtWidgets import QApplication
from dcs.countries import (
    Canada,
    CombinedJointTaskForcesBlue,
    Greece,
    Switzerland,
    USA,
    country_dict,
)
from dcs.planes import FA_18C_hornet


@pytest.fixture(scope="module", autouse=True)
def _qt_app() -> Iterator[QApplication]:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    yield app


def _squadron(country: Any, aircraft: Any = FA_18C_hornet) -> Any:
    return SimpleNamespace(
        country=country,
        aircraft=SimpleNamespace(dcs_unit_type=aircraft),
        coalition=SimpleNamespace(
            faction=SimpleNamespace(country=CombinedJointTaskForcesBlue())
        ),
    )


def _selector(squadron: Any) -> Any:
    from qt_ui.windows.AirWingConfigurationDialog import SquadronCountrySelector

    return SquadronCountrySelector(cast(Any, squadron))


def test_opens_on_the_squadrons_nation_and_writes_live() -> None:
    squadron = _squadron(USA())
    selector = _selector(squadron)
    assert selector.currentText() == "USA"

    selector.setCurrentText("Switzerland")
    assert squadron.country.id == Switzerland.id


def test_set_squadron_repoints_after_replace_with_preset() -> None:
    first = _squadron(USA())
    replacement = _squadron(Greece())
    selector = _selector(first)

    selector.set_squadron(replacement)
    assert selector.currentText() == "Greece"
    # The re-sync itself must not write anything...
    assert first.country.name == "USA"
    # ...and later edits land on the replacement, not the discarded squadron.
    selector.setCurrentText("Canada")
    assert replacement.country.id == Canada.id
    assert first.country.name == "USA"


def test_unlisted_country_is_shown_faithfully() -> None:
    modded = _squadron(SimpleNamespace(id=999, name="Atlantis"))
    selector = _selector(modded)
    assert selector.currentText() == "Atlantis"


def test_list_is_trimmed_to_the_airframes_operators() -> None:
    selector = _selector(_squadron(USA()))
    assert selector.findText("USA") >= 0
    assert selector.findText("Third Reich") == -1
    assert selector.count() < 20


def test_faction_country_is_always_offered() -> None:
    # CJTF Blue is no Hornet operator, but reverting to the faction's shared
    # voice must stay possible.
    selector = _selector(_squadron(USA()))
    assert selector.findText("Combined Joint Task Forces Blue") >= 0


def test_airframe_without_operator_data_offers_the_full_list() -> None:
    mod_jet = cast(Any, SimpleNamespace(id="Not A Real Jet"))
    selector = _selector(_squadron(USA(), aircraft=mod_jet))
    assert selector.count() >= len(country_dict)
