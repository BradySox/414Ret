"""The modern AMRAAM/JATM stores the F-22A and CJS Super Hornet packs ship are
date-gated like every other missile.

Both packs register AIM-120D (and the F-22A pack AIM-260A and AIM9X-BLKII)
clsids, but none of them appeared in resources/weapons -- and an unregistered
clsid falls through `WeaponGroup.register_unknown_weapons`, which sets
introduction_year=None. `Weapon.available_on` reads that as "always available",
so those stores were ungated with no fallback: `resources/customized_payloads/
F-22A.lua` frags {AIM-120D-3} in 12 fits, which a 1991 campaign would have
happily flown.

These tests pin the registration itself, so a pack update that adds new
AIM-120D/AIM-260A pylon stores fails here rather than silently shipping another
ungated missile.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path

import pytest

from game.data.weapons import Weapon, WeaponGroup

PACKS = (
    Path("pydcs_extensions/f22a/f22a.py"),
    Path("pydcs_extensions/fa18efg/fa18efg.py"),
)


class _NoOverrides:
    """Duck-typed Faction: `available_on` only reads the overrides mapping."""

    weapons_introduction_year_overrides: dict[str, int] = {}


def _pack_clsids(pattern: str) -> set[str]:
    found: set[str] = set()
    for pack in PACKS:
        for clsid in re.findall(
            r'"clsid":\s*"([^"]+)"', pack.read_text(encoding="utf-8")
        ):
            if re.search(pattern, clsid):
                found.add(clsid)
    return found


def _group_of(clsid: str) -> WeaponGroup:
    weapon = Weapon.with_clsid(clsid)
    assert weapon is not None, f"{clsid} is not registered in resources/weapons"
    return weapon.weapon_group


@pytest.mark.parametrize(
    ("pattern", "group_name"),
    [
        (r"AIM-120D|AIM_120D", "AIM-120D"),
        (r"AIM-260A|AIM_260A", "AIM-260A"),
        (r"AIM9X-BLKII|2xAIM9X-II", "AIM-9X"),
    ],
)
def test_every_pack_store_is_registered_to_its_group(
    pattern: str, group_name: str
) -> None:
    clsids = _pack_clsids(pattern)
    assert clsids, f"no {group_name} stores found in the packs -- did a pack move?"
    for clsid in sorted(clsids):
        assert _group_of(clsid).name == group_name


def test_the_amraam_ladder_is_ordered() -> None:
    """C -> D -> 260A must not let a later missile arrive before an earlier one.

    Repo-wide monotonicity is deliberately NOT an invariant (cross-family
    fallbacks like a targeting pod falling back to a missile are intentional),
    so this is scoped to the one ladder these files add to.
    """
    jatm = WeaponGroup.named("AIM-260A")
    amraam_d = WeaponGroup.named("AIM-120D")
    amraam_c = WeaponGroup.named("AIM-120C")

    assert amraam_d.fallback is amraam_c
    assert jatm.fallback is amraam_d

    assert amraam_c.introduction_year is not None
    assert amraam_d.introduction_year is not None
    assert jatm.introduction_year is not None
    assert amraam_c.introduction_year <= amraam_d.introduction_year
    assert amraam_d.introduction_year <= jatm.introduction_year


@pytest.mark.parametrize(
    ("year", "available"),
    [
        (1991, False),  # Desert Storm -- falls back down the ladder
        (2018, False),  # AIM-120C era
        (2027, True),  # Baltic Fury
    ],
)
def test_aim_120d_is_date_gated(year: int, available: bool) -> None:
    weapon = Weapon.with_clsid("{AIM-120D-3}")
    assert weapon is not None
    assert (
        weapon.available_on(datetime.date(year, 6, 1), _NoOverrides())  # type: ignore[arg-type]
        is available
    )


def test_the_f22a_payload_store_resolves() -> None:
    """The one AIM-120D store a shipped Retribution fit actually frags."""
    payload = Path("resources/customized_payloads/F-22A.lua").read_text(
        encoding="utf-8"
    )
    assert "{AIM-120D-3}" in payload
    assert _group_of("{AIM-120D-3}").name == "AIM-120D"
