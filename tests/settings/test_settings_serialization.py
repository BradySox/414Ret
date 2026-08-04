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


def test_campaign_enum_wrong_type_falls_back_to_default() -> None:
    # A serialized value whose enum type does not match the setting's field type
    # is a stale/garbled save. It must not be assigned (and must never crash the
    # load); the field falls back to its default instead.
    restored = Settings.deserialize_state_dict(
        {"target_intel_precision": "NightMissions.OnlyNight"}
    )

    assert restored["target_intel_precision"] is TargetIntelPrecision.EXACT


def test_save_settings_survives_the_campaign_preseed_record() -> None:
    """Save Settings died with "Circular reference detected" on any campaign game.

    The New Game wizard records which fields a campaign pre-seeded as a frozenset
    in ``Settings.__dict__``. json cannot encode a set, so it called ``default_json``
    -- which handed the same object back, and json read that as a container of
    itself. The error named nothing useful; the real fix is encoding the set.
    """
    settings = Settings()
    settings.record_campaign_preseeds(["convoy_ambush", "coin_insurgency"])

    encoded = json.dumps(settings.__dict__, default=settings.default_json)
    decoded = json.loads(encoded, object_hook=settings.obj_hook)

    reloaded = Settings()
    reloaded.__setstate__(decoded)
    assert reloaded.campaign_preseeded_fields() == frozenset(
        {"convoy_ambush", "coin_insurgency"}
    )


def test_sets_encode_in_a_stable_order() -> None:
    """A settings file must not churn between runs just because a set reordered."""
    settings = Settings()
    settings.record_campaign_preseeds(["convoy_ambush", "coin_insurgency"])
    assert settings.default_json(settings.campaign_preseeded_fields()) == [
        "coin_insurgency",
        "convoy_ambush",
    ]


def test_an_unencodable_value_names_itself() -> None:
    """Returning the object unchanged turned every such bug into "circular
    reference". json's contract is to raise TypeError, which names the type."""
    with pytest.raises(TypeError, match="object"):
        json.dumps({"bad": object()}, default=Settings.default_json)
