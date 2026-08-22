"""Guard: every CJS Super Hornet claiming a networked datalink must be one pydcs knows.

`FlyingUnit.__init__` unconditionally calls `get_default_datalink()`, which routes
`networked_datalink = True` types through `DataLink.for_aircraft_id`. That function
RAISES on an unknown id rather than degrading, so a mod class flagged True for an id
pydcs has no entry for kills mission generation the moment the airframe is spawned
(the flown `RuntimeError: Datalink network not supported for aircraft with id
'FA-18ET'`). The tanker variants ship no datalink/DTC descriptor, so they must stay
False.
"""

from typing import Type

import game  # noqa: F401  (import first: pydcs_extensions is circular without it)
import pytest
from dcs.datalinks.datalink import DataLink
from dcs.planes import PlaneType

from pydcs_extensions.fa18efg.fa18efg import (
    EA_18G,
    FA_18E,
    FA_18ET,
    FA_18F,
    FA_18FT,
)

SUPER_HORNET_TYPES = [FA_18E, FA_18F, EA_18G, FA_18ET, FA_18FT]


@pytest.mark.parametrize("plane", SUPER_HORNET_TYPES, ids=lambda p: p.id)
def test_networked_datalink_types_resolve_in_pydcs(plane: Type[PlaneType]) -> None:
    if not plane.networked_datalink:
        assert plane.get_default_datalink() is None
        return
    assert DataLink.for_aircraft_id(plane.id) is not None


def test_tanker_variants_claim_no_networked_datalink() -> None:
    # Both are absent from pydcs' `for_aircraft_id` table and from the mod's own
    # DTC descriptors (only FA-18E/F and EA-18G ship one).
    for plane in (FA_18ET, FA_18FT):
        assert plane.networked_datalink is False
