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
def test_legacy_sam_fields_the_truck_and_fuel_spread(layout_name: str) -> None:
    """Trucks AND fuel, in separate slots (the S-300 spread, extended to the
    legacy families in the 'do them all' pass).

    The Logistics whitelist must stay TRUCKS-ONLY: a bowser in that whitelist
    makes `has_unit_for_layout_group` skip the faction truck fill (a fuel unit
    satisfies the slot), which is exactly the trucks-OR-fuel behaviour this
    pass replaced. The trio lives in the dedicated Fuel slot instead --
    fill:false, preset-carried, era-safe for every legacy campaign."""
    layout = LAYOUTS.by_name(layout_name)
    logistics = [ug for ug in layout.all_unit_groups if ug.name == "Logistics"]
    assert len(logistics) == 1, f"{layout_name} lost its Logistics slot"
    truck_types = {t.id for t in logistics[0].unit_types}
    assert not truck_types & SIXTIES_FUEL_TRIO, (
        f"{layout_name}: bowsers back in the Logistics whitelist -- this "
        f"reintroduces trucks-OR-fuel and displaces the faction truck fill"
    )
    assert "GAZ-66" in truck_types or "Ural-375" in truck_types

    fuel = [ug for ug in layout.all_unit_groups if ug.name == "Fuel"]
    assert len(fuel) == 1, f"{layout_name} has no Fuel slot"
    assert fuel[0].optional and not fuel[0].fill
    assert {t.id for t in fuel[0].unit_types} == SIXTIES_FUEL_TRIO
    assert len(fuel[0].layout_units) >= max(fuel[0].unit_count)


GENERIC_LAUNCHER_LAYOUTS = [
    "4 Launcher Site (Circle)",
    "4 Launcher Site (Semicircle)",
    "6 Launcher Site (Circle)",
    "6 Launcher Site (Semicircle)",
]


@pytest.mark.parametrize("layout_name", GENERIC_LAUNCHER_LAYOUTS)
def test_generic_launcher_site_has_a_fuel_slot(layout_name: str) -> None:
    layout = LAYOUTS.by_name(layout_name)
    fuel = [ug for ug in layout.all_unit_groups if ug.name == "Fuel"]
    assert len(fuel) == 1, f"{layout_name} has no Fuel slot"
    assert fuel[0].optional and not fuel[0].fill
    assert len(fuel[0].layout_units) >= max(fuel[0].unit_count)


# Every legacy/generic family preset carries its own trucks + bowsers now (the
# S-300 pattern), so both the Logistics and the Fuel slot resolve family-wide.
PRESET_SUPPORT_KIT = {
    "SA-2/S-75": {"Truck GAZ-66", "Refueler ATZ-5"},
    "SA-2/S-75 with ZSU-23/57": {"Truck GAZ-66", "Refueler ATZ-5"},
    "SA-3/S-125": {"Truck GAZ-66", "Refueler ATZ-5"},
    "SA-5/S-200": {"Truck GAZ-66", "Refueler TZ-22 (KrAZ-258B1)"},
    "SA-5/S-200 (Single Radar)": {"Truck GAZ-66", "Refueler TZ-22 (KrAZ-258B1)"},
    "SA-6": {"Truck GAZ-66", "Refueler ATZ-5"},
    "HQ-2": {"Truck GAZ-66", "Refueler ATZ-5"},
    "SA-11": {"Truck KAMAZ 43101", "Refueler ATZ-10"},
    "SA-17": {"Truck KAMAZ 43101", "Refueler ATZ-10"},
    "Hawk": {"Truck M818 6x6", "Refueler M978 HEMTT"},
    # DM call 2026-08-04: China runs the Soviet fuel kit.
    "HQ-22": {"Truck KAMAZ 43101", "Refueler ATZ-10", "Diesel Power Station 5I57A"},
}


@pytest.mark.parametrize("preset_name,expected", sorted(PRESET_SUPPORT_KIT.items()))
def test_family_preset_carries_its_support_kit(
    preset_name: str, expected: set[str]
) -> None:
    from game.armedforces.forcegroup import ForceGroup

    group = ForceGroup.from_preset_group(preset_name)
    have = {u.variant_id for u in group.units}
    missing = expected - have
    assert not missing, f"{preset_name} is missing {sorted(missing)}"


def test_hq22_battery_declares_the_s300_support_slots() -> None:
    """China's HQ-22 uses the shared S-300 template, whose support groups have
    existed since §85 -- the slots just needed declaring."""
    layout = LAYOUTS.by_name("HQ-22 Battery")
    present = {ug.name for ug in layout.all_unit_groups}
    for slot in ("S-300 Site Logistics", "S-300 Site Fuel", "S-300 Site Power"):
        assert slot in present, f"HQ-22 Battery lost its {slot!r} slot"


# The Gazetchik-E decoy is an HDS MOD unit (pydcs_extensions/highdigitsams), so
# it may ride only the already-HDS-gated modern S-300 presets -- a vanilla game
# must never see it. SA-10/SA-10B/SA-12 and the single-radar preset (Red Tide's)
# stay decoy-free: era and vanilla-satefy both.
DECOY_PRESETS = [
    "SA-20/S-300PMU-1",
    "SA-20B/S-300PMU-2",
    "SA-21/S-400",
    "SA-23/S-300VM",
    "SA-23B/S-300V4",
]
NO_DECOY_PRESETS = ["SA-10/S-300PS", "SA-10B/S-300PS", "SA-10/S-300PS (Single Radar)"]


def _preset_names() -> set[str]:
    names = set()
    for path in sorted(PRESET_GROUP_DIR.glob("*.yaml")):
        names.add(yaml.safe_load(path.read_text(encoding="utf-8"))["name"])
    return names


def test_gazetchik_decoy_rides_only_hds_gated_presets() -> None:
    from game.armedforces.forcegroup import ForceGroup

    all_names = _preset_names()
    for name in DECOY_PRESETS:
        if name not in all_names:
            # Preset display names can drift; fail loudly rather than skip.
            raise AssertionError(
                f"decoy preset {name!r} not found in {sorted(all_names)}"
            )
        group = ForceGroup.from_preset_group(name)
        assert "EW 34Ya6E Gazetchik-E Decoy" in {u.variant_id for u in group.units}
    for name in NO_DECOY_PRESETS:
        if name not in all_names:
            continue
        group = ForceGroup.from_preset_group(name)
        assert "EW 34Ya6E Gazetchik-E Decoy" not in {u.variant_id for u in group.units}


def test_s300_layout_offers_the_decoy_to_a_carrying_preset() -> None:
    from game.armedforces.forcegroup import ForceGroup

    group = ForceGroup.from_preset_group("SA-20/S-300PMU-1")
    layout = LAYOUTS.by_name(group.layouts[0].name)
    decoy = [ug for ug in layout.all_unit_groups if ug.name == "S-300 Site Decoy"]
    assert len(decoy) == 1
    offered = [t.id for t in group.dcs_unit_types_for_group(decoy[0])]
    assert offered == ["34Ya6E Gazetchik E decoy"]


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


def _all_layout_yamls() -> list[Path]:
    """Every layout family, not just anti-air -- the dead-slot bug is generic."""
    return sorted(Path("resources/layouts").rglob("*.yaml"))


@pytest.mark.parametrize("layout_yaml", _all_layout_yamls(), ids=lambda p: p.name)
def test_no_layout_declares_a_dead_slot(layout_yaml: Path) -> None:
    """Every slot a layout declares must exist as a group in its .miz template.

    THE failure mode this whole change came from. `LayoutLoader._load_from_miz`
    iterates the MIZ's red+blue groups and looks each up in the mapping -- so a
    slot the yaml declares that no MIZ group is named after is never created,
    with no warning and no error. It had silently disabled the S-300 family's
    logistics section and the Sky Sabre battery's point defence. The loader
    matches a MIZ group against either the slot's own name or an entry in the
    slot's `statics` list (the building layouts are carried entirely by their
    statics), so a slot is alive if any of those names exists as a group. The
    red+blue restriction matters too: a group parked in the NEUTRALS block is
    invisible to the loader (found the hard way -- pydcs seeds unused countries
    into neutrals, and a support group added under one never loaded).
    """
    data = yaml.safe_load(layout_yaml.read_text(encoding="utf-8"))
    layout_file = data.get("layout_file")
    miz = Path(layout_file) if layout_file else layout_yaml.with_suffix(".miz")
    assert miz.is_file(), f"{layout_yaml.name} points at a missing template {miz}"

    miz_groups = _miz_group_names(miz)
    dead = []
    for group in data["groups"]:
        for slots in group.values():
            for slot in slots:
                candidates = {slot["name"], *slot.get("statics", [])}
                if not candidates & miz_groups:
                    dead.append(slot["name"])
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


# --- Economy building furnishing (the 2026-08-04 "Ammo, Factory, anything" pass) --

# The fuel farm, ammo depot, factory and warehouse were pure static dioramas --
# eight fuel tanks and not one bowser. Each now carries one optional Logistics
# vehicle group dealt from the faction's own roster.
FURNISHED_BUILDINGS = ["fuel1", "ammo1", "ware1", "factory1"]


@pytest.mark.parametrize("layout_name", FURNISHED_BUILDINGS)
def test_economy_building_has_a_logistics_slot(layout_name: str) -> None:
    layout = LAYOUTS.by_name(layout_name)
    slots = [
        ug for ug in layout.all_unit_groups if ug.name == f"{layout_name} Logistics"
    ]
    assert len(slots) == 1, f"{layout_name} lost its Logistics slot"
    slot = slots[0]
    assert slot.optional, "must be optional: a truck-less faction keeps bare statics"
    assert UnitClass.LOGISTICS in slot.unit_classes, (
        "class-based on purpose -- the faction's own trucks deal in, so the kit "
        "is nation-correct with zero per-faction wiring"
    )
    assert len(slot.layout_units) >= max(slot.unit_count)


@pytest.mark.parametrize("layout_name", FURNISHED_BUILDINGS)
def test_economy_building_origin_still_anchors_on_the_building(
    layout_name: str,
) -> None:
    """The template origin must stay on the layout's first static.

    The loader anchors a layout on the first unit of the first matched group,
    iterating vehicle groups before statics within a country. A vehicle group
    added under the wrong country steals the origin, and every authored
    building position on every campaign shifts by the vehicle's offset. The
    origin unit's relative offset is (0,0) by construction -- pin it.
    """
    layout = LAYOUTS.by_name(layout_name)
    first = layout.groups[0].unit_groups[0].layout_units[0]
    assert abs(first.position.x) < 0.5 and abs(first.position.y) < 0.5, (
        f"{layout_name}'s template origin moved off its first static -- the "
        f"support vehicle group is being loaded before the statics"
    )


def test_furnished_building_offers_the_faction_roster() -> None:
    from game.armedforces.forcegroup import ForceGroup
    from game.factions import FACTIONS

    layout = LAYOUTS.by_name("fuel1")
    group = ForceGroup.for_layout(layout, FACTIONS["Russia 1980 (Red Tide)"])
    slot = [ug for ug in layout.all_unit_groups if ug.name == "fuel1 Logistics"][0]
    offered = {t.id for t in group.dcs_unit_types_for_group(slot)}
    assert "ATZ-10" in offered, "the fuel farm cannot roll a fuel bowser"
    assert "Ural-375" in offered


# --- C2 compound furnishing (comms + command center; DM call 2026-08-04) ---------

# The §51/§52 SEMANTICS CHANGE IS DELIBERATE and these tests document it: the
# comms-jam emitter transmits from every ALIVE unit of a node, §70 counts a
# source alive while any unit lives, and §52 counts a command center alive
# while any unit lives -- so with the compound furnished, killing the building
# alone no longer silences/decapitates the site. The surviving comms van keeps
# transmitting; full decapitation must kill the C2 vehicles too.
C2_BUILDINGS = {
    "comms": ("comms1 C2", "comms1 Power", "comms1 Logistics"),
    "command_center": (
        "CommandCenter C2",
        "CommandCenter Power",
        "CommandCenter Logistics",
    ),
}


@pytest.mark.parametrize("layout_name,slots", sorted(C2_BUILDINGS.items()))
def test_c2_building_declares_its_compound(
    layout_name: str, slots: tuple[str, ...]
) -> None:
    layout = LAYOUTS.by_name(layout_name)
    present = {ug.name for ug in layout.all_unit_groups}
    for slot in slots:
        assert slot in present, f"{layout_name} lost its {slot!r} slot"
    for unit_group in layout.all_unit_groups:
        if unit_group.name in slots:
            assert unit_group.optional
            assert len(unit_group.layout_units) >= max(unit_group.unit_count)
            if "C2" in unit_group.name or "Power" in unit_group.name:
                assert unit_group.unit_types and not unit_group.unit_classes, (
                    f"{unit_group.name} must whitelist unit_types -- a class-based "
                    f"slot would pull wrong-nation or wrong-role CommandPost units"
                )


@pytest.mark.parametrize("layout_name", sorted(C2_BUILDINGS))
def test_c2_building_origin_still_anchors_on_the_building(layout_name: str) -> None:
    layout = LAYOUTS.by_name(layout_name)
    first = layout.groups[0].unit_groups[0].layout_units[0]
    assert abs(first.position.x) < 0.5 and abs(first.position.y) < 0.5


def test_command_center_kit_is_nation_and_era_correct() -> None:
    from game.armedforces.forcegroup import ForceGroup
    from game.factions import FACTIONS

    layout = LAYOUTS.by_name("command_center")
    c2_slot = [ug for ug in layout.all_unit_groups if ug.name == "CommandCenter C2"][0]

    # Red Tide (1988): the full kit including the GCI station shelter.
    rt = ForceGroup.for_layout(layout, FACTIONS["Russia 1980 (Red Tide)"])
    rt_offered = {t.id for t in rt.dcs_unit_types_for_group(c2_slot)}
    assert "GCI_station_MiG29" in rt_offered

    # Vietnam 1970: the GCI station is 1980s kit and must NOT appear; the
    # PBU (1961) carries the era.
    vn = ForceGroup.for_layout(layout, FACTIONS["Vietnam 1970"])
    vn_offered = {t.id for t in vn.dcs_unit_types_for_group(c2_slot)}
    assert "GCI_station_MiG29" not in vn_offered
    assert "Ural-375 PBU" in vn_offered

    # USA 2020: the western kit (fire-control bunker + Predator GCS), and
    # never the Soviet shelters.
    us = ForceGroup.for_layout(layout, FACTIONS["USA 2020"])
    us_offered = {t.id for t in us.dcs_unit_types_for_group(c2_slot)}
    assert us_offered == {"fire_control", "Predator GCS"}
    assert not us_offered & {"GCI_station_MiG29", "ZIL-131 KUNG", "Ural-375 PBU"}


def test_china_2027_rosters_the_soviet_fuel_kit() -> None:
    """DM call 2026-08-04: 'China totally has refuelers or can use Soviet
    stuff' -- the PLA runs the Soviet bowsers in convoys and at its sites."""
    from game.factions import FACTIONS

    faction = FACTIONS["China 2027"]
    have = {u.variant_id for u in faction.logistics_units}
    assert {"Refueler ATZ-10", "Refueler ATZ-5"} <= have


def test_western_factions_reach_their_c2_kit() -> None:
    """The registered US C2 kit (fire-control bunker, Predator GCS + Trojan
    Spirit) is access-gated like the Soviet shelters; era decides who gets the
    Predator vans (1995+ only)."""
    from game.factions import FACTIONS

    modern = {u.variant_id for u in FACTIONS["USA 2020"].air_defense_units}
    assert {
        "C2 Fire Control Bunker",
        "C2 Predator UAV Comms Link",
        "C2 Predator UAV Ground Control Station",
    } <= modern

    coldwar = {
        u.variant_id for u in FACTIONS["Blufor Late Cold War (80s)"].air_defense_units
    }
    assert "C2 Fire Control Bunker" in coldwar
    assert (
        "C2 Predator UAV Comms Link" not in coldwar
    ), "the Predator vans are 1995+ kit and must not reach a 1988 faction"


@pytest.mark.parametrize(
    "layout_name",
    ["S-300 Site", "S-300 Site (Single Radar)", "HQ-22 Battery"],
)
def test_textbook_configuration_is_the_only_configuration(layout_name: str) -> None:
    """DM call 2026-08-04: the textbook SA-10 site IS the configuration -- the
    support section renders at FULL strength every time, never a 1-of-2 roll.
    2 trucks + 2 bowsers + 2 power stations, deterministically."""
    layout = LAYOUTS.by_name(layout_name)
    for slot in ("S-300 Site Logistics", "S-300 Site Fuel", "S-300 Site Power"):
        groups = [ug for ug in layout.all_unit_groups if ug.name == slot]
        assert len(groups) == 1, f"{layout_name} lost {slot!r}"
        assert groups[0].unit_count == [2], (
            f"{layout_name}/{slot}: the textbook spread must be a fixed 2, "
            f"not a roll ({groups[0].unit_count})"
        )
