"""Vietnam Ops suite -> Lua config bridge (dcsRetribution.VietnamOps).

The Vietnam Ops suite (docs/dev/design/414th-vietnam-ops-notes.md) adds opt-in
period mechanics that run inside the generated .miz via the ``vietnamops`` plugin.
Following the MANTIS/Combat-SAR pattern, Python emits a data table and the Lua side
executes the behavior. Each sub-feature is emitted **only when its Settings toggle is
on**, so the plugin gates purely on data presence (an absent node = feature off).

Features so far:

* **Arc Light** (``vietnam_arc_light``): a heavy-bomber ``STRIKE`` carpets its target area
  at the run-in instead of dropping a single aimpoint (the reframe -- an *effect* of the
  Strike task, not a new FlightType). Tactical strikers are never matched.
* **AAA flak gauntlet** (``vietnam_flak_gauntlet``): an on-marker only -- the runtime
  discovers AAA guns by attribute and barrages opposing aircraft, tightening on predictable
  run-ins. No per-mission threat data is emitted from Python.
* **Naval gunfire support** (``vietnam_naval_gunfire``): emits each naval gun ship + its
  coalition; the runtime offers a player F10 call-for-fire (on the last F10 map marker) and
  an automatic coastal bombardment of in-range enemy ground targets. Coastal campaigns only
  (inland missions have no gun ships in range, so it no-ops).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.ato import FlightType
from game.data.units import UnitClass

if TYPE_CHECKING:
    from dcs.mapping import Point

    from game import Game

    from .aircraft.flightdata import FlightData
    from .luagenerator import LuaData, LuaItem
    from .missiondata import MissionData


#: DCS unit ids of heavy bombers whose Strike is flown as an Arc Light carpet. Vanilla
#: DCS heavy bombers only (per the fork's vanilla-units rule). A Strike by anything not
#: in this set is an ordinary single-aimpoint strike -- the gate that keeps an F-4 / A-4
#: tactical strike untouched.
HEAVY_BOMBER_DCS_IDS = frozenset(
    {
        "B-52H",
        "B-1B",
        "Tu-95MS",
        "Tu-142",
        "Tu-160",
        "Tu-22M3",
    }
)

#: Naval unit classes that carry deck guns usable for shore bombardment. Mirrors the
#: classes the generator already treats as ship artillery; the VWV battleship (New Jersey)
#: is class Destroyer, so it is covered.
NAVAL_GUN_SHIP_CLASSES = frozenset(
    {
        UnitClass.CRUISER,
        UnitClass.DESTROYER,
        UnitClass.FRIGATE,
    }
)


def populate_vietnam_ops_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Build the ``dcsRetribution.VietnamOps`` subtree from the enabled features.

    Emits nothing when no Vietnam Ops feature is on, so non-Vietnam missions carry no
    ``VietnamOps`` node and the plugin no-ops.
    """
    settings = game.settings

    # Extend this guard as each suite feature lands.
    if not (
        settings.vietnam_arc_light
        or settings.vietnam_flak_gauntlet
        or settings.vietnam_naval_gunfire
        or settings.vietnam_convoy_interdiction
    ):
        return

    vietnam = root.add_item("VietnamOps")

    if settings.vietnam_arc_light:
        _populate_arc_light(vietnam, mission_data)
    if settings.vietnam_flak_gauntlet:
        _populate_flak(vietnam)
    if settings.vietnam_naval_gunfire:
        _populate_naval_gunfire(vietnam, game)
    if settings.vietnam_convoy_interdiction:
        _populate_convoy_interdiction(vietnam, game)


def _populate_arc_light(vietnam: "LuaItem", mission_data: "MissionData") -> None:
    """Emit one record per eligible heavy-bomber Strike: the bomber group + its target.

    The Lua side watches each bomber and, when it reaches its run-in, walks a carpet of
    explosions across the target (orientation/density are Lua-side), so Python only needs
    the group name and the target centre. A bomber shot down before the run-in simply
    never fires its carpet -- losses stay native.
    """
    strikes: list[tuple[str, float, float]] = []
    for flight in mission_data.flights:
        if flight.flight_type is not FlightType.STRIKE:
            continue
        if flight.aircraft_type.dcs_unit_type.id not in HEAVY_BOMBER_DCS_IDS:
            continue
        position = _target_position(flight)
        if position is None:
            continue
        strikes.append((flight.group_name, position[0], position[1]))

    if not strikes:
        return

    arc = vietnam.add_item("arcLight")
    strikes_item = arc.add_item("strikes")
    for group_name, x, y in strikes:
        record = strikes_item.add_item()
        record.add_key_value("group", group_name)
        # pydcs Point: x = north, y = east. The Lua maps these onto the DCS world vec3
        # ({ x = north, y = alt, z = east }) when it places the explosions.
        record.add_key_value("x", str(x))
        record.add_key_value("y", str(y))


def _populate_flak(vietnam: "LuaItem") -> None:
    """Emit the flak-gauntlet on-marker.

    The runtime discovers AAA guns itself (by the DCS ``AAA`` unit attribute) and runs
    barrage flak against opposing aircraft in range, so the node only signals the feature
    is on -- no per-mission threat data needs emitting from Python.
    """
    flak = vietnam.add_item("flak")
    flak.add_key_value("enabled", "true")


def _populate_naval_gunfire(vietnam: "LuaItem", game: "Game") -> None:
    """Emit each friendly/enemy naval gun ship + its coalition for shore bombardment.

    The runtime runs two modes off this list (the player F10 call-for-fire and the
    automatic coastal bombardment), so Python only needs which ships have guns and whose
    side they are on; targets + ranging are resolved live. Mirrors the generator's existing
    ship-artillery classification (CRUISER/DESTROYER/FRIGATE).
    """
    ships: list[tuple[str, str]] = []
    for ground_object in game.theater.ground_objects:
        for group in ground_object.groups:
            if not group.units:
                continue
            unit_type = group.units[0].unit_type
            if unit_type is None:
                continue
            if unit_type.unit_class in NAVAL_GUN_SHIP_CLASSES:
                ships.append((group.group_name, ground_object.faction_color))

    if not ships:
        return

    ngfs = vietnam.add_item("navalGunfire")
    ships_item = ngfs.add_item("ships")
    for group_name, coalition in ships:
        record = ships_item.add_item()
        record.add_key_value("group", group_name)
        record.add_key_value("coalition", coalition)  # "BLUE" / "RED"


def _populate_convoy_interdiction(vietnam: "LuaItem", game: "Game") -> None:
    """Emit the enemy supply **corridor** nearest the FLOT (Steel Tiger interdiction).

    The auto-planner surfaces this through Armed Recon; the runtime seeds a moving truck
    convoy on the chosen road that scatters when hunted. Python only picks the corridor
    (the enemy reinforcement road closest to the fighting -- reusing the engine's existing
    ``convoy_routes`` so the kill ties back to real red logistics) and emits its path.
    Inland or not, an enemy with no road behind the front simply yields no node -> the
    plugin no-ops. The opfor is the side the human fights; for the Vietnam case that is RED.
    """
    from game.theater import ControlPoint, Player

    fronts = list(game.theater.conflicts())
    if not fronts:
        return

    def enemy(cp: "ControlPoint") -> bool:
        return cp.captured == Player.RED

    best_path: tuple["Point", ...] = ()
    best_distance = float("inf")
    seen: set[frozenset[str]] = set()
    for cp in game.theater.controlpoints:
        if not enemy(cp):
            continue
        for other, path in cp.convoy_routes.items():
            # Only enemy -> enemy roads (a supply corridor behind the lines); an enemy ->
            # friendly road is the contested front itself.
            if not enemy(other) or len(path) < 2:
                continue
            key = frozenset((str(cp.id), str(other.id)))
            if key in seen:
                continue
            seen.add(key)
            midpoint = path[len(path) // 2]
            distance = min(
                front.position.distance_to_point(midpoint) for front in fronts
            )
            if distance < best_distance:
                best_distance = distance
                best_path = path

    if not best_path:
        return

    convoy = vietnam.add_item("convoy")
    # A node serializes EITHER its key-values OR its child items, not both, so the
    # scalar coalition is emitted as its own child rather than a sibling key-value.
    convoy.add_item("coalition").set_value("RED")
    waypoints = convoy.add_item("waypoints")
    for point in best_path:
        record = waypoints.add_item()
        # pydcs Point: x = north, y = east (the Lua maps these onto the DCS world vec2).
        record.add_key_value("x", str(point.x))
        record.add_key_value("y", str(point.y))


def _target_position(flight: "FlightData") -> tuple[float, float] | None:
    """Return the (x, y) of the flight's package target, or None if unavailable."""
    target = flight.package.target
    position = getattr(target, "position", None)
    if position is None:
        return None
    return position.x, position.y
