"""Datalink is era-gated per airframe, the way payload properties are (§24).

Flown 2026-08-16: a generated Caucasus mission carried the DCS ``EPLRS`` task on
**1 of 23** blue plane groups, against **16 of 18** in a hand-built modern
mission on the same install — so datalink worked there and not here. The cause
was the old single boolean, off in the saved-settings baseline.

That boolean could never be right for a fork shipping both 1988 and 2027
campaigns: on gives Desert Storm Hornets Link 16 a decade early, off costs the
modern campaigns their datalink entirely.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from game import persistency
from game.datalinkera import datalink_available
from game.dcs.aircrafttype import AircraftType
from game.settings import DatalinkPolicy


@pytest.fixture(scope="module")
def fleet(tmp_path_factory: pytest.TempPathFactory) -> Iterator[list[AircraftType]]:
    tmp_path: Path = tmp_path_factory.mktemp("datalink_era")
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16884)
    yield list(AircraftType.iter_all())


# ------------------------------------------------------------------ the rule


def test_era_correct_withholds_a_datalink_that_does_not_exist_yet() -> None:
    assert not datalink_available(DatalinkPolicy.ERA_CORRECT, 2002, 1991)


def test_era_correct_grants_it_from_its_service_year() -> None:
    assert datalink_available(DatalinkPolicy.ERA_CORRECT, 2002, 2002)
    assert datalink_available(DatalinkPolicy.ERA_CORRECT, 2002, 2016)


def test_an_unauthored_airframe_is_unrestricted() -> None:
    """Permissive when unknown: adding dates is incremental, and a missing date
    must never silently strip a capability from an airframe nobody researched."""
    assert datalink_available(DatalinkPolicy.ERA_CORRECT, None, 1944)


def test_the_overrides_ignore_the_date_entirely() -> None:
    assert datalink_available(DatalinkPolicy.ALWAYS, 2002, 1991)
    assert not datalink_available(DatalinkPolicy.NEVER, 2002, 2027)
    assert not datalink_available(DatalinkPolicy.NEVER, None, 2027)


# ----------------------------------------------------------------- the data


def test_the_authored_dates_split_the_forks_own_eras(fleet: list[AircraftType]) -> None:
    """The point of the feature: the same airframe answers differently in a
    Gulf War campaign and a modern one."""
    hornet = AircraftType.named("F/A-18C Hornet (Lot 20)")
    assert hornet.datalink_introduced == 2002

    assert not datalink_available(
        DatalinkPolicy.ERA_CORRECT, hornet.datalink_introduced, 1991
    ), "Desert Storm Hornets must not have Link 16"
    assert datalink_available(
        DatalinkPolicy.ERA_CORRECT, hornet.datalink_introduced, 2016
    ), "Inherent Resolve Hornets must have Link 16"


def test_every_authored_date_is_sane(fleet: list[AircraftType]) -> None:
    """A typo here silently removes datalink from a whole campaign era."""
    authored = [a for a in fleet if a.datalink_introduced is not None]
    assert authored, "no airframe declares datalink_introduced"
    for aircraft in authored:
        year = aircraft.datalink_introduced
        assert year is not None
        assert 1980 <= year <= 2030, f"{aircraft.display_name}: implausible {year}"
        assert (
            aircraft.eplrs_capable
        ), f"{aircraft.display_name} declares a datalink year but DCS gives it no EPLRS"


def test_a_malformed_year_is_ignored_not_fatal(fleet: list[AircraftType]) -> None:
    """A typo in one unit file must not take the whole game down."""
    assert AircraftType._parse_datalink_introduced({}) is None
    assert (
        AircraftType._parse_datalink_introduced({"datalink_introduced": "2002"}) == 2002
    )
    assert (
        AircraftType._parse_datalink_introduced({"datalink_introduced": "soon"}) is None
    )


# ------------------------------------------------------------- the migration


def test_the_old_boolean_migrates_to_an_explicit_choice() -> None:
    """A campaign that deliberately turned datalink off stays off, and one that
    had it on does not lose it mid-campaign to an airframe date. ERA_CORRECT is
    the default for NEW games only."""
    from game.settings import Settings

    for had_it, expected in (
        (True, DatalinkPolicy.ALWAYS),
        (False, DatalinkPolicy.NEVER),
    ):
        migrated = Settings._migrate_legacy_settings({"eplrs_enabled": had_it})
        assert migrated["datalink_policy"] is expected

    assert Settings().datalink_policy is DatalinkPolicy.ERA_CORRECT
