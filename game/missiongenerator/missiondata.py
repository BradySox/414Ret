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
from game.runways import RunwayData

if TYPE_CHECKING:
    from game.radio.radios import RadioFrequency
    from game.radio.tacan import TacanChannel
    from game.theater.player import Player
    from game.utils import Distance
    from uuid import UUID


@dataclass
class CombatSarTemplates:
    """On-demand AI rescue sources (§21). Two, in preference order:

    1. ``parked_helos`` -- **real** untasked rescue helos already sitting cold on
       the ramp (`AircraftGenerator._spawn_unused_for`, in the UnitMap). The
       runtime starts one and flies the OPSTRANSPORT pickup: a **tracked** airframe
       whose loss is recorded, launched from a *parked* aircraft (not the retired
       commandeer of an *airborne* orbit helo -- that airborne re-task is what
       failed, G21). Empty when the ramp is bare (perf toggle / fully-tasked wing).
    2. ``helo_group`` -- a cold late-activation **clone template** as the fallback
       when no parked helo is free. The runtime SPAWN-clones it (the proven
       clone-into-mission path); the clone is untracked, like the pre-rework
       rescue clones. None if no parking was available to place the template.

    The Sandy (arming needs the configurator pass) + King (needs the TACAN beacon
    setup) on-demand clones stay §21 v2.
    """

    #: Friendly field the rescue delivers the survivor to (CP display name; the
    #: runtime falls back to the nearest resolvable field for a FARP).
    delivery_field: str
    #: Real untasked rescue helos parked on the ramp -- preferred (tracked).
    parked_helos: list[str] = field(default_factory=list)
    #: The cold clone-template helo group; fallback when no parked helo is free.
    helo_group: Optional[str] = None


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
    # Cold late-activation template group(s) the combatsar runtime clones for an
    # on-demand AI rescue (§21). Populated by
    # AircraftGenerator.spawn_combat_sar_templates when auto_combat_sar is on and
    # BLUE owns a CSAR-capable helo; None otherwise. Whether the runtime actually
    # auto-spawns is a separate gate (no player CSAR package this mission), decided
    # in luagenerator so the template can exist unused.
    combat_sar_templates: Optional[CombatSarTemplates] = None
    # Group names of BLUE untasked rescue helos parked cold on the ramp
    # (`_spawn_unused_for`) — the preferred, **tracked** on-demand rescue source
    # (§21). Collected during flight generation; folded into
    # ``combat_sar_templates`` by ``spawn_combat_sar_templates``.
    parked_rescue_helos: list[str] = field(default_factory=list)
