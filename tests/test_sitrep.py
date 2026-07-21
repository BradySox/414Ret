from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable, cast

from game.debriefing import Debriefing
from game.sitrep import SideLosses, Sitrep, sitrep_for_kneeboard
from game.theater.player import Player


def _loss(aircraft: int, front_line: int, ground_objects: int) -> Any:
    return SimpleNamespace(
        aircraft=aircraft, front_line=front_line, ground_objects=ground_objects
    )


def _capture(name: str, by: Player) -> Any:
    return SimpleNamespace(
        control_point=SimpleNamespace(name=name), captured_by_player=by
    )


def _debrief(
    blue: Any,
    red: Any,
    captures: Iterable[Any] = (),
    rescues: Iterable[str] = (),
) -> Debriefing:
    return cast(
        Debriefing,
        SimpleNamespace(
            loss_counts=lambda p: blue if p == Player.BLUE else red,
            base_captures=list(captures),
            state_data=SimpleNamespace(combat_sar_rescues=list(rescues)),
        ),
    )


def test_from_debriefing_splits_sides_captures_and_rescues() -> None:
    debrief = _debrief(
        blue=_loss(2, 5, 1),
        red=_loss(4, 11, 2),
        captures=[
            _capture("Al Dhafra", Player.BLUE),
            _capture("FOB Reaper", Player.RED),
        ],
        rescues=["unit-1", "unit-2"],
    )
    sitrep = Sitrep.from_debriefing(debrief, turn=7, day=date(1988, 6, 6))
    assert sitrep.turn == 7
    assert sitrep.friendly == SideLosses(2, 5, 1)
    assert sitrep.enemy == SideLosses(4, 11, 2)
    assert sitrep.captured == ["Al Dhafra"]  # BLUE took it
    assert sitrep.lost == ["FOB Reaper"]  # RED took it from the player
    assert sitrep.pilots_recovered == 2
    assert not sitrep.is_empty


def test_quiet_turn_is_empty() -> None:
    sitrep = Sitrep.from_debriefing(
        _debrief(_loss(0, 0, 0), _loss(0, 0, 0)), turn=3, day=date(2000, 1, 1)
    )
    assert sitrep.is_empty


def test_has_news_is_the_app_surface_gate() -> None:
    # The web LAST TURN panel and the Qt debrief box gate on `has_news`; the
    # 2026-07-18 flown turn crashed the debrief window because the SITREP-parity
    # commit referenced it without defining it. Pin it as the inverse of the
    # kneeboard band's quiet-turn gate so every §29 surface agrees.
    quiet = Sitrep.from_debriefing(
        _debrief(_loss(0, 0, 0), _loss(0, 0, 0)), turn=3, day=date(2000, 1, 1)
    )
    assert not quiet.has_news
    newsy = Sitrep.from_debriefing(
        _debrief(_loss(1, 0, 0), _loss(0, 0, 0)), turn=3, day=date(2000, 1, 1)
    )
    assert newsy.has_news
    assert newsy.has_news == (not newsy.is_empty)


def test_kneeboard_lines_formatting_and_plurals() -> None:
    sitrep = Sitrep(
        turn=7,
        day=date(1988, 6, 6),
        friendly=SideLosses(2, 5, 1),
        enemy=SideLosses(4, 11, 0),
        captured=["Al Dhafra"],
        lost=[],
        pilots_recovered=1,
    )
    lines = sitrep.kneeboard_lines()
    assert lines[0] == "Friendly losses: 2 air, 5 armor, 1 site"  # singular site
    assert lines[1] == "Enemy (claimed): 4 air, 11 armor"  # 0 sites omitted
    assert "Captured: Al Dhafra" in lines
    assert "Recovered 1 downed pilot" in lines  # singular
    assert not any(line.startswith("Lost:") for line in lines)


def test_kneeboard_lines_render_held_pows() -> None:
    sitrep = Sitrep(
        turn=7,
        day=date(1968, 6, 6),
        friendly=SideLosses(1, 0, 0),
        enemy=SideLosses(0, 0, 0),
        captured=[],
        lost=[],
        pilots_recovered=0,
        pows_held=["Capt Mitchell — held at Mozdok (held)"],
    )
    lines = sitrep.kneeboard_lines()
    assert "POW: Capt Mitchell — held at Mozdok (held)" in lines
    assert not sitrep.is_empty  # a held POW is news even with no losses


def test_sitrep_page_renders_standalone(tmp_path: Path) -> None:
    """The SITREP renders on its own kneeboard page (§29): a busy turn's
    POW/MIA list clipped at the Mission Info page edge (flown 2026-07-19), so
    the news moved to a dedicated page with room for the full list."""
    from game.missiongenerator.kneeboard import SitrepPage

    sitrep = Sitrep(
        turn=1,
        day=date(1991, 1, 17),
        friendly=SideLosses(10, 1, 0),
        enemy=SideLosses(21, 5, 18),
        captured=[],
        lost=[],
        pilots_recovered=0,
        pows_held=["Bertrand Lambert — held at Al-Taquddum Airport (held)"],
        pilots_mia=[
            "Corey Johnson — evading near H-2 Airbase (downed this turn)",
            "Garry Stevens — evading near Al-Asad Airbase (downed this turn)",
        ],
    )
    page = tmp_path / "sitrep.png"
    SitrepPage(sitrep, dark_kneeboard=False).write(page)
    assert page.exists() and page.stat().st_size > 0


def test_a_held_pow_alone_is_not_a_quiet_turn() -> None:
    sitrep = Sitrep(
        turn=2,
        day=date(1968, 1, 1),
        friendly=SideLosses(0, 0, 0),
        enemy=SideLosses(0, 0, 0),
        captured=[],
        lost=[],
        pilots_recovered=0,
        pows_held=["A — held at B (2 turns left)"],
    )
    assert not sitrep.is_empty


def test_c2_status_renders_but_rides_along_with_real_news() -> None:
    # A degraded enemy C2 shows on the band...
    sitrep = Sitrep(
        turn=5,
        day=date(1988, 6, 6),
        friendly=SideLosses(1, 0, 0),
        enemy=SideLosses(0, 0, 1),
        captured=[],
        lost=[],
        pilots_recovered=0,
        red_c2_status="1/3 command posts operational",
    )
    assert (
        "Enemy C2 degraded (claimed): 1/3 command posts operational"
        in sitrep.kneeboard_lines()
    )
    # ...but like the will band, it never forces a SITREP on an otherwise-quiet turn.
    quiet = Sitrep(
        turn=5,
        day=date(1988, 6, 6),
        friendly=SideLosses(0, 0, 0),
        enemy=SideLosses(0, 0, 0),
        captured=[],
        lost=[],
        pilots_recovered=0,
        red_c2_status="1/3 command posts operational",
    )
    assert quiet.is_empty


def test_loss_phrase_handles_none_and_site_plural() -> None:
    none_side = Sitrep(
        1, date(2000, 1, 1), SideLosses(0, 0, 0), SideLosses(0, 0, 2), [], [], 0
    )
    lines = none_side.kneeboard_lines()
    assert lines[0] == "Friendly losses: none"
    assert lines[1] == "Enemy (claimed): 2 sites"  # plural


def test_sitrep_for_kneeboard_gating() -> None:
    sitrep = Sitrep(
        7, date(1988, 6, 6), SideLosses(2, 0, 0), SideLosses(0, 0, 0), [], [], 0
    )
    empty = Sitrep(
        7, date(1988, 6, 6), SideLosses(0, 0, 0), SideLosses(0, 0, 0), [], [], 0
    )
    assert sitrep_for_kneeboard(sitrep, enabled=False) is None  # toggle off
    assert sitrep_for_kneeboard(None, enabled=True) is None  # turn 1 / no prior
    assert sitrep_for_kneeboard(empty, enabled=True) is None  # quiet turn
    assert sitrep_for_kneeboard(sitrep, enabled=True) is sitrep  # shown
