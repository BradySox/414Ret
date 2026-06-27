from __future__ import annotations

from enum import Enum

from game.sidc import AirEntity


class FlightType(Enum):
    """Enumeration of mission types.

    The value of each enumeration is the name that will be shown in the UI.

    These values are persisted to the save game as well since they are a part of
    each flight and thus a part of the ATO, so changing these values will break
    save compat.

    When adding new mission types to this list, you will also need to update:

    * flightplan.py: Add waypoint population in generate_flight_plan. Add a new flight
      plan type if necessary, though most are a subclass of StrikeFlightPlan.
    * aircraftgenerator.py: Add a configuration method and call it in setup_flight_group. This is
      responsible for configuring waypoint 0 actions like setting ROE, threat reaction,
      and mission abort parameters (winchester, bingo, etc).
    * Implementations of MissionTarget.mission_types: A mission type can only be planned
      against compatible targets. The mission_types method of each target class defines
      which missions may target it.
    * resources/units/aircraft/*.yaml: Assign aircraft weight for the new task type in
      the `tasks` dict for all capable aircraft.

    You may also need to update:

    * flightwaypointtype.py: Add a new waypoint type if necessary. Most mission types
      will need these, as aircraftgenerator.py uses the ingress point type to specialize AI
      tasks, and non-strike-like missions will need more specialized control.
    * ai_flight_planner.py: Use the new mission type in propose_missions so the AI will
      plan the new mission type.
    * FlightType.is_air_to_air and FlightType.is_air_to_ground: If the new mission type
      fits either of these categories, update those methods accordingly.
    """

    TARCAP = "TARCAP"
    BARCAP = "BARCAP"
    CAS = "CAS"
    # Legacy/unplanned task retained for save compatibility only. QRA interceptors
    # are now modeled via the squadron intercept_reserve, not a dedicated FlightType.
    INTERCEPTION = "Intercept"
    STRIKE = "Strike"
    ANTISHIP = "Anti-ship"
    SEAD = "SEAD"
    DEAD = "DEAD"
    ESCORT = "Escort"
    BAI = "BAI"
    SWEEP = "Fighter sweep"
    JAMMING = "Jamming"  # Standoff EW orbit — C-130J holds racetrack outside threat zone, WeaponHold
    OCA_RUNWAY = "OCA/Runway"
    OCA_AIRCRAFT = "OCA/Aircraft"
    AEWC = "AEW&C"
    TRANSPORT = "Transport"
    SEAD_ESCORT = "SEAD Escort"
    REFUELING = "Refueling"
    FERRY = "Ferry"
    AIR_ASSAULT = "Air Assault"
    SEAD_SWEEP = "SEAD Sweep"  # Reintroduce legacy "engage-whatever-you-can-find" SEAD
    ARMED_RECON = "Armed Recon"
    RECOVERY = "Recovery"
    TARPS = "TARPS"  # Player-flown F-14 photo recon — overflies target +5 min behind strikers
    SCAR = "SCAR"  # Rescue-escort "Sandy" in the Combat SAR package: A-10/Apache that protects the downed pilot, suppresses threats, and walks Jolly Green in. Repurposed from the retired strike-coord/armor-hunt task (see 414th-scar-rescue-rework-notes.md).
    SOF = "SOF Insert"  # C-130 airdrop that inserts a SOF capture team at a SCAR ambush point (helo does the CSAR recovery)
    CSAR = "CSAR"  # Helo extraction of a SOF team stranded by a botched SCAR capture (the recovery leg of the SOF loop)
    COMBAT_SAR = "Combat SAR"  # Standing pilot-rescue orbit near the FLOT (CH-47 pickup + C-130 "King"); rescues downed HUMAN pilots via MOOSE CSAR. Distinct from the SOF-recovery CSAR. Support orbit, modeled on RECOVERY/AEWC.

    @classmethod
    def _missing_(cls, value: object) -> FlightType | None:
        """Handle legacy persisted values from older 414th builds."""
        if value == "ISR":
            return cls.JAMMING
        # The 414th's SCRAMBLE QRA flight type was retired; it always behaved as a
        # BARCAP (BarCap flight plan, configure_cap, BARCAP loadout). Map old saves.
        if value == "Scramble":
            return cls.BARCAP
        # The Pretense campaign export (and its AI cargo flight type) was removed.
        # Only exported Pretense .miz used it, but migrate any stray persisted value.
        if value == "Cargo Transport":
            return cls.TRANSPORT
        return None

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_name(cls, name: str) -> FlightType:
        for entry in cls:
            if name == entry.value:
                return entry
        raise KeyError(f"No FlightType with name {name}")

    @property
    def is_air_to_air(self) -> bool:
        return self in {
            FlightType.TARCAP,
            FlightType.BARCAP,
            FlightType.INTERCEPTION,
            FlightType.ESCORT,
            FlightType.SWEEP,
        }

    @property
    def is_air_to_ground(self) -> bool:
        return self in {
            FlightType.CAS,
            FlightType.STRIKE,
            FlightType.ANTISHIP,
            FlightType.SEAD,
            FlightType.DEAD,
            FlightType.BAI,
            FlightType.OCA_RUNWAY,
            FlightType.OCA_AIRCRAFT,
            FlightType.SEAD_ESCORT,
            FlightType.AIR_ASSAULT,
            FlightType.SEAD_SWEEP,
            FlightType.ARMED_RECON,
            FlightType.SCAR,
            FlightType.SOF,
            FlightType.CSAR,
        }

    @property
    def is_escort_type(self) -> bool:
        return self in {FlightType.ESCORT, FlightType.SEAD_ESCORT}

    @property
    def is_primary_package_task(self) -> bool:
        return self in {
            FlightType.STRIKE,
            FlightType.OCA_AIRCRAFT,
            FlightType.OCA_RUNWAY,
            FlightType.DEAD,
            FlightType.ANTISHIP,
            FlightType.BAI,
            FlightType.CAS,
            FlightType.ARMED_RECON,
            FlightType.AIR_ASSAULT,
            FlightType.TARPS,
            FlightType.SCAR,
            FlightType.SOF,
            FlightType.CSAR,
        }

    @property
    def provides_escort_coverage(self) -> bool:
        """Flight types that fly escort-like coverage tied to the package's timing.

        Broader than ``is_escort_type``: includes TARCAP, which guards a strike package
        the same way a dedicated escort does and so is affected by manual-timing drift.
        """
        return self in {
            FlightType.ESCORT,
            FlightType.SEAD_ESCORT,
            FlightType.TARCAP,
        }

    @property
    def entity_type(self) -> AirEntity:
        return {
            FlightType.AEWC: AirEntity.AIRBORNE_EARLY_WARNING,
            FlightType.ANTISHIP: AirEntity.ANTISURFACE_WARFARE,
            FlightType.ARMED_RECON: AirEntity.ATTACK_STRIKE,
            FlightType.BAI: AirEntity.ATTACK_STRIKE,
            FlightType.BARCAP: AirEntity.FIGHTER,
            FlightType.CAS: AirEntity.ATTACK_STRIKE,
            FlightType.DEAD: AirEntity.ATTACK_STRIKE,
            FlightType.ESCORT: AirEntity.ESCORT,
            FlightType.FERRY: AirEntity.UNSPECIFIED,
            FlightType.INTERCEPTION: AirEntity.FIGHTER,
            FlightType.OCA_AIRCRAFT: AirEntity.ATTACK_STRIKE,
            FlightType.OCA_RUNWAY: AirEntity.ATTACK_STRIKE,
            FlightType.RECOVERY: AirEntity.TANKER,
            FlightType.REFUELING: AirEntity.TANKER,
            FlightType.SEAD: AirEntity.SUPPRESSION_OF_ENEMY_AIR_DEFENCE,
            FlightType.SEAD_ESCORT: AirEntity.SUPPRESSION_OF_ENEMY_AIR_DEFENCE,
            FlightType.SEAD_SWEEP: AirEntity.SUPPRESSION_OF_ENEMY_AIR_DEFENCE,
            FlightType.STRIKE: AirEntity.ATTACK_STRIKE,
            FlightType.SWEEP: AirEntity.FIGHTER,
            FlightType.JAMMING: AirEntity.ELECTRONIC_COMBAT_JAMMER,
            FlightType.TARPS: AirEntity.RECONNAISSANCE,
            FlightType.SCAR: AirEntity.ATTACK_STRIKE,
            FlightType.TARCAP: AirEntity.FIGHTER,
            FlightType.TRANSPORT: AirEntity.UTILITY,
            FlightType.AIR_ASSAULT: AirEntity.ROTARY_WING,
            # SOF insert is a fixed-wing transport airdrop (C-130), like TRANSPORT.
            FlightType.SOF: AirEntity.UTILITY,
            # CSAR is a helo recovery of a stranded SOF team.
            FlightType.CSAR: AirEntity.COMBAT_SEARCH_AND_RESCUE,
            # Combat SAR is a standing pilot-rescue orbit (same SIDC entity).
            FlightType.COMBAT_SAR: AirEntity.COMBAT_SEARCH_AND_RESCUE,
        }.get(self, AirEntity.UNSPECIFIED)
