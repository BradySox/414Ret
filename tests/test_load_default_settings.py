"""Regression tests for QSettingsWidget.load_default_settings archive reading.

Pins a launch crash: opening the New Game wizard read the saved ``Default.zip`` to
seed settings, but it only looked for a ``default.json`` member -- while the
"Save Settings" button writes the member as ``settings.json``. A user who had saved
their defaults therefore had the archive silently skipped, ``Settings.__setstate__``
(which seeds plugin-option defaults) never ran, and the plugins settings UI then
raised ``KeyError: 'ctld.tailorctld'``.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

import qt_ui.windows.settings.QSettingsWindow as qsw
from game.settings import Settings
from qt_ui.windows.settings.QSettingsWindow import QSettingsWidget


def _widget_loading_default_from(sd: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setattr(qsw, "settings_dir", lambda: sd)
    # load_default_settings only touches self.settings + settings_dir(); skip the
    # QWidget machinery (and the need for a QApplication) entirely.
    widget: Any = QSettingsWidget.__new__(QSettingsWidget)
    widget.settings = Settings()
    QSettingsWidget.load_default_settings(widget)
    return widget.settings


def test_reads_save_settings_member_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # "Save Settings" writes the JSON member as settings.json, not Default.json.
    with zipfile.ZipFile(tmp_path / "Default.zip", "w") as zf:
        zf.writestr("settings.json", json.dumps({"plugins": {}}))

    settings = _widget_loading_default_from(tmp_path, monkeypatch)

    # The archive was read -> __setstate__ ran -> plugin options are seeded, so the
    # settings UI won't KeyError.
    assert "ctld.tailorctld" in settings.plugins
    settings.plugin_option("ctld.tailorctld")  # must not raise


def test_reads_legacy_default_json_member_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with zipfile.ZipFile(tmp_path / "Default.zip", "w") as zf:
        zf.writestr("Default.json", json.dumps({"plugins": {}}))

    settings = _widget_loading_default_from(tmp_path, monkeypatch)

    assert "ctld.tailorctld" in settings.plugins


def test_seeds_defaults_even_with_no_json_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A Default.zip with no usable JSON member must still seed plugin defaults
    # rather than leave the settings half-initialized.
    with zipfile.ZipFile(tmp_path / "Default.zip", "w") as zf:
        zf.writestr("readme.txt", "not json")

    settings = _widget_loading_default_from(tmp_path, monkeypatch)

    assert "ctld.tailorctld" in settings.plugins
