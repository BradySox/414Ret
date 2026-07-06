"""The packaged drone-as-JTAC (AircraftGenerator._maybe_configure_jtac).

A faction's designated UAV (`jtac_unit`), AI-flown in an air-to-ground package,
is emitted as a `JtacInfo` -> `dcsRetribution.JTACs` -> CTLD autolase + kneeboard +
radio, so it lazes/marks for the shooters. These lock the qualification gate (blue
+ AI + jtac airframe + A/G package) and the laser-code choice without a full mission.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from game.ato.flighttype import FlightType
from game.missiongenerator.aircraft.aircraftgenerator import AircraftGenerator

REAPER = "MQ-9 Reaper"


def _ac(unit_id: str) -> Any:
    return SimpleNamespace(dcs_unit_type=SimpleNamespace(id=unit_id))


def _flight(
    *,
    blue: bool = True,
    client_count: int = 0,
    unit_id: str = REAPER,
    jtac_unit_id: str | None = REAPER,
    primary: FlightType = FlightType.ARMED_RECON,
) -> Any:
    jtac_unit = _ac(jtac_unit_id) if jtac_unit_id is not None else None
    return SimpleNamespace(
        coalition=SimpleNamespace(
            player=SimpleNamespace(is_blue=blue),
            faction=SimpleNamespace(jtac_unit=jtac_unit),
        ),
        client_count=client_count,
        unit_type=_ac(unit_id),
        package=SimpleNamespace(
            primary_flight=SimpleNamespace(flight_type=primary),
            target=SimpleNamespace(name="Mosul"),
        ),
    )


def _group() -> Any:
    unit = SimpleNamespace(name="Reaper11-1", callsign_as_str=lambda: "Reaper11")
    return SimpleNamespace(name="Reaper11", units=[unit])


def _generator(*, fc3: bool = False) -> AircraftGenerator:
    gen = AircraftGenerator.__new__(AircraftGenerator)
    gen.game = SimpleNamespace(  # type: ignore[assignment]
        settings=SimpleNamespace(plugins={"ctld.fc3LaserCode": fc3}),
        laser_code_registry=SimpleNamespace(
            alloc_laser_code=lambda: SimpleNamespace(code=1688),
            fc3_code=SimpleNamespace(code=1113),
        ),
    )
    gen.radio_registry = SimpleNamespace(alloc_uhf=lambda: "UHF")  # type: ignore[assignment]
    gen.mission_data = SimpleNamespace(jtacs=[])  # type: ignore[assignment]
    return gen


def _jtacs(gen: AircraftGenerator) -> list[Any]:
    return gen.mission_data.jtacs


def test_ai_jtac_drone_in_an_ag_package_becomes_a_jtac() -> None:
    gen = _generator()
    gen._maybe_configure_jtac(cast(Any, _flight()), cast(Any, _group()))
    jtacs = _jtacs(gen)
    assert len(jtacs) == 1
    assert jtacs[0].group_name == "Reaper11"
    assert jtacs[0].unit_name == "Reaper11-1"
    assert jtacs[0].region == "Mosul"
    assert jtacs[0].code == "1688"


def test_all_ag_package_primaries_qualify() -> None:
    for primary in (
        FlightType.ARMED_RECON,
        FlightType.CAS,
        FlightType.BAI,
        FlightType.STRIKE,
    ):
        gen = _generator()
        gen._maybe_configure_jtac(
            cast(Any, _flight(primary=primary)), cast(Any, _group())
        )
        assert len(_jtacs(gen)) == 1, primary


def test_non_ag_package_does_not_get_a_jtac() -> None:
    gen = _generator()
    gen._maybe_configure_jtac(
        cast(Any, _flight(primary=FlightType.BARCAP)), cast(Any, _group())
    )
    assert _jtacs(gen) == []


def test_only_the_factions_jtac_airframe_qualifies() -> None:
    gen = _generator()
    # An F-16 in the package is not the JTAC drone.
    gen._maybe_configure_jtac(cast(Any, _flight(unit_id="F-16CM")), cast(Any, _group()))
    assert _jtacs(gen) == []
    # A faction with no designated JTAC unit never emits one.
    gen._maybe_configure_jtac(
        cast(Any, _flight(jtac_unit_id=None)), cast(Any, _group())
    )
    assert _jtacs(gen) == []


def test_red_and_player_drones_are_not_jtacs() -> None:
    gen = _generator()
    gen._maybe_configure_jtac(cast(Any, _flight(blue=False)), cast(Any, _group()))
    gen._maybe_configure_jtac(cast(Any, _flight(client_count=1)), cast(Any, _group()))
    assert _jtacs(gen) == []


def test_fc3_laser_code_is_used_when_the_plugin_option_is_set() -> None:
    gen = _generator(fc3=True)
    gen._maybe_configure_jtac(cast(Any, _flight()), cast(Any, _group()))
    assert _jtacs(gen)[0].code == "1113"
