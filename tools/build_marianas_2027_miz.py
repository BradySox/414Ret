"""Build ``resources/campaigns/marianas_2027.miz`` from Fuzzle's Pacific Repartee miz.

"Marianas - Second Island Chain (2027)" forks the laydown of
``pacific_repartee.miz`` rather than re-authoring the Marianas from scratch: that
miz already carries a furnished 15-CP island chain (four FOBs, three PLAN carrier
groups, two LHAs, the SAM/EWR/armor/strike markers and the Guam supply road), and
its every unit is vanilla, so pydcs round-trips it losslessly.

Five edits are applied, all of which the source miz cannot express by itself:

1.  **Guam goes blue.**  Repartee's premise is a lone carrier task group retaking a
    Guam that China already holds, which caps the campaign at three blue CPs and no
    runway.  The real Second Island Chain fight is the opposite: Guam is US soil and
    the hard part is holding it and rolling *north*.  Andersen AFB (194 parking
    slots -- the only field on the map that can base a heavy wing), Antonio B. Won
    Pat Intl and Olf Orote flip to BLUE.

2.  **Two dormant airfields are activated.**  ``Airport.is_neutral()`` returns False
    for a NEUTRAL coalition, so ``MizCampaignLoader.control_points`` (which gates on
    ``is_blue() or is_red() or is_neutral()``) silently drops such a field entirely.
    Rota Intl and Pagan Airstrip sat NEUTRAL in Repartee and therefore never became
    control points at all; both are declared RED here, putting a red strike field
    (Rota) 90 km off Guam and extending the chain north.  North West Field is left
    NEUTRAL deliberately -- pydcs reports it with **zero runways**, so it can host no
    fixed wing.

3.  **Red gets theatre missile sites.**  Repartee places no ``missile``-category
    marker anywhere, so the China factions' DF-21D / CJ-10 / YJ-12B launchers are
    never fielded and the §49 shoot-and-scoot relocation has nothing to hunt.  A
    ``MissilesSS.Scud_B`` marker in the red block is what the loader reads as a
    missile site; one goes on each of Rota, Tinian and Saipan (see MISSILE_SITES
    for why none are authored further north).

4.  **Rota gets a long-range SAM battery.**  It was NEUTRAL and therefore carries no
    authored garrison of any kind, which would leave the newly-red field nearest Guam
    naked.  The band matters -- see ``LONG_SAM_SITES``.

5.  **The naval laydown is re-seated.**  Repartee sailed the blue carrier group in
    from the far NORTH (its premise is a lone CSG fighting south to retake a Chinese
    Guam).  Inverting the premise without moving the fleet left blue holding both ends
    of the chain with red sandwiched between them, and parked red's three carrier
    groups 220-500 km behind the very islands the player has to retake.  Blue's CSG and
    LHA now operate south-west of Guam, FOB Uracus (a blue island 780 km behind red
    lines) reverts to red, and red's carriers, amphibious groups and escort screen are
    pulled south into the Guam-Saipan corridor where they can actually contest it.

Every added marker position is validated against the real landmap
(``ConflictTheater.is_on_land``) so nothing is authored into the sea, and every naval
position is checked to be OFF land for the same reason.

Run from the repo root::

    python tools/build_marianas_2027_miz.py

The tool is the source of truth for the *edits*; the laydown it inherits belongs to
``pacific_repartee.miz``.  Never hand-edit ``marianas_2027.miz`` -- re-run this.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from dcs.mission import Mission  # noqa: E402
from dcs.point import PointAction  # noqa: E402
from dcs.terrain.terrain import Airport  # noqa: E402
from dcs.unittype import VehicleType  # noqa: E402
from dcs.vehicles import AirDefence, MissilesSS  # noqa: E402

from game.campaignloader.mizcampaignloader import MizCampaignLoader  # noqa: E402

SOURCE = _REPO_ROOT / "resources/campaigns/pacific_repartee.miz"
DEST = _REPO_ROOT / "resources/campaigns/marianas_2027.miz"

# Guam is American soil and stays that way; the war is fought northward up the
# chain. North West Field is deliberately absent (0 runways -- see module docstring).
BLUE_AIRFIELDS = (
    "Andersen AFB",
    "Antonio B. Won Pat Intl",
    "Olf Orote",
)
RED_AIRFIELDS = (
    "Rota Intl",
    "Tinian Intl",
    "Saipan Intl",
    "Pagan Airstrip",
)

# Theatre-missile sites, one per occupied island in the southern (contested) half of
# the chain. The anchor is the island's airfield; the real position is searched
# outward from it so the launchers sit on land and clear of the runway.
#
# Only Guam, Rota, Tinian and Saipan exist in the Marianas landmap -- Anatahan,
# Pagan, Agrihan and Uracus are all `is_in_sea` as far as the engine is concerned
# (a pre-existing property of the terrain data, inherited from Repartee, whose four
# FOBs sit on those islands). So no missile site is authored north of Saipan; that
# also happens to be the right threat picture, since a launcher 500 km up the chain
# reaches nothing that matters while Rota/Tinian/Saipan range Guam and the CSG.
MISSILE_SITES: tuple[tuple[str, str], ...] = (
    ("Rota PLARF Site", "Rota Intl"),
    ("Tinian PLARF Site", "Tinian Intl"),
    ("Saipan PLARF Site", "Saipan Intl"),
)

# Rota was NEUTRAL in Repartee, so it carries no authored garrison at all -- which
# would leave the red strike field nearest Guam (and its PLARF site) undefended.
#
# The band is SHORT, and that is load-bearing. Rota is only **75 km from Andersen**, so
# any long-range battery sited here puts Guam inside a SAM envelope on turn 1 -- an
# HQ-22 (170 km) covers the airfield with 95 km to spare. Rota gets point defence; the
# long-range belt starts at Tinian, 175 km out. (The campaign pins this marker to HQ-7,
# and `get_unit_group_for_task` only honours an override whose task matches the marker
# band, so the band and the pin have to agree -- see the ground_forces block.)
SHORT_SAM_SITES: tuple[tuple[str, str], ...] = (("Rota SAM Site", "Rota Intl"),)

# ---------------------------------------------------------------------------
# Naval laydown, in metres (x = north, y = east; Guam sits at the origin).
#
# The islands run NNE from Guam: Rota (76, 49), Tinian (167, 90), Saipan (180, 102),
# then the far-north FOBs at 317 / 512 / 585 / 781. The fight is the 0-205 km corridor,
# so that is where the fleets belong.
# ---------------------------------------------------------------------------

# Blue's carrier and amphibious groups, south-west of Guam -- close enough to cover the
# island and to strike up the chain, far enough to keep the boat out of the first salvo.
BLUE_NAVAL: dict[str, tuple[int, int]] = {
    "Naval-1": (-53_583, -111_230),  # CVN-74 John C. Stennis
    "Naval-2": (-102_353, -70_160),  # LHA-1 Tarawa
}

# Three escort markers held close to Guam. A ship marker binds to the nearest control
# point and prefers a blue one, so these become the carrier group's screen rather than
# red hulls (Naval-17 is left where Repartee had it).
BLUE_ESCORTS: dict[str, tuple[int, int]] = {
    "Naval-18": (20_000, -86_417),
    "Naval-27": (-91_230, 13_690),
}

# The PLAN covering force: two groups east and north-east of Saipan and one to the west,
# all ~290-340 km off Guam -- inside J-15/H-6J reach of the island, and reachable by
# blue's B-1B and carrier air. Amphibious groups sit on the lodgements they landed.
RED_NAVAL: dict[str, tuple[int, int]] = {
    # Pushed back out. The first flown mission had the PLAN groups ~300 km off Guam,
    # which with 250 km air-defence hulls and 540 km anti-ship missiles meant both fleets
    # were mutually engaged at t=0. Every group now sits BEYOND 250 km of Andersen, so no
    # red ring reaches the airfield and the exchange has to be closed to, not inherited.
    "Naval-3": (420_000, 60_000),  # carrier, north-west
    "Naval-4": (360_000, 260_000),  # carrier, north-east
    "Naval-28": (300_000, 400_000),  # carrier, the far eastern group
    "OPLHA": (240_000, 150_000),  # amphibious group, 266 km out
    "OPLHA-1": (280_000, 40_000),  # amphibious group, 270 km out
}

# The red screen. SIX groups, not eighteen.
#
# A flown mission produced 374 weapon launches in the opening five minutes because every
# ship fires autonomously the moment a target is in range (`set_ship_engagement` spawns
# them WeaponFree + alarm RED) and modern AShM out-range the whole theatre. The volume
# driver was hull count: eighteen escort markers plus the carrier and amphibious groups
# put **93 red hulls in 23 groups** at sea against blue's 15. A real fleet does not empty
# its magazines in the first minute of a war, and a 20-turn campaign cannot sustain it.
#
# Six screens, spread down the chain, cut red to roughly a third of the hulls while still
# giving every occupied island and each carrier group a covering escort.
RED_ESCORTS: dict[str, tuple[int, int]] = {
    # Eight screens spread across the whole red half rather than bunched in the corridor.
    # These are frigate groups (~45 km), so they shape where the fight is without putting
    # an envelope over anything; two stay forward with the occupied islands and the rest
    # cover the approaches to the carrier and amphibious groups.
    "Naval-16": (120_000, 40_000),  # forward, off Rota/Tinian
    "Naval-13": (215_000, 115_000),  # forward, off Saipan
    "Naval-12": (300_000, 210_000),
    "Naval-9": (255_000, 320_000),
    "Naval-10": (390_000, 120_000),
    "Naval-24": (330_000, 330_000),
    "Naval-8": (455_000, 200_000),
    "Naval-19": (460_000, 30_000),
}

# A blue FOB 780 km behind red lines is what made the map read as a sandwich; the
# northern chain is red depth, not a blue toehold.
FOBS_TO_RED = ("FOB Uracus",)

# Ship markers deleted outright from the source miz. Repartee authored 21 of them; each
# one becomes a full naval group, and hull count is what drove the 374-launch opening
# salvo. Only the six in RED_ESCORTS plus the three blue-screen markers survive.
CULLED_SHIP_MARKERS = (
    "Naval-5",
    "Naval-7",
    "Naval-11",
    "Naval-14",
    "Naval-15",
    "Naval-20",
    "Naval-21",
    "Naval-22",
    "Naval-23",
    "Naval-26",
)

# Search parameters for _place_on_land, in metres. The minimum keeps a launcher off
# the airfield it anchors to; the maximum keeps it on the same small island.
MIN_OFFSET_M = 1_500
MAX_OFFSET_M = 6_000
STEP_M = 250
BEARING_STEP_DEG = 15
# Two authored sites on the same island must not stack on top of each other.
MIN_SEPARATION_M = 1_200


def _all_groups(mission: Mission) -> dict[str, object]:
    """Every ship/vehicle group in the mission, keyed by name."""
    found: dict[str, object] = {}
    for coalition in mission.coalition.values():
        for country in coalition.countries.values():
            for attr in ("ship_group", "vehicle_group"):
                for group in getattr(country, attr):
                    found[group.name] = group
    return found


def _move_group(group: object, x: int, y: int) -> float:
    """Translate a group -- units and route points alike -- to (x, y).

    Setting ``group.position`` alone does not move anything: the units and the route
    carry their own coordinates, so the whole group is shifted by the delta.
    """
    origin = group.position  # type: ignore[attr-defined]
    dx, dy = x - origin.x, y - origin.y
    for unit in group.units:  # type: ignore[attr-defined]
        unit.position.x += dx
        unit.position.y += dy
    for point in group.points:  # type: ignore[attr-defined]
        point.position.x += dx
        point.position.y += dy
    return (dx * dx + dy * dy) ** 0.5


def _reseat_naval(
    mission: Mission, theater: object, table: dict[str, tuple[int, int]], heading: str
) -> None:
    print()
    print(f"{heading}:")
    groups = _all_groups(mission)
    for name, (x, y) in table.items():
        group = groups.get(name)
        if group is None:
            raise RuntimeError(f"{name} is not a group in the source miz")
        moved = _move_group(group, x, y) / 1000
        position = group.position  # type: ignore[attr-defined]
        if theater.is_on_land(position):  # type: ignore[attr-defined]
            raise RuntimeError(f"{name} would be placed on land at ({x}, {y})")
        print(
            f"  {name:<10} -> ({x/1000:7.0f}, {y/1000:7.0f}) km   moved {moved:5.0f} km"
        )


def _cull_ship_markers(mission: Mission) -> None:
    """Delete surplus ship markers -- every one generates a whole naval group."""
    print()
    print("culled ship markers:")
    removed = 0
    for coalition in mission.coalition.values():
        for country in coalition.countries.values():
            for group in list(country.ship_group):
                if group.name in CULLED_SHIP_MARKERS:
                    country.ship_group.remove(group)
                    removed += 1
    print(f"  removed {removed} of {len(CULLED_SHIP_MARKERS)} named markers")


def _fob_to_red(mission: Mission) -> None:
    """Re-block a FOB declaration: for a FOB the country block IS the owner."""
    blue = mission.country(MizCampaignLoader.BLUE_COUNTRY.name)
    red = mission.country(MizCampaignLoader.RED_COUNTRY.name)
    assert blue is not None and red is not None
    print()
    print("FOB ownership:")
    for name in FOBS_TO_RED:
        match = [g for g in blue.vehicle_group if g.name == name]
        if not match:
            raise RuntimeError(f"{name} is not a blue-block FOB in the source miz")
        group = match[0]
        blue.vehicle_group.remove(group)
        red.add_vehicle_group(group)
        print(f"  {name:<14} BLUE -> RED")


def _theater() -> object:
    """The Marianas theatre, loaded only for its landmap."""
    from game.campaignloader.campaign import Campaign

    campaign = Campaign.from_file(
        _REPO_ROOT / "resources/campaigns/pacific_repartee.yaml"
    )
    return campaign.load_theater(advanced_iads=False)


def _place_on_land(
    theater: object, anchor: Airport, avoid: Optional[list[object]] = None
) -> "object":
    """Return a land point MIN_OFFSET_M..MAX_OFFSET_M from ``anchor``.

    Deterministic: rings outward in fixed steps and takes the first bearing that
    lands on real terrain and clears every already-placed site by MIN_SEPARATION_M,
    so a re-run reproduces the same miz byte-for-byte.
    """
    taken = avoid or []
    origin = anchor.position
    radius = MIN_OFFSET_M
    while radius <= MAX_OFFSET_M:
        for bearing in range(0, 360, BEARING_STEP_DEG):
            candidate = origin.point_from_heading(bearing, radius)
            if not theater.is_on_land(candidate):  # type: ignore[attr-defined]
                continue
            if any(
                candidate.distance_to_point(other) < MIN_SEPARATION_M  # type: ignore[attr-defined]
                for other in taken
            ):
                continue
            return candidate
        radius += STEP_M
    raise RuntimeError(
        f"no land point within {MAX_OFFSET_M} m of {anchor.name}; "
        "the missile-site anchor needs re-picking"
    )


def _add_marker(
    mission: Mission,
    country_name: str,
    name: str,
    position: "object",
    unit_type: type[VehicleType],
) -> None:
    """Author a one-unit vehicle group -- the loader's marker convention."""
    country = mission.country(country_name)
    assert country is not None, country_name
    group = mission.vehicle_group(
        country=country,
        name=name,
        _type=unit_type,
        position=position,  # type: ignore[arg-type]
    )
    # Markers are read for their type and position only; they are never driven.
    for point in group.points:
        point.action = PointAction.OffRoad
        point.speed = 0


def _set_ownership(mission: Mission, names: Iterable[str], blue: bool) -> list[str]:
    changed = []
    for name in names:
        airport = mission.terrain.airports.get(name)
        if airport is None:
            raise RuntimeError(f"{name} is not an airfield on this terrain")
        before = str(airport.coalition)
        if blue:
            airport.set_blue()
        else:
            airport.set_red()
        changed.append(f"  {name:<26} {before:>8} -> {'BLUE' if blue else 'RED'}")
    return changed


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"missing source miz: {SOURCE}")

    mission = Mission()
    mission.load_file(str(SOURCE))
    print(f"loaded {SOURCE.name} ({mission.terrain.name})")

    print("\nairfield ownership:")
    for line in _set_ownership(mission, BLUE_AIRFIELDS, blue=True):
        print(line)
    for line in _set_ownership(mission, RED_AIRFIELDS, blue=False):
        print(line)

    theater = _theater()
    red_country = MizCampaignLoader.RED_COUNTRY.name

    # Two markers on the same island must not stack, so each ring search starts
    # where the previous one stopped.
    used: list[object] = []

    def author(
        sites: Iterable[tuple[str, str]],
        unit_type: type[VehicleType],
        heading: str,
    ) -> None:
        print(f"\n{heading} (red block):")
        for site_name, anchor_name in sites:
            anchor = mission.terrain.airports[anchor_name]
            position = _place_on_land(theater, anchor, avoid=used)
            used.append(position)
            _add_marker(mission, red_country, site_name, position, unit_type)
            offset = position.distance_to_point(anchor.position)  # type: ignore[attr-defined]
            print(
                f"  {site_name:<20} at ({position.x:.0f}, {position.y:.0f})"  # type: ignore[attr-defined]
                f"  {offset / 1000:.1f} km from {anchor_name}"
            )

    author(MISSILE_SITES, MissilesSS.Scud_B, "missile sites")
    author(SHORT_SAM_SITES, AirDefence.Strela_1_9P31, "point-defence SAM sites")

    _cull_ship_markers(mission)
    _fob_to_red(mission)
    _reseat_naval(mission, theater, BLUE_NAVAL, "blue carrier group")
    _reseat_naval(mission, theater, BLUE_ESCORTS, "blue escort screen")
    _reseat_naval(mission, theater, RED_NAVAL, "PLAN task groups")
    _reseat_naval(mission, theater, RED_ESCORTS, "PLAN escort screen")

    mission.save(str(DEST))
    print(f"\nwrote {DEST.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
