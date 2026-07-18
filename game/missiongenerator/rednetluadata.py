"""Red comms net -> Lua config bridge (``dcsRetribution.redNet``, §70 C1).

The enemy C2 net, audible on the dial: with ``red_comms_net`` on, every alive
enemy IADS communications / command-center node (the same objects §51 jams from,
§52 decapitates, and the §70 COMINT take reads) becomes a **transmitting
station** — the ``rednet`` plugin keys periodic coded CW traffic
(``trigger.action.radioTransmission``, an original synthesized morse clip) on
the node's own fixed UHF AM frequency from its campaign-map position. Tune it
and you hear the enemy; a UHF-DF airframe (F-4E, F-14 ARC-182 DF, F/A-18C UFC
ADF, F-5E — the design note's call-#4 module audit) can home on an open window.

Python owns the frequency plan. Each node's frequency is **deterministic**
(seeded from the node name, so the net lives at the same spot on the dial every
mission) and **off the friendly comms plan by construction**: nets sit at
x.500 MHz, while every briefed blue channel allocates on the registry's
whole-MHz grid — and each net frequency is additionally reserved in the
mission's ``RadioRegistry`` so nothing can ever be allocated onto it. GUARD's
neighborhood is excluded. Nothing here targets blue radios; hearing the enemy
requires deliberately tuning off-plan.

Audio + DF geometry ONLY (the §36/§49/§51 discipline): no force-model change,
no kills owned by Lua. Killing the node is an ordinary IADS strike (recorded
natively); the plugin takes the net off the air when the node dies. Emits
nothing when the setting is off or no enemy C2 node is alive — such missions
carry no ``redNet`` node and the plugin no-ops.
"""

from __future__ import annotations

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

#: The net band: whole-MHz slots whose transmit frequency is slot + 0.5 MHz —
#: off the whole-MHz grid the RadioRegistry's BLUFOR UHF allocator uses, so a
#: net can never land on a briefed blue channel by construction.
UHF_NET_FIRST_SLOT_MHZ = 225
UHF_NET_LAST_SLOT_MHZ = 399

#: GUARD's whole-MHz slot (243.0): 243.5 would sit one detent off the emergency
#: channel, so the slot is skipped entirely.
GUARD_SLOT_MHZ = 243


@dataclass
class RedNetNode:
    """One transmitting enemy C2 node: display name, the per-unit DCS names the
    plugin watches for death (the MANTIS ``<name> object`` static convention +
    the ``dead_events`` ledger), the campaign-map transmission origin, and the
    assigned net frequency."""

    name: str
    unit_names: list[str]
    x: float
    y: float
    freq_mhz: float


@dataclass
class RedNetInfo:
    """The mission's red-net plan, stored on ``MissionData.red_net``."""

    nodes: list[RedNetNode]


def plan_red_net(game: "Game", radio_registry: RadioRegistry) -> Optional[RedNetInfo]:
    """Build the red-net plan, or None when the feature has nothing to do."""
    if not getattr(game.settings, "red_comms_net", False):
        return None
    raw = _enemy_net_nodes(game)
    if not raw:
        return None
    # Deterministic assignment order: sorted by node name, so a collision
    # probes the same way every mission and each net keeps its frequency.
    raw.sort(key=lambda entry: entry[0])
    used_slots: set[int] = set()
    nodes: list[RedNetNode] = []
    for name, unit_names, x, y in raw:
        freq_mhz = _assign_frequency(name, used_slots, radio_registry)
        if freq_mhz is None:
            continue
        nodes.append(RedNetNode(name, unit_names, x, y, freq_mhz))
    if not nodes:
        return None
    return RedNetInfo(nodes)


def _assign_frequency(
    name: str, used_slots: set[int], radio_registry: RadioRegistry
) -> Optional[float]:
    """A stable x.500 MHz net frequency for this node, reserved in the registry.

    The slot is seeded from the node name (crc32 — stable across processes,
    unlike ``hash``) and linearly probed past GUARD, same-mission collisions,
    and anything already reserved, so the same node broadcasts on the same
    frequency every mission while never colliding with the comms plan.
    """
    span = UHF_NET_LAST_SLOT_MHZ - UHF_NET_FIRST_SLOT_MHZ + 1
    slot = UHF_NET_FIRST_SLOT_MHZ + zlib.crc32(name.encode("utf-8")) % span
    for _ in range(span):
        if slot != GUARD_SLOT_MHZ and slot not in used_slots:
            frequency = RadioFrequency(int((slot + 0.5) * 1_000_000))
            try:
                radio_registry.reserve(frequency)
            except ChannelInUseError:
                pass
            else:
                used_slots.add(slot)
                return slot + 0.5
        slot += 1
        if slot > UHF_NET_LAST_SLOT_MHZ:
            slot = UHF_NET_FIRST_SLOT_MHZ
    return None


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


def _enemy_net_nodes(game: "Game") -> list[tuple[str, list[str], float, float]]:
    """Alive enemy (non-blue-owned) comms / command-center TGOs.

    Emitted regardless of culling, the §51 stance: the transmission is
    synthetic (a point on the map), and an un-spawned node simply can't be
    killed *this* mission.
    """
    out: list[tuple[str, list[str], float, float]] = []
    for cp in game.theater.controlpoints:
        if cp.captured.is_blue:
            continue
        for tgo in cp.ground_objects:
            if getattr(tgo, "category", None) not in RED_NET_CATEGORIES:
                continue
            unit_names = _alive_unit_names(tgo)
            pos = getattr(tgo, "position", None)
            if not unit_names or pos is None or not hasattr(pos, "x"):
                continue
            name = getattr(tgo, "obj_name", None) or getattr(tgo, "name", "C2 net")
            out.append((str(name), unit_names, pos.x, pos.y))
    return out


def _alive_unit_names(tgo: Any) -> list[str]:
    names: list[str] = []
    for group in getattr(tgo, "groups", []):
        for unit in getattr(group, "units", []):
            unit_name = getattr(unit, "unit_name", None)
            if unit_name and getattr(unit, "alive", False):
                names.append(unit_name)
    return names
