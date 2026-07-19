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

* ``armor``-category TGO groups are always eligible. Theater/coastal missile sites
  (the mobilemissiles movers), ships, motorpool depots (already inert by
  construction) and building TGOs are never emitted.
* ``aa``-category (gun) sites join only under ``perf_aaa_site_sleep`` and only when
  they pass ``_air_defense_group_may_sleep`` -- see below. Dedicated ``ewr`` sites
  are never eligible at all; long-range search radar IS the thing the sleep would
  destroy.
* ``concealed`` / ``map_hidden`` TGOs are skipped -- that set is exactly the COIN /
  convoy-ambush scripted movers (cells, HVT convoys, VBIEDs, ambush teams), whose
  routes a sleeping controller would silently kill.
* FLOT units, convoys and Combat-SAR spawns are not TGOs, so the TGO walk can never
  touch them.

An armor garrison may carry embedded SHORAD/MANPAD escorts, so the plugin
floors its wake radius well above their reach -- the group is awake long before
anything enters its engagement envelope.

Why AAA guns can sleep at all (the 2026-07-19 perf finding). An AAA-doctrine
campaign is where the sim cost actually lives -- 1968 Yankee Station fields ~370
guns, 4-12x every other campaign -- and the ``armor``-only rule left all of it
thinking. Two independent guards make the gun sites safe to switch off:

* **Sensor reach.** ``AAA_SLEEP_MAX_DETECTION`` keeps a group awake unless every
  gun's DCS detection range is comfortably inside the plugin's wake-radius floor
  (10 NM = 18.5 km, the minimum the option allows). A Vietnam-era gun sees 5 km, so
  it is switched back on long before anything reaches the edge of its own sensor
  envelope -- what it feeds the IADS picture, and when it opens fire, are unchanged.
  A Gepard (15 km) and every real search/track radar (35-300 km) sit above the line
  and keep thinking.
* **Engine ownership.** MANTIS *writes* to the roles in ``MANTIS_MANAGED_ROLES``
  (alarm state, EMCON hold), so a switched-off controller would fight the IADS
  engine; those never sleep. It only *reads* detection from the rest, which is why
  an EWR-role gun site is eligible while a SAM or a point defense never is.

Emits nothing when the setting is off or no eligible group exists, so such missions
carry no ``aiSleep`` node and the plugin no-ops.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from game.theater.iadsnetwork.iadsrole import IadsRole
from game.utils import Distance, meters

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData

#: Always-eligible: deployed/garrison vehicle groups (VehicleGroupGroundObject).
SLEEPABLE_CATEGORIES = frozenset({"armor"})

#: Additionally eligible under ``perf_aaa_site_sleep``, and only for groups passing
#: ``_air_defense_group_may_sleep``. Note ``ewr`` is deliberately absent: a dedicated
#: early-warning site is nothing BUT the long-range radar the sleep would silence.
AIR_DEFENSE_SLEEPABLE_CATEGORIES = frozenset({"aa"})

#: A gun site may sleep only if every unit's detection range is inside this, which is
#: comfortably within the plugin's 10 NM (18 520 m) wake-radius floor -- so the group
#: is always awake before anything enters its sensor envelope. Vietnam-era guns
#: (ZU-23, ZSU-57-2, S-60, KS-19, Shilka, Vulcan) report 5 km or less; a Gepard
#: (15 km) and every search/track radar (35-300 km) are above the line.
AAA_SLEEP_MAX_DETECTION: Distance = meters(10_000)

#: Roles MANTIS actively drives (alarm state / EMCON hold). A sleeping controller
#: would fight it, so these never sleep however short-sighted their units are.
MANTIS_MANAGED_ROLES = frozenset(
    {IadsRole.SAM, IadsRole.SAM_AS_EWR, IadsRole.POINT_DEFENSE}
)


def populate_ai_sleep_lua(
    root: "LuaData", game: "Game", mission_data: Optional["MissionData"] = None
) -> None:
    """Build the ``dcsRetribution.aiSleep`` subtree (sleepable garrison groups)."""
    if not getattr(game.settings, "perf_ground_ai_sleep", False):
        return
    include_air_defense = getattr(game.settings, "perf_aaa_site_sleep", False)

    names: list[str] = []
    for cp in game.theater.controlpoints:
        for tgo in cp.ground_objects:
            names.extend(_sleepable_group_names(tgo, include_air_defense))
    if not names:
        return

    node = root.add_item("aiSleep")
    # The exact names Group.getByName needs (TheaterGroup.group_name, what the
    # generator stamps onto the .miz vehicle group).
    node.add_data_array("groups", names)


def _sleepable_group_names(tgo: Any, include_air_defense: bool) -> list[str]:
    """The TGO's groups holding at least one alive vehicle -- the thinking metal.
    A statics-only group has no controller worth sleeping; a dead one has none."""
    category = getattr(tgo, "category", None)
    if category in SLEEPABLE_CATEGORIES:
        air_defense = False
    elif include_air_defense and category in AIR_DEFENSE_SLEEPABLE_CATEGORIES:
        air_defense = True
    else:
        return []

    # The concealed/map-hidden set is exactly the scripted movers (COIN cells/HVT/
    # VBIEDs, convoy-ambush teams); a sleeping controller would silently stop their
    # routes.
    if getattr(tgo, "concealed", False) or getattr(tgo, "map_hidden", False):
        return []

    names: list[str] = []
    for group in getattr(tgo, "groups", []):
        name = getattr(group, "group_name", None)
        if not name:
            continue
        units = getattr(group, "units", [])
        if not any(
            getattr(u, "is_vehicle", False) and getattr(u, "alive", False)
            for u in units
        ):
            continue
        if air_defense and not _air_defense_group_may_sleep(group):
            continue
        names.append(name)
    return names


def _air_defense_group_may_sleep(group: Any) -> bool:
    """Whether switching this gun group off can change nothing but the frame time.

    Both guards must hold: MANTIS must not be driving the group, and every alive
    unit must be too short-sighted to have seen anything at the wake radius anyway.
    See the module docstring for the reasoning behind each.
    """
    if getattr(group, "iads_role", IadsRole.NO_BEHAVIOR) in MANTIS_MANAGED_ROLES:
        return False
    for unit in getattr(group, "units", []):
        if not getattr(unit, "alive", False):
            continue  # a dead unit is not thinking either way
        detection = getattr(unit, "detection_range", None)
        if detection is None:
            return False  # unknown reach -- assume it can see, keep it awake
        if detection() > AAA_SLEEP_MAX_DETECTION:
            return False
    return True
