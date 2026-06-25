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
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, TYPE_CHECKING, Tuple

from PIL import Image, ImageDraw, ImageFont
from dcs.mapping import Point
from dcs.mission import Mission
from dcs.planes import F_15ESE
from suntime import Sun, SunTimeException  # type: ignore
from tabulate import tabulate

from game.ato.flighttype import FlightType
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.data.alic import AlicCodes
from game.dcs.aircrafttype import AircraftType
from game.radio.radios import RadioFrequency
from game.runways import RunwayData
from game.settings.settings import TargetIntelPrecision
from game.theater import TheaterGroundObject, TheaterUnit
from game.theater.bullseye import Bullseye
from game.theater.controlpoint import Airfield
from game.utils import Distance, UnitSystem, inches_hg, meters, mps, pounds
from game.weather.weather import Weather
from .aircraft.flightdata import CombatSarKingBeacon, FlightData
from .briefinggenerator import CommInfo, JtacInfo, MissionInfoGenerator
from .kneeboard_page import KneeboardPage
from .kneeboard_recon import airport_imagery as _airport_imagery
from .kneeboard_recon import generate_recon_pages
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

    def __init__(self, start_time: datetime.datetime, units: UnitSystem) -> None:
        self.start_time = start_time
        self.rows: List[List[str]] = []
        self.target_points: List[NumberedWaypoint] = []
        self.last_waypoint: Optional[FlightWaypoint] = None
        self.units = units

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

        self.rows.append(
            [
                f"{first_waypoint_num}-{last_waypoint_num}",
                "Target points",
                "0",
                self._waypoint_distance(self.target_points[0].waypoint),
                self._ground_speed(self.target_points[0].waypoint),
                self._format_time(self.target_points[0].waypoint.tot),
                self._format_time(self.target_points[0].waypoint.departure_time),
                self._format_min_fuel(self.target_points[0].waypoint.min_fuel),
            ]
        )
        self.last_waypoint = self.target_points[-1].waypoint

    def add_waypoint_row(self, waypoint: NumberedWaypoint) -> None:
        self.rows.append(
            [
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
                self._format_min_fuel(waypoint.waypoint.min_fuel),
            ]
        )

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
        package_rows: Optional[List[List[str]]] = None,
    ) -> None:
        self.flight = flight
        self.bullseye = bullseye
        self.weather = weather
        self.start_time = start_time
        self.dark_kneeboard = dark_kneeboard
        self.theater = theater
        self.atis_by_name = atis_by_name or {}
        self.package_rows = package_rows or []
        self.flight_plan_font = ImageFont.truetype(
            "courbd.ttf",
            16,
            layout_engine=ImageFont.Layout.BASIC,
        )

    #: Folded "Friendly Packages" table presentation, shared by the inline
    #: render and any continuation page that catches its overflow.
    PACKAGES_HEADING = "Friendly Packages"
    PACKAGES_HEADERS = ["Task", "Target", "TOT / Window"]
    PACKAGES_FONT_SIZE = 18

    def _packages_title(self) -> str:
        custom = f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
        return f"{self.flight.callsign} Friendly Packages{custom}"

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self._render(writer)
        writer.write(path)

    def paginate(self) -> List[KneeboardPage]:
        # Replay the layout to discover how many folded package rows spilled
        # past the bottom edge, then carry the remainder onto continuation
        # page(s). The probe image is discarded; write() re-renders.
        probe = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        overflow = self._render(probe)
        pages: List[KneeboardPage] = [self]
        if overflow:
            pages.extend(
                TableKneeboardPage(
                    self._packages_title(),
                    self.PACKAGES_HEADING,
                    self.PACKAGES_HEADERS,
                    overflow,
                    self.PACKAGES_FONT_SIZE,
                    self.dark_kneeboard,
                    continued=True,
                ).paginate()
            )
        return pages

    def _render(self, writer: KneeboardPageWriter) -> List[List[str]]:
        """Draw the Mission Info page; return folded package rows that overflowed."""
        if self.flight.custom_name:
            custom_name_title = ' ("{}")'.format(self.flight.custom_name)
        else:
            custom_name_title = ""
        writer.title(f"{self.flight.callsign} Mission Info{custom_name_title}")

        # TODO: Handle carriers.
        writer.heading("Airfield Info")
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

        units = self.flight.aircraft_type.kneeboard_units

        flight_plan_builder = FlightPlanBuilder(self.start_time, units)
        for num, waypoint in enumerate(self.flight.waypoints):
            flight_plan_builder.add_waypoint(num, waypoint)

        uom_row = [
            [
                "",
                "",
                units.distance_short_uom,
                units.distance_long_uom,
                "T",
                units.speed_uom,
                "",
                "",
                units.mass_uom,
            ]
        ]

        writer.table(
            flight_plan_builder.build() + uom_row,
            headers=[
                "#",
                "Action",
                "Alt",
                "Dist",
                "Brg",
                "GSPD",
                "Time",
                "Departure",
                "Min fuel",
            ],
            font=self.flight_plan_font,
        )

        writer.text(f"Bullseye: {self.bullseye.position.latlng().format_dms()}")

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

        fl = self.flight

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

        # Friendly packages coordination list, at the bottom of the page. Use a
        # smaller font so more packages fit below the flight plan. Rows that
        # don't fit below the flight plan spill onto a continuation page rather
        # than running off the bottom edge (see paginate()).
        overflow: List[List[str]] = []
        if self.package_rows:
            writer.heading(self.PACKAGES_HEADING)
            packages_font = ImageFont.truetype(
                "courbd.ttf",
                self.PACKAGES_FONT_SIZE,
                layout_engine=ImageFont.Layout.BASIC,
            )
            overflow = writer.table_paginated(
                self.package_rows,
                headers=self.PACKAGES_HEADERS,
                font=packages_font,
            )
        return overflow

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

    def _render(self, writer: KneeboardPageWriter) -> List[List[str]]:
        """Draw the Support Info page; return airfield rows that overflowed."""
        if self.flight.custom_name:
            custom_name_title = ' ("{}")'.format(self.flight.custom_name)
        else:
            custom_name_title = ""
        writer.title(f"{self.flight.callsign} Support Info{custom_name_title}")

        # Package Section
        package = self.flight.package
        custom = f' "{package.custom_name}"' if package.custom_name else ""
        writer.heading(f"{package.package_description} Package{custom}")
        freq = self.format_frequency(package.frequency).replace("\n", " - ")
        writer.text(f"  FREQ: {freq}", font=writer.table_font)
        tot = self._format_time(package.time_over_target)
        writer.text(f"  TOT: {tot}", font=writer.table_font)
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

        writer.table(comm_ladder, headers=["Callsign", "Task", "Type", "#A/C", "FREQ"])

        # AEW&C
        writer.heading("AEW&C")
        aewc_ladder = []

        for single_aewc in self.awacs:
            if single_aewc.depature_location is None:
                tot = "-"
                tos = "-"
            else:
                tot = self._format_time(single_aewc.start_time)
                tos = self._format_duration(
                    single_aewc.end_time - single_aewc.start_time
                )

            aewc_ladder.append(
                [
                    str(single_aewc.callsign),
                    self.format_frequency(single_aewc.freq),
                    str(single_aewc.depature_location),
                    "TOT: " + tot + "\n" + "TOS: " + tos,
                ]
            )

        writer.table(
            aewc_ladder,
            headers=["Callsign", "FREQ", "Departure", "TOT / TOS"],
        )

        comm_ladder = []
        writer.heading("Tankers")
        for tanker in self.tankers:
            tot = self._format_time(tanker.start_time)
            tos = self._format_duration(tanker.end_time - tanker.start_time)
            comm_ladder.append(
                [
                    tanker.callsign,
                    KneeboardPageWriter.wrap_line(tanker.variant, 21),
                    str(tanker.tacan) if tanker.tacan else "N/A",
                    self.format_frequency(tanker.freq),
                    "TOT: " + tot + "\n" + "TOS: " + tos,
                ]
            )

        writer.table(
            comm_ladder,
            # Drop the "Task" column (always "Tanker" in this table) and shorten
            # TACAN to TCN (3-char code), so the wider FREQ column (now COMM1 +
            # COMM2) and TOT/TOS no longer run off the page edge.
            headers=["Callsign", "Type", "TCN", "FREQ", "TOT / TOS"],
        )

        writer.heading("JTAC")
        jtacs = []
        for jtac in self.jtacs:
            jtacs.append(
                [
                    jtac.callsign,
                    KneeboardPageWriter.wrap_line(
                        jtac.region,
                        self.JTAC_REGION_MAX_LEN,
                    ),
                    jtac.code,
                    self.format_frequency(jtac.freq),
                ]
            )
        # "Laser" instead of "Laser Code": the code is 4 digits, so the longer
        # header padded the column and pushed the FREQ column off the page.
        writer.table(jtacs, headers=["Callsign", "Region", "Laser", "FREQ"])

        # Airfield Directory (friendly fields: ATC / ATIS / TACAN / I(C)LS / RWY).
        # Rows that don't fit below the support tables spill onto a continuation
        # page rather than running off the bottom edge (see paginate()).
        overflow: List[List[str]] = []
        if self.airfield_rows:
            writer.heading(self.AIRFIELD_HEADING)
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
        if self.flight.custom_name:
            custom_name_title = ' ("{}")'.format(self.flight.custom_name)
        else:
            custom_name_title = ""
        task = "DEAD" if self.flight.flight_type == FlightType.DEAD else "SEAD"
        writer.title(f"{self.flight.callsign} {task} Target Info{custom_name_title}")

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

        writer.write(path)

    def target_info_row(self, unit: TheaterUnit, number: Optional[int]) -> List[str]:
        return [
            "" if number is None else str(number),
            self._unit_description(unit),
            self.alic_for(unit),
            unit.position.latlng().format_dms(include_decimal_seconds=True),
        ]

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

        writer.write(path)

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
        custom = f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
        writer.title(f"{self.flight.callsign} Combat SAR{custom}")

        writer.heading("ROLE")
        if self._is_pickup_helo:
            writer.text("Rescue helo — you make the pickup at the survivor.")
        else:
            writer.text('HC-130 "King" — on-scene command, overhead presence.')

        writer.heading("HOW IT WORKS")
        writer.text(
            "- Orbit near the front. When a friendly pilot ejects in the area, a "
            "downed pilot spawns with a radio beacon.\n"
            '- Use the F10 radio menu -> "CSAR" for the active rescue list, the '
            "bearing/range to the survivor, and to request smoke / flare / beacon.",
            wrap=True,
        )

        if self._is_pickup_helo:
            writer.heading("PICKUP")
            writer.text(
                "- Fly to the survivor's beacon. Come to a low, slow hover directly "
                "over them (or land alongside) and hold until they board.\n"
                "- Keep cargo doors open if your module models them.\n"
                "- Deliver the survivor to ANY friendly airfield or FARP to score "
                "the save.",
                wrap=True,
            )
            kings_with_tacan = [b for b in self.king_beacons if b.tacan is not None]
            if kings_with_tacan:
                writer.heading("KING BEACON")
                writer.text("Home on the HC-130 King (TACAN) to find the rescue area:")
                writer.table(
                    [[b.callsign, self._tacan_str(b)] for b in kings_with_tacan],
                    headers=["King", "TACAN"],
                )
        else:
            writer.heading("ON-SCENE COMMAND")
            writer.text(
                "- Hold your overhead orbit as on-scene commander. Do NOT land at "
                "the crash site.\n"
                "- The rescue helo makes the pickup; you provide presence and "
                "coordination.",
                wrap=True,
            )
            beacon = self.flight.combat_sar_king
            if beacon is not None and beacon.tacan is not None:
                writer.heading("YOUR BEACON")
                writer.text(
                    f"Radiating TACAN {beacon.tacan} ({beacon.callsign}) for the "
                    "rescue helo to home on. F10 -> Combat SAR -> LARS lists active "
                    "survivors (position, bearing/range) for you to relay.",
                    wrap=True,
                )

        writer.write(path)


class ScarTaskPage(KneeboardPage):
    """Player briefing for a SCAR (loiter-and-task) flight.

    Guidance for the loiter rework: hold over the kill box, find + ID the real
    target among look-alikes (mis-ID costs budget), and let the on-scene controller
    ("MAGIC") talk you on and designate. The MOOSE scar plugin drives the live cues,
    so this page is guidance, not exact values.
    """

    def __init__(self, flight: FlightData, dark_kneeboard: bool) -> None:
        self.flight = flight
        self.dark_kneeboard = dark_kneeboard

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        custom = f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
        writer.title(f"{self.flight.callsign} SCAR{custom}")

        writer.heading("TASK")
        writer.text(
            "Hold over the kill box and service the real enemy armor the on-scene "
            "controller (MAGIC) designates. Kills count automatically — it's a real "
            "campaign target — so there's no scoring to chase.",
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

        writer.write(path)


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

    def __init__(self, mission: Mission, game: "Game") -> None:
        super().__init__(mission, game)
        self.dark_kneeboard = self.game.settings.generate_dark_kneeboard and (
            self.mission.start_time.hour > 19 or self.mission.start_time.hour < 7
        )

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

        # Friendly-packages list folds into the bottom of the Mission Info page,
        # gated by the same setting that controls the (now map-only) standalone
        # packages kneeboard.
        package_rows = (
            self.build_all_packages_rows(flight)
            if self.game.settings.generate_all_packages_kneeboard
            else []
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
                package_rows=package_rows,
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

        if (target_page := self.generate_task_page(flight)) is not None:
            pages.append(target_page)

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

        # The friendly-packages coordination list now lives on the Mission Info
        # page (above); only the target map goes last here, gated by settings.
        if self.game.settings.generate_all_packages_kneeboard:
            pages.extend(self.generate_packages_map_page(flight))

        return pages

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
