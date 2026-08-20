from datetime import timedelta

from game.settings import (
    DIFFICULTY_REALISM_PAGE,
    PLANNER_SUITE_PAGE,
    Settings,
    apply_planner_suite,
    detect_planner_suite,
)
from game.settings.plannersuite import PLANNER_SUITE_VALUES


def test_fresh_settings_are_stock() -> None:
    """The 2026-08-09 re-convergence contract: a new game plans like upstream.

    Every planner-suite gate's Settings default must be its stock value, so a
    fresh Settings detects as stock. If this fails, a default drifted back to
    the 414th value without a decision.
    """
    settings = Settings()
    for name, (stock, _suite) in PLANNER_SUITE_VALUES.items():
        assert getattr(settings, name) == stock, name
    assert detect_planner_suite(settings) is False


def test_apply_suite_and_back_round_trips() -> None:
    settings = Settings()
    apply_planner_suite(settings, True)
    assert detect_planner_suite(settings) is True
    assert settings.barcap_overlap_time == timedelta(minutes=15)
    assert settings.max_escort_jammers == 4
    apply_planner_suite(settings, False)
    assert detect_planner_suite(settings) is False
    assert settings.barcap_overlap_time == timedelta(minutes=0)
    assert settings.max_escort_jammers == 0


def test_hand_tuned_mix_detects_custom() -> None:
    settings = Settings()
    settings.sead_strike_coordination = True
    assert detect_planner_suite(settings) is None


def test_suite_fields_exist_on_settings() -> None:
    """Every suite field must remain a real Settings field (rename guard)."""
    settings = Settings()
    for name in PLANNER_SUITE_VALUES:
        assert hasattr(settings, name), name


def test_the_preset_bars_are_bound_to_pages_that_exist() -> None:
    """A bar is prepended by page NAME, so a name nothing resolves to renders no
    bar at all -- no error, no widget. The planner bar shipped that way for eleven
    days pointing at a "Campaign Doctrine" page the dialog never builds.
    """
    pages = set(Settings.pages())
    assert PLANNER_SUITE_PAGE in pages
    assert DIFFICULTY_REALISM_PAGE in pages
