from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from dcs.flyingunit import FlyingUnit
from dcs.unitgroup import ShipGroup

from game.dcs.aircrafttype import AircraftType
from game.dcs.groundunittype import GroundUnitType
from game.missiongenerator.aircraft.flightdata import FlightData
from game.missiongenerator.commsjamluadata import CommsJamInfo
from game.missiongenerator.interceptluadata import InterceptEntry, PlayerAlertEntry
from game.missiongenerator.rednetluadata import RedNetInfo
from game.missiongenerator.redscrambleluadata import RedScrambleTemplate
from game.runways import RunwayData

if TYPE_CHECKING:
    from game.radio.radios import RadioFrequency
    from game.radio.tacan import TacanChannel
    from game.theater.player import Player
    from game.utils import Distance
    from uuid import UUID


@dataclass
class GroupInfo:
    group_name: str
    callsign: str
    freq: RadioFrequency
    blue: Player


@dataclass
class UnitInfo(GroupInfo):
    unit_name: str


@dataclass
class AwacsInfo(GroupInfo):
    """AWACS information for the kneeboard."""

    depature_location: Optional[str]
    start_time: datetime
    end_time: datetime
    unit: FlyingUnit  # reference to be used as L16 donor


@dataclass
class TankerInfo(GroupInfo):
    """Tanker information for the kneeboard."""

    variant: str
    tacan: Optional[TacanChannel]
    start_time: datetime
    end_time: datetime
    aircraft_type: AircraftType


@dataclass
class CarrierInfo(UnitInfo):
    """Carrier information."""

    tacan: TacanChannel
    icls_channel: int | None
    link4_freq: RadioFrequency | None
    ship_group: ShipGroup


@dataclass
class JtacInfo(UnitInfo):
    """JTAC information."""

    region: str
    code: str


@dataclass
class EscortInfo:
    """Escort leash information."""

    escort_group_id: int
    escorted_group_id: int
    engagement_range_meters: int
    escort_group_name: str = ""
    escorted_group_name: str = ""


@dataclass
class CargoInfo:
    """Cargo information."""

    unit_type: str = field(default_factory=str)
    spawn_zone: str = field(default_factory=str)
    amount: int = field(default=1)


@dataclass
class LogisticsInfo:
    """Logistics information."""

    pilot_names: list[str]
    transport: AircraftType
    blue: Player

    logistic_unit: str = field(default_factory=str)
    pickup_zone: str = field(default_factory=str)
    drop_off_zone: str = field(default_factory=str)
    target_zone: str = field(default_factory=str)
    cargo: list[CargoInfo] = field(default_factory=list)
    preload: bool = field(default=False)


@dataclass
class FrontlineUnitGroupsInfo:
    group_name: str
    unit_type: GroundUnitType


@dataclass
class AtisInfo:
    """One blue airfield's ATIS station — single source of truth for its freq.

    ``airfield_name`` is the DCS airbase map name (``ControlPoint.full_name`` /
    ``dcs_airport.name``) — the same string MOOSE keys the station and any
    airport-name soundfile on, and the key the kneeboard surfaces look up by.
    """

    airfield_name: str
    frequency: RadioFrequency


@dataclass
class DeckDecorInfo:
    """One carrier's launch-phase deck dressing (§72) for the deckdecor plugin.

    ``clear_names`` are static UNIT names the plugin strikes below
    (``StaticObject:destroy``) before recovery — on the fallback timer or the
    moment fixed-wing traffic shows up low astern. ``ship_group_name`` finds
    the moving boat at runtime (``Group.getByName``); ``brc_degrees`` is the
    generation-time base recovery course (the boat steams that course all
    mission), so the plugin needs no runtime orientation API for the astern
    cone."""

    ship_group_name: str
    carrier_unit_name: str
    blue: bool
    brc_degrees: float
    clear_names: list[str]


@dataclass
class CsarPilotGroupInfo:
    """A downed pilot placed in the mission as a real ground group."""

    group_name: str
    #: The survivor's own unit. OpsCSAR.lua asks DCS's unit registry about this
    #: name to decide whether they are still in the world -- a group's cached unit
    #: handles can outlive the units themselves.
    unit_name: str
    group_id: int
    blue: bool


@dataclass
class MissionData:
    awacs: list[AwacsInfo] = field(default_factory=list)
    runways: list[RunwayData] = field(default_factory=list)
    carriers: list[CarrierInfo] = field(default_factory=list)
    flights: list[FlightData] = field(default_factory=list)
    packages: dict[int, list[FlightData]] = field(default_factory=dict)
    tankers: list[TankerInfo] = field(default_factory=list)
    jtacs: list[JtacInfo] = field(default_factory=list)
    logistics: list[LogisticsInfo] = field(default_factory=list)
    escorts: list[EscortInfo] = field(default_factory=list)
    cp_stack: dict[UUID, Distance] = field(default_factory=dict)
    player_frontline_groups: list[FrontlineUnitGroupsInfo] = field(default_factory=list)
    enemy_frontline_groups: list[FrontlineUnitGroupsInfo] = field(default_factory=list)
    intercept_entries: list[InterceptEntry] = field(default_factory=list)
    # Bases with a player-manned QRA alert flight (§1); drives the Lua "raid
    # inbound — scramble" cue in intercept-config.lua.
    player_alert_entries: list[PlayerAlertEntry] = field(default_factory=list)
    # Names of frontline ground groups handed over to the Troops In Contact
    # script (TIC plugin). Non-empty means TIC_v1.1.lua must be injected.
    tic_groups: list[str] = field(default_factory=list)
    atis_frequencies: list[AtisInfo] = field(default_factory=list)
    # The enemy comms-jamming plan (§51), computed once before the Lua pass so
    # the emitter and the kneeboard (JAM BACKUP line) read the same plan. None
    # when the feature is off or has nothing to do this mission.
    comms_jam: Optional[CommsJamInfo] = None
    # The red-net plan (§70 C1): each alive enemy C2 node's assigned UHF net
    # frequency, computed once (with the RadioRegistry reservation) before the
    # Lua pass. None when red_comms_net is off or no enemy C2 node is alive.
    red_net: Optional[RedNetInfo] = None
    # Carriers with launch-phase deck dressing to strike below before recovery
    # (§72, the deckdecor plugin). Empty unless the aircraft tier placed
    # launch-phase statics this mission.
    deck_decor: list[DeckDecorInfo] = field(default_factory=list)
    # Cold late-activation red interceptor templates for the host F10 scramble
    # menu (§61). Populated by AircraftGenerator.spawn_red_scramble_templates
    # when host_red_scramble is on; the redscramble plugin clones them on demand.
    red_scramble_templates: list[RedScrambleTemplate] = field(default_factory=list)
    # §49 fire-then-scoot: DCS group name -> the missile-site fire-mission hold
    # deadline (seconds after mission start), recorded by MissileSiteGenerator
    # when it attaches the Hold -> FireAtPoint task. The mobile-missile emitter
    # forwards these so the scoot plugin keeps a site still until its fire
    # mission has run -- a route push would setTask-replace the pending fire
    # task (the 2026-07-16 flown fire-vs-scoot clobber: 12 of 13 batteries
    # silently lost their fire missions to the first relocation).
    missile_fire_missions: dict[str, int] = field(default_factory=dict)
    #: Late-activated infantry template group names Ops.CSAR is constructed with,
    #: keyed by coalition ("blue"/"red"). Empty when CSAR is disabled.
    csar_pilot_templates: dict[str, str] = field(default_factory=dict)
    #: The actual downed-pilot groups placed in the mission, keyed by the
    #: DownedPilot's id (as a string). Used to wire the rescue helicopter's
    #: Embarking task to the right pilot, and to hand the group to Ops.CSAR.
    csar_pilot_groups: dict[str, CsarPilotGroupInfo] = field(default_factory=dict)
