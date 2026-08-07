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

from typing import TYPE_CHECKING

from game.data.carrier_deck_decor import STATIC_META

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData


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
