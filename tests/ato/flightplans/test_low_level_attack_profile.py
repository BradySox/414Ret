"""The doctrine low-level attack profile in the waypoint builder.

Under an authored ``low_level_attack_altitude`` (Vietnam), CAS/BAI/Armed-Recon
flights cap their combat-altitude legs at the doctrine ceiling -- pressing the
run in on the deck so AI deliveries can trip the runtime low/fast gates (§39
snake-and-nape) -- while every other tasking, helos, heavy bombers, and every
stock doctrine keep today's altitudes.
"""

from types import SimpleNamespace
from typing import Any, Optional

from dcs.mapping import Point
from dcs.terrain import Caucasus

from game.ato.flightplans.waypointbuilder import WaypointBuilder
from game.ato.flighttype import FlightType
from game.data.doctrine import (
    COLDWAR_DOCTRINE,
    Doctrine,
    MODERN_DOCTRINE,
    VIETNAM_DOCTRINE,
    WWII_DOCTRINE,
    low_level_attack_altitude_for,
)
from game.utils import Distance, feet, meters


def _wb(
    doctrine: Doctrine,
    flight_type: FlightType,
    unit_id: str = "A-1H",
    preferred: Distance = feet(12000),
    is_helo: bool = False,
    clouds: Optional[object] = None,
) -> Any:
    wb: Any = WaypointBuilder.__new__(WaypointBuilder)
    wb.doctrine = doctrine
    settings = SimpleNamespace(heli_combat_alt_agl=500)
    wb.settings = settings
    wb.flight = SimpleNamespace(
        flight_type=flight_type,
        is_helo=is_helo,
        plane_altitude_offset=0,
        unit_type=SimpleNamespace(
            preferred_combat_altitude=preferred,
            dcs_unit_type=SimpleNamespace(id=unit_id),
        ),
        coalition=SimpleNamespace(
            game=SimpleNamespace(
                conditions=SimpleNamespace(weather=SimpleNamespace(clouds=clouds)),
                settings=settings,
            )
        ),
    )
    return wb


def test_helper_caps_attack_tasks_under_vietnam() -> None:
    for flight_type in (FlightType.CAS, FlightType.BAI, FlightType.ARMED_RECON):
        assert low_level_attack_altitude_for(
            VIETNAM_DOCTRINE, flight_type, False, "A-1H"
        ) == feet(500), flight_type


def test_helper_exempts_other_tasks_helos_and_heavies() -> None:
    # Strike keeps its profile (Alpha Strike dive deliveries + B-52 Arc Light).
    for flight_type in (
        FlightType.STRIKE,
        FlightType.BARCAP,
        FlightType.ESCORT,
        FlightType.OCA_RUNWAY,
        FlightType.TARPS,
    ):
        assert (
            low_level_attack_altitude_for(VIETNAM_DOCTRINE, flight_type, False, "A-1H")
            is None
        ), flight_type
    # A helo keeps its own AGL logic; a heavy is never pressed onto the deck.
    assert (
        low_level_attack_altitude_for(VIETNAM_DOCTRINE, FlightType.CAS, True, "UH-1H")
        is None
    )
    assert (
        low_level_attack_altitude_for(VIETNAM_DOCTRINE, FlightType.BAI, False, "B-52H")
        is None
    )


def test_helper_is_inert_for_stock_doctrines() -> None:
    for doctrine in (MODERN_DOCTRINE, COLDWAR_DOCTRINE, WWII_DOCTRINE):
        assert (
            low_level_attack_altitude_for(doctrine, FlightType.CAS, False, "A-1H")
            is None
        ), doctrine.name


def test_combat_altitude_pressed_to_the_deck_for_vietnam_attack_runs() -> None:
    # The airframe prefers 12,000 ft; the authored profile wins (below the
    # doctrine's own min_combat_altitude by design).
    assert _wb(VIETNAM_DOCTRINE, FlightType.BAI).get_combat_altitude == feet(500)


def test_combat_altitude_unchanged_for_stock_doctrine_and_other_tasks() -> None:
    assert _wb(COLDWAR_DOCTRINE, FlightType.BAI).get_combat_altitude == feet(12000)
    assert _wb(VIETNAM_DOCTRINE, FlightType.STRIKE).get_combat_altitude == feet(12000)
    assert _wb(
        VIETNAM_DOCTRINE, FlightType.BAI, unit_id="B-52H"
    ).get_combat_altitude == feet(12000)


def test_cas_track_floor_bypassed_by_the_low_level_profile() -> None:
    # The stock CAS track floors at 1,000 m AGL; the authored profile presses the
    # track down to its own ceiling instead.
    position = Point(0, 0, Caucasus())
    wb = _wb(VIETNAM_DOCTRINE, FlightType.CAS)
    wp = wb.cas(position, wb.get_combat_altitude)
    assert wp.alt == feet(500)
    assert wp.alt_type == "RADIO"

    stock = _wb(COLDWAR_DOCTRINE, FlightType.CAS, preferred=feet(2000))
    stock_wp = stock.cas(position, stock.get_combat_altitude)
    assert stock_wp.alt == meters(1000)
