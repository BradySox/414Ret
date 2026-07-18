"""Curated carrier deck decoration layouts (§72).

Deck-dressing statics for the Nimitz-family carriers, extracted verbatim from
the OCN 2 (Operation Cerberus North 2) campaign missions -- Sedlo's deck
dressing language, replayed onto Retribution's carriers: LSO platform crew on
the port-aft sponson plus a "street" of deck equipment (tow tractors, P-25
firefighting vehicle, Hyster forklift, deck crew) alongside the island.

Every static type here is base-game content: the AS32 gear and carrier
personnel ship in ``CoreMods/tech/USS_Nimitz`` and the CV-59 Hyster forklift in
``CoreMods/aircraft/F14`` -- both distributed with every DCS install, no module
ownership required.

Parking safety is the hard constraint (the whole point of the curation): every
placement keeps ALL of the deck's parking spawn spots and all four catapults
usable. Two envelopes are provably parking-free:

- The LSO platform sponson (x -134..-126, y -25..-18): off the deck surface;
  aircraft physically cannot park there.
- The island street (x -68..-40, y +12.5..+24.5): the strip between the
  landing-area foul line and the island. It is flanked by the six-pack row
  (y = +34), the corral (forward of the island face, x > -38) and the junkyard
  (aft, x < -72); no DCS parking location is documented or was ever observed
  inside it, and OCN 2 dresses it in all 13 missions of a flyable campaign.

The known spot anchors below were measured from flown-mission Tacview
recordings (t=0 frame, ship-frame transform) plus a 12 m row-pitch
extrapolation, and a guard test (tests/missiongenerator/test_carrier_deck_
decor.py) enforces the clearance for every table entry. The OCN missions also
dress the fantail and bow with static aircraft (E-2C, S-3B, SH-60B) -- those
sit on real parking real estate and are deliberately NOT reproduced.

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
    "AS32-p25": ("ADEquipment", None),  # P-25 firefighting vehicle
    "CV_59_H60": ("ADEquipment", None),  # CV-59 Hyster 60 forklift
    "us carrier tech": ("Personnel", "carrier_tech_USA"),
    "Carrier LSO Personell": ("Personnel", "carrier_lso_usa"),
    "Carrier LSO Personell 1": ("Personnel", "carrier_lso1_usa"),
    "Carrier LSO Personell 3": ("Personnel", "carrier_lso3_usa"),
    "Carrier LSO Personell 4": ("Personnel", "carrier_lso4_usa"),
}

# Hulls sharing the Nimitz deck plan (same spot geography, same island/LSO
# geometry). Kuznetsov, Tarawa and Forrestal have different decks with
# starboard-aft parking rows where these envelopes are NOT provably safe --
# deliberately excluded until their own layouts are curated.
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

# Minimum clearance any decoration must keep from every known spot centre.
# A folded Hornet half-span is ~4.7 m and observed spot placement jitter is
# under 2 m; 9 m leaves a parked jet plus margin.
MIN_SPOT_CLEARANCE_M = 9.0

# The safe envelopes, as (x_min, x_max, y_min, y_max).
LSO_PLATFORM_ENVELOPE = (-134.0, -126.0, -25.0, -18.0)
ISLAND_STREET_ENVELOPE = (-68.0, -40.0, 12.5, 24.5)

# The LSO platform crew -- identical offsets in all 13 OCN missions.
LSO_PLATFORM_CREW: list[DeckStatic] = [
    DeckStatic("Carrier LSO Personell", -129.45, -20.73, 349.1),
    DeckStatic("Carrier LSO Personell 4", -130.43, -20.64, 138.1),
    DeckStatic("Carrier LSO Personell 3", -130.49, -21.19, 165.1),
    DeckStatic("Carrier LSO Personell 1", -130.57, -22.34, 203.1),
]

# Island street sets, one per source mission, rotated per turn for variety.
# Placements are verbatim OCN 2 authoring filtered to the safe envelope.
STREET_VARIANTS: list[list[DeckStatic]] = [
    # OCN 2 mission 3 island street set
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
    # OCN 2 mission 10 island street set
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
    # OCN 2 mission 11 island street set
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
    # OCN 2 mission 12/13 island street set
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


def deck_layout_for(hull_id: str, seed_key: str, turn: int) -> list[DeckStatic]:
    """The decoration set for one carrier this turn.

    Empty for non-Nimitz decks. The street variant rotates deterministically
    on (carrier, turn) so a re-generated turn always dresses the deck the
    same way, while consecutive turns vary.
    """
    if hull_id not in NIMITZ_DECK_HULLS:
        return []
    variant = (crc32(seed_key.encode()) + turn) % len(STREET_VARIANTS)
    return LSO_PLATFORM_CREW + STREET_VARIANTS[variant]
