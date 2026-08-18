"""One record per flight of what the mission actually did.

The campaign historically learned only which units died. Everything else about a
two-hour sortie was discarded, and each feature that needed more cut its own
channel through `state.json` -- there are seven. This is the general form those
should collapse into, so the next feature needing mission facts extends a schema
instead of punching another hole. See
`docs/dev/design/414th-retribution-long-view.md` seam 1.

Written by `resources/plugins/base/sortie_recorder.lua`, which uses nothing
outside vanilla DCS. Notably NOT Tacview: it is a paid third-party program, so a
feature depending on it would silently do nothing for most players.

Forward compatible by construction. Unknown keys are ignored and a newer
`version` still parses, because the schema only ever gains fields. Anything
malformed degrades to "no data" rather than breaking debrief parsing -- a
mission's results must never be lost to a telemetry bug.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Sequence

#: Bumped only when an existing field changes meaning. Adding a field does not
#: need a bump -- readers ignore what they do not know.
SORTIE_RECORD_VERSION = 1


@dataclass(frozen=True)
class TrackSample:
    """Where a flight was at one moment."""

    #: Seconds since mission start.
    time: float
    x: float
    #: DCS's `z`, kept as `y` to match the engine's 2D convention elsewhere.
    y: float
    #: Metres above sea level.
    altitude: float
    #: Internal fuel remaining, 0.0-1.0.
    fuel: float


@dataclass(frozen=True)
class SortieRecord:
    """What one aircraft did over the course of the mission.

    Per aircraft, not per flight. Four humans in one group do not fly the same
    track, and `group:getUnits()` returns only the living units, so there is no
    stable "the lead" to record against. AI groups still produce one record --
    the recorder samples a single anchor jet for them.
    """

    #: DCS unit name. Unique; this is the record's key.
    unit: str
    #: DCS group name. Several records can share one.
    group: str
    unit_type: str
    #: DCS coalition id: 1 red, 2 blue.
    coalition: int
    first_seen: float
    last_seen: float
    track: tuple[TrackSample, ...]
    shots: int
    hits: int
    ejected: bool
    #: True if a human occupied the slot at any point in the mission.
    player: bool = False

    @property
    def duration(self) -> float:
        """Seconds the flight was airborne and observed."""
        return max(0.0, self.last_seen - self.first_seen)

    @property
    def distance_flown(self) -> float:
        """Metres along the sampled track.

        A lower bound: the track is downsampled, so turns cut corners.
        """
        total = 0.0
        for before, after in zip(self.track, self.track[1:]):
            total += math.hypot(after.x - before.x, after.y - before.y)
        return total

    @property
    def fuel_at_end(self) -> float | None:
        return self.track[-1].fuel if self.track else None

    @property
    def peak_altitude(self) -> float | None:
        return max((sample.altitude for sample in self.track), default=None)


def _sample_from(raw: Any) -> TrackSample | None:
    if not isinstance(raw, dict):
        return None
    try:
        return TrackSample(
            time=float(raw.get("t", 0.0)),
            x=float(raw.get("x", 0.0)),
            y=float(raw.get("z", 0.0)),
            altitude=float(raw.get("alt", 0.0)),
            fuel=float(raw.get("fuel", 0.0)),
        )
    except (TypeError, ValueError):
        return None


def _record_from(name: str, raw: Any) -> SortieRecord | None:
    if not isinstance(raw, dict):
        return None
    samples = raw.get("track")
    track: list[TrackSample] = []
    if isinstance(samples, list):
        for entry in samples:
            sample = _sample_from(entry)
            if sample is not None:
                track.append(sample)
    try:
        return SortieRecord(
            unit=name,
            group=str(raw.get("group", name)),
            unit_type=str(raw.get("type", "")),
            coalition=int(raw.get("coalition", 0)),
            first_seen=float(raw.get("first_seen", 0.0)),
            last_seen=float(raw.get("last_seen", 0.0)),
            track=tuple(track),
            shots=int(raw.get("shots", 0)),
            hits=int(raw.get("hits", 0)),
            ejected=bool(raw.get("ejected", False)),
            player=bool(raw.get("player", False)),
        )
    except (TypeError, ValueError):
        return None


def parse_sortie_records(raw: Any) -> tuple[SortieRecord, ...]:
    """Read the `sortie_records` channel out of a parsed `state.json`.

    Returns an empty tuple for every "no data" case: the recorder disabled, a
    pre-feature save, or a malformed payload.
    """
    if not isinstance(raw, dict):
        # Lua encodes an empty table as [], so a mission with no flights lands
        # here rather than as an empty dict.
        return ()
    version = raw.get("version")
    if isinstance(version, int) and version > SORTIE_RECORD_VERSION:
        logging.info(
            "state.json sortie records are version %s, this build reads %s; "
            "reading the fields it recognises",
            version,
            SORTIE_RECORD_VERSION,
        )
    flights = raw.get("flights")
    if not isinstance(flights, dict):
        return ()
    records = []
    for name, entry in flights.items():
        record = _record_from(str(name), entry)
        if record is not None:
            records.append(record)
    records.sort(key=lambda record: (record.first_seen, record.unit))
    return tuple(records)


def sorties_flown(records: Sequence[SortieRecord]) -> int:
    """How many aircraft actually got airborne.

    A record with no track is a counters-only entry -- a wingman that fired but
    was never position-sampled, which is every AI jet except its group's anchor.
    Counting those as sorties would inflate the figure by the group size.
    """
    return sum(1 for record in records if record.track)
