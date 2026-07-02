"""Build resources/campaigns/red_flag_81_2.miz from exercise_vegas_nerve.miz.

Reshapes the Vegas Nerve NTTR miz into the Red Flag 81-2 laydown per
docs/dev/design/414th-red-flag-81-campaign-notes.md section 3:

- Airport ownership flipped to the classic Red Flag geometry: Blue at Nellis +
  Creech (Indian Springs), Red holding the north-west ranges (Tonopah Test
  Range, Groom Lake, Pahute Mesa, Beatty, Tonopah), everything else neutral.
- Every old objective marker dropped; the 81-2 threat-array first cut added
  (marker unit types follow game/campaignloader/mizcampaignloader.py).
- One off-map spawn kept, renamed "Strategic Air Command" and moved SE of
  Nellis (the SAC Arc Light / tanker cells).

The laydown tables below are the single place to edit when re-pointing the
first cut at the real 81-2 reference miz. Re-run with any pydcs new enough to
round-trip the miz (the release pydcs works; the retribution fork is not
required for authoring — the campaign loader reads the result with its own).

Usage: python tools/build_red_flag_81_2_miz.py
"""

from pathlib import Path

import dcs.statics as statics
from dcs.mapping import Point
from dcs.mission import Mission
from dcs.vehicles import AirDefence, Armor, Unarmed

# pydcs class naming differs between the release package (X_5p73_s_125_ln,
# X_1L13_EWR) and the retribution fork (lowercase x_...); accept either so the
# builder runs in both environments.
S125_MARKER = getattr(AirDefence, "X_5p73_s_125_ln", None) or getattr(
    AirDefence, "x_5p73_s_125_ln"
)
EWR_MARKER = getattr(AirDefence, "X_1L13_EWR", None) or getattr(
    AirDefence, "x_1L13_EWR"
)

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "resources/campaigns/exercise_vegas_nerve.miz"
DST = REPO / "resources/campaigns/red_flag_81_2.miz"

BLUE_AIRPORTS = {4, 1}  # Nellis, Creech (Indian Springs)
RED_AIRPORTS = {2, 16, 17, 18, 5}  # Groom, Pahute Mesa, Tonopah, TTR, Beatty

# --- The laydown (design note section 3), re-pointed 2026-07-02 at the
# --- Reflected Simulations "F-4E Red Flag 81-2" reference miz set: positions
# --- below are cross-mission cluster centers extracted from the 15 campaign
# --- missions (raw-Lua parse; see the design note for the method + census).
SA2_SITES = [
    (-270620, -182300),  # Tolicha Peak complex -- the ref's one full S-75 site
]
SA3_SITES = [
    (-248510, -189000),  # NW airfield/EWR complex (SW of TTR)
]
# MERAD to the loader like the SA-2/SA-3 markers (Hawk marker type keeps them
# distinct in the ME); the faction's "SA-6" preset gives the fill variety. The
# reference fields four Kub sites -- the aggressor MUTES Straight Flush play.
SA6_SITES = [
    (-264410, -159010),  # main mock airfield south
    (-274480, -179250),  # Tolicha Peak south
    (-219490, -164060),  # TTR south-east approach (full 11-unit ref site)
]
# SHORAD (Strela marker -> faction SA-8 Osa): the two real ref SA-8 positions
# plus two stand-ins for the ref's dense eastern "Smokey" GTR-18 manpad belt
# (100 SA-18 sims in the reference; the squadron's no-manpads call stands, so
# the belt reads as point SAMs instead).
SHORAD_SITES = [
    (-263000, -149800),  # central band (ref SA-8; offset off the EWR it guards)
    (-261040, -161380),  # main mock airfield west (ref SA-8)
    (-253930, -123080),  # Smoky belt west
    (-242390, -115590),  # Smoky belt east
]
AAA_SITES = [
    # Range-array gun belts (reference positions; KS-19/SON-9 heavy flak +
    # ZSU fills come from the faction).
    (-268650, -180950),  # Tolicha KS-19 north belt
    (-270900, -184600),  # Tolicha south / POL-farm guns
    (-268590, -164010),  # main mock airfield guns
    (-249420, -185720),  # NW complex guns
    (-241270, -188920),  # NW satellite (ref "EWR-1") guns
    (-269600, -126100),  # east mock airfield (ref "AirfieldZEUS")
    (-264400, -153480),  # central band column guard
    (-259520, -140510),  # Fire Can site
    (-282500, -171400),  # refueler camp west
    (-285700, -149700),  # fuel-camp guard west (ref "FuelAAA-1")
    (-284650, -141700),  # fuel-camp guard east (ref "FuelAAA")
    # Campaign-fabric point defense (kept from the first cut: red fields, the
    # FEBA, and the front corridor feed the flak gauntlet).
    (-321000, -149500),  # FOB Tolicha
    (-304500, -131500),  # Pahute strip
    (-334000, -125000),  # FEBA corridor
    (-227500, -172500),  # TTR
    (-289500, -89000),  # Groom
    (-329000, -172000),  # Beatty
    (-199000, -198000),  # Tonopah civil
]
EWR_SITES = [
    (-296700, -169930),  # deep south-west (Beatty corridor; ref "EWR-5")
    (-263360, -151050),  # central band -- the GCI heart
    (-249070, -187460),  # NW airfield complex (ref "EWR-1")
]
ARMOR_SITES = [
    (-271490, -182790),  # Tolicha T-55 array
    (-249000, -186600),  # NW complex T-55 array
    (-266840, -126420),  # east mock airfield armor (ref "Ground-1")
    (-252210, -118490),  # Smoky belt armor (ref "PepsiTarget")
    (-247670, -121600),  # Smoky belt array (ref "RocketTarget", 24 units)
]
FOBS = [
    ("Camp Mercury", "blue", (-352000, -103000)),
    ("FOB Tolicha", "red", (-322000, -148000)),
]
# (static type, owner, position). Factories are only read from the BLUE country
# block (loader quirk); objective coalition follows the nearest control point.
# The four "strike" range complexes are the reference's F-86F-dressed mock
# airfields; the Tolicha ammo pair is its train marshalling yard + POL farm.
STATIC_TARGETS = [
    ("factory", "blue", (-267000, -161900)),  # main mock airfield industry
    ("strike", "red", (-267800, -162510)),  # main mock airfield (24-Sabre ramp)
    ("strike", "red", (-275000, -178690)),  # Tolicha mock airfield
    ("strike", "red", (-249520, -185780)),  # NW airfield complex
    ("strike", "red", (-269380, -125890)),  # east mock airfield
    ("ammo", "red", (-269000, -182100)),  # Tolicha marshalling yard (train)
    ("ammo", "red", (-270770, -185280)),  # Tolicha POL farm (32-tank ref site)
    ("ammo", "red", (-248730, -186710)),  # NW truck park (51 trucks in ref)
    ("strike", "red", (-225000, -176000)),  # TTR industrial (campaign economy)
    ("ammo", "red", (-198500, -199500)),  # Tonopah depot (campaign economy)
    ("ammo", "red", (-331500, -173500)),  # Beatty depot (campaign economy)
    ("c2", "red", (-288000, -88500)),  # Red Force C2 inside the Box
]
# Blue point defense is AAA-only by loader rule: MizCampaignLoader reads
# MERAD/SHORAD markers from the RED country block only (its aaa property is
# the one that scans both), so a blue Hawk marker is silently dropped -- the
# first cut's "Hawk at Creech" never actually loaded. The player faction
# carries the Hawk preset for purchase instead.
BLUE_DEFENSE = [
    ("aaa", (-359000, -72000)),  # Vulcan at Creech
    ("aaa", (-396500, -15500)),  # Vulcan at Nellis
]
CONVOY_SPAWNS = [
    (-397000, -18500),  # Nellis
    (-361500, -76500),  # Creech
    (-352800, -104000),  # Camp Mercury
    (-322800, -149000),  # FOB Tolicha
    (-304300, -133800),  # Pahute Mesa
    (-331300, -175800),  # Beatty
    (-227300, -175500),  # TTR
    (-198000, -202000),  # Tonopah
    (-289400, -87700),  # Groom Lake
]
SAC_SPAWN = (-470000, 40000)  # off-map spawn, SE of Nellis (blue rear)


def main() -> None:
    m = Mission()
    m.load_file(str(SRC))
    terrain = m.terrain

    for ap in terrain.airport_list():
        if ap.id in BLUE_AIRPORTS:
            ap.set_blue()
            ap.unlimited_aircrafts = False
        elif ap.id in RED_AIRPORTS:
            ap.set_red()
            # captured_invert: red fields flip to the player on an inverted start.
            ap.unlimited_aircrafts = True
        else:
            ap.set_neutral()
            ap.unlimited_aircrafts = False

    blue = m.country("Combined Joint Task Forces Blue")
    red = m.country("Combined Joint Task Forces Red")
    sides = {"blue": blue, "red": red}

    # Clear the old laydown. Red statics stay (the TTR Invisible-FARP helipad
    # cluster -- red helo ground spawns); Vegas Nerve has no blue statics.
    blue.vehicle_group.clear()
    red.vehicle_group.clear()

    # Off-map spawns: keep one, rename + move; drop the other.
    keep = None
    for g in list(blue.plane_group):
        if str(g.name) == "Bombers from Minot AFB":
            keep = g
        else:
            blue.plane_group.remove(g)
    assert keep is not None, "expected the Minot off-map spawn group"
    keep.name = "Strategic Air Command"
    sac_pos = Point(*SAC_SPAWN, terrain)
    for u in keep.units:
        u.position = sac_pos
    for p in keep.points:
        p.position = sac_pos

    counter = 0

    def vgroup(country, prefix, vtype, x, y, waypoint=None):
        nonlocal counter
        counter += 1
        group = m.vehicle_group(
            country, f"{prefix}-{counter}", vtype, Point(x, y, terrain)
        )
        if waypoint is not None:
            group.add_waypoint(Point(waypoint[0], waypoint[1], terrain))
        return group

    def sgroup(country, prefix, stype, x, y):
        nonlocal counter
        counter += 1
        return m.static_group(
            country, f"{prefix}-{counter}", stype, Point(x, y, terrain)
        )

    for x, y in SA2_SITES:
        vgroup(red, "SA2", AirDefence.S_75M_Volhov, x, y)
    for x, y in SA3_SITES:
        vgroup(red, "SA3", S125_MARKER, x, y)
    for x, y in SA6_SITES:
        vgroup(red, "SA6", AirDefence.Hawk_ln, x, y)
    for x, y in SHORAD_SITES:
        vgroup(red, "SHORAD", AirDefence.Strela_1_9P31, x, y)
    for x, y in AAA_SITES:
        vgroup(red, "AAA", AirDefence.ZSU_23_4_Shilka, x, y)
    for x, y in EWR_SITES:
        vgroup(red, "EWR", EWR_MARKER, x, y)
    for x, y in ARMOR_SITES:
        vgroup(red, "ARMOR", Armor.M_1_Abrams, x, y)

    blue_defense_types = {"aaa": AirDefence.Vulcan}
    for kind, (x, y) in BLUE_DEFENSE:
        vgroup(blue, kind.upper(), blue_defense_types[kind], x, y)

    for name, side, (x, y) in FOBS:
        m.vehicle_group(sides[side], name, Unarmed.SKP_11, Point(x, y, terrain))

    static_types = {
        "factory": statics.Fortification.Workshop_A,
        "strike": statics.Fortification.Tech_combine,
        "ammo": statics.Warehouse._Ammunition_depot,
        "c2": statics.Fortification._Command_Center,
    }
    for kind, side, (x, y) in STATIC_TARGETS:
        sgroup(sides[side], kind.upper(), static_types[kind], x, y)

    # Convoy spawn hints all live in the BLUE country block (the loader's
    # cp_convoy_spawns only scans blue), one per active control point.
    for x, y in CONVOY_SPAWNS:
        vgroup(
            blue,
            "CPSPAWN",
            Armor.M1043_HMMWV_Armament,
            x,
            y,
            waypoint=(x + 500, y + 500),
        )

    m.save(str(DST))
    print(f"saved {DST}")


if __name__ == "__main__":
    main()
