"""Guards for tools/will_pacing_model.py -- the offline will-pacing projector.

Two things: (1) the tool mirrors the real WillWeights defaults in a plain dict (it is
standalone, pyyaml-only, no game import), so this asserts the mirror can never silently
drift from the dataclass; (2) a smoke test that the model loads the shipped Yankee
Station campaign and its three archetypes bracket the arc as designed (elite/average
break Hanoi, a floundering war breaks Washington first).
"""

from __future__ import annotations

import dataclasses
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

from game.fourteenth.political_will import WillWeights

_REPO = Path(__file__).resolve().parents[2]


def _load_tool() -> Any:
    spec = importlib.util.spec_from_file_location(
        "will_pacing_model", _REPO / "tools" / "will_pacing_model.py"
    )
    assert spec and spec.loader
    module: Any = importlib.util.module_from_spec(spec)
    # Register before exec: the module defines @dataclasses, whose machinery looks the
    # module up in sys.modules by __module__ while the class body runs.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.CAMP = _REPO / "resources" / "campaigns"  # cwd-independent
    return module


TOOL = _load_tool()


def test_default_weights_mirror_the_real_dataclass() -> None:
    # The tool's DEFAULT_WEIGHTS is a hand-mirror of WillWeights' defaults; if a weight
    # is added/renamed/re-defaulted in political_will.py, this fails until the mirror
    # is updated -- so the offline model never tunes against stale defaults.
    real = {
        f.name: getattr(WillWeights(), f.name) for f in dataclasses.fields(WillWeights)
    }
    assert TOOL.DEFAULT_WEIGHTS == real


def test_load_campaign_reads_the_ratchet_overrides() -> None:
    camp = TOOL.load_campaign("1968_Yankee_Station")
    # The redo's signature overrides are present...
    assert camp.weights["blue_passive_regen"] == -0.4
    assert camp.weights["red_convoy_unit_lost"] == 1.0
    # ...and the arc carries the escalation tax on the late phases.
    by_key = {p.key: p for p in camp.phases}
    assert by_key["linebacker"].blue_will_on_entry == -3.0
    assert by_key["linebacker_ii"].blue_will_on_entry == -5.0
    assert by_key["rolling_thunder"].trail_surge == 1.5


def test_load_campaign_rejects_an_unknown_weight(tmp_path: Any) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "name: Bad\nwill:\n  weights:\n    not_a_weight: 3\n", encoding="utf-8"
    )
    TOOL.CAMP = tmp_path
    try:
        with pytest.raises(SystemExit):
            TOOL.load_campaign("bad")
    finally:
        TOOL.CAMP = _REPO / "resources" / "campaigns"


def test_archetypes_bracket_the_arc() -> None:
    camp = TOOL.load_campaign("1968_Yankee_Station")
    outcomes = {}
    for name, play in TOOL.ARCHETYPES.items():
        rows = TOOL.simulate(camp, play, turns=30)
        last = rows[-1]
        outcomes[name] = (last.turn, last.blue, last.red)
    # Elite and average break Hanoi (RED hits 0, BLUE survives).
    assert outcomes["elite"][2] <= 0 < outcomes["elite"][1]
    assert outcomes["average"][2] <= 0 < outcomes["average"][1]
    # A floundering war breaks Washington first (BLUE hits 0, RED still standing).
    assert outcomes["flounder"][1] <= 0 < outcomes["flounder"][2]
    # And the race has real time pressure: average wins later than elite.
    assert outcomes["average"][0] > outcomes["elite"][0]
