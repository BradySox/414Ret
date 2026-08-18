"""A player's ramp allowance follows the airframe where somebody has sourced one.

`player_startup_time` is one campaign-wide number for every aircraft a player might
cold-start. A Viper on a stored-heading alignment is ready in ~90 seconds; an F-4E cannot
even begin aligning until its gyros reach 160 degrees. Upstream issue #214, open since 2023.

Values and their sources are in docs/dev/design/414th-startup-times-notes.md. These tests
pin the plumbing and the invariants, not the numbers themselves -- a measured value is
allowed to move.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
import yaml

from game.ato.starttype import StartType

AIRCRAFT = Path("resources/units/aircraft")
NOTE = Path("docs/dev/design/414th-startup-times-notes.md")


def _yamls_with_a_value() -> dict[str, int]:
    found = {}
    for path in sorted(AIRCRAFT.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if "startup_minutes" in data:
            found[path.name] = data["startup_minutes"]
    return found


def _estimate_startup(startup_minutes: int | None, clients: int) -> timedelta:
    """FlightPlan is abstract, so call the method against a stand-in rather than
    instantiating a concrete plan and dragging a whole theater in with it."""
    from game.ato.flightplans.flightplan import FlightPlan

    plan = cast(
        Any,
        SimpleNamespace(
            flight=SimpleNamespace(
                start_type=StartType.COLD,
                client_count=clients,
                unit_type=SimpleNamespace(startup_minutes=startup_minutes),
                coalition=SimpleNamespace(
                    game=SimpleNamespace(
                        settings=SimpleNamespace(player_startup_time=10)
                    )
                ),
            )
        ),
    )
    return FlightPlan.estimate_startup(plan)


def test_an_airframe_without_a_value_uses_the_campaign_setting() -> None:
    """The no-change case: 254 of 258 yamls carry no value and must not move."""
    assert _estimate_startup(None, clients=2) == timedelta(minutes=10)


def test_an_airframe_with_a_value_uses_it() -> None:
    assert _estimate_startup(4, clients=2) == timedelta(minutes=4)


def test_ai_flights_are_untouched() -> None:
    """DCS AI skips the procedure entirely, so alignment data says nothing about it.
    A per-airframe value must not leak into the AI's 2 minutes."""
    assert _estimate_startup(9, clients=0) == timedelta(minutes=2)


def test_a_zero_minute_value_is_honoured_rather_than_falling_back() -> None:
    """0 is a legitimate value; only an absent key means 'use the setting'."""
    assert _estimate_startup(0, clients=2) == timedelta()


@pytest.mark.parametrize("name, minutes", sorted(_yamls_with_a_value().items()))
def test_every_value_is_plausible(name: str, minutes: int) -> None:
    assert 1 <= minutes <= 30, f"{name}: {minutes} min is not a startup time"


@pytest.mark.parametrize("name", sorted(_yamls_with_a_value()))
def test_every_value_is_sourced_in_the_design_note(name: str) -> None:
    """The yaml carries the number; the note carries where it came from. A value
    nobody can trace back to a manual page is exactly what this must not accumulate."""
    airframe = name.removesuffix(".yaml")
    note = NOTE.read_text(encoding="utf-8")
    assert airframe in note, (
        f"{name} sets startup_minutes but is not in {NOTE}. Add its source, or drop "
        "the value and let it fall back to player_startup_time."
    )
