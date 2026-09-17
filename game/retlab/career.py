"""Pilot career logbook (§96) — ranks, awards and the career view.

Retribution already knew who a pilot was, whether they were alive, and how many
times the ATO had put them in a seat. It never knew what any of them had *done*:
`PilotRecord` was one integer. §91 records what every aircraft did in a mission
and then throws it away at end of turn.

This module is the ledger between the two. It owns nothing about a mission —
`fold_sortie_records` is called once when results are committed, and everything
here is a pure read over the accumulated record.

Ranks and awards are data (`resources/pilot_career.yaml`), not code, because the
fork ships campaigns spanning many air forces and seventy years. A ladder
hard-coded to one service would be wrong for most of them.

Records, never rewards. Nothing here unlocks an aircraft, changes availability,
or gates a mission. The career is a read-out of what happened.

Nothing in this module raises. It backs a dialog and a per-turn fold, and a
malformed data file must cost an empty award list, never a turn.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from game.squadrons.pilot import PilotRecord
    from game.sortierecord import SortieRecord

#: The curated source, relative to the install root like every other resource
#: read (§92 reads `resources/whatsnew.yaml` the same way).
CAREER_FILE = Path("resources/pilot_career.yaml")

#: Fields a `requires:` block may name. A closed list rather than "any attribute"
#: so a typo is caught and logged instead of silently never being met, and so
#: adding a private field to PilotRecord cannot accidentally become authorable.
REQUIREMENT_FIELDS = frozenset(
    {
        "missions_flown",
        "sorties",
        "combat_sorties",
        "flight_seconds",
        "flight_hours",
        "shots",
        "hits",
        "air_kills",
        "ground_kills",
        "naval_kills",
        "kills",
        "ejections",
    }
)


@dataclass(frozen=True)
class RankGrade:
    """One rung of a rank ladder."""

    key: str
    name: str
    requires: Mapping[str, float]


@dataclass(frozen=True)
class RankLadder:
    """A service's rank ladder, lowest grade first.

    ``countries`` are DCS country names. An empty tuple marks the fallback
    ladder, used by every squadron no ladder claims.
    """

    key: str
    countries: tuple[str, ...]
    grades: tuple[RankGrade, ...]


@dataclass(frozen=True)
class Award:
    key: str
    name: str
    description: str
    requires: Mapping[str, float]


@dataclass(frozen=True)
class CareerData:
    ladders: tuple[RankLadder, ...]
    awards: tuple[Award, ...]

    def ladder_for(self, country: Optional[str]) -> Optional[RankLadder]:
        """The ladder a squadron of this country ranks against.

        First ladder naming the country, else the fallback, else nothing.
        """
        if country:
            for ladder in self.ladders:
                if country in ladder.countries:
                    return ladder
        for ladder in self.ladders:
            if not ladder.countries:
                return ladder
        return None

    def award(self, key: str) -> Optional[Award]:
        for award in self.awards:
            if award.key == key:
                return award
        return None


_EMPTY = CareerData(ladders=(), awards=())

#: Parsed once. The file ships with the build and cannot change under a running
#: app, and the logbook dialog would otherwise re-read it per pilot.
_cache: Optional[CareerData] = None


def _requirements_from(raw: Any, where: str) -> Optional[Mapping[str, float]]:
    """A `requires:` block, or None if it names something unauthorable.

    Rejected rather than dropped: an entry whose requirement was silently
    discarded would be earned by everyone on their first sortie.
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        logging.warning("Pilot career: %s has a non-mapping requires block", where)
        return None
    parsed: dict[str, float] = {}
    for name, value in raw.items():
        key = str(name)
        if key not in REQUIREMENT_FIELDS:
            logging.warning("Pilot career: %s requires unknown field %r", where, key)
            return None
        try:
            parsed[key] = float(value)
        except (TypeError, ValueError):
            logging.warning("Pilot career: %s requires non-numeric %r", where, key)
            return None
    return parsed


def _ladder_from(raw: Any, index: int) -> Optional[RankLadder]:
    if not isinstance(raw, dict):
        return None
    key = str(raw.get("ladder") or f"ladder-{index}")
    countries = raw.get("countries") or []
    if not isinstance(countries, list):
        countries = []
    grades: list[RankGrade] = []
    for entry in raw.get("grades") or []:
        if not isinstance(entry, dict):
            continue
        grade_key = entry.get("key")
        name = entry.get("name")
        if not grade_key or not name:
            logging.warning("Pilot career: ladder %s has a grade with no key/name", key)
            continue
        requires = _requirements_from(entry.get("requires"), f"grade {grade_key}")
        if requires is None:
            continue
        grades.append(RankGrade(str(grade_key), str(name), requires))
    if not grades:
        return None
    return RankLadder(key, tuple(str(c) for c in countries), tuple(grades))


def _award_from(raw: Any) -> Optional[Award]:
    if not isinstance(raw, dict):
        return None
    key = raw.get("key")
    name = raw.get("name")
    if not key or not name:
        logging.warning("Pilot career: award with no key/name")
        return None
    requires = _requirements_from(raw.get("requires"), f"award {key}")
    if requires is None:
        return None
    return Award(str(key), str(name), str(raw.get("description") or ""), requires)


def load_career_data(path: Optional[Path] = None) -> CareerData:
    """Ranks and awards from the data file.

    Returns empty data — never raises — when the file is missing, unreadable or
    malformed. A single bad entry is skipped rather than discarding the file.
    """
    global _cache
    if path is None and _cache is not None:
        return _cache
    source = path or CAREER_FILE
    try:
        raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logging.info("No %s; the pilot logbook has no ranks or awards", source)
        raw = None
    except (OSError, yaml.YAMLError):
        logging.exception("Could not read %s", source)
        raw = None

    data = _EMPTY
    if isinstance(raw, dict):
        ladders = [
            ladder
            for index, entry in enumerate(raw.get("ranks") or [])
            if (ladder := _ladder_from(entry, index)) is not None
        ]
        awards = [
            award
            for entry in raw.get("awards") or []
            if (award := _award_from(entry)) is not None
        ]
        data = CareerData(tuple(ladders), tuple(awards))

    if path is None:
        _cache = data
    return data


def _value_of(record: "PilotRecord", field: str) -> float:
    value = getattr(record, field, 0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _meets(record: "PilotRecord", requires: Mapping[str, float]) -> bool:
    return all(_value_of(record, field) >= need for field, need in requires.items())


def rank_for(
    record: "PilotRecord",
    country: Optional[str] = None,
    data: Optional[CareerData] = None,
) -> Optional[str]:
    """The pilot's rank name: the highest grade whose requirements are met.

    Walks the whole ladder rather than stopping at the first unmet grade, so a
    ladder that mixes requirement fields cannot strand a pilot on a lower rung.
    """
    career = data if data is not None else load_career_data()
    ladder = career.ladder_for(country)
    if ladder is None:
        return None
    held: Optional[str] = None
    for grade in ladder.grades:
        if _meets(record, grade.requires):
            held = grade.name
    return held


def awards_held(
    record: "PilotRecord", data: Optional[CareerData] = None
) -> list[Award]:
    """The awards the record carries, in the order they were earned.

    A key with no matching entry is dropped: an award may be renamed or removed
    from the data file, and a career from an older build must still open.
    """
    career = data if data is not None else load_career_data()
    held = []
    for key in record.awards:
        award = career.award(key)
        if award is not None:
            held.append(award)
    return held


def update_awards(
    record: "PilotRecord", data: Optional[CareerData] = None
) -> list[Award]:
    """Grants every award the record now qualifies for. Returns the new ones.

    Once granted, an award is never taken back — the key stays on the record even
    if the data file later raises the bar.
    """
    career = data if data is not None else load_career_data()
    earned = []
    for award in career.awards:
        if award.key in record.awards:
            continue
        if _meets(record, award.requires):
            record.awards.append(award.key)
            earned.append(award)
    return earned


def is_combat_sortie(flight_type: Any) -> bool:
    """Whether a task counts as a combat sortie.

    Air-to-air, air-to-ground, or an escort type — the last so an escort jammer
    riding into the same threat ring as the strikers is not filed as a transit.
    A tanker orbit is a sortie and is not a combat sortie.
    """
    try:
        return bool(
            flight_type.is_air_to_air
            or flight_type.is_air_to_ground
            or flight_type.is_escort_type
        )
    except AttributeError:
        return False


def fold_sortie_records(
    records: Sequence["SortieRecord"],
    pilot_for: Any,
    data: Optional[CareerData] = None,
) -> dict[str, list[Award]]:
    """Adds a mission's §91 records to the careers of the pilots who flew them.

    ``pilot_for`` maps a DCS unit name to ``(pilot, flight_type)``, returning
    ``None`` for a unit the campaign does not own — an AI jet whose flight has
    already been cleaned up, or red's side of the mission.

    Only records that actually flew are folded. A counters-only wingman entry
    would otherwise add a sortie for a jet that was never position-sampled, and
    a parked airframe would add one for a jet that never moved (§91's
    ``MIN_SORTIE_DISTANCE_M``). Their weapons and kills are lost with them; a
    logbook that overcounts sorties is worse than one that misses a stray shot.

    Returns the awards earned this mission, keyed by pilot name, for a caller
    that wants to say so.
    """
    earned: dict[str, list[Award]] = {}
    for record in records:
        if not record.flew:
            continue
        try:
            resolved = pilot_for(record.unit)
        except Exception:
            logging.exception("Career fold: could not resolve %s", record.unit)
            continue
        if resolved is None:
            continue
        pilot, flight_type = resolved
        if pilot is None:
            continue
        career = pilot.record
        career.sorties += 1
        if is_combat_sortie(flight_type):
            career.combat_sorties += 1
        career.flight_seconds += record.duration
        career.shots += record.shots
        career.hits += record.hits
        career.air_kills += record.air_kills
        career.ground_kills += record.ground_kills
        career.naval_kills += record.naval_kills
        if record.ejected:
            career.ejections += 1
        new_awards = update_awards(career, data)
        if new_awards:
            earned.setdefault(pilot.name, []).extend(new_awards)
    return earned


def career_lines(record: "PilotRecord") -> list[tuple[str, str]]:
    """The logbook as label/value rows, for any surface that renders it."""
    rows = [
        ("Sorties", str(record.sorties)),
        ("Combat sorties", str(record.combat_sorties)),
        ("Flight time", f"{record.flight_hours:.1f} h"),
        ("Air kills", str(record.air_kills)),
        ("Ground kills", str(record.ground_kills)),
        ("Naval kills", str(record.naval_kills)),
        ("Ejections", str(record.ejections)),
    ]
    if record.shots:
        rows.append(("Shots for hits", f"{record.shots} for {record.hits}"))
    return rows
