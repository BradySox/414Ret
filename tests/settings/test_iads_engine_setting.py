"""Settings coverage for the Skynet -> MANTIS IADS engine migration.

MANTIS is now the default engine for new campaigns (after passing the G6 in-game
pass); Skynet remains a supported choice. Existing campaigns must keep the engine
they were created with -- a save predating the ``iads_engine`` field is explicitly
pinned to Skynet in ``Settings.__setstate__`` so the default flip never swaps a
running campaign's engine. See docs/dev/design/414th-mantis-migration-notes.md.
"""

from typing import Any

from game.settings import IadsEngine, Settings


def _load_from_state(raw: dict[str, Any]) -> Settings:
    """Simulate unpickling a save with the given raw __dict__ state."""
    settings = Settings.__new__(Settings)
    settings.__setstate__(raw)
    return settings


def test_iads_engine_defaults_to_mantis() -> None:
    # New campaigns get MANTIS.
    assert Settings().iads_engine is IadsEngine.MANTIS


def test_iads_engine_values() -> None:
    assert IadsEngine.SKYNET.value == "skynet"
    assert IadsEngine.MANTIS.value == "mantis"


def test_saved_iads_engine_survives_migration() -> None:
    # A non-default value persisted in an existing save must not be stripped.
    migrated = Settings._migrate_legacy_settings({"iads_engine": IadsEngine.SKYNET})
    assert migrated["iads_engine"] is IadsEngine.SKYNET


def test_pre_field_save_pinned_to_skynet() -> None:
    # A save created before the iads_engine field existed (key absent from the
    # raw state) must load as Skynet, NOT inherit the new MANTIS default --
    # otherwise the default flip would silently switch a running campaign.
    loaded = _load_from_state({})
    assert loaded.iads_engine is IadsEngine.SKYNET


def test_existing_engine_choice_preserved_on_load() -> None:
    # A save that already carries an explicit engine choice is left untouched by
    # the migration pin (both directions).
    assert _load_from_state({"iads_engine": IadsEngine.MANTIS}).iads_engine is (
        IadsEngine.MANTIS
    )
    assert _load_from_state({"iads_engine": IadsEngine.SKYNET}).iads_engine is (
        IadsEngine.SKYNET
    )


def test_iads_engine_is_user_visible() -> None:
    names = {
        name
        for page in Settings.pages()
        for section in Settings.sections(page)
        for name, _description in Settings.fields(page, section)
    }
    assert "iads_engine" in names
