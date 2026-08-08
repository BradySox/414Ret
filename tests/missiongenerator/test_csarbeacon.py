"""The pinned SAR beacon channel has to stay legal for MOOSE and for the ADF sets."""

from __future__ import annotations

import re
from pathlib import Path

from game.missiongenerator.csarbeacon import (
    BEACON_BAND_KHZ,
    BEACON_GRID_KHZ,
    SAR_BEACON_KHZ,
    sar_beacon_brief,
    sar_beacon_hz,
)

MOOSE = Path("resources/plugins/base/Moose.lua")


def _moose_skip_list() -> set[float]:
    """The navaid frequencies MOOSE's own beacon allocator refuses to use.

    Parsed from ``UTILS.GenerateVHFrequencies`` rather than copied, so a Moose.lua
    update that adds a conflicting navaid fails this test instead of silently
    parking our briefed beacon on top of one.
    """
    text = MOOSE.read_text(encoding="utf-8", errors="ignore")
    start = text.index("function UTILS.GenerateVHFrequencies")
    block = text[start : start + 3000]
    table = block[
        block.index("_skipFrequencies={") + len("_skipFrequencies={") : block.index("}")
    ]
    return {float(value) for value in re.findall(r"[\d.]+", table)}


def test_beacon_is_inside_moose_band() -> None:
    low, high = BEACON_BAND_KHZ
    assert low <= SAR_BEACON_KHZ <= high


def test_beacon_is_on_the_tuning_grid() -> None:
    assert SAR_BEACON_KHZ % BEACON_GRID_KHZ == 0


def test_beacon_avoids_every_navaid_moose_skips() -> None:
    skipped = _moose_skip_list()
    assert skipped, "parsed an empty skip list -- the Moose.lua parse broke"
    assert float(SAR_BEACON_KHZ) not in skipped, (
        f"{SAR_BEACON_KHZ} kHz is on MOOSE's navaid skip list, so the briefed "
        "survivor beacon would sit on top of a real theater navaid."
    )


def test_beacon_is_receivable_by_the_rescue_fleet() -> None:
    """C-130J ADF-462 (NDB), UH-1H ARN-83 190-1750, Mi-8 ARK-9 150-1290 kHz."""
    assert 190 <= SAR_BEACON_KHZ <= 1290


def test_hz_and_brief_forms() -> None:
    assert sar_beacon_hz() == SAR_BEACON_KHZ * 1000
    assert sar_beacon_brief() == f"{SAR_BEACON_KHZ} kHz ADF"
