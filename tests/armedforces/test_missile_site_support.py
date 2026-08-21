"""A theatre-missile battery generates as a battery, and its launchers cost money.

Background (2026-08-06). A missile site (`resources/layouts/defenses/missile.yaml`,
the ONE generic layout behind every SCUD / Iskander / CJ-10 / V-1 / ATACMS site in
the fork) generated three launchers and a UAZ-469 jeep. The real thing -- see the
9K720 Iskander's own system list: TEL, transporter/loader, command-and-staff
vehicle, information preparation station, maintenance vehicle, life support
vehicle -- is a small convoy of trucks around the launchers.

Three separate defects, one per test group below:

1. Every launcher in the fork was `price: 0`, and missile sites ARE purchasable
   (`GroupRole.DEFENSES`), so the buy menu sold free ballistic missiles and
   repairing a killed launcher was free.
2. The site's single class-based `Logistics` slot picks ONE type from a pool that
   since §85 also holds fuel bowsers -- so the bowser DISPLACED the cargo truck
   instead of joining it (what the flown Marianas PLARF sites showed). Fuel is now
   its own slot.
3. There was no transload or command vehicle at all.

The §49 constraint runs through all of it: every unit here shares ONE DCS group
with the launchers, `mist.goRoute` routes a group as a whole, and one undrivable
member pins the whole battery -- so the support section is drivable metal only.
"""

from __future__ import annotations

import itertools
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

import pytest
import yaml
from dcs.mapping import Point
from dcs.unittype import VehicleType

from game import persistency
from game.dcs.groundunittype import GroundUnitType
from game.dcs.helpers import unit_type_from_name
from game.layout import LAYOUTS
from game.layout.layout import TgoLayoutUnitGroup
from game.missiongenerator.mobilemissileluadata import IMMOBILE_UNIT_IDS
from game.theater.presetlocation import PresetLocation
from game.utils import Heading

GROUND_UNIT_DIR = Path("resources/units/ground_units")
MISSILE_LAYOUT_YAML = Path("resources/layouts/defenses/missile.yaml")
LAYOUT_NAME = "Missile"

#: The support slots added on top of the launchers + AAA/SHORAD escorts.
SUPPORT_SLOTS = (
    "ScudGenerator 1",  # cargo trucks
    "Missile Site Transload",
    "Missile Site Fuel",
    "Missile Site C2",
)
CARGO_SLOT = "ScudGenerator 1"
FUEL_SLOT = "Missile Site Fuel"
LAUNCHER_SLOT = "ScudGenerator 0"


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    # Layout/preset loading reads the DCS saved-game folder, which only exists
    # once the app boots. Point it at an empty temp dir so loading falls back to
    # the bundled resources/ templates.
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


def _unit_yamls() -> Iterator[tuple[str, dict[str, Any]]]:
    for path in sorted(GROUND_UNIT_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        yield path.stem, data


def _launcher_yamls() -> list[str]:
    return [
        unit_id
        for unit_id, data in _unit_yamls()
        if data.get("class") in {"Missile", "AntiShipMissile"}
    ]


def _slot(name: str) -> TgoLayoutUnitGroup:
    layout = LAYOUTS.by_name(LAYOUT_NAME)
    for unit_group in layout.all_unit_groups:
        if unit_group.name == name:
            return unit_group
    raise AssertionError(f"the {LAYOUT_NAME} layout has no {name!r} slot")


# --- 1. launchers are not free -------------------------------------------------


@pytest.mark.parametrize("unit_id", _launcher_yamls())
def test_every_missile_launcher_is_priced(unit_id: str) -> None:
    """A launcher at `price: 0` is free to buy and free to repair.

    Missile and coastal sites are purchasable (both tasks are
    `GroupRole.DEFENSES`), and the ground-object repair cost is the unit price,
    so a zero here means the buy menu hands out theatre ballistic missiles and
    coastal anti-ship batteries for nothing.
    """
    data = yaml.safe_load((GROUND_UNIT_DIR / f"{unit_id}.yaml").read_text("utf-8"))
    price = data.get("price")
    assert price, f"{unit_id} is a launcher with price {price!r}"
    assert price > 0


def test_launcher_prices_scale_with_capability() -> None:
    """The ordering is the point, not the absolute numbers: a modern precision
    SRBM outranks a 1960s liquid-fuel rocket, which outranks a WWII ramp."""

    def price(unit_id: str) -> int:
        data = yaml.safe_load((GROUND_UNIT_DIR / f"{unit_id}.yaml").read_text("utf-8"))
        return int(data["price"])

    assert price("v1_launcher") < price("Scud_B") < price("CH_IskanderM")
    assert price("CH_IskanderM") <= price("CH_IskanderK")
    # The two Iskander-M registrations are the same system.
    assert (
        price("CH_IskanderM") == price("CHAP_9K720_HE") == price("CHAP_9K720_Cluster")
    )
    # Cheap-by-design loitering munition stays the cheapest modern launcher.
    assert price("CH_Shahed136") < price("Scud_B")


# --- 2. the layout's shape -----------------------------------------------------


def test_the_battery_has_its_support_section() -> None:
    layout = LAYOUTS.by_name(LAYOUT_NAME)
    slot_names = [ug.name for ug in layout.all_unit_groups]
    for name in SUPPORT_SLOTS:
        assert name in slot_names, f"the missile layout lost its {name!r} slot"
    # One DCS group: the launchers, their escorts and the support park relocate
    # together under §49, and §7's MFD hiding keys off the escorts being in-group.
    assert len(layout.groups) == 1


def test_the_textbook_configuration_is_fixed_not_rolled() -> None:
    """The §85 call: a battery renders the same support park every time, so the
    site is recognisable from the air instead of sometimes generating bare."""
    assert _slot(LAUNCHER_SLOT).unit_count == [3]
    assert _slot(CARGO_SLOT).unit_count == [2]
    for name in ("Missile Site Transload", FUEL_SLOT, "Missile Site C2"):
        assert _slot(name).unit_count == [1]


def test_support_slots_are_optional() -> None:
    """A faction that fields none of this generates the site it generated before,
    rather than failing to generate at all (a non-optional slot with no accessible
    unit raises LayoutException and takes the whole layout out of the game)."""
    for name in SUPPORT_SLOTS:
        assert _slot(name).optional, f"{name} must be optional"


def test_every_unit_id_in_the_layout_resolves_to_a_vehicle() -> None:
    """`unit_type_from_name` returns None for a typo and the loader drops it
    SILENTLY, so a misspelled id is a slot that quietly fields less than it says.
    """
    data = yaml.safe_load(MISSILE_LAYOUT_YAML.read_text(encoding="utf-8"))
    listed = [
        unit_id
        for group in data["groups"]
        for slots in group.values()
        for slot in slots
        for unit_id in slot.get("unit_types", [])
    ]
    assert listed, "the missile layout declares no explicit unit types"
    unresolved = [u for u in listed if unit_type_from_name(u) is None]
    assert not unresolved, f"unresolved unit ids in {MISSILE_LAYOUT_YAML}: {unresolved}"
    not_vehicles = [
        u
        for u in listed
        if not issubclass(unit_type_from_name(u), VehicleType)  # type: ignore[arg-type]
    ]
    assert not not_vehicles, f"non-vehicle unit ids: {not_vehicles}"


# --- 3. fuel no longer displaces the cargo truck -------------------------------


def _refueller_ids() -> set[str]:
    return {
        unit_id
        for unit_id, data in _unit_yamls()
        if "Refueler" in " ".join(str(v) for v in (data.get("variants") or {}))
    }


def test_the_cargo_slot_cannot_roll_a_fuel_bowser() -> None:
    """The displacement fix. A class-based `Logistics` slot picks one type from a
    pool that holds cargo trucks AND refuellers, so §85's bowsers replaced the
    truck. The cargo slot is now an explicit truck whitelist and fuel is its own
    slot, so a battery fields both.
    """
    cargo_ids = {t.id for t in _slot(CARGO_SLOT).unit_types}
    assert cargo_ids, "the cargo slot lost its whitelist"
    assert not cargo_ids & _refueller_ids()

    fuel_ids = {t.id for t in _slot(FUEL_SLOT).unit_types}
    assert fuel_ids <= _refueller_ids(), "the fuel slot lists a non-refueller"


def test_the_transload_slot_never_offers_a_bowser_either() -> None:
    """It used `fallback_classes: [Logistics]`, which resolves to the faction's
    whole logistics pool -- measured 9 of 11 candidates for Russia 2020 were fuel
    bowsers, i.e. the "transloader" was a second ATZ-10. Cargo trucks are listed
    explicitly instead.
    """
    slot = _slot("Missile Site Transload")
    assert not {t.id for t in slot.unit_types} & _refueller_ids()
    assert not slot.fallback_classes


# --- 4. every faction that fields missiles fields the support section ----------


def test_every_missile_fielding_faction_always_fields_trucks() -> None:
    """No bare sites: the cargo and transload slots resolve for every faction
    that can place a missile site, either from the truck whitelist or from its
    own logistics pool via `fallback_classes`.

    Looped rather than parametrized because the faction loader needs the
    persistency fixture, which has not run at collection time.
    """
    from game.armedforces.forcegroup import ForceGroup
    from game.factions import FACTIONS

    layout = LAYOUTS.by_name(LAYOUT_NAME)
    missile_factions = {
        name: faction
        for name, faction in FACTIONS.factions.items()
        if getattr(faction, "missiles", None)
    }
    assert len(missile_factions) > 20, "expected the shipped missile-fielding factions"

    bare = []
    for name, faction in sorted(missile_factions.items()):
        group = ForceGroup.for_layout(layout, faction)
        for slot in (CARGO_SLOT, "Missile Site Transload"):
            if not group.dcs_unit_types_for_group(_slot(slot)):
                bare.append((name, slot))
    assert not bare, f"factions whose missile sites would generate bare: {bare}"


@pytest.mark.parametrize(
    "faction_name,slot,expected",
    [
        # The two campaigns the SCUD hunt is actually played on get the full kit.
        ("Russia 1980 (Red Tide)", "Missile Site C2", "ZIL-131 KUNG"),
        ("Iraq 1991", "Missile Site C2", "ZIL-131 KUNG"),
        ("Russia 1980 (Red Tide)", FUEL_SLOT, "ATZ-10"),
        ("USA 2020", FUEL_SLOT, "M978 HEMTT Tanker"),
        ("USA 2020", "Missile Site Transload", "CH_HEMTT_M977"),
    ],
)
def test_the_kit_is_nation_correct(faction_name: str, slot: str, expected: str) -> None:
    from game.armedforces.forcegroup import ForceGroup
    from game.factions import FACTIONS

    layout = LAYOUTS.by_name(LAYOUT_NAME)
    group = ForceGroup.for_layout(layout, FACTIONS[faction_name])
    offered = {t.id for t in group.dcs_unit_types_for_group(_slot(slot))}
    assert expected in offered, f"{faction_name} {slot} offers {sorted(offered)}"


# --- 5. §49: nothing in the support section may pin the battery ----------------


def test_no_support_unit_can_pin_the_scoot() -> None:
    """The §49 rule, enforced on the data. A missile site is ONE DCS group and
    `mist.goRoute` routes it as a whole, so a single undrivable member stops the
    whole battery relocating -- which is why there is no power station or static
    in this section, unlike the S-300's.
    """
    immobile = []
    for name in SUPPORT_SLOTS:
        for dcs_type in _slot(name).unit_types:
            if dcs_type.id in IMMOBILE_UNIT_IDS:
                immobile.append((name, dcs_type.id))
                continue
            assert issubclass(dcs_type, VehicleType)
            for unit in GroundUnitType.for_dcs_type(dcs_type):
                if not unit.mobile:
                    immobile.append((name, dcs_type.id))
    assert not immobile, f"undrivable support units would pin the battery: {immobile}"


def test_immobile_ids_and_unit_definitions_stay_in_lockstep() -> None:
    """Two sources of truth would drift. The emitter's id set is the fallback for
    a DCS type with no registered yaml; every id in it that DOES have one must
    carry `mobile: false`, and no other unit may claim it silently.
    """
    flagged = {
        unit_id
        for unit_id, data in _unit_yamls()
        if data.get("mobile") is False  # noqa: E712
    }
    registered = {
        u for u in IMMOBILE_UNIT_IDS if (GROUND_UNIT_DIR / f"{u}.yaml").is_file()
    }
    assert registered <= flagged, (
        f"{sorted(registered - flagged)} are excluded in code but their unit "
        f"definitions still say they drive"
    )
    assert flagged == registered, (
        f"{sorted(flagged - registered)} declare `mobile: false` but are missing "
        f"from IMMOBILE_UNIT_IDS"
    )


def test_the_emitter_skips_a_group_with_an_undrivable_launcher() -> None:
    """End to end on real DCS types: a CJ-10 battery is never routed (it does not
    drive), a Scud battery is."""
    from game.missiongenerator.luagenerator import LuaData
    from game.missiongenerator.mobilemissileluadata import populate_mobile_missiles_lua

    def tgo(name: str, unit_id: str) -> Any:
        unit_type = unit_type_from_name(unit_id)
        unit = SimpleNamespace(alive=True, is_vehicle=True, type=unit_type)
        return SimpleNamespace(
            category="missile",
            groups=[SimpleNamespace(group_name=name, units=[unit])],
            position=SimpleNamespace(x=1.0, y=2.0),
        )

    game = SimpleNamespace(
        settings=SimpleNamespace(mobile_missile_relocation=True),
        theater=SimpleNamespace(
            controlpoints=[
                SimpleNamespace(
                    ground_objects=[tgo("scud", "Scud_B"), tgo("cj10", "CH_CJ10")]
                )
            ]
        ),
    )
    root = LuaData("dcsRetribution")
    populate_mobile_missiles_lua(root, game, mission_data=None)  # type: ignore[arg-type]
    node = root.get_item("mobileMissiles")
    assert isinstance(node, LuaData)
    sites = node.get_item("sites")
    assert isinstance(sites, LuaData)
    emitted = sites.serialize()
    assert "scud" in emitted
    assert "cj10" not in emitted


# --- 6. the template itself ----------------------------------------------------


#: Offsets of the pre-existing template units, relative to the layout anchor
#: (the loader anchors on the first unit of the first group in the .miz, which is
#: `ScudGenerator 3`). Appending groups must never move these -- every campaign's
#: authored missile sites are placed against them.
LEGACY_OFFSETS = {
    "ScudGenerator 0-0": (-200.0, -13.0),
    "ScudGenerator 0-1": (-150.0, -14.0),
    "ScudGenerator 0-2": (-100.0, -11.0),
    "ScudGenerator 1-0": (-235.0, -35.0),
    "ScudGenerator 2-0": (-255.0, -53.0),
    "ScudGenerator 3-0": (0.0, 0.0),
}
MIN_SEPARATION_M = 20.0


def test_the_template_origin_and_legacy_offsets_are_unchanged() -> None:
    layout = LAYOUTS.by_name(LAYOUT_NAME)
    positions = {
        unit.name: (round(unit.position.x, 1), round(unit.position.y, 1))
        for unit_group in layout.all_unit_groups
        for unit in unit_group.layout_units
    }
    for name, expected in LEGACY_OFFSETS.items():
        assert positions.get(name) == expected, (
            f"{name} moved to {positions.get(name)} -- appending support groups "
            f"must not re-anchor the template"
        )


def test_support_positions_are_dispersed() -> None:
    """One bomb should not take the launchers and their reloads together."""
    layout = LAYOUTS.by_name(LAYOUT_NAME)
    points = [
        (unit.name, unit.position)
        for unit_group in layout.all_unit_groups
        for unit in unit_group.layout_units
    ]
    for (name_a, a), (name_b, b) in itertools.combinations(points, 2):
        distance = a.distance_to_point(b)
        assert (
            distance >= MIN_SEPARATION_M
        ), f"{name_a} and {name_b} are {distance:.1f} m apart"


def test_a_generated_battery_is_one_group_with_the_full_section() -> None:
    """End to end: build the real TGO for a faction with the full kit."""
    from game.armedforces.forcegroup import ForceGroup
    from game.data.groups import GroupTask
    from game.factions import FACTIONS
    from game.theater.controlpoint import OffMapSpawn, Player

    layout = LAYOUTS.by_name(LAYOUT_NAME)
    group = ForceGroup.for_layout(layout, FACTIONS["Russia 1980 (Red Tide)"])
    control_point = OffMapSpawn(
        name="cp",
        position=Point(0, 0, None),  # type: ignore[arg-type]
        theater=None,  # type: ignore[arg-type]
        starts_blue=Player.RED,
    )
    # Generation reads control_point.captured, which goes through the coalition.
    control_point._coalition = SimpleNamespace(player=Player.RED)  # type: ignore[assignment]
    location = PresetLocation(
        name="site", position=Point(0, 0, None), heading=Heading(0)  # type: ignore[arg-type]
    )
    groups = itertools.count(1)
    units_ids = itertools.count(1)
    game = SimpleNamespace(
        next_group_id=lambda: next(groups), next_unit_id=lambda: next(units_ids)
    )
    tgo = group.create_ground_object_for_layout(
        layout,
        "battery",
        location,
        control_point,
        game,  # type: ignore[arg-type]
        GroupTask.MISSILE,
    )

    assert len(tgo.groups) == 1, "the battery must generate as one DCS group"
    units = [unit.type.id for unit in tgo.groups[0].units]
    launchers = [u for u in units if u == "Scud_B"]
    assert len(launchers) == 3
    # 3 launchers + 2 trucks + transload + fuel + C2, plus the optional AAA and
    # SHORAD escorts (the SHORAD slot can roll zero).
    assert 8 <= len(units) <= 10, units
    for slot in (CARGO_SLOT, "Missile Site Transload", FUEL_SLOT, "Missile Site C2"):
        offered = {t.id for t in _slot(slot).unit_types}
        assert offered & set(units), f"{slot} generated nothing: {units}"
