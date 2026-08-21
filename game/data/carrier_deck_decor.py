"""Curated carrier deck decoration layouts (§72).

Deck-dressing statics for the Nimitz-family carriers, extracted from the
campaign A campaign missions -- the campaign author's deck dressing language,
replayed onto Retribution's carriers: LSO platform crew on the port-aft
sponson, and a "street" of deck equipment (tow tractors, P-25 firefighting
vehicle, Hyster forklift, crane, deck crew) alongside the island, forward of
the angled deck.

One tier, standing the whole mission. There is no launch-phase or
recovery-phase set: the same dressing is correct for both cycles because it
stands where a deck is never spotted (DM call, 2026-08-20). The two phase
tiers that used to exist -- a round-down E-2C struck below before recovery,
and a bow respot spawned in its place -- are gone, along with the runtime
plugin that swapped them.

Every static type here is base-game content: the AS32 gear and carrier
personnel ship in ``CoreMods/tech/USS_Nimitz`` and the CV-59 Hyster forklift in
``CoreMods/aircraft/F14`` -- both distributed with every DCS install, no module
ownership required.

Parking safety is the hard constraint (the whole point of the curation).
Dressing may stand ONLY where parking does not happen -- the off-deck LSO
sponson and the island street, starboard of the angled-deck foul line and
inboard of the six-pack parking row (the campaign A by-the-island offsets
rendered on the foul-line strip and were repositioned forward, flown CVN-71
2026-07-21). Never inside the recovery corridor, and guard-tested clear of
every known spot.

NO static aircraft, anywhere, ever. The first cut parked campaign A's Seahawk
pair + a fixed-wing accent on the starboard-aft spots under the manual's "a
blocked spot is skipped" claim -- and the first flown mission FALSIFIED that
for Retribution's dominant spawn path: LATE-ACTIVATED groups (the §64 TOT-delay
pattern) do NOT skip statics-obstructed spots (a flown CVN-73 late-activated
A-6E pair straight INTO the Seahawk statics, 2026-07-18). Test 11 then showed
the same hazard reaches any hour of the mission: 14 aircraft late-activated
onto the CVN-71 deck between t=2340 and t=3913, so "it only stands once
launches are over" was never a safe exemption. The parked-aircraft look comes
from Retribution's real deck population instead; those positions are kept
below as LEARNED spot anchors.

The known spot anchors below were measured from flown-mission Tacview
recordings (t=0 frame, ship-frame transform) plus a 12 m row-pitch
extrapolation; the guard tests in tests/missiongenerator/test_carrier_deck_
decor.py enforce every rule above against every table entry.

Ship frame convention: x along the keel (positive forward), y athwartships
(positive starboard), angle in degrees relative to the ship's heading -- the
same frame as the DCS mission format's linked-static ``offsets`` table.
"""

from __future__ import annotations

import math
from typing import NamedTuple
from zlib import crc32

from dcs.ships import CVN_71, CVN_72, CVN_73, CVN_75, Stennis


class DeckStatic(NamedTuple):
    """One deck decoration: a static type at a ship-frame offset."""

    type: str
    x: float
    y: float
    angle_deg: float


# DCS static category / shape_name per type (as authored in the campaign A missions;
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
    (-108.0, -34.0),  # port quarter, forward end (measured, flown CVN-71 2026-07-21;
    #                   a Hornet spawned here 8.7 m from the port junk-row static)
    (58.5, -31.4),  # bow-port helo spot (measured; Airboss's rescue helo spawns here)
    # LEARNED the hard way (flown CVN-73, 2026-07-18): late-activated A-6s
    # spawned INTO statics standing at these former aircraft-tier positions --
    # the starboard-aft junkyard pair + the El-3 shoulder are real spawn
    # spots, and late activations do not skip obstructed spots.
    (-134.3, 27.0),  # junkyard spot (~spot 7; campaign A parks a Seahawk here)
    (-122.6, 28.2),  # junkyard spot (~spot 8; campaign A parks a Seahawk here)
    (-98.7, 29.9),  # El-3 shoulder spot (campaign A parks an S-3/E-2 here)
    # MEASURED 2026-08-17 from five CVN-71 recordings by the same t=0 method,
    # closing the two holes the 2026-08-07 audit named: the row was known only
    # aft of x=+1.0, and nothing at all was known between x=-35.5 and x=-98.7.
    # Cluster centres over 6-9 sightings each, across 4-5 independent missions,
    # with F-14/Hornet/EA-18G all parking to the same centres.
    (35.6, 36.7),  # six-pack row, forward pair (n=6, 5 missions)
    (23.4, 35.5),  # six-pack row, forward pair (n=6, 4 missions)
    (-89.8, 26.4),  # starboard mid-deck, aft end of the old blind band (n=9, 5)
    (-76.3, 26.4),  # starboard mid-deck, same row forward (n=1 -- see below)
    (-74.6, -38.4),  # port quarter, forward of -84.5 (n=2; continues the 12 m pitch)
)
# The two thin entries above (n=1 and n=2) are deliberately kept. This table is
# a KEEP-OUT set: an extra entry can only reject a decoration, never place one,
# so a single real sighting is worth more than the certainty it lacks.

# Minimum centre distance a SMALL static (deck gear / a crew figure) must keep
# from every measured spot: a folded Hornet half-span (~4.7 m) at the spot +
# placement jitter (<2 m) + margin.
MIN_SPOT_CLEARANCE_M = 9.0

# The safe envelopes, as (x_min, x_max, y_min, y_max).
LSO_PLATFORM_ENVELOPE = (-134.0, -126.0, -25.0, -18.0)
# The island street: the clear staging strip ALONGSIDE the island, starboard
# of the angled-deck foul line and inboard of the six-pack parking row. This is
# where the street gear lives after the flown reposition (2026-07-27) -- the
# forward corral (the previous 2026-07-21 reposition) was too far forward, so
# the user marked the cluster "generating in the red instead of the blue" and
# wanted it pulled back aft, tucked outboard against the island. The campaign A
# literals are shifted into this box by CORRAL_SHIFT. Box is guard-tested clear
# of the six-pack row (y = +34) and the aft junkyard/El-3 spots (x < -98).
ISLAND_STREET_ENVELOPE = (-65.0, -30.0, 10.0, 25.0)

# The ramp-crossing / wires keep-out (x_min, x_max, y_min, y_max): the stern
# threshold and touchdown zone that every recovering aircraft crosses a few
# metres above the deck. Nothing may stand here -- the lesson of the round-down
# E-2C (user-caught 2026-07-18): it cleared every parking spot but stands 5.6 m
# tall and 17.6 m long essentially at the ramp crossing.
LANDING_AREA_KEEP_OUT = (-170.0, -120.0, -15.0, 12.0)

# The LSO platform crew -- identical offsets in all 13 campaign A missions.
LSO_PLATFORM_CREW: list[DeckStatic] = [
    DeckStatic("Carrier LSO Personell", -129.45, -20.73, 349.1),
    DeckStatic("Carrier LSO Personell 4", -130.43, -20.64, 138.1),
    DeckStatic("Carrier LSO Personell 3", -130.49, -21.19, 165.1),
    DeckStatic("Carrier LSO Personell 1", -130.57, -22.34, 203.1),
]

# The island-street reposition (flown, 2026-07-27). History: the campaign A street
# gear offsets below place the cluster on the foul-line strip (x -40..-74),
# which the user rejected 2026-07-21; that fix shoved the whole cluster +30 m
# FORWARD into the corral, but the forward corral overshot -- the user marked
# it "generating in the red instead of the blue" and wanted it pulled back aft
# and tucked outboard against the island (the clear street between the foul
# line and the island base). This shift moves the campaign A arrangement ~10 m aft of
# raw / ~5 m outboard vs the old forward corral, preserving the relative
# layout. Every shifted variant clears every KNOWN_PARKING_SPOT by >= 12 m
# (guard-tested); the min is 12.7 m at the six-pack row.
CORRAL_SHIFT = (9.0, -1.0)

# campaign A street sets, one per source mission, rotated per turn for variety.
# Placements are verbatim campaign A authoring (by-the-island) -- never mixed across
# missions within a zone (mixed sets clip). Shifted into the corral by
# CORRAL_SHIFT to form STREET_VARIANTS below.
_CAMPAIGN_A_STREET_VARIANTS: list[list[DeckStatic]] = [
    # campaign A mission 3 street set
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
    # campaign A mission 6 street set (incl. the crane at the island's aft corner)
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
    # campaign A mission 9 street set (incl. the crane)
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
    # campaign A mission 10 street set
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
    # campaign A mission 11 street set
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
    # campaign A mission 12/13 street set
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
    # campaign A mission 1 street set
    [
        DeckStatic("AS32-p25", -39.71, 16.43, 260.0),
        DeckStatic("us carrier tech", -41.54, 20.11, 189.0),
        DeckStatic("AS32-32A", -43.71, 19.81, 76.0),
        DeckStatic("us carrier tech", -45.31, 20.31, 305.0),
        DeckStatic("AS32-31A", -47.90, 20.08, 265.0),
        DeckStatic("AS32-p25", -53.85, 15.14, 260.0),
        DeckStatic("AS32-31A", -54.28, 20.87, 265.0),
        DeckStatic("AS32-31A", -60.12, 15.65, 265.0),
    ],
    # campaign A mission 2 street set
    [
        DeckStatic("us carrier tech", -43.17, 16.66, 217.3),
        DeckStatic("AS32-p25", -44.74, 18.78, 268.3),
        DeckStatic("us carrier tech", -52.24, 18.97, 298.3),
        DeckStatic("us carrier tech", -53.47, 17.77, 298.3),
        DeckStatic("AS32-p25", -54.00, 21.55, 268.3),
        DeckStatic("AS32-31A", -55.29, 14.95, 265.0),
        DeckStatic("us carrier tech", -57.33, 18.44, 298.3),
        DeckStatic("AS32-p25", -57.46, 21.77, 268.3),
    ],
    # campaign A mission 4 street set
    [
        DeckStatic("us carrier tech", -43.45, 22.70, 250.6),
        DeckStatic("us carrier tech", -45.35, 22.84, 302.6),
        DeckStatic("us carrier tech", -46.51, 21.72, 302.6),
        DeckStatic("us carrier tech", -47.45, 21.97, 257.6),
        DeckStatic("AS32-31A", -48.08, 23.37, 357.6),
    ],
    # campaign A mission 5 street set
    [
        DeckStatic("us carrier tech", -52.16, 18.61, 246.8),
        DeckStatic("us carrier tech", -53.28, 18.53, 269.8),
        DeckStatic("AS32-p25", -54.42, 20.27, 170.8),
        DeckStatic("us carrier tech", -57.35, 19.35, 272.8),
        DeckStatic("AS32-p25", -59.34, 21.34, 170.8),
        DeckStatic("us carrier tech", -61.72, 20.34, 266.8),
        DeckStatic("us carrier tech", -62.46, 20.90, 266.8),
    ],
]

# The shipped street sets: campaign A arrangements translated forward into the corral.
STREET_VARIANTS: list[list[DeckStatic]] = [
    [
        DeckStatic(
            it.type, it.x + CORRAL_SHIFT[0], it.y + CORRAL_SHIFT[1], it.angle_deg
        )
        for it in variant
    ]
    for variant in _CAMPAIGN_A_STREET_VARIANTS
]


def clears_known_spots(item: DeckStatic) -> bool:
    """Whether this placement keeps its required distance from every known spot."""
    return all(
        math.hypot(item.x - sx, item.y - sy) >= MIN_SPOT_CLEARANCE_M
        for sx, sy in KNOWN_PARKING_SPOTS
    )


def _pick(
    variants: list[list[DeckStatic]], seed_key: str, salt: str, turn: int
) -> list[DeckStatic]:
    return variants[(crc32(f"{seed_key}|{salt}".encode()) + turn) % len(variants)]


def deck_layout_for(hull_id: str, seed_key: str, turn: int) -> list[DeckStatic]:
    """The decoration set for one carrier this turn.

    Empty for non-Nimitz decks. The street variant rotates deterministically
    on (carrier, turn) so a re-generated turn always dresses the deck the
    same way, while consecutive turns vary.
    """
    if hull_id not in NIMITZ_DECK_HULLS:
        return []
    return LSO_PLATFORM_CREW + _pick(STREET_VARIANTS, seed_key, "street", turn)
