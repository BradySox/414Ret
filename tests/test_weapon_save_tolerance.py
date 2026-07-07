"""Unknown weapon data in a save must degrade, not break.

Weapon.__setstate__ left an EMPTY object when the pickled clsid was unknown
(mod pack disabled, weapon data removed) -- the load succeeded and the crash
came later on first attribute access. WeaponGroup.__setstate__ hard-KeyErrored
on a removed/renamed group name, aborting the whole load as 'Invalid Save
game'. Both now keep the pickled state, matching FlightType's unknown-value
tolerance.
"""

from __future__ import annotations

from game.data.weapons import Weapon, WeaponGroup


def test_unknown_clsid_keeps_pickled_weapon_state() -> None:
    weapon = Weapon.__new__(Weapon)
    weapon.__setstate__({"clsid": "{NOT-A-REAL-CLSID}", "weapon_group": None})
    assert weapon.clsid == "{NOT-A-REAL-CLSID}"  # not an empty __dict__


def test_unknown_group_name_keeps_pickled_group_state() -> None:
    group = WeaponGroup.__new__(WeaponGroup)
    group.__setstate__(
        {
            "name": "not-a-real-group-name",
            "type": None,
            "introduction_year": None,
        }
    )
    assert group.name == "not-a-real-group-name"  # load survives, no KeyError
