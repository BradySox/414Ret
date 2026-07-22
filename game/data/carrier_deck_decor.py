"""Curated carrier deck decoration layouts (§72).

Deck-dressing statics for the Nimitz-family carriers, extracted verbatim from
the OCN 2 (Operation Cerberus North 2) campaign missions -- Sedlo's deck
dressing language, replayed onto Retribution's carriers: LSO platform crew on
the port-aft sponson, a "street" of deck equipment (tow tractors, P-25
firefighting vehicle, Hyster forklift, crane, deck crew) alongside the island,
and an opt-in LAUNCH-PHASE set in the recovery corridor (the round-down E-2 +
the port junk-row gear) that the ``deckdecor`` plugin strikes below before
recovery traffic arrives.

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
- LAUNCH-PHASE (the opt-in aircraft tier, default OFF): may stand in the
  recovery corridor because the deckdecor plugin strikes them below before
  recovery (fallback timer / the Airboss window / fixed-wing traffic low
  astern). Must still clear every known spot (spawns run while they stand),
  and must always reach the plugin's clear list.

There is deliberately NO permanent static-aircraft class. The first cut
parked OCN's Seahawk pair + a fixed-wing accent on the starboard-aft spots
under the manual's "a blocked spot is skipped" claim -- and the first flown
mission FALSIFIED that for Retribution's dominant spawn path: LATE-ACTIVATED
groups (the §64 TOT-delay pattern) do NOT skip statics-obstructed spots (a
flown CVN-73 late-activated A-6E pair straight INTO the Seahawk statics,
2026-07-18). No static may stand on ANY spawn spot, so the parked-aircraft
look comes from Retribution's real deck population instead; those positions
are kept below as LEARNED spot anchors.

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
    "E-2C": ("Planes", None),  # static Hawkeye (renders FOLDED -- user-confirmed)
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
    (-134.3, 27.0),  # junkyard spot (~spot 7; OCN parks a Seahawk here)
    (-122.6, 28.2),  # junkyard spot (~spot 8; OCN parks a Seahawk here)
    (-98.7, 29.9),  # El-3 shoulder spot (OCN parks an S-3/E-2 here)
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

# Everything launch-phase must stand INSIDE the recovery-corridor keep-out box
# (LANDING_AREA_KEEP_OUT) -- that is the ONLY zone the deckdecor plugin clears
# before recovery, and by definition it is not a parking area. The flown
# CVN-71 (2026-07-21) proved why this must be the rule and not a looser
# "aft of x" one: the old port junk row sat at x -105..-114 / y -24..-28 --
# forward and port of the keep-out box, i.e. squarely in the port-quarter
# PARKING row -- and a Hornet spawned onto the port-quarter spot at (-108,-34)
# 8.7 m from its tractor. It was launch-phase in name only. Removed; the
# guard test now requires every launch-phase item to fall inside the box.

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

# --- Launch-phase dressing (aircraft tier; runtime-cleared) -----------------
#
# Statics that stand INSIDE the recovery corridor (LANDING_AREA_KEEP_OUT)
# during the launch cycle and are struck below by the deckdecor plugin before
# recovery. Only the round-down E-2 qualifies: it stands on the aft round-down,
# in the corridor (not a parking area), and no aircraft has ever spawned near
# it across the flown missions. The OCN "port junk row" was tried here and
# REMOVED (flown CVN-71, 2026-07-21): it sat forward/port of the corridor box,
# in the port-quarter parking row, and clipped a spawning Hornet.
ROUND_DOWN_VARIANTS: list[list[DeckStatic]] = [
    [DeckStatic("E-2C", -152.14, 5.37, 350.0)],  # OCN 2 mission 8
    [DeckStatic("E-2C", -138.04, 5.12, 352.1)],  # OCN 2 mission 1
]


def _pick(
    variants: list[list[DeckStatic]], seed_key: str, salt: str, turn: int
) -> list[DeckStatic]:
    return variants[(crc32(f"{seed_key}|{salt}".encode()) + turn) % len(variants)]


def deck_layout_for(hull_id: str, seed_key: str, turn: int) -> list[DeckStatic]:
    """The PERMANENT decoration set for one carrier this turn.

    Empty for non-Nimitz decks. The street variant rotates deterministically
    on (carrier, turn) so a re-generated turn always dresses the deck the
    same way, while consecutive turns vary. Deliberately gear-only: permanent
    static aircraft were removed after the flown late-activation spawn-clip
    (see the module docstring).
    """
    if hull_id not in NIMITZ_DECK_HULLS:
        return []
    return LSO_PLATFORM_CREW + _pick(STREET_VARIANTS, seed_key, "street", turn)


def launch_phase_dressing_for(
    hull_id: str, seed_key: str, turn: int, include_aircraft: bool
) -> list[DeckStatic]:
    """The launch-phase (runtime-cleared) set for one carrier this turn."""
    if not include_aircraft or hull_id not in NIMITZ_DECK_HULLS:
        return []
    return _pick(ROUND_DOWN_VARIANTS, seed_key, "rounddown", turn)
