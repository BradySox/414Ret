"""Mobile missile sites -> Lua config bridge (``dcsRetribution.mobileMissiles``).

The SCUD hunt, made a hunt. A mobile theater-missile site (SCUD/SSM group --
``TheaterGroundObject.category == "missile"``) has always spawned parked exactly where
the campaign map says it is, so "hunting" it was flying to a coordinate. With
``mobile_missile_relocation`` on, this emitter lists each side's missile-site vehicle
groups + their campaign position, and the ``mobilemissiles`` plugin drives them on a slow
shoot-and-scoot wander around that position at runtime (alarm-green -- they relocate,
they don't stop to fight), so the launcher is never quite where the last recon photo
froze it.

**Movement only**, the Combat-SAR / COIN mover pattern: kills record natively (the
routed DCS group is the same one the force model owns), the site never migrates beyond
the plugin's scoot radius of its campaign position (threat rings and the turn-boundary
model stay honest), and a dead site simply stops being routed. The radar SAM network is
untouched by construction -- MERAD/LORAD/SHORAD are different TGO categories, so MANTIS
never sees a moved emitter.

Symmetric (both sides' mobile missile sites). Emits nothing when the setting is off or
no live vehicle-carrying missile site exists, so such missions carry no
``mobileMissiles`` node and the plugin no-ops.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData

#: The TGO category this feature moves. Deliberately ONLY the theater-missile sites --
#: never anti-air (IADS/MANTIS owns those) and never the coastal anti-ship sites (their
#: geometry is authored against the water they cover).
MOBILE_MISSILE_CATEGORY = "missile"


def populate_mobile_missiles_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Build the ``dcsRetribution.mobileMissiles`` subtree (shoot-and-scoot sites)."""
    if not getattr(game.settings, "mobile_missile_relocation", False):
        return

    sites: list[dict[str, Any]] = []
    for cp in game.theater.controlpoints:
        for tgo in cp.ground_objects:
            if getattr(tgo, "category", None) != MOBILE_MISSILE_CATEGORY:
                continue
            groups = _mobile_group_names(tgo)
            pos = getattr(tgo, "position", None)
            if not groups or pos is None or not hasattr(pos, "x"):
                continue
            sites.append({"groups": groups, "x": pos.x, "y": pos.y})
    if not sites:
        return

    node = root.add_item("mobileMissiles")
    site_list = node.add_item("sites")
    for site in sites:
        rec = site_list.add_item()
        # The exact names Group.getByName needs (TheaterGroup.group_name, what the
        # generator stamps onto the .miz vehicle group).
        rec.add_data_array("groups", site["groups"])
        # pydcs Point: x = north, y = east (the emitter frame the coin plugin shares).
        rec.add_key_value("x", str(site["x"]))
        rec.add_key_value("y", str(site["y"]))


def _mobile_group_names(tgo: Any) -> list[str]:
    """The TGO's groups that contain at least one *alive vehicle* -- the drivable metal.
    A statics-only group (or a fully dead one) has nothing to route and is skipped."""
    names: list[str] = []
    for group in getattr(tgo, "groups", []):
        name = getattr(group, "group_name", None)
        if not name:
            continue
        units = getattr(group, "units", [])
        if any(
            getattr(u, "is_vehicle", False) and getattr(u, "alive", False)
            for u in units
        ):
            names.append(name)
    return names
