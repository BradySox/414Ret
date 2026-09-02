"""The session-start board must agree with the documents it summarises.

Everything here is a defect that actually shipped. The board is read at the top of
every session and is the only surface that routes cockpit time, so a board that
lies costs flights: six rows closed with a marker the parser did not know were
briefed as outstanding work for two weeks, and two crossed-off fly-card items were
briefed as live for two days after they were closed.

The rules mirror `.claude/hooks/session-start.sh`. Keep the two in step.
"""

from __future__ import annotations

import re
from pathlib import Path

CHECKLIST = Path("docs/dev/414th-ingame-pass-checklist.md")
WATCH = Path("docs/dev/flycards/WATCH.md")
LOCAL = Path("docs/dev/flycards/LOCAL.md")

#: A row's status is the first `<symbol> <WORD>` pair on its heading line. Pairing
#: the symbol with the word is what survives someone inventing a marker; matching
#: whole fixed strings is what let `✅ CLOSED` fall through to the "(was ☐ UNTESTED"
#: that every re-verified row quotes.
STATUS = re.compile(
    r"(?P<symbol>[\u2610\u2611\u2612\u2298\u2716\u2717\u25d0\u2705]) "
    r"(?P<word>VERIFIED|UNTESTED|PARTIAL|REGRESSED|RETIRED|REMOVED|CLOSED)"
)

#: Row ids are a letter block plus a number: B6, G19, S2, C9. The `### Session 1 —`
#: headings under "Drain order" are prose, not rows, and carry no status.
ROW_HEADING = re.compile(r"^### (?P<row>[A-Z]+[0-9]+) ")

#: A card section holding history rather than work. Matches the hook's list.
DEAD_SECTION = re.compile(
    r"^## *(Done|Archive|Archived|Closed|Dropped|Superseded|Parking)", re.I
)

#: An item crossed off in place still says so in its own heading.
CLOSED_ITEM = re.compile(r"CLOSED|OFF THE CARD|DONE|VERIFIED")


def _legend() -> dict[str, str]:
    """The `Status legend` table: symbol -> word.

    Scanned line by line and stopped at the section's closing rule. Slicing to the
    next ``---`` instead lands on the table's own ``|---|---|`` separator, which
    yields an empty legend and makes every check below pass vacuously.
    """
    lines = CHECKLIST.read_text(encoding="utf-8").splitlines()
    start = next(
        i for i, line in enumerate(lines) if line.startswith("## Status legend")
    )
    marks = {}
    for line in lines[start + 1 :]:
        if line.strip() == "---":
            break
        found = STATUS.search(line)
        if found:
            marks[found["symbol"]] = found["word"]
    assert marks, "Status legend table parsed empty"
    return marks


def _row_statuses() -> dict[str, str]:
    """Row id -> status word, taken from the `### ` headings."""
    statuses = {}
    for line in CHECKLIST.read_text(encoding="utf-8").splitlines():
        heading = ROW_HEADING.match(line)
        if not heading:
            continue
        found = STATUS.search(line)
        if found:
            statuses[heading["row"]] = found["word"]
    return statuses


def _live_card_items(path: Path) -> list[str]:
    """The `### ` items a reader is actually being asked to do."""
    items: list[str] = []
    live = True
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            live = not DEAD_SECTION.match(line)
        elif line.startswith("### ") and live:
            items.append(line[4:])
    return items


def test_no_two_rows_share_an_id() -> None:
    """A long-lived branch and main allocate row ids from the same end.

    Four collisions on the §96 branch alone -- B100/B101, then B106/B107, then
    B110/B111 twice. `_row_statuses()` keys by id, so a duplicate silently
    overwrites its twin and the board under-reports outstanding work; the
    count test catches that only indirectly, and only when the two rows differ
    in status. The fourth collision landed on a row already marked VERIFIED,
    so being closed is no protection either.
    """
    from collections import Counter

    ids = [
        heading["row"]
        for line in CHECKLIST.read_text(encoding="utf-8").splitlines()
        if (heading := ROW_HEADING.match(line))
    ]
    repeated = sorted(row for row, n in Counter(ids).items() if n > 1)
    assert not repeated, (
        f"row id(s) used twice: {', '.join(repeated)}. Renumber YOUR rows to "
        "the next free id, never main's, and update the features doc, the "
        "design note and every `row:` in resources/whatsnew.yaml."
    )


def test_every_row_heading_carries_a_legend_marker() -> None:
    # A row whose marker is not in the legend is invisible to the board: it is
    # dropped from the counts, and the parser falls through to whatever marker the
    # row's prose quotes next -- which is how a CLOSED row gets briefed as work.
    legend = _legend()
    unmarked = []
    unknown = []
    for line in CHECKLIST.read_text(encoding="utf-8").splitlines():
        heading = ROW_HEADING.match(line)
        if not heading:
            continue
        found = STATUS.search(line)
        if not found:
            unmarked.append(heading["row"])
        elif legend.get(found["symbol"]) != found["word"]:
            unknown.append(f"{heading['row']}: {found['symbol']} {found['word']}")
    assert not unmarked, f"checklist row heading(s) with no status marker: {unmarked}"
    assert not unknown, (
        "checklist row heading(s) using a symbol/word pair the Status legend does "
        f"not list: {unknown}"
    )


def test_at_a_glance_table_agrees_with_the_row_headings() -> None:
    # The summary table is what a reader skims; the row heading is the record. They
    # drifted on four rows, two of them reporting a closed feature as outstanding.
    legend = _legend()
    rows = _row_statuses()
    drift = []
    for line in CHECKLIST.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) != 6 or not re.fullmatch(r"[A-Z]+[0-9]+", cells[1]):
            continue
        row, mark = cells[1], cells[4]
        if row not in rows or mark not in legend:
            continue
        if legend[mark] != rows[row]:
            drift.append(f"{row}: table {legend[mark]} vs heading {rows[row]}")
    assert not drift, f"at-a-glance table disagrees with the row heading: {drift}"


def test_outstanding_count_in_the_table_header_is_right() -> None:
    # The header states the number the board also computes. When they disagree the
    # reader has no way to know which one is stale.
    rows = _row_statuses()
    open_now = sum(
        1 for w in rows.values() if w in {"UNTESTED", "PARTIAL", "REGRESSED"}
    )
    text = CHECKLIST.read_text(encoding="utf-8")
    header = re.search(r"^(\d+) rows need a live pass", text, re.M)
    assert header, "the at-a-glance header no longer states an outstanding count"
    stated = int(header.group(1))
    assert stated == open_now, (
        f"the at-a-glance header says {stated} rows need a live pass, but the row "
        f"headings count {open_now}"
    )


def test_fly_cards_hold_no_closed_items_in_their_live_section() -> None:
    # `G29` and the `B25` follow-on were both crossed off on 2026-08-20 and both kept
    # being briefed, because the hook read every heading in the file rather than only
    # the live section. Closing an item has to actually take it off the board.
    for path in (WATCH, LOCAL):
        stale = [i for i in _live_card_items(path) if CLOSED_ITEM.search(i)]
        assert not stale, f"{path} briefs closed item(s) as live work: {stale}"


def test_fly_card_items_name_a_checklist_row_that_is_still_open() -> None:
    # Seeding a card from a stale checklist inherits the staleness: the parking lot
    # carried `Q3` after it was VERIFIED, and a loadout watch for RETIRED `B42`.
    rows = _row_statuses()
    for path in (WATCH, LOCAL):
        for item in _live_card_items(path):
            ids = re.findall(r"`([A-Z]+[0-9]+)`", item)
            assert ids, f"{path} item names no checklist row: {item}"
            for row in ids:
                assert row in rows, f"{path} names unknown checklist row {row}"
                assert rows[row] in {
                    "UNTESTED",
                    "PARTIAL",
                    "REGRESSED",
                }, f"{path} asks for {row}, which is already {rows[row]}"


def test_watch_card_respects_its_five_slot_cap() -> None:
    # "A watch list of twenty items is a watch list of zero." The cap is the card's
    # own rule and the reason it gets read at all.
    items = _live_card_items(WATCH)
    assert len(items) <= 5, f"WATCH.md has {len(items)} items, cap is 5"
