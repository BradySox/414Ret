"""Mission-start briefing popup -> Lua config bridge (``dcsRetribution.briefing``).

The professional DCS campaigns greet a pilot who slots in with a short on-screen
card -- campaign, mission, time, date, callsign, field -- so you always know what
you are flying before you have opened a kneeboard. This emitter recreates that for
the dynamic campaign: it lists the shared header (campaign name, mission number,
date, mission clock) once, plus one record per **player-crewed** flight carrying
that flight's callsign, airframe, task, and departure field. The ``briefing``
plugin shows each player their own card for a few seconds when they enter a slot
(``S_EVENT_BIRTH``), so it fires at mission start in single-player and whenever a
pilot slots in / rejoins on a server.

Display-only: no gameplay-model change, no ``.miz`` object, no persistence. The
plugin owns nothing but the text.

Emits nothing when ``mission_briefing_popup`` is off, or when the mission has no
player-crewed flight, so such missions carry no ``briefing`` node and the plugin
no-ops. All fields are single-line strings -- the Lua composes the multi-line card
with real newlines, because ``escape_string_for_lua`` does not escape ``\\n`` (and a
literal newline inside a Lua 5.1 ``"..."`` literal is a parse error).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData


def populate_briefing_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Build the ``dcsRetribution.briefing`` subtree (mission-start popup)."""
    if not getattr(game.settings, "mission_briefing_popup", False):
        return

    player_flights = [flight for flight in mission_data.flights if flight.client_units]
    if not player_flights:
        return

    node = root.add_item("briefing")

    # Shared header -- the same for every flight, emitted once. Sourced to match the
    # kneeboard cover page (§30): the campaign date is game.current_day, the mission
    # clock is conditions.start_time. Mission number is turn + 1 (game.turn is
    # 0-indexed) so the first sortie reads "Mission 1".
    header = node.add_item("header")
    header.add_key_value("campaign", game.campaign_name or "")
    header.add_key_value("mission", str(game.turn + 1))
    header.add_key_value("date", game.current_day.strftime("%A %d %B %Y"))
    header.add_key_value("time", game.conditions.start_time.strftime("%H:%M") + "L")

    flights_item = node.add_item("flights")
    for flight in player_flights:
        rec = flights_item.add_item()
        # group_name is what unit:getGroup():getName() returns at runtime, so the
        # plugin can match the slotting pilot's group to its card.
        rec.add_key_value("group", flight.group_name)
        rec.add_key_value("callsign", flight.callsign)
        rec.add_key_value("aircraft", flight.aircraft_type.display_name)
        # Doctrine-aware task label (the Vietnam rename layer etc.).
        rec.add_key_value("task", flight.task_display_name)
        rec.add_key_value("airfield", flight.departure.airfield_name)
