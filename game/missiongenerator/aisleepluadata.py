"""Ground AI sleep -> Lua config bridge (``dcsRetribution.aiSleep``).

The graduated alternative to binary culling (the "all or nothing" complaint): with
``perf_ground_ai_sleep`` on, this emitter lists every rear-area *garrison* vehicle
group (``TheaterGroundObject.category == "armor"``) and the ``aisleep`` plugin puts
each one's DCS controller to sleep at mission start, waking it only while an
aircraft -- either side's, human or AI -- is inside the wake radius. The units keep
existing (visible, strikeable, recon/BDA and threat rings stay honest, deaths record
natively), they just stop *thinking* while nobody is near, which is where the sim
cost of hundreds of garrison units actually goes.

Safety is decided HERE, in Python, as a positive list -- the plugin never guesses:

* Only ``armor``-category TGO groups are eligible. The air-defense network
  (``aa``/``ewr`` -- MANTIS owns it, and we have crash scars from toggling SAM state
  at runtime), theater/coastal missile sites (the mobilemissiles movers), ships,
  motorpool depots (already inert by construction) and building TGOs are never
  emitted.
* ``concealed`` / ``map_hidden`` TGOs are skipped -- that set is exactly the COIN /
  convoy-ambush scripted movers (cells, HVT convoys, VBIEDs, ambush teams), whose
  routes a sleeping controller would silently kill.
* FLOT units, convoys and Combat-SAR spawns are not TGOs, so the TGO walk can never
  touch them.

An armor garrison may carry embedded SHORAD/MANPAD escorts, so the plugin
floors its wake radius well above their reach -- the group is awake long before
anything enters its engagement envelope.

Emits nothing when the setting is off or no eligible group exists, so such missions
carry no ``aiSleep`` node and the plugin no-ops.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData

#: The one eligible TGO category: deployed/garrison vehicle groups
#: (VehicleGroupGroundObject). Everything else is excluded by construction -- see
#: the module docstring for why each other category must never sleep.
SLEEPABLE_CATEGORIES = frozenset({"armor"})


def populate_ai_sleep_lua(
    root: "LuaData", game: "Game", mission_data: Optional["MissionData"] = None
) -> None:
    """Build the ``dcsRetribution.aiSleep`` subtree (sleepable garrison groups)."""
    if not getattr(game.settings, "perf_ground_ai_sleep", False):
        return

    names: list[str] = []
    for cp in game.theater.controlpoints:
        for tgo in cp.ground_objects:
            if getattr(tgo, "category", None) not in SLEEPABLE_CATEGORIES:
                continue
            # The concealed/map-hidden set is exactly the scripted movers (COIN
            # cells/HVT/VBIEDs, convoy-ambush teams); a sleeping controller would
            # silently stop their routes.
            if getattr(tgo, "concealed", False) or getattr(tgo, "map_hidden", False):
                continue
            names.extend(_sleepable_group_names(tgo))
    if not names:
        return

    node = root.add_item("aiSleep")
    # The exact names Group.getByName needs (TheaterGroup.group_name, what the
    # generator stamps onto the .miz vehicle group).
    node.add_data_array("groups", names)


def _sleepable_group_names(tgo: Any) -> list[str]:
    """The TGO's groups holding at least one alive vehicle -- the thinking metal.
    A statics-only group has no controller worth sleeping; a dead one has none."""
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
