"""The §18 fog-of-war reveal must never leak into generated missions.

The reveal toggle short-circuits ``known_for`` (and the other fog leaves) to
ground truth for any viewer. Mission generation reads those same leaves for
shared artifacts — the kneeboard threat pages and the §74 DTC threat rings —
so a host generating with the overview ticked used to hand every client the
god-view (the flown 2026-07-19 report: 40 exact SAM rings in a cartridge on a
turn where blue had scouted 0 of 87 sites). Generation now runs inside
``fog_intact()``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from game.missiongenerator.missiongenerator import MissionGenerator
from game.theater import fogofwar


@pytest.fixture(autouse=True)
def _fog_off_after() -> Any:
    yield
    fogofwar.set_fog_revealed(False)


def test_fog_intact_suppresses_and_restores() -> None:
    fogofwar.set_fog_revealed(True)
    with fogofwar.fog_intact():
        assert not fogofwar.fog_revealed()
        # Nesting stays suppressed and unwinds correctly.
        with fogofwar.fog_intact():
            assert not fogofwar.fog_revealed()
        assert not fogofwar.fog_revealed()
    assert fogofwar.fog_revealed()


def test_fog_intact_restores_on_exception() -> None:
    fogofwar.set_fog_revealed(True)
    with pytest.raises(RuntimeError):
        with fogofwar.fog_intact():
            raise RuntimeError("boom")
    assert fogofwar.fog_revealed()


def test_generation_runs_with_the_fog_intact(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, bool] = {}

    def fake_body(self: MissionGenerator, output: Path) -> str:
        seen["revealed_during_generation"] = fogofwar.fog_revealed()
        return "unit-map"

    monkeypatch.setattr(MissionGenerator, "_generate_miz", fake_body)
    generator = object.__new__(MissionGenerator)
    fogofwar.set_fog_revealed(True)
    result = generator.generate_miz(Path("unused.miz"))
    assert result == "unit-map"
    assert seen["revealed_during_generation"] is False
    # The player's map overview survives generation untouched.
    assert fogofwar.fog_revealed()
