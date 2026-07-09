"""COIN fiction-kit selection + re-type: the rework that makes a static roadside IED an
emplaced device (a barrel static) with a security team, a VBIED a lone supply truck, an
HVT a leader's jeep + rifles, and a cell an armed technical + infantry -- instead of the
faction's default armor wearing a re-skinned map icon.

Locks the faction-roster selection (:func:`_pick_faction_unit` + the composition
builders) and :func:`_retype_units`, mirroring the Toyota Al Gaib 2001 roster the
Enduring Resolve campaign fields, without needing the real unit DB.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.data.units import UnitClass
from game.fourteenth.coin import (
    _pick_faction_unit,
    _retype_units,
    ambush_unit_types,
    cell_unit_types,
    hvt_unit_types,
    ied_emplacement_unit_types,
    ied_unit_types,
)


def _dcs(uid: str, name: str | None = None) -> Any:
    return SimpleNamespace(id=uid, name=name or uid)


def _gut(variant: str, unit_class: UnitClass, price: int, dcs_id: str) -> Any:
    """A fake ``GroundUnitType`` -- just the fields the selectors read."""
    return SimpleNamespace(
        variant_id=variant,
        unit_class=unit_class,
        price=price,
        dcs_unit_type=_dcs(dcs_id),
    )


# The Toyota Al Gaib 2001 roster (the Enduring Resolve opfor), plus a heavy IFV that the
# price cap must keep out of the "technical" pick.
_INFANTRY = [
    _gut("Insurgent AK-74", UnitClass.INFANTRY, 0, "Infantry AK Ins"),
    _gut("Infantry RPG", UnitClass.INFANTRY, 0, "Soldier RPG"),
    _gut("MANPADS SA-18 Igla", UnitClass.MANPAD, 0, "SA-18 Igla manpad"),
    _gut("Mortar 2B11 120mm", UnitClass.INFANTRY, 0, "2B11 mortar"),
]
_FRONTLINE = [
    _gut("DIM' TOYOTA GREEN", UnitClass.IFV, 2, "Toyota_vert"),
    _gut("Scout HL with DSHK 12.7mm", UnitClass.IFV, 4, "HL_DSHK"),
    _gut("SPAAA HL with ZU-23", UnitClass.AAA, 6, "HL_ZU-23"),
    _gut("BMP-1 (should be excluded by price)", UnitClass.IFV, 14, "BMP-1"),
]
_LOGISTICS = [
    _gut("LUV UAZ-469 Jeep", UnitClass.LOGISTICS, 3, "UAZ-469"),
    _gut("Truck Ural-375", UnitClass.LOGISTICS, 3, "Ural-375"),
]


def _game() -> Any:
    faction = SimpleNamespace(
        infantry_units=_INFANTRY,
        frontline_units=_FRONTLINE,
        logistics_units=_LOGISTICS,
    )
    return SimpleNamespace(red=SimpleNamespace(faction=faction))


def _ids(types: list[Any]) -> list[str]:
    return [t.id for t in types]


# --- composition builders -----------------------------------------------------------


def test_vbied_is_a_lone_supply_truck() -> None:
    assert _ids(ied_unit_types(_game())) == ["Ural-375"]


def test_static_ied_is_an_emplaced_device_plus_a_security_team() -> None:
    # The device is a vanilla barrel STATIC (faction-independent), guarded by a rifle
    # pair from the faction's own infantry.
    assert _ids(ied_emplacement_unit_types(_game())) == [
        "Oil Barrel",
        "Infantry AK Ins",
        "Infantry AK Ins",
    ]


def test_static_ied_device_never_degrades_even_without_a_faction() -> None:
    # No red faction (headless/fake game): the emplacement is still the bare device.
    faceless: Any = SimpleNamespace(red=SimpleNamespace(faction=None))
    assert _ids(ied_emplacement_unit_types(faceless)) == ["Oil Barrel"]


def test_hvt_is_a_small_convoy_jeep_technical_and_two_rifles() -> None:
    # A leader's jeep + an armed technical escort + a rifle pair -- a small convoy.
    assert _ids(hvt_unit_types(_game())) == [
        "UAZ-469",
        "HL_DSHK",
        "Infantry AK Ins",
        "Infantry AK Ins",
    ]


def test_cell_is_an_armed_technical_plus_infantry() -> None:
    # The armed DShK gun-truck wins over the cheaper plain Toyota (name hint), and the
    # over-priced BMP-1 + the AAA ZU-23 are both excluded.
    assert _ids(cell_unit_types(_game())) == ["HL_DSHK", "Infantry AK Ins"]


def test_ambush_is_a_light_raider_team_not_armor() -> None:
    # A §50 backline convoy ambush is a light raid: an armed gun-truck + a rifle pair --
    # never the front-line MBTs the FRONT_LINE task would otherwise spawn (the price cap
    # keeps the BMP-1 out; a conventional faction with no cheap technical falls to a truck).
    assert _ids(ambush_unit_types(_game())) == [
        "HL_DSHK",
        "Infantry AK Ins",
        "Infantry AK Ins",
    ]


def test_builders_noop_without_a_red_faction() -> None:
    faceless: Any = SimpleNamespace(red=SimpleNamespace(faction=None))
    assert ied_unit_types(faceless) == []
    assert hvt_unit_types(faceless) == []
    assert cell_unit_types(faceless) == []
    assert ambush_unit_types(faceless) == []
    no_red: Any = SimpleNamespace()  # no .red at all
    assert cell_unit_types(no_red) == []


# --- _pick_faction_unit -------------------------------------------------------------


def test_pick_excludes_anti_air_even_on_a_name_match() -> None:
    # A ZU-23 name hint must never return the AAA piece -- a device is never a gun; it
    # falls through to an eligible unit instead.
    picked = _pick_faction_unit([_FRONTLINE], name_hints=("zu-23",))
    assert picked is None or picked.id != "HL_ZU-23"
    # With ONLY the anti-air piece available there is nothing eligible -> None.
    only_aaa = [_gut("SPAAA HL with ZU-23", UnitClass.AAA, 6, "HL_ZU-23")]
    assert _pick_faction_unit([only_aaa], name_hints=("zu-23",)) is None


def test_pick_respects_the_price_cap() -> None:
    picked = _pick_faction_unit(
        [_FRONTLINE], classes=frozenset({UnitClass.IFV}), max_price=10
    )
    assert picked is not None and picked.id in {"Toyota_vert", "HL_DSHK"}
    assert picked.id != "BMP-1"


def test_pick_name_hint_beats_cheapest() -> None:
    # Toyota (price 2) is cheaper, but the DShK hint should still win.
    picked = _pick_faction_unit(
        [_FRONTLINE],
        classes=frozenset({UnitClass.IFV}),
        name_hints=("dshk",),
        max_price=10,
    )
    assert picked is not None and picked.id == "HL_DSHK"


def test_pick_falls_back_to_cheapest_by_price_then_name() -> None:
    picked = _pick_faction_unit([_FRONTLINE], classes=frozenset({UnitClass.IFV}))
    # No hint, no cap -> cheapest IFV is the price-2 Toyota.
    assert picked is not None and picked.id == "Toyota_vert"


def test_pick_returns_none_when_nothing_eligible() -> None:
    assert _pick_faction_unit([_LOGISTICS], classes=frozenset({UnitClass.ATGM})) is None


# --- _retype_units ------------------------------------------------------------------


def _tgo_with(n_units: int) -> Any:
    units = [SimpleNamespace(type=_dcs("BMP-1"), name="BMP-1") for _ in range(n_units)]
    group = SimpleNamespace(units=units)
    return SimpleNamespace(groups=[group])


def test_retype_reassigns_type_and_name() -> None:
    tgo = _tgo_with(1)
    new = _dcs("Ural-375", "Truck Ural-4320")
    _retype_units(tgo, [new])
    unit = tgo.groups[0].units[0]
    assert unit.type is new
    assert unit.name == "Truck Ural-4320"


def test_retype_cycles_when_group_larger_than_composition() -> None:
    tgo = _tgo_with(3)
    a, b = _dcs("UAZ-469"), _dcs("Infantry AK Ins")
    _retype_units(tgo, [a, b])
    assert [u.type.id for u in tgo.groups[0].units] == [
        "UAZ-469",
        "Infantry AK Ins",
        "UAZ-469",
    ]


def test_retype_empty_composition_is_a_noop() -> None:
    tgo = _tgo_with(2)
    _retype_units(tgo, [])
    assert all(u.type.id == "BMP-1" for u in tgo.groups[0].units)
