"""The dated posture table (§96): reading it, and the rules for reading it.

Spot-checks are deliberately anchored to events the design note cites, so a
silent edit to the data trips a test rather than only changing a map.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from game.theater.nationalpostures import (
    RU_LED,
    US_LED,
    aircraft_for,
    load_postures,
    posture_for,
)

VALID = {"allied", "permissive", "contested", "closed", "hostile"}


def test_the_shipped_table_loads_and_is_well_formed() -> None:
    table = load_postures()
    assert len(table) > 40, "the shipped table should carry every DCS-map nation"
    for country, body in table.items():
        for bloc, ranges in body.items():
            if bloc == "aircraft":
                continue
            assert bloc in (US_LED, RU_LED), f"{country}: unknown bloc {bloc}"
            for entry in ranges:
                assert entry["posture"] in VALID, f"{country}: {entry}"


def test_a_missing_file_costs_the_feature_not_the_campaign() -> None:
    assert load_postures(Path("resources/borders/does-not-exist.yaml")) == {}


# -- the reading rules ---------------------------------------------------------


def test_an_unknown_country_is_closed() -> None:
    assert posture_for("Freedonia", date(2006, 1, 1), US_LED) == "closed"


def test_a_date_before_any_range_is_closed() -> None:
    """Never invent coverage: the safe default for a border is that it defends."""
    assert posture_for("Iran", date(1900, 1, 1), US_LED) == "closed"


def test_ranges_are_half_open_so_a_flip_month_lands_once() -> None:
    """Iran's revolution: allied up to 1979-02, not on it."""
    assert posture_for("Iran", date(1979, 1, 31), US_LED) == "allied"
    assert posture_for("Iran", date(1979, 2, 1), US_LED) != "allied"


def test_present_extends_to_the_far_future() -> None:
    assert posture_for("Iran", date(2030, 1, 1), US_LED) == "closed"


@pytest.mark.parametrize(
    "country,when,bloc,expected",
    [
        # The 1979 revolution, and the tanker war that followed.
        ("Iran", date(1977, 6, 1), US_LED, "allied"),
        ("Iran", date(1980, 6, 1), US_LED, "hostile"),
        ("Iran", date(1988, 1, 1), US_LED, "hostile"),
        ("Iran", date(2006, 4, 24), US_LED, "closed"),
        # Sadat expels the Soviet advisers, then Camp David.
        ("Egypt", date(1970, 1, 1), RU_LED, "allied"),
        ("Egypt", date(2006, 1, 1), US_LED, "permissive"),
        # OEF access, and its loss after Abbottabad.
        ("Pakistan", date(2006, 4, 24), US_LED, "permissive"),
        ("Pakistan", date(2015, 1, 1), US_LED, "contested"),
        # Turkey is NATO, and still refused twice.
        ("Turkey", date(2022, 6, 4), US_LED, "allied"),
        ("Turkey", date(2003, 3, 20), US_LED, "contested"),
        ("Turkey", date(1973, 11, 1), US_LED, "contested"),
    ],
)
def test_documented_history(country: str, when: date, bloc: str, expected: str) -> None:
    assert posture_for(country, when, bloc) == expected


# -- what the table still decides ---------------------------------------------
# Consent moved to the airbases inside a border on 2026-08-26 (DM call), so
# `permits_overflight`, `bloc_for_country` and `bloc_for_faction` are gone with
# it. The posture ranges are kept and still read by `posture_for`; the airframe
# is the answer §96 actually uses.


def test_the_era_picks_the_interceptor() -> None:
    """The reason the table survives: a country with no control points has no
    faction to borrow a jet from, and nothing else knows what it flew."""
    assert aircraft_for("Turkey", date(1965, 1, 1)) == "F-100D"
    assert aircraft_for("Turkey", date(1985, 1, 1)) == "F-4E"
    assert aircraft_for("Turkey", date(2022, 1, 1)) == "F-16C bl.50"


def test_an_unrecorded_country_gets_no_interceptor() -> None:
    assert aircraft_for("Freedonia", date(2006, 1, 1)) is None
