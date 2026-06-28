from __future__ import annotations

import dcs.countries as countries
from dcs.vehicles import Unarmed

from game.missiongenerator.tgogenerator import (
    _GROUND_SUPPORT_INTRO_YEAR,
    _SOVIET_TRUCKS,
    _US_TRUCKS,
    _support_vehicles_in_service,
    farp_truck_types_for_country,
)


def test_no_year_does_not_filter() -> None:
    # year=None (date restriction off) returns the full pool unchanged.
    assert _support_vehicles_in_service(_SOVIET_TRUCKS, None) is _SOVIET_TRUCKS


def test_year_filter_keeps_only_in_service_vehicles() -> None:
    in_service = _support_vehicles_in_service(_SOVIET_TRUCKS, 1968)
    assert in_service  # non-empty
    assert all(_GROUND_SUPPORT_INTRO_YEAR[v] <= 1968 for v in in_service)
    assert Unarmed.KAMAZ_Truck not in in_service  # 1976, post-Vietnam
    assert Unarmed.GAZ_66 in in_service  # 1964, period-correct


def test_empty_filter_falls_back_to_oldest() -> None:
    # No US cargo truck predates 1970 in vanilla DCS; the filter must still
    # return the oldest rather than empty (which would crash random.choice).
    assert _support_vehicles_in_service(_US_TRUCKS, 1968) == [Unarmed.M_818]


def test_vietnam_era_red_support_is_period_correct() -> None:
    # Run repeatedly to exercise random.choice across the filtered pools.
    for _ in range(50):
        tanker, ammo, power = farp_truck_types_for_country(
            countries.Russia.id, year=1968
        )
        assert _GROUND_SUPPORT_INTRO_YEAR[tanker] <= 1968
        assert _GROUND_SUPPORT_INTRO_YEAR[ammo] <= 1968
        assert _GROUND_SUPPORT_INTRO_YEAR[power] <= 1968


def test_vietnam_era_us_support_falls_back_without_crashing() -> None:
    # The US pools have no pre-1970 entries; generation must still succeed and
    # clamp to the oldest available rather than raise.
    tanker, ammo, power = farp_truck_types_for_country(countries.USA.id, year=1968)
    assert tanker == Unarmed.M978_HEMTT_Tanker
    assert ammo == Unarmed.M_818
    # The ground-power pool is shared; ZiL-131 APA (1967) is the period option.
    assert power == Unarmed.ZiL_131_APA_80


def test_unrestricted_pick_returns_known_vehicles() -> None:
    # Legacy behaviour with no year: every returned type is a real support
    # vehicle (present in the intro-year table).
    for country_id in (countries.Russia.id, countries.USA.id):
        for vehicle in farp_truck_types_for_country(country_id):
            assert vehicle in _GROUND_SUPPORT_INTRO_YEAR
