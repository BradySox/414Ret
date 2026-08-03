"""The settings dialog's filter bar, advanced disclosure, and Features page.

The settings surface had grown to 200+ options across seven pages with no way to
ask for one by name, and every per-feature kill switch filed on whichever topical
page looked closest. These tests drive the *real* Qt widgets under the offscreen
platform (the ``test_settings_dependencies`` pattern) so the behaviour is pinned
against Qt's actual visibility/enabled semantics rather than a reimplementation.
"""

from __future__ import annotations

import os
from typing import Any, Iterator

import pytest

from game.settings import Settings
from game.settings.settings import (
    FEATURE_GATE_FIELDS,
    FEATURES_PAGE,
    HIDDEN_FIELDS,
    _FEATURE_GATE_NAMES,
)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# --- layout / registry invariants (no Qt needed) -----------------------------------


def test_every_field_survives_the_features_page_move() -> None:
    """Relocating the gates must not drop or duplicate a single option."""
    settings = Settings()
    seen: list[str] = []
    for page in settings.pages():
        for section in settings.sections(page):
            for name, _description in settings.fields(page, section):
                seen.append(name)
    assert len(seen) == len(set(seen)), "a field is rendered on two pages"

    expected = {f.name for f in Settings._user_fields()}
    assert set(seen) == expected


def test_feature_gates_live_on_the_features_page() -> None:
    settings = Settings()
    on_features_page = {
        name
        for section in settings.sections(FEATURES_PAGE)
        for name, _ in settings.fields(FEATURES_PAGE, section)
    }
    assert on_features_page == set(_FEATURE_GATE_NAMES)


def test_feature_gate_list_matches_the_registry() -> None:
    """The literal in settings.py must track game/fourteenth/features.py.

    settings.py cannot import the registry (game/__init__ already imports
    settings, so it would be circular), so the list is a literal kept honest
    here -- the same registry-plus-test discipline as the feature index.
    """
    from game.fourteenth.features import FEATURES

    settings = Settings()
    vietnam_page_fields = {
        name
        for section in settings.sections("Vietnam Ops")
        for name, _ in settings.fields("Vietnam Ops", section)
    }

    registry_bool_gates = set()
    for feature in FEATURES:
        for field_name in feature.settings_fields:
            if field_name in HIDDEN_FIELDS:
                continue
            if not isinstance(getattr(settings, field_name, None), bool):
                continue
            # The Vietnam Ops page is already a scoped features page; its gates
            # deliberately stay there rather than being re-listed.
            if field_name in vietnam_page_fields:
                continue
            registry_bool_gates.add(field_name)

    assert set(_FEATURE_GATE_NAMES) == registry_bool_gates, (
        "FEATURE_GATE_FIELDS has drifted from the feature registry; add the new "
        "feature's boolean gate to a section in game/settings/settings.py"
    )


def test_feature_gates_are_all_booleans() -> None:
    settings = Settings()
    for section, names in FEATURE_GATE_FIELDS.items():
        for name in names:
            assert isinstance(
                getattr(settings, name), bool
            ), f"{name} in Features section {section!r} is not a toggle"


# --- basic / advanced classification ------------------------------------------------


def test_numeric_knobs_are_advanced_and_choices_are_not() -> None:
    settings = Settings()
    for page in settings.pages():
        for section in settings.sections(page):
            for name, description in settings.fields(page, section):
                advanced = Settings.is_advanced(name, description)
                if isinstance(getattr(settings, name), bool):
                    # Booleans are basic unless explicitly listed as expert aids.
                    assert advanced == (
                        name
                        in {
                            "combat_sar_test_force_capture",
                            "combat_sar_test_easy_rescue",
                            "switch_baro_fix",
                            "ground_start_scenery_remove_triggers",
                        }
                    ), name


def test_difficulty_economy_dials_stay_basic() -> None:
    """The preset bar drives these, so the page must not bury them."""
    settings = Settings()
    for page in settings.pages():
        for section in settings.sections(page):
            for name, description in settings.fields(page, section):
                if name in ("player_income_multiplier", "enemy_income_multiplier"):
                    assert not Settings.is_advanced(name, description)


def test_no_feature_gate_is_advanced() -> None:
    """A feature's on/off switch is never buried behind a disclosure."""
    settings = Settings()
    for section in settings.sections(FEATURES_PAGE):
        for name, description in settings.fields(FEATURES_PAGE, section):
            assert not Settings.is_advanced(name, description), name


# --- is_default / campaign preseeds -------------------------------------------------


def test_is_default_tracks_changes() -> None:
    settings = Settings()
    assert settings.is_default("player_income_multiplier")
    settings.player_income_multiplier = 9.5
    assert not settings.is_default("player_income_multiplier")


def test_is_default_is_safe_for_unknown_fields() -> None:
    """The filter must never hide a row by erroring on it."""
    assert Settings().is_default("no_such_setting")


def test_campaign_preseeds_round_trip_and_ignore_unknown_names() -> None:
    settings = Settings()
    assert settings.campaign_preseeded_fields() == frozenset()
    settings.record_campaign_preseeds(["convoy_ambush", "bogus_key"])
    assert settings.campaign_preseeded_fields() == frozenset({"convoy_ambush"})


def test_campaign_preseed_key_is_not_a_setting() -> None:
    """It lives in __dict__, so it must not leak into the settings UI."""
    settings = Settings()
    settings.record_campaign_preseeds(["convoy_ambush"])
    rendered = {
        name
        for page in settings.pages()
        for section in settings.sections(page)
        for name, _ in settings.fields(page, section)
    }
    assert "_campaign_preseeded_fields" not in rendered


# --- the real Qt widgets ------------------------------------------------------------


@pytest.fixture(scope="module")
def qt_app() -> Iterator[object]:
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


class _Container:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings


def _group(
    qt_app: object, settings: Settings, page: str, section: str
) -> tuple[Any, Any]:
    from qt_ui.windows.settings.QSettingsWindow import AutoSettingsGroup, SettingsFilter

    settings_filter = SettingsFilter()
    group = AutoSettingsGroup(
        page,
        section,
        _Container(settings),  # type: ignore[arg-type]
        lambda: None,
        settings_filter,
    )
    return group, settings_filter


def _find_section_with_advanced(settings: Settings) -> tuple[str, str]:
    for page in settings.pages():
        for section in settings.sections(page):
            fields = list(settings.fields(page, section))
            has_advanced = any(Settings.is_advanced(n, d) for n, d in fields)
            has_basic = any(not Settings.is_advanced(n, d) for n, d in fields)
            if has_advanced and has_basic:
                return page, section
    raise AssertionError("no mixed basic/advanced section to test")


def test_advanced_rows_are_hidden_until_disclosed(qt_app: object) -> None:
    settings = Settings()
    page, section = _find_section_with_advanced(settings)
    group, _filter = _group(qt_app, settings, page, section)

    advanced = sorted(group.grid.advanced_names)
    assert advanced, "fixture picked a section with no advanced fields"
    for name in advanced:
        assert not group.grid.labels_map[name].isVisible()
    assert group.disclosure.isVisible()

    group._toggle_advanced()
    for name in advanced:
        assert group.grid.labels_map[name].isVisible()


def test_search_reaches_advanced_rows_without_disclosing(qt_app: object) -> None:
    """Typing a knob's name must find it, not tell you it's behind a link."""
    settings = Settings()
    page, section = _find_section_with_advanced(settings)
    group, settings_filter = _group(qt_app, settings, page, section)

    target = sorted(group.grid.advanced_names)[0]
    settings_filter.query = target.casefold()
    group.apply_filter()

    assert group.grid.labels_map[target].isVisible()
    assert not group.disclosure.isVisible()


def test_search_hides_non_matching_rows_and_empty_sections(qt_app: object) -> None:
    settings = Settings()
    page, section = _find_section_with_advanced(settings)
    group, settings_filter = _group(qt_app, settings, page, section)

    settings_filter.query = "zzz-no-such-setting-zzz"
    assert group.apply_filter() == 0
    assert not group.isVisible()


def test_modified_only_filters_to_changed_values(qt_app: object) -> None:
    from qt_ui.windows.settings.QSettingsWindow import SettingsFilter

    settings = Settings()
    settings_filter = SettingsFilter(modified_only=True)
    for page in settings.pages():
        for section in settings.sections(page):
            for name, description in settings.fields(page, section):
                assert not settings_filter.matches(name, description, settings)

    settings.player_income_multiplier = 9.5
    matched = [
        name
        for page in settings.pages()
        for section in settings.sections(page)
        for name, description in settings.fields(page, section)
        if settings_filter.matches(name, description, settings)
    ]
    assert matched == ["player_income_multiplier"]


def test_search_terms_narrow_rather_than_widen() -> None:
    from qt_ui.windows.settings.QSettingsWindow import SettingsFilter

    settings = Settings()
    descriptions = {
        name: description
        for page in settings.pages()
        for section in settings.sections(page)
        for name, description in settings.fields(page, section)
    }

    def hits(query: str) -> set[str]:
        settings_filter = SettingsFilter(query=query)
        return {
            name
            for name, description in descriptions.items()
            if settings_filter.matches(name, description, settings)
        }

    carrier = hits("carrier")
    assert carrier
    assert hits("carrier deck") <= carrier


def test_campaign_badge_renders_and_clears(qt_app: object) -> None:
    settings = Settings()
    page, section = FEATURES_PAGE, next(iter(Settings().sections(FEATURES_PAGE)))
    name = next(iter(dict(settings.fields(page, section))))

    group, _filter = _group(qt_app, settings, page, section)
    assert "SET BY CAMPAIGN" not in group.grid.labels_map[name].text()

    settings.record_campaign_preseeds([name])
    group.update_from_settings()
    assert "SET BY CAMPAIGN" in group.grid.labels_map[name].text()
