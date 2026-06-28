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
            "perf_red_alert_state": True,
        }
    )

    assert "prefer_squadrons_with_matching_primary_task" not in migrated
    assert "pretense_num_of_cargo_planes" not in migrated
    assert "nevatim_parking_fix" not in migrated
    assert "only_player_takeoff" not in migrated
    # Removed once the IADS engine (MANTIS/Skynet) became the SAM-emissions owner.
    assert "perf_red_alert_state" not in migrated


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
    assert "perf_red_alert_state" not in names
    # The per-base-type ground-start truck toggles were consolidated.
    assert "ground_start_trucks_roadbase" not in names
    assert "ground_start_ground_power_trucks_roadbase" not in names


def test_ground_start_truck_toggles_merge_either_base_type() -> None:
    # A save that enabled trucks at *either* base type keeps them enabled after
    # the airbase/roadbase toggles are consolidated into one.
    enabled_at_roadbase_only = Settings._migrate_legacy_settings(
        {"ground_start_trucks": False, "ground_start_trucks_roadbase": True}
    )
    assert enabled_at_roadbase_only["ground_start_trucks"] is True
    assert "ground_start_trucks_roadbase" not in enabled_at_roadbase_only

    enabled_at_airbase_only = Settings._migrate_legacy_settings(
        {"ground_start_trucks": True, "ground_start_trucks_roadbase": False}
    )
    assert enabled_at_airbase_only["ground_start_trucks"] is True

    disabled_everywhere = Settings._migrate_legacy_settings(
        {"ground_start_trucks": False, "ground_start_trucks_roadbase": False}
    )
    assert disabled_everywhere["ground_start_trucks"] is False


def test_ground_power_truck_toggles_merge_either_base_type() -> None:
    # Same consolidation for the ground-power trucks (which default ON). A save
    # that turned them off at *both* base types stays off; otherwise on.
    off_at_both = Settings._migrate_legacy_settings(
        {
            "ground_start_ground_power_trucks": False,
            "ground_start_ground_power_trucks_roadbase": False,
        }
    )
    assert off_at_both["ground_start_ground_power_trucks"] is False
    assert "ground_start_ground_power_trucks_roadbase" not in off_at_both

    off_at_roadbase_only = Settings._migrate_legacy_settings(
        {
            "ground_start_ground_power_trucks": True,
            "ground_start_ground_power_trucks_roadbase": False,
        }
    )
    assert off_at_roadbase_only["ground_start_ground_power_trucks"] is True
