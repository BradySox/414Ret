"""The briefed CSAR hover must sit under MOOSE's winch ceiling.

A **player** hoist is gated by MOOSE, not by the fork's plugin: ``CSAR:_CheckOnboard``
only runs the winch while the helicopter is within ``rescuehoverheight`` of the
survivor. The mission, meanwhile, briefs its own hover altitude on the CSAR pickup
waypoint. Those two numbers live in different repos and nothing connected them.

They were inconsistent on adoption: the waypoint briefed 100 ft (30.5 m) against a 20 m
ceiling, so a crew flying the waypoint exactly hovered 10 m too high and the winch never
started — with no cockpit message explaining why. Found 2026-08-07 while writing the CSAR
in-game-pass rows.

The ceiling is **parsed out of Moose.lua** rather than copied, so a MOOSE update that
lowers it fails here instead of silently re-opening the gap.
"""

from __future__ import annotations

import re
from pathlib import Path

from game.missiongenerator.aircraft.waypoints.csarpickup import HOVER_ALTITUDE

MOOSE = Path("resources/plugins/base/Moose.lua")


def _moose_rescue_hover_ceiling_m() -> int:
    """MOOSE's ``CSAR.rescuehoverheight`` default, in metres."""
    text = MOOSE.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"self\.rescuehoverheight\s*=\s*(\d+)", text)
    assert match, (
        "could not find CSAR.rescuehoverheight in Moose.lua — the parse broke, or "
        "MOOSE renamed the winch-ceiling field. Do not delete this test; re-point it."
    )
    return int(match.group(1))


def test_the_ceiling_is_still_findable() -> None:
    ceiling = _moose_rescue_hover_ceiling_m()
    assert 5 <= ceiling <= 200, f"implausible winch ceiling parsed: {ceiling} m"


def test_briefed_hover_is_below_the_winch_ceiling() -> None:
    ceiling = _moose_rescue_hover_ceiling_m()
    assert HOVER_ALTITUDE.meters < ceiling, (
        f"the CSAR pickup waypoint briefs a {HOVER_ALTITUDE.feet:.0f} ft "
        f"({HOVER_ALTITUDE.meters:.1f} m) hover, but MOOSE only winches at or below "
        f"{ceiling} m (CSAR.rescuehoverheight). A player flying the briefed altitude "
        "would never get the survivor aboard, and DCS would say nothing."
    )


def test_briefed_hover_keeps_a_usable_margin() -> None:
    """Exactly at the ceiling is not good enough — a helo bobs, and MOOSE samples
    height on a timer, so a hover sitting on the limit would winch intermittently."""
    ceiling = _moose_rescue_hover_ceiling_m()
    margin = ceiling - HOVER_ALTITUDE.meters
    assert margin >= 3.0, (
        f"only {margin:.1f} m of margin between the briefed hover "
        f"({HOVER_ALTITUDE.meters:.1f} m) and MOOSE's {ceiling} m winch ceiling. "
        "Station-keeping noise would drop the helo in and out of the winch window."
    )


def test_briefed_hover_clears_the_survivor() -> None:
    """And it must not be so low that the hover is unflyable over the survivor."""
    assert HOVER_ALTITUDE.meters >= 10.0, (
        f"a {HOVER_ALTITUDE.meters:.1f} m hover is too low to fly over a survivor on "
        "uneven ground."
    )
