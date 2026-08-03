from __future__ import annotations

from dataclasses import fields

from game.settings import Settings
from game.settings.optiondescription import SETTING_DESCRIPTION_KEY
from game.settings.settings import FIELD_LAYOUT, HIDDEN_FIELDS


def _user_field_names() -> set[str]:
    return {
        f.name
        for f in fields(Settings)
        if SETTING_DESCRIPTION_KEY in f.metadata and f.name not in HIDDEN_FIELDS
    }


def test_field_layout_covers_every_user_field_exactly_once() -> None:
    # A missing field would vanish from the UI; an extra key would be a typo.
    assert set(FIELD_LAYOUT) == _user_field_names()
    assert len(FIELD_LAYOUT) == len(_user_field_names())


def test_ui_walk_emits_every_field_exactly_once() -> None:
    emitted: list[str] = []
    for page in Settings.pages():
        for section in Settings.sections(page):
            emitted += [name for name, _ in Settings.fields(page, section)]
    assert sorted(emitted) == sorted(_user_field_names())
    assert len(emitted) == len(set(emitted))  # no field shown on two pages


def test_pages_are_in_the_designed_order() -> None:
    assert list(Settings.pages()) == [
        "Difficulty & Realism",
        "Air Doctrine",
        "Campaign Management",
        "Mission Generation",
        "Kneeboards",
        "Vietnam Ops",
        "Performance",
        # Last on purpose: the per-feature on/off gates, lifted off the topical
        # pages so those hold choices rather than a mix of choices and switches.
        "414th Features",
    ]


def test_no_grab_bag_sections_remain() -> None:
    # The reorg's whole point: kill the 30+-item "General"/"Gameplay" dumping
    # grounds. Assert no section exceeds a sane size.
    for page in Settings.pages():
        for section in Settings.sections(page):
            count = len(list(Settings.fields(page, section)))
            assert count <= 13, f"{page} / {section} has {count} settings"


def test_hidden_fields_are_real_dataclass_fields_but_never_shown() -> None:
    # §57 (air-droppable minefields) is SHELVED: the fields must keep existing so a
    # saved settings file with them True still deserializes and the (dormant) code
    # can still read them -- but they must never appear on any settings surface.
    all_declared = {
        f.name for f in fields(Settings) if SETTING_DESCRIPTION_KEY in f.metadata
    }
    for name in HIDDEN_FIELDS:
        assert name in all_declared, f"{name} must stay a declared Settings field"
        assert name not in FIELD_LAYOUT
    emitted: set[str] = set()
    for page in Settings.pages():
        for section in Settings.sections(page):
            emitted.update(name for name, _ in Settings.fields(page, section))
    assert emitted.isdisjoint(HIDDEN_FIELDS)


def test_unlisted_field_falls_back_to_its_metadata() -> None:
    # A field not in FIELD_LAYOUT must still resolve (to its own metadata) so it
    # is never dropped from the UI.
    sample = next(iter(_user_field_names()))
    description = Settings._field_description(
        next(f for f in fields(Settings) if f.name == sample)
    )
    page, section = Settings._effective_layout("not_a_real_field", description)
    assert (page, section) == (description.page, description.section)
