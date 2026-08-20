"""The What's New feed (§92) must load, order, and degrade safely.

The window it backs is reachable with no game open, so the load path is held to
"never raises": a missing, unreadable, or half-written data file costs an empty
window and nothing else. The ordering test pins the property the file's whole
existence rests on -- the changelog cannot answer "what changed lately" because
it is grouped by area, so this file is authored newest-first and must stay that
way.
"""

from __future__ import annotations

from pathlib import Path

from game.fourteenth.whatsnew import (
    DEFAULT_LIMIT,
    WHATS_NEW_FILE,
    load_whats_new,
)


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "whatsnew.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_the_shipped_file_loads_and_every_entry_is_complete() -> None:
    entries = load_whats_new()
    assert entries, f"{WHATS_NEW_FILE} should ship a non-empty list"
    assert len(entries) <= DEFAULT_LIMIT
    for entry in entries:
        assert entry.date and entry.title and entry.change and entry.watch


def test_the_shipped_file_is_newest_first() -> None:
    dates = [entry.date for entry in load_whats_new()]
    assert dates == sorted(dates, reverse=True)


def test_same_day_entries_keep_the_order_the_file_wrote_them(tmp_path: Path) -> None:
    """The sort is stable, so a day's changes read in the order they were added
    rather than being shuffled by an unstable tiebreak."""
    path = _write(
        tmp_path,
        "entries:\n"
        + "".join(
            f"  - date: 2026-08-19\n"
            f"    title: t{i}\n"
            f"    change: c\n"
            f"    watch: w\n"
            for i in range(4)
        )
        + "  - date: 2026-08-20\n    title: newer\n    change: c\n    watch: w\n",
    )
    titles = [entry.title for entry in load_whats_new(path=path)]
    assert titles == ["newer", "t0", "t1", "t2", "t3"]


def test_limit_caps_the_list(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "entries:\n"
        + "".join(
            f"  - date: 2026-08-{20 - i:02d}\n"
            f"    title: t{i}\n"
            f"    change: c\n"
            f"    watch: w\n"
            for i in range(6)
        ),
    )
    assert len(load_whats_new(limit=2, path=path)) == 2
    assert len(load_whats_new(limit=99, path=path)) == 6


def test_a_missing_file_is_an_empty_list_not_a_crash(tmp_path: Path) -> None:
    assert load_whats_new(path=tmp_path / "absent.yaml") == []


def test_malformed_yaml_is_an_empty_list_not_a_crash(tmp_path: Path) -> None:
    assert load_whats_new(path=_write(tmp_path, "entries: [oh: no: yes")) == []


def test_a_document_without_entries_is_an_empty_list(tmp_path: Path) -> None:
    assert load_whats_new(path=_write(tmp_path, "something: else\n")) == []
    assert load_whats_new(path=_write(tmp_path, "- just\n- a\n- list\n")) == []


def test_one_bad_entry_is_skipped_and_the_rest_survive(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "entries:\n"
        "  - date: 2026-08-19\n"
        "    title: good\n"
        "    change: c\n"
        "    watch: w\n"
        "  - date: 2026-08-18\n"
        "    title: no watch line\n"
        "    change: c\n"
        "  - just a string\n",
    )
    assert [entry.title for entry in load_whats_new(path=path)] == ["good"]


def test_optional_fields_normalise(tmp_path: Path) -> None:
    """An unquoted PR number is an int in YAML, and a blank row is not a row."""
    path = _write(
        tmp_path,
        "entries:\n"
        "  - date: 2026-08-19\n"
        "    title: t\n"
        "    change: c\n"
        "    watch: w\n"
        "    pr: 906\n"
        "    row: '   '\n",
    )
    (entry,) = load_whats_new(path=path)
    assert entry.pr == "906"
    assert entry.row is None
