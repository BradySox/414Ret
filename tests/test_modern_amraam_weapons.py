"""The modern AMRAAM/JATM stores the F-22A and CJS Super Hornet packs ship are
date-gated like every other missile.

Both packs register AIM-120D (and the F-22A pack AIM-260A, AIM9X-BLKII and the
Mako hypersonic) clsids, but none of them appeared in resources/weapons -- and
an unregistered clsid falls through `WeaponGroup.register_unknown_weapons`,
which sets introduction_year=None. `Weapon.available_on` reads that as "always
available", so those stores were ungated with no fallback.

That is not academic: `resources/customized_payloads/F-22A.lua` frags
{AIM-120D-3} in 12 fits, so every F-22A A2A sortie in the eleven campaigns that
preseed the pack was carrying an ungated AIM-120D -- including Clash of the
Titans, set in 2006.

The pack's payloads also put 2x Mako in all six of the Raptor's "Retribution
..." fits. Per the DM's 2026-08-03 call, AIM-260A is blue's top-end air-to-air
missile, so those stations now carry AIM-260A and nothing Retribution plans
frags a hypersonic. Mako stays registered anyway -- it is still selectable in
the payload editor, and an unregistered clsid is ungated in every era, so
deleting the group would be a regression rather than a removal.

These tests pin the registration itself, so a pack update that adds new pylon
stores fails here rather than silently shipping another ungated missile; that
no shipped fit frags Mako; and that the Raptor's real fit survives the 2027
date gate in the two campaigns actually set in 2027.
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
        (r"MAKO", "Mako"),
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
    """C -> D -> 260A -> Mako must not let a later missile arrive before an earlier one.

    Repo-wide monotonicity is deliberately NOT an invariant (cross-family
    fallbacks like a targeting pod falling back to a missile are intentional),
    so this is scoped to the one ladder these files add to.
    """
    ladder = [
        WeaponGroup.named(name) for name in ("AIM-120C", "AIM-120D", "AIM-260A", "Mako")
    ]

    for lower, higher in zip(ladder, ladder[1:]):
        assert (
            higher.fallback is lower
        ), f"{higher.name} should fall back to {lower.name}"
        assert lower.introduction_year is not None
        assert higher.introduction_year is not None
        assert lower.introduction_year <= higher.introduction_year


def test_aim_260a_is_blues_top_end_and_mako_is_not_fragged() -> None:
    """DM call 2026-08-03: AIM-260A is the ceiling; nothing plans a hypersonic.

    The F-22A pack's own payloads put 2x Mako in all six of the Raptor's
    "Retribution ..." fits. Those stations carry AIM-260A instead, so no
    generated loadout in any campaign frags {MAKO_A2A_C}.
    """
    for payload in Path("resources/customized_payloads").glob("*.lua"):
        assert "MAKO" not in payload.read_text(
            encoding="utf-8", errors="replace"
        ), f"{payload.name} frags a hypersonic; AIM-260A is blue's top-end missile"

    raptor = Path("resources/customized_payloads/F-22A.lua").read_text(encoding="utf-8")
    assert raptor.count('"{AIM-260A}"') == 12  # 2 per fit across the six A2A fits


def test_the_raptor_keeps_its_shipped_fit_in_the_2027_campaigns() -> None:
    """The stores the Raptor actually frags must survive the 2027 date gate.

    Baltic Fury (2027-07-17) and Marianas 2027 (2027-04-12) are the two
    campaigns set in 2027, so registering these must not strip the fit.
    """
    for clsid in ("{AIM-260A}", "{AIM-120D-3}", "{AIM-9XX}"):
        weapon = Weapon.with_clsid(clsid)
        assert weapon is not None
        assert weapon.available_on(
            datetime.date(2027, 4, 12), _NoOverrides()  # type: ignore[arg-type]
        ), f"{clsid} would be stripped from the Raptor's 2027 fit"


def test_mako_stays_registered_so_a_hand_load_is_still_gated() -> None:
    """Deleting the group is not neutral -- it would be ungated in every era.

    The store is still selectable in the payload editor, so it must keep a
    date even though nothing frags it. Clash of the Titans is 2006.
    """
    weapon = Weapon.with_clsid("{MAKO_A2A_C}")
    assert weapon is not None
    assert weapon.weapon_group.introduction_year is not None
    assert not weapon.available_on(
        datetime.date(2006, 1, 27), _NoOverrides()  # type: ignore[arg-type]
    )


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
