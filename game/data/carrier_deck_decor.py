"""Curated carrier deck decoration layouts (§72).

Deck-dressing statics for the Nimitz-family carriers, extracted verbatim from
the OCN 2 (Operation Cerberus North 2) campaign missions -- Sedlo's deck
dressing language, replayed onto Retribution's carriers: LSO platform crew on
the port-aft sponson, a "street" of deck equipment (tow tractors, P-25
firefighting vehicle, Hyster forklift, crane, deck crew) alongside the island,
an opt-in aft aircraft tier (folded Seahawks + a Hawkeye or Viking behind the
island), and an opt-in LAUNCH-PHASE set in the recovery corridor (the
round-down E-2 + the port junk-row gear) that the ``deckdecor`` plugin strikes
below before recovery traffic arrives.

Every static type here is base-game content: the AS32 gear and carrier
personnel ship in ``CoreMods/tech/USS_Nimitz`` and the CV-59 Hyster forklift in
``CoreMods/aircraft/F14`` -- both distributed with every DCS install, no module
ownership required.

Parking safety is the hard constraint (the whole point of the curation).
Placement classes and their rules:

- PERMANENT gear (LSO crew + street): only inside envelopes where parking is
  impossible -- the off-deck LSO sponson and the island street (the strip
  between the landing-area foul line and the island, flanked by the six-pack
  row, the corral forward and the junkyard aft; extended to the island's aft
  corner for the crane accents -- the junkyard's own spots sit further aft,
  x <= -80 by the SC manual's diagrams). Never inside the recovery corridor.
- AIRCRAFT tier (opt-in, default OFF): the starboard-aft arrangements
  DELIBERATELY spend a few of the deck's unmeasured aft parking spots
  (documented cost); they must still clear every MEASURED spot -- the ones
  Retribution's own spawns demonstrably use -- with per-type footprint
  margins.
- LAUNCH-PHASE (with the aircraft tier): may stand in the recovery corridor
  because the deckdecor plugin strikes them below before recovery (fallback
  timer, or fixed-wing traffic low astern). Must still clear every measured
  spot (the t=0 spawn wave runs while they stand), and must always reach the
  plugin's clear list.

The known spot anchors below were measured from flown-mission Tacview
recordings (t=0 frame, ship-frame transform) plus a 12 m row-pitch
extrapolation; the guard tests in tests/missiongenerator/test_carrier_deck_
decor.py enforce every rule above against every table entry.

Ship frame convention: x along the keel (positive forward), y athwartships
(positive starboard), angle in degrees relative to the ship's heading -- the
same frame as the DCS mission format's linked-static ``offsets`` table.
"""

from __future__ import annotations

from typing import NamedTuple
from zlib import crc32

from dcs.ships import CVN_71, CVN_72, CVN_73, CVN_75, Stennis


class DeckStatic(NamedTuple):
    """One deck decoration: a static type at a ship-frame offset."""

    type: str
    x: float
    y: float
    angle_deg: float


# DCS static category / shape_name per type (as authored in the OCN missions;
# the miz omits shape_name for the ADEquipment gear).
STATIC_META: dict[str, tuple[str, str | None]] = {
    "AS32-31A": ("ADEquipment", None),  # flight deck tow tractor
    "AS32-32A": ("ADEquipment", None),  # spotting dolly / tow tractor
    "AS32-36A": ("ADEquipment", None),  # aircraft crane
    "AS32-p25": ("ADEquipment", None),  # P-25 firefighting vehicle
    "CV_59_H60": ("ADEquipment", None),  # CV-59 Hyster 60 forklift
    "us carrier tech": ("Personnel", "carrier_tech_USA"),
    "Carrier LSO Personell": ("Personnel", "carrier_lso_usa"),
    "Carrier LSO Personell 1": ("Personnel", "carrier_lso1_usa"),
    "Carrier LSO Personell 3": ("Personnel", "carrier_lso3_usa"),
    "Carrier LSO Personell 4": ("Personnel", "carrier_lso4_usa"),
    "Carrier LSO Personell 5": ("Personnel", "carrier_lso5_usa"),
    "SH-60B": ("Helicopters", None),  # static folded Seahawk
    "E-2C": ("Planes", None),  # static Hawkeye (renders FOLDED -- user-confirmed)
    "S-3B Tanker": ("Planes", None),  # static Viking
}

# Hulls sharing the Nimitz deck plan (same spot geography, same island/LSO
# geometry). Kuznetsov, Tarawa and Forrestal have different decks with
# starboard-aft parking rows where these envelopes are NOT provably safe --
# deliberately excluded (offered and declined 2026-07-18).
NIMITZ_DECK_HULLS = frozenset({Stennis.id, CVN_71.id, CVN_72.id, CVN_73.id, CVN_75.id})

# Measured parking spawn spots (ship frame). Sources: Tacview recordings of
# flown Retribution carrier missions, t=0 frame -- deck cold-spawns relative
# to the carrier -- plus the observed 12 m six-pack row pitch extrapolated to
# the row's documented four spots. Kept here as the guard-test keep-out set
# and as documentation of the evidence this curation rests on.
KNOWN_PARKING_SPOTS: tuple[tuple[float, float], ...] = (
    (1.0, 34.0),  # six-pack row spot (measured; player took it first)
    (-11.5, 34.0),  # six-pack row spot (measured)
    (-23.5, 34.0),  # six-pack row (extrapolated, 12 m pitch)
    (-35.5, 34.0),  # six-pack row (extrapolated, 12 m pitch)
    (-84.5, -34.0),  # port quarter (measured; first F-14-capable spot)
    (-96.5, -34.0),  # port quarter (measured)
    (58.5, -31.4),  # bow-port helo spot (measured; the CSAR helo parks here)
)

# Minimum centre distance a SMALL static (deck gear / a crew figure) must keep
# from every measured spot: a folded Hornet half-span (~4.7 m) at the spot +
# placement jitter (<2 m) + margin.
MIN_SPOT_CLEARANCE_M = 9.0

# Aircraft statics are bigger than deck gear: their required clearance is
# MIN_SPOT_CLEARANCE_M + this per-type extra (their own worst-case
# half-extent). The E-2C static renders FOLDED (user-confirmed in game --
# the earlier wings-spread read was wrong), so its extent is the 17.6 m
# fuselage length, not the 24.6 m span.
FOOTPRINT_EXTRA_M: dict[str, float] = {
    "E-2C": 8.0,
    "S-3B Tanker": 10.5,  # fold state unverified -- keep the spread margin
    "SH-60B": 6.5,
}


def required_spot_clearance_m(static_type: str) -> float:
    return MIN_SPOT_CLEARANCE_M + FOOTPRINT_EXTRA_M.get(static_type, 0.0)


# The safe envelopes for PERMANENT gear, as (x_min, x_max, y_min, y_max).
LSO_PLATFORM_ENVELOPE = (-134.0, -126.0, -25.0, -18.0)
ISLAND_STREET_ENVELOPE = (-74.0, -40.0, 12.5, 26.0)

# The ramp-crossing / wires keep-out (x_min, x_max, y_min, y_max): the stern
# threshold and touchdown zone that every recovering aircraft crosses a few
# metres above the deck. PERMANENT placements may never stand here -- the
# lesson of the round-down E-2C (user-caught 2026-07-18): it cleared every
# parking spot but stands 5.6 m tall and 17.6 m long essentially at the ramp
# crossing. Only LAUNCH-PHASE dressing may stand inside, because the deckdecor
# plugin strikes it below before recovery.
LANDING_AREA_KEEP_OUT = (-170.0, -120.0, -15.0, 12.0)

# Everything launch-phase must be AFT dressing (the recovery corridor / LSO
# area). Nothing launch-phase may stand forward of this -- forward statics
# would stand in the bow-catapult taxi flow exactly during the launch cycle
# (the reason M4's bow set stays excluded entirely).
LAUNCH_PHASE_MAX_X = -100.0

# The LSO platform crew -- identical offsets in all 13 OCN missions.
LSO_PLATFORM_CREW: list[DeckStatic] = [
    DeckStatic("Carrier LSO Personell", -129.45, -20.73, 349.1),
    DeckStatic("Carrier LSO Personell 4", -130.43, -20.64, 138.1),
    DeckStatic("Carrier LSO Personell 3", -130.49, -21.19, 165.1),
    DeckStatic("Carrier LSO Personell 1", -130.57, -22.34, 203.1),
]

# Island street sets, one per source mission, rotated per turn for variety.
# Placements are verbatim OCN 2 authoring filtered to the safe envelope --
# never mixed across missions within a zone (mixed sets clip; the M11 tractor
# vs the M9 crane sit 2 m apart).
STREET_VARIANTS: list[list[DeckStatic]] = [
    # OCN 2 mission 3 street set
    [
        DeckStatic("us carrier tech", -40.37, 20.35, 316.5),
        DeckStatic("AS32-31A", -41.13, 14.24, 259.5),
        DeckStatic("us carrier tech", -42.70, 14.13, 316.5),
        DeckStatic("us carrier tech", -43.27, 21.11, 263.5),
        DeckStatic("AS32-31A", -43.29, 16.57, 255.5),
        DeckStatic("us carrier tech", -45.66, 18.79, 317.5),
        DeckStatic("AS32-32A", -47.66, 15.14, 359.5),
        DeckStatic("AS32-31A", -49.13, 23.20, 0.5),
        DeckStatic("us carrier tech", -52.64, 24.01, 316.5),
        DeckStatic("us carrier tech", -53.47, 23.28, 354.5),
        DeckStatic("CV_59_H60", -54.20, 19.40, 258.5),
        DeckStatic("AS32-p25", -59.84, 19.11, 267.5),
    ],
    # OCN 2 mission 6 street set (incl. the crane at the island's aft corner)
    [
        DeckStatic("us carrier tech", -44.79, 18.86, 281.4),
        DeckStatic("us carrier tech", -45.97, 18.74, 305.0),
        DeckStatic("AS32-p25", -47.34, 20.65, 260.0),
        DeckStatic("us carrier tech", -51.61, 16.16, 281.4),
        DeckStatic("us carrier tech", -51.83, 14.74, 304.4),
        DeckStatic("AS32-p25", -53.13, 16.92, 264.4),
        DeckStatic("AS32-32A", -58.26, 22.29, 76.0),
        DeckStatic("AS32-36A", -72.86, 25.69, 182.0),
    ],
    # OCN 2 mission 9 street set (incl. the crane)
    [
        DeckStatic("AS32-p25", -40.73, 16.35, 269.2),
        DeckStatic("AS32-31A", -44.77, 19.68, 265.0),
        DeckStatic("CV_59_H60", -47.96, 21.66, 285.2),
        DeckStatic("CV_59_H60", -50.25, 21.85, 273.2),
        DeckStatic("us carrier tech", -54.84, 18.59, 314.2),
        DeckStatic("AS32-31A", -55.35, 20.98, 265.0),
        DeckStatic("us carrier tech", -58.71, 17.75, 281.2),
        DeckStatic("AS32-32A", -59.89, 19.95, 76.0),
        DeckStatic("AS32-36A", -68.95, 20.73, 162.2),
    ],
    # OCN 2 mission 10 street set
    [
        DeckStatic("us carrier tech", -40.35, 16.87, 322.7),
        DeckStatic("CV_59_H60", -41.37, 17.85, 81.7),
        DeckStatic("us carrier tech", -42.67, 16.29, 314.7),
        DeckStatic("AS32-31A", -43.50, 20.72, 265.0),
        DeckStatic("AS32-31A", -46.65, 20.94, 277.7),
        DeckStatic("us carrier tech", -48.93, 17.86, 189.0),
        DeckStatic("us carrier tech", -50.14, 17.70, 305.0),
        DeckStatic("us carrier tech", -51.71, 12.95, 288.7),
        DeckStatic("AS32-32A", -53.07, 15.08, 357.7),
        DeckStatic("AS32-31A", -53.19, 20.68, 265.0),
        DeckStatic("AS32-p25", -56.21, 20.71, 268.7),
        DeckStatic("AS32-31A", -58.51, 21.68, 265.0),
        DeckStatic("AS32-p25", -62.31, 18.40, 268.7),
    ],
    # OCN 2 mission 11 street set
    [
        DeckStatic("us carrier tech", -41.09, 13.62, 189.0),
        DeckStatic("AS32-31A", -42.17, 16.42, 265.0),
        DeckStatic("CV_59_H60", -44.86, 20.73, 105.7),
        DeckStatic("us carrier tech", -47.49, 19.04, 277.7),
        DeckStatic("us carrier tech", -51.66, 16.03, 276.7),
        DeckStatic("us carrier tech", -52.43, 15.75, 276.7),
        DeckStatic("AS32-p25", -53.08, 18.47, 266.7),
        DeckStatic("AS32-p25", -56.08, 18.30, 266.7),
        DeckStatic("us carrier tech", -56.81, 13.41, 276.7),
        DeckStatic("CV_59_H60", -57.88, 23.30, 257.7),
        DeckStatic("us carrier tech", -58.18, 15.57, 276.7),
        DeckStatic("us carrier tech", -58.44, 14.78, 34.7),
        DeckStatic("us carrier tech", -60.35, 21.44, 277.7),
        DeckStatic("AS32-32A", -62.99, 21.12, 357.7),
        DeckStatic("AS32-32A", -66.76, 20.52, 269.7),
    ],
    # OCN 2 mission 12/13 street set
    [
        DeckStatic("us carrier tech", -41.69, 16.35, 340.8),
        DeckStatic("us carrier tech", -42.79, 15.58, 340.8),
        DeckStatic("AS32-31A", -42.89, 18.92, 265.0),
        DeckStatic("us carrier tech", -44.94, 17.08, 276.8),
        DeckStatic("AS32-31A", -45.35, 19.94, 265.0),
        DeckStatic("us carrier tech", -46.05, 17.06, 281.8),
        DeckStatic("AS32-32A", -47.49, 14.72, 0.8),
        DeckStatic("CV_59_H60", -53.00, 22.95, 269.1),
        DeckStatic("CV_59_H60", -55.11, 22.75, 269.1),
        DeckStatic("AS32-31A", -58.93, 19.84, 259.8),
    ],
]

# --- The aircraft tier (carrier_deck_decorations_aircraft, default OFF) -----
#
# Starboard-aft PERMANENT arrangements. These deliberately spend a few of the
# deck's unmeasured aft spots (the junkyard pair + roughly one more under the
# fixed-wing accent) -- the documented tier cost. Helo pairs and fixed-wing
# accents live in separate sub-zones (25+ m apart), so rotating them
# independently can never clip; each entry is one mission's verbatim
# arrangement.
HELO_ARRANGEMENTS: list[list[DeckStatic]] = [
    # OCN 2 missions 6/7/9 pair (outer row)
    [
        DeckStatic("SH-60B", -134.29, 27.02, 277.0),
        DeckStatic("SH-60B", -122.57, 28.24, 277.0),
    ],
    # OCN 2 mission 2 pair (inner row)
    [
        DeckStatic("SH-60B", -130.21, 23.91, 275.3),
        DeckStatic("SH-60B", -121.76, 23.70, 275.3),
    ],
    # OCN 2 mission 4 pair (forward inner row)
    [
        DeckStatic("SH-60B", -121.86, 23.84, 277.0),
        DeckStatic("SH-60B", -115.89, 23.54, 265.2),
    ],
]

# One fixed-wing parked behind the island (the El-3/junkyard shoulder).
FIXED_WING_ACCENTS: list[list[DeckStatic]] = [
    [DeckStatic("E-2C", -97.80, 28.80, 272.3)],  # OCN 2 mission 2
    [DeckStatic("E-2C", -97.00, 31.40, 285.7)],  # OCN 2 mission 11
    [DeckStatic("S-3B Tanker", -98.70, 29.90, 265.8)],  # OCN 2 mission 5
]

# --- Launch-phase dressing (aircraft tier; runtime-cleared) -----------------
#
# Statics that stand in/near the recovery corridor during the launch cycle and
# are struck below by the deckdecor plugin before recovery. Two independent
# sub-zones, rotated per turn; zones are 25+ m apart so cross-mission
# combination cannot clip.
ROUND_DOWN_VARIANTS: list[list[DeckStatic]] = [
    [DeckStatic("E-2C", -152.14, 5.37, 350.0)],  # OCN 2 mission 8
    [DeckStatic("E-2C", -138.04, 5.12, 352.1)],  # OCN 2 mission 1
]

# The port junk row between the LSO platform and the wires -- gear and hands
# dressing the LSO approach area during launch.
PORT_JUNK_VARIANTS: list[list[DeckStatic]] = [
    # OCN 2 mission 4 set (incl. the fifth LSO figure up-deck of the platform)
    [
        DeckStatic("AS32-p25", -120.03, -25.65, 89.6),
        DeckStatic("us carrier tech", -122.14, -24.90, 250.6),
        DeckStatic("us carrier tech", -119.34, -28.92, 355.6),
        DeckStatic("us carrier tech", -118.30, -27.07, 340.6),
        DeckStatic("Carrier LSO Personell 5", -113.58, -23.42, 325.6),
    ],
    # OCN 2 mission 5 set
    [
        DeckStatic("AS32-31A", -113.70, -27.63, 265.0),
        DeckStatic("us carrier tech", -105.66, -24.61, 292.8),
    ],
]


def _pick(
    variants: list[list[DeckStatic]], seed_key: str, salt: str, turn: int
) -> list[DeckStatic]:
    return variants[(crc32(f"{seed_key}|{salt}".encode()) + turn) % len(variants)]


def deck_layout_for(
    hull_id: str, seed_key: str, turn: int, include_aircraft: bool = False
) -> list[DeckStatic]:
    """The PERMANENT decoration set for one carrier this turn.

    Empty for non-Nimitz decks. Every slot rotates deterministically on
    (carrier, turn) so a re-generated turn always dresses the deck the same
    way, while consecutive turns vary. ``include_aircraft`` appends the
    spot-costing starboard-aft aircraft arrangements.
    """
    if hull_id not in NIMITZ_DECK_HULLS:
        return []
    layout = LSO_PLATFORM_CREW + _pick(STREET_VARIANTS, seed_key, "street", turn)
    if include_aircraft:
        layout = layout + _pick(HELO_ARRANGEMENTS, seed_key, "helos", turn)
        layout = layout + _pick(FIXED_WING_ACCENTS, seed_key, "accent", turn)
    return layout


def launch_phase_dressing_for(
    hull_id: str, seed_key: str, turn: int, include_aircraft: bool
) -> list[DeckStatic]:
    """The launch-phase (runtime-cleared) set for one carrier this turn."""
    if not include_aircraft or hull_id not in NIMITZ_DECK_HULLS:
        return []
    return _pick(ROUND_DOWN_VARIANTS, seed_key, "rounddown", turn) + _pick(
        PORT_JUNK_VARIANTS, seed_key, "portjunk", turn
    )
