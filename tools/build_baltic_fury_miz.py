"""Build resources/campaigns/operation_baltic_fury.miz from red_tide.miz.

Reshapes the all-vanilla Red Tide GermanyCW miz into the Operation Baltic Fury
laydown (docs/dev/design/414th-baltic-fury-campaign-notes.md):

- Airport ownership flipped to the Baltic-approaches geometry: BLUE holds the
  German Bight corner (Nordholz, Bremen, Hamburg), RED holds the NE arc up to
  Copenhagen (Kastrup, Laage/Rostock, Peenemünde, Parchim, Wismar,
  Szczecin-Goleniów, Bornholm + the coastal-spine objectives Lübeck & Barth).
- A US CVN steams in the German Bight (blue ship group -> carrier control point,
  named to match the campaign yaml's carrier air-wing key + the §65 comms card).
- The signature IADS belt: coastal anti-ship wall (Bastion/Bal), strategic S-400
  regiments (single-radar battalions + shared EWR), a forward MERAD screen, point
  defense per base, an EWR net, the Baltic Fleet SAG, per-base advanced-IADS C2
  cells, blue/red economy, and a coastal SS-26 (§49 SCUD hunt).

Band-marker convention (game/campaignloader/mizcampaignloader.py): placed SAM/
EWR/ship/coastal/missile groups are BAND MARKERS read by position + unit class;
the FACTION supplies the real mod (CH/HDS) units at generation. Every marker here
is a VANILLA DCS unit (the exact marker types the loader keys on), so the miz
round-trips through pydcs losslessly (mod units would corrupt the save).

The laydown tables below are the single source of truth -- edit them and re-run;
a hand edit to the .miz is lost on the next build.

Usage: python tools/build_baltic_fury_miz.py
"""

import sys
from pathlib import Path

import dcs.statics as statics
from dcs import ships
from dcs.mapping import Point
from dcs.mission import Mission
from dcs.vehicles import AirDefence, MissilesSS

# pydcs class-name drift between the release package (X_1L13_EWR) and the
# retribution fork (x_1L13_EWR); accept either so the builder runs in both.
EWR_MARKER = getattr(AirDefence, "x_1L13_EWR", None) or getattr(
    AirDefence, "X_1L13_EWR", None
)

# --- Band-marker unit types (must match MizCampaignLoader's *_UNIT_TYPE(S)) ---
LORAD = AirDefence.S_300PS_5P85C_ln  # -> faction S-400 (SA-21) at generation
MERAD = AirDefence.S_75M_Volhov  # -> faction SA-11 / SA-17 / BUK-M3
SHORAD = AirDefence.Strela_1_9P31  # -> faction SA-15 Tor / Pantsir
AAA = AirDefence.Vulcan  # blue base point defense
COASTAL = MissilesSS.hy_launcher  # -> faction Bastion-P / Bal LBASM
MISSILE = MissilesSS.Scud_B  # §49 coastal SS-26 (category "missile")
CARRIER_HULL = ships.Stennis  # blue carrier -> Carrier control point
FLEET_HULL = ships.USS_Arleigh_Burke_IIa  # naval-target marker -> faction navy

CC = statics.Fortification._Command_Center
COMMS = statics.Fortification.Comms_tower_M
POWER = statics.Fortification.GeneratorF
FACTORY = statics.Fortification.Workshop_A
AMMO = statics.Warehouse._Ammunition_depot

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "resources/campaigns/red_tide.miz"
DST = REPO / "resources/campaigns/operation_baltic_fury.miz"

# --- Control-point ownership (turn-1) ---------------------------------------
BLUE_AIRPORTS = {47, 5, 17}  # Nordholz, Bremen, Hamburg
RED_AIRPORTS = {
    41,  # Kastrup / Copenhagen  (the prize)
    20,  # Laage / Rostock
    25,  # Peenemünde
    84,  # Parchim
    108,  # Wismar
    50,  # Szczecin-Goleniów
    33,  # Bornholm
    81,  # Lübeck  (first coastal-spine objective; front sits Hamburg->here)
    3,  # Barth   (coastal-spine objective)
}
# Everything else -> neutral (captured as the front sweeps up the coast).

CARRIER = ("CVN-75 Harry S. Truman", (127353, -868754))  # 55.0N 6.8E, blue

# --- SAM / IADS belt (vanilla band markers) ---------------------------------
# Strategic S-400 regiments: single-radar battalions + a shared EWR per hub
# (regiment-by-authoring; §60 doubling stays off for these). LORAD band.
S400_REGIMENTS = [
    (127222, -500129),
    (121000, -503000),
    (132000, -496000),  # Copenhagen
    (-46917, -547933),
    (-52000, -543000),
    (-42000, -552000),  # Rostock
    (-104437, -377931),
    (-99000, -381000),
    (-109000, -373000),  # Szczecin
]
# Mid S-300 (SA-20) nodes on the coast / eastern shoulder. LORAD band.
S300_NODES = [
    (-40000, -440000),  # Peenemünde defensive ring
    (-90000, -470000),  # Neubrandenburg deep-rear node
]
# Forward MERAD screen across the Lübeck–Wismar–Rostock neck. MERAD band.
MERAD_SCREEN = [
    (-52000, -628000),  # Lübeck approach (binds to red Lübeck, not neutral H FRG 12)
    (-45742, -587524),  # Wismar
    (-38000, -560000),  # Rostock forward
    (-20000, -520000),  # Barth / Stralsund approach
]
# Point defense, one per red base (faction supplies SA-15 Tor / Pantsir). SHORAD.
POINT_DEFENSE = [
    (131000, -486000),  # Kastrup
    (-49000, -534000),  # Laage
    (-33000, -433000),  # Peenemünde
    (-99000, -573000),  # Parchim
    (-43000, -585000),  # Wismar
    (-104000, -365000),  # Szczecin
    (60000, -360000),  # Bornholm
    (-48000, -638000),  # Lübeck
    (-6000, -500000),  # Barth
]
# EWR net (vanilla 1L13 marker; faction supplies Nebo-U / Nebo-SVU).
EWR_SITES = [
    (25000, -453000),  # Kap Arkona / Rügen (coastal early-warning eye)
    (-44000, -545000),  # Rostock
    (129000, -493000),  # Copenhagen
    (-106000, -370000),  # Szczecin
    (58000, -364000),  # Bornholm
]
# Coastal anti-ship wall (Bastion-P / Bal LBASM), sea-facing. COASTAL marker.
COASTAL_ANTISHIP = [
    (-21425, -544701),  # Rostock coast
    (23897, -452187),  # Kap Arkona / Rügen
    (-49529, -425779),  # Usedom / Peenemünde
    (1512, -502398),  # Darß / Barth
    (131614, -490031),  # Copenhagen / Øresund
]
# §49 coastal SS-26 Iskander (shoot-and-scoot). category "missile".
ISKANDER = [(-70726, -537596)]  # red rear near Rostock

# --- Naval: the Baltic Fleet SAG (red ship group; 3-hull marker) ------------
FLEET_SAG = (19397, -441610)  # 54.65N 13.60E, between Rügen and Bornholm

# --- Advanced-IADS C2 cells (Command Center + Comms + Generator per red hub) -
C2_HUBS = [
    (127222, -500129),  # Copenhagen
    (-46917, -547933),  # Rostock
    (-104437, -377931),  # Szczecin
    (-40000, -440000),  # Peenemünde
]

# --- Economy (§53): (kind, x, y) --------------------------------------------
BLUE_ECONOMY = [
    ("factory", -114116, -781460),  # Bremen
    ("ammo", -63016, -691931),  # Hamburg
]
RED_ECONOMY = [
    ("factory", -51929, -536642),  # Rostock
    ("ammo", -36297, -436060),  # Peenemünde
    ("factory", 133729, -489625),  # Copenhagen
    ("ammo", -107006, -368018),  # Szczecin
]

# --- Blue base air defense (AAA-only by loader rule; faction buys Patriot) ---
BLUE_DEFENSE = [
    (-33001, -776115),  # Nordholz
    (-114116, -781460),  # Bremen
]


def main() -> None:
    # ⚠️  The campaign miz is HAND-AUTHORED now -- the DM built out the laydown in the DCS
    # Mission Editor (2026-07-20). This generator was a ONE-TIME bootstrap; re-running it would
    # OVERWRITE those edits (the "generated .miz -- never hand-edit" gotcha). Refuse unless the
    # DM explicitly passes --force to rebuild the laydown from scratch (losing all ME edits).
    if DST.exists() and "--force" not in sys.argv:
        raise SystemExit(
            f"REFUSING to overwrite {DST.name}: it is now HAND-AUTHORED (edited in the ME).\n"
            f"Re-running would wipe the DM's laydown. Delete the miz or pass --force ONLY if you\n"
            f"truly want to regenerate from the tables below and discard every Mission Editor edit."
        )

    m = Mission()
    m.load_file(str(SRC))
    terrain = m.terrain

    # 1) Airport ownership -> the Baltic-approaches geometry.
    for ap in terrain.airport_list():
        if ap.id in BLUE_AIRPORTS:
            ap.set_blue()
        elif ap.id in RED_AIRPORTS:
            ap.set_red()
        else:
            ap.set_neutral()
        ap.unlimited_aircrafts = False

    blue = m.country("Combined Joint Task Forces Blue")
    red = m.country("Combined Joint Task Forces Red")

    # 2) Clear Red Tide's laydown for a clean slate (we own the whole theater).
    for c in (blue, red):
        c.vehicle_group.clear()
        c.static_group.clear()
        c.ship_group.clear()
        c.plane_group.clear()
        c.helicopter_group.clear()
    # Trigger zones carry Red Tide's scenery-strike + CP-influence zones (named
    # after its CPs, e.g. "Haina"); drop them so the loader's preset-location
    # pass doesn't look up control points this laydown no longer owns.
    m.triggers._zones.clear()

    counter = 0

    def vg(country, prefix, vtype, x, y):
        nonlocal counter
        counter += 1
        return m.vehicle_group(
            country, f"{prefix}-{counter}", vtype, Point(x, y, terrain)
        )

    def sg(country, prefix, stype, x, y):
        nonlocal counter
        counter += 1
        return m.static_group(
            country, f"{prefix}-{counter}", stype, Point(x, y, terrain)
        )

    # 3) SAM / IADS belt (all in the RED block: nearest-CP binding).
    for x, y in S400_REGIMENTS:
        vg(red, "S400", LORAD, x, y)
    for x, y in S300_NODES:
        vg(red, "S300", LORAD, x, y)
    for x, y in MERAD_SCREEN:
        vg(red, "MERAD", MERAD, x, y)
    for x, y in POINT_DEFENSE:
        vg(red, "SHORAD", SHORAD, x, y)
    for x, y in EWR_SITES:
        vg(red, "EWR", EWR_MARKER, x, y)
    for x, y in COASTAL_ANTISHIP:
        vg(red, "COASTAL", COASTAL, x, y)
    for x, y in ISKANDER:
        vg(red, "SS26", MISSILE, x, y)

    # 4) Blue base air defense (AAA marker; faction buys Patriot/NASAMS).
    for x, y in BLUE_DEFENSE:
        vg(blue, "AAA", AAA, x, y)

    # 5) Advanced-IADS C2 cells: Command Center + Comms + Generator per hub,
    #    co-located so range mode wires each base's SAMs to them.
    for x, y in C2_HUBS:
        sg(red, "CC", CC, x, y)
        sg(red, "COMMS", COMMS, x + 400, y + 200)
        sg(red, "POWER", POWER, x - 300, y + 350)

    # 6) Economy (§53).
    econ = {"factory": FACTORY, "ammo": AMMO}
    for kind, x, y in BLUE_ECONOMY:
        sg(blue, kind.upper(), econ[kind], x, y)
    for kind, x, y in RED_ECONOMY:
        sg(red, kind.upper(), econ[kind], x, y)

    # 7) Carrier (blue Stennis -> Carrier CP; NOT late-activated).
    name, (cx, cy) = CARRIER
    m.ship_group(blue, name, CARRIER_HULL, Point(cx, cy, terrain))

    # 8) Baltic Fleet SAG (red ship marker(s) -> faction navy at generation;
    #    3 single-hull groups, the Red Tide naval-marker pattern).
    fx, fy = FLEET_SAG
    for i, off in enumerate((0, 2500, 5000)):
        m.ship_group(
            red,
            f"Baltic Fleet SAG-{i + 1}",
            FLEET_HULL,
            Point(fx + off, fy + off, terrain),
        )

    m.save(str(DST))
    print(f"saved {DST}")


if __name__ == "__main__":
    main()
