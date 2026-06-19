from unittest.mock import MagicMock

from game.data.units import UnitClass
from game.theater.base import Base


def test_non_frontline_inventory_does_not_count_as_combat_strength() -> None:
    tank = MagicMock(unit_class=UnitClass.TANK)
    sof = MagicMock(unit_class=UnitClass.INFANTRY)
    base = Base()
    base.armor = {tank: 10, sof: 3}

    assert base.total_armor == 13
    assert base.total_frontline_units == 10
