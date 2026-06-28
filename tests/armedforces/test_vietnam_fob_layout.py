"""The Vietnam factions render the themed ``vietnam_fob`` FOB layout deterministically,
while other factions keep the stock ``fob1`` -- verifying the faction
``excluded_generic_layouts`` / ``extra_layouts`` opt-out/opt-in mechanism.
"""

import pytest

from game import persistency
from game.armedforces.armedforces import ArmedForces
from game.data.groups import GroupTask
from game.factions.factionloader import FactionLoader
from game.layout import LAYOUTS


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    # Layout/faction loading reads the DCS saved-game folder; point it at an empty
    # temp dir so loading falls back to the bundled resources/ files.
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


def _fob_layout_names(faction_name: str) -> set[str]:
    faction = FactionLoader()[faction_name]
    armed_forces = ArmedForces(faction)
    names: set[str] = set()
    for group in armed_forces.groups_for_task(GroupTask.FOB):
        names.update(layout.name for layout in group.layouts)
    return names


@pytest.mark.parametrize(
    "faction_name", ["USA 1970 Vietnam War", "NVA 1970", "Vietnam 1965"]
)
def test_vietnam_factions_render_only_vietnam_fob(faction_name: str) -> None:
    names = _fob_layout_names(faction_name)
    assert names == {"vietnam_fob"}, names


def test_non_vietnam_faction_keeps_stock_fob() -> None:
    names = _fob_layout_names("Bluefor Coldwar")
    assert names == {"fob1"}, names


def test_vietnam_fob_is_non_generic_so_it_cannot_leak() -> None:
    # Non-generic means it is never auto-added to a faction; only the factions that
    # opt in via extra_layouts get it, so it can't appear in other campaigns.
    layout = next(layout for layout in LAYOUTS.layouts if layout.name == "vietnam_fob")
    assert not layout.generic


def test_vietnam_fob_renders_non_empty_for_a_vietnam_faction() -> None:
    from game.armedforces.forcegroup import ForceGroup

    faction = FactionLoader()["USA 1970 Vietnam War"]
    layout = next(layout for layout in LAYOUTS.layouts if layout.name == "vietnam_fob")
    assert layout.usable_by_faction(faction)
    group = ForceGroup.for_layout(layout, faction)
    assert group.units or group.statics
