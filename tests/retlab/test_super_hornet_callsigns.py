"""Guard: CJS Super Hornet callsign pools must be keyed by pydcs country shortname.

`Mission._assign_callsign` resolves a flight's pool with
``callnames.get(_country.shortname)`` -- ``AUS``, ``KWT``, ``AUSAF``, ``USA`` -- while the
pydcs exporter writes the mod's *display* names (``Australia``, ``Kuwait``,
``USAF Aggressors``). A block copied straight out of an export therefore resolves for USA
alone, where name and shortname coincide, and the other three pools are dead data that
nothing reads and no test would notice.

The same lookup is why the pools were wrong before 2026-09-09: the extension carried a
single ``"USA"`` key holding the mod's *Australian* names, so every US Rhino called
"Brutal" instead of "Hornet". A CJTF country chains every pool regardless of key
(``if "Combined Joint Task Forces" in _country.name``), which is what hid the defect --
most fork factions fielding the type are CJTF.
"""

from typing import Type

import game  # noqa: F401  (import first: pydcs_extensions is circular without it)
import pytest
from dcs.countries import country_dict
from dcs.planes import PlaneType

from pydcs_extensions.fa18efg.fa18efg import (
    EA_18G,
    FA_18E,
    FA_18ET,
    FA_18F,
    FA_18FT,
)

SUPER_HORNET_TYPES = [FA_18E, FA_18F, EA_18G, FA_18ET, FA_18FT]
EXPECTED_POOLS = {"AUS", "AUSAF", "USA", "KWT"}

SHORTNAMES = {c.shortname for c in country_dict.values()}


@pytest.mark.parametrize("plane", SUPER_HORNET_TYPES, ids=lambda p: p.id)
def test_every_callsign_pool_is_keyed_by_a_real_shortname(
    plane: Type[PlaneType],
) -> None:
    unknown = set(plane.callnames) - SHORTNAMES
    assert (
        not unknown
    ), f"{plane.id} pools keyed by display name, not shortname: {unknown}"


@pytest.mark.parametrize("plane", SUPER_HORNET_TYPES, ids=lambda p: p.id)
def test_all_four_mod_pools_are_present(plane: Type[PlaneType]) -> None:
    assert set(plane.callnames) == EXPECTED_POOLS


@pytest.mark.parametrize("plane", SUPER_HORNET_TYPES, ids=lambda p: p.id)
def test_us_pool_is_the_us_one(plane: Type[PlaneType]) -> None:
    # "Brutal" heads the mod's Australian pool. Before 2026-09-09 it was filed under USA,
    # which is the whole defect this file guards.
    assert "Hornet" in plane.callnames["USA"]
    assert "Brutal" not in plane.callnames["USA"]
    assert "Brutal" in plane.callnames["AUS"]
