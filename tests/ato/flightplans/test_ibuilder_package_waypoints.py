"""``IBuilder._generate_package_waypoints_if_needed`` friendly-target skip.

Regression for a live crash (2026-06-30 flown session): planning a Combat SAR /
POW-recovery flight (``FlightType.CSAR``) against a ``CapturedPilotGroundObject``
hit ``assert self.package.waypoints is not None`` in
``AirAssaultFlightPlan.Builder.layout()``. Root cause: that objective is
deliberately flagged "friendly" (``is_friendly() == True``) so it renders/tasks
correctly for its owning side, even though it's physically positioned at the
enemy control point holding the POW -- but the "friendly target -> skip
offensive routing" shortcut treated that flag as "no ingress route needed",
leaving ``package.waypoints`` at its default ``None``. CSAR must always get a
real route regardless of the friendly flag.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from game.ato.flighttype import FlightType
from game.ato.flightplans.ibuilder import IBuilder
from game.ato.packagewaypoints import PackageWaypoints


class _ConcreteBuilder(IBuilder[Any, Any]):
    def build(self, dump_debug_info: bool = False) -> Any:
        return None


def _builder(
    flight_type: FlightType, target_is_friendly: bool
) -> tuple[_ConcreteBuilder, Any]:
    package = SimpleNamespace(
        waypoints=None,
        target=SimpleNamespace(is_friendly=lambda _player: target_is_friendly),
    )
    flight = SimpleNamespace(
        flight_type=flight_type,
        package=package,
        coalition=SimpleNamespace(game=SimpleNamespace(settings=None), player=object()),
    )
    return _ConcreteBuilder(cast(Any, flight)), package


def test_csar_generates_waypoints_even_against_a_friendly_flagged_target(
    monkeypatch: Any,
) -> None:
    builder, package = _builder(FlightType.CSAR, target_is_friendly=True)
    sentinel = object()
    monkeypatch.setattr(PackageWaypoints, "create", lambda *a, **k: sentinel)

    builder._generate_package_waypoints_if_needed(dump_debug_info=False)

    assert package.waypoints is sentinel


def test_non_csar_still_skips_waypoints_for_a_friendly_target(monkeypatch: Any) -> None:
    builder, package = _builder(FlightType.BARCAP, target_is_friendly=True)

    def _fail(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("PackageWaypoints.create should not be called")

    monkeypatch.setattr(PackageWaypoints, "create", _fail)

    builder._generate_package_waypoints_if_needed(dump_debug_info=False)

    assert package.waypoints is None


def test_offensive_target_still_generates_waypoints_regardless_of_type(
    monkeypatch: Any,
) -> None:
    builder, package = _builder(FlightType.STRIKE, target_is_friendly=False)
    sentinel = object()
    monkeypatch.setattr(PackageWaypoints, "create", lambda *a, **k: sentinel)

    builder._generate_package_waypoints_if_needed(dump_debug_info=False)

    assert package.waypoints is sentinel
