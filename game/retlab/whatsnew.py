"""What's New (§92) — the recent player-visible changes, read in the app.

The changelog cannot answer "what changed lately", because it is grouped by area
(``[Campaign]`` / ``[Mission Generation]`` / ``[UI]``) rather than ordered by
date: two changes landing the same afternoon get written 70 lines apart. So the
recent-changes list is its own small curated file, ``resources/whatsnew.yaml``,
authored newest-first.

It also carries something the changelog deliberately does not: a ``watch`` line
per entry saying what to look for in the next mission. That is the point of the
window — the fork's features are mostly runtime behaviour that CI cannot
exercise, so knowing what changed is only useful alongside knowing how to see it.
``row`` links the in-game-pass checklist row that owns the verdict.

Nothing here may raise. It backs a toolbar button that is available with no game
loaded, and a malformed data file must cost an empty window, never a crash.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

#: The curated source, relative to the install root like every other resource
#: read (``game.version`` reads ``resources/buildnumber`` the same way).
WHATS_NEW_FILE = Path("resources/whatsnew.yaml")

#: How many entries the window shows. The file may hold more; the tail is
#: history, not something anyone scrolls to.
DEFAULT_LIMIT = 10

_REQUIRED_FIELDS = ("date", "title", "change", "watch")


@dataclass(frozen=True)
class WhatsNewEntry:
    """One recent change, as the What's New window renders it."""

    date: str
    title: str
    change: str
    watch: str
    #: In-game-pass checklist row that owns this change's verdict, e.g. "B39".
    row: Optional[str] = None
    #: Pull request number, without the "#".
    pr: Optional[str] = None


def load_whats_new(
    limit: int = DEFAULT_LIMIT, path: Optional[Path] = None
) -> list[WhatsNewEntry]:
    """The most recent entries, newest first.

    Returns an empty list — never raises — when the file is missing, unreadable,
    or malformed. A single bad entry is skipped rather than discarding the file.
    """
    source = path or WHATS_NEW_FILE
    raw = _read(source)
    if raw is None:
        return []
    entries = [entry for entry in (_entry_from(item, source) for item in raw) if entry]
    # Stable sort, so entries sharing a date keep the order the file wrote them.
    entries.sort(key=lambda entry: entry.date, reverse=True)
    if limit >= 0:
        return entries[:limit]
    return entries


def _read(source: Path) -> Optional[list[Any]]:
    if not source.is_file():
        logging.info("What's New: %s is not present; nothing to show", source)
        return None
    try:
        document = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        logging.exception("What's New: could not read %s", source)
        return None
    if not isinstance(document, dict):
        logging.warning("What's New: %s has no top-level mapping", source)
        return None
    entries = document.get("entries")
    if not isinstance(entries, list):
        logging.warning("What's New: %s has no 'entries' list", source)
        return None
    return entries


def _entry_from(item: Any, source: Path) -> Optional[WhatsNewEntry]:
    if not isinstance(item, dict):
        logging.warning("What's New: skipping a non-mapping entry in %s", source)
        return None
    values = {}
    for field in _REQUIRED_FIELDS:
        value = item.get(field)
        # A YAML date scalar arrives as datetime.date, not str; str() it rather
        # than demanding the author quote every date.
        text = str(value).strip() if value is not None else ""
        if not text:
            logging.warning(
                "What's New: skipping an entry in %s with no '%s'", source, field
            )
            return None
        values[field] = text
    return WhatsNewEntry(
        date=values["date"],
        title=values["title"],
        change=values["change"],
        watch=values["watch"],
        row=_optional(item.get("row")),
        pr=_optional(item.get("pr")),
    )


def _optional(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
