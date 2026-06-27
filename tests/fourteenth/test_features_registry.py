"""The 414th feature registry must stay honest.

These tests turn registry drift into a CI failure: a renamed Settings field, a
removed plugin, or a stale generated wiring-map all go red here instead of
silently rotting a doc.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from game.fourteenth.features import (
    FEATURE_INDEX_DOC,
    FEATURES,
    render_feature_index,
)
from game.settings.settings import Settings


def _settings_field_names() -> set[str]:
    return {field.name for field in dataclasses.fields(Settings)}


def _plugin_ids() -> set[str]:
    return set(json.loads(Path("resources/plugins/plugins.json").read_text()))


def test_keys_are_unique() -> None:
    keys = [feature.key for feature in FEATURES]
    assert len(keys) == len(set(keys)), "duplicate Feature.key"


def test_settings_fields_exist() -> None:
    names = _settings_field_names()
    for feature in FEATURES:
        for field_name in feature.settings_fields:
            assert (
                field_name in names
            ), f"{feature.key}: '{field_name}' is not a Settings field"


def test_plugin_ids_exist() -> None:
    ids = _plugin_ids()
    for feature in FEATURES:
        if feature.plugin_id is not None:
            assert (
                feature.plugin_id in ids
            ), f"{feature.key}: '{feature.plugin_id}' is not a registered plugin"


def test_every_feature_has_wiring() -> None:
    # The registry's scope is features WITH concrete wiring. An entry with
    # neither a plugin nor a setting belongs in the prose docs, not here.
    for feature in FEATURES:
        assert feature.plugin_id or feature.settings_fields, (
            f"{feature.key} has no plugin and no settings — it does not belong "
            "in the wiring registry"
        )


def test_doc_sections_are_positive() -> None:
    for feature in FEATURES:
        if feature.doc_section is not None:
            assert feature.doc_section > 0, f"{feature.key}: bad doc_section"


def test_generated_wiring_map_is_current() -> None:
    actual = Path(FEATURE_INDEX_DOC).read_text(encoding="utf-8")
    assert actual == render_feature_index(), (
        f"{FEATURE_INDEX_DOC} is stale; regenerate with "
        "`python -m game.fourteenth.features`"
    )
