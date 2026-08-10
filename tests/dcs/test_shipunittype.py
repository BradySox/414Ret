from __future__ import annotations

from typing import Any

import pytest
from dcs.ships import CVN_71, LHA_Tarawa

from game.dcs.shipunittype import ShipUnitType


def _data(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "class": "AircraftCarrier",
        "price": 0,
    }
    data.update(overrides)
    return data


def test_omitted_landing_deck_angle_defaults_to_zero() -> None:
    ship = ShipUnitType._variant_from_dict(CVN_71, "test", _data())
    assert ship.landing_deck_angle == 0.0


def test_landing_deck_angle_accepts_numeric_value() -> None:
    ship = ShipUnitType._variant_from_dict(CVN_71, "test", _data(landing_deck_angle=9))
    assert ship.landing_deck_angle == 9.0


@pytest.mark.parametrize("value", ["nine", None, True, False])
def test_landing_deck_angle_rejects_malformed_values(value: Any) -> None:
    with pytest.raises(ValueError):
        ShipUnitType._variant_from_dict(CVN_71, "test", _data(landing_deck_angle=value))


@pytest.mark.parametrize("value", [90.1, -90.1])
def test_landing_deck_angle_rejects_out_of_range_values(value: float) -> None:
    with pytest.raises(ValueError):
        ShipUnitType._variant_from_dict(CVN_71, "test", _data(landing_deck_angle=value))


def test_carrier_yaml_values_are_loaded() -> None:
    assert ShipUnitType.named("CVN-71 Theodore Roosevelt").landing_deck_angle == 9.0


def test_zero_offset_platform_loads_as_zero() -> None:
    assert ShipUnitType.named("LHA-1 Tarawa").landing_deck_angle == 0.0
    assert ShipUnitType.named("LHA-1 Tarawa").dcs_unit_type is LHA_Tarawa


@pytest.mark.parametrize(
    ("variant", "expected_angle"),
    [
        ("CVN-71 Theodore Roosevelt", 9.0),
        ("CVN-70 Carl Vinson", 9.0),
        ("CVN-74 John C. Stennis", 9.0),
        ("CV 1143.5 Admiral Kuznetsov (2017)", 7.95),
        ("[VWV] CV Essex Class SCB-125", 10.5),
        ("CV-59 Forrestal", 10.5),
        ("HMAS Melbourne", 5.5),
        ("ARA Veinticinco de Mayo", 8.0),
        ("R05 Invincible", 0.0),
        ("LHA-1 Tarawa", 0.0),
        ("L02 Canberra", 0.0),
        ("L61 Juan Carlos I", 0.0),
        ("Type 071 Amphibious Transport Dock", 0.0),
        ("USS Bennington (CV-20)", 0.0),
    ],
)
def test_carrier_variants_use_class_specific_recovery_deck_angles(
    variant: str, expected_angle: float
) -> None:
    assert ShipUnitType.named(variant).landing_deck_angle == expected_angle
