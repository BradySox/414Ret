from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from game.customkneeboard import CustomKneeboard
from game.missiongenerator.kneeboard import KneeboardGenerator


def _generator(mission: Any) -> KneeboardGenerator:
    # Bypass __init__ (needs a full mission/game); we only exercise the pure
    # scope-routing helper, which touches self.mission only.
    gen = KneeboardGenerator.__new__(KneeboardGenerator)
    gen.mission = mission
    return gen


def test_custom_kneeboard_scope_label() -> None:
    assert CustomKneeboard("a", b"x").scope_label == "All flights"
    assert CustomKneeboard("a", b"x", "FA-18C_hornet").scope_label == "FA-18C_hornet"


def test_inject_custom_kneeboards_routes_by_scope(tmp_path: Path) -> None:
    mission = SimpleNamespace(custom_kneeboards=defaultdict(list))
    gen = _generator(mission)

    boards = [
        CustomKneeboard("all.png", b"\x89PNG-all", airframe_id=None),
        CustomKneeboard("hornet.png", b"\x89PNG-hornet", airframe_id="FA-18C_hornet"),
    ]
    gen._inject_custom_kneeboards(boards, tmp_path)

    # "" key = every client flight; the airframe id = that type only.
    assert len(mission.custom_kneeboards[""]) == 1
    assert len(mission.custom_kneeboards["FA-18C_hornet"]) == 1

    all_path = mission.custom_kneeboards[""][0]
    hornet_path = mission.custom_kneeboards["FA-18C_hornet"][0]
    # Bytes are written to disk for pydcs to pick up at save time.
    assert all_path.read_bytes() == b"\x89PNG-all"
    assert hornet_path.read_bytes() == b"\x89PNG-hornet"
    assert all_path.parent == tmp_path / "_custom"


def test_inject_custom_kneeboards_noop_when_empty(tmp_path: Path) -> None:
    mission = SimpleNamespace(custom_kneeboards=defaultdict(list))
    _generator(mission)._inject_custom_kneeboards([], tmp_path)
    assert not mission.custom_kneeboards
    assert not (tmp_path / "_custom").exists()
