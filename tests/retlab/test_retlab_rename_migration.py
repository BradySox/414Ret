"""The package rebrand must not cost a save.

``game/fourteenth`` became ``game/retlab`` when the fork dropped the squadron
branding. Pickle stores the module path, and three of the package's classes reach
a save through objects that are always persisted -- so without the remap every
campaign saved before the rename fails to load in find_class, long before any
__setstate__ could help.
"""

import io

from game.persistency import DummyObject, MigrationUnpickler
from game.retlab.region_priorities import RegionPriority
from game.retlab.victory import VictoryBaseline


def _global_pickle(module: str, name: str) -> bytes:
    """A protocol-2 pickle whose whole payload is one GLOBAL lookup."""
    return b"\x80\x02c" + module.encode() + b"\n" + name.encode() + b"\n."


def _load(module: str, name: str) -> object:
    return MigrationUnpickler(io.BytesIO(_global_pickle(module, name))).load()


def test_legacy_module_path_resolves_to_the_renamed_package() -> None:
    assert _load("game.fourteenth.region_priorities", "RegionPriority") is (
        RegionPriority
    )
    assert _load("game.fourteenth.victory", "VictoryBaseline") is VictoryBaseline


def test_current_module_path_still_resolves() -> None:
    assert _load("game.retlab.region_priorities", "RegionPriority") is RegionPriority


def test_tombstoned_modules_keep_the_pre_rename_path() -> None:
    # Removed while the package was still named fourteenth, so the old path is the
    # only one a pickle can carry. The remap must not reach them first.
    assert _load("game.fourteenth.wing_growth", "ScheduledSquadron") is DummyObject
    assert _load("game.fourteenth.war_economy", "WarEconomy") is DummyObject
