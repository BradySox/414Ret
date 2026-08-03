"""Build ``resources/campaigns/marianas_2027.miz`` from Fuzzle's Pacific Repartee miz.

"Marianas - Second Island Chain (2027)" forks the laydown of
``pacific_repartee.miz`` rather than re-authoring the Marianas from scratch: that
miz already carries a furnished 15-CP island chain (four FOBs, three PLAN carrier
groups, two LHAs, the SAM/EWR/armor/strike markers and the Guam supply road), and
its every unit is vanilla, so pydcs round-trips it losslessly.

Four edits are applied, all of which the source miz cannot express by itself:

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

4.  **Rota gets a SAM battery.**  It was NEUTRAL and therefore carries no authored
    garrison of any kind, which would leave the newly-red field nearest Guam naked.

Every added marker position is validated against the real landmap
(``ConflictTheater.is_on_land``) so nothing is authored into the sea.

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
# would leave the red strike field nearest Guam (and its PLARF site) undefended.  One
# medium-range SAM marker gives it a real battery; the marker type only selects the
# band, the red faction's own roster fills it (HQ-22 / SA-11 for China 2020).
MEDIUM_SAM_SITES: tuple[tuple[str, str], ...] = (("Rota SAM Site", "Rota Intl"),)

# Search parameters for _place_on_land, in metres. The minimum keeps a launcher off
# the airfield it anchors to; the maximum keeps it on the same small island.
MIN_OFFSET_M = 1_500
MAX_OFFSET_M = 6_000
STEP_M = 250
BEARING_STEP_DEG = 15
# Two authored sites on the same island must not stack on top of each other.
MIN_SEPARATION_M = 1_200


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
    author(MEDIUM_SAM_SITES, AirDefence.S_75M_Volhov, "medium SAM sites")

    mission.save(str(DEST))
    print(f"\nwrote {DEST.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
