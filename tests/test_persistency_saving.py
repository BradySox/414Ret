from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from game import persistency
from game.game import Game


class PreparedLandmap:
    def __init__(self) -> None:
        self.prepare_calls = 0

    def prepare(self) -> None:
        self.prepare_calls += 1


def fake_game(savepath: str = "") -> tuple[Game, PreparedLandmap]:
    landmap = PreparedLandmap()
    game = SimpleNamespace(
        savepath=savepath,
        theater=SimpleNamespace(landmap=landmap),
    )
    return cast(Game, cast(Any, game)), landmap


def test_save_failure_restores_landmap_and_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "campaign.retribution"
    destination.write_bytes(b"known-good-save")
    game, landmap = fake_game(str(destination))

    def fail_dump(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(persistency.pickle, "dump", fail_dump)

    assert not persistency.save_game(game)
    assert game.theater.landmap is landmap
    assert landmap.prepare_calls == 1
    assert destination.read_bytes() == b"known-good-save"
    assert not (tmp_path / ".campaign.retribution.tmp").exists()


def test_save_as_failure_preserves_previous_savepath(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    previous = tmp_path / "previous.retribution"
    destination = tmp_path / "new.retribution"
    game, _ = fake_game(str(previous))
    monkeypatch.setattr(
        persistency.pickle,
        "dump",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )

    assert not persistency.save_game(game, destination)
    assert game.savepath == str(previous)


def test_successful_save_is_atomic_and_updates_savepath(tmp_path: Path) -> None:
    destination = tmp_path / "campaign.retribution"
    destination.write_bytes(b"old")
    game, landmap = fake_game()

    assert persistency.save_game(game, destination)
    assert game.savepath == str(destination)
    assert game.theater.landmap is landmap
    assert landmap.prepare_calls == 1
    assert destination.read_bytes() != b"old"
    assert not (tmp_path / ".campaign.retribution.tmp").exists()
