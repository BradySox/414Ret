"""Lifetime pilot profiles (§97): the career that outlives the campaign.

The store is append-only and lives outside every save, so there is no campaign
to re-derive it from and a bad write is permanent. That shapes what is pinned:

* A mission is folded ONCE. The double-count guard is keyed on the game, not on
  the campaign name, so replaying a campaign records its sorties again instead
  of being mistaken for the playthrough already on file.
* Only human-crewed records that actually FLEW are filed. An AI jet has no
  career, and §91 emits counters-only and parked-airframe records that are not
  sorties.
* A malformed or unwritable store costs the profiles and never the turn.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pytest

from game.fourteenth import pilot_profile
from game.fourteenth.pilot_profile import (
    PilotProfile,
    load_profiles,
    mission_id,
    profile_lines,
    record_mission,
    save_profiles,
)
from game.sortierecord import SortieRecord, TrackSample


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
        "player": True,
        "player_name": "Viper",
    }
    spec.update(overrides)
    return SortieRecord(**spec)


def _task_for(name: str = "Strike", combat: bool = True) -> Any:
    def resolve(unit_name: str) -> tuple[str, bool]:
        return (name, combat)

    return resolve


def _file(tmp_path: Path) -> Path:
    return tmp_path / "pilot_profiles.json"


def _fold(
    path: Path,
    records: list[SortieRecord],
    turn: int = 1,
    uid: str = "game-a",
    campaign: str = "Red Tide",
    task: Any = None,
) -> dict[str, int]:
    return record_mission(
        records,
        campaign=campaign,
        campaign_uid=uid,
        turn=turn,
        day="1985-06-01",
        task_for=task or _task_for(),
        path=path,
    )


def test_a_flown_sortie_creates_a_profile_and_a_log_entry(tmp_path: Path) -> None:
    path = _file(tmp_path)
    _fold(path, [_record(shots=4, hits=2, air_kills=1, ground_kills=2)])

    profile = load_profiles(path)["Viper"]
    assert profile.sorties == 1
    assert profile.combat_sorties == 1
    assert profile.hours == pytest.approx(1.0)
    assert (profile.air_kills, profile.ground_kills) == (1, 2)
    assert profile.campaigns == ["Red Tide"]
    assert profile.by_airframe["FA-18C_hornet"].sorties == 1

    entry = profile.log[0]
    assert entry.campaign == "Red Tide"
    assert entry.aircraft == "FA-18C_hornet"
    assert entry.task == "Strike"
    assert entry.minutes == pytest.approx(60.0)


def test_the_same_mission_is_never_folded_twice(tmp_path: Path) -> None:
    # The store is append-only with nothing to re-derive it from, so a double
    # count is permanent and looks like a bug forever.
    path = _file(tmp_path)
    _fold(path, [_record()])
    _fold(path, [_record()])

    profile = load_profiles(path)["Viper"]
    assert profile.sorties == 1
    assert len(profile.log) == 1


def test_replaying_a_campaign_records_its_sorties_again(tmp_path: Path) -> None:
    # Keyed on the GAME, not the campaign name: turn 1 of a fresh playthrough is
    # a real sortie, not the one already on file.
    path = _file(tmp_path)
    _fold(path, [_record()], turn=1, uid="game-a")
    _fold(path, [_record()], turn=1, uid="game-b")

    assert load_profiles(path)["Viper"].sorties == 2


def test_a_pilot_who_reslotted_logs_both_sorties(tmp_path: Path) -> None:
    # Ejected, took a second jet: two units, one player, one mission. The guard
    # is decided before the fold, so the second record is a sortie and not a
    # replay of the first -- and re-running the same mission still adds nothing.
    path = _file(tmp_path)
    records = [
        _record("Enfield 1-1", ejected=True),
        _record("Enfield 2-1", unit_type="F-16C_50"),
    ]
    _fold(path, records)
    _fold(path, records)

    profile = load_profiles(path)["Viper"]
    assert profile.sorties == 2
    assert profile.ejections == 1
    assert [entry.aircraft for entry in profile.log] == ["F-16C_50", "FA-18C_hornet"]
    assert profile.logged_missions == [mission_id("game-a", 1)]


def test_a_failed_write_leaves_the_old_store_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Append-only with nothing to re-derive it from: a write that dies halfway
    # must not take the file with it, and must not leave its temp file behind.
    path = _file(tmp_path)
    _fold(path, [_record()])
    before = path.read_text(encoding="utf-8")

    def refuse(self: Path, target: Any) -> Any:
        raise OSError("disk full")

    monkeypatch.setattr(Path, "replace", refuse)
    assert save_profiles(load_profiles(path), path) is False
    assert path.read_text(encoding="utf-8") == before
    assert not list(tmp_path.glob(".*.tmp"))


def test_a_pilot_who_joined_late_still_logs_that_mission(tmp_path: Path) -> None:
    # The guard is per profile, not per store.
    path = _file(tmp_path)
    _fold(path, [_record(player_name="Viper")])
    _fold(path, [_record("Enfield 1-2", player_name="Jester")])

    profiles = load_profiles(path)
    assert profiles["Viper"].sorties == 1
    assert profiles["Jester"].sorties == 1


def test_each_human_in_one_mission_gets_their_own_profile(tmp_path: Path) -> None:
    path = _file(tmp_path)
    _fold(
        path,
        [
            _record("Enfield 1-1", player_name="Viper"),
            _record("Enfield 1-2", player_name="Jester"),
            _record("Enfield 1-3", player_name="Maverick"),
        ],
    )

    assert sorted(load_profiles(path)) == ["Jester", "Maverick", "Viper"]


def test_an_ai_jet_has_no_career(tmp_path: Path) -> None:
    path = _file(tmp_path)
    filed = _fold(path, [_record(player="", player_name="")])

    assert filed == {}
    assert load_profiles(path) == {}


def test_a_counters_only_or_parked_record_is_not_a_sortie(tmp_path: Path) -> None:
    # §91 emits one counters-only entry per unsampled wingman, and parks the
    # squadron's untasked airframes as groups the sweep cannot tell from flights.
    path = _file(tmp_path)
    _fold(
        path,
        [
            _record("wingman", track=(), shots=3),
            _record("parked", track=_track(points=3, spacing=1.0)),
        ],
    )

    assert load_profiles(path) == {}


def test_a_tanker_orbit_is_a_sortie_and_not_a_combat_sortie(tmp_path: Path) -> None:
    path = _file(tmp_path)
    _fold(path, [_record()], task=_task_for("Refueling", combat=False))

    profile = load_profiles(path)["Viper"]
    assert (profile.sorties, profile.combat_sorties) == (1, 0)


def test_a_unit_the_campaign_does_not_own_still_logs_the_flight(
    tmp_path: Path,
) -> None:
    # A human flew it; losing the sortie because the flight lookup missed would
    # be worse than filing it with a generic task.
    path = _file(tmp_path)

    def resolve(unit_name: str) -> None:
        return None

    _fold(path, [_record()], task=resolve)
    profile = load_profiles(path)["Viper"]
    assert profile.sorties == 1
    assert profile.combat_sorties == 0
    assert profile.log[0].task == "Sortie"


def test_a_resolver_that_raises_costs_one_record_not_the_turn(
    tmp_path: Path,
) -> None:
    path = _file(tmp_path)

    def resolve(unit_name: str) -> tuple[str, bool]:
        if unit_name == "bad":
            raise RuntimeError("no")
        return ("Strike", True)

    _fold(
        path,
        [_record("bad", player_name="Viper"), _record("good", player_name="Viper")],
        task=resolve,
    )
    assert load_profiles(path)["Viper"].sorties == 1


def test_flights_accumulate_across_campaigns(tmp_path: Path) -> None:
    path = _file(tmp_path)
    _fold(path, [_record()], uid="game-a", campaign="Red Tide")
    _fold(path, [_record(unit_type="F-16C_50")], uid="game-b", campaign="Iron Gate")

    profile = load_profiles(path)["Viper"]
    assert profile.sorties == 2
    assert profile.campaigns == ["Red Tide", "Iron Gate"]
    assert set(profile.by_airframe) == {"FA-18C_hornet", "F-16C_50"}
    assert profile.most_flown in {"FA-18C_hornet", "F-16C_50"}


def test_the_log_is_capped_and_keeps_the_newest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The cap is lowered rather than exercised at its real value: every fold
    # rewrites the whole store, so folding 2,000 of them is quadratic and would
    # cost the suite half a minute to assert a slice.
    monkeypatch.setattr(pilot_profile, "MAX_LOG_ENTRIES", 5)
    path = _file(tmp_path)
    for turn in range(9):
        _fold(path, [_record()], turn=turn)

    stored = load_profiles(path)["Viper"]
    assert len(stored.log) == 5
    assert stored.sorties == 9, "the totals keep counting past the log cap"
    assert stored.log[0].turn == 8, "the newest flight survives"
    assert stored.log[-1].turn == 4, "the oldest are the ones dropped"


def test_a_display_name_never_moves_the_key(tmp_path: Path) -> None:
    path = _file(tmp_path)
    _fold(path, [_record()])
    profiles = load_profiles(path)
    profiles["Viper"].display_name = 'Maj. James "Viper" Smith'
    save_profiles(profiles, path)

    reloaded = load_profiles(path)
    assert "Viper" in reloaded
    assert reloaded["Viper"].name == 'Maj. James "Viper" Smith'
    # And it keeps accumulating under the same key.
    _fold(path, [_record()], turn=2)
    assert load_profiles(path)["Viper"].sorties == 2


def test_a_malformed_store_costs_the_profiles_and_nothing_else(
    tmp_path: Path,
) -> None:
    path = _file(tmp_path)
    path.write_text("{not json", encoding="utf-8")
    assert load_profiles(path) == {}


def test_a_missing_store_is_not_an_error(tmp_path: Path) -> None:
    assert load_profiles(tmp_path / "nope.json") == {}


def test_a_store_round_trips_through_json(tmp_path: Path) -> None:
    path = _file(tmp_path)
    _fold(path, [_record(shots=2, hits=1, naval_kills=1, ejected=True)])

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["version"] == 1
    assert raw["profiles"]["Viper"]["naval_kills"] == 1

    profile = load_profiles(path)["Viper"]
    assert profile.ejections == 1
    assert profile.log[0].ejected is True


def test_the_page_rows_read_for_an_untouched_profile() -> None:
    rows = dict(profile_lines(PilotProfile(key="Viper")))
    assert rows["Sorties"] == "0"
    assert rows["Flight time"] == "0.0 h"
    assert rows["Campaigns"] == "0"
    # No shots means no "0 for 0" row, and no aircraft means no "Most flown".
    assert "Shots for hits" not in rows
    assert "Most flown" not in rows


def test_the_mission_id_separates_games_not_just_turns() -> None:
    assert mission_id("game-a", 3) != mission_id("game-b", 3)
    assert mission_id("game-a", 3) != mission_id("game-a", 4)
