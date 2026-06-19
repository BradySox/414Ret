from game.settings import AiRadioBehavior, Settings


def test_ai_radio_behavior_defaults_to_limited() -> None:
    assert Settings().ai_radio_behavior is AiRadioBehavior.LIMITED


def test_legacy_radio_booleans_migrate_to_single_choice() -> None:
    assert (
        Settings._migrate_legacy_settings(
            {"limit_ai_radios": False, "silence_ai_radios": False}
        )["ai_radio_behavior"]
        is AiRadioBehavior.FULL
    )
    assert (
        Settings._migrate_legacy_settings(
            {"limit_ai_radios": True, "silence_ai_radios": False}
        )["ai_radio_behavior"]
        is AiRadioBehavior.LIMITED
    )
    assert (
        Settings._migrate_legacy_settings(
            {"limit_ai_radios": True, "silence_ai_radios": True}
        )["ai_radio_behavior"]
        is AiRadioBehavior.SILENT
    )


def test_obsolete_settings_are_discarded_during_migration() -> None:
    migrated = Settings._migrate_legacy_settings(
        {
            "prefer_squadrons_with_matching_primary_task": True,
            "pretense_num_of_cargo_planes": 12,
            "nevatim_parking_fix": True,
            "only_player_takeoff": False,
        }
    )

    assert "prefer_squadrons_with_matching_primary_task" not in migrated
    assert "pretense_num_of_cargo_planes" not in migrated
    assert "nevatim_parking_fix" not in migrated
    assert "only_player_takeoff" not in migrated


def test_obsolete_settings_are_not_user_visible() -> None:
    names = {
        name
        for page in Settings.pages()
        for section in Settings.sections(page)
        for name, _description in Settings.fields(page, section)
    }

    assert "ai_radio_behavior" in names
    assert "limit_ai_radios" not in names
    assert "silence_ai_radios" not in names
    assert "prefer_squadrons_with_matching_primary_task" not in names
    assert "pretense_num_of_cargo_planes" not in names
    assert "nevatim_parking_fix" not in names
