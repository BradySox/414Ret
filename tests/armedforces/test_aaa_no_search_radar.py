import pytest

from game import persistency
from game.armedforces.forcegroup import ForceGroup
from game.data.units import UnitClass
from game.layout import LAYOUTS


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    # ForceGroup/layout preset loading reads from the DCS saved-game folder,
    # which is only configured once the app boots. Point it at an empty temp
    # dir so loading falls back to the bundled resources/ presets.
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


# Generic AAA sites must be optically-guided guns, so their layouts must not
# auto-fill a SearchRadar. The radar slot stays in the layout (optional) only so
# preset groups that explicitly bring a radar (e.g. the KS-19 Fire Can) can place
# one, but fill is disabled so a generic faction's SAM search radars never bleed
# into a plain AAA site.
@pytest.mark.parametrize("layout_name", ["AAA Site", "Cold War Flak Site"])
def test_aaa_radar_slot_is_not_auto_filled(layout_name: str) -> None:
    layout = LAYOUTS.by_name(layout_name)
    radar_groups = [
        ug for ug in layout.all_unit_groups if UnitClass.SEARCH_RADAR in ug.unit_classes
    ]
    assert radar_groups, f"{layout_name} should still expose a radar slot"
    for ug in radar_groups:
        assert ug.optional, f"{layout_name} radar slot should be optional"
        assert not ug.fill, f"{layout_name} radar slot must not auto-fill a radar"


def test_fire_can_preset_still_keeps_its_radar() -> None:
    # The KS-19 is a genuinely radar-directed gun: it must keep its SON-9 Fire Can
    # because the preset explicitly lists it, even though the shared AAA Site layout
    # no longer auto-fills a radar.
    group = ForceGroup.from_preset_group("KS-19/SON-9")
    assert any(unit.unit_class is UnitClass.SEARCH_RADAR for unit in group.units)


def test_cold_war_flak_is_faction_generic_not_hardcoded_german_88() -> None:
    # The Cold War Flak Site used to hardcode the WWII German 8.8 cm Flak 18 as its
    # main guns for every faction. It is now a generic layout whose gun slots fill
    # from each faction's own AAA pool, so it must be generic and must not pin any
    # specific gun type.
    layout = LAYOUTS.by_name("Cold War Flak Site")
    assert layout.generic, "Cold War Flak Site should be a generic layout"
    gun_groups = [
        ug
        for ug in layout.all_unit_groups
        if UnitClass.AAA in ug.unit_classes and not ug.optional
    ]
    assert gun_groups, "Cold War Flak Site should have faction-filled AAA gun slots"
    for ug in layout.all_unit_groups:
        assert not ug.unit_types, (
            f"{ug.name} pins specific unit types {ug.unit_types}; "
            "the flak site should fill from the faction's AAA pool"
        )
