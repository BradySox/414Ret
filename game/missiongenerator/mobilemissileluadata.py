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

#: The default category this feature moves: theater-missile sites (SCUD/SSM). Never
#: anti-air -- IADS/MANTIS owns those.
MOBILE_MISSILE_CATEGORY = "missile"
#: Coastal anti-ship sites (e.g. Silkworm batteries) -- opted in per-campaign by the
#: ``coastal_missile_relocation`` setting (default off). Excluded by default because a
#: shore battery's geometry is usually authored against the water it covers; a naval
#: campaign (the Tanker War) turns it on so the coastal-missile hunt is a hunt for
#: something that moves.
COASTAL_DEFENSE_CATEGORY = "coastal"

#: DCS unit types that physically cannot drive. The vanilla Silkworm battery
#: (HY-2 launcher + its search radar) is a fixed emplacement -- routing it
#: produces no movement, only a per-frame "has request to level but
#: 'GT.maxDeviationRoll' are not set!" ground-AI storm (~15k log events in the
#: first scoot-tick minute of the 2026-07-17 Scenic Route fly, ANTIFREEZE for
#: the whole mission). A group containing any of these is never emitted;
#: mod coastal sites with genuinely mobile launchers still scoot.
IMMOBILE_UNIT_IDS = frozenset({"hy_launcher", "Silkworm_SR"})


def populate_mobile_missiles_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Build the ``dcsRetribution.mobileMissiles`` subtree (shoot-and-scoot sites)."""
    categories: set[str] = set()
    if getattr(game.settings, "mobile_missile_relocation", False):
        categories.add(MOBILE_MISSILE_CATEGORY)
    if getattr(game.settings, "coastal_missile_relocation", False):
        categories.add(COASTAL_DEFENSE_CATEGORY)
    if not categories:
        return

    # Fire-mission hold deadlines recorded by MissileSiteGenerator (guarded:
    # tests call with mission_data=None).
    fire_missions: dict[str, int] = (
        getattr(mission_data, "missile_fire_missions", None) or {}
    )

    sites: list[dict[str, Any]] = []
    for cp in game.theater.controlpoints:
        for tgo in cp.ground_objects:
            if getattr(tgo, "category", None) not in categories:
                continue
            groups = _mobile_group_names(tgo)
            pos = getattr(tgo, "position", None)
            if not groups or pos is None or not hasattr(pos, "x"):
                continue
            # §49 fire-then-scoot: a group carrying a scripted fire mission
            # (MissileSiteGenerator's Hold -> FireAtPoint, recorded on the
            # mission data) must not be routed until it has fired -- the scoot's
            # setTask would replace the pending fire task (the 2026-07-16 flown
            # clobber). Forward each such group's hold deadline to the plugin.
            holds = {
                name: fire_missions[name] for name in groups if name in fire_missions
            }
            sites.append({"groups": groups, "x": pos.x, "y": pos.y, "holds": holds})
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
        if site["holds"]:
            # Parallel arrays (a LuaData record cannot mix key-values with
            # nested items -- serialize drops the scalars): fireHoldGroups[i]
            # holds its fire mission until fireHoldS[i] seconds.
            names = list(site["holds"])
            rec.add_data_array("fireHoldGroups", names)
            rec.add_data_array("fireHoldS", [str(site["holds"][n]) for n in names])


def _mobile_group_names(tgo: Any) -> list[str]:
    """The TGO's groups that contain at least one *alive vehicle* -- the drivable metal.
    A statics-only group (or a fully dead one) has nothing to route and is skipped, and
    so is any group carrying an IMMOBILE_UNIT_IDS unit -- mist.goRoute routes every
    member of a group, so one undrivable emplacement in it turns the whole route push
    into ground-AI leveling spam."""
    names: list[str] = []
    for group in getattr(tgo, "groups", []):
        name = getattr(group, "group_name", None)
        if not name:
            continue
        units = getattr(group, "units", [])
        alive_vehicles = [
            u
            for u in units
            if getattr(u, "is_vehicle", False) and getattr(u, "alive", False)
        ]
        if not alive_vehicles:
            continue
        if any(
            getattr(getattr(u, "type", None), "id", None) in IMMOBILE_UNIT_IDS
            for u in alive_vehicles
        ):
            continue
        names.append(name)
    return names
