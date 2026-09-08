"""The pilot career logbook (§96): the ledger between §91 and the pilot roster.

Three things are pinned here because getting any of them wrong makes the feature
worse than not having it:

* Only records that actually FLEW are folded. §91 emits a counters-only entry
  for every AI wingman that was never position-sampled, and a track-but-no-
  movement entry for the untasked airframes parked on the ramp. Folding either
  inflates a career's sortie count by the group size.
* A career only ever grows. An award, once earned, survives a data-file change.
* An award whose requirement names a field that does not exist is REJECTED, not
  dropped -- a dropped requirement is met by everyone on their first sortie.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import pytest

from game.fourteenth.career import (
    CareerData,
    RankGrade,
    RankLadder,
    Award,
    awards_held,
    career_lines,
    fold_sortie_records,
    is_combat_sortie,
    load_career_data,
    rank_for,
    update_awards,
)
from game.ato.flighttype import FlightType
from game.sortierecord import TrackSample, SortieRecord
from game.squadrons.pilot import Pilot, PilotRecord


def _track(points: int = 2, spacing: float = 5000.0) -> tuple[TrackSample, ...]:
    return tuple(
        TrackSample(time=i * 30.0, x=i * spacing, y=0.0, altitude=6000.0, fuel=0.8)
        for i in range(points)
    )


def _record(unit: str = "Enfield 1-1", **overrides: Any) -> SortieRecord:
    spec: dict[str, Any] = {
        "unit": unit,
        "group": "Enfield",
        "unit_type": "FA-18C_hornet",
        "coalition": 2,
        "first_seen": 0.0,
        "last_seen": 3600.0,
        "track": _track(),
        "shots": 0,
        "hits": 0,
        "ejected": False,
    }
    spec.update(overrides)
    return SortieRecord(**spec)


def _data() -> CareerData:
    return CareerData(
        ladders=(
            RankLadder(
                "test",
                (),
                (
                    RankGrade("g1", "Junior", {}),
                    RankGrade("g2", "Senior", {"combat_sorties": 2}),
                ),
            ),
        ),
        awards=(
            Award("first", "First Sortie", "", {"sorties": 1}),
            Award("ace", "Ace", "", {"air_kills": 5}),
        ),
    )


def _pilot_for(pilot: Pilot, flight_type: FlightType = FlightType.STRIKE) -> Any:
    def resolve(unit_name: str) -> Optional[tuple[Pilot, FlightType]]:
        return (pilot, flight_type)

    return resolve


def test_a_flown_sortie_is_added_to_the_career() -> None:
    pilot = Pilot("Viper")
    fold_sortie_records(
        [_record(shots=4, hits=2, air_kills=1, ground_kills=3, naval_kills=1)],
        _pilot_for(pilot),
        _data(),
    )

    career = pilot.record
    assert career.sorties == 1
    assert career.combat_sorties == 1
    assert career.flight_seconds == pytest.approx(3600.0)
    assert career.flight_hours == pytest.approx(1.0)
    assert (career.shots, career.hits) == (4, 2)
    assert (career.air_kills, career.ground_kills, career.naval_kills) == (1, 3, 1)
    assert career.kills == 5


def test_a_counters_only_wingman_is_not_a_sortie() -> None:
    # §91 emits one of these per AI jet that was never position-sampled. Folding
    # it would add a sortie for every wingman in the formation.
    pilot = Pilot("Viper")
    fold_sortie_records([_record(track=(), shots=2)], _pilot_for(pilot), _data())

    assert pilot.record.sorties == 0
    assert pilot.record.shots == 0


def test_a_parked_airframe_is_not_a_sortie() -> None:
    # `_spawn_unused_for` parks untasked airframes as 1-ship Completed groups and
    # the recorder's sweep cannot tell them from flights. 82 of test 12's 158
    # records were these.
    pilot = Pilot("Viper")
    fold_sortie_records(
        [_record(track=_track(points=3, spacing=1.0))], _pilot_for(pilot), _data()
    )

    assert pilot.record.sorties == 0


def test_a_tanker_orbit_is_a_sortie_and_not_a_combat_sortie() -> None:
    pilot = Pilot("Texaco")
    fold_sortie_records([_record()], _pilot_for(pilot, FlightType.REFUELING), _data())

    assert pilot.record.sorties == 1
    assert pilot.record.combat_sorties == 0


def test_an_escort_jammer_counts_as_a_combat_sortie() -> None:
    # It rides into the same threat ring as the strikers it is covering.
    assert is_combat_sortie(FlightType.ESCORT_JAMMER)
    assert is_combat_sortie(FlightType.BARCAP)
    assert is_combat_sortie(FlightType.STRIKE)
    assert not is_combat_sortie(FlightType.FERRY)
    assert not is_combat_sortie(FlightType.AEWC)


def test_an_ejection_is_logged_once_per_sortie() -> None:
    pilot = Pilot("Viper")
    fold_sortie_records([_record(ejected=True)], _pilot_for(pilot), _data())

    assert pilot.record.ejections == 1


def test_a_unit_the_campaign_does_not_own_is_skipped() -> None:
    pilot = Pilot("Viper")

    def resolve(unit_name: str) -> None:
        return None

    fold_sortie_records([_record()], resolve, _data())
    assert pilot.record.sorties == 0


def test_a_resolver_that_raises_costs_one_record_not_the_turn() -> None:
    # The fold runs inside mission-results commit. A lookup fault must never take
    # the turn's results down with it.
    pilot = Pilot("Viper")
    calls: list[str] = []

    def resolve(unit_name: str) -> Any:
        calls.append(unit_name)
        if unit_name == "bad":
            raise RuntimeError("no")
        return (pilot, FlightType.STRIKE)

    fold_sortie_records([_record("bad"), _record("good")], resolve, _data())

    assert calls == ["bad", "good"]
    assert pilot.record.sorties == 1


def test_the_rank_is_the_highest_grade_the_record_meets() -> None:
    data = _data()
    record = PilotRecord()
    assert rank_for(record, None, data) == "Junior"
    record.combat_sorties = 2
    assert rank_for(record, None, data) == "Senior"


def test_a_squadron_ranks_against_its_own_service() -> None:
    data = CareerData(
        ladders=(
            RankLadder("raf", ("UK",), (RankGrade("a", "Plt Off", {}),)),
            RankLadder("default", (), (RankGrade("b", "2nd Lt.", {}),)),
        ),
        awards=(),
    )
    assert rank_for(PilotRecord(), "UK", data) == "Plt Off"
    assert rank_for(PilotRecord(), "USA", data) == "2nd Lt."
    # No fallback ladder at all is not a crash, it is no rank.
    assert rank_for(PilotRecord(), "USA", CareerData((), ())) is None


def test_an_award_is_granted_once_and_never_taken_back() -> None:
    data = _data()
    record = PilotRecord(sorties=1)

    assert [award.key for award in update_awards(record, data)] == ["first"]
    assert update_awards(record, data) == []
    assert record.awards == ["first"]

    # The bar moving does not un-earn it.
    harder = CareerData(
        data.ladders, (Award("first", "First Sortie", "", {"sorties": 99}),)
    )
    assert [award.name for award in awards_held(record, harder)] == ["First Sortie"]


def test_an_award_key_with_no_entry_is_dropped_not_rendered() -> None:
    # An award may be renamed or removed; a career from an older build must open.
    record = PilotRecord(awards=["gone"])
    assert awards_held(record, _data()) == []


def test_a_requirement_naming_an_unknown_field_rejects_its_entry(
    tmp_path: Path,
) -> None:
    # Dropping the requirement instead would make the award unconditional.
    source = tmp_path / "career.yaml"
    source.write_text(
        "awards:\n"
        "  - key: bogus\n"
        "    name: Bogus\n"
        "    requires: {enemy_beers_drunk: 1}\n"
        "  - key: real\n"
        "    name: Real\n"
        "    requires: {sorties: 1}\n",
        encoding="utf-8",
    )
    data = load_career_data(source)
    assert [award.key for award in data.awards] == ["real"]


def test_a_malformed_file_costs_the_awards_and_nothing_else(tmp_path: Path) -> None:
    source = tmp_path / "career.yaml"
    source.write_text("this: [is not, {valid", encoding="utf-8")
    data = load_career_data(source)
    assert data.ladders == ()
    assert data.awards == ()


def test_a_missing_file_is_not_an_error(tmp_path: Path) -> None:
    data = load_career_data(tmp_path / "nope.yaml")
    assert data.awards == ()


def test_the_shipped_data_file_parses() -> None:
    data = load_career_data()
    assert data.awards, "resources/pilot_career.yaml should ship awards"
    assert data.ladder_for(None) is not None, "there must be a fallback ladder"
    assert data.ladder_for("UK") is not None


def test_a_pre_logbook_save_loads_with_an_empty_career() -> None:
    # Saves before §96 carry only missions_flown. Starting the career at zero is
    # the honest degrade: the sortie records for those turns are long gone.
    record = PilotRecord()
    record.__setstate__({"missions_flown": 12})

    assert record.missions_flown == 12
    assert record.sorties == 0
    assert record.flight_hours == 0.0
    assert record.awards == []


def test_the_career_page_says_something_for_an_empty_record() -> None:
    rows = dict(career_lines(PilotRecord()))
    assert rows["Sorties"] == "0"
    assert rows["Flight time"] == "0.0 h"
    # A pilot who has fired nothing gets no shots/hits row rather than "0 for 0".
    assert "Shots for hits" not in rows
