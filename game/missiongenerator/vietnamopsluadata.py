"""Vietnam Ops suite -> Lua config bridge (dcsRetribution.VietnamOps).

The Vietnam Ops suite (docs/dev/design/retlab-vietnam-ops-notes.md) adds opt-in
period mechanics that run inside the generated .miz via the ``vietnamops`` plugin.
Following the IADS pattern, Python emits a data table and the Lua side executes the
behavior. Each sub-feature is emitted **only when its Settings toggle is on**, so the
plugin gates purely on data presence (an absent node = feature off).

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

* **FAC(A) marking** (``vietnam_fac_marking``): an on-marker only -- the runtime discovers
  airborne friendly OV-10 Broncos by DCS unit type and marks the nearest opposing ground with
  white-phosphorus smoke on a cadence (the iconic Vietnam forward air controller). No
  per-mission data is emitted from Python.
* **Snake and nape** (``vietnam_snake_and_nape``): an on-marker only -- the runtime discovers
  attack aircraft (by the DCS "Attack airplanes" attribute) making a low, fast pass over
  opposing ground and lays a napalm swath (a line of fire + a modest bite) across the target,
  modelling the iconic low-level napalm CAS delivery. Symmetric; no per-mission data from Python.

**Convoy interdiction** (``vietnam_convoy_interdiction``) is intentionally NOT here: it emits
no Lua node. Rather than spawn a phantom truck column at runtime, it now creates a *real*,
tracked enemy convoy in the force model (``game/retlab/vietnam_convoy.py``, run from
``finish_turn``) so interdicting it costs the opfor real reinforcements and the loss is
recorded natively. See §35.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.ato import FlightType
from game.data.units import HEAVY_BOMBER_DCS_IDS, UnitClass

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint

    from .aircraft.flightdata import FlightData
    from .luagenerator import LuaData, LuaItem
    from .missiondata import MissionData


# HEAVY_BOMBER_DCS_IDS (the Arc Light eligibility set -- a Strike by anything not in
# it is an ordinary single-aimpoint strike, the gate that keeps an F-4 / A-4 tactical
# strike untouched) is imported from game.data.units: the doctrine low-level attack
# profile shares it, and game/ato must not import game/missiongenerator.

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

    # Extend this guard as each suite feature lands. NB: vietnam_convoy_interdiction is
    # deliberately absent -- it no longer emits a Lua node. Convoy interdiction is now a
    # real, tracked enemy convoy created in the force model (game/retlab/vietnam_convoy.py
    # from finish_turn), not a phantom runtime spawn, so it needs nothing from the plugin.
    if not (
        settings.vietnam_arc_light
        or settings.vietnam_flak_gauntlet
        or settings.vietnam_naval_gunfire
        or settings.vietnam_super_gaggle
        or settings.vietnam_fac_marking
        or settings.vietnam_snake_and_nape
    ):
        return

    vietnam = root.add_item("VietnamOps")

    if settings.vietnam_arc_light:
        _populate_arc_light(vietnam, mission_data)
    if settings.vietnam_flak_gauntlet:
        _populate_flak(vietnam)
    if settings.vietnam_naval_gunfire:
        _populate_naval_gunfire(vietnam, game)
    if settings.vietnam_super_gaggle:
        _populate_super_gaggle(vietnam, game)
    if settings.vietnam_fac_marking:
        _populate_fac(vietnam)
    if settings.vietnam_snake_and_nape:
        _populate_snake_nape(vietnam)


def _populate_snake_nape(vietnam: "LuaItem") -> None:
    """Emit the snake-and-nape on-marker.

    Like the flak gauntlet and FAC(A), the runtime discovers the delivering aircraft itself
    (airborne attack aircraft, by the DCS "Attack airplanes" attribute) making a low, fast
    pass over opposing ground, and lays a napalm fire swath across the target. The node only
    signals the feature is on -- no per-mission data needs emitting from Python.
    """
    nape = vietnam.add_item("snakeNape")
    nape.add_key_value("enabled", "true")


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


def _populate_super_gaggle(vietnam: "LuaItem", game: "Game") -> None:
    """Emit the turn's planned Super Gaggle run (real squadron airframes + names).

    Models the Khe Sanh "Super Gaggle": a formation of transport helos runs supplies into a
    cut-off forward outpost while the player can fly escort. The geography + squadron selection
    happen once per turn in ``game/retlab/super_gaggle.py`` (``plan_super_gaggle``), which
    draws the helos + suppressors from **real BLUE squadrons** and records the exact per-airframe
    unit names in ``game.super_gaggle_commitment``; the plugin spawns **exactly those** airframes,
    by name, **once** (no respawn), and a killed name is charged back to its squadron at debrief
    (§37). No committed gaggle (feature off / no besieged outpost / no launch field / no helo
    squadron with airframes) ⇒ no node ⇒ the plugin no-ops.
    """
    commitment = getattr(game, "super_gaggle_commitment", None)
    if commitment is None:
        return

    gaggle = vietnam.add_item("superGaggle")
    # A node serializes EITHER its key-values OR its child items, not both, so the scalar
    # coalition is emitted as its own child (mirrors the convoy node).
    gaggle.add_item("coalition").set_value("BLUE")
    # The DCS country the gaggle spawns under. Must be a country registered on the
    # BLUE coalition in this .miz -- the faction country always is -- because
    # coalition.addGroup puts the units on whatever coalition owns the country: the
    # plugin's old hardcoded USA fallback spawned NEUTRAL units for any faction
    # whose country differs.
    gaggle.add_item("countryId").set_value(str(game.blue.faction.country.id))
    outpost_item = gaggle.add_item("outpost")
    outpost_item.add_key_value("name", commitment.outpost_name)
    # pydcs Point: x = north, y = east (the Lua maps these onto the DCS world vec2/vec3).
    outpost_item.add_key_value("x", str(commitment.outpost_x))
    outpost_item.add_key_value("y", str(commitment.outpost_y))
    launch_item = gaggle.add_item("launch")
    launch_item.add_key_value("x", str(commitment.launch_x))
    launch_item.add_key_value("y", str(commitment.launch_y))

    # The exact airframes to spawn, by real per-unit name, so a killed name maps straight back
    # to a squadron at debrief. Counts are implicit in the name lists (no respawn -> bounded).
    # `type` must be a named child item, not add_key_value: a node with child items (the
    # `names` list) serializes ONLY its children, silently dropping any key-values.
    helo = gaggle.add_item("helo")
    helo.add_item("type").set_value(commitment.helo_type)
    helo_names = helo.add_item("names")
    for name in commitment.helo_unit_names:
        helo_names.add_item().set_value(name)

    if commitment.supp_type and commitment.supp_unit_names:
        supp = gaggle.add_item("suppressor")
        supp.add_item("type").set_value(commitment.supp_type)
        supp_names = supp.add_item("names")
        for name in commitment.supp_unit_names:
            supp_names.add_item().set_value(name)


def _target_position(flight: "FlightData") -> tuple[float, float] | None:
    """Return the (x, y) of the flight's package target, or None if unavailable."""
    target = flight.package.target
    position = getattr(target, "position", None)
    if position is None:
        return None
    return position.x, position.y
