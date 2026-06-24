"""Settings scaffolding for the Skynet -> MANTIS IADS engine migration.

The ``iads_engine`` field is persisted now (defaulting to Skynet) so that the
eventual cutover is a setting flip rather than a save-schema change. It is
deliberately *internal* -- not a user-facing choice -- until the MANTIS bridge
lands, because only Skynet is implemented today. See
docs/dev/design/414th-mantis-migration-notes.md §7.
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


def test_iads_engine_is_not_user_visible() -> None:
    # Intentionally internal until the MANTIS emitter exists; exposing a MANTIS
    # choice that does nothing would be a trap. Guards against accidental UI
    # exposure landing without a deliberate change here.
    names = {
        name
        for page in Settings.pages()
        for section in Settings.sections(page)
        for name, _description in Settings.fields(page, section)
    }
    assert "iads_engine" not in names
