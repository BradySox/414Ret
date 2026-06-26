"""Task-filtered brevity reminders for the Comms & Brevity kneeboard card.

A short crib sheet of the standard multi-service brevity calls most relevant to a
flight's *task*, so a player sees the handful of terms that matter for what they are
about to do rather than the whole dictionary. Curated and generic (standard
terminology), so it is also upstreamable.

Keyed by ``FlightType`` via a small set of categories; an uncatalogued task falls
back to a general set.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from game.ato.flighttype import FlightType

#: (term, plain-language meaning) lines per category. Kept to ~6 so the block stays
#: a reminder, not a glossary.
_A2A: List[Tuple[str, str]] = [
    ("FOX 1 / 2 / 3", "SARH / IR / active-radar missile away"),
    ("COMMIT", "intercepting the assigned group"),
    ("BANDIT / BOGEY", "confirmed hostile / unknown contact"),
    ("TALLY / VISUAL", "see the threat / see the friendly"),
    ("NO JOY / BLIND", "no contact on threat / on friendly"),
    ("BUGOUT", "abandon the intercept and separate"),
]
_SEAD: List[Tuple[str, str]] = [
    ("MAGNUM", "anti-radiation missile (HARM) in flight"),
    ("SPIKE / NAILS", "RWR lock / RWR search hit"),
    ("MUD <type>", "ground-threat radar, type called"),
    ("SHOOTER", "I am engaging this emitter"),
    ("FENCE IN / OUT", "combat switches set / safe for egress"),
    ("WINCHESTER", "out of anti-radiation missiles"),
]
_STRIKE: List[Tuple[str, str]] = [
    ("RIFLE / PICKLE", "A-G missile away / bombs released"),
    ("CAPTURED", "target acquired on the TGP/sensor"),
    ("FEET WET / DRY", "crossing the coast out / in"),
    ("FENCE IN / OUT", "combat switches set / safe for egress"),
    ("MISSION COMPLETE", "assigned target serviced"),
    ("BINGO", "fuel to RTB with reserves"),
]
_CAS: List[Tuple[str, str]] = [
    ("CONTACT", "I see the point / mark you called"),
    ("CLEARED HOT", "weapons release authorized"),
    ("IN / OFF", "commencing attack run / pulling off"),
    ("ABORT", "cease the attack immediately"),
    ("TALLY", "I see the target"),
    ("WINCHESTER", "out of ordnance"),
]
_EW: List[Tuple[str, str]] = [
    ("MUSIC ON / OFF", "active jamming on / off"),
    ("STROBE", "jammer strobe on the RWR, bearing called"),
    ("FENCE IN / OUT", "combat switches set / safe for egress"),
    ("BINGO", "fuel to RTB with reserves"),
]
_CONTROL: List[Tuple[str, str]] = [
    ("PICTURE", "summary of the air situation"),
    ("BULLSEYE", "range/bearing from the briefed reference"),
    ("BOGEY DOPE", "BRAA to the nearest hostile, requested"),
    ("DECLARE", "identity of a specified contact, requested"),
    ("ON / OFF STATION", "arriving at / leaving the orbit"),
]
_GENERAL: List[Tuple[str, str]] = [
    ("FENCE IN / OUT", "combat switches set / safe for egress"),
    ("FEET WET / DRY", "crossing the coast out / in"),
    ("BINGO / JOKER", "RTB fuel / pre-briefed lower fuel state"),
    ("KNOCK IT OFF", "cease the maneuver / engagement"),
]

_CATEGORY: Dict[FlightType, Tuple[str, List[Tuple[str, str]]]] = {
    FlightType.TARCAP: ("A2A", _A2A),
    FlightType.BARCAP: ("A2A", _A2A),
    FlightType.INTERCEPTION: ("A2A", _A2A),
    FlightType.ESCORT: ("A2A", _A2A),
    FlightType.SWEEP: ("A2A", _A2A),
    FlightType.SEAD: ("SEAD", _SEAD),
    FlightType.DEAD: ("SEAD", _SEAD),
    FlightType.SEAD_ESCORT: ("SEAD", _SEAD),
    FlightType.SEAD_SWEEP: ("SEAD", _SEAD),
    FlightType.STRIKE: ("STRIKE", _STRIKE),
    FlightType.OCA_RUNWAY: ("STRIKE", _STRIKE),
    FlightType.OCA_AIRCRAFT: ("STRIKE", _STRIKE),
    FlightType.ANTISHIP: ("STRIKE", _STRIKE),
    FlightType.CAS: ("CAS", _CAS),
    FlightType.BAI: ("CAS", _CAS),
    FlightType.SCAR: ("CAS", _CAS),
    FlightType.ARMED_RECON: ("CAS", _CAS),
    FlightType.JAMMING: ("EW", _EW),
    FlightType.AEWC: ("CONTROL", _CONTROL),
}


def brevity_for(flight_type: FlightType) -> Tuple[str, List[Tuple[str, str]]]:
    """(category label, brevity lines) most relevant to ``flight_type``.

    Falls back to a small general set for tasks without a dedicated category.
    """
    return _CATEGORY.get(flight_type, ("GENERAL", _GENERAL))
