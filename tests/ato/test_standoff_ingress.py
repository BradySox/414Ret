"""The ingress point must respect the package's own weapon range.

The attack task does not activate until a flight reaches the ingress point, and
the doctrine bound is weapon-agnostic (45 nm on modern doctrine). A package
carrying a 160 nm anti-ship missile therefore flew PAST its own launch range,
into the target's defenses, and was shot down or turned back before it ever
fired -- the "flew straight in and never launched" case documented in
juanjux/dcs-retribution's OPFOR playbook.

The number is a planning bound, not a promise: DCS releases at its own doctrine
distance regardless. What it buys is that the flight is not dragged inside the
defenses before its attack task exists.
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import Any, Optional

from game.ato.packagewaypoints import PackageWaypoints
from game.data.doctrine import MODERN_DOCTRINE
from game.data.weapons import WeaponGroup
from game.utils import Distance, nautical_miles


def _package(*flight_ranges: Optional[Distance]) -> Any:
    return SimpleNamespace(
        target=SimpleNamespace(name="TARGET"),
        flights=[SimpleNamespace(max_standoff_range=r) for r in flight_ranges],
    )


#: Long enough that the 60%-of-leg cap never binds in the tests that are not
#: about the cap.
_LONG_LEG = nautical_miles(1000)


def _ingress_for(package: Any, leg: Distance = _LONG_LEG) -> Distance:
    return PackageWaypoints.standoff_doctrine(
        package, MODERN_DOCTRINE, leg
    ).max_ingress_distance


def test_no_authored_range_leaves_the_doctrine_untouched() -> None:
    # The data is the gate: until a weapon declares a range, nothing moves.
    assert (
        PackageWaypoints.standoff_doctrine(
            _package(None, None), MODERN_DOCTRINE, _LONG_LEG
        )
        is MODERN_DOCTRINE
    )


def test_a_weapon_that_outranges_the_bound_pushes_the_ingress_out() -> None:
    assert _ingress_for(_package(nautical_miles(160))) == nautical_miles(160)


def test_a_short_ranged_weapon_never_narrows_the_bound() -> None:
    # 20 nm is inside the 45 nm bound; the ingress must not be pulled in closer.
    assert _ingress_for(_package(nautical_miles(20))) == (
        MODERN_DOCTRINE.max_ingress_distance
    )


def test_the_shortest_shooter_sets_the_package_number() -> None:
    # One ingress point for the whole package, so it can only stand off as far as
    # its least-capable shooter.
    assert _ingress_for(
        _package(nautical_miles(270), nautical_miles(67))
    ) == nautical_miles(67)


def test_a_flight_carrying_nothing_ranged_is_excluded_not_counted_as_zero() -> None:
    # An escort has no authored range. Treating it as 0 would collapse the
    # package back to the doctrine bound and undo the fix.
    assert _ingress_for(_package(nautical_miles(160), None)) == nautical_miles(160)


def test_the_ingress_is_capped_so_the_route_cannot_invert() -> None:
    # JoinZoneGeometry puts the join at 35-36% of the departure-to-target leg, so
    # an ingress past ~64% from the target would sit behind the join.
    leg = nautical_miles(100)
    assert _ingress_for(_package(nautical_miles(590)), leg) == nautical_miles(60)


def test_the_cap_can_leave_the_bound_unchanged() -> None:
    # A short leg where 60% is still inside the doctrine bound: no widening, and
    # the doctrine object is returned untouched rather than rebuilt.
    leg = nautical_miles(50)
    assert (
        PackageWaypoints.standoff_doctrine(
            _package(nautical_miles(590)), MODERN_DOCTRINE, leg
        )
        is MODERN_DOCTRINE
    )


def test_widening_changes_only_the_ingress_bound() -> None:
    widened = PackageWaypoints.standoff_doctrine(
        _package(nautical_miles(160)), MODERN_DOCTRINE, _LONG_LEG
    )
    assert widened == replace(MODERN_DOCTRINE, max_ingress_distance=nautical_miles(160))


def test_the_yaml_range_reaches_the_weapon_group() -> None:
    # Guards the loader: `range:` is in nautical miles, and the weapon proxies it.
    harpoon = WeaponGroup.named("AGM-84D")
    assert harpoon.standoff_range == nautical_miles(67)
    assert harpoon.weapons[0].standoff_range == nautical_miles(67)


def test_a_weapon_with_no_authored_range_reports_none() -> None:
    assert WeaponGroup.named("BL-755").standoff_range is None
