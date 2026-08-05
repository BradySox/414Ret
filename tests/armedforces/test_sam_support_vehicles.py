"""SAM batteries field their support section: cargo trucks, fuel bowsers, power.

Background (2026-08-04). A textbook SA-10 site is not just radars and launchers --
it carries a refuelling section and the 5I57A diesel power stations that run the
battery. Retribution modelled none of it, for three compounding reasons:

1. No refueller had a unit yaml at all, so `ATZ-10` and friends were never
   `GroundUnitType`s, never in `Faction.accessible_units`, and therefore always
   rejected by `Faction.has_access_to_dcs_type`. They existed only in
   `tgogenerator`'s hardcoded FARP/airfield ground-support pool, which bypasses
   the unit registry -- which is why an ATZ-10 only ever appeared on a ramp.
2. No faction listed one.
3. The S-300 family's `S-300 Site Logistics` slot was DEAD CONFIG: declared in
   the layout yaml with no matching group in the shared `S-300_Site.miz`.

That third point is the dangerous one and it is what `test_no_layout_declares_a_dead_slot`
guards. `LayoutLoader._load_from_miz` walks the groups in the MIZ and looks each
one up in the mapping; a slot named in the yaml that matches no MIZ group is
never instantiated and is silently ignored -- no warning, no error. The same bug
had also quietly disabled the Sky Sabre battery's point defence, whose slot was
named "Point Defense" against a MIZ group called "PD".
"""

from __future__ import annotations

import itertools
from pathlib import Path

import dcs
import pytest
import yaml

from game import persistency
from game.data.units import UnitClass
from game.dcs.groundunittype import GroundUnitType
from game.layout import LAYOUTS

ANTI_AIR_LAYOUT_DIR = Path("resources/layouts/anti_air")
PRESET_GROUP_DIR = Path("resources/groups")


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    # ForceGroup/layout preset loading reads from the DCS saved-game folder,
    # which is only configured once the app boots. Point it at an empty temp
    # dir so loading falls back to the bundled resources/ presets.
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


# variant_id -> (DCS unit id, unit class). Registering these is what makes them
# reachable by a layout at all; the class is what decides where they can be used
# (Logistics is a front-line-deployable class, Power deliberately is not).
SUPPORT_UNITS = {
    "Refueler ATZ-5": ("ATZ-5", UnitClass.LOGISTICS),
    "Refueler ATZ-10": ("ATZ-10", UnitClass.LOGISTICS),
    "Refueler ATMZ-5": ("ATMZ-5", UnitClass.LOGISTICS),
    "Refueler ATZ-60 (MAZ-7410)": ("ATZ-60_Maz", UnitClass.LOGISTICS),
    "Refueler TZ-22 (KrAZ-258B1)": ("TZ-22_KrAZ", UnitClass.LOGISTICS),
    "Refueler M978 HEMTT": ("M978 HEMTT Tanker", UnitClass.LOGISTICS),
    "Diesel Power Station 5I57A": ("generator_5i57", UnitClass.POWER),
}

# Layouts that must carry a full support section, and the slots each declares.
S300_SUPPORT_SLOTS = {
    "S-300 Site": ("S-300 Site Logistics", "S-300 Site Fuel", "S-300 Site Power"),
    "S-300 Site (Single Radar)": (
        "S-300 Site Logistics",
        "S-300 Site Fuel",
        "S-300 Site Power",
    ),
    # No power slot: the 5I57A is S-300 kit, not SA-2/SA-3 kit.
    "SA-2/SA-3 Mixed Site": ("S-300 Site Logistics", "S-300 Site Fuel"),
}


@pytest.mark.parametrize("variant_id,expected", sorted(SUPPORT_UNITS.items()))
def test_support_vehicle_is_registered(
    variant_id: str, expected: tuple[str, UnitClass]
) -> None:
    """Without a yaml the unit is not a GroundUnitType and no layout can use it."""
    dcs_id, unit_class = expected
    unit = GroundUnitType.named(variant_id)
    assert unit.dcs_unit_type.id == dcs_id
    assert unit.unit_class is unit_class


def test_power_units_are_never_deployed_to_a_front_line() -> None:
    """A diesel generator must not march to the FLOT.

    `UnitClass.LOGISTICS` is in the ground planner's deployable set (the fuel
    bowsers ride along with the cargo trucks, which is realistic and matches the
    existing Ural/M818 behaviour). `UnitClass.POWER` must stay out of it.
    """
    from game.data.units import FRONTLINE_UNIT_CLASSES
    from game.ground_forces.ai_ground_planner import _DEPLOYABLE_UNIT_CLASSES

    assert UnitClass.POWER not in FRONTLINE_UNIT_CLASSES
    assert UnitClass.POWER not in _DEPLOYABLE_UNIT_CLASSES


@pytest.mark.parametrize("layout_name,slots", sorted(S300_SUPPORT_SLOTS.items()))
def test_sam_layout_declares_its_support_slots(
    layout_name: str, slots: tuple[str, ...]
) -> None:
    layout = LAYOUTS.by_name(layout_name)
    present = {ug.name for ug in layout.all_unit_groups}
    for slot in slots:
        assert slot in present, f"{layout_name} lost its {slot!r} slot"


@pytest.mark.parametrize("layout_name,slots", sorted(S300_SUPPORT_SLOTS.items()))
def test_support_slots_have_positions_in_the_template(
    layout_name: str, slots: tuple[str, ...]
) -> None:
    """A declared slot is worthless without positions in the shared .miz.

    `generate_units` is hard-capped at the template's position count, so a slot
    asking for 2 units needs at least 2 units in its MIZ group.
    """
    layout = LAYOUTS.by_name(layout_name)
    for slot in slots:
        for unit_group in [ug for ug in layout.all_unit_groups if ug.name == slot]:
            assert len(unit_group.layout_units) >= max(unit_group.unit_count), (
                f"{layout_name}/{slot} wants {max(unit_group.unit_count)} units but "
                f"the template only carries {len(unit_group.layout_units)} positions"
            )


def test_fuel_and_power_are_separate_slots() -> None:
    """A unit group fields ONE type, so a merged slot could never yield both.

    If these were ever folded into one slot an S-300 site would generate two
    bowsers or two generators, never one of each.
    """
    layout = LAYOUTS.by_name("S-300 Site")
    fuel = [ug for ug in layout.all_unit_groups if ug.name == "S-300 Site Fuel"]
    power = [ug for ug in layout.all_unit_groups if ug.name == "S-300 Site Power"]
    assert len(fuel) == 1 and len(power) == 1
    fuel_types = {t.id for t in fuel[0].unit_types}
    power_types = {t.id for t in power[0].unit_types}
    assert not fuel_types & power_types
    assert power_types == {"generator_5i57"}
    assert "ATZ-10" in fuel_types


# --- The 2026-08-04 wiring pass: most-touched content actually fields the kit ---

# The dedicated legacy Soviet layouts (Red Tide's front belt, Vietnam, Desert
# Storm, the COIN crust) carry the 1960s refuellers in their existing Logistics
# whitelist. One slot rolls ONE type, so a site fields trucks OR a bowser.
DEDICATED_LEGACY_LAYOUTS = [
    "SA-2 Battery (4 Launcher Circle)",
    "SA-2 Battery (4 Launcher Semicircle)",
    "SA-2 Battery (6 Launcher Circle)",
    "SA-2 Battery (6 Launcher Semicircle)",
    "SA-3 Site (4 Launcher Circle)",
    "SA-3 Site (4 Launcher Semicircle)",
    "SA-5 Legacy Site (Circle)",
    "SA-5 Legacy Site (Semicircle)",
    "SA-5 Legacy Site (Single Radar Circle)",
    "SA-5 Legacy Site (Single Radar Semicircle)",
    "SA-6 Reinforced Site (Circle)",
    "SA-6 Reinforced Site (Semicircle)",
]
SIXTIES_FUEL_TRIO = {"ATZ-5", "ATZ-60_Maz", "TZ-22_KrAZ"}


@pytest.mark.parametrize("layout_name", DEDICATED_LEGACY_LAYOUTS)
def test_legacy_sam_logistics_whitelist_offers_fuel(layout_name: str) -> None:
    """The dedicated layouts whitelist Logistics by unit_types, so refuellers
    reach those sites only if listed. The trucks must survive alongside them --
    the addition must never displace the cargo trucks from the roll."""
    layout = LAYOUTS.by_name(layout_name)
    slots = [ug for ug in layout.all_unit_groups if ug.name == "Logistics"]
    assert len(slots) == 1, f"{layout_name} lost its Logistics slot"
    types = {t.id for t in slots[0].unit_types}
    assert SIXTIES_FUEL_TRIO <= types, f"{layout_name} lost its refuelling section"
    assert (
        "GAZ-66" in types or "Ural-375" in types
    ), f"{layout_name}: the fuel addition displaced the cargo trucks"


# Era-correct refuellers on the active campaigns' factions. The faction loader
# SILENTLY DROPS unknown unit strings, so this asserts each addition actually
# resolved into the faction -- a typo would otherwise vanish without a trace.
FACTION_REFUELLERS = {
    "Russia 1980 (Red Tide)": {
        "Refueler ATZ-5",
        "Refueler ATZ-60 (MAZ-7410)",
        "Refueler TZ-22 (KrAZ-258B1)",
        "Refueler ATMZ-5",
        "Refueler ATZ-10",
    },
    "Blufor Late Cold War (80s)": {"Refueler M978 HEMTT"},
    "Vietnam 1970": {
        "Refueler ATZ-5",
        "Refueler ATZ-60 (MAZ-7410)",
        "Refueler TZ-22 (KrAZ-258B1)",
    },
    "Iraq 1991": {"Refueler ATZ-10", "Refueler ATMZ-5"},
    "NATO Desert Storm": {"Refueler M978 HEMTT"},
    "OEF Coalition 2006": {"Refueler M978 HEMTT"},
    "Toyota Al Gaib 2001": {"Refueler ATZ-5 civil"},
    "CJTF-OIR 2016": {"Refueler M978 HEMTT"},
    "Islamic State 2016": {"Refueler ATZ-5 civil"},
    "USA 2020": {"Refueler M978 HEMTT"},
}


@pytest.mark.parametrize("faction_name,expected", sorted(FACTION_REFUELLERS.items()))
def test_active_campaign_faction_rosters_its_refuellers(
    faction_name: str, expected: set[str]
) -> None:
    from game.factions import FACTIONS

    faction = FACTIONS[faction_name]
    have = {unit.variant_id for unit in faction.logistics_units}
    missing = expected - have
    assert not missing, (
        f"{faction_name} silently dropped {sorted(missing)} -- the loader ignores "
        f"unknown unit strings, so check the variant_id spelling"
    )


@pytest.mark.parametrize("preset_name", ["SA-2/S-75 with ZSU-23/57", "HQ-2"])
def test_c2less_generic_presets_carry_the_kung(preset_name: str) -> None:
    """SA-2_ZSU and HQ-2 bind generic launcher layouts whose Command Post slot is
    fill:false -- only preset-carried CommandPost units render there. These two
    families have no organic C2 unit, so the ZIL-131 KUNG is theirs; without it
    the slot is dormant forever. SA-11/SA-17/Hawk keep their real C2 instead.
    """
    from game.armedforces.forcegroup import ForceGroup

    group = ForceGroup.from_preset_group(preset_name)
    cp_units = [u for u in group.units if u.unit_class is UnitClass.COMMAND_POST]
    assert [u.dcs_unit_type.id for u in cp_units] == ["ZIL-131 KUNG"]
    layout = LAYOUTS.by_name(group.layouts[0].name)
    cp_slots = [ug for ug in layout.all_unit_groups if ug.name == "Command Post"]
    assert cp_slots, "the generic layout lost its Command Post slot"
    offered = group.dcs_unit_types_for_group(cp_slots[0])
    assert [t.id for t in offered] == ["ZIL-131 KUNG"]


def _preset_groups_bound_to(layout_name: str) -> list[Path]:
    hits = []
    for path in sorted(PRESET_GROUP_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if layout_name in (data.get("layouts") or []):
            hits.append(path)
    return hits


@pytest.mark.parametrize("layout_name", sorted(S300_SUPPORT_SLOTS))
def test_preset_groups_grant_access_to_their_support_units(layout_name: str) -> None:
    """`has_access_to_dcs_type` gates every slot, so the preset must carry them.

    Same pattern the Patriot already uses: MIM-104_Patriot_Stationary.yaml lists
    its own EPP (class Power) and a support truck in `units:`. Listing them on the
    preset means no faction json has to change.
    """
    presets = _preset_groups_bound_to(layout_name)
    assert presets, f"no preset group is bound to {layout_name}"
    wants_power = "S-300 Site Power" in S300_SUPPORT_SLOTS[layout_name]
    for path in presets:
        units = set(yaml.safe_load(path.read_text(encoding="utf-8"))["units"])
        assert "Refueler ATZ-5" in units, f"{path.name} has no fuel bowser"
        assert any(u.startswith("Truck ") for u in units), f"{path.name} has no truck"
        if wants_power:
            assert "Diesel Power Station 5I57A" in units, f"{path.name} has no power"


def _miz_group_names(miz: Path) -> set[str]:
    mission = dcs.Mission()
    mission.load_file(str(miz))
    names = set()
    for coalition in mission.coalition.values():
        for country in coalition.countries.values():
            for group in itertools.chain(
                mission.country(country.name).vehicle_group,
                mission.country(country.name).ship_group,
                mission.country(country.name).static_group,
            ):
                names.add(group.name)
    return names


def _anti_air_layout_yamls() -> list[Path]:
    return sorted(ANTI_AIR_LAYOUT_DIR.glob("*.yaml"))


@pytest.mark.parametrize("layout_yaml", _anti_air_layout_yamls(), ids=lambda p: p.name)
def test_no_layout_declares_a_dead_slot(layout_yaml: Path) -> None:
    """Every slot a layout declares must exist as a group in its .miz template.

    THE failure mode this whole change came from. `LayoutLoader._load_from_miz`
    iterates the MIZ's groups and looks each up in the mapping -- so a slot the
    yaml declares that no MIZ group is named after is never created, with no
    warning and no error. It had silently disabled the S-300 family's logistics
    section and the Sky Sabre battery's point defence.
    """
    data = yaml.safe_load(layout_yaml.read_text(encoding="utf-8"))
    layout_file = data.get("layout_file")
    miz = Path(layout_file) if layout_file else layout_yaml.with_suffix(".miz")
    assert miz.is_file(), f"{layout_yaml.name} points at a missing template {miz}"

    miz_groups = _miz_group_names(miz)
    declared = [
        slot["name"]
        for group in data["groups"]
        for slots in group.values()
        for slot in slots
    ]
    # A slot may also be satisfied by one of its `statics` entries.
    statics = {
        static
        for group in data["groups"]
        for slots in group.values()
        for slot in slots
        for static in slot.get("statics", [])
    }
    dead = [n for n in declared if n not in miz_groups and n not in statics]
    assert not dead, (
        f"{layout_yaml.name} declares slots with no matching group in {miz.name}: "
        f"{dead}. They will be silently dropped. Groups in the template: "
        f"{sorted(miz_groups)}"
    )


# --- EWR-site support sections (the 2026-08-04 follow-on) ------------------------

# The generic EWR site was a single radar unit -- no C2 shelter, no power, no
# trucks. The template gained three appended groups and the layout three optional
# whitelist slots. Access is gated by the faction's own lists, so the kit is
# nation-correct by construction and a faction with none renders a bare radar.
EWR_LAYOUT = "Early-Warning Radar"
EWR_SUPPORT_SLOTS = (
    "Early-Warning Radar C2",
    "Early-Warning Radar Power",
    "Early-Warning Radar Logistics",
)


def test_ewr_layout_declares_its_support_slots() -> None:
    layout = LAYOUTS.by_name(EWR_LAYOUT)
    present = {ug.name for ug in layout.all_unit_groups}
    for slot in EWR_SUPPORT_SLOTS:
        assert slot in present, f"EWR layout lost its {slot!r} slot"
    for slot in EWR_SUPPORT_SLOTS:
        for unit_group in [ug for ug in layout.all_unit_groups if ug.name == slot]:
            assert len(unit_group.layout_units) >= max(unit_group.unit_count)


def test_ewr_c2_slot_is_a_whitelist_not_a_class() -> None:
    """A class-based C2 slot would pull every CommandPost unit the faction can
    reach -- a Patriot ECS or a Buk CC parked at an EWR site. The whitelist plus
    faction-access gating is what keeps the kit nation-correct."""
    layout = LAYOUTS.by_name(EWR_LAYOUT)
    c2 = [ug for ug in layout.all_unit_groups if ug.name == "Early-Warning Radar C2"]
    assert len(c2) == 1
    assert not c2[0].unit_classes, "the C2 slot must whitelist unit_types only"
    assert {t.id for t in c2[0].unit_types} == {
        "ZIL-131 KUNG",
        "Ural-375 PBU",
        "FPS-117 ECS",
    }


# faction -> (units its EWR C2/Power slots must offer, units they must NOT).
EWR_KIT_BY_FACTION = {
    # Soviet-pattern: KUNG C2 + 5I57 power, never the FPS-117 shelter.
    "Russia 1980 (Red Tide)": ({"ZIL-131 KUNG", "generator_5i57"}, {"FPS-117 ECS"}),
    "Vietnam 1970": ({"ZIL-131 KUNG", "generator_5i57"}, {"FPS-117 ECS"}),
    "Iraq 1991": ({"ZIL-131 KUNG", "generator_5i57"}, {"FPS-117 ECS"}),
    # Western FPS-117 owners: the ECS shelter, never the Soviet kit.
    "Blufor Late Cold War (80s)": ({"FPS-117 ECS"}, {"ZIL-131 KUNG", "generator_5i57"}),
    "NATO Desert Storm": ({"FPS-117 ECS"}, {"ZIL-131 KUNG", "generator_5i57"}),
    "USA 2020": ({"FPS-117 ECS"}, {"ZIL-131 KUNG", "generator_5i57"}),
}


@pytest.mark.parametrize("faction_name,kit", sorted(EWR_KIT_BY_FACTION.items()))
def test_ewr_site_offers_nation_correct_support(
    faction_name: str, kit: tuple[set[str], set[str]]
) -> None:
    from game.armedforces.forcegroup import ForceGroup
    from game.factions import FACTIONS

    wanted, forbidden = kit
    layout = LAYOUTS.by_name(EWR_LAYOUT)
    group = ForceGroup.for_layout(layout, FACTIONS[faction_name])
    offered: set[str] = set()
    for unit_group in layout.all_unit_groups:
        if unit_group.name in ("Early-Warning Radar C2", "Early-Warning Radar Power"):
            offered |= {t.id for t in group.dcs_unit_types_for_group(unit_group)}
    assert wanted <= offered, f"{faction_name} EWR kit missing {wanted - offered}"
    assert (
        not offered & forbidden
    ), f"{faction_name} EWR site offers wrong-nation kit: {offered & forbidden}"


def test_ewr_layout_still_usable_by_a_faction_with_no_support_kit() -> None:
    """The support slots are optional: a faction fielding none of the whitelist
    renders a bare radar exactly as before, and the layout stays usable."""
    from game.factions import FACTIONS

    faction = FACTIONS["Germany 1944"]
    layout = LAYOUTS.by_name(EWR_LAYOUT)
    assert layout.usable_by_faction(faction)
    for unit_group in layout.all_unit_groups:
        if unit_group.name == "Early-Warning Radar C2":
            assert unit_group.possible_types_for_faction(faction) == []
