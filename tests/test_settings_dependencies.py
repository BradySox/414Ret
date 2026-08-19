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
from enum import Enum
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
        # A dependency's expected value is usually a bool, but a knob that only
        # applies to one choice of a dropdown (ATMOS-X live weather under the
        # cloud-preset pack) is gated on an enum member. Either way it must be a
        # value the master can actually hold, or the control greys out forever.
        assert isinstance(expected, (bool, Enum))
        assert isinstance(
            getattr(settings, master), type(expected)
        ), f"{name}: master {master!r} can never equal {expected!r}"
        assert master != name, f"{name}: cannot depend on itself"
        wired += 1
    # Guard against a mass-unwiring regression (we wired ~21 dependencies).
    assert wired >= 20


def test_normalize_enabled_when() -> None:
    assert normalize_enabled_when(None) is None
    assert normalize_enabled_when("motorpool_enabled") == ("motorpool_enabled", True)
    assert normalize_enabled_when(("automate_front_line_stance", False)) == (
        "automate_front_line_stance",
        False,
    )
    # An enum member survives normalization intact -- coercing it to a bool would
    # make every choice of the dropdown satisfy the dependency.
    from game.settings.settings import CloudPresetPack

    assert normalize_enabled_when(("cloud_preset_pack", CloudPresetPack.ATMOSX)) == (
        "cloud_preset_pack",
        CloudPresetPack.ATMOSX,
    )


# --- Qt: the greying actually fires --------------------------------------------------


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _layout_for(
    section_page: tuple[str, str], settings: Settings, hub: Any = None
) -> Any:
    from qt_ui.windows.settings.QSettingsWindow import AutoSettingsLayout

    page, section = section_page
    sc = SimpleNamespace(settings=settings)
    return AutoSettingsLayout(page, section, sc, lambda: None, None, hub)  # type: ignore[arg-type]


def _section_of(settings: Settings, field: str) -> tuple[str, str]:
    for page in settings.pages():
        for section in settings.sections(page):
            if field in dict(settings.fields(page, section)):
                return page, section
    raise AssertionError(f"{field} is not rendered anywhere")


def test_child_greys_out_when_master_is_off(qapp: Any) -> None:
    """The master and its child now live on different pages.

    `motorpool_enabled` is a feature gate (Features page) and
    `motorpool_spawn_cap` is one of its knobs (Campaign Management), so this also
    covers the cross-page half of the dependency wiring.
    """
    from qt_ui.windows.settings.QSettingsWindow import SettingsDependencyHub

    settings = Settings()
    settings.motorpool_enabled = False

    hub = SettingsDependencyHub()
    master_layout = _layout_for(
        _section_of(settings, "motorpool_enabled"), settings, hub
    )
    child_layout = _layout_for(
        _section_of(settings, "motorpool_spawn_cap"), settings, hub
    )
    assert master_layout is not child_layout, "fixture assumes a cross-section pair"

    cap = child_layout.settings_map["motorpool_spawn_cap"]
    label = child_layout.labels_map["motorpool_spawn_cap"]
    # Master off -> child control + label disabled on open.
    assert not cap.isEnabled()
    assert not label.isEnabled()

    # Toggling the master ON re-enables the child live, from another page.
    master_layout.settings_map["motorpool_enabled"].setChecked(True)
    assert cap.isEnabled()
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


def test_enum_dependency_greys_on_the_wrong_choice(qapp: Any) -> None:
    """A dropdown, not a checkbox, is the master: the ATMOS-X knobs only apply to
    one choice of the cloud-preset pack. A bool-only comparison greyed them forever."""
    from game.settings.settings import CloudPresetPack

    settings = Settings()
    settings.cloud_preset_pack = CloudPresetPack.BANDIT
    layout = _layout_for(_section_of(settings, "atmosx_live_weather"), settings)

    live = layout.settings_map["atmosx_live_weather"]
    station = layout.settings_map["atmosx_metar_station"]
    assert not live.isEnabled()
    assert not station.isEnabled()

    pack = layout.settings_map["cloud_preset_pack"]
    pack.setCurrentIndex(pack.findData(CloudPresetPack.ATMOSX))
    assert live.isEnabled()
    assert station.isEnabled()


def test_a_text_setting_renders_as_an_editable_box(qapp: Any) -> None:
    """A settings type the dialog does not know raises at build time, but one that
    renders and never writes back is silent -- so pin the round-trip."""
    from PySide6.QtWidgets import QLineEdit

    settings = Settings()
    layout = _layout_for(_section_of(settings, "atmosx_metar_station"), settings)

    box = layout.settings_map["atmosx_metar_station"]
    assert isinstance(box, QLineEdit)
    assert box.placeholderText()  # the "worked out for you" default announces itself
    box.setText("  lclk  ")
    assert settings.atmosx_metar_station == "lclk"


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
