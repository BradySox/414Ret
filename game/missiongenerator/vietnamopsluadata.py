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
* **Airbase harassment** (``vietnam_airbase_harassment``): emits each forward, occupied
  airfield/FARP (parking centroid + coalition) plus the player-spawn *exclude* set; the
  runtime lands sporadic standoff rocket/mortar clusters near the ramp, modelling the
  near-constant siege of Bien Hoa/Da Nang/Khe Sanh. Client-spawn fields are filtered out in
  Python (never emitted) and a startup grace period is honored Lua-side, so a cold-starting
  player is never shelled.
* **FAC(A) marking** (``vietnam_fac_marking``): an on-marker only -- the runtime discovers
  airborne friendly OV-10 Broncos by DCS unit type and marks the nearest opposing ground with
  white-phosphorus smoke on a cadence (the iconic Vietnam forward air controller). No
  per-mission data is emitted from Python.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.ato import FlightType
from game.data.units import UnitClass
from game.theater import ControlPointType

if TYPE_CHECKING:
    from dcs.mapping import Point

    from game import Game
    from game.theater import ControlPoint

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

#: Control-point types that host aircraft and so can be harassed on the ramp. Carriers /
#: LHAs (their own ControlPointType) and FOBs (ground-only, no parking) are excluded -- the
#: siege modelled here is 122 mm rockets / 82 mm mortars walking a land field's ramp.
HARASSABLE_CP_TYPES = frozenset(
    {
        ControlPointType.AIRBASE,
        ControlPointType.FARP,
    }
)

#: How near a front line a field must be to count as "forward / contested" and so eligible
#: for harassment. A field deeper in the rear than this is a safe area and is never shelled
#: (design rule 4: forward-only by construction, like NGFS's gun-range gate). ~200 km.
HARASSMENT_FRONT_REACH_M = 200_000.0

#: Control-point types treated as a besieged **outpost** for the Super Gaggle -- a forward
#: FOB (ground-only hilltop, the Khe Sanh case) or FARP. The helos deliver to its position.
GAGGLE_OUTPOST_CP_TYPES = frozenset(
    {
        ControlPointType.FOB,
        ControlPointType.FARP,
    }
)

#: Control-point types the resupply gaggle can **launch** from -- a rear field that hosts
#: helicopters (an airbase or FARP). The launch point is just a spawn origin at runtime.
GAGGLE_LAUNCH_CP_TYPES = frozenset(
    {
        ControlPointType.AIRBASE,
        ControlPointType.FARP,
    }
)

#: How near a front an outpost must be to count as "besieged / cut off" and so worth a
#: Super Gaggle. No forward friendly outpost within this ⇒ no node ⇒ the plugin no-ops.
GAGGLE_OUTPOST_FRONT_REACH_M = 150_000.0


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
        or settings.vietnam_airbase_harassment
        or settings.vietnam_super_gaggle
        or settings.vietnam_fac_marking
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
    if settings.vietnam_airbase_harassment:
        _populate_airbase_harassment(vietnam, game)
    if settings.vietnam_super_gaggle:
        _populate_super_gaggle(vietnam, game)
    if settings.vietnam_fac_marking:
        _populate_fac(vietnam)


def _populate_fac(vietnam: "LuaItem") -> None:
    """Emit the FAC(A) marking on-marker.

    Like the flak gauntlet, the runtime discovers the FAC aircraft itself (airborne
    friendly OV-10 Broncos, by DCS unit type) and marks nearby opposing ground with
    white-phosphorus smoke, so the node only signals the feature is on -- no per-mission
    data needs emitting from Python.
    """
    fac = vietnam.add_item("fac")
    fac.add_key_value("enabled", "true")


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


def _client_spawn_control_points(game: "Game") -> set["ControlPoint"]:
    """Fields a player flight uses this mission -- the hard *never-harass* exclude set.

    Walks every planned package on both sides for flights carrying at least one client, and
    collects each such flight's departure, divert, and arrival control points. This is the
    #1 anti-grief guarantee (design rule 1): a player cold-and-dark on the ramp, or taxiing
    in to recover, must never be shelled. Mirrors the ``cull_farp_statics`` walk in
    ``tgogenerator.py`` (``ato.packages -> flights -> squadron.location``).
    """
    excluded: set["ControlPoint"] = set()
    for coalition in game.coalitions:
        for package in coalition.ato.packages:
            for flight in package.flights:
                if flight.client_count <= 0:
                    continue
                excluded.add(flight.departure)
                excluded.add(flight.arrival)
                if flight.divert is not None:
                    excluded.add(flight.divert)
    return excluded


def _populate_airbase_harassment(vietnam: "LuaItem", game: "Game") -> None:
    """Emit each forward, occupied airfield/FARP for standoff harassment fire.

    Recreates the near-constant rocket/mortar siege of the Vietnam-era airfields (Bien Hoa,
    Da Nang, the Khe Sanh strip). For every occupied land airfield/FARP that is *forward*
    (within :data:`HARASSMENT_FRONT_REACH_M` of a front) and is **not** a player-spawn field
    this mission, emit its name + parking centroid + coalition; the runtime periodically
    lands a small, dispersed impact cluster near the ramp. Client-spawn fields are filtered
    out here (never emitted -- the authoritative anti-grief guarantee) and are additionally
    surfaced under ``excludedFields`` for the Lua to log/double-guard.

    Forward-only by construction (design rule 4): a campaign with no front, or no field near
    one, yields no ``fields`` node and the plugin no-ops -- so a deep-rear or peacetime
    mission is never shelled.
    """
    fronts = list(game.theater.conflicts())
    if not fronts:
        return

    excluded = _client_spawn_control_points(game)

    fields: list[tuple[str, float, float, str]] = []
    for cp in game.theater.controlpoints:
        if cp.cptype not in HARASSABLE_CP_TYPES:
            continue
        if cp.captured.is_neutral:
            continue
        if cp in excluded:
            continue
        distance = min(
            front.position.distance_to_point(cp.position) for front in fronts
        )
        if distance > HARASSMENT_FRONT_REACH_M:
            continue
        color = "BLUE" if cp.captured.is_blue else "RED"
        fields.append((cp.full_name, cp.position.x, cp.position.y, color))

    if not fields:
        return

    harass = vietnam.add_item("airbaseHarassment")
    fields_item = harass.add_item("fields")
    for name, x, y, color in fields:
        record = fields_item.add_item()
        record.add_key_value("name", name)
        # pydcs Point: x = north, y = east. The Lua maps these onto the DCS world vec3
        # ({ x = north, y = alt, z = east }) when it places the impacts.
        record.add_key_value("x", str(x))
        record.add_key_value("y", str(y))
        record.add_key_value("coalition", color)  # "BLUE" / "RED", the field's owner.

    # Defense-in-depth: the runtime already only sees eligible fields, but emitting the
    # names it must never touch lets the Lua log the guard and skip any name match.
    if excluded:
        excluded_item = harass.add_item("excludedFields")
        for excluded_cp in excluded:
            excluded_item.add_item().set_value(excluded_cp.full_name)


def _populate_super_gaggle(vietnam: "LuaItem", game: "Game") -> None:
    """Emit a besieged friendly outpost + a rear launch field for a resupply gaggle.

    Models the Khe Sanh "Super Gaggle": a formation of transport helos runs supplies into a
    cut-off forward outpost while the player can fly escort. **Runtime-only** -- the design's
    planner-template v1 is blocked on an auto-plannable CTLD cargo run the engine lacks, so
    this follows the convoy pattern instead (Python picks the geography; the ``vietnamops``
    plugin spawns and flies the gaggle, re-rolling on a cadence). Picks the friendly (BLUE)
    FOB/FARP nearest a front as the besieged outpost, and the nearest OTHER friendly
    helo-capable field as the launch point. No forward friendly outpost (or no launch field,
    or no front) ⇒ no node ⇒ the plugin no-ops. The fast-mover AAA-suppression choreography
    that made the historical gaggle distinctive is a deferred later increment (per the design
    note's phasing); v1 is the helo resupply run + the escort opportunity.
    """
    from game.theater import Player

    fronts = list(game.theater.conflicts())
    if not fronts:
        return

    def distance_to_front(cp: "ControlPoint") -> float:
        return min(front.position.distance_to_point(cp.position) for front in fronts)

    outposts = [
        cp
        for cp in game.theater.controlpoints
        if cp.captured == Player.BLUE
        and cp.cptype in GAGGLE_OUTPOST_CP_TYPES
        and distance_to_front(cp) <= GAGGLE_OUTPOST_FRONT_REACH_M
    ]
    if not outposts:
        return
    outpost = min(outposts, key=distance_to_front)

    launch_fields = [
        cp
        for cp in game.theater.controlpoints
        if cp.captured == Player.BLUE
        and cp is not outpost
        and cp.cptype in GAGGLE_LAUNCH_CP_TYPES
    ]
    if not launch_fields:
        return
    launch = min(
        launch_fields,
        key=lambda cp: cp.position.distance_to_point(outpost.position),
    )

    gaggle = vietnam.add_item("superGaggle")
    # A node serializes EITHER its key-values OR its child items, not both, so the scalar
    # coalition is emitted as its own child (mirrors the convoy node).
    gaggle.add_item("coalition").set_value("BLUE")
    outpost_item = gaggle.add_item("outpost")
    outpost_item.add_key_value("name", outpost.full_name)
    # pydcs Point: x = north, y = east (the Lua maps these onto the DCS world vec2/vec3).
    outpost_item.add_key_value("x", str(outpost.position.x))
    outpost_item.add_key_value("y", str(outpost.position.y))
    launch_item = gaggle.add_item("launch")
    launch_item.add_key_value("x", str(launch.position.x))
    launch_item.add_key_value("y", str(launch.position.y))


def _target_position(flight: "FlightData") -> tuple[float, float] | None:
    """Return the (x, y) of the flight's package target, or None if unavailable."""
    target = flight.package.target
    position = getattr(target, "position", None)
    if position is None:
        return None
    return position.x, position.y
