"""Dated national postures (§96): who lets whom fly through, and when.

Reads ``resources/borders/national_postures.yaml`` — 47 countries, both blocs,
dated ranges in five buckets — and answers the one question the border feature
asks: *at this campaign's date, does this country permit this side's aircraft to
transit its airspace?*

Sources and the reasoning behind every range are in
``docs/dev/design/414th-national-postures-notes.md``. The table is data; this
module is the only place that interprets it.

Three things the table deliberately does not decide, resolved here:

* **Which bloc a coalition belongs to.** Taken from the faction's own country
  looked up in the table: the bloc it is most favourably disposed toward at that
  date is its bloc. USA resolves us-led, Russia ru-led, and a faction whose
  country is not in the table (CJTF, Insurgents, a generic "Bluefor Modern")
  falls back to blue=us-led / red=ru-led, which is every fork campaign.
* **An uncovered date is ``closed``** — the safe default for a border feature is
  that it defends. Never invent coverage.
* **The collapse to a boolean**: ``allied`` and ``permissive`` permit transit;
  ``contested``, ``closed`` and ``hostile`` do not. The five buckets are kept in
  the data because the split will matter later (contested = risky transit,
  hostile ≠ closed for basing), but overflight is binary today.
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

#: Buckets whose meaning is "this side's aircraft may transit".
OVERFLIGHT_BUCKETS = frozenset({"allied", "permissive"})

#: An uncovered date, an unknown country, or an unreadable file.
DEFAULT_POSTURE = "closed"

#: How favourably a bucket reads, for deciding which bloc a country belongs to.
_FAVOURABILITY = {
    "allied": 4,
    "permissive": 3,
    "contested": 2,
    "closed": 1,
    "hostile": 0,
}

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


def permits_overflight(
    country: str,
    on: date,
    bloc: str,
    postures: Optional[dict[str, Any]] = None,
) -> bool:
    return posture_for(country, on, bloc, postures) in OVERFLIGHT_BUCKETS


def bloc_for_country(
    country: str,
    on: date,
    postures: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """Which bloc this country belongs to, or None if the table cannot say.

    A country's bloc is the one it is most favourably disposed toward: the USA
    reads allied toward the US-led bloc and closed toward the other, Russia the
    mirror. A tie means the table has no opinion.
    """
    table = load_postures() if postures is None else postures
    if country not in table:
        return None
    us = _FAVOURABILITY.get(posture_for(country, on, US_LED, table), 1)
    ru = _FAVOURABILITY.get(posture_for(country, on, RU_LED, table), 1)
    if us == ru:
        return None
    return US_LED if us > ru else RU_LED


def bloc_for_faction(faction: Any, is_blue: bool, on: date) -> str:
    """The bloc a coalition fights for.

    Derived from its faction's own country where the table knows it; otherwise
    blue is the US-led side and red the Soviet/Russian one, which is true of
    every campaign this fork ships.
    """
    name = None
    try:
        country = getattr(faction, "country", None)
        name = getattr(country, "name", None) or (
            str(country) if country is not None else None
        )
    except Exception:  # a duck-typed faction in a test
        name = None
    if name:
        bloc = bloc_for_country(str(name), on)
        if bloc is not None:
            return bloc
    return US_LED if is_blue else RU_LED
