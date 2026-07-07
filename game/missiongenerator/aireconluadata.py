"""AI recon auto-capture -> Lua config bridge (dcsRetribution.AIRecon).

The MOOSE TARS engine (resources/plugins/tars) that turns a TARPS overflight into a
confirmed-BDA capture is **player-only**: its birth handler drops any unit that isn't
player-crewed (``TARS.lua`` ``if not unit or not unit:GetPlayerName() then return end``).
So the campaign's auto-paired *AI* recon flights fly the recon path but never contribute a
single BDA capture, no matter that they overfly and survive (checklist G19).

This closes that gap without touching the player TARS path: Python emits each **AI-flown,
player-coalition recon-capable flight** + its target point, and the ``airecon`` plugin
records the enemy ground units at the target into the same ``tars_recon_captures`` ledger
the player path writes when such a flight survives to overfly. The debrief side
(``game/debriefing.py`` ``parse_tars_captures`` -> ``tars_reconned_tgos``) then treats an
AI recon capture exactly like a player one.

**A drone is always filming (414th rule).** A UAV (``UAV_DCS_IDS``) is a sensor first --
it feeds recon/BDA home *regardless of its tasked mission*: off on a solo recon, riding
shotgun on a strike as the JTAC, or working CAS, it is still photographing what it
overflies. So the capture is emitted for **any AI-flown blue drone**, not only the
TARPS-tasked flights (a manned bird only feeds it when actually tasked TARPS). The plugin
is unchanged -- it just banks BDA for whatever groups are emitted.

Player-crewed flights are **never** emitted here -- they still use the F10 film menu.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.ato import FlightType
from game.data.units import UAV_DCS_IDS
from game.theater import Player

if TYPE_CHECKING:
    from game import Game

    from .aircraft.flightdata import FlightData
    from .luagenerator import LuaData
    from .missiondata import MissionData


def _feeds_ai_recon(flight: "FlightData") -> bool:
    """Whether this AI blue flight banks BDA when it overflies its target.

    A TARPS-tasked flight (any airframe -- the auto-paired recon bird) always does; and
    a drone always does regardless of task (a drone is always filming). Manned combat
    flights do not -- they are not sensors.
    """
    if flight.flight_type is FlightType.TARPS:
        return True
    return flight.aircraft_type.dcs_unit_type.id in UAV_DCS_IDS


def populate_ai_recon_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Emit one record per AI-flown, player-coalition recon flight + its target.

    Covers TARPS-tasked flights *and* every AI drone (a drone always films). Emits
    nothing (no ``AIRecon`` node) when there are no such flights, so the plugin no-ops. A
    flight carrying any human is skipped -- that pilot films via the F10 TARS menu. Only
    the player coalition's (BLUE) recon feeds the player's BDA fog-of-war; the AI opponent
    plans on ground truth and needs no recon ledger.
    """
    flights: list[tuple[str, str, str, float, float]] = []
    for flight in mission_data.flights:
        if not _feeds_ai_recon(flight):
            continue
        if flight.client_units:
            continue  # a human is aboard -> the F10 TARS film path handles it
        if flight.friendly is not Player.BLUE:
            continue  # only the human coalition's recon feeds the BDA ledger
        target = flight.package.target
        position = getattr(target, "position", None)
        if position is None:
            continue
        # Human-readable identity for the coalition BDA cue: two identical
        # "recon flight confirmed BDA" popups minutes apart are indistinguishable
        # without naming the flight and where it was looking.
        label = f"{flight.callsign} ({flight.aircraft_type.display_name})"
        flights.append((flight.group_name, label, target.name, position.x, position.y))

    if not flights:
        return

    recon = root.add_item("AIRecon")
    flights_item = recon.add_item("flights")
    for group_name, label, target_name, x, y in flights:
        record = flights_item.add_item()
        record.add_key_value("group", group_name)
        record.add_key_value("label", label)
        record.add_key_value("target", target_name)
        # pydcs Point: x = north, y = east. The Lua maps these onto the DCS world.
        record.add_key_value("x", str(x))
        record.add_key_value("y", str(y))
