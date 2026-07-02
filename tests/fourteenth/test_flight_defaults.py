"""Tests for the per-aircraft flight-defaults store (§43).

Covers the round-trip persistence, the BLUE-only / fresh-flight apply path, the
fuel clamp, and the defensive no-ops (no entry, persistency not set up) that keep
this QOL feature from ever breaking flight generation.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from game.fourteenth import flight_defaults

HORNET = "FA-18C_hornet"


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point the store at a throwaway file and start from a clean cache."""
    path = tmp_path / "flight_defaults.json"
    monkeypatch.setattr(flight_defaults, "flight_defaults_path", lambda: path)
    flight_defaults.invalidate_cache()
    yield path
    flight_defaults.invalidate_cache()


def _fake_flight(
    *,
    is_blue: bool = True,
    aircraft_id: str = HORNET,
    fuel_max: float = 4900.0,
    members: int = 2,
    fuel: float = 4900.0,
) -> SimpleNamespace:
    roster = SimpleNamespace(
        members=[SimpleNamespace(properties={}) for _ in range(members)]
    )
    unit_type = SimpleNamespace(
        dcs_unit_type=SimpleNamespace(id=aircraft_id, fuel_max=fuel_max),
        display_name="F/A-18C",
    )
    coalition = SimpleNamespace(player=SimpleNamespace(is_blue=is_blue))
    return SimpleNamespace(
        coalition=coalition, unit_type=unit_type, roster=roster, fuel=fuel
    )


def test_round_trip_and_reload_from_disk(store: Path) -> None:
    assert not flight_defaults.has_defaults_for(HORNET)
    flight_defaults.save_defaults_for(HORNET, 4000.0, {"condition": 80})
    assert flight_defaults.has_defaults_for(HORNET)
    assert store.exists()
    # Drop the in-memory cache -- the value must come back from disk.
    flight_defaults.invalidate_cache()
    assert flight_defaults.has_defaults_for(HORNET)


def test_apply_seeds_blue_fresh_flight(store: Path) -> None:
    flight_defaults.save_defaults_for(HORNET, 3000.0, {"condition": 75})
    flight = _fake_flight(fuel=4900.0)
    flight_defaults.apply_flight_defaults(flight)  # type: ignore[arg-type]
    assert flight.fuel == 3000.0
    for member in flight.roster.members:
        assert member.properties["condition"] == 75


def test_apply_skips_red_coalition(store: Path) -> None:
    flight_defaults.save_defaults_for(HORNET, 3000.0, {"condition": 75})
    flight = _fake_flight(is_blue=False, fuel=4900.0)
    flight_defaults.apply_flight_defaults(flight)  # type: ignore[arg-type]
    assert flight.fuel == 4900.0
    assert flight.roster.members[0].properties == {}


def test_apply_without_entry_is_noop(store: Path) -> None:
    flight = _fake_flight(fuel=4900.0)
    flight_defaults.apply_flight_defaults(flight)  # type: ignore[arg-type]
    assert flight.fuel == 4900.0
    assert flight.roster.members[0].properties == {}


def test_fuel_clamped_to_tank(store: Path) -> None:
    flight_defaults.save_defaults_for(HORNET, 10_000_000.0, {})
    flight = _fake_flight(fuel_max=4900.0, fuel=4900.0)
    flight_defaults.apply_flight_defaults(flight)  # type: ignore[arg-type]
    assert flight.fuel == 4900.0


def test_clear_removes_entry(store: Path) -> None:
    flight_defaults.save_defaults_for(HORNET, 3000.0, {"condition": 75})
    flight_defaults.clear_defaults_for(HORNET)
    assert not flight_defaults.has_defaults_for(HORNET)
    # Clearing a non-existent entry is a no-op, not an error.
    flight_defaults.clear_defaults_for("does-not-exist")


def test_missing_persistency_is_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> Path:
        raise AssertionError("persistency not set up")

    monkeypatch.setattr(flight_defaults, "flight_defaults_path", boom)
    flight_defaults.invalidate_cache()
    assert flight_defaults.has_defaults_for(HORNET) is False
    flight = _fake_flight()
    flight_defaults.apply_flight_defaults(flight)  # type: ignore[arg-type]
    assert flight.fuel == 4900.0
    flight_defaults.invalidate_cache()
