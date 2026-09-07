"""Which SAM a bordering nation stands up, and how big it is (§96)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from dcs.unittype import VehicleType
from dcs.vehicles import AirDefence

from game.utils import Distance, nautical_miles


@dataclass(frozen=True)
class SamSystem:
    """One rung of the border-defense ladder."""

    #: Suffix on the group name, so a debrief says which system it was.
    name: str
    #: Plausibly EXPORTED from this year, which is later than entering service
    #: for the Soviet systems. Checked 2026-09-07 against the 1982 Falklands
    #: column, where in-service dates handed Argentina a Buk.
    since: int
    #: Engagement reach, used to keep the site within range of its own border.
    reach: Distance
    #: Fixed composition (v1). Search radar, track radar, then launchers.
    units: tuple[type[VehicleType], ...]


#: East-bloc kit, the default: it is what most of the bordering nations on the
#: shipped terrains actually field. DM call 2026-09-07 -- SA-3 rather than SA-6
#: on the bottom rung.
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
SA_11 = SamSystem(
    "SA-11",
    1995,
    nautical_miles(19),
    (
        AirDefence.SA_11_Buk_SR_9S18M1,
        AirDefence.SA_11_Buk_CC_9S470M1,
        AirDefence.SA_11_Buk_LN_9A310M1,
        AirDefence.SA_11_Buk_LN_9A310M1,
    ),
)
S_300 = SamSystem(
    "S-300",
    1990,
    nautical_miles(40),
    (
        AirDefence.S_300PS_64H6E_sr,
        AirDefence.S_300PS_40B6M_tr,
        AirDefence.S_300PS_54K6_cp,
        AirDefence.S_300PS_5P85C_ln,
        AirDefence.S_300PS_5P85D_ln,
    ),
)

#: West-bloc kit, for the nations that plainly field it.
HAWK = SamSystem(
    "Hawk",
    1960,
    nautical_miles(22),
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
    nautical_miles(43),
    (
        AirDefence.Patriot_str,
        AirDefence.Patriot_cp,
        AirDefence.Patriot_ECS,
        AirDefence.Patriot_ln,
        AirDefence.Patriot_ln,
    ),
)

#: Longest first: the first rung the country has room for AND the era allows.
EAST_LADDER = (S_300, SA_11, SA_3)
WEST_LADDER = (PATRIOT, HAWK)

#: Room (largest inscribed circle) a country needs before it is worth standing
#: the next rung up. Measured over the 52 shipped zones 2026-09-07: 23 sit under
#: 40 NM and the rest run to 186.
ROOM_FOR = {
    S_300: nautical_miles(100),
    PATRIOT: nautical_miles(100),
    SA_11: nautical_miles(40),
    HAWK: nautical_miles(0),
    SA_3: nautical_miles(0),
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
    }
)


def system_for(country: str, room: Distance, day: date) -> SamSystem:
    """The best rung this country has both the room and the era for."""
    ladder = WEST_LADDER if country in WEST_EQUIPPED else EAST_LADDER
    for system in ladder:
        if day.year >= system.since and room >= ROOM_FOR[system]:
            return system
    return ladder[-1]
