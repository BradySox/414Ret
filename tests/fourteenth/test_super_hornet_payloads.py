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

import re
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


class TestTheAuthoredFitsUseTheModsOwnStores:
    """A CJS jet must never be authored a stock store.

    The mod models its own pylons and namespaces every store it ships
    (``{SUPERHORNET_PYLON_10_AM_1X_AIM-120C}``) **and inherits ED's entries into
    the same pydcs pylon table**. So a stock store passes ``can_equip`` on the mod
    jet without being mountable on the mod's geometry, DCS silently drops a store
    it cannot resolve, and the pylon spawns EMPTY -- the failure mode §71
    documents for ``(XW)`` fits flown without their pylon injection.

    Reported from a generated Marianas mission as "the Super Hornets are
    generating with empty inside pylons where fuel tanks would normally be". The
    centre-line was the visible one: the DEAD / OCA-Aircraft fits authored a stock
    Litening (``{A111396E-...}``) on station 5. 34 stock stores across the E and F
    fits were re-pointed at the mod's own equivalents.
    """

    CLSID_AND_STATION = re.compile(
        r'\["CLSID"\]\s*=\s*"([^"]*)".*?\["num"\]\s*=\s*(\d+)', re.S
    )

    @staticmethod
    def _payload_files() -> Iterator[tuple[str, Path]]:
        root = Path(__file__).resolve().parents[2] / "resources" / "customized_payloads"
        for name in ("FA-18E", "FA-18F", "EA-18G"):
            path = root / f"{name}.lua"
            assert path.exists(), f"missing authored payloads for {name}"
            yield name, path

    def _stores(self) -> Iterator[tuple[str, str, int]]:
        for name, path in self._payload_files():
            src = path.read_text(encoding="utf-8", errors="replace")
            for clsid, num in self.CLSID_AND_STATION.findall(src):
                if clsid:
                    yield name, clsid, int(num)

    def test_no_authored_store_is_a_stock_store(self) -> None:
        foreign = [(n, c, s) for n, c, s in self._stores() if "SUPERHORNET" not in c]
        assert not foreign, (
            "stock stores authored on a CJS jet -- DCS will drop these and the "
            f"pylon will spawn empty: {foreign[:8]}"
        )

    def test_the_centreline_tgp_is_the_mods_own(self) -> None:
        """The specific store behind the reported empty centre-line."""
        stores = {(n, c, s) for n, c, s in self._stores()}
        assert not [x for x in stores if x[1].startswith("{A111396E")]
        assert any(
            c == "{SUPERHORNET_PYLON_06_CN_TP_AAQ28}" for _, c, _ in stores
        ), "the DEAD/OCA fits should carry the mod's own centre-line pod"

    def test_every_authored_store_is_registered_in_the_weapon_data(self) -> None:
        """Anything we newly point at must be date-gated, not ungated.

        An unregistered clsid falls through ``register_unknown_weapons`` to
        ``introduction_year=None``, which ``Weapon.available_on`` reads as
        "available in every era with no fallback" -- the hole #771 closed for the
        modern AMRAAMs. Fuel tanks and the JSOW rack are pre-existing exceptions
        (era-agnostic hardware).
        """
        from game.data.weapons import Weapon, WeaponGroup

        WeaponGroup.load_all()
        unregistered = set()
        for _, clsid, _ in self._stores():
            weapon = Weapon.with_clsid(clsid)
            group = getattr(weapon, "weapon_group", None)
            if getattr(group, "name", None) in (None, "Unknown"):
                unregistered.add(clsid)
        # Tanks / racks are allowed to be unregistered; ordnance is not.
        offenders = {
            c
            for c in unregistered
            if "_FT_" not in c and "FT_AUX" not in c and "BRU55" not in c
        }
        assert not offenders, f"unregistered ordnance: {sorted(offenders)}"
