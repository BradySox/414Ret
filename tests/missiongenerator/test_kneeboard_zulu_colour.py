"""The Viper's two times are told apart by colour, not just by their suffixes.

``17:28L 14:28Z`` puts both clocks in one cell. The letters distinguish them on a
careful read; the colour does it at a glance, and the local figure keeps the
page's own foreground because it is the primary time.

The alignment invariant matters as much as the colour: the highlighted path draws
the table in segments rather than one block, so it has to leave the cursor exactly
where the plain path would or everything below the flight plan shifts.
"""

from __future__ import annotations

from typing import Any

from game.missiongenerator.kneeboard import ZULU_CELL_TOKEN, KneeboardPageWriter

HEADERS = ["#", "Time"]
ROWS = [["0", "17:28L 14:28Z"], ["1", "17:33L 14:33Z"]]


def _colours(writer: KneeboardPageWriter) -> set[Any]:
    return set(writer.image.convert("RGB").getcolors(maxcolors=1 << 20) or [])


def _has(writer: KneeboardPageWriter, colour: Any) -> bool:
    return any(px == colour for _count, px in _colours(writer))


def test_the_token_is_the_cell_form_not_the_prose_form() -> None:
    # The BLUF's "17:53:16 (14:53:16Z)" is parenthesised and reads apart already;
    # matching inside it would colour the "53:16Z" tail of one number.
    assert ZULU_CELL_TOKEN.findall("17:28L 14:28Z") == ["14:28Z"]
    assert ZULU_CELL_TOKEN.findall("17:53:16 (14:53:16Z)") == []


def test_a_highlighted_table_puts_the_zulu_figure_in_the_nav_colour() -> None:
    writer = KneeboardPageWriter(dark_theme=False)
    writer.table(
        ROWS, headers=HEADERS, highlight=ZULU_CELL_TOKEN, highlight_fill=writer.col_nav
    )
    assert _has(writer, writer.col_nav)


def test_a_plain_table_stays_one_colour() -> None:
    writer = KneeboardPageWriter(dark_theme=False)
    writer.table(ROWS, headers=HEADERS)
    assert not _has(writer, writer.col_nav)


def test_a_local_only_card_is_never_highlighted() -> None:
    # BriefingPage passes highlight=None when the airframe does not ask for Zulu,
    # and a None pattern must take the plain path rather than colour nothing.
    writer = KneeboardPageWriter(dark_theme=False)
    writer.table([["0", "17:28:52"]], headers=HEADERS, highlight=None)
    assert not _has(writer, writer.col_nav)


def test_highlighting_does_not_move_the_cursor() -> None:
    # The whole page below the flight plan is positioned off this.
    plain = KneeboardPageWriter(dark_theme=False)
    plain.table(ROWS, headers=HEADERS)
    coloured = KneeboardPageWriter(dark_theme=False)
    coloured.table(
        ROWS,
        headers=HEADERS,
        highlight=ZULU_CELL_TOKEN,
        highlight_fill=coloured.col_nav,
    )
    assert coloured.y == plain.y
