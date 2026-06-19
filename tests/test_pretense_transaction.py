from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from game.game import Game
from game.pretense import pretensemissiongenerator
from game.pretense.pretensemissiongenerator import PretenseMissionGenerator


def test_generation_failure_restores_original_game_in_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game = cast(Game, cast(Any, SimpleNamespace(marker="original")))
    generator = object.__new__(PretenseMissionGenerator)
    generator.game = game
    generator.generation_started = False

    def fail_after_mutation() -> None:
        setattr(generator.game, "marker", "mutated")
        raise RuntimeError("generation failed")

    generator.setup_mission_coalitions = fail_after_mutation  # type: ignore[method-assign]
    monkeypatch.setattr(
        pretensemissiongenerator,
        "pre_pretense_backups_dir",
        lambda: tmp_path,
    )
    emitted: list[Game] = []
    signal = SimpleNamespace(game_loaded=SimpleNamespace(emit=emitted.append))
    monkeypatch.setattr(
        pretensemissiongenerator.GameUpdateSignal,
        "get_instance",
        lambda: signal,
    )

    with pytest.raises(RuntimeError, match="generation failed"):
        generator.generate_miz(tmp_path / "pretense.miz")

    assert generator.game is game
    assert getattr(game, "marker") == "original"
    assert not hasattr(game, "pretense_ground_supply")
    assert emitted == [game]
