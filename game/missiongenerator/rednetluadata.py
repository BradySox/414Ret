"""Red comms net -> Lua config bridge (``dcsRetribution.redNet``, §70 C1+C2).

The enemy net, audible on the dial: with ``red_comms_net`` on, every alive
enemy IADS communications / command-center node (the same objects §51 jams from,
§52 decapitates, and the §70 COMINT take reads) becomes a **transmitting
station** — the ``rednet`` plugin keys periodic coded CW traffic
(``trigger.action.radioTransmission``, an original synthesized morse clip) on
the node's own fixed UHF AM frequency from its campaign-map position. Tune it
and you hear the enemy; a UHF-DF airframe (F-4E, F-14 ARC-182 DF, F/A-18C UFC
ADF, F-5E — the design note's call-#4 module audit) can home on an open window.

C2 adds the **clandestine stations**: concealed COIN spawns (cells, IED teams,
the HVT convoy — an insurgency runs on radios) and any authored *concealed*
comms TGO transmit on the same net with a distinctive short-window/long-gap
schedule — the §3 suspected-activity circle is the search area, and DF-ing an
open window is how you turn the circle into a fix. ``map_hidden`` TGOs (the
§50 ambush teams) are never emitted.

Python owns the frequency plan, and it is deliberately **small and quiet**:

* **A handful of stations, not the whole net.** Every red C2 TGO in the theater
  plus every concealed COIN spawn is comms-active, which on a KARI-style IADS
  or a COIN laydown is dozens of transmitters — a wall of CW across the UHF
  band. Only ``red_net_max_stations`` of them go on the air, picked closest to
  blue territory (a net you can actually hear and DF is worth a dial slot; one
  400 km behind the lines is band clutter), with one slot anchored to each kind
  so the fixed C2 net never vanishes behind a crowd of clandestine cells.
* **Guard-banded off every channel in use.** Each node's frequency is
  **deterministic** (seeded from the node name, so the net lives at the same
  spot on the dial every mission) and sits at x.500 MHz — but x.500 is *not*
  off-limits to the comms plan the way this once claimed: only the inter-flight
  ``BLUFOR UHF`` allocator uses the whole-MHz grid, while per-flight aircraft
  radios, ATC, and ATIS all allocate on the **25 kHz** grid, on which x.500 is a
  perfectly ordinary slot. So a candidate is rejected unless it clears every
  frequency the mission's ``RadioRegistry`` has allocated by ``NET_GUARD_HZ``
  (compared by hertz, modulation-blind), and on success the whole guard band is
  reserved — so nothing allocated afterwards can park a briefed channel a
  detent off an enemy carrier either. GUARD's slot is excluded outright.

Nothing here targets blue radios; hearing the enemy requires deliberately
tuning off-plan.

Audio + DF geometry ONLY (the §36/§49/§51 discipline): no force-model change,
no kills owned by Lua. Killing the node is an ordinary IADS strike (recorded
natively); the plugin takes the net off the air when the node dies. Emits
nothing when the setting is off or no enemy C2 node is alive — such missions
carry no ``redNet`` node and the plugin no-ops.
"""

from __future__ import annotations

import math
import zlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from game.radio.radios import ChannelInUseError, RadioFrequency, RadioRegistry

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData

#: TGO categories that transmit — the IADS C2 objects only, the same set §51
#: (comms jamming) and the §70 COMINT take key on. Never SAMs, never EWRs.
RED_NET_CATEGORIES = ("comms", "commandcenter")

#: The net band: whole-MHz slots whose transmit frequency is slot + 0.5 MHz.
#: The half-MHz offset keeps nets off the whole-MHz grid the BLUFOR UHF
#: inter-flight allocator uses; it does NOT by itself clear the 25 kHz grid
#: every other UHF consumer allocates on -- NET_GUARD_HZ does that.
UHF_NET_FIRST_SLOT_MHZ = 225
UHF_NET_LAST_SLOT_MHZ = 399

#: GUARD's whole-MHz slot (243.0): 243.5 would sit one detent off the emergency
#: channel, so the slot is skipped entirely.
GUARD_SLOT_MHZ = 243

#: Clearance a net must keep from every frequency the mission has already
#: allocated, and the span reserved around it once assigned. 100 kHz is four
#: detents of the 25 kHz grid on which aircraft radios, ATC, and ATIS allocate,
#: so a briefed channel never sits adjacent to an enemy CW carrier.
NET_GUARD_HZ = 100_000

#: The step the guard band is reserved on -- the tuning grid every UHF
#: allocator in the mission uses.
NET_GRID_HZ = 25_000

#: Default cap on how many stations go on the air when the setting is absent
#: (old saves, headless fixtures). Deliberately small: the band is shared.
DEFAULT_MAX_STATIONS = 3


@dataclass
class RedNetNode:
    """One transmitting enemy net station: display name, the per-unit DCS names
    the plugin watches for death (the MANTIS ``<name> object`` static convention
    + the ``dead_events`` ledger), the campaign-map transmission origin, the
    assigned net frequency, whether it keys the **clandestine** schedule (short
    windows, long gaps — the C2 hunt), and the coarse area name the COMINT
    active-nets listing briefs (the parent CP — never exact coordinates)."""

    name: str
    unit_names: list[str]
    x: float
    y: float
    freq_mhz: float
    clandestine: bool = False
    area: str = ""


@dataclass
class RedNetInfo:
    """The mission's red-net plan, stored on ``MissionData.red_net``."""

    nodes: list[RedNetNode]


@dataclass
class _Candidate:
    """One comms-active enemy object, before the station cap picks who is on
    the air: the emit payload plus the geometry the pick is made on."""

    name: str
    unit_names: list[str]
    x: float
    y: float
    clandestine: bool
    area: str
    #: Metres to the nearest blue control point, or ``inf`` when the theater
    #: exposes no blue position (headless fixtures) — then name order decides.
    blue_range_m: float


def plan_red_net(game: "Game", radio_registry: RadioRegistry) -> Optional[RedNetInfo]:
    """Build the red-net plan, or None when the feature has nothing to do."""
    if not getattr(game.settings, "red_comms_net", False):
        return None
    candidates = _enemy_net_nodes(game)
    if not candidates:
        return None
    used_slots: set[int] = set()
    nodes: list[RedNetNode] = []
    for candidate in _stations_on_the_air(candidates, _max_stations(game)):
        freq_mhz = _assign_frequency(candidate.name, used_slots, radio_registry)
        if freq_mhz is None:
            continue
        nodes.append(
            RedNetNode(
                candidate.name,
                candidate.unit_names,
                candidate.x,
                candidate.y,
                freq_mhz,
                candidate.clandestine,
                candidate.area,
            )
        )
    if not nodes:
        return None
    return RedNetInfo(nodes)


def _max_stations(game: "Game") -> int:
    """How many stations may go on the air (never below one)."""
    configured = getattr(game.settings, "red_net_max_stations", DEFAULT_MAX_STATIONS)
    try:
        return max(1, int(configured))
    except (TypeError, ValueError):
        return DEFAULT_MAX_STATIONS


def _stations_on_the_air(candidates: list[_Candidate], limit: int) -> list[_Candidate]:
    """Pick the few stations that transmit, closest to blue territory first.

    The band is shared with the whole comms plan, so a theater's entire C2 net
    plus every insurgent cell cannot each own a frequency. Ordering is
    ``(range to the nearest blue CP, name)`` — deterministic, and it keeps the
    nets a pilot can actually hear and DF rather than the ones parked in the
    deep rear. One slot is anchored to each **kind** (fixed C2, clandestine) so
    a crowd of near cells can never push the fixed C2 net off the dial
    entirely, and vice versa; the remaining slots fill purely by range.
    """
    ordered = sorted(candidates, key=lambda c: (c.blue_range_m, c.name))
    picked: list[_Candidate] = []
    claimed: set[int] = set()
    for clandestine in (False, True):
        if len(picked) >= limit:
            break
        anchor = next((c for c in ordered if c.clandestine is clandestine), None)
        if anchor is not None:
            picked.append(anchor)
            claimed.add(id(anchor))
    picked.extend(c for c in ordered if id(c) not in claimed)
    del picked[limit:]
    # Emit (and so assign frequencies) in the same deterministic order every
    # mission, independent of which anchors were chosen.
    return sorted(picked, key=lambda c: c.name)


def _assign_frequency(
    name: str, used_slots: set[int], radio_registry: RadioRegistry
) -> Optional[float]:
    """A stable x.500 MHz net frequency for this node, reserved in the registry.

    The slot is seeded from the node name (crc32 — stable across processes,
    unlike ``hash``) and linearly probed past GUARD, same-mission collisions,
    and anything within ``NET_GUARD_HZ`` of a frequency the mission has already
    allocated — so the same node broadcasts on the same frequency every mission
    while never landing on, or beside, a briefed channel. On success the whole
    guard band is reserved, closing the band to anything allocated later.
    """
    in_band = _allocated_in_band(radio_registry)
    span = UHF_NET_LAST_SLOT_MHZ - UHF_NET_FIRST_SLOT_MHZ + 1
    slot = UHF_NET_FIRST_SLOT_MHZ + zlib.crc32(name.encode("utf-8")) % span
    for _ in range(span):
        if slot != GUARD_SLOT_MHZ and slot not in used_slots:
            hertz = slot * 1_000_000 + 500_000
            if not any(abs(other - hertz) <= NET_GUARD_HZ for other in in_band):
                _reserve_guard_band(radio_registry, hertz)
                used_slots.add(slot)
                return slot + 0.5
        slot += 1
        if slot > UHF_NET_LAST_SLOT_MHZ:
            slot = UHF_NET_FIRST_SLOT_MHZ
    return None


def _allocated_in_band(radio_registry: RadioRegistry) -> list[int]:
    """Every allocated frequency inside the net band, in hertz.

    Modulation-blind on purpose: ``RadioFrequency`` equality includes the
    modulation, so an AM-vs-FM pair at the same hertz reads as two distinct
    channels to the registry — but they are the same spot on the dial.
    """
    low = UHF_NET_FIRST_SLOT_MHZ * 1_000_000 - NET_GUARD_HZ
    high = UHF_NET_LAST_SLOT_MHZ * 1_000_000 + 1_000_000 + NET_GUARD_HZ
    return [
        frequency.hertz
        for frequency in radio_registry.allocated_channels
        if low <= frequency.hertz <= high
    ]


def _reserve_guard_band(radio_registry: RadioRegistry, hertz: int) -> None:
    """Claim the net frequency and every tuning detent inside its guard band.

    Reserving the neighbours is what stops a *later* allocation (ATIS runs
    after the red-net plan, and any future consumer might too) from putting a
    briefed channel one detent off an enemy carrier.
    """
    steps = int(NET_GUARD_HZ // NET_GRID_HZ)
    for offset in range(-steps, steps + 1):
        try:
            radio_registry.reserve(RadioFrequency(hertz + offset * NET_GRID_HZ))
        except ChannelInUseError:
            # Unreachable in practice -- net slots are a whole MHz apart, so
            # two guard bands never overlap, and the caller only gets here on
            # a candidate that already cleared the band scan. Swallowed as
            # defence in depth: a guard detent is never worth failing a mission
            # generation over.
            pass


def populate_red_net_lua(root: "LuaData", mission_data: "MissionData") -> None:
    """Emit the ``dcsRetribution.redNet`` subtree from the stored plan."""
    info = getattr(mission_data, "red_net", None)
    if info is None or not info.nodes:
        return

    node = root.add_item("redNet")
    node_list = node.add_item("nodes")
    for net in info.nodes:
        rec = node_list.add_item()
        rec.add_key_value("name", net.name)
        # Unit names, per the MANTIS C2 convention: the plugin checks
        # StaticObject.getByName(name .. " object") + the dead_events ledger.
        rec.add_data_array("units", net.unit_names)
        # pydcs Point: x = north, y = east (the emitter frame the other
        # runtime plugins share; the Lua builds the vec3).
        rec.add_key_value("x", str(net.x))
        rec.add_key_value("y", str(net.y))
        rec.add_key_value("mhz", str(net.freq_mhz))
        # Clandestine stations key the short-window/long-gap hunt schedule.
        rec.add_key_value("clandestine", "true" if net.clandestine else "false")


def _enemy_net_nodes(game: "Game") -> list[_Candidate]:
    """Every comms-active enemy object, before the station cap picks.

    Two source sets, mirroring the §70 COMINT source definition
    (``game/fourteenth/comint.py`` — feature A and feature B must agree on who
    is comms-active):

    * ``comms``/``commandcenter`` TGOs — the fixed C2 net (C1). An authored
      *concealed* comms TGO keys the clandestine schedule (a field site whose
      §3 circle is the search area).
    * **Concealed COIN spawns** (``coin_spawned`` + ``concealed`` — cells, IED
      teams, the HVT convoy): an insurgency runs on radios, so each live spawn
      is a clandestine station on its own frequency — DF the net and the §3
      suspected-activity circle becomes a huntable fix.

    ``map_hidden`` TGOs (the §50 ambush teams) are NEVER emitted — nothing may
    telegraph them (that feature's core rule). Emitted regardless of culling,
    the §51 stance: the transmission is synthetic (a point on the map), and an
    un-spawned node simply can't be killed *this* mission.
    """
    blue_positions = _blue_positions(game)
    out: list[_Candidate] = []
    for cp in game.theater.controlpoints:
        if cp.captured.is_blue:
            continue
        for tgo in cp.ground_objects:
            if getattr(tgo, "map_hidden", False):
                continue
            is_c2 = getattr(tgo, "category", None) in RED_NET_CATEGORIES
            is_coin_cell = getattr(tgo, "coin_spawned", False) and getattr(
                tgo, "concealed", False
            )
            if not is_c2 and not is_coin_cell:
                continue
            unit_names = _alive_unit_names(tgo)
            pos = getattr(tgo, "position", None)
            if not unit_names or pos is None or not hasattr(pos, "x"):
                continue
            name = getattr(tgo, "obj_name", None) or getattr(tgo, "name", "C2 net")
            clandestine = is_coin_cell or bool(getattr(tgo, "concealed", False))
            area = str(getattr(cp, "name", ""))
            out.append(
                _Candidate(
                    name=str(name),
                    unit_names=unit_names,
                    x=pos.x,
                    y=pos.y,
                    clandestine=clandestine,
                    area=area,
                    blue_range_m=_range_to_nearest(pos, blue_positions),
                )
            )
    return out


def _blue_positions(game: "Game") -> list[tuple[float, float]]:
    """Blue control point positions, for the station pick's range ordering."""
    positions: list[tuple[float, float]] = []
    for cp in game.theater.controlpoints:
        if not cp.captured.is_blue:
            continue
        pos = getattr(cp, "position", None)
        if pos is not None and hasattr(pos, "x") and hasattr(pos, "y"):
            positions.append((float(pos.x), float(pos.y)))
    return positions


def _range_to_nearest(pos: Any, positions: list[tuple[float, float]]) -> float:
    """Metres to the closest of ``positions``; ``inf`` when there are none."""
    if not positions:
        return float("inf")
    return min(math.hypot(pos.x - x, pos.y - y) for x, y in positions)


def _alive_unit_names(tgo: Any) -> list[str]:
    names: list[str] = []
    for group in getattr(tgo, "groups", []):
        for unit in getattr(group, "units", []):
            unit_name = getattr(unit, "unit_name", None)
            if unit_name and getattr(unit, "alive", False):
                names.append(unit_name)
    return names
