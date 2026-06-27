from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List, Optional

from game.missiongenerator.kneeboard import (
    FriendlyPackagesPage,
    FuelLadderCard,
    KneeboardPageWriter,
)


def _units() -> Any:
    # mass() returns the raw pound value so the rendered figures equal the inputs.
    return SimpleNamespace(mass=lambda m: m.pounds, mass_uom="lb")


def _wp(name: str, plan: Optional[float], min_fuel: Optional[float]) -> Any:
    return SimpleNamespace(display_name=name, fuel_planned=plan, min_fuel=min_fuel)


def _flight(
    waypoints: List[Any], *, bingo: float = 5100.0, joker: float = 6100.0
) -> Any:
    return SimpleNamespace(
        callsign="Sting 2",
        custom_name=None,
        aircraft_type=SimpleNamespace(kneeboard_units=_units()),
        waypoints=waypoints,
        bingo_fuel=bingo,
        joker_fuel=joker,
    )


def _render_fuel(flight: Any) -> str:
    writer = KneeboardPageWriter()
    FuelLadderCard(flight, dark_kneeboard=False).render_into(writer)
    return writer.get_text_string()


# Mirrors the screenshot: plan/min walked from opposite ends, margin constant 1507.
_LADDER = [
    _wp("Takeoff", 10633, 9126),
    _wp("Hold", 9969, 8462),
    _wp("Target area", 7026, 5519),
    _wp("Land", 3507, 2000),
    _wp("Bullseye", 425, None),  # post-landing reference: no min-to-RTB
]


def test_fuel_ladder_has_one_fuel_column_not_plan_min_margin() -> None:
    txt = _render_fuel(_flight(_LADDER))

    # The single planned-fuel figure is shown per row...
    assert "10633" in txt
    # ...but the per-row Min and Margin columns are gone (their values don't repeat).
    assert "9126" not in txt  # a Min value
    assert "8462" not in txt  # another Min value
    # The old three-column headers are gone (the lone column is "Fuel").
    assert "Margin" not in txt


def test_fuel_ladder_surfaces_the_constant_margin_once() -> None:
    txt = _render_fuel(_flight(_LADDER))

    # The trip-wide surplus is reported a single time in the summary, not per row.
    assert "RTB margin +1507 lb" in txt
    assert txt.count("1507") == 1


def test_fuel_ladder_drops_post_landing_reference_points() -> None:
    # The bullseye (no min-to-RTB) is not a real arrival state and must not appear.
    txt = _render_fuel(_flight(_LADDER))
    assert "Bullseye" not in txt
    assert "425" not in txt
    assert "Takeoff" in txt and "Land" in txt


def test_fuel_ladder_negative_margin_warns_to_tank_or_divert() -> None:
    short = [_wp("Takeoff", 5000, 6000), _wp("Land", 2000, 3000)]
    txt = _render_fuel(_flight(short))
    assert "RTB margin -1000 lb" in txt
    assert "tank or divert" in txt


def test_fuel_ladder_keeps_bingo_joker() -> None:
    txt = _render_fuel(_flight(_LADDER))
    assert "Bingo" in txt and "Joker" in txt
    assert "5100" in txt and "6100" in txt


def _packages(rows: int) -> FriendlyPackagesPage:
    flight = SimpleNamespace(callsign="Sting 2", custom_name=None)
    data = [["SEAD", f"Target {i}", "20:30"] for i in range(rows)]
    return FriendlyPackagesPage(flight, data, dark_kneeboard=False)  # type: ignore[arg-type]


def test_packages_section_draws_when_there_is_room() -> None:
    writer = KneeboardPageWriter()
    _packages(4).render_section(writer)
    txt = writer.get_text_string()
    assert "Friendly Packages" in txt
    assert "Target 0" in txt


def test_packages_section_draws_nothing_when_no_room_for_a_row() -> None:
    # Cursor parked near the page bottom: the self-limiting table would fit zero rows,
    # so the section must draw nothing rather than strand a lonely heading (the bug the
    # unpacked .miz showed on the Comms & Coordination page).
    writer = KneeboardPageWriter()
    writer.y = writer.image_size[1] - writer.page_margin - 5
    _packages(4).render_section(writer)
    assert "Friendly Packages" not in writer.get_text_string()
