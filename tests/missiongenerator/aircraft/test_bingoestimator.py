import pytest
from dcs import Point
from dcs.terrain import Terrain, Caucasus

from game.ato import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.dcs.aircrafttype import FuelConsumption
from game.missiongenerator.aircraft.bingoestimator import BingoEstimator
from game.utils import nautical_miles


@pytest.fixture(name="terrain")
def terrain_fixture() -> Terrain:
    return Caucasus()


@pytest.fixture(name="waypoints")
def waypoints_fixture(terrain: Terrain) -> list[FlightWaypoint]:
    return [
        FlightWaypoint(
            "", FlightWaypointType.NAV, Point(0, nautical_miles(d).meters, terrain)
        )
        for d in range(101)
    ]


def test_legacy_bingo_estimator(
    waypoints: list[FlightWaypoint], terrain: Terrain
) -> None:
    estimator = BingoEstimator(None, Point(0, 0, terrain), None, waypoints)
    assert estimator.estimate_bingo() == 3000
    assert estimator.estimate_joker() == estimator.estimate_bingo() + 1000
    estimator = BingoEstimator(
        None, Point(0, 0, terrain), Point(0, 5, terrain), waypoints
    )
    assert estimator.estimate_bingo() == 4000
    assert estimator.estimate_joker() == estimator.estimate_bingo() + 1000


def test_fuel_consumption_based_bingo_estimator(
    waypoints: list[FlightWaypoint], terrain: Terrain
) -> None:
    consumption = FuelConsumption(100, 50, 10, 25, 1000)
    estimator = BingoEstimator(consumption, Point(0, 0, terrain), None, waypoints)
    assert estimator.estimate_bingo() == 2000
    assert estimator.estimate_joker() == estimator.estimate_bingo() + 1000
    estimator = BingoEstimator(
        consumption, Point(0, 0, terrain), Point(0, 5, terrain), waypoints
    )
    assert estimator.estimate_bingo() == 2000
    assert estimator.estimate_joker() == estimator.estimate_bingo() + 1000


def test_fuel_consumption_bingo_credits_a_tanker(terrain: Terrain) -> None:
    consumption = FuelConsumption(
        100, 50, 10, 25, 1000
    )  # cruise 10 lb/nm, reserve 1000

    def wp(d: int, kind: FlightWaypointType = FlightWaypointType.NAV) -> FlightWaypoint:
        return FlightWaypoint("", kind, Point(0, nautical_miles(d).meters, terrain))

    home = Point(0, 0, terrain)
    # Out to 100 nm, recovering at the field with nothing else on the route.
    without_tanker = [wp(0), wp(100), wp(0, FlightWaypointType.LANDING_POINT)]
    # Same depth, but a tanker 10 nm from the field on the egress: the deepest point now
    # only has to reach the tanker (90 nm), not the field (100 nm).
    with_tanker = [
        wp(0),
        wp(100),
        wp(10, FlightWaypointType.REFUEL),
        wp(0, FlightWaypointType.LANDING_POINT),
    ]
    base = BingoEstimator(consumption, home, None, without_tanker)
    refueled = BingoEstimator(consumption, home, None, with_tanker)

    assert base.estimate_bingo() == 2000  # 100 nm * 10 lb + 1000 reserve
    assert refueled.estimate_bingo() == 1900  # 90 nm to the tanker * 10 + 1000
    assert refueled.estimate_bingo() < base.estimate_bingo()
