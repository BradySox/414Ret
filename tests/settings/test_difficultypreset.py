from __future__ import annotations

from dataclasses import MISSING, fields
from types import SimpleNamespace
from typing import Any, cast

import pytest

from game.settings import (
    DifficultyPreset,
    Settings,
    apply_preset,
    detect_preset,
)
from game.settings.difficultypreset import PRESET_FIELDS, PRESET_VALUES


def _field_default(name: str) -> Any:
    for f in fields(Settings):
        if f.name == name:
            assert f.default is not MISSING, f"{name} has no scalar default"
            return f.default
    raise KeyError(name)


def _settings_with(**values: Any) -> Settings:
    # apply/detect are duck-typed (getattr/setattr only), so a namespace is a
    # sufficient and fast stand-in for a full Settings instance.
    return cast(Settings, SimpleNamespace(**values))


def test_normal_preset_is_a_clean_reset_to_defaults() -> None:
    # Picking "Normal" must restore stock values, so it has to equal the
    # Settings field defaults exactly.
    for name, value in PRESET_VALUES[DifficultyPreset.NORMAL].items():
        assert _field_default(name) == value, name


def test_all_preset_fields_are_real_settings_fields() -> None:
    assert PRESET_FIELDS <= {f.name for f in fields(Settings)}


def test_every_preset_sets_the_same_fields() -> None:
    keysets = [frozenset(values) for values in PRESET_VALUES.values()]
    assert all(keys == keysets[0] for keys in keysets)


@pytest.mark.parametrize("preset", list(DifficultyPreset))
def test_apply_then_detect_round_trips(preset: DifficultyPreset) -> None:
    settings = _settings_with()
    apply_preset(settings, preset)
    for name, value in PRESET_VALUES[preset].items():
        assert getattr(settings, name) == value
    assert detect_preset(settings) is preset


def test_apply_leaves_unrelated_fields_untouched() -> None:
    ns = SimpleNamespace(use_auto_fog="sentinel", supercarrier="sentinel")
    apply_preset(cast(Settings, ns), DifficultyPreset.ACE)
    assert ns.use_auto_fog == "sentinel"
    assert ns.supercarrier == "sentinel"


def test_detect_returns_none_for_a_custom_mix() -> None:
    settings = _settings_with()
    apply_preset(settings, DifficultyPreset.ACE)
    settings.labels = "Full"  # tweak one field away from the preset
    assert detect_preset(settings) is None


def test_presets_are_mutually_distinct() -> None:
    # Otherwise detect_preset would be ambiguous.
    seen: list[tuple[tuple[str, str], ...]] = []
    for preset in DifficultyPreset:
        signature = tuple(sorted((k, str(v)) for k, v in PRESET_VALUES[preset].items()))
        assert signature not in seen
        seen.append(signature)
