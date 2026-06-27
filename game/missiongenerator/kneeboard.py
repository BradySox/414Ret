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
from typing import Callable, Dict, Iterator, List, Optional, TYPE_CHECKING, Tuple

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
from game.data.brevity_reference import brevity_for
from game.data.threat_reference import ThreatReference, reference_for
from game.dcs.aircrafttype import AircraftType
from game.radio.radios import RadioFrequency
from game.runways import RunwayData
from game.settings.settings import TargetIntelPrecision
from game.theater import FrontLine, TheaterGroundObject, TheaterUnit
from game.theater.bullseye import Bullseye
from game.theater.controlpoint import Airfield, ControlPoint
from game.theater.theatergroundobject import EwrGroundObject, SamGroundObject
from game.utils import Distance, UnitSystem, inches_hg, meters, mps, pounds
from game.weather.weather import Weather
from .aircraft.flightdata import CombatSarKingBeacon, FlightData
from .briefinggenerator import CommInfo, JtacInfo, MissionInfoGenerator
from .kneeboard_page import KneeboardPage
from .kneeboard_recon import airport_imagery as _airport_imagery
from .kneeboard_recon import generate_recon_pages
from .kneeboard_recon.pages import (
    _FLIGHT_TYPES_WITH_RECON,
    _greatest_alive_threat,
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
from .scarluadata import ScarTasking
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
        else:
            self.foreground_fill = (15, 15, 15)
            # Light grey rather than near-white: avoids glare under HDR / Auto-HDR
            # while staying perfectly readable in daylight.
            self.background_fill = (210, 210, 210)
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
        table = tabulate(cells, headers=headers, numalign="right")
        self.text(table, font, fill=self.foreground_fill)

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
        self.image.save(path)
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
        include_min_fuel: bool = True,
    ) -> None:
        self.start_time = start_time
        self.rows: List[List[str]] = []
        self.target_points: List[NumberedWaypoint] = []
        self.last_waypoint: Optional[FlightWaypoint] = None
        self.units = units
        # Drop the Min-fuel column when the dedicated Fuel Ladder page owns the fuel
        # ladder (avoids printing the bingo-at-waypoint figure on two pages).
        self.include_min_fuel = include_min_fuel

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
        ]
        if self.include_min_fuel:
            row.append(self._format_min_fuel(self.target_points[0].waypoint.min_fuel))
        self.rows.append(row)
        self.last_waypoint = self.target_points[-1].waypoint

    def add_waypoint_row(self, waypoint: NumberedWaypoint) -> None:
        row = [
            str(waypoint.number),
            KneeboardPageWriter.wrap_line(
                waypoint.waypoint.display_name,
                FlightPlanBuilder.WAYPOINT_DESC_MAX_LEN,
            ),
            self._format_alt(waypoint.waypoint.alt),
            self._waypoint_distance(waypoint.waypoint),
            self._waypoint_bearing(waypoint.waypoint),
            self._ground_speed(waypoint.waypoint),
            self._format_time(waypoint.waypoint.tot),
            self._format_time(waypoint.waypoint.departure_time),
        ]
        if self.include_min_fuel:
            row.append(self._format_min_fuel(waypoint.waypoint.min_fuel))
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

    def _waypoint_bearing(self, waypoint: FlightWaypoint) -> str:
        if self.last_waypoint is None:
            return "-"
        bearing = self.last_waypoint.position.heading_between_point(waypoint.position)

        return f"{(bearing):.0f}"

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

        if (waypoint.tot - last_time).total_seconds() == 0.0:
            return "-"

        speed = mps(
            self.last_waypoint.position.distance_to_point(waypoint.position)
            / (waypoint.tot - last_time).total_seconds()
        )

        return f"{self.units.speed(speed):.0f}"

    def _format_min_fuel(self, min_fuel: Optional[float]) -> str:
        if min_fuel is None:
            return ""

        mass = pounds(min_fuel)
        return f"{math.ceil(self.units.mass(mass) / 100) * 100:.0f}"

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
        omit_min_fuel: bool = False,
        task_line: Optional[str] = None,
        push_line: Optional[str] = None,
        threat_line: Optional[str] = None,
        page_title: str = "Mission Info",
    ) -> None:
        self.flight = flight
        self.bullseye = bullseye
        self.weather = weather
        self.start_time = start_time
        self.dark_kneeboard = dark_kneeboard
        self.theater = theater
        self.atis_by_name = atis_by_name or {}
        # Page heading; the compact deck renames this to "Game Plan" to match its
        # three-page naming (Game Plan / Threats & Targets / Comms & Coordination).
        self.page_title = page_title
        # BLUF (bottom line up front): the few items a pilot needs even if this is
        # the only kneeboard page they read (design §4 -- priority on the page they
        # open to first). Computed by the generator and passed in so the page stays
        # decoupled from the threat/code-word models; any may be None.
        self.task_line = task_line
        self.push_line = push_line
        self.threat_line = threat_line
        # De-duplication (design §4): drop the weather block when the recon Departure
        # page already carries it, and the Min-fuel column when the Fuel Ladder page
        # owns the fuel ladder. The Friendly Packages list moved to its own page.
        self.omit_weather = omit_weather
        self.omit_min_fuel = omit_min_fuel
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
        writer.title(f"{self.flight.callsign} {self.page_title}{custom_name_title}")

        # BLUF block: task/target/TOT, push + event code words, the single most
        # lethal live threat, and bullseye -- the priority items on the page players
        # open to first (design §4). Kept tight so the flight-plan table still fits
        # on this same page. Each line is optional; bullseye is always present.
        bluf = [
            line for line in (self.task_line, self.push_line, self.threat_line) if line
        ]
        bluf.append(f"BULLSEYE {self.bullseye.position.latlng().format_dms()}")
        writer.heading("BLUF")
        writer.rule()
        for line in bluf:
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
            f"{self.flight.flight_type.value})"
        )
        writer.rule()

        units = self.flight.aircraft_type.kneeboard_units

        flight_plan_builder = FlightPlanBuilder(
            self.start_time, units, include_min_fuel=not self.omit_min_fuel
        )
        for num, waypoint in enumerate(self.flight.waypoints):
            flight_plan_builder.add_waypoint(num, waypoint)

        headers = ["#", "Action", "Alt", "Dist", "Brg", "GSPD", "Time", "Departure"]
        uom_row = [
            "",
            "",
            units.distance_short_uom,
            units.distance_long_uom,
            "T",
            units.speed_uom,
            "",
            "",
        ]
        if not self.omit_min_fuel:
            headers.append("Min fuel")
            uom_row.append(units.mass_uom)

        writer.table(
            flight_plan_builder.build() + [uom_row],
            headers=headers,
            font=self.flight_plan_font,
        )

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

    def _departure_elevation_m(self) -> Optional[float]:
        """DCS-mesh field elevation (m) of the departure field, or None.

        Looks up the departure airport via the theater's controlpoints (matched
        by airfield name) and reads ``elevation_m`` from
        ``resources/airport_imagery/<terrain>.json``. None when no theater, no
        matching control point, or no elevation shipped.
        """
        if self.theater is None:
            return None
        dep = self.flight.departure
        airport = None
        for cp in self.theater.controlpoints:
            dcs_ap = getattr(cp, "dcs_airport", None)
            if dcs_ap is None:
                continue
            if cp.full_name == dep.airfield_name or dcs_ap.name == dep.airfield_name:
                airport = dcs_ap
                break
        if airport is None:
            return None
        # Shared helper with the recon ATIS pipeline so both consumers walk
        # the same lookup chain (load â†’ for_airport â†’ elevation_m). When
        # this lookup changes (alt source for elevation, new key for
        # matching airports), both surfaces update together.
        return _airport_imagery.field_elevation_for_airport(
            self.theater.terrain, airport
        )

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

    def render_section(self, writer: KneeboardPageWriter) -> None:
        """Draw heading + two-column table at the cursor (no title; for composite use).

        Rows that don't fit below the cursor are dropped rather than paginated, so the
        compact deck stays within its page budget.
        """
        writer.heading(self.HEADING)
        writer.rule()
        font = self._font()
        single_capacity = writer.remaining_table_rows(font, bool(self.HEADERS))
        if len(self.rows) <= single_capacity:
            writer.table_paginated(self.rows, headers=self.HEADERS, font=font)
        else:
            writer.table_two_column_paginated(
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

    def _render(
        self,
        writer: KneeboardPageWriter,
        *,
        draw_title: bool = True,
        fill: bool = True,
        include_airfield_dir: bool = True,
    ) -> List[List[str]]:
        """Draw the Support Info page; return airfield rows that overflowed.

        ``draw_title`` / ``fill`` / ``include_airfield_dir`` let the compact deck's
        Comms & Coordination page reuse this without the page title, with tight
        section spacing (so code words + brevity + packages fit below), and without
        the friendly-field directory (the relevant fields are on the Game Plan page).
        """
        if draw_title:
            if self.flight.custom_name:
                custom_name_title = ' ("{}")'.format(self.flight.custom_name)
            else:
                custom_name_title = ""
            writer.title(f"{self.flight.callsign} Support Info{custom_name_title}")

        # Package FREQ / TOT line, above the boxed section tables.
        package = self.flight.package
        custom = f' "{package.custom_name}"' if package.custom_name else ""
        freq = self.format_frequency(package.frequency).replace("\n", " - ")
        tot = self._format_time(package.time_over_target)
        writer.text(f"  FREQ: {freq}    TOT: {tot}", font=writer.table_font)

        # Build each support section as (title, rows, headers); they render as
        # bordered boxes with header bars (the professional-campaign look) and
        # are spaced to fill the page rather than leaving the bottom half blank.
        comm_ladder = []
        for comm in self.comms:
            comm_ladder.append(
                [
                    comm.name,
                    str(self.flight.flight_type),
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
                    str(f.flight_type),
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
            for heading, cells, hdr in sections:
                w.text(heading, font=w.heading_font)
                w.rule()
                w.table(cells, headers=hdr)
                w.vspace(section_gap)

        # When there's no airfield directory below, distribute the leftover
        # vertical space as even gaps so the tables breathe down the page
        # (light underline-rule headings, no boxes). With a directory present we
        # use a small fixed gap and let the directory fill the rest (it paginates).
        # In compact mode (``fill=False``) keep a small fixed gap so code words +
        # brevity + packages fit below on the same page.
        gap = 12
        if fill and not self.airfield_rows:
            probe = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
            probe.y = writer.y
            render_sections(probe, 0)
            leftover = (writer.image_size[1] - writer.page_margin) - probe.y
            gap = int(max(12, min(90, leftover // max(1, len(sections)))))

        render_sections(writer, gap)

        # Airfield Directory (friendly fields: ATC / ATIS / TACAN / I(C)LS / RWY).
        # Rows that don't fit spill onto a continuation page (see paginate()).
        overflow: List[List[str]] = []
        if include_airfield_dir and self.airfield_rows:
            writer.text(self.AIRFIELD_HEADING, font=writer.heading_font)
            writer.rule()
            overflow = writer.table_paginated(
                self.airfield_rows,
                headers=self.AIRFIELD_HEADERS,
            )
        return overflow

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

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self.render_into(writer)
        writer.write(path)

    def render_into(
        self, writer: KneeboardPageWriter, *, draw_title: bool = True
    ) -> None:
        task = "DEAD" if self.flight.flight_type == FlightType.DEAD else "SEAD"
        if draw_title:
            if self.flight.custom_name:
                custom_name_title = ' ("{}")'.format(self.flight.custom_name)
            else:
                custom_name_title = ""
            writer.title(
                f"{self.flight.callsign} {task} Target Info{custom_name_title}"
            )

        # Larger-than-default fonts: this page carries only a few rows, so bigger type
        # fills the page and reads better in the cockpit. The exact-coords table keeps
        # the default font (its long coordinate strings need the narrower glyphs).
        body_font = ImageFont.truetype(
            "courbd.ttf", 20, layout_engine=ImageFont.Layout.BASIC
        )
        area_font = ImageFont.truetype(
            "courbd.ttf", 24, layout_engine=ImageFont.Layout.BASIC
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
            # steerpoint if one maps. The table then just lists the site's emitters
            # and their ALIC codes.
            cue = self._bullseye_cue_for(self.flight.package.target.position)
            stpt = self._target_area_stpt()
            area = f"{task} target area"
            if stpt is not None:
                area += f" — STPT {stpt}"
            writer.heading(f"{area} — {cue}")
            writer.table(
                [
                    [self._unit_description(t), self.alic_for(t)]
                    for t in self.target_units
                ],
                headers=["Description", "ALIC"],
                font=area_font,
            )
        else:
            # Exact (SEAD) view: per-emitter steerpoint + precise coordinates.
            target_numbers = self._target_point_numbers()
            writer.table(
                [
                    self.target_info_row(
                        t, target_numbers[i] if i < len(target_numbers) else None
                    )
                    for i, t in enumerate(self.target_units)
                ],
                headers=["STPT", "Description", "ALIC", "Location"],
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

    def render_into(
        self, writer: KneeboardPageWriter, *, draw_title: bool = True
    ) -> None:
        if draw_title:
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

    def render_into(
        self,
        writer: KneeboardPageWriter,
        *,
        draw_title: bool = True,
        fill: bool = True,
    ) -> None:
        custom = f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
        if draw_title:
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

        if not fill:
            # Composite (compact deck) use: fixed modest gap, no fill-distribute, so
            # the brief sits below any threat cards without claiming the whole page.
            render(writer, 16)
            return

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
    """Player briefing for a SCAR (loiter-and-task) flight.

    Guidance for the loiter rework: hold over the kill box, find + ID the real
    target among look-alikes (mis-ID costs budget), and let the on-scene controller
    ("MAGIC") talk you on and designate. The MOOSE scar plugin drives the live cues,
    so this page is guidance, not exact values.
    """

    def __init__(
        self,
        flight: FlightData,
        dark_kneeboard: bool,
        tasking: Optional[ScarTasking] = None,
    ) -> None:
        self.flight = flight
        self.dark_kneeboard = dark_kneeboard
        self.tasking = tasking

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self.render_into(writer)
        writer.write(path)

    def render_into(
        self, writer: KneeboardPageWriter, *, draw_title: bool = True
    ) -> None:
        if draw_title:
            custom = (
                f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
            )
            writer.title(f"{self.flight.callsign} SCAR{custom}")

        writer.heading("TASK")
        writer.text(
            "Hold over the kill box and service the real enemy armor the on-scene "
            "controller (MAGIC) designates. Kills count automatically — it's a real "
            "campaign target — so there's no scoring to chase.",
            wrap=True,
        )

        # The full HVT signature for this tasking, so the pilot can win the ID puzzle
        # off the kneeboard rather than the (now group-targeted) MAGIC call. No exact
        # target coords by design — finding it in the box is the task.
        signature = self.tasking.signature_text if self.tasking else ""
        if signature:
            writer.heading("TARGET SIGNATURE")
            writer.text(
                f"Full signature: {signature}.\n"
                "DECOYS in the box carry a PARTIAL match (one element dropped) — match "
                "ALL of it before you shoot; hitting a decoy costs your side budget "
                "(mis-ID).",
                wrap=True,
            )

        writer.heading("FIND + ID")
        writer.text(
            "- The box holds the real target mixed with look-alike DECOYS + clutter. "
            "Match the FULL signature; hitting a decoy costs your side budget (mis-ID).\n"
            "- On station MAGIC pops GREEN smoke on the box and talks you on. Work the "
            "ID first; if you're stuck, MAGIC escalates to RED smoke on the real target "
            "after ~2 min and clears you hot.",
            wrap=True,
        )

        writer.heading("DESIGNATION")
        writer.text(
            "- GREEN smoke = the box. RED smoke = the confirmed target, cleared hot.\n"
            "- If a C-130 KING is on station it lases the target (laser code 1688 + IR "
            "pointer) for LGBs / guided Mavericks. No King up = smoke + your own visual.\n"
            '- F10 -> "MAGIC: say again SCAR target" re-pops the smoke if it burns out '
            "(and re-calls the laser code).",
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


def _site_reference(tgo: TheaterGroundObject) -> Optional[ThreatReference]:
    """Curated reference for a site, matched on any of its units' type ids."""
    for unit in tgo.units:
        ref = reference_for(unit.type.id)
        if ref is not None:
            return ref
    return None


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
        dominant = _greatest_alive_threat(tgo)
        name = dominant[0] if dominant else (band or "AD site")
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
            site.ref = _site_reference(tgo)

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
            intro += (
                f" {self.unidentified} site(s) still unidentified — "
                "fly TARPS recon to ID."
            )
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
    def _cues_text(cues: List[str], limit: int) -> str:
        shown = ", ".join(cues[:limit])
        if len(cues) > limit:
            shown += f", +{len(cues) - limit}"
        return shown

    def _render_card(self, writer: KneeboardPageWriter, card: ThreatCard) -> None:
        body = self._body_font()
        writer.text(card.system, font=self._heading_font())
        writer.rule(gap_below=4)
        if card.identified:
            writer.text(
                f"Guidance: {card.guidance}    Ceiling: {card.ceiling}", font=body
            )
            writer.text(
                f"MEZ: {card.mez_nm} nm   Detect: {card.detect_nm} nm   "
                f"HARM: {card.harm}   Band: {card.band}",
                font=body,
            )
            sites = f"Sites: {card.live} live"
            if card.dead:
                sites += f" / {card.dead} dead"
            writer.text(f"{sites}   BE {self._cues_text(card.cues, 6)}", font=body)
            if card.defeat:
                writer.text(f"DEFEAT: {card.defeat}", font=body, wrap=True)
        else:
            writer.text(
                f"{card.live} site(s) — fly TARPS to ID.   "
                f"BE {self._cues_text(card.cues, 8)}",
                font=body,
                wrap=True,
            )
        writer.vspace(12)

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


class BrevityCard(KneeboardPage):
    """Comms & Brevity card: the side's mission code words + task-filtered brevity.

    Two layers: the **mission-wide code-word table** (a push word per task plus the
    event words, shared by the whole side — `game/ato/codewords.py`), with the
    flight's own task row marked, so a call ("Red Kite") tells everyone SEAD is
    pushing; and a short **brevity** crib filtered to the flight's task
    (`game/data/brevity_reference.py`). Human comms aids only; nothing scripts off them.
    """

    def __init__(self, flight: FlightData, dark_kneeboard: bool) -> None:
        self.flight = flight
        self.dark_kneeboard = dark_kneeboard

    @staticmethod
    def _table_font() -> ImageFont.FreeTypeFont:
        # Larger fonts than the defaults: this card is sparse, so a bigger type fills
        # the page and reads better at a glance in the cockpit.
        return ImageFont.truetype(
            "courbd.ttf", 24, layout_engine=ImageFont.Layout.BASIC
        )

    @staticmethod
    def _brevity_font() -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(
            "courbd.ttf", 20, layout_engine=ImageFont.Layout.BASIC
        )

    def render_code_words(self, writer: KneeboardPageWriter) -> None:
        """Draw the code-word + event tables (no page title; for composite reuse)."""
        table_font = self._table_font()
        coalition = self.flight.squadron.coalition
        code_words = coalition.code_words
        own = push_category_for(self.flight.flight_type)
        present = present_categories(
            p.primary_task for p in coalition.ato.packages if p.primary_task is not None
        )
        if own is not None:
            present = present | {own}

        writer.heading(f"Code Words — {code_words.theme}")
        writer.rule()
        push_rows = []
        for category in PushCategory:
            if category not in present:
                continue
            word = code_words.push[category]
            if category is own:
                word = f"{word}  (you)"
            push_rows.append([category.value, word])
        writer.table(push_rows, headers=["Task push", "Word"], font=table_font)

        event_rows = [["SUCCESS", code_words.success], ["ABORT", code_words.abort]]
        if PushCategory.EW in present:
            event_rows.append(["STOP JAM", code_words.stop_jam])
        writer.table(event_rows, headers=["Event", "Word"], font=table_font)
        writer.text(
            "Call over SRS. Your task's push word is marked (you); a push call tells "
            "the whole package who's committing. SUCCESS on target down, ABORT to "
            "knock it off.",
            wrap=True,
        )

    def render_brevity(self, writer: KneeboardPageWriter) -> None:
        """Draw the task-filtered brevity crib (no page title; for composite reuse)."""
        label, lines = brevity_for(self.flight.flight_type)
        writer.heading(f"Brevity — {label}")
        writer.rule()
        writer.table(
            [[term, meaning] for term, meaning in lines],
            headers=["Call", "Meaning"],
            font=self._brevity_font(),
        )

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        custom = f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
        writer.title(f"{self.flight.callsign} Comms & Brevity{custom}")
        self.render_code_words(writer)
        writer.vspace(12)
        self.render_brevity(writer)
        writer.write(path)


class FuelLadderCard(KneeboardPage):
    """Fuel ladder: planned fuel remaining vs. minimum required at each steerpoint.

    The flight-plan page already carries the *minimum* fuel (bingo-at-waypoint); this
    focused card adds the **planned remaining** (estimated forward from the starting
    load over the per-leg burn model, `FlightWaypoint.fuel_planned`) and the **margin**
    between them — the Red Flag-style fuel ladder. The burn model is approximate, so
    treat the numbers as planning figures.
    """

    DESC_MAX_LEN = 24

    def __init__(self, flight: FlightData, dark_kneeboard: bool) -> None:
        self.flight = flight
        self.dark_kneeboard = dark_kneeboard

    @staticmethod
    def _fmt(units: UnitSystem, lbs: Optional[float]) -> str:
        return "-" if lbs is None else f"{units.mass(pounds(lbs)):.0f}"

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        custom = f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
        writer.title(f"{self.flight.callsign} Fuel Ladder{custom}")
        self.render_into(writer, draw_heading=False)
        writer.write(path)

    def render_into(
        self, writer: KneeboardPageWriter, *, draw_heading: bool = True
    ) -> None:
        """Draw the fuel ladder + Bingo/Joker (no page title; for composite reuse)."""
        units = self.flight.aircraft_type.kneeboard_units
        # Larger-than-default table font: the ladder is short, so a bigger type fills
        # the page and is easier to read in the cockpit.
        ladder_font = ImageFont.truetype(
            "courbd.ttf", 22, layout_engine=ImageFont.Layout.BASIC
        )
        bingo_font = ImageFont.truetype(
            "courbd.ttf", 24, layout_engine=ImageFont.Layout.BASIC
        )
        if draw_heading:
            writer.heading("Fuel Ladder")
            writer.rule()
        writer.text(
            f"Planned fuel remaining vs. minimum to RTB at each steerpoint, in "
            f"{units.mass_uom}. Margin = Plan - Min; a negative margin means you can't "
            "make it home as planned -- tank or divert.",
            wrap=True,
        )

        rows: List[List[str]] = []
        for number, waypoint in enumerate(self.flight.waypoints):
            if waypoint.fuel_planned is None and waypoint.min_fuel is None:
                continue
            margin: Optional[float] = None
            if waypoint.fuel_planned is not None and waypoint.min_fuel is not None:
                margin = waypoint.fuel_planned - waypoint.min_fuel
            rows.append(
                [
                    str(number),
                    KneeboardPageWriter.wrap_line(
                        waypoint.display_name, self.DESC_MAX_LEN
                    ),
                    self._fmt(units, waypoint.fuel_planned),
                    self._fmt(units, waypoint.min_fuel),
                    self._fmt(units, margin),
                ]
            )

        if rows:
            writer.table(
                rows,
                headers=["#", "Action", "Plan", "Min", "Margin"],
                font=ladder_font,
            )
        else:
            writer.text("No fuel estimate available for this aircraft.")

        if self.flight.bingo_fuel and self.flight.joker_fuel:
            writer.vspace(10)
            writer.table(
                [
                    [
                        self._fmt(units, self.flight.bingo_fuel),
                        self._fmt(units, self.flight.joker_fuel),
                    ]
                ],
                headers=["Bingo", "Joker"],
                font=bingo_font,
            )


def _draw_section_if_fits(
    writer: KneeboardPageWriter,
    dark: bool,
    render_fn: Callable[[KneeboardPageWriter], None],
    *,
    gap: int = 14,
) -> None:
    """Draw a section (preceded by a gap) only if it fits below the cursor.

    Keeps the compact deck within its page budget: a section that would overflow the
    page is dropped rather than spilled onto an extra page. Shared by the composite
    Comms & Coordination and Flex Reference pages.
    """
    probe = KneeboardPageWriter(dark_theme=dark)
    probe.x, probe.y = writer.x, writer.y
    probe.vspace(gap)
    render_fn(probe)
    if probe.y <= (writer.image_size[1] - writer.page_margin):
        writer.vspace(gap)
        render_fn(writer)


class CombatIntelPage(KneeboardPage):
    """Compact-deck page 2: the flight's target info over the enemy air-defense cards.

    Composes the per-task target page (SEAD/DEAD/Strike ALIC + coords, or the
    SCAR / Combat SAR brief) with the Threat Intel cards under one title, so the player
    gets "what am I hitting / what's shooting at me" on a single page. The target is
    drawn first (it's the flight's own tasking and short); the threat cards then fill
    the remaining space, packing as many as fit. Part of the compact 3-page kneeboard
    (``settings.compact_kneeboard``).
    """

    def __init__(
        self,
        flight: FlightData,
        threat_page: Optional[ThreatIntelBriefPage],
        target_page: Optional[KneeboardPage],
        dark_kneeboard: bool,
    ) -> None:
        self.flight = flight
        self.threat_page = threat_page
        self.target_page = target_page
        self.dark_kneeboard = dark_kneeboard

    def _title(self) -> str:
        custom = f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
        return f"{self.flight.callsign} Threats & Targets{custom}"

    def _render_target_into(self, writer: KneeboardPageWriter) -> None:
        page = self.target_page
        if isinstance(page, CombatSarTaskPage):
            page.render_into(writer, draw_title=False, fill=False)
        elif isinstance(page, (SeadTaskPage, StrikeTaskPage, ScarTaskPage)):
            page.render_into(writer, draw_title=False)

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        writer.title(self._title())
        if self.target_page is not None:
            self._render_target_into(writer)
            writer.vspace(14)
        if self.threat_page is not None:
            writer.heading("Enemy Air Defenses")
            writer.rule()
            writer.text(self.threat_page._intro(), wrap=True)
            writer.vspace(4)
            self.threat_page.render_cards(writer)
        writer.write(path)


class CommsCoordPage(KneeboardPage):
    """Compact-deck page 3: comms + coordination, composed under one title.

    The support sections (package comm ladder, AWACS, tankers, JTAC) over the code
    words + brevity crib and the friendly-package list. Lower-priority sections are
    only drawn if they fit below the cursor, so the page never spills to a fourth.
    Part of the compact 3-page kneeboard (``settings.compact_kneeboard``).
    """

    def __init__(
        self,
        flight: FlightData,
        support_page: SupportPage,
        brevity_card: Optional[BrevityCard],
        packages_page: Optional[FriendlyPackagesPage],
        dark_kneeboard: bool,
    ) -> None:
        self.flight = flight
        self.support_page = support_page
        self.brevity_card = brevity_card
        self.packages_page = packages_page
        self.dark_kneeboard = dark_kneeboard

    def _title(self) -> str:
        custom = f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
        return f"{self.flight.callsign} Comms & Coordination{custom}"

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        writer.title(self._title())
        dark = self.dark_kneeboard
        # Support sections (no own title, tight spacing, no field directory).
        self.support_page._render(
            writer, draw_title=False, fill=False, include_airfield_dir=False
        )
        if self.brevity_card is not None:
            _draw_section_if_fits(writer, dark, self.brevity_card.render_code_words)
            _draw_section_if_fits(writer, dark, self.brevity_card.render_brevity)
        if self.packages_page is not None:
            _draw_section_if_fits(writer, dark, self.packages_page.render_section)
        writer.write(path)


class FlexReferencePage(KneeboardPage):
    """Compact-deck page 4 (text mode): the Fuel Ladder over the friendly-package list.

    The flex page that appears when recon imagery isn't generated. It restores the
    Fuel Ladder (planned vs. minimum + margin) the 3-page deck would otherwise drop and
    gives the friendly-package list a full page (decluttering Comms & Coordination).
    Sections draw only if they fit. Part of the compact deck (settings.compact_kneeboard).
    """

    def __init__(
        self,
        flight: FlightData,
        fuel_card: Optional["FuelLadderCard"],
        packages_page: Optional[FriendlyPackagesPage],
        dark_kneeboard: bool,
    ) -> None:
        self.flight = flight
        self.fuel_card = fuel_card
        self.packages_page = packages_page
        self.dark_kneeboard = dark_kneeboard

    def _title(self) -> str:
        parts = []
        if self.fuel_card is not None:
            parts.append("Fuel")
        if self.packages_page is not None:
            parts.append("Packages")
        name = " & ".join(parts) if parts else "Reference"
        custom = f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
        return f"{self.flight.callsign} {name}{custom}"

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        writer.title(self._title())
        dark = self.dark_kneeboard
        if self.fuel_card is not None:
            self.fuel_card.render_into(writer, draw_heading=True)
        if self.packages_page is not None:
            _draw_section_if_fits(writer, dark, self.packages_page.render_section)
        writer.write(path)


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
        self,
        mission: Mission,
        game: "Game",
        scar_taskings: Optional[List[ScarTasking]] = None,
    ) -> None:
        super().__init__(mission, game)
        self.dark_kneeboard = self.game.settings.generate_dark_kneeboard and (
            self.mission.start_time.hour > 19 or self.mission.start_time.hour < 7
        )
        # SCAR taskings (one per SCAR target), so a SCAR flight's kneeboard can carry
        # its own target signature instead of relying on the coalition-wide call.
        self.scar_taskings: List[ScarTasking] = scar_taskings or []

    def _scar_tasking_for(self, flight: FlightData) -> Optional[ScarTasking]:
        """The SCAR tasking built for this flight's package target, if any. Matched by
        object identity (same generation pass; see ScarTasking.target_id)."""
        target = getattr(flight.package, "target", None)
        if target is None:
            return None
        target_id = id(target)
        for tasking in self.scar_taskings:
            if tasking.target_id == target_id:
                return tasking
        return None

    def generate(self) -> None:
        """Generates a kneeboard per client flight."""
        temp_dir = Path("kneeboards")
        temp_dir.mkdir(exist_ok=True)
        for aircraft, pages in self.pages_by_airframe().items():
            aircraft_dir = temp_dir / aircraft.dcs_unit_type.id
            aircraft_dir.mkdir(exist_ok=True)
            # Pages may expand into continuation pages when a folded list
            # overflows a single image, so flatten before numbering the files.
            concrete_pages = [
                concrete for page in pages for concrete in page.paginate()
            ]
            for idx, page in enumerate(concrete_pages):
                page_path = aircraft_dir / f"page{idx:02}.png"
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

    def pages_by_airframe(self) -> Dict[AircraftType, List[KneeboardPage]]:
        """Returns a list of kneeboard pages per airframe in the mission.

        Only client flights will be included, but because DCS does not support
        group-specific kneeboard pages, flights (possibly from opposing sides)
        will be able to see the kneeboards of all aircraft of the same type.

        Returns:
            A dict mapping aircraft types to the list of kneeboard pages for
            that aircraft.
        """
        all_flights: Dict[AircraftType, List[KneeboardPage]] = defaultdict(list)
        for flight in self.flights:
            if not flight.client_units:
                continue
            package_flights = [
                f
                for f in self.flights
                if f.package is flight.package and f is not flight
            ]
            all_flights[flight.aircraft_type].extend(
                self.generate_flight_kneeboard(flight, package_flights)
            )
        return all_flights

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
            return ScarTaskPage(
                flight, self.dark_kneeboard, self._scar_tasking_for(flight)
            )
        return None

    def _compact_kneeboard_pages(
        self,
        flight: FlightData,
        package_flights: List[FlightData],
        zoned_time: datetime.datetime,
        airfield_rows: List[List[str]],
        threat_cards: List[ThreatCard],
        unidentified: int,
        task_line: Optional[str],
        push_line: Optional[str],
        threat_line: Optional[str],
    ) -> List[KneeboardPage]:
        """Build the compact deck: at most four pages (settings.compact_kneeboard).

        Page 1 Game Plan (BLUF + route + fuel + fields + weather), page 2 Threats &
        Targets (target ALIC over the enemy AD cards; skipped when there's neither),
        page 3 Comms & Coordination (radios + AWACS/tanker/JTAC + code words + brevity
        + friendly packages). Page 4 is an adaptive flex page: when target-recon imagery
        is enabled it carries the recon target photo, otherwise a text page with the
        Fuel Ladder + the full friendly-package list (which then drops off page 3 to
        declutter it). Theater/package map images are never generated in this mode.
        """
        dark = self.dark_kneeboard
        pages: List[KneeboardPage] = []

        # Page 1 — Game Plan. Weather + the per-waypoint Min (bingo) column stay on
        # this page in compact mode (the recon Departure / Fuel Ladder pages that would
        # otherwise own them are not generated).
        pages.append(
            BriefingPage(
                flight,
                self.game.coalition_for(flight.friendly).bullseye,
                self.game.conditions.weather,
                zoned_time,
                dark,
                atis_by_name=self.atis_by_name,
                theater=self.game.theater,
                omit_weather=False,
                omit_min_fuel=False,
                task_line=task_line,
                push_line=push_line,
                threat_line=threat_line,
                page_title="Game Plan",
            )
        )

        # Page 2 — Threats & Targets. Skipped entirely when the flight has neither a
        # target page nor any enemy air defenses to brief (e.g. a BARCAP over friendly
        # territory), so such flights get a 2-page deck.
        threat_page = (
            ThreatIntelBriefPage(flight, threat_cards, unidentified, dark)
            if threat_cards
            else None
        )
        target_page = self.generate_task_page(flight)
        if threat_page is not None or target_page is not None:
            pages.append(CombatIntelPage(flight, threat_page, target_page, dark))

        # Page 4 (decided first, so page 3 knows whether it keeps the package list).
        # Recon imagery wins the flex slot when enabled; otherwise a text flex page
        # carries the Fuel Ladder + the full friendly-package list.
        packages_page: Optional[FriendlyPackagesPage] = None
        if self.game.settings.generate_all_packages_kneeboard:
            package_rows = self.build_all_packages_rows(flight)
            if package_rows:
                packages_page = FriendlyPackagesPage(flight, package_rows, dark)

        recon_detail = self._recon_detail_page(flight)
        fuel_card = (
            FuelLadderCard(flight, dark)
            if self.game.settings.generate_fuel_ladder_kneeboard
            else None
        )
        page4: Optional[KneeboardPage] = None
        packages_on_comms = packages_page
        if recon_detail is not None:
            # Recon target photo takes the flex slot; the package list stays on page 3.
            page4 = recon_detail
        elif fuel_card is not None or packages_page is not None:
            # Text flex page: Fuel Ladder + the full package list (moved off page 3).
            page4 = FlexReferencePage(flight, fuel_card, packages_page, dark)
            packages_on_comms = None

        # Page 3 — Comms & Coordination (keeps the package list only when page 4 didn't
        # take it onto the text flex page).
        support_page = SupportPage(
            flight,
            package_flights,
            self.comms,
            self.awacs,
            self.tankers,
            self.jtacs,
            zoned_time,
            dark,
            airfield_rows=airfield_rows,
        )
        brevity_card = (
            BrevityCard(flight, dark)
            if self.game.settings.enable_package_code_words
            else None
        )
        pages.append(
            CommsCoordPage(flight, support_page, brevity_card, packages_on_comms, dark)
        )

        if page4 is not None:
            pages.append(page4)

        return pages

    def _recon_detail_page(self, flight: FlightData) -> Optional[KneeboardPage]:
        """The single recon target-imagery page for this flight, or None.

        Mirrors the target-detail branch of ``generate_recon_pages`` (the satellite
        photo of the target: ground object, airbase, or front line) so the compact
        deck can carry just that page as its flex slot. Skips the Departure + Overview
        pages the full recon deck would also emit. None when target recon is disabled,
        the flight isn't an air-to-ground recon type, or it has no eligible target.
        """
        if not self.game.settings.generate_target_recon_kneeboard:
            return None
        if flight.flight_type not in _FLIGHT_TYPES_WITH_RECON:
            return None
        target = getattr(flight.package, "target", None)
        if target is None:
            return None
        if isinstance(target, ControlPoint):
            if getattr(target, "dcs_airport", None) is not None:
                return AirbaseReconPage(
                    flight=flight, game=self.game, dark=self.dark_kneeboard
                )
            return None
        if isinstance(target, FrontLine):
            return FrontLineDetailPage(
                flight=flight, game=self.game, dark=self.dark_kneeboard
            )
        if isinstance(target, TheaterGroundObject):
            return DetailReconPage(
                flight=flight, game=self.game, dark=self.dark_kneeboard
            )
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
        # The Fuel Ladder page carries the per-waypoint bingo (Min) fuel + planned + margin.
        omit_min_fuel = self.game.settings.generate_fuel_ladder_kneeboard

        # Threat cards are computed once and feed both the always-on BLUF top-threat
        # line on the Mission Info page and (when enabled) the dedicated Threat Intel
        # Brief. Computed unconditionally so the BLUF can warn about the single most
        # lethal system even when the full brief page is off.
        threat_cards, unidentified = build_threat_intel_cards(self.game, flight)
        task_line, push_line, threat_line = self._bluf_lines(flight, threat_cards)

        # Compact 3-page deck (default): fold the optional content into at most three
        # text pages and skip the image pages. See settings.compact_kneeboard.
        if self.game.settings.compact_kneeboard:
            return self._compact_kneeboard_pages(
                flight,
                package_flights,
                zoned_time,
                airfield_rows,
                threat_cards,
                unidentified,
                task_line,
                push_line,
                threat_line,
            )

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
                omit_min_fuel=omit_min_fuel,
                task_line=task_line,
                push_line=push_line,
                threat_line=threat_line,
            ),
            SupportPage(
                flight,
                package_flights,
                self.comms,
                self.awacs,
                self.tankers,
                self.jtacs,
                zoned_time,
                self.dark_kneeboard,
                airfield_rows=airfield_rows,
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

        # Comms & Brevity card: package code words + task-filtered brevity, gated by
        # the feature toggle. The code words are also surfaced to planners (ATO package
        # tooltip + join-waypoint echo); this is the in-cockpit copy.
        if self.game.settings.enable_package_code_words:
            pages.append(BrevityCard(flight, self.dark_kneeboard))

        # Fuel ladder: planned remaining vs. minimum required per steerpoint (gated).
        if self.game.settings.generate_fuel_ladder_kneeboard:
            pages.append(FuelLadderCard(flight, self.dark_kneeboard))

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
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Compute the BLUF lines for the Mission Info page (priority on page one).

        Returns ``(task_line, push_line, threat_line)``; any may be None. The task
        line is always present (task, plus target/TOT when applicable); the push line
        is gated on the code-words feature; the threat line is the single most lethal
        live, identified system from the already-built threat cards.
        """
        # Task / target / TOT.
        parts = [flight.flight_type.value]
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

        # Push + event code words (gated by the feature toggle).
        push_line: Optional[str] = None
        if self.game.settings.enable_package_code_words:
            code_words = self.game.coalition_for(flight.friendly).code_words
            bits: List[str] = []
            push = code_words.push_for(flight.flight_type)
            if push:
                bits.append(f"PUSH {push}")
            bits.append(f"SUCCESS {code_words.success}")
            bits.append(f"ABORT {code_words.abort}")
            push_line = "   ".join(bits)

        # Single most lethal live, identified threat (cards are sorted lethal-first).
        threat_line: Optional[str] = None
        for card in threat_cards:
            if card.identified and card.live:
                defeat = card.defeat or card.guidance
                threat_line = f"TOP THREAT  {card.system} — MEZ {card.mez_nm} nm"
                if defeat and defeat != "—":
                    threat_line += f" — {defeat}"
                break

        return task_line, push_line, threat_line

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
