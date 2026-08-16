"""Every yaml task claim must survive AircraftBehavior.configure_task.

Airframe yamls (and upstream's data) claim tasks the pydcs unit type cannot
express — the Tu-160 claims DEAD but pydcs only exports Pinpoint Strike. Before
the degrade in configure_task, any such auto-planned tasking raised
RuntimeError at generation time and cost the whole mission. This walks every
(airframe, claimed task) pair through the real configure_task and asserts a
group role is always assigned, never raised.
"""

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

import pytest
from dcs.task import (
    AFAC,
    AWACS,
    CAP,
    CAS,
    SEAD,
    AntishipStrike,
    Escort,
    FighterSweep,
    GroundAttack,
    Nothing,
    PinpointStrike,
    Reconnaissance,
    Refueling,
    RunwayAttack,
    Transport,
)

from game import persistency
from game.ato.flighttype import FlightType
from game.dcs.aircrafttype import AircraftType
from game.missiongenerator.aircraft.aircraftbehavior import AircraftBehavior

# Mirror of AircraftBehavior.apply_to's dispatch to configure_task. When a
# configure_* method's preferred/fallback lists change, update this table too.
TASK_MAPPING: dict[FlightType, tuple[Any, list[Any]]] = {
    FlightType.BARCAP: (CAP, []),
    FlightType.TARCAP: (CAP, []),
    FlightType.INTERCEPTION: (CAP, []),
    FlightType.SWEEP: (FighterSweep, []),
    FlightType.AEWC: (AWACS, []),
    FlightType.REFUELING: (Refueling, []),
    FlightType.RECOVERY: (Refueling, []),
    FlightType.CAS: (CAS, [AFAC, AntishipStrike]),
    FlightType.BAI: (CAS, [AFAC, AntishipStrike]),
    FlightType.ARMED_RECON: (CAS, [AFAC, AntishipStrike]),
    FlightType.DEAD: (SEAD, [CAS, AFAC, AntishipStrike]),
    FlightType.SEAD: (SEAD, [CAS, AFAC, AntishipStrike]),
    FlightType.SEAD_SWEEP: (SEAD, [CAS, AFAC, AntishipStrike]),
    FlightType.SEAD_ESCORT: (SEAD, []),
    FlightType.ESCORT_JAMMER: (SEAD, [Escort]),
    FlightType.STRIKE: (GroundAttack, [PinpointStrike, AFAC]),
    FlightType.ANTISHIP: (AntishipStrike, [CAS, AFAC, SEAD]),
    FlightType.ESCORT: (Escort, []),
    FlightType.OCA_RUNWAY: (RunwayAttack, []),
    FlightType.OCA_AIRCRAFT: (CAS, [AFAC, SEAD, AntishipStrike]),
    FlightType.JAMMING: (AWACS, [Transport, Nothing]),
    FlightType.TARPS: (Reconnaissance, [CAS, GroundAttack]),
    FlightType.TRANSPORT: (Transport, []),
    FlightType.AIR_ASSAULT: (Transport, []),
    FlightType.CSAR: (Transport, []),
}


@pytest.fixture(scope="module")
def fleet(tmp_path_factory: pytest.TempPathFactory) -> Iterator[list[AircraftType]]:
    tmp_path: Path = tmp_path_factory.mktemp("task_gen")
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16884)
    yield list(AircraftType.iter_all())


def fake_flight(aircraft: AircraftType, task: FlightType) -> Any:
    return SimpleNamespace(
        unit_type=aircraft,
        flight_type=task,
        roster=SimpleNamespace(members=[]),
    )


def test_every_claimed_task_generates(fleet: list[AircraftType]) -> None:
    checked = 0
    for aircraft in fleet:
        for task in aircraft.task_priorities:
            if task not in TASK_MAPPING:
                continue
            checked += 1
            preferred, fallbacks = TASK_MAPPING[task]
            group = SimpleNamespace(task="CAP")
            AircraftBehavior.configure_task(
                fake_flight(aircraft, task), group, preferred, fallbacks  # type: ignore[arg-type]
            )
            assert (
                isinstance(group.task, str) and group.task
            ), f"{aircraft.display_name} {task} produced no group role"
    # The fleet is large; a collapsed registry would pass vacuously.
    assert checked > 1000


def test_tu160_dead_degrades_to_pinpoint_strike(fleet: list[AircraftType]) -> None:
    # The reproduced crash: upstream data claims DEAD on the Tu-160, pydcs
    # exports only Pinpoint Strike, and generation raised for the AI flight.
    tu160 = next(a for a in fleet if a.display_name == "Tu-160 Blackjack")
    preferred, fallbacks = TASK_MAPPING[FlightType.DEAD]
    group = SimpleNamespace(task="CAP")
    AircraftBehavior.configure_task(
        fake_flight(tu160, FlightType.DEAD), group, preferred, fallbacks  # type: ignore[arg-type]
    )
    assert group.task == "Pinpoint Strike"
