"""Dated national postures (§96): what each country flew, and where it stood.

Reads ``resources/borders/national_postures.yaml`` — 47 countries, both blocs,
244 dated ranges in five buckets. Sources and the reasoning behind every range
are in ``docs/dev/design/414th-national-postures-notes.md``.

**What this decides today: the airframe.** ``aircraft_for`` is what lets a border
be drawn from terrain data alone — the campaign names no fighter and the era
picks one, so the same file is right in 1975 and 2025. Nothing else can supply
it: a country with no control points has no faction to borrow a jet from.

**What it no longer decides: whether you may transit.** That was its original
job and it was dropped on 2026-08-26 (DM call) in favour of deriving consent
from the airbases inside a country's border — see
``NeutralBorderZone.permits``. The table made consent a fact about the calendar
rather than about the campaign in front of you: it reads Sweden and Finland
``closed`` in 1983, while on the Kola map both sides fly combat sorties off
their runways, and it cannot see a base change hands mid-campaign.

The posture data is kept, not deleted, and ``posture_for`` still reads it — it
is 244 researched ranges that took a session to assemble, and the question it
answers ("whose side was this country on, that year") is a real one that a
future feature may want. It just is not the question §96 asks.

An uncovered date, country or bloc is ``closed``: never invent coverage.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any, Optional

import yaml

#: Relative to the install root, like every other resource read.
POSTURES_FILE = Path("resources/borders/national_postures.yaml")

US_LED = "toward_us_led"
RU_LED = "toward_ru_led"

#: An uncovered date, an unknown country, or an unreadable file.
DEFAULT_POSTURE = "closed"

_cache: Optional[dict[str, Any]] = None


def _sort_key(token: Any) -> tuple[int, int]:
    """A ``YYYY`` / ``YYYY-MM`` / ``present`` bound as a comparable pair."""
    text = str(token)
    if text == "present":
        return (9999, 12)
    parts = text.split("-")
    year = int(parts[0])
    month = int(parts[1]) if len(parts) > 1 else 1
    return (year, month)


def load_postures(path: Optional[Path] = None) -> dict[str, Any]:
    """The posture table, cached. Never raises — a bad file costs the feature."""
    global _cache
    if path is None and _cache is not None:
        return _cache
    target = path or POSTURES_FILE
    data: dict[str, Any] = {}
    try:
        raw = yaml.safe_load(target.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("countries"), dict):
            data = raw["countries"]
        else:
            logging.warning("National postures: %s has no countries map.", target)
    except FileNotFoundError:
        logging.warning("National postures: %s not found.", target)
    except Exception:
        logging.warning("National postures: %s unreadable.", target, exc_info=True)
    if path is None:
        _cache = data
    return data


def posture_for(
    country: str,
    on: date,
    bloc: str,
    postures: Optional[dict[str, Any]] = None,
) -> str:
    """This country's posture toward ``bloc`` on ``on``.

    ``closed`` whenever the country, the bloc or the date is not covered.
    """
    table = load_postures() if postures is None else postures
    ranges = (table.get(country) or {}).get(bloc)
    if not ranges:
        return DEFAULT_POSTURE
    when = (on.year, on.month)
    for entry in ranges:
        try:
            if _sort_key(entry["from"]) <= when < _sort_key(entry["to"]):
                return str(entry["posture"])
        except (KeyError, TypeError, ValueError):
            continue
    return DEFAULT_POSTURE


def aircraft_for(
    country: str,
    on: date,
    postures: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """The interceptor this country flew on ``on``, or None if unrecorded.

    Lets a border be drawn from terrain data alone: the campaign states no
    airframe, and the era picks one. Vanilla pydcs ids only.
    """
    table = load_postures() if postures is None else postures
    ranges = (table.get(country) or {}).get("aircraft")
    if not ranges:
        return None
    when = (on.year, on.month)
    for entry in ranges:
        try:
            if _sort_key(entry["from"]) <= when < _sort_key(entry["to"]):
                return str(entry["id"])
        except (KeyError, TypeError, ValueError):
            continue
    return None
