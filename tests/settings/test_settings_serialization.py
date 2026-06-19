import json

import pytest

from game.settings.settings import NightMissions, Settings, TargetIntelPrecision


def test_settings_enum_json_round_trip() -> None:
    settings = Settings()
    settings.night_day_missions = NightMissions.OnlyNight

    encoded = json.dumps(settings.__dict__, default=settings.default_json)
    decoded = json.loads(encoded, object_hook=settings.obj_hook)
    restored = Settings.deserialize_state_dict(decoded)

    assert restored["night_day_missions"] is NightMissions.OnlyNight


def test_campaign_style_enum_string_is_deserialized() -> None:
    restored = Settings.deserialize_state_dict(
        {"target_intel_precision": "TargetIntelPrecision.APPROXIMATE"}
    )

    assert restored["target_intel_precision"] is TargetIntelPrecision.APPROXIMATE


@pytest.mark.parametrize(
    "payload",
    [
        {"Enum": "__import__('os').system('echo unsafe')"},
        {"Enum": "UnknownEnum.VALUE"},
        {"Enum": "NightMissions.Unknown"},
        {"Enum": 42},
    ],
)
def test_object_hook_rejects_untrusted_enum_payloads(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        Settings.obj_hook(payload)


def test_campaign_enum_must_match_the_setting_type() -> None:
    with pytest.raises(ValueError):
        Settings.deserialize_state_dict(
            {"target_intel_precision": "NightMissions.OnlyNight"}
        )
