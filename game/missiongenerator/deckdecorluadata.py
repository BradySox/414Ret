"""Launch-phase carrier deck dressing -> Lua bridge (``dcsRetribution.deckDecor``).

The §72 aircraft tier may place statics that stand INSIDE the recovery corridor
-- campaign A's round-down E-2C -- because they only exist while the deck is a launch
deck. Statics cannot drive (no AI), so "moving" one means striking it below:
the ``deckdecor`` plugin despawns each boat's launch-phase statics
(``StaticObject:destroy``, silent -- the elevator ride, narratively) on a
fallback timer or the moment fixed-wing traffic appears low astern, whichever
comes first.

One record per carrier that received launch-phase dressing: the ship group
name (to find the moving boat at runtime), the flagship unit name (log
readability), the coalition side (whose fixed-wing traffic arms the astern
cone), the generation-time BRC (the boat steams that course all mission, so
the plugin needs no runtime orientation API), and the static unit names to
clear. Emits nothing when no launch-phase static was placed, so the plugin
no-ops.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from game.data.carrier_deck_decor import STATIC_META

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData


#: Margin (s) after the last flight leaves a deck before that deck may respot
#: for recovery. Covers the difference between the planned departure delay and
#: the actual takeoff roll, which is minutes for a cold start. Doubles as the
#: idle gap that ends a launch cycle -- both are "this deck is done" in seconds,
#: and inventing a second constant would only let the two drift.
LAUNCH_CYCLE_MARGIN_S = 600


def launch_cycle_ends_at(mission_data: "MissionData", carrier_unit_name: str) -> int:
    """Seconds after mission start when this deck's CURRENT launch cycle ends.

    A deck cannot respot for recovery while it is still a launch deck, and the
    plan already knows when each jet leaves it. Flown 2026-08-16: the recovery
    set spawned at t+79 s of a 2,233 s mission -- 375 s before the player's own
    takeoff roll -- putting three static Hornets in his taxi lane, one of them
    8.66 m off his track. The astern cone had tripped on something that could not
    be identified from the recording, so this bounds what a spurious trip can do
    rather than relying on finding every trip source.

    The cycle is the run of departures from the first, broken by an idle gap
    longer than ``LAUNCH_CYCLE_MARGIN_S``. It is NOT the last departure in the
    ATO: ``departure_delay`` is the whole wait until a flight's scheduled start,
    which for a late package is hours. Flown 2026-08-16 (5th test): a single such
    flight held CVN-71 to t+11,388 s of a 19-minute mission, so the deck never
    respotted at all -- the previous "latest departure" reading traded one
    failure for its mirror image.

    Matched on ``RunwayData.airfield_name``, which for a carrier is the control
    point's name and equals the flagship unit's name -- the same string
    ``DeckDecorInfo.carrier_unit_name`` carries. Zero when nothing launches from
    this deck, leaving the existing deadline and cone in sole charge (the
    pre-2026-08-16 behaviour).
    """
    delays: list[int] = []
    for flight in getattr(mission_data, "flights", None) or []:
        departure = getattr(flight, "departure", None)
        if getattr(departure, "airfield_name", None) != carrier_unit_name:
            continue
        delay = getattr(flight, "departure_delay", None)
        delays.append(int(delay.total_seconds()) if delay is not None else 0)
    if not delays:
        logging.info(
            "DECKDECOR: nothing launches from %s; the recovery respot is left to "
            "the cone and the fallback deadline.",
            carrier_unit_name,
        )
        return 0

    delays.sort()
    cycle_end = delays[0]
    in_cycle = 1
    for delay in delays[1:]:
        if delay - cycle_end > LAUNCH_CYCLE_MARGIN_S:
            break
        cycle_end = delay
        in_cycle += 1
    logging.info(
        "DECKDECOR: %s launches %d flight(s), %d in the current cycle; respot held "
        "until t+%ds.",
        carrier_unit_name,
        len(delays),
        in_cycle,
        cycle_end + LAUNCH_CYCLE_MARGIN_S,
    )
    return cycle_end + LAUNCH_CYCLE_MARGIN_S


def populate_deck_decor_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Build the ``dcsRetribution.deckDecor`` subtree (launch-phase clears)."""
    if not mission_data.deck_decor:
        return

    node = root.add_item("deckDecor")
    boats = node.add_item("boats")
    for info in mission_data.deck_decor:
        rec = boats.add_item()
        rec.add_key_value("group", info.ship_group_name)
        rec.add_key_value("unit", info.carrier_unit_name)
        # DCS coalition side id: 1 red, 2 blue.
        rec.add_key_value("side", "2" if info.blue else "1")
        rec.add_key_value(
            "earliestClearS",
            str(launch_cycle_ends_at(mission_data, info.carrier_unit_name)),
        )
        rec.add_key_value("brc", f"{info.brc_degrees:.1f}")
        rec.add_data_array("clearNames", info.clear_names)
        # Recovery-phase spawns: absent from the mission by design, so the
        # plugin needs the full placement, not just a name. Category and shape
        # come from STATIC_META so the Lua side never has to know the table.
        if info.recovery_specs:
            spawns = rec.add_item("recoverySpawns")
            for item in info.recovery_specs:
                category, shape_name = STATIC_META[item.type]
                spec = spawns.add_item()
                spec.add_key_value("type", item.type)
                spec.add_key_value("category", category)
                if shape_name is not None:
                    spec.add_key_value("shape", shape_name)
                spec.add_key_value("x", f"{item.x:.2f}")
                spec.add_key_value("y", f"{item.y:.2f}")
                spec.add_key_value("angle", f"{item.angle_deg:.1f}")
