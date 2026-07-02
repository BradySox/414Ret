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

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "resources/campaigns/exercise_vegas_nerve.miz"
DST = REPO / "resources/campaigns/red_flag_81_2.miz"

BLUE_AIRPORTS = {4, 1}  # Nellis, Creech (Indian Springs)
RED_AIRPORTS = {2, 16, 17, 18, 5}  # Groom, Pahute Mesa, Tonopah, TTR, Beatty

# --- The laydown (design note section 3) -- edit these when the reference
# --- 81-2 miz arrives, then re-run.
SA2_SITES = [
    (-318000, -163000),  # Tolicha Peak west complex
    (-305000, -155000),  # Tolicha Peak north
    (-232000, -170000),  # TTR ring
    (-300000, -138000),  # Pahute Mesa
    (-292000, -95000),  # Groom box edge
]
SA3_SITES = [
    (-224000, -177000),  # TTR field
    (-315000, -158000),  # mock airfield complex
]
# No SHORAD markers: the 1981 Red Force faction has no SAM-SHORAD unit (guns
# were the point defense), so the FEBA/strip point defense is AAA too.
AAA_SITES = [
    (-321000, -149500),  # FOB Tolicha
    (-304500, -131500),  # Pahute strip
    (-334000, -125000),  # FEBA corridor
    (-322000, -168000),  # western (Beatty) corridor
    (-227500, -172500),  # TTR
    (-289500, -89000),  # Groom
    (-329000, -172000),  # Beatty
    (-199000, -198000),  # Tonopah civil
]
EWR_SITES = [
    (-205000, -195000),  # Tonopah (P-37 Bar Lock when HDS is on)
    (-265000, -75000),  # Groom / east approach
]
ARMOR_SITES = [
    (-255000, -150000),  # Kawich Valley array
    (-280000, -140000),  # Gold Flat array
    (-325000, -143000),  # FEBA north
    (-318000, -152000),  # FEBA west
    (-291000, -92000),  # Groom defense
]
FOBS = [
    ("Camp Mercury", "blue", (-352000, -103000)),
    ("FOB Tolicha", "red", (-322000, -148000)),
]
# (static type, owner, position). Factories are only read from the BLUE country
# block (loader quirk); objective coalition follows the nearest control point.
STATIC_TARGETS = [
    ("factory", "blue", (-316000, -157000)),  # mock airfield industry
    ("strike", "red", (-315500, -158500)),  # mock airfield complex
    ("strike", "red", (-225000, -176000)),  # TTR industrial
    ("ammo", "red", (-198500, -199500)),  # Tonopah depot
    ("ammo", "red", (-331500, -173500)),  # Beatty depot
    ("c2", "red", (-288000, -88500)),  # Red Force C2 inside the Box
]
BLUE_DEFENSE = [
    ("merad", (-359000, -72000)),  # Hawk at Creech
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
        vgroup(red, "SA3", AirDefence.X_5p73_s_125_ln, x, y)
    for x, y in AAA_SITES:
        vgroup(red, "AAA", AirDefence.ZSU_23_4_Shilka, x, y)
    for x, y in EWR_SITES:
        vgroup(red, "EWR", AirDefence.X_1L13_EWR, x, y)
    for x, y in ARMOR_SITES:
        vgroup(red, "ARMOR", Armor.M_1_Abrams, x, y)

    blue_defense_types = {"merad": AirDefence.Hawk_ln, "aaa": AirDefence.Vulcan}
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
