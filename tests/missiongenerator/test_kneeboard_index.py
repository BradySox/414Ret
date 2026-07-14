"""Tests for the shared-airframe flight index page (§27) + the SITREP gating (§29).

DCS stacks every client flight of an airframe into one kneeboard deck; when 2+
flights share a type, a one-page callsign -> start-page index fronts the stack.
These exercise the page-number math, the SITREP gating for the briefing page,
and the deterministic grouping with duck-typed fakes, without standing up a
full mission.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List, Optional

from game.ato.flighttype import FlightType
from game.missiongenerator.kneeboard import KneeboardGenerator, KneeboardIndexPage
from game.sitrep import SideLosses, Sitrep


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
        task_display_name=flight_type.value,
        custom_name=custom_name,
        aircraft_type=aircraft,
        client_units=[object()] if client else [],
    )


def _generator(
    sitrep: Optional[Sitrep] = None,
    sitrep_enabled: bool = True,
) -> KneeboardGenerator:
    gen = KneeboardGenerator.__new__(KneeboardGenerator)
    gen.dark_kneeboard = False
    gen.game = SimpleNamespace(  # type: ignore[assignment]
        settings=SimpleNamespace(
            generate_sitrep_kneeboard=sitrep_enabled,
        ),
        last_sitrep=sitrep,
    )
    return gen


def _sitrep(turn: int = 6, empty: bool = False) -> Sitrep:
    losses = SideLosses(0, 0, 0) if empty else SideLosses(2, 5, 1)
    return Sitrep(
        turn=turn,
        day=date(1988, 6, 5),
        friendly=losses,
        enemy=SideLosses(0, 0, 0),
        captured=[],
        lost=[],
        pilots_recovered=0,
    )


def test_index_start_pages_account_for_the_index_and_block_sizes() -> None:
    gen = _generator()
    blocks: List[Any] = [
        (_flight("Uzi 1"), [None, None, None]),  # 3 pages
        (_flight("Pontiac 1", custom_name="SEAD"), [None, None, None, None]),  # 4
        (_flight("Colt 1"), [None, None]),  # 2
    ]
    page = gen._build_index_page(_Aircraft("F/A-18C Hornet"), blocks)  # type: ignore[arg-type]
    assert isinstance(page, KneeboardIndexPage)
    # The index is page 1; blocks start at 2, then 2+3=5, then 5+4=9.
    assert [row[2] for row in page.rows] == ["2", "5", "9"]
    assert page.rows[0][0] == "Uzi 1"
    assert page.rows[1][0] == 'Pontiac 1 ("SEAD")'  # custom name annotated
    assert page.rows[0][1] == "Strike"  # task column
    assert page.aircraft.display_name == "F/A-18C Hornet"


def test_briefing_sitrep_is_gated_by_setting_and_emptiness() -> None:
    sitrep = _sitrep()
    assert _generator(sitrep=sitrep)._briefing_sitrep() is sitrep
    assert _generator(sitrep=sitrep, sitrep_enabled=False)._briefing_sitrep() is None
    assert _generator(sitrep=_sitrep(empty=True))._briefing_sitrep() is None
    assert _generator(sitrep=None)._briefing_sitrep() is None  # turn 1 / no prior


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
    text = out.with_suffix(".txt").read_text("utf8")
    assert "Flight Index" in text
    assert "Uzi 1" in text and "Colt 1" in text
