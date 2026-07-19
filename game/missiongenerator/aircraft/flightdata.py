from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional, TYPE_CHECKING

from dcs.flyingunit import FlyingUnit

from game.ato.dtcoptions import DtcOptions
from game.ato.flighttype import FlightType
from game.ato.starttype import StartType
from game.callsigns import create_group_callsign_from_unit
from game.squadrons import Squadron

if TYPE_CHECKING:
    from game.ato import FlightWaypoint, Package
    from game.dcs.aircrafttype import AircraftType
    from game.radio.radios import RadioFrequency
    from game.radio.tacan import TacanChannel
    from game.runways import RunwayData
    from game.theater.player import Player
    from game.utils import Speed


@dataclass(frozen=True)
class ChannelAssignment:
    radio_id: int
    channel: int


@dataclass(frozen=True)
class CombatSarKingBeacon:
    """The homing beacon for a C-130 "King" Combat SAR flight.

    The King orbits as the on-scene-command anchor and lights a TACAN the rescue
    helo homes on. TACAN is air-tracking, so it follows the moving orbit (the
    combatsar plugin calls MOOSE ActivateTACAN), and every DCS rescue helo we use
    has a TACAN receiver -- it is the single homing solution. (An ADF radio beacon
    was considered and dropped: MOOSE's RadioBeacon is fixed-point and the King is a
    mover, so TACAN does the job without a position-refresh loop.)
    """

    callsign: str
    #: The King beacon (air-tracking TACAN); None if the channel pool was dry.
    tacan: Optional[TacanChannel]


@dataclass
class FlightData:
    """Details of a planned flight."""

    #: The package that the flight belongs to.
    package: Package

    flight_type: FlightType

    aircraft_type: AircraftType

    #: The DCS group name of the flight's group. Used by plugins that need to
    #: bind runtime behavior to a specific generated group (e.g. the Combat SAR
    #: rescue set).
    group_name: str

    squadron: Squadron

    #: All units in the flight.
    units: list[FlyingUnit]

    #: Total number of aircraft in the flight.
    size: int

    #: True if this flight belongs to the player's coalition.
    friendly: Player

    #: Number of seconds after mission start the flight is set to depart.
    departure_delay: timedelta

    #: Arrival airport.
    arrival: RunwayData

    #: Departure airport.
    departure: RunwayData

    #: Diver airport.
    divert: Optional[RunwayData]

    #: Waypoints of the flight plan.
    waypoints: list[FlightWaypoint]

    #: Radio frequency for intra-flight communications.
    intra_flight_channel: RadioFrequency

    #: Bingo fuel value in lbs.
    bingo_fuel: Optional[int]

    joker_fuel: Optional[int]

    laser_codes: list[Optional[int]]

    custom_name: Optional[str]

    #: How the flight starts (cold, warm, runway, or in-flight).
    start_type: StartType

    callsign: str = field(init=False)

    #: Map of radio frequencies to the radio/channel presets they were assigned
    #: to. A frequency can land on more than one channel -- e.g. on both COMM1
    #: and COMM2 -- so each maps to a list, ordered by assignment (COMM1 first).
    frequency_to_channel_map: dict[RadioFrequency, list[ChannelAssignment]] = field(
        init=False, default_factory=dict
    )

    #: Nav beacons when this is a C-130 "King" Combat SAR flight; None otherwise.
    combat_sar_king: Optional[CombatSarKingBeacon] = None

    #: Planned on-station speed when this flight flies a racetrack (BARCAP,
    #: TARCAP, AEW&C, tanker...); None for point-to-point plans. The kneeboard
    #: shows it on the racetrack row, where the schedule time is dwell rather
    #: than transit and distance/time would be nonsense.
    patrol_speed: Optional[Speed] = None

    #: The planner's per-flight DTC cartridge controls (§74), carried over from
    #: the Flight so the DtcGenerator honors the Edit Flight dialog's choices.
    dtc_options: DtcOptions = field(default_factory=DtcOptions)

    def __post_init__(self) -> None:
        self.callsign = create_group_callsign_from_unit(self.units[0])

    @property
    def client_units(self) -> list[FlyingUnit]:
        """List of playable units in the flight."""
        return [u for u in self.units if u.is_human()]

    @property
    def task_display_name(self) -> str:
        """The flight's tasking label under its coalition's doctrine -- the Vietnam
        rename layer (e.g. STRIKE -> "Alpha Strike"). Falls back to the canonical
        ``FlightType.value`` when the doctrine supplies no override. A STRIKE flight
        only reads the era "Alpha Strike" label when its package actually masses
        (>= 2 sections on one target); a lone section is a plain Strike. Display
        only."""
        if self.flight_type is FlightType.STRIKE and not self.package.is_massed_strike:
            return FlightType.STRIKE.value
        return self.squadron.coalition.doctrine.display_name_for(self.flight_type)

    def num_radio_channels(self, radio_id: int) -> int:
        """Returns the number of preset channels for the given radio."""
        # Note: pydcs only initializes the radio presets for client slots.
        return self.client_units[0].num_radio_channels(radio_id)

    def channel_for(self, frequency: RadioFrequency) -> Optional[ChannelAssignment]:
        """Returns the first (lowest) channel a frequency was assigned to."""
        channels = self.frequency_to_channel_map.get(frequency)
        return channels[0] if channels else None

    def channels_for(self, frequency: RadioFrequency) -> list[ChannelAssignment]:
        """Returns every channel a frequency was assigned to (COMM1 first)."""
        return self.frequency_to_channel_map.get(frequency, [])

    def assign_channel(
        self, radio_id: int, channel_id: int, frequency: RadioFrequency
    ) -> None:
        """Assigns a preset radio channel to the given frequency."""
        for unit in self.client_units:
            unit.set_radio_channel_preset(radio_id, channel_id, frequency.mhz)

        # A frequency can be bound to several channels (e.g. mirrored onto both
        # COMM1 and COMM2). Record them all, in assignment order.
        self.frequency_to_channel_map.setdefault(frequency, []).append(
            ChannelAssignment(radio_id, channel_id)
        )
