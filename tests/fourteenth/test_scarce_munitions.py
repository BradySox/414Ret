"""§54 M0 -- the curated scarce-munitions taxonomy.

The load-bearing guard is ``test_every_scarce_name_resolves``: the map is keyed by
exact ``WeaponGroup.name``, so if a weapon is renamed/removed upstream the map would
silently point at nothing -- this fails CI instead (the dead-name lesson). Plus
representative-family spot checks and negatives (dumb/IR weapons stay infinite).
"""

from __future__ import annotations

import pytest

from game.data.weapons import (
    _SCARCE_FAMILY_BY_NAME,
    _SCARCE_MUNITIONS,
    WeaponGroup,
)


@pytest.fixture(scope="module", autouse=True)
def _loaded() -> None:
    WeaponGroup.load_all()


def test_every_scarce_name_resolves() -> None:
    missing = sorted(n for n in _SCARCE_FAMILY_BY_NAME if n not in WeaponGroup._by_name)
    assert missing == [], f"scarce-munitions map has dead names: {missing}"


def test_no_name_appears_in_two_families() -> None:
    total = sum(len(names) for names in _SCARCE_MUNITIONS.values())
    assert total == len(_SCARCE_FAMILY_BY_NAME)


def test_representative_weapons_classify() -> None:
    cases = {
        "AIM-120C": "a2a_medium",
        "AIM-54C-MK47": "a2a_medium",
        "AGM-88C HARM": "arm",
        "Kh-25MP": "arm",  # anti-radar variant -> arm, not guided_asm
        "GBU-12": "pgm_bomb",
        "8xGBU-31(V)1/B": "pgm_bomb",  # a rack variant inherits its base family
        "Storm Shadow": "standoff",
        "AGM-154C JSOW": "standoff",
        "AGM-65D": "guided_asm",
        "Kh-25ML": "guided_asm",
    }
    for name, family in cases.items():
        assert WeaponGroup.named(name).scarce_family == family, name


def test_infinite_weapons_are_not_scarce() -> None:
    # Dumb / IR-dogfight munitions are never tracked (they stay effectively infinite).
    for name in ("AIM-9M", "R-73 (AA-11 Archer) - Infra Red", "FAB-500 M62"):
        assert WeaponGroup.named(name).scarce_family is None, name
