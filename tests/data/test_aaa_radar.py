from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from game.armedforces.forcegroup import ForceGroup
from game.data.groups import GroupTask
from game.data.units import ANTI_AIR_UNIT_CLASSES, UnitClass
from game.dcs.groundunittype import GroundUnitType
from game.factions.faction import Faction
from game.layout.layout import TgoLayout, TgoLayoutGroup, TgoLayoutUnitGroup

# The two SON-9 "Fire Can" variants are the only stand-alone AAA gun-laying radars.
FIRE_CAN_VARIANTS = ["AAA Fire Can SON-9", "AAA SON-9 Fire Can"]
KS19_GUN_VARIANT = "AAA KS-19 100mm"
S60_GUN_VARIANT = "S-60 57mm"
SAM_SEARCH_RADAR_VARIANT = "SAM Patriot STR"


def _faction_with(*units: GroundUnitType) -> Faction:
    """Minimal Faction stand-in exposing just what the layout code reads."""
    return cast(
        Faction,
        SimpleNamespace(
            name="Test Faction",
            accessible_units=list(units),
            has_access_to_dcs_type=lambda dcs_type: False,
        ),
    )


def _radar_slot() -> TgoLayoutUnitGroup:
    """Mirror the generic AAA radar slot after the fix."""
    return TgoLayoutUnitGroup(
        name="AAA Site Radar",
        layout_units=[],
        unit_classes=[UnitClass.AAA_RADAR],
        optional=True,
        fill=False,
    )


def _gun_slot() -> TgoLayoutUnitGroup:
    return TgoLayoutUnitGroup(
        name="AAA Site",
        layout_units=[],
        unit_classes=[UnitClass.AAA],
    )


def _generic_aaa_site_layout() -> TgoLayout:
    layout = TgoLayout("AAA Site")
    layout.tasks = [GroupTask.AAA]
    layout.generic = True
    layout.groups = [
        TgoLayoutGroup(
            group_name="AAA",
            group_index=0,
            unit_groups=[_radar_slot(), _gun_slot()],
        )
    ]
    return layout


def test_fire_can_radars_are_aaa_radar() -> None:
    for variant in FIRE_CAN_VARIANTS:
        assert GroundUnitType.named(variant).unit_class is UnitClass.AAA_RADAR


def test_aaa_radar_is_still_anti_air() -> None:
    # Reclassifying must not drop the Fire Can from anti-air handling.
    assert UnitClass.AAA_RADAR in ANTI_AIR_UNIT_CLASSES


def test_sam_search_radar_class_unchanged() -> None:
    # Negative case: SAM search radars stay SearchRadar.
    assert GroundUnitType.named(SAM_SEARCH_RADAR_VARIANT).unit_class is (
        UnitClass.SEARCH_RADAR
    )


def test_generic_aaa_site_never_gets_a_fire_can() -> None:
    # A faction with a Fire Can and a non-KS-19 gun must NOT produce a generic AAA
    # site pairing them: the radar slot does not auto-fill.
    fire_can = GroundUnitType.named(FIRE_CAN_VARIANTS[0])
    s60 = GroundUnitType.named(S60_GUN_VARIANT)
    faction = _faction_with(fire_can, s60)

    force_group = ForceGroup.for_layout(_generic_aaa_site_layout(), faction)

    assert s60 in force_group.units
    assert fire_can not in force_group.units


def test_bundled_ks19_preset_pairs_fire_can_with_ks19() -> None:
    # The preset path (KS-19 + SON-9 bundled) still pairs them.
    fire_can = GroundUnitType.named(FIRE_CAN_VARIANTS[0])
    ks19 = GroundUnitType.named(KS19_GUN_VARIANT)
    force_group = ForceGroup(
        name="KS-19/SON-9",
        units=[fire_can, ks19],
        statics=[],
        tasks=[GroupTask.AAA],
        layouts=[],
    )

    assert force_group.dcs_unit_types_for_group(_radar_slot()) == [
        fire_can.dcs_unit_type
    ]
    assert ks19.dcs_unit_type in force_group.dcs_unit_types_for_group(_gun_slot())


def test_non_ks19_bundle_gets_no_fire_can() -> None:
    # A group with only non-KS-19 guns has nothing to offer the radar slot.
    s60 = GroundUnitType.named(S60_GUN_VARIANT)
    force_group = ForceGroup(
        name="S-60",
        units=[s60],
        statics=[],
        tasks=[GroupTask.AAA],
        layouts=[],
    )

    assert force_group.dcs_unit_types_for_group(_radar_slot()) == []
