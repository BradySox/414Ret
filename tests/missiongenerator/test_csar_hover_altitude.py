"""The briefed CSAR hover must sit under the player winch ceiling.

A **player** hoist is gated by MOOSE, not by the fork's plugin: ``CSAR:_CheckOnboard``
only runs the winch while the helicopter is within ``rescuehoverheight`` of the
survivor. The mission, meanwhile, briefs its own hover altitude on the CSAR pickup
waypoint. Those two numbers live in different repos and nothing connected them.

They were inconsistent on adoption: the waypoint briefed 100 ft (30.5 m) against a 20 m
ceiling, so a crew flying the waypoint exactly hovered 10 m too high and the winch never
started — with no cockpit message explaining why. Found 2026-08-07 while writing the CSAR
in-game-pass rows.

Upstream #929 Phase 5 then made that ceiling a **setting** (``csar_player_hover_height``,
5–100 m), so a fixed briefed altitude is only safe at the default and the original defect
could reopen at the bottom of the range. ``briefed_hover_altitude`` clamps against the
setting instead, and these tests hold it to that across the setting's whole range.

Moose.lua is still parsed, for the two things the setting cannot tell us: that the field
we assign to still exists under that name, and that MOOSE's own default has not moved
away from the setting's.
"""

from __future__ import annotations

import re
from dataclasses import fields
from pathlib import Path

import pytest

from game.missiongenerator.aircraft.waypoints.csarpickup import (
    HOVER_ALTITUDE,
    briefed_hover_altitude,
)
from game.settings import Settings
from game.settings.optiondescription import SETTING_DESCRIPTION_KEY

MOOSE = Path("resources/plugins/base/Moose.lua")

#: The fraction of the ceiling the margin test demands stay free. Proportional, not
#: absolute: a 3 m margin is unavailable at a 5 m ceiling.
REQUIRED_MARGIN_FRACTION = 0.1


def _moose_rescue_hover_ceiling_m() -> int:
    """MOOSE's ``CSAR.rescuehoverheight`` default, in metres."""
    text = MOOSE.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"self\.rescuehoverheight\s*=\s*(\d+)", text)
    assert match, (
        "could not find CSAR.rescuehoverheight in Moose.lua — the parse broke, or "
        "MOOSE renamed the winch-ceiling field. Do not delete this test; re-point it, "
        "and re-point OpsCSAR.lua's assignment to it in the same change."
    )
    return int(match.group(1))


def _hover_height_bounds() -> tuple[int, int, int]:
    """The setting's ``(min, default, max)``, read off the dataclass field."""
    for f in fields(Settings):
        if f.name == "csar_player_hover_height":
            option = f.metadata[SETTING_DESCRIPTION_KEY]
            assert isinstance(f.default, int)
            return option.min, f.default, option.max
    raise AssertionError(
        "csar_player_hover_height is gone from Settings. If upstream withdrew the "
        "setting the ceiling is a constant again — re-point this test at Moose.lua."
    )


def _settings_with_ceiling(ceiling: int) -> Settings:
    settings = Settings()
    settings.csar_player_hover_height = ceiling
    return settings


def test_the_ceiling_is_still_findable() -> None:
    ceiling = _moose_rescue_hover_ceiling_m()
    assert 5 <= ceiling <= 200, f"implausible winch ceiling parsed: {ceiling} m"


def test_moose_default_still_agrees_with_the_setting_default() -> None:
    """The setting exists to override MOOSE's default, so the two should start equal.

    A drift here means one side moved alone: either MOOSE retuned the winch and the
    setting's default is now wrong, or upstream changed the default against MOOSE.
    """
    _, default, _ = _hover_height_bounds()
    assert default == _moose_rescue_hover_ceiling_m()


@pytest.mark.parametrize("ceiling", [5, 10, 15, 20, 30, 50, 75, 100])
def test_briefed_hover_is_below_the_winch_ceiling(ceiling: int) -> None:
    briefed = briefed_hover_altitude(_settings_with_ceiling(ceiling)).meters
    assert briefed < ceiling, (
        f"at a {ceiling} m winch ceiling the CSAR pickup waypoint briefs a "
        f"{briefed:.1f} m hover. A player flying the briefed altitude would never get "
        "the survivor aboard, and DCS would say nothing."
    )


@pytest.mark.parametrize("ceiling", [5, 10, 15, 20, 30, 50, 75, 100])
def test_briefed_hover_keeps_a_usable_margin(ceiling: int) -> None:
    """Exactly at the ceiling is not good enough — a helo bobs, and MOOSE samples
    height on a timer, so a hover sitting on the limit would winch intermittently."""
    briefed = briefed_hover_altitude(_settings_with_ceiling(ceiling)).meters
    margin = ceiling - briefed
    assert margin >= ceiling * REQUIRED_MARGIN_FRACTION, (
        f"only {margin:.1f} m of margin between the briefed hover ({briefed:.1f} m) "
        f"and the {ceiling} m winch ceiling. Station-keeping noise would drop the helo "
        "in and out of the winch window."
    )


def test_the_whole_setting_range_is_covered() -> None:
    """The parametrized cases must actually span the range the UI offers."""
    low, _, high = _hover_height_bounds()
    assert low >= 5 and high <= 100, (
        f"csar_player_hover_height now spans {low}-{high} m; the cases above only "
        "cover 5-100. Widen them."
    )


def test_the_default_ceiling_does_not_clamp_the_briefed_hover() -> None:
    """At the default the clamp must not bind, so the flown value is still 50 ft.

    This is what keeps the adoption unchanged for anyone who never touches the
    setting — the clamp is a floor guard, not a retune.
    """
    _, default, _ = _hover_height_bounds()
    briefed = briefed_hover_altitude(_settings_with_ceiling(default))
    assert briefed.meters == pytest.approx(HOVER_ALTITUDE.meters)


def test_briefed_hover_clears_the_survivor_at_the_default() -> None:
    """And it must not be so low that the hover is unflyable over the survivor.

    Only checked at the default: a crew who sets a 5 m winch ceiling has asked for a
    hover that low, and the clamp is right to give it to them.
    """
    _, default, _ = _hover_height_bounds()
    briefed = briefed_hover_altitude(_settings_with_ceiling(default)).meters
    assert (
        briefed >= 10.0
    ), f"a {briefed:.1f} m hover is too low to fly over a survivor on uneven ground."
