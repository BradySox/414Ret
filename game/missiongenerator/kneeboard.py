"""Generates kneeboard pages relevant to the player's mission.

The player kneeboard includes the following information:

* Airfield (departure, arrival, divert) info.
* Flight plan (waypoint numbers, names, altitudes).
* Comm channels.
* AWACS info.
* Tanker info.
* JTAC info.

Things we should add:

* Flight plan ToT and fuel ladder (current have neither available).
* Support for planning an arrival/divert airfield separate from departure.
* Mission package infrastructure to include information about the larger
  mission, i.e. information about the escort flight for a strike package.
* Target information. Steerpoints, preplanned objectives, ToT, etc.

For multiplayer missions, a kneeboard will be generated per flight.
https://forums.eagle.ru/showthread.php?t=206360 claims that kneeboard pages can
only be added per airframe, so PvP missions where each side have the same
aircraft will be able to see the enemy's kneeboard for the same airframe.
"""

import datetime
import math
import textwrap
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, TYPE_CHECKING, Tuple

from PIL import Image, ImageDraw, ImageFont
from dcs.mapping import Point
from dcs.mission import Mission
from dcs.planes import F_15ESE
from suntime import Sun, SunTimeException  # type: ignore
from tabulate import tabulate

from game.ato.codewords import PushCategory, present_categories, push_category_for
from game.ato.flighttype import FlightType
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.data.alic import AlicCodes
from game.data.threat_reference import ThreatReference, reference_for
from game.data.units import UnitClass
from game.data.weapons import Weapon, WeaponType
from game.dcs.aircrafttype import AircraftType
from game.radio.radios import RadioFrequency
from game.runways import RunwayData
from game.settings.settings import TargetIntelPrecision
from game.sitrep import Sitrep, sitrep_for_kneeboard
from game.theater import FrontLine, TheaterGroundObject, TheaterUnit
from game.theater.bullseye import Bullseye
from game.theater.controlpoint import Airfield, ControlPoint
from game.theater.theatergroundobject import EwrGroundObject, SamGroundObject
from game.utils import Distance, UnitSystem, inches_hg, meters, mps, pounds
from game.weather.weather import Weather
from .aircraft.flightdata import CombatSarKingBeacon, FlightData
from .briefinggenerator import CommInfo, JtacInfo, MissionInfoGenerator
from .commsjamluadata import JAM_BACKUP_COMM_NAME
from .kneeboard_page import KneeboardPage, save_kneeboard_image
from .kneeboard_recon import airport_imagery as _airport_imagery
from .kneeboard_recon import generate_recon_pages
from .kneeboard_recon.pages import (
    _FLIGHT_TYPES_WITH_RECON,
    _should_emit_departure,
    AirbaseReconPage,
    DetailReconPage,
    FrontLineDetailPage,
)
from .kneeboard_recon.atis import (
    THUNDERSTORM_PRESSURE_DROP_INHG,
    altimeter_setting_inhg,
    compute_qfe_inhg,
    has_thunderstorm_cells,
    wind_from_deg,
)
from .missiondata import AwacsInfo, TankerInfo
from ..persistency import kneeboards_dir

if TYPE_CHECKING:
    from dcs.terrain.terrain import Terrain
    from game import Game
    from game.customkneeboard import CustomKneeboard
    from game.theater.conflicttheater import ConflictTheater


class KneeboardPageWriter:
    """Creates kneeboard images."""

    def __init__(
        self, page_margin: int = 24, line_spacing: int = 12, dark_theme: bool = False
    ) -> None:
        if dark_theme:
            self.foreground_fill = (215, 200, 200)
            self.background_fill = (10, 5, 5)
            # Semantic accent palette for the Brief Sheet (§ brief sheet). Colour
            # encodes meaning, not decoration: nav/comms, caution, go, emergency.
            # Light, desaturated shades read on the near-black night background.
            self.col_nav = (127, 176, 216)  # blue: route, freqs, bullseye, divert
            self.col_caution = (216, 176, 112)  # amber: threats, bingo/joker
            self.col_success = (132, 192, 138)  # green: SUCCESS / go
            self.col_danger = (224, 138, 138)  # red: ABORT / emergency
            self.col_muted = (150, 134, 134)  # field labels
            self.col_emphasis = (240, 232, 232)  # header lines
        else:
            self.foreground_fill = (15, 15, 15)
            # Light grey rather than near-white: avoids glare under HDR / Auto-HDR
            # while staying perfectly readable in daylight.
            self.background_fill = (210, 210, 210)
            # Darker variants of the same four hues so they stay legible on the
            # daytime light-grey background (the night shades would wash out).
            self.col_nav = (24, 86, 140)
            self.col_caution = (130, 84, 12)
            self.col_success = (28, 104, 40)
            self.col_danger = (158, 36, 36)
            self.col_muted = (96, 88, 88)
            self.col_emphasis = (0, 0, 0)
        self.image_size = (960, 1080)
        self.image = Image.new("RGB", self.image_size, self.background_fill)
        # These font sizes create a relatively full page for current sorties. If
        # we start generating more complicated flight plans, or start including
        # more information in the comm ladder (the latter of which we should
        # probably do), we'll need to split some of this information off into a
        # second page.
        self.title_font = ImageFont.truetype(
            "courbd.ttf", 32, layout_engine=ImageFont.Layout.BASIC
        )
        self.heading_font = ImageFont.truetype(
            "courbd.ttf", 24, layout_engine=ImageFont.Layout.BASIC
        )
        self.content_font = ImageFont.truetype(
            "courbd.ttf", 16, layout_engine=ImageFont.Layout.BASIC
        )
        self.table_font = ImageFont.truetype(
            "courbd.ttf", 20, layout_engine=ImageFont.Layout.BASIC
        )
        self.draw = ImageDraw.Draw(self.image)
        self.page_margin = page_margin
        self.x = page_margin
        self.y = page_margin
        self.line_spacing = line_spacing
        self.text_buffer: List[str] = []

    @property
    def position(self) -> Tuple[int, int]:
        return self.x, self.y

    def text(
        self,
        text: str,
        font: Optional[ImageFont.FreeTypeFont] = None,
        fill: Optional[Tuple[int, int, int]] = None,
        wrap: bool = False,
    ) -> None:
        if font is None:
            font = self.content_font
        if fill is None:
            fill = self.foreground_fill

        if wrap:
            text = "\n".join(
                self.wrap_line_with_font(
                    line, self.image_size[0] - self.page_margin - self.x, font
                )
                for line in text.splitlines()
            )

        self.draw.text(self.position, text, font=font, fill=fill)
        box = self.draw.textbbox(self.position, text, font=font)
        height = abs(box[1] - box[3])  # abs(top - bottom) => offset
        self.y += height + self.line_spacing
        self.text_buffer.append(text)

    def text_runs(
        self,
        runs: List[Tuple[str, Optional[Tuple[int, int, int]]]],
        font: Optional[ImageFont.FreeTypeFont] = None,
    ) -> None:
        """Draw a single line made of coloured segments, left to right.

        Each run is ``(text, fill)``; ``fill`` None falls back to the foreground.
        Runs carry their own spacing (trailing blanks), so the caller controls gaps.
        Advances the cursor one line down. Used by the Brief Sheet to colour
        individual tokens (a freq, the ABORT word) inside an otherwise plain line.
        """
        if font is None:
            font = self.content_font
        x = self.x
        for text, fill in runs:
            self.draw.text(
                (x, self.y), text, font=font, fill=fill or self.foreground_fill
            )
            x += int(round(font.getlength(text)))
            self.text_buffer.append(text)
        box = self.draw.textbbox((self.x, self.y), "Ag", font=font)
        self.y += abs(box[1] - box[3]) + self.line_spacing

    def flush_text_buffer(self) -> None:
        self.text_buffer = []

    def get_text_string(self) -> str:
        return "\n".join(x for x in self.text_buffer)

    def title(self, title: str) -> None:
        self.text(title, font=self.title_font, fill=self.foreground_fill)

    def heading(self, text: str) -> None:
        self.text(text, font=self.heading_font, fill=self.foreground_fill)

    def table(
        self,
        cells: List[List[str]],
        headers: Optional[List[str]] = None,
        font: Optional[ImageFont.FreeTypeFont] = None,
    ) -> None:
        if headers is None:
            headers = []
        if font is None:
            font = self.table_font
        maxcolwidths = self._fit_col_widths(cells, headers, font)
        table = tabulate(
            cells, headers=headers, numalign="right", maxcolwidths=maxcolwidths
        )
        self.text(table, font, fill=self.foreground_fill)

    def _fit_col_widths(
        self,
        cells: List[List[str]],
        headers: List[str],
        font: ImageFont.FreeTypeFont,
    ) -> Optional[List[int]]:
        """Per-column character caps that keep a table within the page width.

        Returns ``maxcolwidths`` for ``tabulate`` (which word-wraps any cell past its
        cap) or ``None`` when the table already fits. Shrinks the widest column first,
        down to a floor, so a runaway column (e.g. a 3-radio FREQ ladder) wraps instead
        of running off the right edge and losing data. The fit is measured against
        ``tabulate``'s *actual* rendered output (its padding is hard to predict), so a
        table that already fits returns ``None`` and is byte-identical to before.
        """
        rows = list(cells) + ([headers] if headers else [])
        ncols = max((len(r) for r in rows), default=0)
        if ncols == 0:
            return None

        max_px = self.image_size[0] - self.page_margin - self.x

        def widest_line_px(maxcolwidths: Optional[List[int]]) -> float:
            rendered = tabulate(
                cells, headers=headers, numalign="right", maxcolwidths=maxcolwidths
            )
            return max(
                (font.getlength(line) for line in rendered.splitlines()), default=0.0
            )

        if widest_line_px(None) <= max_px:
            return None

        def natural(col: int) -> int:
            return max(
                (
                    len(line)
                    for r in rows
                    if col < len(r)
                    for line in str(r[col]).splitlines()
                ),
                default=1,
            )

        widths = [natural(col) for col in range(ncols)]
        floor = 8  # never crush a column below a legible minimum
        # Shrink the widest column one char at a time until the rendered table fits (or
        # nothing can shrink further -- then we've done all we can without illegibility).
        while widest_line_px(widths) > max_px:
            widest = max(range(ncols), key=lambda i: widths[i])
            if widths[widest] <= floor:
                break
            widths[widest] -= 1
        return widths

    def rule(self, thickness: int = 2, gap_above: int = 2, gap_below: int = 8) -> None:
        """Draw a thin horizontal separator across the content width.

        A light alternative to a boxed panel: it underlines a heading (or
        divides sections) without the heavy filled-bar / full-border look.
        """
        self.y += gap_above
        self.draw.line(
            (self.x, self.y, self.image_size[0] - self.page_margin, self.y),
            fill=self.foreground_fill,
            width=thickness,
        )
        self.y += thickness + gap_below

    def vspace(self, pixels: int) -> None:
        """Advance the cursor by ``pixels`` to add vertical breathing room."""
        self.y += max(0, pixels)

    def _line_height(self, font: ImageFont.FreeTypeFont) -> int:
        """Vertical advance of one rendered text line for the given font.

        Measured from the delta between a one-line and two-line bbox so it
        matches PIL's actual multiline layout (including its inter-line
        padding) rather than relying on font metrics.
        """
        one = self.draw.textbbox((0, 0), "Ag", font=font)
        two = self.draw.textbbox((0, 0), "Ag\nAg", font=font)
        return (two[3] - two[1]) - (one[3] - one[1])

    def remaining_table_rows(
        self, font: ImageFont.FreeTypeFont, has_headers: bool
    ) -> int:
        """Number of data rows that still fit below the cursor for a table.

        Accounts for tabulate's two lines of header chrome (header + separator)
        and leaves one row of slack so a table never kisses the bottom edge.
        """
        line_height = self._line_height(font)
        if line_height <= 0:
            return 0
        available = (self.image_size[1] - self.page_margin) - self.y
        capacity = available // line_height
        if has_headers:
            capacity -= 2
        return max(0, capacity - 1)

    def table_paginated(
        self,
        cells: List[List[str]],
        headers: Optional[List[str]] = None,
        font: Optional[ImageFont.FreeTypeFont] = None,
    ) -> List[List[str]]:
        """Render as many rows as fit below the cursor; return the overflow.

        The returned rows did not fit on this page and should be carried onto a
        continuation page (see ``TableKneeboardPage``). Deterministic for a
        given starting cursor, so callers can replay it to discover the split
        without saving an image.
        """
        if font is None:
            font = self.table_font
        max_rows = self.remaining_table_rows(font, bool(headers))
        if max_rows <= 0:
            return list(cells)
        shown, overflow = cells[:max_rows], cells[max_rows:]
        self.table(shown, headers=headers, font=font)
        return overflow

    def table_two_column_paginated(
        self,
        cells: List[List[str]],
        headers: Optional[List[str]] = None,
        font: Optional[ImageFont.FreeTypeFont] = None,
        col_gap: int = 48,
    ) -> List[List[str]]:
        """Render a narrow table in two side-by-side columns; return overflow.

        Used for the Friendly Packages list, which is narrow enough that a
        single column wastes the right half of the page (and spills a handful
        of rows onto a near-empty continuation page). Filling the left column
        first, then the right, roughly doubles the rows per page. Rows beyond
        both columns are returned to paginate onto a continuation page.
        """
        if font is None:
            font = self.table_font
        capacity = self.remaining_table_rows(font, bool(headers))
        if capacity <= 0:
            return list(cells)
        left_rows = cells[:capacity]
        right_rows = cells[capacity : 2 * capacity]
        overflow = cells[2 * capacity :]

        start_x, start_y = self.x, self.y
        self.table(left_rows, headers=headers, font=font)
        left_bottom = self.y
        if right_rows:
            half = (self.image_size[0] - 2 * self.page_margin - col_gap) // 2
            self.x = start_x + half + col_gap
            self.y = start_y
            self.table(right_rows, headers=headers, font=font)
            self.x = start_x
            self.y = max(left_bottom, self.y)
        return overflow

    def write(self, path: Path) -> None:
        save_kneeboard_image(self.image, path)
        path.with_suffix(".txt").write_text(self.get_text_string(), "utf8")

    @staticmethod
    def wrap_line(inputstr: str, max_length: int) -> str:
        if len(inputstr) <= max_length:
            return inputstr
        tokens = inputstr.split(" ")
        output = ""
        segments = []
        for token in tokens:
            combo = output + " " + token
            if len(combo) > max_length:
                combo = output + "\n" + token
                segments.append(combo)
                output = ""
            else:
                output = combo
        return "".join(segments + [output]).strip()

    @staticmethod
    def wrap_line_with_font(
        inputstr: str, max_width: int, font: ImageFont.FreeTypeFont
    ) -> str:
        if font.getlength(inputstr) <= max_width:
            return inputstr
        tokens = inputstr.split(" ")
        output = ""
        segments = []
        for token in tokens:
            combo = output + " " + token
            if font.getlength(combo) > max_width:
                segments.append(output + "\n")
                output = token
            else:
                output = combo
        return "".join(segments + [output]).strip()


@dataclass(frozen=True)
class NumberedWaypoint:
    number: int
    waypoint: FlightWaypoint


class FlightPlanBuilder:
    WAYPOINT_DESC_MAX_LEN = 25

    def __init__(
        self,
        start_time: datetime.datetime,
        units: UnitSystem,
    ) -> None:
        self.start_time = start_time
        self.rows: List[List[str]] = []
        self.target_points: List[NumberedWaypoint] = []
        self.last_waypoint: Optional[FlightWaypoint] = None
        self.units = units
        # Per-waypoint (planned - min) fuel margins; constant across the route by
        # construction, so the page reports min() once as the RTB margin call-out.
        self.fuel_margins: List[float] = []

    def add_waypoint(self, waypoint_num: int, waypoint: FlightWaypoint) -> None:
        if waypoint.waypoint_type == FlightWaypointType.TARGET_POINT:
            self.target_points.append(NumberedWaypoint(waypoint_num, waypoint))
            return

        if self.target_points:
            self.coalesce_target_points()
            self.target_points = []

        self.add_waypoint_row(NumberedWaypoint(waypoint_num, waypoint))
        self.last_waypoint = waypoint

    def coalesce_target_points(self) -> None:
        if len(self.target_points) <= 4:
            for steerpoint in self.target_points:
                self.add_waypoint_row(steerpoint)
            if self.target_points:
                self.last_waypoint = self.target_points[-1].waypoint
            return

        first_waypoint_num = self.target_points[0].number
        last_waypoint_num = self.target_points[-1].number

        row = [
            f"{first_waypoint_num}-{last_waypoint_num}",
            "Target points",
            "0",
            self._waypoint_distance(self.target_points[0].waypoint),
            self._ground_speed(self.target_points[0].waypoint),
            self._format_time(self.target_points[0].waypoint.tot),
            self._format_time(self.target_points[0].waypoint.departure_time),
            self._format_fuel(self.target_points[0].waypoint),
        ]
        self.rows.append(row)
        self.last_waypoint = self.target_points[-1].waypoint

    def add_waypoint_row(self, waypoint: NumberedWaypoint) -> None:
        # Kneeboards are only generated for client flights (see
        # client_flights_by_airframe), so a ground-marked waypoint is always zeroed in
        # the .miz for this reader -- print what the cockpit will actually show rather
        # than the AI track altitude the planner recorded.
        alt = (
            meters(0)
            if waypoint.waypoint.marks_ground_for_player
            else waypoint.waypoint.alt
        )
        row = [
            str(waypoint.number),
            KneeboardPageWriter.wrap_line(
                waypoint.waypoint.display_name,
                FlightPlanBuilder.WAYPOINT_DESC_MAX_LEN,
            ),
            self._format_alt(alt),
            self._waypoint_distance(waypoint.waypoint),
            self._ground_speed(waypoint.waypoint),
            self._format_time(waypoint.waypoint.tot),
            self._format_time(waypoint.waypoint.departure_time),
            self._format_fuel(waypoint.waypoint),
        ]
        self.rows.append(row)

    @staticmethod
    def _format_time(time: datetime.datetime | None) -> str:
        if time is None:
            return ""
        return f"{time.strftime('%H:%M:%S')}{'Z' if time.tzinfo is not None else ''}"

    def _format_alt(self, alt: Distance) -> str:
        return f"{self.units.distance_short(alt):.0f}"

    def _waypoint_distance(self, waypoint: FlightWaypoint) -> str:
        if self.last_waypoint is None:
            return "-"

        distance = meters(
            self.last_waypoint.position.distance_to_point(waypoint.position)
        )

        return f"{self.units.distance_long(distance):.1f}"

    def _ground_speed(self, waypoint: FlightWaypoint) -> str:
        if self.last_waypoint is None:
            return "-"

        if waypoint.tot is None:
            return "-"

        if self.last_waypoint.departure_time is not None:
            last_time = self.last_waypoint.departure_time
        elif self.last_waypoint.tot is not None:
            last_time = self.last_waypoint.tot
        else:
            return "-"

        if (waypoint.tot - last_time).total_seconds() <= 0.0:
            # A zero or negative leg time (drifted structural vs chained clocks,
            # degenerate manual timing) has no meaningful ground speed.
            return "-"

        speed = mps(
            self.last_waypoint.position.distance_to_point(waypoint.position)
            / (waypoint.tot - last_time).total_seconds()
        )

        return f"{self.units.speed(speed):.0f}"

    def _format_fuel(self, waypoint: FlightWaypoint) -> str:
        """The fuel ladder folded into the flight plan: planned fuel remaining.

        Only genuine RTB checkpoints (those with a min-to-RTB figure) get a fuel
        entry; post-landing reference points like the bullseye carry a forward-burn
        "fuel" that isn't a real arrival state, so their cell stays blank. The
        constant (planned - min) margin is collected once per row for the one-line
        RTB call-out under the table instead of repeating a Min/Margin pair per row.
        """
        if waypoint.min_fuel is None:
            return ""
        if waypoint.fuel_planned is None:
            return "-"
        self.fuel_margins.append(waypoint.fuel_planned - waypoint.min_fuel)
        return f"{self.units.mass(pounds(waypoint.fuel_planned)):.0f}"

    def fuel_margin_line(self) -> Optional[str]:
        """The one-line RTB margin call-out for the flight plan, or None.

        (Planned - min) is constant across the route by construction (start fuel -
        total burn - reserve), so the worst case is reported once instead of
        printing Min and Margin columns that repeat the same number every row.
        """
        if not self.fuel_margins:
            return None
        surplus = min(self.fuel_margins)
        uom = self.units.mass_uom
        amount = f"{self.units.mass(pounds(abs(surplus))):.0f}"
        if surplus >= 0:
            return (
                f"RTB margin +{amount} {uom} — spare over the minimum to get home "
                "with reserves."
            )
        return (
            f"RTB margin -{amount} {uom} — short of getting home as planned; "
            "tank or divert."
        )

    def build(self) -> List[List[str]]:
        if self.target_points:
            self.coalesce_target_points()
            self.target_points = []
        return self.rows


class TableKneeboardPage(KneeboardPage):
    """A standalone title + table page that auto-paginates across images.

    Used to hold the overflow of a folded list (friendly packages, airfield
    directory) that did not fit on its host page. ``paginate`` pre-splits the
    rows into per-page slices that fit, so each rendered image stays within the
    bottom margin.
    """

    def __init__(
        self,
        title: str,
        heading: str,
        headers: List[str],
        rows: List[List[str]],
        font_size: int,
        dark_kneeboard: bool,
        continued: bool = False,
    ) -> None:
        self.title = title
        self.heading = heading
        self.headers = headers
        self.rows = rows
        self.font_size = font_size
        self.dark_kneeboard = dark_kneeboard
        self.continued = continued

    def _font(self) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(
            "courbd.ttf", self.font_size, layout_engine=ImageFont.Layout.BASIC
        )

    def _draw_header(self, writer: "KneeboardPageWriter", continued: bool) -> None:
        writer.title(self.title)
        writer.heading(f"{self.heading} (cont.)" if continued else self.heading)
        writer.rule()

    def paginate(self) -> List[KneeboardPage]:
        """Split the rows into the smallest set of pages that all fit."""
        pages: List[KneeboardPage] = []
        remaining = self.rows
        continued = self.continued
        while remaining:
            probe = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
            self._draw_header(probe, continued)
            # Always place at least one row so a pathological case can't loop.
            capacity = max(
                1, probe.remaining_table_rows(self._font(), bool(self.headers))
            )
            slice_rows, remaining = remaining[:capacity], remaining[capacity:]
            pages.append(
                TableKneeboardPage(
                    self.title,
                    self.heading,
                    self.headers,
                    slice_rows,
                    self.font_size,
                    self.dark_kneeboard,
                    continued=continued,
                )
            )
            continued = True
        return pages

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self._draw_header(writer, self.continued)
        writer.table(self.rows, headers=self.headers, font=self._font())
        writer.write(path)


def _airfield_elevation_m(
    theater: Optional["ConflictTheater"], airfield_name: str
) -> Optional[float]:
    """DCS-mesh field elevation (m) of a named airfield, or None.

    Looks up the airport via the theater's controlpoints (matched by airfield
    name) and reads ``elevation_m`` from ``resources/airport_imagery/<terrain>.json``.
    None when no theater, no matching control point, or no elevation shipped.
    Shared by the full deck's weather block and the Brief Sheet's WX line so both
    walk the same lookup chain as the recon ATIS pipeline.
    """
    if theater is None or not airfield_name:
        return None
    for cp in theater.controlpoints:
        dcs_ap = getattr(cp, "dcs_airport", None)
        if dcs_ap is None:
            continue
        if cp.full_name == airfield_name or dcs_ap.name == airfield_name:
            return _airport_imagery.field_elevation_for_airport(theater.terrain, dcs_ap)
    return None


class BriefingPage(KneeboardPage):
    """A kneeboard page containing briefing information."""

    def __init__(
        self,
        flight: FlightData,
        bullseye: Bullseye,
        weather: Weather,
        start_time: datetime.datetime,
        dark_kneeboard: bool,
        atis_by_name: Optional[dict[str, RadioFrequency]] = None,
        theater: Optional["ConflictTheater"] = None,
        omit_weather: bool = False,
        bluf_lines: Optional[List[str]] = None,
        sitrep: Optional[Sitrep] = None,
        comint_lines: Optional[List[str]] = None,
    ) -> None:
        self.flight = flight
        self.bullseye = bullseye
        self.weather = weather
        self.start_time = start_time
        self.dark_kneeboard = dark_kneeboard
        self.theater = theater
        self.atis_by_name = atis_by_name or {}
        # BLUF (bottom line up front): the few items a pilot needs even if this is
        # the only kneeboard page they read -- task/TOT, code words, JAM BACKUP,
        # the compact threat picture, loadout and SAR guidance. Composed by the
        # generator (``_bluf_lines``) and passed in so the page stays decoupled
        # from the threat/code-word models.
        self.bluf_lines = bluf_lines or []
        # Previous turn's campaign SITREP (§29), rendered as a short section at the
        # bottom of the page. None on turn 1 / a quiet turn / when the toggle is off.
        self.sitrep = sitrep
        # §70 COMINT block (C0), rendered right under the SITREP: the tier status
        # + (Tier 2) the tasking leak and the reveal note. None/empty when
        # comint_collection is off.
        self.comint_lines = comint_lines or []
        # De-duplication (design §4): drop the weather block when the recon Departure
        # page already carries it. The Friendly Packages list moved to its own page.
        self.omit_weather = omit_weather
        self.flight_plan_font = ImageFont.truetype(
            "courbd.ttf",
            16,
            layout_engine=ImageFont.Layout.BASIC,
        )

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self._render(writer)
        writer.write(path)

    def _render(self, writer: KneeboardPageWriter) -> None:
        """Draw the Mission Info page."""
        if self.flight.custom_name:
            custom_name_title = ' ("{}")'.format(self.flight.custom_name)
        else:
            custom_name_title = ""
        writer.title(f"{self.flight.callsign} Mission Info{custom_name_title}")

        # BLUF block: task/target/TOT, push + event code words, JAM BACKUP, the
        # compact threat picture, loadout and SAR guidance -- the priority items on
        # the page players open to first (design §4). Kept tight so the flight-plan
        # table still fits on this same page.
        if self.bluf_lines:
            writer.heading("BLUF")
            writer.rule()
            for line in self.bluf_lines:
                writer.text(line, wrap=True)
            writer.vspace(8)

        # TODO: Handle carriers.
        writer.heading("Airfield Info")
        writer.rule()
        # Only show the ATIS column when ATIS is in play (plugin enabled), so a
        # mission without ATIS sees no kneeboard change (design §5).
        if self.atis_by_name:
            writer.table(
                [
                    self._row_with_atis("Departure", self.flight.departure),
                    self._row_with_atis("Arrival", self.flight.arrival),
                    self._row_with_atis("Divert", self.flight.divert),
                ],
                headers=["", "Airbase", "ATC", "TCN", "I(C)LS", "RWY", "ATIS"],
            )
        else:
            writer.table(
                [
                    self.airfield_info_row("Departure", self.flight.departure),
                    self.airfield_info_row("Arrival", self.flight.arrival),
                    self.airfield_info_row("Divert", self.flight.divert),
                ],
                headers=["", "Airbase", "ATC", "TCN", "I(C)LS", "RWY"],
            )

        writer.heading(
            f"Flight Plan ({self.flight.squadron.aircraft.variant_id} - "
            f"{self.flight.task_display_name})"
        )
        writer.rule()

        units = self.flight.aircraft_type.kneeboard_units

        flight_plan_builder = FlightPlanBuilder(self.start_time, units)
        for num, waypoint in enumerate(self.flight.waypoints):
            flight_plan_builder.add_waypoint(num, waypoint)

        # The fuel ladder rides in the flight plan: a Fuel column (planned remaining
        # at each RTB steerpoint) + a one-line RTB margin call-out, instead of a
        # separate near-empty Fuel Ladder page.
        headers = ["#", "Action", "Alt", "Dist", "GSPD", "Time", "Departure", "Fuel"]
        uom_row = [
            "",
            "",
            units.distance_short_uom,
            units.distance_long_uom,
            units.speed_uom,
            "",
            "",
            units.mass_uom,
        ]

        writer.table(
            flight_plan_builder.build() + [uom_row],
            headers=headers,
            font=self.flight_plan_font,
        )

        margin_line = flight_plan_builder.fuel_margin_line()
        if margin_line is not None:
            # Amber when short — caution colour, so a fuel problem reads at a glance.
            surplus = margin_line.startswith("RTB margin +")
            writer.text(
                margin_line,
                wrap=True,
                fill=None if surplus else writer.col_caution,
            )

        writer.text(f"Bullseye: {self.bullseye.position.latlng().format_dms()}")

        fl = self.flight

        # Weather block. Dropped (design §4) when the recon Departure page already
        # carries the field weather + winds + sunrise/sunset, so it isn't printed twice.
        if not self.omit_weather:
            # QNH = the temperature-corrected altimeter setting at the departure field
            # (what ATIS broadcasts), via game.utils for canonical unit conversions.
            qnh = inches_hg(self._effective_qnh_inhg())
            qnh_in_hg = f"{qnh.inches_hg:.2f}"
            qnh_mm_hg = f"{qnh.mm_hg:.1f}"
            qnh_hpa = f"{qnh.hecto_pascals:.1f}"
            writer.text(
                f"Temperature: {round(self.weather.atmospheric.temperature_celsius)} °C at sea level"
            )
            writer.text(f"QNH: {qnh_in_hg} inHg / {qnh_mm_hg} mmHg / {qnh_hpa} hPa")
            qfe_line = self._format_departure_qfe()
            if qfe_line is not None:
                writer.text(qfe_line)
            writer.text(
                f"Turbulence: {round(self.weather.atmospheric.turbulence_per_10cm)} per 10cm at ground level."
            )
            writer.text(
                f"Wind: {wind_from_deg(self.weather.wind.at_0m.direction)}°"
                f" / {round(mps(self.weather.wind.at_0m.speed).knots)}kts (0ft)"
                f" ; {wind_from_deg(self.weather.wind.at_2000m.direction)}°"
                f" / {round(mps(self.weather.wind.at_2000m.speed).knots)}kts (~6500ft)"
                f" ; {wind_from_deg(self.weather.wind.at_8000m.direction)}°"
                f" / {round(mps(self.weather.wind.at_8000m.speed).knots)}kts (~26000ft)"
            )
            c = self.weather.clouds
            writer.text(
                f'Cloud base: {f"{int(round(meters(c.base).feet, -2))}ft" if c else "CAVOK"}'
                f'{f", {c.preset.ui_name[:-2]}" if c and c.preset else ""}'
            )

            start_pos = fl.waypoints[0].position.latlng()
            sun = Sun(start_pos.lat, start_pos.lng)
            date = fl.squadron.coalition.game.date
            dt = datetime.datetime(date.year, date.month, date.day)
            tz = fl.squadron.coalition.game.theater.timezone
            # Get today's sunrise and sunset in UTC
            try:
                rise_utc = sun.get_sunrise_time(dt)
                rise = rise_utc + tz.utcoffset(sun.get_sunrise_time(dt))
            except SunTimeException:
                rise_utc = None
                rise = None
            try:
                set_utc = sun.get_sunset_time(dt)
                sunset = set_utc + tz.utcoffset(sun.get_sunset_time(dt))
            except SunTimeException:
                set_utc = None
                sunset = None
            writer.text(
                f"Sunrise - Sunset: {rise.strftime('%H:%M') if rise else 'N/A'} - {sunset.strftime('%H:%M') if sunset else 'N/A'}"
                f" ({rise_utc.strftime('%H:%M') if rise_utc else 'N/A'} - {set_utc.strftime('%H:%M') if set_utc else 'N/A'} UTC)"
            )

        if fl.bingo_fuel and fl.joker_fuel:
            writer.table(
                [
                    [
                        f"{units.mass(pounds(fl.bingo_fuel)):.0f} {units.mass_uom}",
                        f"{units.mass(pounds(fl.joker_fuel)):.0f} {units.mass_uom}",
                    ]
                ],
                ["Bingo", "Joker"],
            )

        if any(self.flight.laser_codes):
            codes: list[list[str]] = []
            for idx, code in enumerate(self.flight.laser_codes, start=1):
                codes.append([str(idx), "" if code is None else str(code)])
            writer.table(codes, ["#", "Laser Code"])

        # Previous turn's campaign SITREP (§29): a short "what happened last turn"
        # band at the bottom of the page. Already gated (setting / turn 1 / quiet
        # turn) by the generator, so its presence alone means there is news.
        if self.sitrep is not None:
            writer.vspace(8)
            writer.heading(f"SITREP — Turn {self.sitrep.turn}")
            writer.rule()
            for line in self.sitrep.kneeboard_lines():
                writer.text(line, wrap=True)

        # §70 COMINT (C0): the collection take, right under the SITREP. Empty
        # unless comint_collection is on, so the stock deck is unchanged.
        if self.comint_lines:
            writer.vspace(8)
            writer.heading("COMINT")
            writer.rule()
            for line in self.comint_lines:
                writer.text(line, wrap=True)

    def _departure_elevation_m(self) -> Optional[float]:
        """DCS-mesh field elevation (m) of the departure field, or None."""
        return _airfield_elevation_m(self.theater, self.flight.departure.airfield_name)

    def _altimeter_setting_inhg(self, elevation_m: Optional[float]) -> float:
        """Temperature-corrected altimeter-setting QNH (what ATIS reports) for a
        known field elevation; raw sea-level QNH when the elevation is unknown.
        """
        qnh_inhg = self.weather.atmospheric.qnh.inches_hg
        if elevation_m is None:
            return qnh_inhg
        return altimeter_setting_inhg(
            qnh_inhg, elevation_m, self.weather.atmospheric.temperature_celsius
        )

    def _effective_qnh_inhg(self) -> float:
        """QNH as ATIS reports it at the departure field (raw when no elevation)."""
        return self._altimeter_setting_inhg(self._departure_elevation_m())

    def _format_departure_qfe(self) -> Optional[str]:
        """Return "QFE: ..." line for the departure field, or None.

        QFE is derived from the temperature-corrected altimeter-setting QNH, so it
        equals the actual field pressure (matching the in-sim ATIS QFE).
        """
        dep = self.flight.departure
        elevation_m = self._departure_elevation_m()
        if elevation_m is None:
            return None

        # One elevation lookup feeds both the QNH correction and the QFE.
        qnh_inhg = self._altimeter_setting_inhg(elevation_m)
        qfe_inhg = compute_qfe_inhg(qnh_inhg, elevation_m)
        qfe_hpa = inches_hg(qfe_inhg).hecto_pascals
        elev_ft = meters(elevation_m).feet
        line = (
            f"QFE ({dep.airfield_name}, field elev {elev_ft:.0f} ft): "
            f"{qfe_inhg:.2f} inHg / {qfe_hpa:.1f} hPa"
        )
        if has_thunderstorm_cells(self.weather.clouds):
            qfe_low = compute_qfe_inhg(
                qnh_inhg - THUNDERSTORM_PRESSURE_DROP_INHG, elevation_m
            )
            line += (
                f" (~{qfe_low:.2f} in CB cells â€” local QNH may drop "
                "~3 mb inside storm cores)"
            )
        return line

    def airfield_info_row(
        self, row_title: str, runway: Optional[RunwayData]
    ) -> List[str]:
        """Creates a table row for a given airfield.

        Args:
            row_title: Purpose of the airfield. e.g. "Departure", "Arrival" or
                "Divert".
            runway: The runway described by this row.

        Returns:
            A list of strings to be used as a row of the airfield table.
        """
        if runway is None:
            return [row_title, "", "", "", "", ""]

        atc = ""
        if runway.atc is not None:
            atc = self.format_frequency(runway.atc)
        if runway.tacan is None:
            tacan = ""
        else:
            tacan = str(runway.tacan)
        if runway.ils is not None:
            ils = str(runway.ils)
        elif runway.icls is not None:
            ils = str(runway.icls)
        else:
            ils = ""
        return [
            row_title,
            "\n".join(textwrap.wrap(runway.airfield_name, width=17)),
            atc,
            tacan,
            ils,
            runway.runway_name,
        ]

    def _row_with_atis(self, row_title: str, runway: Optional[RunwayData]) -> List[str]:
        row = self.airfield_info_row(row_title, runway)
        atis = ""
        if runway is not None:
            freq = self.atis_by_name.get(runway.airfield_name)
            if freq is not None:
                atis = self.format_frequency(freq)
        row.append(atis)
        return row

    def format_frequency(self, frequency: RadioFrequency) -> str:
        channels = self.flight.channels_for(frequency)
        if not channels:
            return str(frequency)

        names = " / ".join(
            self.flight.aircraft_type.channel_name(c.radio_id, c.channel)
            for c in channels
        )
        return f"{names}\n{frequency}"


class FriendlyPackagesPage(KneeboardPage):
    """Standalone Friendly Packages coordination list (de-duped from Mission Info).

    Every friendly package with its TOT (strike) or patrol window (CAP/tanker/AWACS),
    laid out two-up (the list is narrow) and paginating onto continuation pages. Pulled
    out of the Mission Info page (design §4) so the same list isn't split across the
    bottom of Mission Info and a near-empty spill page.
    """

    HEADING = "Friendly Packages"
    HEADERS = ["Task", "Target", "TOT / Window"]
    FONT_SIZE = 18

    def __init__(
        self, flight: FlightData, rows: List[List[str]], dark_kneeboard: bool
    ) -> None:
        self.flight = flight
        self.rows = rows
        self.dark_kneeboard = dark_kneeboard

    def _title(self) -> str:
        custom = f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
        return f"{self.flight.callsign} Friendly Packages{custom}"

    def _font(self) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(
            "courbd.ttf", self.FONT_SIZE, layout_engine=ImageFont.Layout.BASIC
        )

    def _render(self, writer: KneeboardPageWriter) -> List[List[str]]:
        """Draw title + two-column packages table; return rows that overflowed."""
        writer.title(self._title())
        writer.heading(self.HEADING)
        writer.rule()
        font = self._font()
        single_capacity = writer.remaining_table_rows(font, bool(self.HEADERS))
        if len(self.rows) <= single_capacity:
            return writer.table_paginated(self.rows, headers=self.HEADERS, font=font)
        return writer.table_two_column_paginated(
            self.rows, headers=self.HEADERS, font=font
        )

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self._render(writer)
        writer.write(path)

    def paginate(self) -> List[KneeboardPage]:
        probe = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        overflow = self._render(probe)
        pages: List[KneeboardPage] = [self]
        if overflow:
            pages.extend(
                TableKneeboardPage(
                    self._title(),
                    self.HEADING,
                    self.HEADERS,
                    overflow,
                    self.FONT_SIZE,
                    self.dark_kneeboard,
                    continued=True,
                ).paginate()
            )
        return pages


@dataclass(frozen=True)
class CodeWordsBlock:
    """The side's mission code words, rendered on the Support Info page.

    ``pushes`` is one row per task category present in the ATO: (label, word,
    is_own_task). The event words follow; ``stop_jam`` only when an EW package
    exists. Built by the generator so the page stays decoupled from the ATO.
    """

    theme: str
    pushes: List[Tuple[str, str, bool]]
    success: str
    abort: str
    stop_jam: Optional[str]


class SupportPage(KneeboardPage):
    """A kneeboard page containing information about support units."""

    JTAC_REGION_MAX_LEN = 25

    def __init__(
        self,
        flight: FlightData,
        package_flights: List[FlightData],
        comms: List[CommInfo],
        awacs: List[AwacsInfo],
        tankers: List[TankerInfo],
        jtacs: List[JtacInfo],
        start_time: datetime.datetime,
        dark_kneeboard: bool,
        airfield_rows: Optional[List[List[str]]] = None,
        code_words: Optional[CodeWordsBlock] = None,
    ) -> None:
        self.flight = flight
        self.package_flights = package_flights
        self.comms = list(comms)
        self.awacs = awacs
        self.tankers = tankers
        self.jtacs = jtacs
        self.start_time = start_time
        self.dark_kneeboard = dark_kneeboard
        self.airfield_rows = airfield_rows or []
        self.code_words = code_words
        flight_name = self.flight.custom_name if self.flight.custom_name else "Flight"
        self.comms.append(CommInfo(flight_name, self.flight.intra_flight_channel))

    #: Folded "Airfield Directory" table presentation, shared by the inline
    #: render and any continuation page that catches its overflow.
    AIRFIELD_HEADING = "Airfield Directory"
    AIRFIELD_HEADERS = ["Field", "ATC", "ATIS", "TCN", "I(C)LS", "RWY"]
    AIRFIELD_FONT_SIZE = 20

    def _airfield_title(self) -> str:
        custom = f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
        return f"{self.flight.callsign} Airfield Directory{custom}"

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self._render(writer)
        writer.write(path)

    def paginate(self) -> List[KneeboardPage]:
        # Carry any airfield-directory rows that spilled past the bottom onto
        # continuation page(s). The probe image is discarded; write() re-renders.
        probe = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        overflow = self._render(probe)
        pages: List[KneeboardPage] = [self]
        if overflow:
            pages.extend(
                TableKneeboardPage(
                    self._airfield_title(),
                    self.AIRFIELD_HEADING,
                    self.AIRFIELD_HEADERS,
                    overflow,
                    self.AIRFIELD_FONT_SIZE,
                    self.dark_kneeboard,
                    continued=True,
                ).paginate()
            )
        return pages

    def _render(self, writer: KneeboardPageWriter) -> List[List[str]]:
        """Draw the Support Info page; return airfield rows that overflowed."""
        if self.flight.custom_name:
            custom_name_title = ' ("{}")'.format(self.flight.custom_name)
        else:
            custom_name_title = ""
        writer.title(f"{self.flight.callsign} Support Info{custom_name_title}")

        # Package FREQ / TOT line, above the boxed section tables. A package on three
        # radio channels makes a long FREQ ladder; when FREQ + TOT would overrun the
        # page width, split TOT onto its own line (and wrap the FREQ) so the TOT is
        # never clipped off the right edge.
        package = self.flight.package
        custom = f' "{package.custom_name}"' if package.custom_name else ""
        freq = self.format_frequency(package.frequency).replace("\n", " - ")
        tot = self._format_time(package.time_over_target)
        one_line = f"  FREQ: {freq}    TOT: {tot}"
        content_px = writer.image_size[0] - 2 * writer.page_margin
        if writer.table_font.getlength(one_line) <= content_px:
            writer.text(one_line, font=writer.table_font)
        else:
            writer.text(f"  FREQ: {freq}", font=writer.table_font, wrap=True)
            writer.text(f"  TOT: {tot}", font=writer.table_font)

        # Build each support section as (title, rows, headers); they render as
        # bordered boxes with header bars (the professional-campaign look) and
        # are spaced to fill the page rather than leaving the bottom half blank.
        comm_ladder = []
        for comm in self.comms:
            comm_ladder.append(
                [
                    comm.name,
                    self.flight.task_display_name,
                    KneeboardPageWriter.wrap_line(str(self.flight.aircraft_type), 23),
                    str(len(self.flight.units)),
                    self.format_frequency(comm.freq),
                ]
            )
        for f in self.package_flights:
            callsign = f.callsign
            if f.custom_name:
                callsign = f"{callsign}\n({f.custom_name})"
            comm_ladder.append(
                [
                    callsign,
                    f.task_display_name,
                    KneeboardPageWriter.wrap_line(str(f.aircraft_type), 23),
                    str(len(f.units)),
                    self.format_frequency(f.intra_flight_channel),
                ]
            )

        aewc_ladder = []
        for single_aewc in self.awacs:
            if single_aewc.depature_location is None:
                tot_a = "-"
                tos_a = "-"
            else:
                tot_a = self._format_time(single_aewc.start_time)
                tos_a = self._format_duration(
                    single_aewc.end_time - single_aewc.start_time
                )
            aewc_ladder.append(
                [
                    str(single_aewc.callsign),
                    self.format_frequency(single_aewc.freq),
                    str(single_aewc.depature_location),
                    "TOT: " + tot_a + "\n" + "TOS: " + tos_a,
                ]
            )

        tanker_ladder = []
        for tanker in self.tankers:
            tot_t = self._format_time(tanker.start_time)
            tos_t = self._format_duration(tanker.end_time - tanker.start_time)
            tanker_ladder.append(
                [
                    tanker.callsign,
                    KneeboardPageWriter.wrap_line(tanker.variant, 21),
                    str(tanker.tacan) if tanker.tacan else "N/A",
                    self.format_frequency(tanker.freq),
                    "TOT: " + tot_t + "\n" + "TOS: " + tos_t,
                ]
            )

        jtac_rows = []
        for jtac in self.jtacs:
            jtac_rows.append(
                [
                    jtac.callsign,
                    KneeboardPageWriter.wrap_line(
                        jtac.region, self.JTAC_REGION_MAX_LEN
                    ),
                    jtac.code,
                    self.format_frequency(jtac.freq),
                ]
            )

        # (title, cells, headers) for each non-empty section. Empty sections are
        # skipped so a mission without (e.g.) a tanker shows no empty heading.
        sections: List[Tuple[str, List[List[str]], List[str]]] = [
            (
                f"{package.package_description} Package{custom}",
                comm_ladder,
                ["Callsign", "Task", "Type", "#A/C", "FREQ"],
            )
        ]
        if aewc_ladder:
            sections.append(
                ("AEW&C", aewc_ladder, ["Callsign", "FREQ", "Departure", "TOT / TOS"])
            )
        if tanker_ladder:
            # Drop the "Task" column (always "Tanker") and shorten TACAN to TCN so
            # the wider FREQ column (COMM1 + COMM2) and TOT/TOS fit.
            sections.append(
                (
                    "Tankers",
                    tanker_ladder,
                    ["Callsign", "Type", "TCN", "FREQ", "TOT / TOS"],
                )
            )
        if jtac_rows:
            # "Laser" not "Laser Code": the 4-digit code padded the column and
            # pushed FREQ off the page.
            sections.append(
                ("JTAC", jtac_rows, ["Callsign", "Region", "Laser", "FREQ"])
            )

        def render_sections(w: KneeboardPageWriter, section_gap: int) -> None:
            for idx, (heading, cells, hdr) in enumerate(sections):
                w.text(heading, font=w.heading_font)
                w.rule()
                w.table(cells, headers=hdr)
                w.vspace(section_gap)
                # Code words ride directly under the package comm ladder: the
                # push/event words are package-coordination data, so they live
                # next to the frequencies they are called on.
                if idx == 0 and self.code_words is not None:
                    self._render_code_words(w)
                    w.vspace(section_gap)

        # When there's no airfield directory below, distribute the leftover
        # vertical space as even gaps so the tables breathe down the page
        # (light underline-rule headings, no boxes). With a directory present we
        # use a small fixed gap and let the directory fill the rest (it paginates).
        gap = 12
        if not self.airfield_rows:
            probe = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
            probe.y = writer.y
            render_sections(probe, 0)
            leftover = (writer.image_size[1] - writer.page_margin) - probe.y
            n_blocks = len(sections) + (1 if self.code_words is not None else 0)
            gap = int(max(12, min(90, leftover // max(1, n_blocks))))

        render_sections(writer, gap)

        # Airfield Directory (friendly fields: ATC / ATIS / TACAN / I(C)LS / RWY).
        # Rows that don't fit spill onto a continuation page (see paginate()).
        overflow: List[List[str]] = []
        if self.airfield_rows:
            writer.text(self.AIRFIELD_HEADING, font=writer.heading_font)
            writer.rule()
            overflow = writer.table_paginated(
                self.airfield_rows,
                headers=self.AIRFIELD_HEADERS,
            )
        return overflow

    def _render_code_words(self, w: KneeboardPageWriter) -> None:
        """The side's code words: a push word per task (yours marked) + event words.

        Colour keys the call: push words blue, SUCCESS green, ABORT red, STOP JAM
        amber -- so the word you need is found without reading labels. This is the
        in-cockpit copy of the code words the planners see on the ATO tooltip.
        """
        cw = self.code_words
        assert cw is not None
        w.text(f"Code Words — {cw.theme}", font=w.heading_font)
        w.rule()
        for label, word, own in cw.pushes:
            runs: List[Tuple[str, Optional[Tuple[int, int, int]]]] = [
                (f"{label:<10}", w.col_muted),
                (word, w.col_nav),
            ]
            if own:
                runs.append(("  (you)", w.col_emphasis))
            w.text_runs(runs, font=w.table_font)
        w.text_runs(
            [("SUCCESS   ", w.col_muted), (cw.success, w.col_success)],
            font=w.table_font,
        )
        w.text_runs(
            [("ABORT     ", w.col_muted), (cw.abort, w.col_danger)],
            font=w.table_font,
        )
        if cw.stop_jam:
            w.text_runs(
                [("STOP JAM  ", w.col_muted), (cw.stop_jam, w.col_caution)],
                font=w.table_font,
            )

    def format_frequency(self, frequency: Optional[RadioFrequency]) -> str:
        if frequency is None:
            return ""
        channels = self.flight.channels_for(frequency)
        if not channels:
            return str(frequency)

        names = " / ".join(
            self.flight.aircraft_type.channel_name(c.radio_id, c.channel)
            for c in channels
        )
        return f"{names}\n{frequency}"

    @staticmethod
    def _format_time(time: datetime.datetime | None) -> str:
        if time is None:
            return ""
        return f"{time.strftime('%H:%M:%S')}{'Z' if time.tzinfo is not None else ''}"

    @staticmethod
    def _format_duration(time: Optional[datetime.timedelta]) -> str:
        if time is None:
            return ""
        time -= datetime.timedelta(microseconds=time.microseconds)
        return f"{time}"


class SeadTaskPage(KneeboardPage):
    """A kneeboard page containing SEAD/DEAD target information."""

    def __init__(
        self, flight: FlightData, bullseye: Bullseye, dark_kneeboard: bool
    ) -> None:
        self.flight = flight
        self.bullseye = bullseye
        self.dark_kneeboard = dark_kneeboard

    @property
    def target_units(self) -> Iterator[TheaterUnit]:
        if isinstance(self.flight.package.target, TheaterGroundObject):
            yield from self.flight.package.target.strike_targets

    def _target_point_numbers(self) -> List[int]:
        """STPT numbers of the per-target waypoints, in target order.

        DEAD/SEAD flights get one TARGET_POINT waypoint per target, built from
        the same ``strike_targets`` list (in the same order) that this page
        lists, so the i-th TARGET_POINT waypoint is the i-th listed target. The
        number is the index into the flight's waypoint list, matching the
        flight-plan page. Pairing by order (rather than by position) is robust
        to APPROXIMATE target intel offsetting the waypoint away from the unit's
        true position, which previously left every STPT blank. Old flight plans
        generated before per-target waypoints existed simply have no entries.
        """
        return [
            idx
            for idx, waypoint in enumerate(self.flight.waypoints)
            if waypoint.waypoint_type == FlightWaypointType.TARGET_POINT
        ]

    @staticmethod
    def alic_for(unit: TheaterUnit) -> str:
        try:
            return str(AlicCodes.code_for(unit))
        except KeyError:
            return ""

    def _bullseye_cue_for(self, position: Point) -> str:
        """A rough bullseye bearing/range to ``position``, accurate to ~1nm.

        Bearing is rounded to the nearest degree and range to the nearest
        nautical mile, giving the player a search anchor without exact coords.
        """
        bearing = self.bullseye.position.heading_between_point(position)
        distance = meters(self.bullseye.position.distance_to_point(position))
        return f"Bullseye {bearing:03.0f} for {distance.nautical_miles:.0f}"

    def _bullseye_cue(self, unit: TheaterUnit) -> str:
        return self._bullseye_cue_for(unit.position)

    def _target_area_stpt(self) -> Optional[int]:
        """The single steerpoint that best anchors the whole site: the per-target
        waypoint nearest the site center. ``None`` when the flight has no per-target
        waypoints (e.g. legacy plans). Used for the consolidated DEAD area cue."""
        numbers = self._target_point_numbers()
        if not numbers:
            return None
        center = self.flight.package.target.position
        return min(
            numbers,
            key=lambda i: self.flight.waypoints[i].position.distance_to_point(center),
        )

    @staticmethod
    def _unit_description(unit: TheaterUnit) -> str:
        unit_type = unit.type
        return unit.name if unit_type is None else unit_type.name

    def _emitter_units(self) -> Iterator[Tuple[int, TheaterUnit]]:
        """``(index, unit)`` for the site's HARM-targetable emitters only.

        Only units with an ALIC code (radars and self-contained TELs) are HARM
        aimpoints; the launchers, command trucks and AAA guns that pad
        ``strike_targets`` aren't, and enumerating every one just hands the player the
        full site composition and exact unit counts (recon fog §3). The index pairs an
        emitter with its per-target steerpoint in the exact view.
        """
        for index, unit in enumerate(self.target_units):
            if self.alic_for(unit):
                yield index, unit

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self.render_into(writer)
        writer.write(path)

    def render_into(self, writer: KneeboardPageWriter) -> None:
        task = "DEAD" if self.flight.flight_type == FlightType.DEAD else "SEAD"
        if self.flight.custom_name:
            custom_name_title = ' ("{}")'.format(self.flight.custom_name)
        else:
            custom_name_title = ""
        writer.title(f"{self.flight.callsign} {task} Target Info{custom_name_title}")

        # Larger-than-default fonts: this page carries only a few rows, so bigger type
        # fills the page and reads better in the cockpit. The exact-coords table
        # instead drops BELOW the default (and shortens "STPT" to "#"): at size 20
        # the longest SAM names (e.g. S-300 Big Bird SR) pushed the DMS Location
        # column off the right edge (upstream PR #766).
        body_font = ImageFont.truetype(
            "courbd.ttf", 20, layout_engine=ImageFont.Layout.BASIC
        )
        area_font = ImageFont.truetype(
            "courbd.ttf", 24, layout_engine=ImageFont.Layout.BASIC
        )
        exact_font = ImageFont.truetype(
            "courbd.ttf", 18, layout_engine=ImageFont.Layout.BASIC
        )

        target = self.flight.package.target
        if not self._target_identified and isinstance(target, TheaterGroundObject):
            # Recon fog (§3): the site is on the map as a threat (you know roughly
            # where), but it hasn't been identified -- so don't hand over its full
            # composition + HARM codes. Give the area cue + intel-tier band and prompt
            # recon, the same way the Threat Intel Brief redacts undiscovered sites.
            cue = self._bullseye_cue_for(target.position)
            writer.heading(f"{task} target area — {cue}")
            band = target.air_defense_band or "Air-defense site"
            writer.text(
                f"{band}. Composition not yet identified — fly TARPS recon (or "
                "strike/scout the site) to reveal the emitters and their HARM codes.",
                font=body_font,
                wrap=True,
            )
            return

        if self._use_target_area_cues:
            # Consolidated view: one bullseye cue for the *center of the site* (not
            # one per unit -- that was cluttered) plus the single target-area
            # steerpoint if one maps. The table lists only the site's HARM-targetable
            # **emitters**, deduped by type -- not every launcher, command truck and
            # gun (and not their exact counts), which would reveal the whole site.
            cue = self._bullseye_cue_for(self.flight.package.target.position)
            stpt = self._target_area_stpt()
            area = f"{task} target area"
            if stpt is not None:
                area += f" — STPT {stpt}"
            writer.heading(f"{area} — {cue}")
            seen: set[Tuple[str, str]] = set()
            rows: List[List[str]] = []
            for _, unit in self._emitter_units():
                key = (self._unit_description(unit), self.alic_for(unit))
                if key in seen:
                    continue
                seen.add(key)
                rows.append([key[0], key[1]])
            if not rows:
                # No coded emitter (e.g. a pure AAA/launcher site): fall back to the
                # full unit list so the page is never blank.
                rows = [
                    [self._unit_description(t), self.alic_for(t)]
                    for t in self.target_units
                ]
            writer.table(rows, headers=["Description", "ALIC"], font=area_font)
        else:
            # Exact (SEAD) view: per-emitter steerpoint + precise coordinates, emitters
            # only -- the launchers/trucks/guns aren't HARM aimpoints.
            target_numbers = self._target_point_numbers()
            rows = [
                self.target_info_row(
                    unit, target_numbers[i] if i < len(target_numbers) else None
                )
                for i, unit in self._emitter_units()
            ]
            if not rows:
                rows = [
                    self.target_info_row(
                        t, target_numbers[i] if i < len(target_numbers) else None
                    )
                    for i, t in enumerate(self.target_units)
                ]
            writer.table(
                rows, headers=["#", "Description", "ALIC", "Location"], font=exact_font
            )

    def target_info_row(self, unit: TheaterUnit, number: Optional[int]) -> List[str]:
        return [
            "" if number is None else str(number),
            self._unit_description(unit),
            self.alic_for(unit),
            unit.position.latlng().format_dms(include_decimal_seconds=True),
        ]

    @property
    def _target_identified(self) -> bool:
        """Whether the player has discovered this site's composition (recon fog §3).

        Gates the emitter/ALIC breakdown: an un-identified site (``known_for`` False)
        is redacted to its intel-tier band so the kneeboard doesn't hand over the full
        composition before it's been recon'd. A non-TGO target (shouldn't happen for
        SEAD/DEAD) is treated as identified.
        """
        target = self.flight.package.target
        if not isinstance(target, TheaterGroundObject):
            return True
        return target.known_for(self.flight.friendly)

    @property
    def _approximate_target_intel(self) -> bool:
        return (
            self.flight.squadron.coalition.game.settings.target_intel_precision
            is TargetIntelPrecision.APPROXIMATE
        )

    @property
    def _use_target_area_cues(self) -> bool:
        return (
            self._approximate_target_intel or self.flight.flight_type == FlightType.DEAD
        )


class StrikeTaskPage(KneeboardPage):
    """A kneeboard page containing strike target information."""

    WAYPOINT_DESC_MAX_LEN = 35

    def __init__(self, flight: FlightData, dark_kneeboard: bool) -> None:
        self.flight = flight
        self.dark_kneeboard = dark_kneeboard

    @property
    def targets(self) -> Iterator[NumberedWaypoint]:
        for idx, waypoint in enumerate(self.flight.waypoints):
            if waypoint.waypoint_type == FlightWaypointType.TARGET_POINT:
                yield NumberedWaypoint(idx, waypoint)

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self.render_into(writer)
        writer.write(path)

    def render_into(self, writer: KneeboardPageWriter) -> None:
        if self.flight.custom_name:
            custom_name_title = ' ("{}")'.format(self.flight.custom_name)
        else:
            custom_name_title = ""
        writer.title(f"{self.flight.callsign} Strike Task Info{custom_name_title}")

        is_f15e = self.flight.units[0].unit_type == F_15ESE
        headers = ["STPT", "Description", "Location"]
        if self._approximate_target_intel:
            headers[2] = "Cue"
        writer.table(
            [
                [
                    str(target.number),
                    writer.wrap_line(
                        self._target_description(
                            target.waypoint.display_name, i, is_f15e
                        ),
                        self.WAYPOINT_DESC_MAX_LEN,
                    ),
                    (
                        "Search around target area waypoint"
                        if self._approximate_target_intel
                        else target.waypoint.position.latlng().format_dms(
                            include_decimal_seconds=True
                        )
                    ),
                ]
                for i, target in enumerate(self.targets)
            ],
            headers=headers,
        )

    @staticmethod
    def _target_description(display_name: str, index: int, is_f15e: bool) -> str:
        """The Strike Task 'Description' cell for one target.

        Built from the waypoint's display_name so a player's rename shows here too, and
        NOT written back to the waypoint: the F15E DTC data-cartridge slot reference stays
        confined to this page. (The previous code mutated pretty_name in place, which both
        leaked the DTC tag into the list / flight-plan kneeboard and, once renames moved to
        custom_name, regressed this page to the long auto name.)
        """
        if is_f15e:
            # Slot math must match the CDU data-cartridge programming in
            # PydcsWaypointBuilder.register_special_strike_points ("M{i//8+1}.{i%8+1}")
            # so the kneeboard label points at the slot the jet was actually programmed
            # with -- 8 minor slots per major group.
            return f"{display_name} (DTC M{(index // 8) + 1}.{index % 8 + 1})"
        return display_name

    @property
    def _approximate_target_intel(self) -> bool:
        return (
            self.flight.squadron.coalition.game.settings.target_intel_precision
            is TargetIntelPrecision.APPROXIMATE
        )


class CombatSarTaskPage(KneeboardPage):
    """Player briefing for a Combat SAR (pilot-rescue) flight.

    Role-aware: the CH-47 does the pickup, the C-130 flies the HC-130 "King"
    overhead-command orbit. Runtime is the MOOSE CSAR engine (combatsar plugin),
    which drives the F10 "CSAR" menu and the on-screen ranges in-game, so this
    page is guidance rather than exact tunable values.
    """

    def __init__(
        self,
        flight: FlightData,
        king_beacons: List[CombatSarKingBeacon],
        dark_kneeboard: bool,
    ) -> None:
        self.flight = flight
        # Every blue King's beacon in the mission, so the rescue helo knows what to
        # tune to home on the on-scene-command orbit.
        self.king_beacons = king_beacons
        self.dark_kneeboard = dark_kneeboard

    @property
    def _is_pickup_helo(self) -> bool:
        return self.flight.aircraft_type.helicopter

    @staticmethod
    def _tacan_str(beacon: CombatSarKingBeacon) -> str:
        return str(beacon.tacan) if beacon.tacan is not None else "--"

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self.render_into(writer)
        writer.write(path)

    def render_into(self, writer: KneeboardPageWriter) -> None:
        custom = f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
        writer.title(f"{self.flight.callsign} Combat SAR{custom}")

        # Larger body/heading type than the page defaults: this briefing is a few
        # short paragraphs, so we scale up and space the sections out (an
        # underline rule under each heading, blank space between) to fill the
        # page without the heavy boxed-panel look.
        heading_font = ImageFont.truetype(
            "courbd.ttf", 24, layout_engine=ImageFont.Layout.BASIC
        )
        body_font = ImageFont.truetype(
            "courbd.ttf", 20, layout_engine=ImageFont.Layout.BASIC
        )

        # Collect (heading, body-lines) sections, then space them down the page.
        sections: List[Tuple[str, List[str]]] = []

        if self._is_pickup_helo:
            sections.append(
                ("ROLE", ["Rescue helo — you make the pickup at the survivor."])
            )
        else:
            sections.append(
                ("ROLE", ['HC-130 "King" — on-scene command, overhead presence.'])
            )

        sections.append(
            (
                "HOW IT WORKS",
                [
                    "- Orbit near the front. When a friendly pilot ejects in the "
                    "area, a downed pilot spawns with a radio beacon.",
                    '- Use the F10 radio menu -> "CSAR" for the active rescue list, '
                    "the bearing/range to the survivor, and to request smoke / "
                    "flare / beacon.",
                ],
            )
        )

        if self._is_pickup_helo:
            sections.append(
                (
                    "PICKUP",
                    [
                        "- Fly to the survivor's beacon. Come to a low, slow hover "
                        "directly over them (or land alongside) and hold until they "
                        "board.",
                        "- Keep cargo doors open if your module models them.",
                        "- Deliver the survivor to ANY friendly airfield or FARP to "
                        "score the save.",
                    ],
                )
            )
            kings_with_tacan = [b for b in self.king_beacons if b.tacan is not None]
            if kings_with_tacan:
                lines = ["Home on the HC-130 King (TACAN) to find the rescue area:"]
                lines += [
                    f"    {b.callsign}    TACAN {self._tacan_str(b)}"
                    for b in kings_with_tacan
                ]
                sections.append(("KING BEACON", lines))
        else:
            sections.append(
                (
                    "ON-SCENE COMMAND",
                    [
                        "- Hold your overhead orbit as on-scene commander. Do NOT "
                        "land at the crash site.",
                        "- The rescue helo makes the pickup; you provide presence "
                        "and coordination.",
                    ],
                )
            )
            beacon = self.flight.combat_sar_king
            if beacon is not None and beacon.tacan is not None:
                sections.append(
                    (
                        "YOUR BEACON",
                        [
                            f"Radiating TACAN {beacon.tacan} ({beacon.callsign}) for "
                            "the rescue helo to home on.",
                            "F10 -> Combat SAR -> LARS lists active survivors "
                            "(position, bearing/range) for you to relay.",
                        ],
                    )
                )

        def render(w: KneeboardPageWriter, section_gap: int) -> None:
            w.vspace(8)
            for i, (heading, body) in enumerate(sections):
                w.text(heading, font=heading_font)
                w.rule()
                for line in body:
                    w.text(line, font=body_font, wrap=True)
                if i < len(sections) - 1:
                    w.vspace(section_gap)

        # Probe the natural height with no extra spacing, then distribute the
        # leftover vertical space as even gaps between sections so the page
        # breathes top-to-bottom — capped so a short brief doesn't leave yawning
        # gaps between two-line sections.
        probe = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        probe.title(f"{self.flight.callsign} Combat SAR{custom}")
        render(probe, 0)
        leftover = (writer.image_size[1] - writer.page_margin) - probe.y
        section_gap = int(max(16, min(80, leftover // max(1, len(sections) - 1))))

        render(writer, section_gap)


class ScarTaskPage(KneeboardPage):
    """Player briefing for a SCAR ("Sandy") rescue-escort flight.

    Sandy is the RESCAP escort in the Combat SAR package: hold near the FLOT with
    the King and Jolly Green, protect the downed pilot, suppress the threats around
    them, and walk the rescue helo in. The King (C-130 on-scene commander) runs the
    rescue and talks Sandy on; this page is role guidance, not exact values.
    """

    def __init__(self, flight: FlightData, dark_kneeboard: bool) -> None:
        self.flight = flight
        self.dark_kneeboard = dark_kneeboard

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self.render_into(writer)
        writer.write(path)

    def render_into(self, writer: KneeboardPageWriter) -> None:
        custom = f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
        writer.title(f"{self.flight.callsign} SCAR{custom}")

        writer.heading("ROLE — SANDY (RESCAP escort)")
        writer.text(
            "You are SANDY: the rescue escort in the Combat SAR package. Hold near "
            "the FLOT with the KING (C-130 on-scene commander) and JOLLY GREEN (the "
            "rescue helo). Bring the downed pilot home alive — protect the survivor, "
            "suppress the threats around them, and walk Jolly Green in.",
            wrap=True,
        )

        writer.heading("WHEN A PILOT GOES DOWN")
        writer.text(
            "- Work for the KING — he runs the rescue and talks you onto the survivor "
            "and the threats (voice/SRS; smoke and marks back him up).\n"
            "- Kill the air defences and troops near the survivor so JOLLY GREEN can "
            "get in and out. Keep the rescue helo alive — it is the mission.\n"
            "- The enemy may push a party to capture the downed pilot. If they do, "
            "destroy it before it reaches the survivor.",
            wrap=True,
        )

        writer.heading("COORDINATION")
        writer.text(
            "- KING (C-130): on-scene commander — check in, take his talk-on, hold "
            "where he tells you.\n"
            "- JOLLY GREEN (helo): the pickup — escort it in, suppress on ingress, "
            "cover the hover.\n"
            "- Get the pilot to a friendly field and the aviator is spared at debrief.",
            wrap=True,
        )


def build_airfield_directory_rows(
    game: "Game",
    flight: "FlightData",
    atis_by_name: dict[str, RadioFrequency],
) -> List[List[str]]:
    """Build directory rows (Field | ATC | ATIS | TCN | I(C)LS | RWY) for all
    blue airfields, sorted by name."""

    def fmt(freq: Optional[RadioFrequency]) -> str:
        if freq is None:
            return ""
        channel = flight.channel_for(freq)
        if channel is None:
            return str(freq)
        name = flight.aircraft_type.channel_name(channel.radio_id, channel.channel)
        return f"{name}\n{freq}"

    rows: List[List[str]] = []
    airfields = [
        cp
        for cp in game.theater.controlpoints
        if isinstance(cp, Airfield) and cp.is_friendly(flight.friendly)
    ]
    for cp in sorted(airfields, key=lambda c: c.full_name):
        rw = cp.active_runway(game.theater, game.conditions, {})
        if rw.ils is not None:
            ils = str(rw.ils)
        elif rw.icls is not None:
            ils = str(rw.icls)
        else:
            ils = ""
        rows.append(
            [
                cp.full_name,
                fmt(rw.atc),
                fmt(atis_by_name.get(cp.full_name)),
                str(rw.tacan) if rw.tacan is not None else "",
                ils,
                rw.runway_name,
            ]
        )
    return rows


#: Short codes for the intel-tier bands on the Threat Intel Brief, so an
#: undiscovered site can be labelled by tier ("Unidentified MERAD") without
#: leaking its exact system.
_AD_BAND_SHORT = {
    "Long-range SAM": "LORAD",
    "Medium-range SAM": "MERAD",
    "Short-range SAM": "SHORAD",
    "Point-defense SAM": "PD SAM",
    "AAA": "AAA",
    "Early-warning radar": "EWR",
}


def _threat_harm_code(tgo: TheaterGroundObject) -> Optional[int]:
    """First HARM ALIC code among the site's live units, or None if none is coded."""
    for unit in tgo.units:
        if not unit.alive:
            continue
        try:
            return AlicCodes.code_for(unit)
        except KeyError:
            continue
    return None


# Which of a SAM/EWR site's units names its threat card and supplies the curated
# reference. UNLIKE the recon-map "greatest threat" ranking (``_greatest_alive_threat``,
# which keys on the lethal *radar* to size the engagement ring), a SEAD/DEAD brief
# should name the *weapon system* the player is tied to. So launchers and track radars
# (the HARM-targetable shooters) outrank the search / acquisition / early-warning radars
# whose DCS display names read as "... SR" and would otherwise hijack the card — e.g. an
# SA-5 site labelled by its co-located ST-68U "Tin Shield SR" (and described as the
# weaponless EWR) instead of its Square Pair TR. A bare search/EW radar still names its own
# card (nothing lethal outranks it), which is honest. Lower wins.
_CARD_IDENTITY_PRIORITY: Dict[UnitClass, int] = {
    UnitClass.TRACK_RADAR: 1,  # Square Pair, Flap Lid, Low Blow, Hawk TR
    UnitClass.SEARCH_TRACK_RADAR: 1,  # Straight Flush (SA-6) — lethal & signature
    UnitClass.TELAR: 1,  # Fire Dome (SA-11), Tor, Tunguska, Osa, Roland
    UnitClass.LAUNCHER: 2,  # bare launchers (S-200, S-300 TEL, SA-2/3)
    UnitClass.MANPAD: 2,
    UnitClass.SHORAD: 2,
    UnitClass.AAA: 3,
    UnitClass.SEARCH_RADAR: 6,  # Big Bird, Snow Drift, Tin Shield, Flat Face, Dog Ear
    UnitClass.SPECIALIZED_RADAR: 6,  # Clam Shell
    UnitClass.EARLY_WARNING_RADAR: 7,  # 1L13 / 55G6 — only names a card when alone
}
_CARD_IDENTITY_DEFAULT = 5


def _system_identity(
    tgo: TheaterGroundObject,
) -> Tuple[Optional[str], Optional[ThreatReference]]:
    """Display name + curated reference identifying a site as its weapon system.

    Picks the highest-priority unit (weapon system over search/EW radar — see
    ``_CARD_IDENTITY_PRIORITY``) for the card name, and the first curated reference
    found scanning units in that same order for the stat block. Live units win ties
    over dead ones, so a partially-attrited site still names from a survivor; the name
    is otherwise stable across losses so live and dead sites of one system share a card.
    Returns ``(None, None)`` only when the site has no units at all.
    """
    units = list(tgo.units)
    if not units:
        return None, None

    def rank(unit: TheaterUnit) -> Tuple[int, int]:
        unit_type = getattr(unit, "unit_type", None)
        unit_class = getattr(unit_type, "unit_class", None)
        priority = (
            _CARD_IDENTITY_PRIORITY.get(unit_class, _CARD_IDENTITY_DEFAULT)
            if isinstance(unit_class, UnitClass)
            else _CARD_IDENTITY_DEFAULT
        )
        # Alive first within a tier (0 sorts before 1); sorted() is stable otherwise.
        return priority, 0 if getattr(unit, "alive", False) else 1

    ordered = sorted(units, key=rank)

    name: Optional[str] = None
    for unit in ordered:
        candidate = getattr(getattr(unit, "unit_type", None), "display_name", None)
        if candidate:
            name = candidate
            break
    if name is None:
        name = ordered[0].type.name

    ref: Optional[ThreatReference] = None
    for unit in ordered:
        ref = reference_for(unit.type.id)
        if ref is not None:
            break
    return name, ref


def _bullseye_brg_range(bullseye: Bullseye, position: Point) -> str:
    """Bullseye bearing/range cue ("045/30") to a position, ~1° / 1nm accuracy."""
    bearing = bullseye.position.heading_between_point(position)
    distance = meters(bullseye.position.distance_to_point(position))
    return f"{bearing:03.0f}/{distance.nautical_miles:.0f}"


@dataclass(frozen=True)
class ThreatCard:
    """One enemy air-defense *system* in the dossier (all its sites aggregated)."""

    system: str
    band: str
    identified: bool
    guidance: str
    ceiling: str
    mez_nm: str
    detect_nm: str
    harm: str
    live: int
    dead: int
    cues: List[str]
    defeat: str
    sort_range_m: float


@dataclass
class _KnownAccum:
    band: str
    live: int = 0
    dead: int = 0
    mez_m: float = 0.0
    det_m: float = 0.0
    harm: Optional[str] = None
    ref: Optional[ThreatReference] = None
    cues: List[str] = field(default_factory=list)


@dataclass
class _UnknownAccum:
    band: str
    count: int = 0
    cues: List[str] = field(default_factory=list)


def build_threat_intel_cards(
    game: "Game", flight: FlightData
) -> Tuple[List[ThreatCard], int]:
    """Per-system threat cards for the enemy air-defense laydown (recon-fog aware).

    Sites are aggregated by system: each identified system becomes one card with a
    curated stat block (guidance, ceiling, defeat note from
    ``game.data.threat_reference``) over its live numbers (MEZ, detection, HARM
    ALIC) plus the live/dead site counts and bullseye cues. Recon fog (design §3): a
    site the player has not identified (``known_for`` False) contributes only to a
    per-band "Unidentified MERAD" card — its system, ring and HARM code are withheld
    until a TARPS overflight reveals it. Cards sort live-most-lethal → unidentified.
    Returns the cards plus the count of unidentified sites (for the intro line).
    """
    player = flight.friendly
    bullseye = game.coalition_for(player).bullseye

    known: Dict[str, _KnownAccum] = {}
    unknown: Dict[str, _UnknownAccum] = {}
    unidentified = 0
    for tgo in game.theater.ground_objects:
        if not isinstance(tgo, (SamGroundObject, EwrGroundObject)):
            continue
        if tgo.is_friendly(player):
            continue
        band = tgo.air_defense_band
        short = _AD_BAND_SHORT.get(band or "", band or "AD")
        cue = _bullseye_brg_range(bullseye, tgo.position)
        if not tgo.known_for(player):
            unidentified += 1
            unknown_acc = unknown.setdefault(short, _UnknownAccum(short))
            unknown_acc.count += 1
            unknown_acc.cues.append(cue)
            continue
        name, ref = _system_identity(tgo)
        if name is None:
            name = band or "AD site"
        site = known.setdefault(name, _KnownAccum(short))
        if tgo.is_dead(player):
            site.dead += 1
        else:
            site.live += 1
        site.cues.append(cue)
        site.mez_m = max(site.mez_m, tgo.max_threat_range(player).meters)
        site.det_m = max(site.det_m, tgo.max_detection_range(player).meters)
        if site.harm is None:
            code = _threat_harm_code(tgo)
            site.harm = str(code) if code is not None else None
        if site.ref is None:
            site.ref = ref

    cards: List[ThreatCard] = []
    for name, site in known.items():
        ref = site.ref
        cards.append(
            ThreatCard(
                system=name,
                band=site.band,
                identified=True,
                guidance=ref.guidance if ref else "—",
                ceiling=f"{ref.ceiling_ft:,} ft" if ref and ref.ceiling_ft else "—",
                mez_nm=(
                    f"{meters(site.mez_m).nautical_miles:.0f}"
                    if site.mez_m > 0
                    else "—"
                ),
                detect_nm=(
                    f"{meters(site.det_m).nautical_miles:.0f}"
                    if site.det_m > 0
                    else "—"
                ),
                harm=site.harm or "—",
                live=site.live,
                dead=site.dead,
                cues=site.cues,
                defeat=ref.defeat if ref else "",
                sort_range_m=site.mez_m,
            )
        )
    # Live, longest-range systems first.
    cards.sort(key=lambda c: (0 if c.live else 1, -c.sort_range_m))

    unknown_cards = [
        ThreatCard(
            system=f"Unidentified {acc.band}",
            band=acc.band,
            identified=False,
            guidance="—",
            ceiling="—",
            mez_nm="—",
            detect_nm="—",
            harm="—",
            live=acc.count,
            dead=0,
            cues=acc.cues,
            defeat="",
            sort_range_m=0.0,
        )
        for acc in sorted(unknown.values(), key=lambda a: a.band)
    ]
    return cards + unknown_cards, unidentified


class ThreatIntelBriefPage(KneeboardPage):
    """Enemy air-defense dossier for the player — one card per system.

    Adapts the per-system "threat card" of professional campaign Intelligence
    Briefings to the dynamic campaign: each identified SAM/EWR system gets a card
    with a curated stat block (guidance, ceiling, **how to defeat**) over its live
    numbers (MEZ, detection, HARM ALIC), site counts and bullseye cues. Recon-fog
    aware (design §3): undiscovered sites collapse into per-band "Unidentified"
    cards until a TARPS overflight reveals them. Cards pack down the page and
    overflow onto continuation pages.
    """

    def __init__(
        self,
        flight: FlightData,
        cards: List[ThreatCard],
        unidentified: int,
        dark_kneeboard: bool,
        continued: bool = False,
    ) -> None:
        self.flight = flight
        self.cards = cards
        self.unidentified = unidentified
        self.dark_kneeboard = dark_kneeboard
        self.continued = continued

    def _title(self) -> str:
        custom = f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
        cont = " (cont.)" if self.continued else ""
        return f"{self.flight.callsign} Threat Intel Brief{custom}{cont}"

    def _intro(self) -> str:
        intro = "Enemy air-defense laydown. MEZ in nm; BE = bullseye bearing/range."
        if self.unidentified:
            # No total count: how many unidentified (often mobile) sites are in
            # theatre is intel we wouldn't realistically have (design §3).
            intro += " Unidentified contacts remain — fly TARPS recon to ID."
        return intro

    def _heading_font(self) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(
            "courbd.ttf", 26, layout_engine=ImageFont.Layout.BASIC
        )

    def _body_font(self) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(
            "courbd.ttf", 19, layout_engine=ImageFont.Layout.BASIC
        )

    def _draw_header(self, writer: KneeboardPageWriter) -> None:
        writer.title(self._title())
        if not self.continued:
            writer.text(self._intro(), wrap=True)
        writer.vspace(4)

    @staticmethod
    def _fit_cues(
        cues: List[str],
        limit: int,
        *,
        count_overflow: bool,
        font: Optional[ImageFont.FreeTypeFont] = None,
        avail_px: Optional[float] = None,
    ) -> str:
        """Bullseye cue list truncated to a hard ``limit`` AND (when a font + width are
        given) to the pixels available on the line, so the cue string never runs off
        the right edge. Overflow shows the remaining count ("+N") when ``count_overflow``
        else an ellipsis ("…") -- an unidentified card withholds its count (design §3).
        """
        shown: List[str] = []
        for cue in cues[:limit]:
            if (
                shown
                and font is not None
                and avail_px is not None
                and font.getlength(", ".join(shown + [cue])) > avail_px
            ):
                break
            shown.append(cue)
        text = ", ".join(shown)
        remaining = len(cues) - len(shown)
        if remaining > 0:
            text += f", +{remaining}" if count_overflow else ", …"
        return text

    def _render_card(self, writer: KneeboardPageWriter, card: ThreatCard) -> None:
        body = self._body_font()
        # System name in emphasis; the same four-colour scheme as the Brief Sheet --
        # amber = the threat envelope (MEZ/Detect), blue = the HARM code + bullseye cues.
        writer.text(card.system, font=self._heading_font(), fill=writer.col_emphasis)
        writer.rule(gap_below=4)
        if card.identified:
            writer.text(
                f"Guidance: {card.guidance}    Ceiling: {card.ceiling}", font=body
            )
            writer.text_runs(
                [
                    ("MEZ ", None),
                    (f"{card.mez_nm} nm", writer.col_caution),
                    ("   Detect ", None),
                    (f"{card.detect_nm} nm", writer.col_caution),
                    ("   HARM ", None),
                    (card.harm, writer.col_nav),
                    ("   Band ", None),
                    (card.band, None),
                ],
                font=body,
            )
            sites = f"Sites: {card.live} live"
            if card.dead:
                sites += f" / {card.dead} dead"
            prefix = f"{sites}   BE "
            writer.text_runs(
                [
                    (prefix, None),
                    (
                        self._fit_cues(
                            card.cues,
                            6,
                            count_overflow=True,
                            font=body,
                            avail_px=self._cue_avail_px(writer, body, prefix),
                        ),
                        writer.col_nav,
                    ),
                ],
                font=body,
            )
            if card.defeat:
                writer.text(f"DEFEAT: {card.defeat}", font=body, wrap=True)
        else:
            prefix = "Fly TARPS to ID.   BE "
            writer.text_runs(
                [
                    (prefix, None),
                    (
                        self._fit_cues(
                            card.cues,
                            8,
                            count_overflow=False,
                            font=body,
                            avail_px=self._cue_avail_px(writer, body, prefix),
                        ),
                        writer.col_nav,
                    ),
                ],
                font=body,
            )
        writer.vspace(16)

    @staticmethod
    def _cue_avail_px(
        writer: KneeboardPageWriter, font: ImageFont.FreeTypeFont, prefix: str
    ) -> float:
        """Pixels left on the cue line after the label prefix and a margin reserved
        for the overflow marker (", +NN" / ", …")."""
        line_left = writer.image_size[0] - writer.page_margin - writer.x
        return line_left - font.getlength(prefix) - font.getlength(", +99")

    def _card_height(self, card: ThreatCard) -> int:
        probe = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        probe.y = 0
        self._render_card(probe, card)
        return probe.y

    def render_cards(self, writer: KneeboardPageWriter) -> int:
        """Draw as many cards as fit below the cursor; return the number drawn.

        Used by the compact deck's Threats & Targets page, which composes the cards
        under a shared title with the target ALIC table. Greedy single-page fill (no
        continuation) so the compact deck stays within its page budget.
        """
        limit = writer.image_size[1] - writer.page_margin
        drawn = 0
        for card in self.cards:
            if drawn and writer.y + self._card_height(card) > limit:
                break
            self._render_card(writer, card)
            drawn += 1
        return drawn

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self._draw_header(writer)
        for card in self.cards:
            self._render_card(writer, card)
        writer.write(path)

    def paginate(self) -> List[KneeboardPage]:
        # Greedily pack cards down each page; overflow starts a continuation page
        # (header repeats, intro only on the first). Always place >=1 card per page
        # so an over-tall card can't loop.
        pages: List[KneeboardPage] = []
        remaining = self.cards
        continued = self.continued
        while remaining:
            page = ThreatIntelBriefPage(
                self.flight, [], self.unidentified, self.dark_kneeboard, continued
            )
            writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
            page._draw_header(writer)
            limit = writer.image_size[1] - writer.page_margin
            fit = 0
            for card in remaining:
                if fit and writer.y + self._card_height(card) > limit:
                    break
                self._render_card(writer, card)
                fit += 1
            pages.append(
                ThreatIntelBriefPage(
                    self.flight,
                    remaining[:fit],
                    self.unidentified,
                    self.dark_kneeboard,
                    continued,
                )
            )
            remaining = remaining[fit:]
            continued = True
        return pages or [self]


def _brief_sam_threats(cards: List[ThreatCard], limit: int = 3) -> str:
    """Condensed top live SAM/AD systems: 'SA-5 S-200 138nm · SA-10 65nm · ...'."""
    bits: List[str] = []
    for card in cards:
        if not (card.identified and card.live):
            continue
        label = card.system.split('"')[0] if '"' in card.system else card.system
        label = " ".join(label.replace("SAM ", "").split()[:3])[:16]
        suffix = f" {card.mez_nm}nm" if card.mez_nm not in ("—", "") else ""
        bits.append(f"{label}{suffix}".strip())
        if len(bits) >= limit:
            break
    return " · ".join(bits)


def _brief_loadout(units: List[Any]) -> str:
    """One-line **ordnance** summary from the lead aircraft's generated pylons.

    Keeps the munitions a pilot briefs (bombs, missiles, rockets); a targeting pod
    collapses to a single "TGP" and fuel tanks to "bag". Skips the noise -- ECM pods,
    empty/clean stations, and clsids that don't resolve to a named weapon. Counts by
    station and strips a rack multiplier from the name ("2xGBU-12" -> "GBU-12").
    """
    if not units:
        return ""
    pylons = getattr(units[0], "pylons", None) or {}
    counts: Dict[str, int] = {}
    order: List[str] = []
    has_tgp = False
    has_hts = False
    for station in pylons.values():
        clsid = station.get("CLSID") if isinstance(station, dict) else None
        if not clsid:
            continue
        weapon = Weapon.with_clsid(clsid)
        if weapon is None:
            continue
        if getattr(weapon.weapon_group, "type", None) is WeaponType.TGP:
            has_tgp = True
            continue
        name = (getattr(weapon.weapon_group, "name", None) or weapon.name or "").strip()
        low = name.lower()
        if "harm targeting" in low:  # AN/ASQ-213 HTS pod -- a SEAD sensor, not a weapon
            has_hts = True
            continue
        if (
            not name
            or name == "Unknown"
            or "clean" in low
            or "pylon" in low
            or "ecm" in low
            or "jammer" in low
        ):
            continue
        if "fuel" in low or "tank" in low:
            name = "bag"
        elif name[0].isdigit() and "x" in name[:4].lower():
            name = name.split("x", 1)[1].strip()  # strip a rack multiplier
        if name not in counts:
            order.append(name)
        counts[name] = counts.get(name, 0) + 1
    parts = [(f"{counts[n]}× {n}" if counts[n] > 1 else n) for n in order]
    if has_hts:
        parts.append("HTS")
    if has_tgp:
        parts.append("TGP")
    return " · ".join(parts)


class NotesPage(KneeboardPage):
    """A kneeboard page containing the campaign owner's notes."""

    def __init__(
        self,
        notes: str,
        dark_kneeboard: bool,
    ) -> None:
        self.notes = notes
        self.dark_kneeboard = dark_kneeboard

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        writer.title(f"Notes")
        writer.text(self.notes, wrap=True)
        writer.write(path)


def _abbreviated_target_name(name: str) -> str:
    """Shorten verbose target prefixes so long names fit the kneeboard tables.

    Front-line objectives are named "Front line <CP A>/<CP B>", wide enough to
    overflow the packages list and crowd the map labels; "Front" is
    unambiguous in context.
    """
    return name.replace("Front line ", "Front ")


class PackagesMapPage(KneeboardPage):
    """A theater map with each attack package's target labelled.

    Draws the theater coastline (filled land over sea, from the recon module's
    landmap) so the pilot can see where the attack packages on the previous
    page are headed. Control points are marked for orientation: airfields,
    carriers and LHAs get a distinct shape (square / diamond / triangle) and a
    haloed name label, while FOBs and other points stay as plain dots. All are
    coloured by side (blue friendly, red enemy). Overlapping labels are stacked
    downward (and flipped left near the right edge).
    """

    FRIENDLY = (40, 90, 200)
    ENEMY = (200, 45, 45)
    NEUTRAL = (110, 110, 110)
    TARGET = (255, 140, 0)

    def __init__(
        self,
        targets: List[Tuple[str, float, float]],
        control_points: List[Tuple[float, float, str, str, str]],
        terrain: "Terrain",
        dark_kneeboard: bool,
    ) -> None:
        self.targets = targets
        self.control_points = control_points
        self.terrain = terrain
        self.dark_kneeboard = dark_kneeboard

    def write(self, path: Path) -> None:
        from dcs.mapping import Point as DcsPoint
        from .kneeboard_recon.basemap import render_landmap_basemap
        from .kneeboard_recon.extent import MapExtent, aspect_correct
        from .kneeboard_recon.projection import Projector

        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        writer.title("Package Targets Map")
        label_font = ImageFont.truetype(
            "courbd.ttf", 13, layout_engine=ImageFont.Layout.BASIC
        )
        writer.text(
            "Orange = package targets; airfields, carriers & LHAs are named "
            "(blue = friendly, red = enemy).",
            font=label_font,
        )

        points = [(x, y) for _, x, y in self.targets]
        points += [(x, y) for x, y, *_ in self.control_points]
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        margin = writer.page_margin
        top = writer.y + 8
        avail_w = writer.image_size[0] - 2 * margin
        avail_h = writer.image_size[1] - top - margin

        # World bounding box of everything shown, plus an 8% margin.
        pad = 0.08 * max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
        extent = MapExtent(
            min_x=min(xs) - pad,
            max_x=max(xs) + pad,
            min_y=min(ys) - pad,
            max_y=max(ys) + pad,
            terrain=self.terrain,
        )

        # Size the rendered map to the area-of-operations aspect rather than
        # stretching it to fill the near-square page. A wide, short theater
        # (carriers far offshore + inland targets) would otherwise be aspect-
        # padded with ~half a page of empty sea above and below, squashing the
        # actual front into the middle. Fit to the binding axis, then centre the
        # strip so it reads as a deliberate map rather than a cut-off frame.
        # Page-x (width) <- DCS y (east); page-y (height) <- DCS x (north).
        content_ew = max(extent.span_y_m, 1.0)
        content_ns = max(extent.span_x_m, 1.0)
        map_w = avail_w
        map_h = round(map_w * content_ns / content_ew)
        if map_h > avail_h:
            map_h = avail_h
            map_w = round(map_h * content_ew / content_ns)
        off_x = margin + (avail_w - map_w) // 2
        off_y = top + (avail_h - map_h) // 2

        extent = aspect_correct(extent, map_w, map_h)
        writer.image.paste(
            render_landmap_basemap(extent, map_w, map_h, dark=self.dark_kneeboard),
            (off_x, off_y),
        )

        projector = Projector(extent=extent, pixel_width=map_w, pixel_height=map_h)

        def to_px(x: float, y: float) -> Tuple[int, int]:
            px, py = projector.project(DcsPoint(x, y, self.terrain))
            return off_x + px, off_y + py

        draw = writer.draw
        base_labels: List[Tuple[str, int, int, Tuple[int, int, int]]] = []
        for x, y, side, kind, name in self.control_points:
            px, py = to_px(x, y)
            color = (
                self.FRIENDLY
                if side == "friendly"
                else self.ENEMY if side == "enemy" else self.NEUTRAL
            )
            if kind == "airbase":
                draw.rectangle(
                    (px - 4, py - 4, px + 4, py + 4), fill=color, outline=(0, 0, 0)
                )
            elif kind == "carrier":
                draw.polygon(
                    [(px, py - 5), (px + 5, py), (px, py + 5), (px - 5, py)],
                    fill=color,
                    outline=(0, 0, 0),
                )
            elif kind == "lha":
                draw.polygon(
                    [(px, py - 5), (px + 5, py + 4), (px - 5, py + 4)],
                    fill=color,
                    outline=(0, 0, 0),
                )
            else:
                draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=color)
                continue
            base_labels.append((name, px, py, color))

        placed: List[Tuple[float, float, float, float]] = []

        def overlaps(box: Tuple[float, float, float, float]) -> bool:
            ax0, ay0, ax1, ay1 = box
            return any(
                ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1
                for bx0, by0, bx1, by1 in placed
            )

        label_h = 15
        right_edge = off_x + map_w
        bottom_edge = off_y + map_h - label_h
        for name, x, y in self.targets:
            px, py = to_px(x, y)
            draw.ellipse(
                [px - 5, py - 5, px + 5, py + 5], fill=self.TARGET, outline=(0, 0, 0)
            )
            tw = label_font.getlength(name)
            lx = px - 8 - tw if px + 8 + tw > right_edge else px + 8
            ly = py - 7
            # Stack overlapping labels downward so clustered targets stay legible.
            while overlaps((lx, ly, lx + tw, ly + label_h)) and ly < bottom_edge:
                ly += label_h
            placed.append((lx, ly, lx + tw, ly + label_h))
            # White plate behind the label so it reads against the map.
            draw.rectangle(
                (lx - 1, ly, lx + tw + 1, ly + label_h), fill=(255, 255, 255)
            )
            draw.text((lx, ly), name, font=label_font, fill=(0, 0, 0))

        # Base names: a white halo instead of a solid plate, in the base's side
        # colour, so they read apart from the boxed black-on-white target labels.
        base_font = ImageFont.truetype(
            "courbd.ttf", 12, layout_engine=ImageFont.Layout.BASIC
        )
        for name, px, py, color in base_labels:
            tw = base_font.getlength(name)
            lx = px - 8 - tw if px + 8 + tw > right_edge else px + 8
            ly = py - 6
            while overlaps((lx, ly, lx + tw, ly + label_h)) and ly < bottom_edge:
                ly += label_h
            placed.append((lx, ly, lx + tw, ly + label_h))
            draw.text(
                (lx, ly),
                name,
                font=base_font,
                fill=color,
                stroke_width=2,
                stroke_fill=(255, 255, 255),
            )

        writer.write(path)


class KneeboardIndexPage(KneeboardPage):
    """Flight index fronting a stacked multi-flight airframe deck (§27).

    DCS scopes kneeboards per *airframe*, so every client flight of a type
    shares one stacked deck. This page maps callsign -> start page so a pilot
    can flip straight to their own block. Only generated when 2+ client
    flights share the airframe; a lone flight needs no index.
    """

    HEADERS = ["Flight", "Task", "Page"]

    def __init__(
        self,
        aircraft: AircraftType,
        rows: List[List[str]],
        dark_kneeboard: bool,
    ) -> None:
        self.aircraft = aircraft
        self.rows = rows
        self.dark_kneeboard = dark_kneeboard

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        writer.title(f"{self.aircraft.display_name} — Flight Index")
        writer.text(
            "DCS stacks every flight of this airframe into one kneeboard. "
            "Flip to your callsign's start page.",
            wrap=True,
        )
        writer.vspace(6)
        writer.table(self.rows, headers=self.HEADERS)
        writer.write(path)


class KneeboardGenerator(MissionInfoGenerator):
    """Creates kneeboard pages for each client flight in the mission."""

    #: Tasks shown with a patrol window (start - end) instead of a single TOT.
    PATROL_TASKS = frozenset(
        {
            FlightType.BARCAP,
            FlightType.TARCAP,
            FlightType.REFUELING,
            FlightType.AEWC,
        }
    )

    def __init__(
        self, mission: Mission, game: "Game", red_net: Optional[Any] = None
    ) -> None:
        super().__init__(mission, game)
        self.dark_kneeboard = self.game.settings.generate_dark_kneeboard and (
            self.mission.start_time.hour > 19 or self.mission.start_time.hour < 7
        )
        # §70 C2: this mission's red-net plan (MissionData.red_net), so the
        # COMINT block can brief the active nets. None when red_comms_net is
        # off or nothing transmits.
        self.red_net = red_net

    def generate(self) -> None:
        """Generates a kneeboard per client flight, grouped by airframe.

        DCS scopes kneeboards per airframe, so all client flights of a type share one
        stacked deck. Each flight's pages stay a contiguous block in deterministic
        (callsign-sorted) order; when 2+ flights share a type a one-page index is
        prepended so a pilot can flip straight to their own block (#P4).
        """
        temp_dir = Path("kneeboards")
        temp_dir.mkdir(exist_ok=True)
        for aircraft, flights in self.client_flights_by_airframe().items():
            aircraft_dir = temp_dir / aircraft.dcs_unit_type.id
            aircraft_dir.mkdir(exist_ok=True)
            # Per-flight concrete pages. paginate() may expand a flight's pages into
            # continuation pages, so flatten each flight's block before numbering.
            flight_blocks: List[Tuple[FlightData, List[KneeboardPage]]] = []
            for flight in flights:
                package_flights = [
                    f
                    for f in self.flights
                    if f.package is flight.package and f is not flight
                ]
                pages = self.generate_flight_kneeboard(flight, package_flights)
                concrete = [c for page in pages for c in page.paginate()]
                flight_blocks.append((flight, concrete))

            # When 2+ client flights share this airframe, front the stacked deck
            # with a callsign -> start-page index (§27); a lone flight's deck
            # opens straight on its Mission Info page, like stock.
            ordered_pages: List[KneeboardPage] = []
            if len(flight_blocks) > 1:
                ordered_pages.append(self._build_index_page(aircraft, flight_blocks))
            for _flight, concrete in flight_blocks:
                ordered_pages.extend(concrete)

            for idx, page in enumerate(ordered_pages):
                # The suffix picks the encoder: photographic recon basemaps go
                # out as JPEG, line-art pages stay PNG (see KneeboardPage).
                page_path = aircraft_dir / f"page{idx:02}{page.image_suffix}"
                page.write(page_path)
                self.mission.add_aircraft_kneeboard(aircraft.dcs_unit_type, page_path)
        for type in kneeboards_dir().iterdir():
            if type.is_dir():
                for kneeboard in type.iterdir():
                    self.mission.custom_kneeboards[type.name].append(kneeboard)
            else:
                self.mission.custom_kneeboards[""].append(type)

        # Player-imported custom kneeboards stored in the campaign save (see
        # game/customkneeboard.py). ``getattr`` default keeps pre-feature saves
        # working even if the __setstate__ migration hasn't run yet.
        self._inject_custom_kneeboards(
            getattr(self.game, "custom_kneeboards", []), temp_dir
        )

    def _inject_custom_kneeboards(
        self, custom_kneeboards: List["CustomKneeboard"], temp_dir: Path
    ) -> None:
        """Write each saved custom kneeboard to a temp PNG and register it.

        Bytes are written and appended like the loose-folder kneeboards: the ""
        key scopes to all client flights, an airframe id scopes to that type only
        (the finest grain DCS allows). Extracted from ``generate`` so the
        scope-routing is unit-testable without a full mission.
        """
        if not custom_kneeboards:
            return
        custom_dir = temp_dir / "_custom"
        custom_dir.mkdir(exist_ok=True)
        for idx, custom in enumerate(custom_kneeboards):
            image_path = custom_dir / f"custom{idx:02}.png"
            image_path.write_bytes(custom.image)
            key = custom.airframe_id or ""
            self.mission.custom_kneeboards[key].append(image_path)

    def client_flights_by_airframe(self) -> Dict[AircraftType, List[FlightData]]:
        """Client flights grouped by airframe, in deterministic per-airframe order.

        Only client flights are included. DCS does not support group-specific kneeboard
        pages, so every flight of a type shares the same stacked deck; sorting by
        callsign keeps the stack (and the index that fronts it) stable across
        regenerations.
        """
        by_airframe: Dict[AircraftType, List[FlightData]] = defaultdict(list)
        for flight in self.flights:
            if not flight.client_units:
                continue
            by_airframe[flight.aircraft_type].append(flight)
        for grouped in by_airframe.values():
            grouped.sort(key=lambda f: f.callsign)
        return by_airframe

    def _build_index_page(
        self,
        aircraft: AircraftType,
        flight_blocks: List[Tuple[FlightData, List[KneeboardPage]]],
    ) -> KneeboardPage:
        """The flight index fronting a stacked multi-flight airframe deck (§27).

        The index is page 1, so the first flight's block starts on page 2. Only
        called when 2+ client flights share the airframe.
        """
        rows: List[List[str]] = []
        page_cursor = 2  # this index is page 1
        for flight, concrete in flight_blocks:
            name = flight.callsign
            if flight.custom_name:
                name += f' ("{flight.custom_name}")'
            rows.append([name, flight.task_display_name, str(page_cursor)])
            page_cursor += len(concrete)
        return KneeboardIndexPage(aircraft, rows, self.dark_kneeboard)

    def _briefing_sitrep(self) -> Optional[Sitrep]:
        """The SITREP to show on the briefing page, gated by the setting + non-empty
        (§29): None on turn 1, after a quiet turn, or when the toggle is off."""
        return sitrep_for_kneeboard(
            getattr(self.game, "last_sitrep", None),
            self.game.settings.generate_sitrep_kneeboard,
        )

    def _briefing_comint(self) -> List[str]:
        """The §70 COMINT block for the briefing page ([] when the feature is off).

        Built at generation time on purpose: red's ATO for THIS mission is fully
        planned by now, so the Tier-2 tasking leak warns of a package actually
        flying today — and the active-nets listing (C2) briefs the frequencies
        the §70 C1 red net actually transmits on this mission.
        """
        from game.fourteenth.comint import comint_kneeboard_lines

        return comint_kneeboard_lines(self.game, self.red_net)

    def generate_task_page(self, flight: FlightData) -> Optional[KneeboardPage]:
        if flight.flight_type in (FlightType.DEAD, FlightType.SEAD):
            return SeadTaskPage(
                flight,
                self.game.coalition_for(flight.friendly).bullseye,
                self.dark_kneeboard,
            )
        elif flight.flight_type is FlightType.STRIKE:
            return StrikeTaskPage(flight, self.dark_kneeboard)
        elif flight.flight_type is FlightType.COMBAT_SAR:
            king_beacons: List[CombatSarKingBeacon] = []
            for f in self.flights:
                if (
                    f.flight_type is FlightType.COMBAT_SAR
                    and f.friendly.is_blue
                    and f.combat_sar_king is not None
                ):
                    king_beacons.append(f.combat_sar_king)
            return CombatSarTaskPage(flight, king_beacons, self.dark_kneeboard)
        elif flight.flight_type is FlightType.SCAR:
            return ScarTaskPage(flight, self.dark_kneeboard)
        return None

    def generate_flight_kneeboard(
        self, flight: FlightData, package_flights: List[FlightData]
    ) -> List[KneeboardPage]:
        """Returns a list of kneeboard pages for the given flight."""

        if flight.aircraft_type.utc_kneeboard:
            zoned_time = self.game.conditions.start_time.replace(
                tzinfo=self.game.theater.timezone
            ).astimezone(datetime.timezone.utc)
        else:
            zoned_time = self.game.conditions.start_time

        airfield_rows = (
            build_airfield_directory_rows(self.game, flight, self.atis_by_name)
            if self.atis_by_name
            else []
        )

        # De-duplication (design §4): drop blocks from the always-on Mission Info page
        # when an enabled optional page already carries the same data, so nothing is
        # printed twice. Each is conditional on the *other* page existing, so a deck
        # with options off is unchanged.
        recon_on = self.game.settings.generate_target_recon_kneeboard
        # The recon Departure page carries the field weather + winds + sunrise/sunset.
        omit_weather = recon_on and _should_emit_departure(flight, self.game)

        # Threat cards are computed once and feed the BLUF's condensed SAM line on
        # the Mission Info page and (when enabled) the dedicated Threat Intel
        # Brief. Computed unconditionally so the BLUF threat picture is present
        # even when the full brief page is off.
        threat_cards, unidentified = build_threat_intel_cards(self.game, flight)
        bluf_lines = self._bluf_lines(flight, threat_cards)

        # The JAM BACKUP fallback channel now lives in the Mission Info BLUF (above),
        # so keep it out of the Support Info comms ladder -- there it borrowed the
        # viewing flight's Type/#A/C columns and read as a phantom flight (§51).
        support_comms = [c for c in self.comms if c.name != JAM_BACKUP_COMM_NAME]

        pages: List[KneeboardPage] = [
            BriefingPage(
                flight,
                self.game.coalition_for(flight.friendly).bullseye,
                self.game.conditions.weather,
                zoned_time,
                self.dark_kneeboard,
                atis_by_name=self.atis_by_name,
                theater=self.game.theater,
                omit_weather=omit_weather,
                bluf_lines=bluf_lines,
                sitrep=self._briefing_sitrep(),
                comint_lines=self._briefing_comint(),
            ),
            SupportPage(
                flight,
                package_flights,
                support_comms,
                self.awacs,
                self.tankers,
                self.jtacs,
                zoned_time,
                self.dark_kneeboard,
                airfield_rows=airfield_rows,
                code_words=self._code_words_block(flight),
            ),
        ]

        # Only create the notes page if there are notes to show.
        if notes := self.game.notes:
            pages.append(NotesPage(notes, self.dark_kneeboard))

        # The SEAD/Strike Target Info page is superseded by the recon Detail page, which
        # already lists the same emitters + role + HARM ALIC over a satellite view. When
        # that detail page will be generated for this target, drop the standalone task
        # page -- but keep it in APPROXIMATE intel (the recon page shows exact coords,
        # while the task page intentionally fuzzes them; §5), so we only fold in EXACT.
        target = getattr(flight.package, "target", None)
        recon_detail_covers_target = (
            recon_on
            and flight.flight_type in _FLIGHT_TYPES_WITH_RECON
            and isinstance(target, TheaterGroundObject)
        )
        exact_intel = (
            self.game.settings.target_intel_precision is TargetIntelPrecision.EXACT
        )
        target_page = self.generate_task_page(flight)
        folds_into_recon = (
            recon_detail_covers_target
            and exact_intel
            and flight.flight_type
            in (FlightType.SEAD, FlightType.DEAD, FlightType.STRIKE)
        )
        if target_page is not None and not folds_into_recon:
            pages.append(target_page)

        # Enemy air-defense dossier (per-system cards, recon-fog aware), gated by
        # setting. Reuses the cards already built for the BLUF; only appended when
        # there are enemy air defenses to brief.
        if self.game.settings.generate_threat_intel_kneeboard and threat_cards:
            pages.append(
                ThreatIntelBriefPage(
                    flight, threat_cards, unidentified, self.dark_kneeboard
                )
            )

        # Recon overview + detail + airfield-departure pages (gated by settings).
        if self.game.settings.generate_target_recon_kneeboard:
            extra_radius_m = (
                self.game.settings.target_recon_extra_threat_search_nmi * 1852.0
            )
            pages.extend(
                generate_recon_pages(
                    flight=flight,
                    game=self.game,
                    weather=self.game.conditions.weather,
                    extra_threat_search_m=extra_radius_m,
                    dark=self.dark_kneeboard,
                )
            )

        # Friendly packages: a dedicated list page (de-duped from the Mission Info
        # page, where it used to fold + spill) plus the targets map, gated by settings.
        if self.game.settings.generate_all_packages_kneeboard:
            package_rows = self.build_all_packages_rows(flight)
            if package_rows:
                pages.append(
                    FriendlyPackagesPage(flight, package_rows, self.dark_kneeboard)
                )
            pages.extend(self.generate_packages_map_page(flight))

        return pages

    def _bluf_lines(
        self, flight: FlightData, threat_cards: List[ThreatCard]
    ) -> List[str]:
        """Compose the BLUF lines for the Mission Info page (priority on page one).

        The task line is always present (task, plus target/TOT when applicable);
        the push line is gated on the code-words feature; the JAM BACKUP line
        appears only when enemy comms jamming (§51) allocated a fallback channel.
        The threat, loadout and SAR lines carry the survivors of the retired
        one-page Brief Sheet: a compact air + SAM threat picture, a one-line
        ordnance summary, and the SAR assets + if-down drill.
        """
        lines: List[str] = []

        # Task / target / TOT.
        parts = [flight.task_display_name]
        target = getattr(flight.package, "target", None)
        target_name = getattr(target, "name", None)
        if target_name:
            parts.append(_abbreviated_target_name(target_name)[:40])
        task_line = "TASK  " + "  —  ".join(parts)
        tot = getattr(flight.package, "time_over_target", None)
        utc = flight.aircraft_type.utc_kneeboard
        if tot is not None and tot != datetime.datetime.min:
            task_line += (
                f"   TOT {SupportPage._format_time(self._to_kneeboard_time(tot, utc))}"
            )
        lines.append(task_line)

        # Push + event code words (gated by the feature toggle).
        if self.game.settings.enable_package_code_words:
            code_words = self.game.coalition_for(flight.friendly).code_words
            bits: List[str] = []
            push = code_words.push_for(flight.flight_type)
            if push:
                bits.append(f"PUSH {push}")
            bits.append(f"SUCCESS {code_words.success}")
            bits.append(f"ABORT {code_words.abort}")
            lines.append("   ".join(bits))

        # JAM BACKUP fallback channel (§51). The frequency is already registered on
        # the generator's comm ladder (missiongenerator.add_comm); surface it in the
        # BLUF next to the code words instead of the Support Info package table,
        # where the borrowed Type/#A/C columns made it read as a phantom flight. The
        # channel is freshly allocated (used by nothing), so it maps to no briefed
        # channel name -- str(freq) is exactly what the ladder would have shown.
        for comm in self.comms:
            if comm.name == JAM_BACKUP_COMM_NAME:
                lines.append(f"{JAM_BACKUP_COMM_NAME}  {comm.freq}")
                break

        # Compact threat picture: the enemy's likely CAP fighters + the condensed
        # top live SAM systems ("SA-5 S-200 138nm · SA-11 Buk 27nm · ...").
        air = self._brief_air_threats(flight)
        if air:
            lines.append(f"THREATS  AIR {air}")
        sam = _brief_sam_threats(threat_cards)
        if sam:
            lines.append(f"         SAM {sam}")

        # One-line ordnance summary from the lead jet's generated pylons.
        loadout = _brief_loadout(flight.units)
        if loadout:
            lines.append(f"LOADOUT  {loadout}")

        # SAR assets on this mission (King / Jolly / Sandy) + the if-down drill.
        sar_bits = " · ".join(
            f"{role} {airframe}" for role, airframe in self._brief_sar(flight)
        )
        if_down = "If down: beacon on, squawk 7700, get to high ground, voice on GUARD"
        lines.append(
            f"SAR      {sar_bits} — {if_down}" if sar_bits else f"SAR      {if_down}"
        )

        return lines

    def _code_words_block(self, flight: FlightData) -> Optional[CodeWordsBlock]:
        """The code-words block for the Support Info page, or None when the
        feature is off: one push word per task category present in the ATO (the
        flight's own marked), plus the event words (STOP JAM only with an EW
        package). The planners see the same words on the ATO package tooltip and
        the join waypoint; this is the in-cockpit copy.
        """
        if not self.game.settings.enable_package_code_words:
            return None
        coalition = self.game.coalition_for(flight.friendly)
        code_words = coalition.code_words
        own = push_category_for(flight.flight_type)
        present = present_categories(
            p.primary_task for p in coalition.ato.packages if p.primary_task is not None
        )
        if own is not None:
            present = present | {own}
        pushes = [
            (category.value, code_words.push[category], category is own)
            for category in PushCategory
            if category in present
        ]
        return CodeWordsBlock(
            theme=code_words.theme,
            pushes=pushes,
            success=code_words.success,
            abort=code_words.abort,
            stop_jam=code_words.stop_jam if PushCategory.EW in present else None,
        )

    def _brief_air_threats(self, flight: FlightData) -> str:
        """Loose, faction-derived air-threat line (the enemy's likely CAP fighters)."""
        try:
            opponent = self.game.coalition_for(flight.friendly).opponent
            fighters = [
                ac
                for ac in opponent.faction.aircraft
                if ac.capable_of(FlightType.BARCAP)
            ]
            fighters.sort(
                key=lambda ac: ac.task_priority(FlightType.BARCAP), reverse=True
            )
            names: List[str] = []
            for aircraft in fighters:
                if aircraft.variant_id not in names:
                    names.append(aircraft.variant_id)
                if len(names) >= 2:
                    break
            if names:
                return f"{' / '.join(names)} CAP likely near the front."
        except Exception:
            pass
        return "Enemy CAP possible near the front."

    def _brief_sar(self, flight: FlightData) -> List[Tuple[str, str]]:
        """King / Jolly / Sandy rescue assets from the side's Combat SAR + SCAR flights.

        The role IS the callsign (the SAR package flies as King / Jolly / Sandy), so the
        value is the **aircraft type** -- what to look for -- not a redundant callsign.
        """
        king: Optional[str] = None
        jolly: Optional[str] = None
        sandy: Optional[str] = None
        for other in self.flights:
            if other.friendly is not flight.friendly:
                continue
            airframe = other.aircraft_type.variant_id
            if other.flight_type is FlightType.COMBAT_SAR:
                if other.combat_sar_king is not None:
                    king = airframe
                elif jolly is None:
                    jolly = airframe
            elif other.flight_type is FlightType.SCAR and sandy is None:
                sandy = airframe
        sar: List[Tuple[str, str]] = []
        if king:
            sar.append(("King", king))
        if jolly:
            sar.append(("Jolly", jolly))
        if sandy:
            sar.append(("Sandy", sandy))
        return sar

    def _to_kneeboard_time(
        self, time: Optional[datetime.datetime], utc: bool
    ) -> Optional[datetime.datetime]:
        """Apply the same UTC/local convention the rest of the kneeboard uses."""
        if time is None:
            return None
        if utc:
            return time.replace(tzinfo=self.game.theater.timezone).astimezone(
                datetime.timezone.utc
            )
        return time

    def build_all_packages_rows(self, flight: FlightData) -> List[List[str]]:
        """One row per friendly package (target + TOT, or patrol window), sorted by time."""
        utc = flight.aircraft_type.utc_kneeboard
        ato = self.game.coalition_for(flight.friendly).ato
        entries: List[Tuple[datetime.datetime, List[str]]] = []
        for package in ato.packages:
            if not package.flights:
                continue
            target = (
                _abbreviated_target_name(package.target.name)[:40]
                if package.target is not None
                else ""
            )
            primary = package.primary_flight
            flight_plan = primary.flight_plan if primary is not None else None
            start = getattr(flight_plan, "patrol_start_time", None)
            end = getattr(flight_plan, "patrol_end_time", None)
            if package.primary_task in self.PATROL_TASKS and start and end:
                timing = (
                    f"{SupportPage._format_time(self._to_kneeboard_time(start, utc))}"
                    f" - {SupportPage._format_time(self._to_kneeboard_time(end, utc))}"
                )
                sort_key = start
            else:
                tot = package.time_over_target
                if tot is not None and tot != datetime.datetime.min:
                    timing = SupportPage._format_time(self._to_kneeboard_time(tot, utc))
                    sort_key = tot
                else:
                    timing = ""
                    sort_key = datetime.datetime.max
            entries.append((sort_key, [package.package_description, target, timing]))

        entries.sort(key=lambda entry: entry[0])
        return [row for _, row in entries]

    def generate_packages_map_page(self, flight: FlightData) -> List[KneeboardPage]:
        """A schematic theater map labelling where each friendly package is headed."""
        player = flight.friendly
        ato = self.game.coalition_for(player).ato
        targets: List[Tuple[str, float, float]] = []
        seen: set[str] = set()
        for package in ato.packages:
            if not package.flights or package.target is None:
                continue
            # Attack packages only -- skip the support patrols (CAP, AWACS,
            # tankers) that loiter rather than head to a target. Strike, CAS,
            # DEAD/SEAD, BAI, anti-ship, OCA, air assault and recon all show.
            if package.primary_task in self.PATROL_TASKS:
                continue
            if package.target.name in seen:
                continue
            seen.add(package.target.name)
            pos = package.target.position
            targets.append(
                (_abbreviated_target_name(package.target.name)[:40], pos.x, pos.y)
            )
        if not targets:
            return []

        control_points: List[Tuple[float, float, str, str, str]] = []
        for cp in self.game.theater.controlpoints:
            if cp.captured == player:
                side = "friendly"
            elif cp.captured.is_neutral:
                side = "neutral"
            else:
                side = "enemy"
            # Fixed bases that can host aircraft get a distinct icon + name;
            # FOBs and off-map spawns stay anonymous dots to avoid clutter.
            if cp.is_carrier:
                kind = "carrier"
            elif cp.is_lha:
                kind = "lha"
            elif cp.category == "airfield":
                kind = "airbase"
            else:
                kind = "dot"
            name = cp.name[:24] if kind != "dot" else ""
            control_points.append((cp.position.x, cp.position.y, side, kind, name))

        return [
            PackagesMapPage(
                targets,
                control_points,
                self.game.theater.terrain,
                self.dark_kneeboard,
            )
        ]
