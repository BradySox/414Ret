"""No faction may keep a mod preset group when that mod is disabled.

Regression lock for the 2026-07-12 Red Tide finding: the fork faction's new
``SA-10A/S-300PT (Single Radar)`` preset survived a no-mod game because
``Faction.apply_mod_settings`` strips preset groups by an exact-name list and
nobody added the new name. The leaked group offered High Digit SAMs units in
the buy menu and the AI procurement pool of a vanilla game -- and a generated
``.miz`` carrying them would not load for clients without the mod installed.

``apply_mod_settings`` now carries a provenance backstop that strips any
preset group containing a unit from a disabled ``pydcs_extensions`` package,
regardless of the preset's name. These tests walk every shipped faction so a
renamed or newly-authored preset can't reintroduce the leak.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from game import persistency
from game.factions.faction import Faction
from game.theater.start_generator import ModSettings

FACTIONS_DIR = Path("resources/factions")
RED_TIDE_FACTION = FACTIONS_DIR / "russia_1980_red_tide.json"


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    # Unit-type loading reads user overrides from the DCS saved-game folder,
    # which is only configured once the app boots. Point it at an empty temp
    # dir so loading falls back to the bundled resources/ data.
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


def _load(path: Path) -> Faction:
    with path.open(encoding="utf-8") as data:
        return Faction.from_dict(json.load(data))


def _mod_preset_packages(faction: Faction) -> dict[str, set[str]]:
    """Preset-group name -> the pydcs_extensions packages its units come from."""
    result: dict[str, set[str]] = {}
    for preset_group in faction.preset_groups:
        packages = {
            unit.dcs_unit_type.__module__.split(".")[1]
            for unit in preset_group.units
            if unit.dcs_unit_type.__module__.startswith("pydcs_extensions.")
        }
        if packages:
            result[preset_group.name] = packages
    return result


def test_no_shipped_faction_keeps_mod_presets_with_mods_off() -> None:
    for path in sorted(FACTIONS_DIR.glob("*.json")):
        faction = _load(path)
        faction.apply_mod_settings(ModSettings.all_off())
        leaks = _mod_preset_packages(faction)
        assert (
            not leaks
        ), f"{path.name} keeps mod preset group(s) with all mods off: {leaks}"


def test_cjs_super_hornet_defaults_off() -> None:
    """DM call 2026-07-21 (revised): the CJS Super Hornet pack (FA-18E/F, EA-18G,
    ET/FT tankers) defaults OFF -- forcing a mod on every client was the wrong
    lever. Escort jamming (§77) is instead available to a curated set of *vanilla*
    EW jets, so the Growler is the DM's opt-in premium tier, not a forced default.
    all_off() must still produce a genuinely mod-free baseline."""
    defaults = ModSettings()
    assert not defaults.fa_18efg
    assert not defaults.fa18ef_tanker
    off = ModSettings.all_off()
    assert not off.fa_18efg
    assert not off.fa18ef_tanker


def test_red_tide_faction_is_pure_vanilla_with_mods_off() -> None:
    """The squadron's campaign runs no mods: with everything off, every unit
    reachable from the fork faction (roster and presets) must be base DCS."""
    faction = _load(RED_TIDE_FACTION)
    faction.apply_mod_settings(ModSettings.all_off())
    offenders = sorted(
        unit.variant_id
        for unit in faction.accessible_units
        if not unit.dcs_unit_type.__module__.startswith("dcs.")
    )
    assert offenders == []
