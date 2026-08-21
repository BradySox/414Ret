"""Mobile missile sites -> Lua config bridge (``dcsRetribution.mobileMissiles``).

The SCUD hunt, made a hunt. A mobile theater-missile site (SCUD/SSM group --
``TheaterGroundObject.category == "missile"``) has always spawned parked exactly where
the campaign map says it is, so "hunting" it was flying to a coordinate. With
``mobile_missile_relocation`` on, this emitter lists each side's missile-site vehicle
groups + their campaign position, and the ``mobilemissiles`` plugin drives them on a slow
shoot-and-scoot wander around that position at runtime (alarm-green -- they relocate,
they don't stop to fight), so the launcher is never quite where the last recon photo
froze it.

**Movement only**, the COIN mover pattern: kills record natively (the
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

#: The only category this feature moves: theater-missile sites (SCUD/SSM). Never
#: anti-air -- IADS/MANTIS owns those. Coastal anti-ship sites had an opt-in until
#: 2026-08-21; the vanilla Silkworm battery is a fixed emplacement, so it moved nothing.
MOBILE_MISSILE_CATEGORY = "missile"

#: DCS unit types that physically cannot drive; a group containing one is never
#: emitted. Routing a fixed emplacement produces no movement, only a per-frame
#: ground-AI storm that ANTIFREEZEs the whole mission. Per-entry flown evidence is
#: in docs/dev/414th-features.md §49.
#:
#: ``CH_Shahed136`` is deliberately NOT listed -- its never-fired sites drive fine,
#: so excluding it would kill a scoot that does work before the salvo.
#:
#: The verdicts live in the units' own ``mobile: false``; this set is the fallback
#: for a DCS type with no registered yaml, and a test keeps the two in lockstep.
IMMOBILE_UNIT_IDS = frozenset({"hy_launcher", "Silkworm_SR", "CH_CJ10", "v1_launcher"})


def populate_mobile_missiles_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Build the ``dcsRetribution.mobileMissiles`` subtree (shoot-and-scoot sites)."""
    if not getattr(game.settings, "mobile_missile_relocation", False):
        return

    # Fire-mission hold deadlines recorded by MissileSiteGenerator (guarded:
    # tests call with mission_data=None).
    fire_missions: dict[str, int] = (
        getattr(mission_data, "missile_fire_missions", None) or {}
    )

    sites: list[dict[str, Any]] = []
    for cp in game.theater.controlpoints:
        for tgo in cp.ground_objects:
            if getattr(tgo, "category", None) != MOBILE_MISSILE_CATEGORY:
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


def _is_immobile(dcs_type: Any) -> bool:
    """True if this DCS type physically cannot drive (see IMMOBILE_UNIT_IDS).

    Reads the unit definition's ``mobile:`` flag, falling back to the id set for
    a type with no registered ``GroundUnitType`` (statics, unregistered mod
    hardware) so an unknown type is never treated as immobile by accident.
    """
    type_id = getattr(dcs_type, "id", None)
    if type_id is None:
        return False
    if type_id in IMMOBILE_UNIT_IDS:
        return True
    try:
        from game.dcs.groundunittype import GroundUnitType

        return any(not unit.mobile for unit in GroundUnitType.for_dcs_type(dcs_type))
    except Exception:  # pragma: no cover - unregistered/duck-typed test units
        return False


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
        if any(_is_immobile(getattr(u, "type", None)) for u in alive_vehicles):
            continue
        names.append(name)
    return names
