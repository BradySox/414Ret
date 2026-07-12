"""Helo cruise waypoints use the dedicated cruise AGL setting.

``WaypointBuilder.get_altitude`` short-circuits every helo altitude to the
*combat* AGL setting, which pressed all transit waypoints (JOIN/HOLD/REFUEL/NAV)
to treetop height -- 100 ft AGL through the Harz was the flown Red Tide M1 helo
CFIT pattern. ``get_cruise_altitude`` must return ``heli_cruise_alt_agl`` for
helos (the pattern ferry.py/rtb.py already use) while combat legs keep the
combat setting and fixed-wing is untouched.
"""

from types import SimpleNamespace
from typing import Any

from game.ato.flightplans.waypointbuilder import WaypointBuilder
from game.ato.flighttype import FlightType
from game.data.doctrine import MODERN_DOCTRINE
from game.utils import Distance, feet


def _wb(
    is_helo: bool,
    combat_agl: int = 200,
    cruise_agl: int = 500,
    preferred_cruise: Distance = feet(25000),
    preferred_combat: Distance = feet(12000),
) -> Any:
    wb: Any = WaypointBuilder.__new__(WaypointBuilder)
    wb.doctrine = MODERN_DOCTRINE
    settings = SimpleNamespace(
        heli_combat_alt_agl=combat_agl,
        heli_cruise_alt_agl=cruise_agl,
    )
    wb.settings = settings
    wb.flight = SimpleNamespace(
        flight_type=FlightType.TRANSPORT,
        is_helo=is_helo,
        plane_altitude_offset=0,
        unit_type=SimpleNamespace(
            preferred_cruise_altitude=preferred_cruise,
            preferred_combat_altitude=preferred_combat,
            dcs_unit_type=SimpleNamespace(id="Mi-8MT"),
        ),
        coalition=SimpleNamespace(game=SimpleNamespace(settings=settings)),
    )
    return wb


def test_helo_cruise_altitude_uses_the_cruise_setting() -> None:
    wb = _wb(is_helo=True, combat_agl=100, cruise_agl=500)
    assert wb.get_cruise_altitude == feet(500)


def test_helo_combat_altitude_still_uses_the_combat_setting() -> None:
    wb = _wb(is_helo=True, combat_agl=100, cruise_agl=500)
    assert wb.get_combat_altitude == feet(100)


def test_fixed_wing_cruise_altitude_unchanged() -> None:
    wb = _wb(is_helo=False, preferred_cruise=feet(25000))
    # Fixed wing routes through get_altitude: the preferred cruise clamped to
    # the doctrine band (25,000 ft is inside the modern band, so unchanged).
    assert wb.get_cruise_altitude == feet(25000)
