"""Cut-off bases are reported, and a healthy theatre stays quiet.

§90 rung A decides whether a base rebuilds at all -- in full, at a quarter, or
not until the route is reopened -- and it had no surface anywhere. A player whose
base stopped recovering had no way to find out why. An invisible consequential
mechanic is a fairness problem, not a polish one. Seam 5's Phase 0 picked this
out as the most actionable invisible between-turn state.
"""

from __future__ import annotations

from typing import Any, cast

from game.fourteenth.supply_report import supply_sitrep_lines
from game.theater.supply import SupplyStatus
from game.theater.transitnetwork import TransitNetwork


class FakeControlPoint:
    def __init__(self, name: str, in_contact: bool) -> None:
        self.name = name
        self.has_active_frontline = in_contact


class FakeTheater:
    def __init__(self, points: list[Any]) -> None:
        self._points = points

    def control_points_for(self, player: Any) -> list[Any]:
        return self._points


class FakeCoalition:
    def __init__(self, network: TransitNetwork) -> None:
        self.transit_network = network


class FakeSettings:
    def __init__(self, gated: bool) -> None:
        self.supply_gated_reinforcement = gated


class FakeGame:
    def __init__(
        self, points: list[Any], network: TransitNetwork, gated: bool = True
    ) -> None:
        self.theater = FakeTheater(points)
        self.blue = FakeCoalition(network)
        self.settings = FakeSettings(gated)


def _cp(name: str, in_contact: bool) -> Any:
    return cast(Any, FakeControlPoint(name, in_contact))


def test_a_healthy_theatre_says_nothing() -> None:
    """A SITREP line per turn saying everything is fine is worse than silence."""
    rear = _cp("Ramstein", in_contact=False)
    front = _cp("Fulda", in_contact=True)
    network = TransitNetwork()
    network.link_road(front, rear)

    assert supply_sitrep_lines(cast(Any, FakeGame([rear, front], network))) == []


def test_a_cut_off_base_is_named() -> None:
    rear = _cp("Ramstein", in_contact=False)
    pocket = _cp("Fulda", in_contact=True)
    network = TransitNetwork()  # pocket is linked to nothing

    (line,) = supply_sitrep_lines(cast(Any, FakeGame([rear, pocket], network)))

    assert line == "Cut off, not being reinforced: Fulda"


def test_an_air_supplied_base_gets_its_own_line() -> None:
    rear = _cp("Ramstein", in_contact=False)
    pocket = _cp("Fulda", in_contact=True)
    network = TransitNetwork()
    network.link_airport(pocket, rear)

    (line,) = supply_sitrep_lines(cast(Any, FakeGame([rear, pocket], network)))

    assert line == "Air resupply only, rebuilding slowly: Fulda"


def test_both_tiers_report_separately_and_are_sorted() -> None:
    rear = _cp("Ramstein", in_contact=False)
    flown_in = _cp("Fulda", in_contact=True)
    encircled_b = _cp("Bravo", in_contact=True)
    encircled_a = _cp("Alpha", in_contact=True)
    network = TransitNetwork()
    network.link_airport(flown_in, rear)

    lines = supply_sitrep_lines(
        cast(Any, FakeGame([rear, flown_in, encircled_a, encircled_b], network))
    )

    assert lines == [
        "Cut off, not being reinforced: Alpha, Bravo",
        "Air resupply only, rebuilding slowly: Fulda",
    ]


def test_the_setting_off_reports_nothing() -> None:
    """With the gate off nothing is throttled, so there is nothing to report."""
    pocket = _cp("Fulda", in_contact=True)
    rear = _cp("Ramstein", in_contact=False)

    game = FakeGame([rear, pocket], TransitNetwork(), gated=False)

    assert supply_sitrep_lines(cast(Any, game)) == []


def test_the_report_covers_every_throttled_tier() -> None:
    """A tier added to SupplyStatus must not silently go unreported."""
    reported = {SupplyStatus.ISOLATED, SupplyStatus.AIRLIFTED}
    silent = {SupplyStatus.SUPPLIED}

    assert reported | silent == set(SupplyStatus)
