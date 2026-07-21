"""CI lock on the Growler-only ESCORT_JAMMER role (2026-07-21).

Escort jamming is the EA-18G's job and nobody else's (user call: the FA-18E/F
never fly it). Capability comes solely from the yaml ``tasks:`` block -- only
EA-18G.yaml declares ``Escort Jammer`` -- and the planner adds the escort on the
same radar-SAM trigger as the SEAD escorts, pruning it silently when no capable
squadron exists. These tests pin the enum wiring, the capability boundary, the
loadout fallback (SEAD Escort stores: pods + ARMs), and the escort-threat
plumbing so an upstream merge can't quietly drop a seam.
"""

from types import SimpleNamespace

import pytest

from game import persistency
from game.ato.flighttype import FlightType
from game.ato.flightplans.escort import EscortFlightPlan
from game.ato.flightplans.flightplanbuildertypes import FlightPlanBuilderTypes
from game.ato.loadouts import Loadout
from game.commander.missionproposals import EscortType
from game.commander.packagefulfiller import PackageFulfiller
from game.dcs.aircrafttype import AircraftType
from game.sidc import AirEntity


@pytest.fixture(autouse=True, scope="module")
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    # Resolving an AircraftType reads the DCS saved-game folder (weapon
    # injections), which is only configured once the app boots. Point it at an
    # empty temp dir so it falls back to the bundled resources/ data.
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


def test_escort_jammer_enum_wiring() -> None:
    task = FlightType.ESCORT_JAMMER
    assert task.value == "Escort Jammer"
    assert task.is_escort_type
    assert task.provides_escort_coverage
    # The jamming effect is scripted; the flight itself is neither an A2A nor
    # an A2G shooter for planner categorization.
    assert not task.is_air_to_air
    assert not task.is_air_to_ground
    assert not task.is_primary_package_task
    assert task.entity_type is AirEntity.ELECTRONIC_COMBAT_JAMMER


def test_escort_jammer_uses_the_escort_flight_plan() -> None:
    # Rides the package join->split like the SEAD escort -- never a standoff
    # racetrack (that is the C-130's JAMMING task, deliberately distinct).
    flight = SimpleNamespace(flight_type=FlightType.ESCORT_JAMMER)
    assert (
        FlightPlanBuilderTypes.for_flight(flight)  # type: ignore[arg-type]
        is EscortFlightPlan.builder_type()
    )


def test_escort_jammer_is_growler_only() -> None:
    """The capability boundary: only the EA-18G declares the task."""
    growler = AircraftType.named("EA-18G Growler")
    assert growler.capable_of(FlightType.ESCORT_JAMMER)
    for variant in (
        "F/A-18E Super Hornet",
        "F/A-18F Super Hornet",
        "F/A-18C Hornet (Lot 20)",
    ):
        other = AircraftType.named(variant)
        assert not other.capable_of(FlightType.ESCORT_JAMMER), (
            f"{variant} must never fly the jamming escort -- the role is "
            "Growler-only (user call 2026-07-21)"
        )


def test_escort_jammer_loadout_falls_back_to_sead_escort() -> None:
    names = list(Loadout.default_loadout_names_for(FlightType.ESCORT_JAMMER))
    own = names.index("Retribution Escort Jammer")
    fallback = names.index("Retribution SEAD Escort")
    # A dedicated Escort Jammer preset wins when one exists; otherwise the
    # SEAD Escort fit (ALQ-99 pods + ARMs on the EA-18G) is the right stores.
    assert own < fallback


def test_can_plan_escort_routes_jammer_to_escort_jammer() -> None:
    asked: list[FlightType] = []

    def air_wing_can_plan(task: FlightType) -> bool:
        asked.append(task)
        return task is FlightType.ESCORT_JAMMER

    stub = SimpleNamespace(air_wing_can_plan=air_wing_can_plan)
    assert PackageFulfiller.can_plan_escort(stub, EscortType.Jammer)  # type: ignore[arg-type]
    assert asked == [FlightType.ESCORT_JAMMER]


def test_radar_sam_threat_requests_the_jammer_escort() -> None:
    """check_needed_escorts marks Jammer alongside Sead on a radar-SAM route."""
    flight = SimpleNamespace(
        flight_plan=SimpleNamespace(escorted_waypoints=lambda: iter(()))
    )
    builder = SimpleNamespace(
        package=SimpleNamespace(flights=[flight], primary_flight=None)
    )
    threat_zones = SimpleNamespace(
        waypoints_threatened_by_aircraft_engagement=lambda waypoints: False,
        waypoints_threatened_by_radar_sam=lambda waypoints: True,
    )
    stub = SimpleNamespace(
        threat_zones=threat_zones,
        doctrine=SimpleNamespace(always_escort_strikes=False),
    )
    threats = PackageFulfiller.check_needed_escorts(stub, builder)  # type: ignore[arg-type]
    assert threats[EscortType.Sead]
    assert threats[EscortType.Jammer]
    assert not threats[EscortType.AirToAir]
