from __future__ import annotations

from game.ato.flighttype import FlightType
from game.data.brevity_reference import brevity_for


def test_brevity_is_filtered_to_the_task() -> None:
    label, lines = brevity_for(FlightType.SEAD)
    assert label == "SEAD"
    terms = [term for term, _ in lines]
    assert "MAGNUM" in terms
    assert all(isinstance(t, str) and isinstance(m, str) for t, m in lines)


def test_distinct_tasks_get_distinct_sets() -> None:
    a2a = [term for term, _ in brevity_for(FlightType.BARCAP)[1]]
    strike = [term for term, _ in brevity_for(FlightType.STRIKE)[1]]
    assert "FOX 1 / 2 / 3" in a2a
    assert "RIFLE / PICKLE" in strike
    assert a2a != strike


def test_uncatalogued_task_falls_back_to_general() -> None:
    label, lines = brevity_for(FlightType.FERRY)
    assert label == "GENERAL"
    assert lines  # non-empty fallback
