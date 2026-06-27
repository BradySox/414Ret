"""Tests for the shared-airframe kneeboard index (P4 co-op orientation page).

DCS scopes kneeboards per airframe, so several flights of a type share one stacked deck.
``KneeboardGenerator`` prepends a one-page index (callsign -> start page) when 2+ client
flights share a type. These exercise the index page-number math + the deterministic
grouping with duck-typed fakes, without standing up a full mission.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, List, Optional

from game.ato.flighttype import FlightType
from game.missiongenerator.kneeboard import KneeboardGenerator, KneeboardIndexPage


class _Aircraft:
    """Hashable AircraftType stand-in (SimpleNamespace defines __eq__ -> unhashable)."""

    def __init__(self, name: str) -> None:
        self.display_name = name


def _flight(
    callsign: str,
    flight_type: FlightType = FlightType.STRIKE,
    custom_name: Optional[str] = None,
    aircraft: Any = None,
    client: bool = True,
) -> Any:
    return SimpleNamespace(
        callsign=callsign,
        flight_type=flight_type,
        custom_name=custom_name,
        aircraft_type=aircraft,
        client_units=[object()] if client else [],
    )


def _generator() -> KneeboardGenerator:
    gen = KneeboardGenerator.__new__(KneeboardGenerator)
    gen.dark_kneeboard = False
    return gen


def test_index_start_pages_account_for_index_and_block_sizes() -> None:
    gen = _generator()
    aircraft = _Aircraft("F/A-18C Hornet")
    blocks: List[Any] = [
        (_flight("Uzi 1"), [None, None, None]),  # 3 pages
        (_flight("Pontiac 1", custom_name="SEAD"), [None, None, None, None]),  # 4 pages
        (_flight("Colt 1"), [None, None]),  # 2 pages
    ]
    page = gen._build_kneeboard_index(aircraft, blocks)  # type: ignore[arg-type]
    assert isinstance(page, KneeboardIndexPage)
    # Index is page 1; blocks start at 2, then 2+3=5, then 5+4=9.
    assert [row[2] for row in page.rows] == ["2", "5", "9"]
    assert page.rows[0][0] == "Uzi 1"
    assert page.rows[1][0] == 'Pontiac 1 ("SEAD")'  # custom name annotated
    assert page.rows[0][1] == "Strike"  # task column


def test_client_flights_by_airframe_groups_and_sorts_by_callsign() -> None:
    gen = _generator()
    hornet = _Aircraft("F/A-18C")
    viper = _Aircraft("F-16C")
    gen.flights = [
        _flight("Uzi 2", aircraft=hornet),
        _flight("Colt 1", aircraft=viper),
        _flight("Enfield 1", aircraft=hornet),
        _flight("Aiflight 1", aircraft=hornet, client=False),  # AI excluded
    ]
    grouped = gen.client_flights_by_airframe()
    assert set(grouped) == {hornet, viper}
    assert [f.callsign for f in grouped[hornet]] == ["Enfield 1", "Uzi 2"]  # type: ignore[index]
    assert [f.callsign for f in grouped[viper]] == ["Colt 1"]  # type: ignore[index]


def test_index_page_renders_to_file(tmp_path: Path) -> None:
    page = KneeboardIndexPage(
        _Aircraft("F/A-18C"),  # type: ignore[arg-type]
        [["Uzi 1", "Strike", "2"], ["Colt 1", "SEAD", "5"]],
        dark_kneeboard=False,
    )
    out = tmp_path / "index.png"
    page.write(out)
    assert out.exists() and out.stat().st_size > 0
