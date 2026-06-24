"""Settings scaffolding for the Skynet -> MANTIS IADS engine migration.

The ``iads_engine`` field defaults to Skynet (so the eventual cutover is a
setting flip, not a save-schema change) and is now exposed as an experimental UI
choice so the MANTIS engine can be selected for its in-game pass. See
docs/dev/design/414th-mantis-migration-notes.md.
"""

from game.settings import IadsEngine, Settings


def test_iads_engine_defaults_to_skynet() -> None:
    # Old saves backfill to this default via Settings.__setstate__.
    assert Settings().iads_engine is IadsEngine.SKYNET


def test_iads_engine_values() -> None:
    assert IadsEngine.SKYNET.value == "skynet"
    assert IadsEngine.MANTIS.value == "mantis"


def test_saved_iads_engine_survives_migration() -> None:
    # A non-default value persisted in an existing save must not be stripped.
    migrated = Settings._migrate_legacy_settings({"iads_engine": IadsEngine.MANTIS})
    assert migrated["iads_engine"] is IadsEngine.MANTIS


def test_iads_engine_is_user_visible() -> None:
    # Now that MANTIS is a real (if experimental) engine, the selector is a UI
    # choice so it can be picked for the in-game pass.
    names = {
        name
        for page in Settings.pages()
        for section in Settings.sections(page)
        for name, _description in Settings.fields(page, section)
    }
    assert "iads_engine" in names
