"""Which SAM a bordering nation stands up, and how big it is (§98)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from dcs.unittype import VehicleType
from dcs.vehicles import AirDefence

from game.utils import Distance, meters, nautical_miles

#: How much of the database reach a site is placed to cover. The DCS
#: ``threat_range`` is the kinematic maximum against a target that does not
#: manoeuvre -- it equals ``air_weapon_dist`` exactly on every system here -- so
#: a battery sited at the full figure defends its border on paper and not in the
#: air. DM call 2026-09-10: place conservatively.
#:
#: **Unrelated to** ``neutralborder.MAX_DEPTH_FRACTION``, which happens to share
#: the number. That one stops a system out-ranging its own country from
#: collapsing every site onto the country's centre; this one is about what the
#: missile really covers.
PLACEMENT_FRACTION = 0.6


@dataclass(frozen=True)
class SamSystem:
    """One rung of the border-defense ladder."""

    #: Suffix on the group name, so a debrief says which system it was.
    name: str
    #: Plausibly EXPORTED from this year, which is later than entering service
    #: for the Soviet systems. Checked 2026-09-07 against the 1982 Falklands
    #: column, where in-service dates handed Argentina a Buk.
    since: int
    #: The DCS launcher's own ``threat_range``, read off pydcs 2026-09-10 and
    #: confirmed against the DM's stock no-mod export -- all eight agree, and
    #: the earlier hand-picked numbers did not (SA-3 matched exactly, SA-11 read
    #: 19 against 27, S-300 40 against 65). This is the record of what the unit
    #: claims; :attr:`placement_reach` is what the siting believes.
    reach: Distance
    #: Fixed composition (v1). Search radar, track radar, then launchers.
    units: tuple[type[VehicleType], ...]

    @property
    def placement_reach(self) -> Distance:
        """How far from the frontier a battery of this system is stood.

        Deliberately short of :attr:`reach`. Siting at the database maximum puts
        the border on the very edge of the envelope, where a crossing aircraft
        is inside the ring and outside anything the missile can actually catch.
        """
        return meters(self.reach.meters * PLACEMENT_FRACTION)


# --------------------------------------------------------------------------
# Legacy east: what a country fielded before the mid-90s, and plenty still do.
# --------------------------------------------------------------------------
SA_3 = SamSystem(
    "SA-3",
    1961,
    nautical_miles(10),
    (
        AirDefence.p_19_s_125_sr,
        AirDefence.snr_s_125_tr,
        AirDefence.x_5p73_s_125_ln,
        AirDefence.x_5p73_s_125_ln,
    ),
)
SA_2 = SamSystem(
    "SA-2",
    1960,
    nautical_miles(23),
    (
        AirDefence.p_19_s_125_sr,
        AirDefence.SNR_75V,
        AirDefence.S_75M_Volhov,
        AirDefence.S_75M_Volhov,
    ),
)
#: The legacy long-range belt. Composition follows the shipped "SA-5 Legacy
#: Site" layout, which pairs the 19J6 search set with the 5N62V tracker.
SA_5 = SamSystem(
    "SA-5",
    1970,
    nautical_miles(138),
    (
        AirDefence.RLS_19J6,
        AirDefence.RPC_5N62V,
        AirDefence.S_200_Launcher,
        AirDefence.S_200_Launcher,
    ),
)

# --------------------------------------------------------------------------
# Modern east.
# --------------------------------------------------------------------------
SA_11 = SamSystem(
    "SA-11",
    1995,
    nautical_miles(27),
    (
        AirDefence.SA_11_Buk_SR_9S18M1,
        AirDefence.SA_11_Buk_CC_9S470M1,
        AirDefence.SA_11_Buk_LN_9A310M1,
        AirDefence.SA_11_Buk_LN_9A310M1,
    ),
)
S_300 = SamSystem(
    "SA-10",
    1990,
    nautical_miles(65),
    (
        AirDefence.S_300PS_64H6E_sr,
        AirDefence.S_300PS_40B6M_tr,
        AirDefence.S_300PS_54K6_cp,
        AirDefence.S_300PS_5P85C_ln,
        AirDefence.S_300PS_5P85D_ln,
    ),
)

# --------------------------------------------------------------------------
# West-bloc kit, for the nations that plainly field it.
# --------------------------------------------------------------------------
RAPIER = SamSystem(
    "Rapier",
    1971,
    nautical_miles(4),
    (
        AirDefence.rapier_fsa_blindfire_radar,
        AirDefence.rapier_fsa_optical_tracker_unit,
        AirDefence.rapier_fsa_launcher,
        AirDefence.rapier_fsa_launcher,
    ),
)
HAWK = SamSystem(
    "Hawk",
    1960,
    nautical_miles(24),
    (
        AirDefence.Hawk_sr,
        AirDefence.Hawk_tr,
        AirDefence.Hawk_pcp,
        AirDefence.Hawk_ln,
        AirDefence.Hawk_ln,
    ),
)
PATRIOT = SamSystem(
    "Patriot",
    1990,
    nautical_miles(54),
    (
        AirDefence.Patriot_str,
        AirDefence.Patriot_cp,
        AirDefence.Patriot_ECS,
        AirDefence.Patriot_ln,
        AirDefence.Patriot_ln,
    ),
)

#: The campaign year from which a country is assumed to have re-equipped. Set at
#: the modern ladder's own latest export rather than at a political date, so a
#: ladder can never offer a system its own ``since`` then refuses.
MODERN_FROM = 1995

#: Best first. The LADDER is picked by era and the RUNG within it by room --
#: the two-tier split the DM asked for (2026-09-10): SA-2/3/5, or SA-10/11.
EAST_MODERN = (S_300, SA_11, SA_3)
EAST_LEGACY = (SA_5, SA_2, SA_3)
#: **The west has no legacy long-range rung**, because vanilla DCS models no
#: Nike Hercules. A large pre-1995 western country tops out at Hawk. That is a
#: gap in the available kit, not a judgement about the country.
WEST_MODERN = (PATRIOT, HAWK, RAPIER)
WEST_LEGACY = (HAWK, RAPIER)

#: Room (largest inscribed circle) a country needs before the next rung up is
#: worth standing. Re-scaled 2026-09-10 against the 55 zones the corrected clip
#: boxes produce, which run 5.8 NM to 216 NM. The old thresholds were set while
#: those boxes still stopped inside the terrain, so every country measured
#: smaller than it really is on the map.
#:
#: The bands are where the measured distribution actually breaks: 12 zones over
#: 100 NM, 16 under 25. **The top rung is the same band in both eras** -- a
#: country large enough for an SA-5 in 1982 is large enough for an SA-10 in
#: 2004, which is the point of having two tiers rather than two scales.
ROOM_FOR = {
    S_300: nautical_miles(100),
    PATRIOT: nautical_miles(100),
    SA_5: nautical_miles(100),
    SA_11: nautical_miles(25),
    SA_2: nautical_miles(25),
    HAWK: nautical_miles(25),
    SA_3: nautical_miles(0),
    RAPIER: nautical_miles(0),
}

#: Nations on the shipped terrains that field western SAMs. Everything else
#: takes the east ladder, which is the common case rather than a judgement about
#: alignment -- bloc posture gets Iraq and Russia wrong, so it is not used here.
WEST_EQUIPPED = frozenset(
    {
        "Israel",
        "Turkey",
        "Norway",
        "Sweden",
        "Finland",
        "Kuwait",
        "United Arab Emirates",
        "Bahrain",
        "Oman",
        "Saudi Arabia",
        "Jordan",
        # The Falkland Islands are a UK zone, and Rapier is what actually
        # defended them.
        "UK",
    }
)


def ladder_for(country: str, day: date) -> tuple[SamSystem, ...]:
    """Which tier this country draws from: legacy kit, or modern."""
    if country in WEST_EQUIPPED:
        return WEST_MODERN if day.year >= MODERN_FROM else WEST_LEGACY
    return EAST_MODERN if day.year >= MODERN_FROM else EAST_LEGACY


def system_for(country: str, room: Distance, day: date) -> SamSystem:
    """The best rung this country has both the room and the era for."""
    ladder = ladder_for(country, day)
    for system in ladder:
        if day.year >= system.since and room >= ROOM_FOR[system]:
            return system
    # Out of room, out of era, or both. Take the lightest rung the era DOES
    # allow, rather than the lightest rung outright: returning the last one
    # unconditionally handed a 1965 campaign a Rapier, six years early.
    for system in reversed(ladder):
        if day.year >= system.since:
            return system
    return ladder[-1]
