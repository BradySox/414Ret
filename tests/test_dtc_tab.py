"""The Edit Flight DTC tab writes flight.dtc_options live (§74).

Drives the real widget offscreen with faked Flight/Game: the master combo's
tri-state maps to DtcOptions.enabled, the contents group greys out whenever the
resolved state is off (including the follow-campaign case), and each section
checkbox writes its field.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace
from typing import Any, Iterator

import pytest
from PySide6.QtWidgets import QApplication

from game.ato.dtcoptions import DtcOptions


@pytest.fixture(scope="module", autouse=True)
def _qt_app() -> Iterator[QApplication]:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    yield app


def _tab(*, campaign_on: bool = True, options: DtcOptions | None = None) -> Any:
    from qt_ui.windows.mission.flight.QFlightDtcTab import QFlightDtcTab

    flight = SimpleNamespace(dtc_options=options or DtcOptions())
    game = SimpleNamespace(settings=SimpleNamespace(dtc_data_cartridges=campaign_on))
    return QFlightDtcTab(flight, game), flight  # type: ignore[arg-type]


def _enabled(flight: Any) -> object:
    # Read through a helper so mypy does not narrow the member expression
    # across the sequential asserts (it flags the later ones unreachable).
    return flight.dtc_options.enabled


def test_master_combo_maps_the_tristate() -> None:
    tab, flight = _tab()
    assert tab.mode_selector.currentIndex() == 0
    assert tab.contents_group.isEnabled()

    tab.mode_selector.setCurrentIndex(2)  # Never load
    assert _enabled(flight) is False
    assert not tab.contents_group.isEnabled()

    tab.mode_selector.setCurrentIndex(1)  # Always load
    assert _enabled(flight) is True
    assert tab.contents_group.isEnabled()

    tab.mode_selector.setCurrentIndex(0)  # Follow campaign
    assert _enabled(flight) is None


def test_follow_campaign_greys_when_the_setting_is_off() -> None:
    tab, flight = _tab(campaign_on=False)
    assert "off" in tab.mode_selector.itemText(0)
    assert not tab.contents_group.isEnabled()
    tab.mode_selector.setCurrentIndex(1)  # per-flight override wins
    assert tab.contents_group.isEnabled()


def test_section_checkboxes_write_the_options() -> None:
    tab, flight = _tab()
    by_attr = {attr: box for box, attr in tab.section_boxes}
    assert set(by_attr) == {
        "comms",
        "route",
        "nav_aids",
        "flot_and_zones",
        "friendly_orbits",
        "threat_rings",
    }
    assert all(box.isChecked() for box in by_attr.values())

    by_attr["threat_rings"].setChecked(False)
    assert flight.dtc_options.threat_rings is False
    by_attr["threat_rings"].setChecked(True)
    assert flight.dtc_options.threat_rings is True


def test_existing_choices_are_reflected() -> None:
    options = DtcOptions(enabled=False, comms=False)
    tab, _ = _tab(options=options)
    assert tab.mode_selector.currentIndex() == 2
    by_attr = {attr: box for box, attr in tab.section_boxes}
    assert not by_attr["comms"].isChecked()
    assert by_attr["route"].isChecked()
