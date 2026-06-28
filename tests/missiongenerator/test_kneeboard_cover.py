"""Tests for the always-present kneeboard cover page (§30).

Every flight's (airframe's) deck opens on a CoverPage carrying the op/turn/date
header, the previous turn's SITREP (§29), and -- when 2+ client flights share the
airframe -- a callsign -> start-page index. These exercise the page-number math,
the SITREP gating, and the deterministic grouping with duck-typed fakes, without
standing up a full mission.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List, Optional

from game.ato.flighttype import FlightType
from game.missiongenerator.kneeboard import CoverPage, KneeboardGenerator
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
    campaign_name: Optional[str] = "Red Tide",
    turn: int = 7,
    compact: bool = False,
    all_packages: bool = False,
) -> KneeboardGenerator:
    gen = KneeboardGenerator.__new__(KneeboardGenerator)
    gen.dark_kneeboard = False
    gen.game = SimpleNamespace(  # type: ignore[assignment]
        campaign_name=campaign_name,
        turn=turn,
        current_day=date(1988, 6, 6),
        settings=SimpleNamespace(
            generate_sitrep_kneeboard=sitrep_enabled,
            compact_kneeboard=compact,
            generate_all_packages_kneeboard=all_packages,
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


def test_cover_index_start_pages_account_for_cover_and_block_sizes() -> None:
    gen = _generator()
    blocks: List[Any] = [
        (_flight("Uzi 1"), [None, None, None]),  # 3 pages
        (_flight("Pontiac 1", custom_name="SEAD"), [None, None, None, None]),  # 4
        (_flight("Colt 1"), [None, None]),  # 2
    ]
    page = gen._build_cover_page(_Aircraft("F/A-18C Hornet"), blocks)  # type: ignore[arg-type]
    assert isinstance(page, CoverPage)
    # The cover is page 1; blocks start at 2, then 2+3=5, then 5+4=9.
    assert page.index_rows is not None
    assert [row[2] for row in page.index_rows] == ["2", "5", "9"]
    assert page.index_rows[0][0] == "Uzi 1"
    assert page.index_rows[1][0] == 'Pontiac 1 ("SEAD")'  # custom name annotated
    assert page.index_rows[0][1] == "Strike"  # task column
    assert page.turn == 7 and page.campaign_name == "Red Tide"


def test_cover_omits_index_for_a_lone_flight_but_is_still_built() -> None:
    gen = _generator()
    blocks: List[Any] = [(_flight("Viper 1"), [None, None])]
    page = gen._build_cover_page(_Aircraft("F-16C"), blocks)  # type: ignore[arg-type]
    assert isinstance(page, CoverPage)
    assert page.index_rows is None  # no stack -> no index section...
    assert page.turn == 7  # ...but the cover (op/turn header) is always produced


def test_cover_sitrep_is_gated_by_setting_and_emptiness() -> None:
    sitrep = _sitrep()
    assert _generator(sitrep=sitrep)._cover_sitrep() is sitrep
    assert _generator(sitrep=sitrep, sitrep_enabled=False)._cover_sitrep() is None
    assert _generator(sitrep=_sitrep(empty=True))._cover_sitrep() is None
    assert _generator(sitrep=None)._cover_sitrep() is None  # turn 1 / no prior


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


def test_cover_page_renders_to_file(tmp_path: Path) -> None:
    page = CoverPage(
        campaign_name="Red Tide",
        turn=7,
        day=date(1988, 6, 6),
        sitrep=Sitrep(
            6,
            date(1988, 6, 6),
            SideLosses(2, 5, 1),
            SideLosses(4, 11, 0),
            ["Al Dhafra"],
            [],
            1,
        ),
        index_rows=[["Uzi 1", "Strike", "2"], ["Colt 1", "SEAD", "5"]],
        packages=None,
        aircraft=_Aircraft("F/A-18C"),  # type: ignore[arg-type]
        dark_kneeboard=False,
    )
    out = tmp_path / "cover.png"
    page.write(out)
    assert out.exists() and out.stat().st_size > 0


def test_cover_carries_friendly_packages_in_compact_mode() -> None:
    # Compact mode: the package list has nowhere else to live (recon imagery owns the
    # flex page), so it rides on the otherwise-empty cover. Built once for the whole
    # shared-airframe deck from a representative flight.
    gen = _generator(compact=True, all_packages=True)
    gen.build_all_packages_rows = lambda flight: [["SEAD", "BONGO", "20:46"]]  # type: ignore[method-assign]
    blocks: List[Any] = [
        (_flight("Uzi 1", aircraft=_Aircraft("F/A-18C")), [None, None])
    ]
    page = gen._build_cover_page(_Aircraft("F/A-18C"), blocks)  # type: ignore[arg-type]
    assert isinstance(page, CoverPage)
    assert page.packages is not None
    assert page.packages.rows == [["SEAD", "BONGO", "20:46"]]


def test_cover_omits_friendly_packages_outside_compact_mode() -> None:
    # The full multi-page deck keeps its own FriendlyPackagesPage, so the cover must not
    # duplicate the list there.
    gen = _generator(compact=False, all_packages=True)
    gen.build_all_packages_rows = lambda flight: [["SEAD", "BONGO", "20:46"]]  # type: ignore[method-assign]
    blocks: List[Any] = [
        (_flight("Uzi 1", aircraft=_Aircraft("F/A-18C")), [None, None])
    ]
    page = gen._build_cover_page(_Aircraft("F/A-18C"), blocks)  # type: ignore[arg-type]
    assert isinstance(page, CoverPage)
    assert page.packages is None
