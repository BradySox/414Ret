"""Enemy comms jamming -> Lua config bridge (``dcsRetribution.commsJam``).

The IADS comms nodes, given a voice. With ``enemy_comms_jamming`` on, every alive
enemy IADS communications / command-center node becomes a standoff comms jammer:
the ``commsjam`` plugin floods the BLUE side's *briefed* radio channels with
duty-cycled barrage noise transmitted (``trigger.action.radioTransmission``) from
the node's campaign-map position, so the audio arrives in the player's headset
through DCS's own radio path -- SRS users hear it too, because SRS tunes off the
cockpit radios. Power and distance attenuation are DCS-native; no SRS server
dependency exists or is wanted.

Python owns the *plan*: which nodes jam (alive enemy ``comms``/``commandcenter``
TGOs, the same objects MANTIS's C2 graph watches), which frequencies are fair
game (the blue flights' intra-flight channels -- human-crewed flights first --
plus the blue AWACS freqs; GUARD and anything unbriefed are never touched by
construction), and one freshly-allocated **JAM BACKUP** frequency the jammer can
never land on (it comes out of the same ``RadioRegistry`` every briefed channel
came out of, so it is unused by anything). The backup is surfaced on the
kneeboard comms ladder so comms discipline -- push to the backup, kill the node
-- is a play, not a mystery.

Audio pressure ONLY, the §36/§49 discipline: no force-model change, no kills
owned by Lua. Killing the node is an ordinary strike on an ordinary IADS TGO
(recorded natively); the plugin merely stops transmitting when the node dies.
Emits nothing when the setting is off, no enemy comms node is alive, or no blue
frequency exists -- such missions carry no ``commsJam`` node and the plugin
no-ops.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from game.radio.radios import RadioFrequency, RadioRegistry

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData

#: TGO categories that host the jammer. Deliberately the IADS C2 objects only --
#: the same comms masts / command bunkers the MANTIS C2-degradation graph watches
#: -- so the strike that silences the jamming is the strike that degrades the
#: IADS. Never SAMs, never EWRs, never generic buildings.
JAMMER_CATEGORIES = ("comms", "commandcenter")

#: Frequencies that must never be jammed even if they somehow end up briefed as
#: an intra-flight channel: UHF/VHF GUARD (Combat SAR and emergencies live
#: there). The registry reserves both, so this is a defensive double-guard.
GUARD_MHZ = (243.0, 121.5)

#: Hard cap on the emitted jam list. The plugin duty-cycles a small subset per
#: burst anyway; this bounds the Lua config for a huge ATO.
MAX_JAMMED_FREQUENCIES = 10


@dataclass
class CommsJamJammer:
    """One enemy C2 node that jams: display name, the per-unit DCS names the
    plugin watches for death (the MANTIS ``dcs_name_for_group`` convention --
    unit names; statics resolve in Lua as ``<name> .. " object"``), and the
    campaign-map transmission origin."""

    name: str
    unit_names: list[str]
    x: float
    y: float


@dataclass
class CommsJamInfo:
    """The mission's comms-jam plan, stored on ``MissionData.comms_jam`` so the
    Lua emitter and the kneeboard (JAM BACKUP line) read the same plan."""

    jammers: list[CommsJamJammer]
    frequencies: list[RadioFrequency]
    #: The one frequency guaranteed un-jammed (freshly allocated, so no flight
    #: uses it either). None only if the registry is exhausted.
    backup: Optional[RadioFrequency]


def plan_comms_jam(
    game: "Game", mission_data: "MissionData", radio_registry: RadioRegistry
) -> Optional[CommsJamInfo]:
    """Build the comms-jam plan, or None when the feature has nothing to do."""
    if not getattr(game.settings, "enemy_comms_jamming", False):
        return None
    jammers = _enemy_jammer_nodes(game)
    if not jammers:
        return None
    frequencies = _blue_briefed_frequencies(mission_data)
    if not frequencies:
        return None
    # alloc_uhf never raises: on an exhausted registry it degrades to *reusing*
    # a channel, which could (freakishly) be one we're about to jam -- retry a
    # few times, then go without a backup rather than publish a jammed one.
    backup: Optional[RadioFrequency] = None
    for _ in range(5):
        candidate = radio_registry.alloc_uhf()
        if candidate not in frequencies:
            backup = candidate
            break
    else:
        logging.warning(
            "Comms jam: could not allocate an un-jammed JAM BACKUP frequency"
        )
    return CommsJamInfo(jammers, frequencies, backup)


def populate_comms_jam_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Emit the ``dcsRetribution.commsJam`` subtree from the stored plan."""
    info = getattr(mission_data, "comms_jam", None)
    if info is None:
        return

    node = root.add_item("commsJam")
    jammer_list = node.add_item("jammers")
    for jammer in info.jammers:
        rec = jammer_list.add_item()
        rec.add_key_value("name", jammer.name)
        # Unit names, per the MANTIS C2 convention: the plugin checks
        # StaticObject.getByName(name .. " object") + the dead_events ledger.
        rec.add_data_array("units", jammer.unit_names)
        # pydcs Point: x = north, y = east (the emitter frame the other
        # runtime plugins share).
        rec.add_key_value("x", str(jammer.x))
        rec.add_key_value("y", str(jammer.y))

    freq_list = node.add_item("freqs")
    for freq in info.frequencies:
        rec = freq_list.add_item()
        rec.add_key_value("mhz", str(freq.mhz))
        rec.add_key_value("mod", freq.modulation.name)

    if info.backup is not None:
        # Nested single-value item, not add_key_value: the LuaData serializer
        # drops scalar key-values on an object that also carries nested items.
        node.add_item("backupMhz").set_value(str(info.backup.mhz))


def _enemy_jammer_nodes(game: "Game") -> list[CommsJamJammer]:
    """Alive enemy (non-player-owned) comms / command-center TGOs.

    Emitted regardless of culling: the transmission is synthetic (a point on
    the map), and an un-spawned node simply can't be killed *this* mission --
    the standing jamming pressure is exactly what motivates fragging a strike
    at it next turn, which un-culls it.
    """
    jammers: list[CommsJamJammer] = []
    for cp in game.theater.controlpoints:
        if cp.captured.is_blue:
            continue
        for tgo in cp.ground_objects:
            if getattr(tgo, "category", None) not in JAMMER_CATEGORIES:
                continue
            unit_names = _alive_unit_names(tgo)
            pos = getattr(tgo, "position", None)
            if not unit_names or pos is None or not hasattr(pos, "x"):
                continue
            name = getattr(tgo, "obj_name", None) or getattr(tgo, "name", "C2 node")
            jammers.append(CommsJamJammer(str(name), unit_names, pos.x, pos.y))
    return jammers


def _alive_unit_names(tgo: Any) -> list[str]:
    names: list[str] = []
    for group in getattr(tgo, "groups", []):
        for unit in getattr(group, "units", []):
            unit_name = getattr(unit, "unit_name", None)
            if unit_name and getattr(unit, "alive", False):
                names.append(unit_name)
    return names


def _blue_briefed_frequencies(mission_data: "MissionData") -> list[RadioFrequency]:
    """The BLUE channels worth stepping on, most human-relevant first.

    Positive list by construction -- intra-flight channels (human-crewed
    flights first, then AI) and blue AWACS/GCI freqs. ATC, ATIS, tankers and
    GUARD are never listed, so ground ops and emergencies stay clean.
    """
    ordered: list[RadioFrequency] = []

    def add(freq: Optional[RadioFrequency]) -> None:
        if freq is None:
            return
        if any(abs(freq.mhz - guard) < 1e-6 for guard in GUARD_MHZ):
            return
        if freq not in ordered:
            ordered.append(freq)

    for flight in mission_data.flights:
        if flight.friendly.is_blue and flight.client_units:
            add(flight.intra_flight_channel)
    for awacs in mission_data.awacs:
        if awacs.blue.is_blue:
            add(awacs.freq)
    for flight in mission_data.flights:
        if flight.friendly.is_blue and not flight.client_units:
            add(flight.intra_flight_channel)
    return ordered[:MAX_JAMMED_FREQUENCIES]
