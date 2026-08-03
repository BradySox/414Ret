"""One unparseable mod payload file must not cost an airframe its loadouts.

Regression cover for the 2026-08-03 finding. pydcs's ``FlyingType.load_payloads``
catches ``SyntaxError`` but not ``ValueError``, and the CJS Super Hornet mod
indexes its pylon tables with named constants::

    local WTL = 1
    ["pylons"] = { [WTL] = { ["CLSID"] = "...", ["num"] = WTL }, ... }

which pydcs's Lua parser cannot read. Two things went wrong because of it:

1. The exception escaped into whatever first asked for a loadout. Headlessly that
   aborted a whole planning pass (``Coalition.plan_missions`` ->
   ``plan_convoy_mining`` -> ``Loadout.iter_for_aircraft``).
2. Worse and quieter: ``load_payloads`` sets ``cls.payloads = {}`` *before* it
   walks the payload directories, and the mod directory is walked BEFORE the
   fork's own ``resources/customized_payloads``. So the raise truncated the scan
   and the fork's authored ``Retribution <task>`` fits were never reached --
   measured as FA-18E 2 fits, FA-18F 0, EA-18G 0. The second call then returned
   that truncated dict without raising, so nothing looked broken; the jets just
   planned with whatever was left.

``game.dcs.payloadpatch`` skips the bad file with a warning and keeps walking,
which restores FA-18E 13 / FA-18F 13 / EA-18G 4 authored fits.

The tests below use a synthetic payload directory so they do not depend on the
CJS mod being installed. The *contents* of the fork's Super Hornet payload files
are covered by ``tests/fourteenth/test_navy_bomb_variants.py``.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from dcs.payloads import PayloadDirectories
from dcs.planes import FA_18C_hornet

from game.dcs.payloadpatch import (
    _uses_unsupported_lua_table_indices,
    patch_pydcs_payload_loader,
)

# A payload file in the CJS shape: pylon table keyed by a local constant.
UNPARSEABLE = """local WTL = 1
local CEN = 5
local unitPayloads = {
\t["name"] = "FA-18C_hornet",
\t["payloads"] = {
\t\t[1] = {
\t\t\t["name"] = "Mod fit pydcs cannot read",
\t\t\t["pylons"] = {
\t\t\t\t[WTL] = { ["CLSID"] = "{MOD_STORE_A}", ["num"] = WTL },
\t\t\t\t[CEN] = { ["CLSID"] = "{MOD_STORE_B}", ["num"] = CEN },
\t\t\t},
\t\t\t["tasks"] = { [1] = 11 },
\t\t},
\t},
\t["unitType"] = "FA-18C_hornet",
}
return unitPayloads
"""

PARSEABLE = """local unitPayloads = {
\t["name"] = "FA-18C_hornet",
\t["payloads"] = {
\t\t[1] = {
\t\t\t["name"] = "Retribution Fixture",
\t\t\t["pylons"] = {
\t\t\t\t[1] = { ["CLSID"] = "{GOOD_STORE}", ["num"] = 2 },
\t\t\t},
\t\t\t["tasks"] = { [1] = 11 },
\t\t},
\t},
\t["unitType"] = "FA-18C_hornet",
}
return unitPayloads
"""


@pytest.fixture
def payload_dirs(tmp_path: Path) -> Iterator[None]:
    """A preferred dir holding an unreadable mod file, a fallback holding ours.

    This is the real ordering: mod payload directories are searched before the
    fork's customized_payloads, so a raise in the first one hides the second.
    """
    from dcs.unittype import FlyingType

    preferred = tmp_path / "mod"
    fallback = tmp_path / "customized_payloads"
    preferred.mkdir()
    fallback.mkdir()
    (preferred / "FA-18C_hornet.lua").write_text(UNPARSEABLE, encoding="utf-8")
    (fallback / "FA-18C_hornet.lua").write_text(PARSEABLE, encoding="utf-8")

    # Replace the whole search order, not just preferred/fallback: the real
    # payload_dirs() also yields the installed DCS and mod directories, which
    # would make this test depend on the host's DCS install.
    saved_dirs = PayloadDirectories.payload_dirs
    # Starts as None until pydcs first scans; treat that as "empty".
    saved_cache = dict(FlyingType._payload_cache or {})
    saved_payloads = FA_18C_hornet.payloads

    PayloadDirectories.payload_dirs = classmethod(  # type: ignore[assignment,method-assign]
        lambda cls: iter([preferred, fallback])
    )
    FlyingType._payload_cache = {}
    FA_18C_hornet.payloads = None
    try:
        yield
    finally:
        PayloadDirectories.payload_dirs = saved_dirs  # type: ignore[method-assign]
        FlyingType._payload_cache = saved_cache
        FA_18C_hornet.payloads = saved_payloads


def test_unreadable_mod_file_does_not_hide_our_own_payloads(payload_dirs: None) -> None:
    """The bug: the raise truncated the scan before customized_payloads."""
    patch_pydcs_payload_loader()
    payloads = FA_18C_hornet.load_payloads()
    assert "Retribution Fixture" in payloads, (
        "an unparseable mod payload file swallowed the fork's own fits -- the "
        "airframe would plan its missions with no loadout"
    )


def test_unreadable_mod_file_does_not_raise(payload_dirs: None) -> None:
    """The loud half: this used to abort a turn's planning pass outright."""
    patch_pydcs_payload_loader()
    FA_18C_hornet.load_payloads()  # must not raise


def test_unsupported_lua_index_detection() -> None:
    """The signature that makes a mod payload file unreadable to pydcs."""
    assert _uses_unsupported_lua_table_indices(UNPARSEABLE)
    assert not _uses_unsupported_lua_table_indices(PARSEABLE)


def test_patching_the_payload_loader_is_idempotent() -> None:
    """persistency.setup() and qt_ui.main both call it; without the guard each
    call would wrap the previously patched loader again."""
    from dcs.unittype import FlyingType

    patch_pydcs_payload_loader()
    # A classmethod hands out a fresh bound method per attribute access, so
    # identity has to be checked on the underlying function.
    once = FlyingType.load_payloads.__func__  # type: ignore[attr-defined]
    patch_pydcs_payload_loader()
    assert FlyingType.load_payloads.__func__ is once  # type: ignore[attr-defined]
