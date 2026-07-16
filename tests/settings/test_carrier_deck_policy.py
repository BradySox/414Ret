from game.settings import CarrierDeckPolicy, Settings


def test_default_is_last_resort() -> None:
    assert Settings().carrier_deck_policy is CarrierDeckPolicy.LAST_RESORT


def test_legacy_sixpack_boolean_migrates_to_policy() -> None:
    # ON exempted player flights from the off-six-pack placement delay, so they
    # filled the six-pack: that intent maps to SIXPACK_FIRST. OFF already
    # behaved like the last-resort policy.
    on = Settings._migrate_legacy_settings({"player_flights_sixpack": True})
    assert on["carrier_deck_policy"] is CarrierDeckPolicy.SIXPACK_FIRST
    assert "player_flights_sixpack" not in on

    off = Settings._migrate_legacy_settings({"player_flights_sixpack": False})
    assert off["carrier_deck_policy"] is CarrierDeckPolicy.LAST_RESORT
    assert "player_flights_sixpack" not in off


def test_migration_never_stomps_an_existing_policy() -> None:
    migrated = Settings._migrate_legacy_settings(
        {
            "player_flights_sixpack": True,
            "carrier_deck_policy": CarrierDeckPolicy.LAST_RESORT,
        }
    )
    assert migrated["carrier_deck_policy"] is CarrierDeckPolicy.LAST_RESORT
    assert "player_flights_sixpack" not in migrated


def test_policy_is_user_visible_and_the_boolean_is_not() -> None:
    names = {
        name
        for page in Settings.pages()
        for section in Settings.sections(page)
        for name, _description in Settings.fields(page, section)
    }
    assert "carrier_deck_policy" in names
    assert "player_flights_sixpack" not in names
