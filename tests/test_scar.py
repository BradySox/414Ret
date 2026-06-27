"""Tests for the SCAR ("Sandy") rescue-escort flight type.

Rescue rework: SCAR is the RESCAP escort in the Combat SAR package (A-10/Apache)
-- it holds near the FLOT, protects the downed pilot, and walks the rescue helo
in. These tests lock in the cheap-to-verify Python contract: the FlightType
classification, builder dispatch, capability gating (fixed-wing CAS + attack
helos, bombers excluded), and front-line target exposure. The runtime rescue
behaviour rides the combatsar plugin and is validated in-game, not here.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from dcs.mapping import Point

from game import persistency
from game.ato.flighttype import FlightType
from game.ato.flightplans.flightplanbuildertypes import FlightPlanBuilderTypes
from game.ato.flightplans.scar import ScarFlightPlan
from game.dcs.aircrafttype import AircraftType
from game.theater.controlpoint import OffMapSpawn, Player
from game.theater.frontline import FrontLine
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import SamGroundObject, TheaterGroundObject
from game.utils import Heading

# Fixed-wing CAS airframe AND CAS-capable attack helo -> SCAR-capable (Sandy);
# a bomber (CAS for called coords only, no AFAC) is excluded.
A10_VARIANT_ID = "A-10C Thunderbolt II (Suite 3)"
APACHE_VARIANT_ID = "AH-64D Apache Longbow (AI)"
BAI_ONLY_BOMBER_VARIANT_ID = "Tu-160 Blackjack"


def test_scar_is_primary_air_to_ground_task() -> None:
    # SCAR is a lead/standalone ground-attack task, not an A2A or support role.
    assert FlightType.SCAR.is_air_to_ground
    assert not FlightType.SCAR.is_air_to_air
    assert FlightType.SCAR.is_primary_package_task
    assert FlightType.SCAR.entity_type.name == "ATTACK_STRIKE"


def test_scar_value_roundtrips() -> None:
    assert FlightType.from_name("SCAR") is FlightType.SCAR
    assert str(FlightType.SCAR) == "SCAR"


def test_scar_dispatches_to_scar_builder() -> None:
    flight = MagicMock()
    flight.flight_type = FlightType.SCAR
    assert FlightPlanBuilderTypes.for_flight(flight) is ScarFlightPlan.builder_type()


def test_fixed_wing_cas_airframe_is_scar_capable(tmp_path: Path) -> None:
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16880)
    a10 = AircraftType.named(A10_VARIANT_ID)
    assert a10.capable_of(FlightType.CAS)
    assert a10.capable_of(FlightType.SCAR)


def test_attack_helicopter_cas_airframe_is_scar_capable(tmp_path: Path) -> None:
    # SCAR is now the "Sandy" RESCAP escort: a CAS-capable attack helo (Apache)
    # qualifies via its CAS capability (transport helos have no CAS, so the rescue
    # helo itself is still excluded).
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16880)
    apache = AircraftType.named(APACHE_VARIANT_ID)
    assert apache.capable_of(FlightType.CAS)
    assert apache.capable_of(FlightType.SCAR)


def test_bai_only_bomber_is_not_scar_capable(tmp_path: Path) -> None:
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16880)
    bomber = AircraftType.named(BAI_ONLY_BOMBER_VARIANT_ID)
    assert bomber.capable_of(FlightType.BAI)
    assert not bomber.capable_of(FlightType.CAS)
    assert not bomber.capable_of(FlightType.SCAR)


def test_scar_is_not_offered_against_generic_ground_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Rescue rework: SCAR is no longer a broad anti-armor task. It is scoped to the
    # FLOT (the rescue context), so a generic enemy ground object no longer exposes
    # it (here a SAM site, matching the TARPS-test fixture pattern).
    monkeypatch.setattr(TheaterGroundObject, "is_friendly", lambda self, player: False)
    location = PresetLocation(
        name="loc", position=Point(0, 0, None), heading=Heading(0)  # type: ignore
    )
    control_point = OffMapSpawn(
        name="cp",
        position=Point(0, 0, None),  # type: ignore
        theater=None,  # type: ignore
        starts_blue=Player.BLUE,
    )
    sam = SamGroundObject(
        name="sam", location=location, control_point=control_point, task=None
    )
    assert FlightType.SCAR not in list(sam.mission_types(for_player=Player.RED))


def test_scar_is_offered_against_the_front_line() -> None:
    # The rescue package (King + Jolly + Sandy) frags against the FLOT, so the front
    # still exposes SCAR even though generic ground targets no longer do. Build a
    # FrontLine without its heavy __init__ -- mission_types/is_friendly need no
    # instance state.
    front = object.__new__(FrontLine)
    types = list(front.mission_types(for_player=Player.RED))
    assert FlightType.SCAR in types
    assert FlightType.COMBAT_SAR in types


def test_scar_not_offered_against_friendly_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(TheaterGroundObject, "is_friendly", lambda self, player: True)
    location = PresetLocation(
        name="loc", position=Point(0, 0, None), heading=Heading(0)  # type: ignore
    )
    control_point = OffMapSpawn(
        name="cp",
        position=Point(0, 0, None),  # type: ignore
        theater=None,  # type: ignore
        starts_blue=Player.BLUE,
    )
    sam = SamGroundObject(
        name="sam", location=location, control_point=control_point, task=None
    )
    assert FlightType.SCAR not in list(sam.mission_types(for_player=Player.BLUE))
