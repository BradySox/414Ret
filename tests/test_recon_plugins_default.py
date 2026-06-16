"""One-time TARS / Flight Control default-on migration.

A save created before these plugins shipped (or before they were flipped to
default-on) can have them recorded as off. ``Settings.__setstate__`` flips them on
exactly once — keyed on the absence of the marker in the raw unpickled state — and
never re-stomps a deliberate choice in an already-migrated save.
"""

from __future__ import annotations

from typing import Any

from game.settings import Settings


def _restore(state: dict[str, Any]) -> Settings:
    settings = Settings.__new__(Settings)
    settings.__setstate__(state)
    return settings


def test_legacy_save_flips_recon_plugins_on() -> None:
    # No marker in the raw state -> legacy save; both plugins recorded as off.
    settings = _restore({"plugins": {"tars": False, "flightcontrol": False}})
    assert settings.plugins["tars"] is True
    assert settings.plugins["flightcontrol"] is True
    assert settings.applied_recon_plugins_default is True


def test_already_migrated_save_keeps_user_choice() -> None:
    # Marker present -> migration already ran; a deliberate "off" must be preserved.
    settings = _restore(
        {
            "plugins": {"tars": False, "flightcontrol": False},
            "applied_recon_plugins_default": True,
        }
    )
    assert settings.plugins["tars"] is False
    assert settings.plugins["flightcontrol"] is False
