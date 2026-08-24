"""The kneeboard's one bullseye row (§95).

The BLUF's second BULLSEYE line was struck as a duplicate, so this row carries
everything: where the bullseye is, its coordinates, and the rare turn it moved.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from game.missiongenerator.kneeboard import BriefingPage


def _page(anchor: str | None, moved: bool = False) -> BriefingPage:
    page = BriefingPage.__new__(BriefingPage)
    bullseye = MagicMock()
    bullseye.position.latlng.return_value.format_dms.return_value = "N31 E035"
    page.bullseye = bullseye
    page.bullseye_anchor = anchor
    page.bullseye_moved = moved
    return page


def test_the_line_names_the_place_before_the_coordinates() -> None:
    assert _page("King Abdullah II")._bullseye_line() == (
        "Bullseye: King Abdullah II — N31 E035"
    )


def test_an_unnamed_anchor_falls_back_to_coordinates_alone() -> None:
    assert _page(None)._bullseye_line() == "Bullseye: N31 E035"


def test_a_move_is_called_out_on_the_same_line() -> None:
    line = _page("FOB Agrihan", moved=True)._bullseye_line()
    assert line.startswith("Bullseye: FOB Agrihan — N31 E035")
    assert "** MOVED THIS TURN **" in line
