"""The Edit Flight payload editor fits on screen without crushing its content.

The reported symptom was the Edit Flight dialog opening past the top of a 1440p
panel at 150% scaling (~928 usable px) with its pylon rows squeezed until the
store names clipped. Two causes, both guarded here:

* the pylon list had no scroll, so its full height was also its *minimum* -- and
  the screen-fit clamp relaxes a minimum to get a window on screen, so the rows
  were squeezed rather than the list scrolling;
* every dropdown hinted at the width of its longest entry, and store names run
  long enough that a full pylon list demanded over 2000 px of width.

These drive the real ``QLoadoutEditor`` against real pydcs pylon data (the
F-15E's 19 stations are the most of any airframe in DCS) rather than a stand-in,
since it is the real widget's size hints that the dialog is laid out from.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

import pytest

from game import persistency
from game.ato.loadouts import Loadout
from game.data.weapons import Pylon
from game.dcs.aircrafttype import AircraftType

#: Usable height of the reported display: 1440p at 150% scaling, minus taskbar
#: and the screen-fit margin. The whole dialog has to fit inside this.
USABLE_HEIGHT = 880

#: The same for a 1080p panel at 150%, the smallest display worth supporting.
SMALL_USABLE_HEIGHT = 624

#: Height the payload tab's loadout column gets on the reported display, once the
#: dialog is sized by its tallest tab (General settings) and its own chrome.
COLUMN_HEIGHT = 700

#: Stations the column must show at once at that height. Covers a full loadout on
#: everything up to the fourteen-station strike jets; the handful of longer lists
#: scroll their last row or two rather than being squeezed.
MIN_STATIONS_ON_SCREEN = 14


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    # AircraftType / Pylon load the unit data + weapon DB from the saved-game dir.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16887)


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


@pytest.fixture
def busiest_flyable_aircraft() -> AircraftType:
    """The longest pylon list a human actually sits in front of.

    The absolute longest belongs to an AI-only airframe; this is the worst case
    for "can I see my whole loadout at once", which only matters where somebody
    is editing stations by hand.
    """
    flyable = [
        variant
        for dcs_type in AircraftType.each_dcs_type()
        for variant in AircraftType.for_dcs_type(dcs_type)
        if variant.flyable
    ]
    return max(flyable, key=lambda a: len(a.dcs_unit_type.pylons))


@pytest.fixture
def busiest_aircraft() -> AircraftType:
    """Whichever airframe carries the most stations -- the worst case for height.

    Picked by measurement rather than by name so a new module (or a mod) with a
    longer pylon list is covered the day it lands.
    """
    with_variants = (
        (len(dcs_type.pylons), variant)
        for dcs_type in AircraftType.each_dcs_type()
        for variant in AircraftType.for_dcs_type(dcs_type)
    )
    return max(with_variants, key=lambda row: row[0])[1]


def _loadout_editor(aircraft: AircraftType) -> Any:
    """A real ``QLoadoutEditor`` over real pylon data.

    Only the handful of attributes the editor reads at construction are faked;
    the pylons, stores and widgets are the real ones.
    """
    from qt_ui.windows.mission.flight.payload.QLoadoutEditor import QLoadoutEditor

    game = SimpleNamespace(
        settings=SimpleNamespace(
            restrict_weapons_by_date=False,
            restrict_weapons_by_stock=False,
        ),
    )
    flight = SimpleNamespace(unit_type=aircraft)
    member = SimpleNamespace(
        loadout=Loadout.empty_loadout(), use_custom_loadout=False, is_player=False
    )
    editor = QLoadoutEditor(flight, member, game)  # type: ignore[arg-type]
    # Size hints are stale until the layout has run; the dialog gets this for
    # free on show, a bare widget in a test does not.
    editor.ensurePolished()
    editor.layout().activate()
    return editor


def test_the_worst_case_is_a_long_pylon_list(busiest_aircraft: AircraftType) -> None:
    # Guard the guards: if the busiest airframe were a two-station trainer, the
    # height checks below would pass without testing anything.
    assert len(busiest_aircraft.dcs_unit_type.pylons) >= 12


def test_pylon_list_scrolls_instead_of_shrinking_its_rows(
    qapp: Any, busiest_aircraft: AircraftType
) -> None:
    editor = _loadout_editor(busiest_aircraft)

    # It can shrink far below the height it would like, so a small screen scrolls
    # the list. Without the scroll these were equal and the rows took the squeeze.
    assert editor.minimumSizeHint().height() < editor.sizeHint().height() / 2
    assert editor.minimumSizeHint().height() < SMALL_USABLE_HEIGHT


def test_the_column_shows_a_full_loadout_without_scrolling(
    qapp: Any, busiest_flyable_aircraft: AircraftType
) -> None:
    from PySide6.QtWidgets import QScrollArea
    from qt_ui.windows.mission.flight.payload.QPylonEditor import QPylonEditor

    editor = _loadout_editor(busiest_flyable_aircraft)
    rows = editor.findChildren(QPylonEditor)
    assert len(rows) == len(list(Pylon.iter_pylons(busiest_flyable_aircraft)))

    # Scrolling is the fallback, not the normal case. Given the height the tab
    # affords this column, the list has to show a real loadout at a glance --
    # this is the check the size hint cannot make, since QScrollArea::sizeHint is
    # capped at 24 font-heights and the list can only grow into space the column
    # gives it. The very longest lists (a 19-station AI F-15E) do scroll the last
    # station or two; what must never happen is the list collapsing to a stub.
    editor.resize(editor.width(), COLUMN_HEIGHT)
    editor.layout().activate()

    scroll = editor.findChild(QScrollArea)
    assert scroll is not None
    row_height = max(row.sizeHint().height() for row in rows)
    visible_rows = scroll.viewport().height() // row_height
    assert visible_rows >= MIN_STATIONS_ON_SCREEN


def test_pylon_list_fits_the_reported_display(
    qapp: Any, busiest_aircraft: AircraftType
) -> None:
    editor = _loadout_editor(busiest_aircraft)
    # The loadout column is one of two, so its hint plus the dialog's own chrome
    # has to leave room. Fitting outright is the simple, sufficient check.
    assert editor.sizeHint().height() <= USABLE_HEIGHT


def test_store_dropdowns_do_not_demand_the_width_of_their_longest_store(
    qapp: Any, busiest_aircraft: AircraftType
) -> None:
    from qt_ui.windows.mission.flight.payload.QPylonEditor import QPylonEditor

    from qt_ui.widgets.dropdownwidth import natural_content_width

    editor = _loadout_editor(busiest_aircraft)
    # The station with the longest store names is the one that used to set the
    # dialog's width; a station offering two short-named stores never did.
    combo = max(
        (row.weapon_combo for row in editor.findChildren(QPylonEditor)),
        key=natural_content_width,
    )

    natural = natural_content_width(combo)
    assert combo.sizeHint().width() < natural, "the box is asking for its longest entry"

    # ...but the list itself still shows the store names in full.
    assert combo.view().minimumWidth() >= natural
