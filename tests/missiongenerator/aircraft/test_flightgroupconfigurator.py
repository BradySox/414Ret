from typing import Any, Dict, Optional

import pytest

from game.lasercodes.ilasercoderegistry import ILaserCodeRegistry
from game.lasercodes.lasercode import LaserCode
from game.missiongenerator.aircraft.flightgroupconfigurator import (
    FlightGroupConfigurator,
)
from game.radio.radios import MHz, RadioFrequency, RadioRegistry


class _StubRegistry(ILaserCodeRegistry):
    def alloc_laser_code(self) -> LaserCode:
        raise NotImplementedError

    def release_code(self, code: LaserCode) -> None:
        pass


class _StubSettings:
    """Stands in for pydcs' WeaponSettings, which reports the weapon's defaults."""

    def __init__(self, values: Dict[str, Any]) -> None:
        self._values = values

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._values)


class _StubWeapon:
    """A weapon whose settings schema declares a tail fuze, like any real bomb."""

    def __init__(
        self, accepts: bool = True, defaults: Optional[Dict[str, Any]] = None
    ) -> None:
        self._accepts = accepts
        self._defaults = {"NFP_fuze_type_tail": "FMU139CB_LD", "laser_code": 1688}
        if defaults is not None:
            self._defaults = defaults

    def accepts_laser_code(self) -> bool:
        return self._accepts

    def create_settings(self) -> Optional[_StubSettings]:
        return _StubSettings(self._defaults) if self._defaults else None


@pytest.fixture(name="laser_code")
def laser_code_fixture() -> LaserCode:
    return LaserCode(1511, _StubRegistry())


def test_merge_keeps_the_weapon_defaults_when_the_loadout_has_no_settings(
    laser_code: LaserCode,
) -> None:
    """The regression this guards: a table holding only the laser code told DCS the
    bomb had no fuze fitted, so it fell as a dud."""
    result = FlightGroupConfigurator._merge_laser_code(
        None, _StubWeapon(), laser_code  # type: ignore[arg-type]
    )
    assert result == {"NFP_fuze_type_tail": "FMU139CB_LD", "laser_code": 1511}


def test_merge_preserves_other_settings_when_accepted(laser_code: LaserCode) -> None:
    base: Dict[str, Any] = {"fuze_setting": "instant"}
    result = FlightGroupConfigurator._merge_laser_code(
        base, _StubWeapon(defaults={}), laser_code  # type: ignore[arg-type]
    )
    assert result == {"fuze_setting": "instant", "laser_code": 1511}


def test_merge_lets_the_loadout_override_a_default(laser_code: LaserCode) -> None:
    base: Dict[str, Any] = {"NFP_fuze_type_tail": "FMU152AB_LD"}
    result = FlightGroupConfigurator._merge_laser_code(
        base, _StubWeapon(), laser_code  # type: ignore[arg-type]
    )
    assert result is not None
    assert result["NFP_fuze_type_tail"] == "FMU152AB_LD"


def test_merge_overrides_existing_laser_code_when_accepted(
    laser_code: LaserCode,
) -> None:
    base: Dict[str, Any] = {"laser_code": 1688}
    result = FlightGroupConfigurator._merge_laser_code(
        base, _StubWeapon(defaults={}), laser_code  # type: ignore[arg-type]
    )
    assert result == {"laser_code": 1511}


def test_merge_returns_base_unchanged_when_not_accepted(
    laser_code: LaserCode,
) -> None:
    base: Dict[str, Any] = {"fuze_setting": "instant"}
    result = FlightGroupConfigurator._merge_laser_code(
        base, _StubWeapon(accepts=False), laser_code  # type: ignore[arg-type]
    )
    assert result is base


def test_merge_returns_base_unchanged_when_no_laser_code() -> None:
    base: Dict[str, Any] = {"fuze_setting": "instant"}
    result = FlightGroupConfigurator._merge_laser_code(
        base, _StubWeapon(), None  # type: ignore[arg-type]
    )
    assert result is base


def test_merge_returns_none_when_no_laser_code_and_no_base() -> None:
    result = FlightGroupConfigurator._merge_laser_code(
        None, _StubWeapon(), None  # type: ignore[arg-type]
    )
    assert result is None


def test_merge_does_not_mutate_input_base(laser_code: LaserCode) -> None:
    base: Dict[str, Any] = {"laser_code": 1688, "fuze_setting": "instant"}
    snapshot = dict(base)
    FlightGroupConfigurator._merge_laser_code(
        base, _StubWeapon(), laser_code  # type: ignore[arg-type]
    )
    assert base == snapshot


class _StubSupportInfo:
    """Stands in for TankerInfo/AwacsInfo; only the channel is read."""

    def __init__(self, freq: RadioFrequency) -> None:
        self.freq = freq


class _StubMissionData:
    def __init__(self) -> None:
        self.tankers: list[Any] = []
        self.awacs: list[Any] = []


class _StubFlight:
    def __init__(self, frequency: Optional[RadioFrequency] = None) -> None:
        self.frequency = frequency


def _configurator(
    flight: _StubFlight, mission_data: _StubMissionData
) -> FlightGroupConfigurator:
    """A configurator with only the collaborators dedicated_support_frequency reads."""
    configurator = object.__new__(FlightGroupConfigurator)
    configurator.flight = flight  # type: ignore[assignment]
    configurator.mission_data = mission_data  # type: ignore[assignment]
    configurator.radio_registry = RadioRegistry()
    return configurator


def test_first_support_flight_keeps_the_package_frequency() -> None:
    """Nothing has claimed the channel yet, so no channel is wasted."""
    mission_data = _StubMissionData()
    configurator = _configurator(_StubFlight(), mission_data)
    package_freq = MHz(396)

    assert configurator.dedicated_support_frequency(package_freq) == package_freq


def test_second_support_flight_in_a_package_gets_its_own_frequency() -> None:
    """The regression this guards: the long range carrier strike puts a buddy tanker
    and an E-2 in one package, so both inherited the package frequency. DCS builds the
    comms menu per frequency, so only the AEW&C answered and the tanker was
    unreachable."""
    mission_data = _StubMissionData()
    package_freq = MHz(396)
    mission_data.tankers.append(_StubSupportInfo(package_freq))
    configurator = _configurator(_StubFlight(), mission_data)
    # In production the package frequency was handed out by this same registry, so
    # the fresh alloc_uhf (a random draw avoiding only ALLOCATED channels) can never
    # re-draw it. Mirror that here or the test flakes ~1 in 175 runs on the draw
    # landing on 396.000 exactly.
    configurator.radio_registry.reserve(package_freq)

    channel = configurator.dedicated_support_frequency(package_freq)

    assert channel != package_freq
    assert channel in configurator.radio_registry.allocated_channels


def test_a_tanker_does_not_share_the_aewc_channel() -> None:
    mission_data = _StubMissionData()
    package_freq = MHz(396)
    mission_data.awacs.append(_StubSupportInfo(package_freq))
    configurator = _configurator(_StubFlight(), mission_data)
    # See test_second_support_flight...: reserve the package frequency as the real
    # registry would have, so the random re-draw cannot land on it (the flake).
    configurator.radio_registry.reserve(package_freq)

    assert configurator.dedicated_support_frequency(package_freq) != package_freq


def test_an_explicit_flight_frequency_is_left_alone() -> None:
    """Only the inherited package frequency is replaced; a deliberate assignment
    stands even if it collides."""
    mission_data = _StubMissionData()
    pinned = MHz(396)
    mission_data.awacs.append(_StubSupportInfo(pinned))
    configurator = _configurator(_StubFlight(frequency=pinned), mission_data)

    assert configurator.dedicated_support_frequency(pinned) == pinned


def test_support_frequencies_covers_both_tankers_and_aewc() -> None:
    mission_data = _StubMissionData()
    mission_data.tankers.append(_StubSupportInfo(MHz(245)))
    mission_data.awacs.append(_StubSupportInfo(MHz(287)))
    configurator = _configurator(_StubFlight(), mission_data)

    assert configurator.support_frequencies() == {MHz(245), MHz(287)}
