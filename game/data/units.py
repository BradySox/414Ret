from __future__ import annotations

from enum import unique, Enum


@unique
class UnitClass(Enum):
    UNKNOWN = "Unknown"
    AAA = "AAA"
    AIRCRAFT_CARRIER = "AircraftCarrier"
    APC = "APC"
    ARTILLERY = "Artillery"
    ATGM = "ATGM"
    BOAT = "Boat"
    COMMAND_POST = "CommandPost"
    CRUISER = "Cruiser"
    DESTROYER = "Destroyer"
    EARLY_WARNING_RADAR = "EarlyWarningRadar"
    FORTIFICATION = "Fortification"
    FRIGATE = "Frigate"
    HELICOPTER = "Helicopter"
    HELICOPTER_CARRIER = "HelicopterCarrier"
    IFV = "IFV"
    INFANTRY = "Infantry"
    LANDING_SHIP = "LandingShip"
    LAUNCHER = "Launcher"
    LOGISTICS = "Logistics"
    MANPAD = "Manpad"
    MISSILE = "Missile"
    ANTISHIP_MISSILE = "AntiShipMissile"
    OPTICAL_TRACKER = "OpticalTracker"
    PLANE = "Plane"
    POWER = "Power"
    RECON = "Recon"
    SEARCH_LIGHT = "SearchLight"
    SEARCH_RADAR = "SearchRadar"
    SEARCH_TRACK_RADAR = "SearchTrackRadar"
    SHORAD = "SHORAD"
    SPECIALIZED_RADAR = "SpecializedRadar"
    SUBMARINE = "Submarine"
    TANK = "Tank"
    TELAR = "TELAR"
    TRACK_RADAR = "TrackRadar"


# All UnitClasses which can have AntiAir capabilities
ANTI_AIR_UNIT_CLASSES = [
    UnitClass.AAA,
    UnitClass.AIRCRAFT_CARRIER,
    UnitClass.CRUISER,
    UnitClass.DESTROYER,
    UnitClass.EARLY_WARNING_RADAR,
    UnitClass.FRIGATE,
    UnitClass.HELICOPTER_CARRIER,
    UnitClass.LAUNCHER,
    UnitClass.MANPAD,
    UnitClass.SEARCH_RADAR,
    UnitClass.SEARCH_TRACK_RADAR,
    UnitClass.SPECIALIZED_RADAR,
    UnitClass.SHORAD,
    UnitClass.SUBMARINE,
    UnitClass.TELAR,
    UnitClass.TRACK_RADAR,
]

# Mobile, self-contained point air-defense unit classes: the unit-level
# complement of forcegroup._MOBILE_TASKS = {SHORAD, AAA}. A generated DCS group
# that contains any of these should be hidden on the MFD/datalink even when the
# group's own task is not air defense -- e.g. a SHORAD/AAA/MANPAD escort placed
# inside an armor or missile group, which would otherwise inherit the parent
# group's visible flag and betray its position on the datalink.
#
# Deliberately excludes TELAR and the radar/launcher classes so standalone
# MERAD/LORAD SAM sites (SA-6/11, SA-2/3/5/10, etc.) stay visible/targetable for
# SEAD, matching the existing _MOBILE_TASKS scope.
MOBILE_AIR_DEFENSE_UNIT_CLASSES = frozenset(
    {
        UnitClass.AAA,
        UnitClass.SHORAD,
        UnitClass.MANPAD,
    }
)

# DCS unit ids of heavy bombers. Vanilla DCS heavy bombers only (per the fork's
# vanilla-units rule). Shared by two Vietnam-era consumers: the Arc Light emitter
# (game/missiongenerator/vietnamopsluadata.py -- a Strike by anything not in this
# set is an ordinary single-aimpoint strike) and the doctrine low-level attack
# profile (game/data/doctrine.py -- a heavy is never pressed onto the deck).
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

# Unmanned ISR/strike aircraft (UAVs). DCS carries no reliable "is a drone" flag --
# `category` buckets them as generic "Air" alongside the B-52/C-130 -- so this is a
# curated id set (the vanilla drones; extend if a mod drone is ever added). A drone is
# always a sensor: it feeds recon/BDA home regardless of its tasked mission (the 414th
# "a drone is always filming" rule), so the AI-recon capture emits every AI-flown drone
# flight, not only the TARPS-tasked ones (game/missiongenerator/aireconluadata.py). Also
# the JTAC-drone platform for a faction (game/factions/faction.py `jtac_unit`).
UAV_DCS_IDS = frozenset(
    {
        "MQ-9 Reaper",
        "RQ-1A Predator",
        "WingLoong-I",
    }
)

# Unit classes the strategic ground-war planner can actually deploy at a front.
# Other inventory-backed assets (notably the SCAR SOF teams, which are INFANTRY)
# may live in Base.armor, but must not dilute deployment ratios or count as
# surviving front-line combat strength.
FRONTLINE_UNIT_CLASSES = frozenset(
    {
        UnitClass.TANK,
        UnitClass.APC,
        UnitClass.ARTILLERY,
        UnitClass.IFV,
        UnitClass.LOGISTICS,
        UnitClass.ATGM,
        UnitClass.SHORAD,
        UnitClass.AAA,
        UnitClass.RECON,
    }
)
