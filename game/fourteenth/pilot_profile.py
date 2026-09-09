"""Lifetime pilot profiles (§97) — a career that outlives the campaign.

§96 gave every pilot a career, and it lives inside the save. Start a new
campaign and it is gone, because a campaign's pilots are generated with it.
What a person actually wants recorded is their own flying: every mission they
have flown in Retribution, across every campaign, still there next year.

So this is a second destination for the same §91 sortie records, written to
``pilot_profiles.json`` under the Saved Games tree -- outside every save, the
same shape as the §43 flight-defaults store.

Identity is the **DCS player name**, which the recorder now reports per slot.
That needs no setup, and on a host box running a squadron event every pilot who
flew gets their own profile rather than all eight collapsing into one.

Three things this deliberately does not do:

* **No ranks or awards.** A lifetime page is numbers; §96 owns the ceremony.
* **No AI.** Only slots a human actually occupied are filed.
* **Nothing is ever recomputed.** A profile is an append-only ledger. There is
  no campaign to re-derive it from, so a bad write is permanent -- which is why
  the double-count guard below exists.

Nothing here raises. It runs inside mission-results commit and backs a window
that opens with no campaign loaded.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from game.sortierecord import SortieRecord

#: Bumped only when an existing field changes meaning.
PROFILE_VERSION = 1

#: Individual sorties kept per profile, newest first. A logbook is a list of
#: flights, not a scoreboard, so the entries are the point -- but the file is
#: read on every window open and written every turn, so it cannot grow forever.
#: At ~120 bytes an entry this is well under a megabyte per pilot.
MAX_LOG_ENTRIES = 2000

#: Mission ids remembered per profile for the double-count guard. Deep enough
#: that re-processing an old turn is still caught.
MAX_LOGGED_MISSIONS = 1000


@dataclass
class SortieLogEntry:
    """One flight, as the logbook lists it."""

    #: Campaign date the mission was flown on, ISO. The in-fiction date, not the
    #: wall clock: it is what the campaign and the kneeboard say.
    date: str
    campaign: str
    turn: int
    aircraft: str
    task: str
    minutes: float
    air_kills: int = 0
    ground_kills: int = 0
    naval_kills: int = 0
    ejected: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "campaign": self.campaign,
            "turn": self.turn,
            "aircraft": self.aircraft,
            "task": self.task,
            "minutes": round(self.minutes, 1),
            "air_kills": self.air_kills,
            "ground_kills": self.ground_kills,
            "naval_kills": self.naval_kills,
            "ejected": self.ejected,
        }

    @classmethod
    def from_dict(cls, raw: Any) -> Optional["SortieLogEntry"]:
        if not isinstance(raw, dict):
            return None
        try:
            return cls(
                date=str(raw.get("date", "")),
                campaign=str(raw.get("campaign", "")),
                turn=int(raw.get("turn", 0)),
                aircraft=str(raw.get("aircraft", "")),
                task=str(raw.get("task", "")),
                minutes=float(raw.get("minutes", 0.0)),
                air_kills=int(raw.get("air_kills", 0)),
                ground_kills=int(raw.get("ground_kills", 0)),
                naval_kills=int(raw.get("naval_kills", 0)),
                ejected=bool(raw.get("ejected", False)),
            )
        except (TypeError, ValueError):
            return None


@dataclass
class AirframeTotals:
    """What one pilot has done in one aircraft type."""

    sorties: int = 0
    minutes: float = 0.0
    air_kills: int = 0
    ground_kills: int = 0
    naval_kills: int = 0

    @property
    def hours(self) -> float:
        return self.minutes / 60.0

    @property
    def kills(self) -> int:
        return self.air_kills + self.ground_kills + self.naval_kills


@dataclass
class PilotProfile:
    """One person's flying, across every campaign they have flown."""

    #: The DCS player name. The key, and never edited -- renaming this would
    #: orphan the career from the seat that feeds it.
    key: str
    #: What the UI shows. Defaults to the key; the user may change it.
    display_name: str = ""
    sorties: int = 0
    combat_sorties: int = 0
    minutes: float = 0.0
    shots: int = 0
    hits: int = 0
    air_kills: int = 0
    ground_kills: int = 0
    naval_kills: int = 0
    ejections: int = 0
    campaigns: list[str] = field(default_factory=list)
    by_airframe: dict[str, AirframeTotals] = field(default_factory=dict)
    log: list[SortieLogEntry] = field(default_factory=list)
    #: Mission ids already folded in, newest last. See `mission_id`.
    logged_missions: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.display_name or self.key

    @property
    def hours(self) -> float:
        return self.minutes / 60.0

    @property
    def kills(self) -> int:
        return self.air_kills + self.ground_kills + self.naval_kills

    @property
    def most_flown(self) -> Optional[str]:
        if not self.by_airframe:
            return None
        return max(self.by_airframe.items(), key=lambda kv: kv[1].minutes)[0]

    def as_dict(self) -> dict[str, Any]:
        return {
            "display_name": self.display_name,
            "sorties": self.sorties,
            "combat_sorties": self.combat_sorties,
            "minutes": round(self.minutes, 1),
            "shots": self.shots,
            "hits": self.hits,
            "air_kills": self.air_kills,
            "ground_kills": self.ground_kills,
            "naval_kills": self.naval_kills,
            "ejections": self.ejections,
            "campaigns": list(self.campaigns),
            "by_airframe": {
                name: {
                    "sorties": totals.sorties,
                    "minutes": round(totals.minutes, 1),
                    "air_kills": totals.air_kills,
                    "ground_kills": totals.ground_kills,
                    "naval_kills": totals.naval_kills,
                }
                for name, totals in self.by_airframe.items()
            },
            "log": [entry.as_dict() for entry in self.log],
            "logged_missions": list(self.logged_missions),
        }

    @classmethod
    def from_dict(cls, key: str, raw: Any) -> "PilotProfile":
        profile = cls(key=key)
        if not isinstance(raw, dict):
            return profile
        profile.display_name = str(raw.get("display_name", "") or "")
        for name in (
            "sorties",
            "combat_sorties",
            "shots",
            "hits",
            "air_kills",
            "ground_kills",
            "naval_kills",
            "ejections",
        ):
            try:
                setattr(profile, name, int(raw.get(name, 0)))
            except (TypeError, ValueError):
                pass
        try:
            profile.minutes = float(raw.get("minutes", 0.0))
        except (TypeError, ValueError):
            pass
        campaigns = raw.get("campaigns")
        if isinstance(campaigns, list):
            profile.campaigns = [str(name) for name in campaigns]
        airframes = raw.get("by_airframe")
        if isinstance(airframes, dict):
            for name, entry in airframes.items():
                if not isinstance(entry, dict):
                    continue
                totals = AirframeTotals()
                try:
                    totals.sorties = int(entry.get("sorties", 0))
                    totals.minutes = float(entry.get("minutes", 0.0))
                    totals.air_kills = int(entry.get("air_kills", 0))
                    totals.ground_kills = int(entry.get("ground_kills", 0))
                    totals.naval_kills = int(entry.get("naval_kills", 0))
                except (TypeError, ValueError):
                    continue
                profile.by_airframe[str(name)] = totals
        entries = raw.get("log")
        if isinstance(entries, list):
            for item in entries:
                entry = SortieLogEntry.from_dict(item)
                if entry is not None:
                    profile.log.append(entry)
        logged = raw.get("logged_missions")
        if isinstance(logged, list):
            profile.logged_missions = [str(item) for item in logged]
        return profile


def mission_id(campaign_uid: str, turn: int) -> str:
    """The id the double-count guard remembers.

    Keyed on the GAME, not the campaign name: replaying the same campaign is a
    different game, and its turn 1 must not be mistaken for one already flown.
    """
    return f"{campaign_uid}:{turn}"


#: Loaded once and held. ``None`` means not yet read; an empty dict is a valid
#: loaded state (nothing flown yet, or persistency was unavailable).
_cache: Optional[dict[str, PilotProfile]] = None


def _store_path() -> Optional[Any]:
    try:
        from game.persistency import pilot_profiles_path

        return pilot_profiles_path()
    except Exception:
        # Persistency is not set up in a headless test, and there is no user
        # directory to write to. Not an error; there is simply no store.
        return None


def load_profiles(path: Optional[Any] = None) -> dict[str, PilotProfile]:
    """Every profile on disk, keyed by DCS player name.

    Returns an empty mapping -- never raises -- for a missing, unreadable or
    malformed file. A single bad profile is skipped rather than losing the rest.
    """
    global _cache
    if path is None and _cache is not None:
        return _cache
    source = path if path is not None else _store_path()
    profiles: dict[str, PilotProfile] = {}
    if source is not None:
        try:
            if source.exists():
                raw = json.loads(source.read_text(encoding="utf-8"))
                entries = raw.get("profiles") if isinstance(raw, dict) else None
                if isinstance(entries, dict):
                    for key, entry in entries.items():
                        profiles[str(key)] = PilotProfile.from_dict(str(key), entry)
        except (OSError, ValueError):
            logging.exception("Could not read the pilot profile store at %s", source)
            profiles = {}
    if path is None:
        _cache = profiles
    return profiles


def save_profiles(
    profiles: dict[str, PilotProfile], path: Optional[Any] = None
) -> bool:
    """Writes the store. Returns whether it reached disk.

    A failure is logged and swallowed: this is called from mission-results
    commit, and a profile that cannot be written must never cost a turn.
    """
    target = path if path is not None else _store_path()
    if target is None:
        return False
    payload = {
        "version": PROFILE_VERSION,
        "profiles": {key: profile.as_dict() for key, profile in profiles.items()},
    }
    try:
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except (OSError, ValueError):
        logging.exception("Could not write the pilot profile store at %s", target)
        return False
    return True


def rename_profile(key: str, display_name: str) -> bool:
    """Changes what the UI calls a profile. The key itself never moves."""
    profiles = load_profiles()
    profile = profiles.get(key)
    if profile is None:
        return False
    profile.display_name = display_name.strip()
    return save_profiles(profiles)


def _fold_one(
    profile: PilotProfile,
    record: "SortieRecord",
    entry: SortieLogEntry,
    combat: bool,
) -> None:
    profile.sorties += 1
    if combat:
        profile.combat_sorties += 1
    profile.minutes += entry.minutes
    profile.shots += record.shots
    profile.hits += record.hits
    profile.air_kills += record.air_kills
    profile.ground_kills += record.ground_kills
    profile.naval_kills += record.naval_kills
    if record.ejected:
        profile.ejections += 1
    if entry.campaign and entry.campaign not in profile.campaigns:
        profile.campaigns.append(entry.campaign)

    totals = profile.by_airframe.setdefault(entry.aircraft, AirframeTotals())
    totals.sorties += 1
    totals.minutes += entry.minutes
    totals.air_kills += record.air_kills
    totals.ground_kills += record.ground_kills
    totals.naval_kills += record.naval_kills

    profile.log.insert(0, entry)
    del profile.log[MAX_LOG_ENTRIES:]


def record_mission(
    records: Sequence["SortieRecord"],
    campaign: str,
    campaign_uid: str,
    turn: int,
    day: str,
    task_for: Any,
    path: Optional[Any] = None,
) -> dict[str, int]:
    """Files a mission's human-flown sorties against their lifetime profiles.

    ``task_for`` maps a DCS unit name to ``(task name, is_combat)``, or None for
    a unit the campaign does not own. Only records that FLEW and carry a player
    name are filed -- an AI jet has no career, and a counters-only or parked
    record is not a sortie (§91's `flew`).

    Returns the number of sorties filed per profile, for a caller that wants to
    say so. An empty result means nothing was written.
    """
    filed: dict[str, int] = {}
    candidates = [r for r in records if r.flew and r.player_name]
    if not candidates:
        return filed

    profiles = load_profiles(path)
    mid = mission_id(campaign_uid, turn)
    dirty = False

    for record in candidates:
        profile = profiles.get(record.player_name)
        if profile is None:
            profile = PilotProfile(key=record.player_name)
            profiles[record.player_name] = profile
        # The guard is per profile: a pilot who joined the event late has not
        # logged this mission even though everyone else has.
        if mid in profile.logged_missions:
            continue
        try:
            resolved = task_for(record.unit)
        except Exception:
            logging.exception("Pilot profile: could not resolve %s", record.unit)
            continue
        task, combat = resolved if resolved is not None else ("Sortie", False)
        entry = SortieLogEntry(
            date=day,
            campaign=campaign,
            turn=turn,
            aircraft=record.unit_type,
            task=task,
            minutes=record.duration / 60.0,
            air_kills=record.air_kills,
            ground_kills=record.ground_kills,
            naval_kills=record.naval_kills,
            ejected=record.ejected,
        )
        _fold_one(profile, record, entry, combat)
        profile.logged_missions.append(mid)
        del profile.logged_missions[:-MAX_LOGGED_MISSIONS]
        filed[record.player_name] = filed.get(record.player_name, 0) + 1
        dirty = True

    if dirty:
        save_profiles(profiles, path)
    return filed


def profile_lines(profile: PilotProfile) -> list[tuple[str, str]]:
    """The lifetime totals as label/value rows, for any surface that shows them."""
    rows = [
        ("Sorties", str(profile.sorties)),
        ("Combat sorties", str(profile.combat_sorties)),
        ("Flight time", f"{profile.hours:.1f} h"),
        ("Air kills", str(profile.air_kills)),
        ("Ground kills", str(profile.ground_kills)),
        ("Naval kills", str(profile.naval_kills)),
        ("Ejections", str(profile.ejections)),
        ("Campaigns", str(len(profile.campaigns))),
    ]
    if profile.shots:
        rows.append(("Shots for hits", f"{profile.shots} for {profile.hits}"))
    most = profile.most_flown
    if most:
        rows.append(("Most flown", most))
    return rows


def reset_cache() -> None:
    """Drops the in-memory copy so the next read comes off disk. Tests only."""
    global _cache
    _cache = None
