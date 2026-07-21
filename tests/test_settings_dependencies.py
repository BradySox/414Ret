"""Settings dependency-greying (``enabled_when``) + the detail-summary rendering.

The pure half (master validity, the normalize/summary helpers) needs no Qt. The
greying half drives the real ``AutoSettingsLayout`` under the offscreen platform to
prove a child control + label grey out when its master toggle is off and come back
when it is on.
"""

from __future__ import annotations

import dataclasses
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace
from typing import Any, Iterator

import pytest

from game.settings import Settings
from game.settings.optiondescription import (
    OptionDescription,
    SETTING_DESCRIPTION_KEY,
    normalize_enabled_when,
)


def _descriptors() -> Iterator[tuple[str, OptionDescription]]:
    for f in dataclasses.fields(Settings):
        description = f.metadata.get(SETTING_DESCRIPTION_KEY)
        if description is not None:
            yield f.name, description


# --- pure: dependency wiring is well-formed ------------------------------------------


def test_enabled_when_masters_are_real_settings() -> None:
    names = {name for name, _ in _descriptors()}
    settings = Settings()
    wired = 0
    for name, description in _descriptors():
        spec = description.enabled_when
        if spec is None:
            continue
        master, expected = spec
        assert (
            master in names
        ), f"{name}: enabled_when master {master!r} is not a setting"
        assert hasattr(
            settings, master
        ), f"{name}: master {master!r} missing on Settings"
        assert isinstance(expected, bool)
        assert master != name, f"{name}: cannot depend on itself"
        wired += 1
    # Guard against a mass-unwiring regression (we wired ~21 dependencies).
    assert wired >= 20


def test_normalize_enabled_when() -> None:
    assert normalize_enabled_when(None) is None
    assert normalize_enabled_when("red_intent") == ("red_intent", True)
    assert normalize_enabled_when(("automate_front_line_stance", False)) == (
        "automate_front_line_stance",
        False,
    )


# --- Qt: the greying actually fires --------------------------------------------------


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _layout_for(section_page: tuple[str, str], settings: Settings) -> Any:
    from qt_ui.windows.settings.QSettingsWindow import AutoSettingsLayout

    page, section = section_page
    sc = SimpleNamespace(settings=settings)
    return AutoSettingsLayout(page, section, sc, lambda: None)  # type: ignore[arg-type]


def test_child_greys_out_when_master_is_off(qapp: Any) -> None:
    settings = Settings()
    settings.red_intent = False
    layout = _layout_for(("Air Doctrine", "Auto-planner behavior"), settings)

    boldness = layout.settings_map["red_intent_boldness"]
    label = layout.labels_map["red_intent_boldness"]
    # Master off -> child control + label disabled on open.
    assert not boldness.isEnabled()
    assert not label.isEnabled()

    # Toggling the master ON re-enables the child live.
    layout.settings_map["red_intent"].setChecked(True)
    assert boldness.isEnabled()
    assert label.isEnabled()


def test_inverse_dependency_greys_when_master_is_on(qapp: Any) -> None:
    # default_front_line_stance is editable only when automation is OFF.
    settings = Settings()
    settings.automate_front_line_stance = True
    layout = _layout_for(("Campaign Management", "HQ automation"), settings)

    stance = layout.settings_map["default_front_line_stance"]
    assert not stance.isEnabled()  # automation on -> the manual default is greyed

    layout.settings_map["automate_front_line_stance"].setChecked(False)
    assert stance.isEnabled()


def test_long_detail_renders_fully_inline(qapp: Any) -> None:
    # The first-sentence + hover-tooltip summarisation is REVERTED (2026-07-20
    # user call): reading a setting must not require hovering it, so the whole
    # detail renders on the page -- and Qt wraps it to the real column width
    # (word wrap + label-column stretch) instead of a fixed 55-char textwrap
    # that left the window's middle as dead space. Exercised on the Victory
    # conditions section, whose details are well past the old 150-char limit.
    page_section = ("Campaign Management", "Victory conditions")
    layout = _layout_for(page_section, Settings())
    assert layout.columnStretch(0) == 1  # the label column absorbs spare width
    checked = 0
    long_seen = False
    for name, description in Settings.fields(*page_section):
        detail = description.detail
        if detail is None:
            continue
        label = layout.labels_map[name]
        assert label.wordWrap(), name  # Qt wraps to the column, not textwrap
        # Any truncation breaks this: the label text must reproduce the full
        # detail verbatim (whitespace-normalized).
        plain = " ".join(label.text().replace("<br />", " ").split())
        assert " ".join(detail.split()) in plain, name
        checked += 1
        long_seen = long_seen or len(detail) > 150
    assert checked >= 1
    assert long_seen  # the section genuinely exercises the old truncation case
