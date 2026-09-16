"""The flight-plan table fits the kneeboard page at its widest.

The Mach column (2026-09-15) was paid for by shortening the GS / M / Dep headers:
tabulate pads every header by two characters, so "Departure" over a six-character
cell was five characters of blank page. The widest possible row -- a coalesced
"10-13" target block, a 25-character action, a supersonic leg, a Zulu+local time,
five-digit altitude and fuel -- must render without ``_fit_col_widths`` having to
wrap the Action column, or every long steerpoint name doubles its row.
"""

from __future__ import annotations

from PIL import ImageFont

from game.missiongenerator.kneeboard import FlightPlanBuilder, KneeboardPageWriter

HEADERS = ["#", "Action", "Alt", "Dist", "GS", "M", "Time", "Dep", "Fuel"]


def test_widest_flight_plan_row_fits_without_wrapping() -> None:
    writer = KneeboardPageWriter()
    font = ImageFont.truetype("courbd.ttf", 16, layout_engine=ImageFont.Layout.BASIC)
    rows = [
        [
            "10-13",
            "W" * FlightPlanBuilder.WAYPOINT_DESC_MAX_LEN,
            "19000",
            "188.3",
            "1234",
            "1.26",
            "17:27Z 20:27L",
            "17:00Z",
            "10633",
        ],
        ["", "", "ft", "nm", "km/h", "Mach", "", "", "kg"],
    ]
    assert writer._fit_col_widths(rows, HEADERS, font) is None
