from dcs.cloud_presets import CLOUD_PRESETS

from game.settings import Settings
from game.settings.settings import CloudPresetPack
from pydcs_extensions import AtmosXClouds, BanditClouds, Weather2Clouds


def test_default_is_stock_presets() -> None:
    assert Settings().cloud_preset_pack is CloudPresetPack.NONE


def test_legacy_bandit_boolean_migrates_to_the_pack_choice() -> None:
    on = Settings._migrate_legacy_settings({"use_bandit_clouds": True})
    assert on["cloud_preset_pack"] is CloudPresetPack.BANDIT
    assert "use_bandit_clouds" not in on

    off = Settings._migrate_legacy_settings({"use_bandit_clouds": False})
    assert off["cloud_preset_pack"] is CloudPresetPack.NONE
    assert "use_bandit_clouds" not in off


def test_migration_never_stomps_an_existing_pack() -> None:
    migrated = Settings._migrate_legacy_settings(
        {
            "use_bandit_clouds": True,
            "cloud_preset_pack": CloudPresetPack.ATMOSX,
        }
    )
    assert migrated["cloud_preset_pack"] is CloudPresetPack.ATMOSX
    assert "use_bandit_clouds" not in migrated


def test_a_legacy_save_loads_with_the_pack_set() -> None:
    settings = Settings()
    settings.__setstate__({"use_bandit_clouds": True})
    assert settings.cloud_preset_pack is CloudPresetPack.BANDIT
    assert "use_bandit_clouds" not in settings.__dict__


def test_pack_is_user_visible_and_the_boolean_is_not() -> None:
    names = {
        name
        for page in Settings.pages()
        for section in Settings.sections(page)
        for name, _description in Settings.fields(page, section)
    }
    assert "cloud_preset_pack" in names
    assert "use_bandit_clouds" not in names


def test_the_pack_choice_survives_a_save_round_trip() -> None:
    # The enum has to be in the safe deserialization registry, or a saved choice
    # silently falls back to the field default on load.
    restored = Settings.deserialize_state_dict(
        {"cloud_preset_pack": {"Enum": "CloudPresetPack.WEATHER2"}}
    )
    assert restored["cloud_preset_pack"] is CloudPresetPack.WEATHER2


def test_only_one_pack_is_ever_injected() -> None:
    # The packs reuse the same PresetN keys for different clouds, so a switch must
    # eject the previous pack rather than layering on top of it.
    packs = (BanditClouds, Weather2Clouds, AtmosXClouds)
    for pack in packs:
        pack.deactivate()
    stock = dict(CLOUD_PRESETS)

    try:
        for pack in packs:
            for other in packs:
                if other is not pack:
                    other.deactivate()
            pack.activate()
            assert len(CLOUD_PRESETS) == len(stock) + len(list(pack))
            assert CLOUD_PRESETS["Preset35"] in list(pack)
    finally:
        for pack in packs:
            pack.deactivate()

    assert CLOUD_PRESETS == stock
