"""Air-dropped minefields -> Lua config bridge (``dcsRetribution.minefields``).

Re-arms persisted fields (§57 Phase 2). The turn-boundary reconcile
(``game/fourteenth/minefields.py``) carries every field left undisturbed across the turn on
``game.minefields``; this emitter lists the live ones so the ``minefields`` plugin re-creates
each proximity field at mission start -- exactly where it was, with its remaining charges.
Fields laid *this* mission come from the plugin's own ``S_EVENT_SHOT`` detection, not from here.

Emits nothing unless ``air_droppable_minefields`` is on and at least one live field exists, so a
normal mission carries no ``minefields`` node and the plugin only watches for fresh drops.
Coordinates are ``x`` = north (``Point.x``) / ``z`` = east (``Point.y``) -- the DCS ``getPoint``
frame the plugin works in (distinct from the ``x``/``y`` convoy-ambush emitter uses).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData


def populate_minefields_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Build the ``dcsRetribution.minefields`` subtree (persisted fields to re-arm)."""
    if not getattr(game.settings, "air_droppable_minefields", False):
        return

    from game.fourteenth.minefields import active_minefields

    fields = active_minefields(game)
    if not fields:
        return

    node = root.add_item("minefields")
    field_list = node.add_item("fields")
    for minefield in fields:
        rec = field_list.add_item()
        rec.add_key_value("id", str(minefield.id))
        rec.add_key_value("x", str(minefield.position.x))
        rec.add_key_value("z", str(minefield.position.y))
        rec.add_key_value("radius", str(minefield.radius_m))
        rec.add_key_value("charges", str(minefield.charges))
