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
    # Growler-only escort jamming: rides the package join->split like a SEAD
    # escort; the growler plugin drives the scripted jamming effect at runtime.
    # Capability comes solely from the yaml `tasks:` block -- only the EA-18G
    # declares it (user call 2026-07-21: the FA-18E/F never fly this).
    ESCORT_JAMMER = "Escort Jammer"
    REFUELING = "Refueling"
    FERRY = "Ferry"
    AIR_ASSAULT = "Air Assault"
    SEAD_SWEEP = "SEAD Sweep"  # Reintroduce legacy "engage-whatever-you-can-find" SEAD
    ARMED_RECON = "Armed Recon"
    RECOVERY = "Recovery"
    TARPS = "TARPS"  # Player-flown F-14 photo recon — overflies target +2 min behind strikers
    CSAR = "CSAR"  # Pilot rescue (upstream dcs-retribution#929).

    @classmethod
    def _missing_(cls, value: object) -> FlightType | None:
        """Remap legacy persisted values from older 414th builds.

        The remap table (_LEGACY_FLIGHT_TYPE_VALUES, below the class) is THE
        single source of truth: both runtime enum lookups (``FlightType("ISR")``)
        and the save unpickler (``persistency._handle_flight_type``, which calls
        ``FlightType(value)``) resolve through here, so a legacy rename is added
        in exactly one place.
        """
        if isinstance(value, str):
            return _LEGACY_FLIGHT_TYPE_VALUES.get(value)
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
        }

    @property
    def is_escort_type(self) -> bool:
        return self in {
            FlightType.ESCORT,
            FlightType.SEAD_ESCORT,
            FlightType.ESCORT_JAMMER,
        }

    @property
    def requires_helicopter(self) -> bool:
        """Tasks whose flight plan a fixed-wing aircraft cannot fly at all.

        CSAR lands at an unprepared site and the DCS AI ``Land`` task is
        helicopter-only, so ``CsarFlightPlan`` refuses to build for a fixed-wing
        flight. Without this the auto-planner picks the C-130J -- which offers
        CSAR for the player-flown King role -- and the PlanningError takes the
        whole turn down with it (flown 2026-08-16, 5th test).
        """
        return self is FlightType.CSAR

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
            FlightType.ESCORT_JAMMER,
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
            FlightType.CSAR: AirEntity.COMBAT_SEARCH_AND_RESCUE,
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
            FlightType.ESCORT_JAMMER: AirEntity.ELECTRONIC_COMBAT_JAMMER,
            FlightType.TARPS: AirEntity.RECONNAISSANCE,
            FlightType.TARCAP: AirEntity.FIGHTER,
            FlightType.TRANSPORT: AirEntity.UTILITY,
            FlightType.AIR_ASSAULT: AirEntity.ROTARY_WING,
        }.get(self, AirEntity.UNSPECIFIED)


# Legacy persisted FlightType values from older 414th builds, remapped on load.
# THE single source of truth for value renames: FlightType._missing_ (runtime
# lookups) and persistency._handle_flight_type (the unpickler, via
# FlightType(value)) both resolve through here. Add a "legacy value" -> live
# member entry here ONLY -- do not reintroduce a parallel table in the unpickler.
_LEGACY_FLIGHT_TYPE_VALUES: dict[str, FlightType] = {
    # C-130 EW/ISR consolidation: the old generic ISR type became JAMMING.
    "ISR": FlightType.JAMMING,
    # The retired SCRAMBLE QRA type always behaved as a BARCAP (BarCap flight
    # plan, configure_cap, BARCAP loadout).
    "Scramble": FlightType.BARCAP,
    # The removed Pretense campaign export's AI cargo flight type.
    "Cargo Transport": FlightType.TRANSPORT,
    # The retired SOF capture-economy insert (a C-130 airdrop). The whole
    # commander-capture loop is dead code removed 2026-07-01; a persisted SOF
    # flight degrades to the closest surviving C-130 task.
    "SOF Insert": FlightType.TRANSPORT,
    # The fork's own Combat SAR (§21) and its "Sandy" rescue escort (§15), both
    # removed 2026-08-07 when the fork adopted upstream #929's CSAR wholesale.
    # A persisted rescue flight becomes the upstream rescue; a persisted Sandy
    # degrades to the CAS it always flew.
    #
    # NOTE: the old shelved-POW-raid entry ("CSAR" -> TRANSPORT) was DELETED here,
    # not kept. FlightType.CSAR is now a live member, so FlightType("CSAR") resolves
    # directly and _missing_ is never consulted -- the entry was dead, and a
    # pre-2026-07-03 save's raid flight now loads as a rescue instead. Accepted:
    # both are helo-lift-shaped and that save predates three flight-type reworks.
    "Combat SAR": FlightType.CSAR,
    "SCAR": FlightType.CAS,
}
