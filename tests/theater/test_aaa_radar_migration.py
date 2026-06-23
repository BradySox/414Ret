"""Save migration: stray search radars are stripped from AAA sites on load.

Older campaigns generated generic AAA sites with a random faction search radar
(the `AAA Site` layout's radar slot defaulted to `fill: true`), turning gun AAA
into a radar/EWR node -- e.g. a ZU-23 site wearing an SA-11 Buk search radar.
These cover the discrimination + in-place removal used by
`TheaterGroundObject.__setstate__`.
"""

from types import SimpleNamespace

from game.data.units import UnitClass
from game.theater.theatergroundobject import (
    _is_erroneous_aaa_search_radar,
    _strip_erroneous_aaa_radars_from_groups,
)


def _unit(unit_class: UnitClass, variant_id: str = "x") -> SimpleNamespace:
    return SimpleNamespace(
        unit_type=SimpleNamespace(unit_class=unit_class, variant_id=variant_id)
    )


def test_sam_search_radar_on_aaa_is_erroneous() -> None:
    sa11 = _unit(UnitClass.SEARCH_RADAR, 'SAM SA-11 Buk "Gadfly" Snow Drift SR')
    assert _is_erroneous_aaa_search_radar(sa11)


def test_son9_fire_can_is_kept() -> None:
    # The KS-19's dedicated fire-control radar legitimately belongs on an AAA site.
    for variant in ("AAA Fire Can SON-9", "AAA SON-9 Fire Can"):
        assert not _is_erroneous_aaa_search_radar(
            _unit(UnitClass.SEARCH_RADAR, variant)
        )


def test_guns_are_kept() -> None:
    assert not _is_erroneous_aaa_search_radar(_unit(UnitClass.AAA, "ZU-23 on Ural-375"))


def test_static_without_unit_type_is_kept() -> None:
    assert not _is_erroneous_aaa_search_radar(SimpleNamespace(unit_type=None))


def test_strip_removes_only_the_sam_radar() -> None:
    sa11 = _unit(UnitClass.SEARCH_RADAR, "SA-11 Buk SR 9S18M1")
    fire_can = _unit(UnitClass.SEARCH_RADAR, "AAA Fire Can SON-9")
    guns = [_unit(UnitClass.AAA, "ZU-23 on Ural-375") for _ in range(5)]
    jeep = _unit(UnitClass.UNKNOWN, "LUV UAZ-469 Jeep")
    group = SimpleNamespace(units=[sa11, *guns, fire_can, jeep])

    removed = _strip_erroneous_aaa_radars_from_groups([group])

    assert removed == 1
    assert sa11 not in group.units
    assert fire_can in group.units  # KS-19 Fire Can survives
    assert all(g in group.units for g in guns)
    assert jeep in group.units
