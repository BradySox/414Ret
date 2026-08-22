"""Native DTC cartridge pre-population (§74).

Locks the cartridge JSON shapes against the format mined from the DCS ME's own
DTC editor (``CoreMods/aircraft/<type>/DTC``) + a working MP mission: the
``DTC/<name>.dtc`` files, the per-unit ``DTC.Cartridges``/``AutoLoad`` block,
channel-number mirroring of the radio allocator, ETA/TOS as seconds since
midnight, SA/HSD elements, and the recon-fog discipline on threat rings.
"""

from __future__ import annotations

import json
import math
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

import pytest
from dcs.mission import Mission
from dcs.planes import FA_18C_hornet
from dcs.terrain import Caucasus

from game.ato.dtcoptions import DtcOptions
from game.ato.flighttype import FlightType
from game.ato.flightwaypoint import GROUND_MARKED_WAYPOINTS
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.dtc import DtcGenerator
from game.missiongenerator.dtc.cartridge import (
    DtcCartridge,
    append_cartridges_to_miz,
    attach_cartridge_to_unit,
)
from game.missiongenerator.dtc.common import (
    SupportTrack,
    steerpoint_elevation,
    dedupe_stations,
    known_enemy_threat_sites,
    sanitize_short_name,
    seconds_of_day,
)
from game.missiongenerator.dtc.generator import CARTRIDGE_BUILDERS
from game.missiongenerator.dtc.hornet import build_hornet_cartridge
from game.missiongenerator.dtc import tomcat
from game.missiongenerator.dtc.tomcat import (
    MAX_ADDITIONAL_POINTS,
    TOMCAT_UNIT_TYPE,
    build_tomcat_cartridge,
    lookup_jdam_lar,
)
from game.missiongenerator.dtc.viper import build_viper_cartridge

#: Metres per degree, near enough for a fake projection the tests only need to
#: be reversible.
DEG_M = 111120.0


class Pt:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def distance_to_point(self, other: "Pt") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def new_in_same_map(self, x: float, y: float) -> "Pt":
        return Pt(x, y)

    def latlng(self) -> Any:
        # DCS x is north, y is east.
        return SimpleNamespace(lat=self.x / DEG_M, lng=self.y / DEG_M)


def _waypoint(
    name: str,
    waypoint_type: FlightWaypointType,
    x: float,
    y: float,
    alt_m: float,
    tot: Optional[datetime],
    *,
    alt_type: str = "BARO",
    targets: Optional[list[Any]] = None,
) -> Any:
    return SimpleNamespace(
        name=name,
        display_name=name,
        waypoint_type=waypoint_type,
        position=Pt(x, y),
        alt=SimpleNamespace(meters=alt_m),
        alt_type=alt_type,
        tot=tot,
        departure_time=None,
        targets=targets or [],
        # Mirror the real FlightWaypoint property (none of these fakes fly over).
        marks_ground_for_player=waypoint_type in GROUND_MARKED_WAYPOINTS,
    )


class _Freq:
    """Hashable RadioFrequency stand-in (SimpleNamespace defines __eq__ and
    loses hashability, but frequencies key the channel map)."""

    def __init__(self, mhz: float) -> None:
        self.mhz = mhz


def _freq(mhz: float) -> Any:
    return _Freq(mhz)


def _runway(name: str, atc_mhz: Optional[float] = None) -> Any:
    return SimpleNamespace(
        airfield_name=name,
        atc=_freq(atc_mhz) if atc_mhz is not None else None,
        tacan=None,
        tacan_callsign=None,
        icls=None,
    )


def _flight(
    *,
    dcs_id: str = "FA-18C_hornet",
    callsign: str = "Wizard 1",
    blue: bool = True,
    clients: int = 1,
    flight_type: FlightType = FlightType.STRIKE,
    waypoints: Optional[list[Any]] = None,
    channel_map: Optional[dict[Any, list[Any]]] = None,
    arrival: Optional[Any] = None,
    dtc_options: Optional[DtcOptions] = None,
) -> Any:
    intra = _freq(258.5)
    return SimpleNamespace(
        group_name=f"{callsign} group",
        callsign=callsign,
        friendly=SimpleNamespace(is_blue=blue),
        client_units=[SimpleNamespace() for _ in range(clients)],
        aircraft_type=SimpleNamespace(dcs_unit_type=SimpleNamespace(id=dcs_id)),
        flight_type=flight_type,
        waypoints=waypoints or [],
        intra_flight_channel=intra,
        frequency_to_channel_map=channel_map or {},
        package=SimpleNamespace(frequency=None),
        departure=_runway("Kutaisi", 259.0),
        arrival=arrival if arrival is not None else _runway("Kutaisi", 259.0),
        divert=None,
        dtc_options=dtc_options if dtc_options is not None else DtcOptions(),
    )


def _support_flight(flight_type: FlightType, callsign: str, start: Pt, end: Pt) -> Any:
    waypoints = [
        _waypoint(
            "RACETRACK START",
            FlightWaypointType.PATROL_TRACK,
            start.x,
            start.y,
            6000,
            None,
        ),
        _waypoint("RACETRACK END", FlightWaypointType.PATROL, end.x, end.y, 6000, None),
    ]
    return _flight(
        callsign=callsign,
        flight_type=flight_type,
        clients=0,
        waypoints=waypoints,
    )


def _mission_data(flights: list[Any], carriers: Optional[list[Any]] = None) -> Any:
    return SimpleNamespace(
        flights=flights,
        awacs=[],
        tankers=[],
        jtacs=[],
        carriers=carriers or [],
    )


def _game(*, dtc_on: bool = True, controlpoints: Optional[list[Any]] = None) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(dtc_data_cartridges=dtc_on),
        conditions=SimpleNamespace(start_time=datetime(1988, 7, 15, 7, 0)),
        theater=SimpleNamespace(
            terrain=SimpleNamespace(name="Caucasus"),
            timezone=timezone(timedelta(hours=4)),
            conflicts=lambda: [],
            controlpoints=controlpoints or [],
        ),
    )


def _sam_cp(*, known: bool = True, hidden: bool = False) -> Any:
    tgo = SimpleNamespace(
        name="SAM SA-2 Site",
        category="aa",
        map_hidden=hidden,
        known_for=lambda viewer: known,
        max_threat_range=lambda: SimpleNamespace(meters=43000.0),
        position=Pt(120000, -30000),
        groups=[SimpleNamespace(units=[SimpleNamespace(type="SA-2 launcher")])],
    )
    return SimpleNamespace(
        name="SAM SA-2 Site",
        position=Pt(120000, -30000),
        is_fleet=False,
        captured=SimpleNamespace(is_red=True),
        ground_objects=[tgo],
        runway_is_operational=lambda: True,
    )


def _airbase_cp(
    name: str,
    x: float,
    y: float,
    *,
    elevation_m: float = 0.0,
    red: bool = False,
    operational: bool = True,
) -> Any:
    return SimpleNamespace(
        name=name,
        position=Pt(x, y),
        field_elevation=SimpleNamespace(meters=elevation_m),
        captured=SimpleNamespace(is_red=red),
        is_fleet=False,
        runway_is_operational=lambda: operational,
        ground_objects=[],
    )


def test_channel_names_pass_the_dtc_filter() -> None:
    assert sanitize_short_name("CVN-71") == "CVN71"
    assert sanitize_short_name("Overlord 1-1") == "OVERL"
    assert sanitize_short_name("Arco") == "ARCO"


def test_eta_is_seconds_since_zulu_midnight() -> None:
    """Cartridge times are Zulu, not the local mission clock: the ME's own DTC
    manager subtracts the terrain's SummerTimeDelta, and both jets read TOT/TOS
    against a Zulu system clock. Caucasus is UTC+4, so 07:19:13 local is
    03:19:13Z."""
    game = _game()
    assert (
        seconds_of_day(game, datetime(1988, 7, 15, 7, 19, 13))
        == 3 * 3600 + 19 * 60 + 13
    )
    assert seconds_of_day(game, None) == 0


def test_eta_keeps_climbing_across_zulu_midnight() -> None:
    """The base is the mission day's Zulu midnight, not the wall clock's, so a
    sortie that crosses 00:00Z still hands the jet increasing times."""
    game = _game()
    game.conditions.start_time = datetime(1988, 7, 15, 22, 0)  # 18:00Z
    before = seconds_of_day(game, datetime(1988, 7, 15, 23, 30))  # 19:30Z
    after = seconds_of_day(game, datetime(1988, 7, 16, 5, 30))  # 01:30Z next day
    assert before == 19 * 3600 + 30 * 60
    assert after == 25 * 3600 + 30 * 60
    assert after > before


def test_threat_sites_respect_recon_fog() -> None:
    viewer = SimpleNamespace(is_blue=True)
    known = _game(controlpoints=[_sam_cp(known=True)])
    fogged = _game(controlpoints=[_sam_cp(known=False)])
    hidden = _game(controlpoints=[_sam_cp(known=True, hidden=True)])
    assert len(known_enemy_threat_sites(known, viewer)) == 1  # type: ignore[arg-type]
    assert known_enemy_threat_sites(fogged, viewer) == []  # type: ignore[arg-type]
    assert known_enemy_threat_sites(hidden, viewer) == []  # type: ignore[arg-type]
    site = known_enemy_threat_sites(known, viewer)[0]  # type: ignore[arg-type]
    assert site.label == "2"
    assert site.range_m == 43000.0


def _hornet_fixture() -> tuple[Any, Any, Any]:
    takeoff = _waypoint(
        "TAKEOFF", FlightWaypointType.TAKEOFF, 0, 0, 0, datetime(1988, 7, 15, 7, 5)
    )
    target = _waypoint(
        "TARGET",
        FlightWaypointType.TARGET_POINT,
        60000,
        80000,
        7620,
        datetime(1988, 7, 15, 7, 30),
        targets=[object()],
    )
    landing = _waypoint(
        "LANDING",
        FlightWaypointType.LANDING_POINT,
        0,
        0,
        0,
        datetime(1988, 7, 15, 8, 10),
    )
    awacs_freq = _freq(251.0)
    carrier = SimpleNamespace(
        unit_name="CVN-71 Theodore Roosevelt",
        callsign="Mother",
        tacan=SimpleNamespace(number=71, band=SimpleNamespace(value="X")),
        icls_channel=11,
        link4_freq=_freq(336.4),
    )
    flight = _flight(
        waypoints=[takeoff, target, landing],
        arrival=SimpleNamespace(
            airfield_name="CVN-71 Theodore Roosevelt",
            atc=_freq(304.25),
            tacan=None,
            tacan_callsign=None,
            icls=None,
        ),
    )
    flight.frequency_to_channel_map = {
        flight.intra_flight_channel: [SimpleNamespace(radio_id=2, channel=1)],
        awacs_freq: [SimpleNamespace(radio_id=1, channel=2)],
    }
    mission_data = _mission_data(
        [
            flight,
            _support_flight(
                FlightType.REFUELING, "Arco 1", Pt(10000, 10000), Pt(30000, 10000)
            ),
            _support_flight(
                FlightType.BARCAP, "Colt 1", Pt(-20000, 5000), Pt(-20000, 25000)
            ),
        ],
        carriers=[carrier],
    )
    mission_data.awacs = [
        SimpleNamespace(callsign="Overlord 1-1", freq=awacs_freq, group_name="ovl")
    ]
    game = _game(controlpoints=[_sam_cp()])
    return flight, mission_data, game


def test_hornet_cartridge_shape() -> None:
    flight, mission_data, game = _hornet_fixture()
    cartridge = build_hornet_cartridge(flight, mission_data, game, "Test FA-18C")

    payload = json.loads(cartridge.to_json())
    assert set(payload) == {"data", "name", "type"}
    assert payload["type"] == "FA-18C_hornet"
    data = payload["data"]
    assert data["terrain"] == "Caucasus"

    # Waypoints: numbered to MATCH THE KNEEBOARD -- its row 0 (takeoff) is not
    # emitted, so STPT n is kneeboard waypoint n.
    nav_pts = data["WYPT"]["NAV_PTS"]
    assert [w["wypt_num"] for w in nav_pts] == [1, 2]
    assert [w["text_note"] for w in nav_pts] == ["TARGET", "LANDING"]
    assert all(w["R1"] for w in nav_pts)
    assert [w["R1_order"] for w in nav_pts] == [1, 2]

    # Route sequence: ETA absolute seconds, target flagged, routes 2/3 empty.
    route = data["WYPT"]["NAV_ROUTE"]
    assert route[1] == [] and route[2] == []
    assert route[0]["STPT1"]["ETA"] == 3 * 3600 + 30 * 60  # 07:30 local, UTC+4
    assert route[0]["STPT1"]["TGT"] is True
    assert route[0]["STPT2"]["TGT"] is False

    # NAV settings: the boat card pre-tuned.
    nav_settings = data["WYPT"]["NAV_SETTINGS"]
    assert nav_settings["TACAN"] == {
        "Mode": 1,
        "Channel": 71,
        "ChannelMode": 1,
        "OnOff": True,
    }
    assert nav_settings["ICLS"] == {"Channel": 11, "OnOff": True}
    assert nav_settings["ACLS"] == {"Frequency": 336.4, "OnOff": True}
    assert nav_settings["Home_Waypoint"] == {"FPAS_HOME_WP": 2}

    # COMM: allocator channels mirrored with names; defaults elsewhere.
    comm1 = data["COMM"]["COMM1"]
    comm2 = data["COMM"]["COMM2"]
    assert comm2["Channel_1"] == {
        "frequency": 258.5,
        "modulation": 0,
        "name": "WIZAR",
    }
    assert comm1["Channel_2"] == {
        "frequency": 251.0,
        "modulation": 0,
        "name": "OVERL",
    }
    assert comm1["Channel_3"]["name"] == "CH 3"  # untouched default
    assert data["COMM"]["mirror_COMM1"] is False

    # SA: the tanker racetrack, the SAM ring, styles visible. The COLT CAP
    # station is another flight's and stays off the page; this strike plan
    # has no hold point, so there is no own-orbit entry either.
    caps = data["SA"]["CAP_PTS"]
    assert [c["note"] for c in caps] == ["ARCO"]
    assert caps[0]["id"] == "CAP_PTS_1"
    assert caps[0]["course"] == pytest.approx(0.0)  # along +x = north
    assert caps[0]["length"] == pytest.approx(20000.0)
    mez = data["SA"]["MEZ_THRTS"]
    assert len(mez) == 1
    assert mez[0]["threat_type"] == "Custom"
    assert mez[0]["text"] == "2"
    assert mez[0]["threat_ring_radius"] == pytest.approx(23.2)
    assert data["SA"]["Default_FLOT_Line"] == 1


def test_hornet_designates_the_bullseye_as_the_aa_waypoint() -> None:
    """The A/A waypoint has to BE a waypoint in the database (EA guide p158),
    and the jet's stock slot 59 is past anything our routes emit."""
    flight, mission_data, game = _hornet_fixture()
    flight.waypoints = list(flight.waypoints) + [
        _waypoint("BULLSEYE", FlightWaypointType.BULLSEYE, 5000, 5000, 0, None)
    ]
    data = json.loads(
        build_hornet_cartridge(flight, mission_data, game, "H").to_json()
    )["data"]
    nav_pts = data["WYPT"]["NAV_PTS"]
    assert nav_pts[-1]["text_note"] == "BULLSEYE"
    bulls = nav_pts[-1]["wypt_num"]
    assert data["WYPT"]["NAV_SETTINGS"]["AA_Waypoint"] == {
        "AA_WP_Number": bulls,
        "AA_WP_Enabled": True,
    }
    # A reference point, never a flown leg.
    assert nav_pts[-1]["R1"] is False
    assert f"STPT{bulls}" not in data["WYPT"]["NAV_ROUTE"][0]


def test_hornet_aa_waypoint_stays_off_without_a_bullseye() -> None:
    """No bullseye in the plan means nothing to designate; leave the jet's own
    slot 59 selected and switched off rather than pointing at empty space."""
    flight, mission_data, game = _hornet_fixture()
    data = json.loads(
        build_hornet_cartridge(flight, mission_data, game, "H").to_json()
    )["data"]
    assert data["WYPT"]["NAV_SETTINGS"]["AA_Waypoint"] == {
        "AA_WP_Number": 59,
        "AA_WP_Enabled": False,
    }


def test_viper_cartridge_shape() -> None:
    flight, mission_data, game = _hornet_fixture()
    flight.aircraft_type = SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-16C_50"))
    cartridge = build_viper_cartridge(flight, mission_data, game, "Test F-16C")
    data = json.loads(cartridge.to_json())["data"]

    nav_pts = data["MPD"]["NAV_PTS"]
    # Route first (kneeboard row 0 / takeoff not emitted, so STPT n matches
    # the kneeboard), then the tanker + CAP anchors as extra steerpoints.
    assert [p["note"] for p in nav_pts] == [
        "TARGET",
        "LANDING",
        "TKR ARCO",
    ]
    assert nav_pts[0]["TOS"] == 3 * 3600 + 30 * 60  # 07:30 local, UTC+4
    assert nav_pts[0]["isTOSEnabled"] is True
    assert nav_pts[2]["R1"] is False
    assert [p["type"] for p in nav_pts] == ["TGT", "STPT", "STPT"]

    threat = data["MPD"]["THREAT_PTS"]
    assert len(threat) == 1
    assert threat[0]["threatName"] == "Custom"
    assert threat[0]["radius"] == pytest.approx(43000.0)
    assert threat[0]["id"] == "THREAT_PTS56"

    # No COMM section: the Viper's schema has no channel names, so it could
    # only mirror the Radio table the miz already carries.
    assert "COMM" not in data


def test_viper_marks_the_target_and_the_run_in() -> None:
    """The HSD draws STPT as a circle, IP as a square and TGT as a triangle
    (EA guide p202), so the ingress and the target read at a glance."""
    flight, mission_data, game = _hornet_fixture()
    flight.aircraft_type = SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-16C_50"))
    flight.waypoints = [
        _waypoint("TAKEOFF", FlightWaypointType.TAKEOFF, 0, 0, 0, None),
        _waypoint("IP", FlightWaypointType.INGRESS_STRIKE, 100, 100, 3000, None),
        _waypoint(
            "TARGET",
            FlightWaypointType.TARGET_POINT,
            200,
            200,
            0,
            None,
            targets=[object()],
        ),
        _waypoint("EGRESS", FlightWaypointType.NAV, 300, 300, 3000, None),
        _waypoint("LANDING", FlightWaypointType.LANDING_POINT, 0, 0, 0, None),
    ]
    data = json.loads(build_viper_cartridge(flight, mission_data, game, "V").to_json())[
        "data"
    ]
    route = data["MPD"]["NAV_PTS"][:4]
    assert [p["type"] for p in route] == ["IP", "TGT", "STPT", "STPT"]
    # The id prefix stays STPT whatever the sub-type is (the editor's own rule).
    assert [p["id"] for p in route] == ["STPT1", "STPT2", "STPT3", "STPT4"]


def test_viper_route_stops_at_the_auto_sequencing_limit() -> None:
    """The jet auto-sequences only from STPT 1-20 (EA guide p223); a longer
    route would silently stop advancing itself past 20, and the support anchors
    must still land in the 21-25 tail rather than being dropped."""
    flight, mission_data, game = _hornet_fixture()
    flight.aircraft_type = SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-16C_50"))
    flight.waypoints = [
        _waypoint("TAKEOFF", FlightWaypointType.TAKEOFF, 0, 0, 0, None)
    ] + [
        _waypoint(f"NAV{i}", FlightWaypointType.NAV, i * 100, i * 100, 3000, None)
        for i in range(1, 25)
    ]
    data = json.loads(build_viper_cartridge(flight, mission_data, game, "V").to_json())[
        "data"
    ]
    nav_pts = data["MPD"]["NAV_PTS"]
    assert [p["note"] for p in nav_pts[:20]] == [f"NAV{i}" for i in range(1, 21)]
    assert [p["note"] for p in nav_pts[20:]] == ["TKR ARCO"]
    assert nav_pts[-1]["number"] == 21


def test_viper_geo_lines_stay_inside_their_partition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GEO_LINES owns steerpoints 31-55 and the editor refuses a 26th point; a
    fuller line source than today's 2-point fronts would otherwise run ids into
    the pre-planned-threat partition at 56."""
    flight, mission_data, game = _hornet_fixture()
    flight.aircraft_type = SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-16C_50"))
    segments = [
        (f"Front {n}", [(float(n * 1000 + i), float(i)) for i in range(8)])
        for n in range(4)
    ]
    monkeypatch.setattr(
        "game.missiongenerator.dtc.viper.flot_segments", lambda g: segments
    )
    data = json.loads(build_viper_cartridge(flight, mission_data, game, "V").to_json())[
        "data"
    ]
    geo = data["MPD"]["GEO_LINES"]
    assert len(geo) == 25
    assert geo[-1]["id"] == "GEO_LINES55"


def _viper_with_fields(fields: list[Any], divert: Optional[str] = None) -> Any:
    flight, mission_data, game = _hornet_fixture()
    flight.aircraft_type = SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-16C_50"))
    game.theater.controlpoints = fields
    if divert is not None:
        flight.divert = _runway(divert)
    return flight, mission_data, game


def test_viper_destinations_lead_with_the_divert() -> None:
    """DEST owns steerpoints 81-99 (EA guide p203). The briefed divert leads;
    the rest sort by distance from the target so the nearest alternates are the
    ones that fit."""
    flight, mission_data, game = _viper_with_fields(
        [
            _airbase_cp("Vaziani", 200000, 200000),
            _airbase_cp("Kobuleti", 61000, 81000, elevation_m=17.0),
            _airbase_cp("Krasnodar", 400000, 400000, red=True),
            _airbase_cp("Senaki", 65000, 85000, operational=False),
            _airbase_cp("Batumi", 70000, 90000),
        ],
        divert="Vaziani",
    )
    data = json.loads(build_viper_cartridge(flight, mission_data, game, "V").to_json())[
        "data"
    ]
    dest = data["MPD"]["DEST"]
    # Red-held and unusable fields drop out; the divert leads, then by range
    # from the target at (60000, 80000).
    assert [d["note"] for d in dest] == ["Vaziani", "Kobuleti", "Batumi"]
    assert [d["id"] for d in dest] == ["DEST81", "DEST82", "DEST83"]
    assert [d["text"] for d in dest] == ["VAZ", "KOB", "BAT"]
    assert dest[1]["alt"] == pytest.approx(17.0)
    assert dest[0]["number"] == 1


def test_viper_destination_labels_stay_three_characters() -> None:
    """The HSD shows three alphanumerics, so a collision has to fit in three."""
    flight, mission_data, game = _viper_with_fields(
        [
            _airbase_cp("Kutaisi", 61000, 81000),
            _airbase_cp("Kut-Al Field", 62000, 82000),
            _airbase_cp("CVN-71 Theodore Roosevelt", 63000, 83000),
        ]
    )
    data = json.loads(build_viper_cartridge(flight, mission_data, game, "V").to_json())[
        "data"
    ]
    labels = [d["text"] for d in data["MPD"]["DEST"]]
    assert labels == ["KUT", "KU2", "CVN"]
    assert all(len(label) <= 3 for label in labels)


def test_viper_destinations_stop_at_the_partition_end() -> None:
    """Steerpoints 81-99 is 19 slots, and the editor refuses a 20th."""
    flight, mission_data, game = _viper_with_fields(
        [_airbase_cp(f"Field{n:02d}", 60000 + n * 1000, 80000) for n in range(25)]
    )
    data = json.loads(build_viper_cartridge(flight, mission_data, game, "V").to_json())[
        "data"
    ]
    dest = data["MPD"]["DEST"]
    assert len(dest) == 19
    assert dest[-1]["id"] == "DEST99"


def test_a_steerpoints_alt_is_its_ground_not_its_leg_altitude() -> None:
    """``alt`` on a point is the ground under it; the leg altitude is a separate
    field. ED's own editors fill the first from terrain -- ``alt = getAltitude(x, y)``
    in the Viper's ``NAV_PTS.lua`` and the Hornet's ``WYPT_NAV.lua`` -- and resolve
    the second against terrain when it is AGL (``tmpAlt + getAltitude(x, y)``,
    Hornet ``ROUTE_SEQ.lua``).

    We wrote the leg altitude into both until 2026-08-20, so a nav point at 22,000 ft
    told the jet the ground under it was at 22,000 ft, and a target told it the
    ground was at sea level. Reported from the cockpit as the target steerpoint
    sitting at 0 MSL rather than 0 AGL.
    """
    takeoff = _waypoint("TAKEOFF", FlightWaypointType.TAKEOFF, 0, 0, 0, None)
    nav = _waypoint("NAV", FlightWaypointType.NAV, 10000, 0, 6705, None)
    target = _waypoint(
        "TARGET", FlightWaypointType.TARGET_GROUP_LOC, 60000, 80000, 6705, None
    )
    land = _waypoint("LANDING", FlightWaypointType.LANDING_POINT, 0, 0, 58, None)
    # Kneeboard row 0 (takeoff) is not emitted; the rest land on STPT 1/2/3.
    flight = _flight(waypoints=[takeoff, nav, target, land])
    mission_data = _mission_data([flight])
    game = _game()

    hornet = json.loads(
        build_hornet_cartridge(flight, mission_data, game, "Test FA-18C").to_json()
    )["data"]
    nav_pts = hornet["WYPT"]["NAV_PTS"]
    route = hornet["WYPT"]["NAV_ROUTE"][0]
    # Nav point: ground unknown, so 0 -- never the 6705 m it is flown at.
    assert nav_pts[0]["alt"] == 0
    assert route["STPT1"]["alt"] == 6705 and route["STPT1"]["altitudeType"] == 1
    # Target: still 0, and the leg is the .miz's 0 AGL.
    assert nav_pts[1]["alt"] == 0
    assert route["STPT2"]["alt"] == 0 and route["STPT2"]["altitudeType"] == 1
    # Landing: the one point whose planned altitude IS its ground (B79).
    assert nav_pts[2]["alt"] == 58

    flight.aircraft_type = SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-16C_50"))
    viper = json.loads(
        build_viper_cartridge(flight, mission_data, game, "Test F-16C").to_json()
    )["data"]
    steerpoints = viper["MPD"]["NAV_PTS"]
    assert steerpoints[0]["alt"] == 0 and steerpoints[0]["routeAltitude"] == 6705
    assert steerpoints[1]["alt"] == 0 and steerpoints[1]["routeAltitude"] == 0
    assert steerpoints[1]["altitudeType"] == 1
    assert steerpoints[2]["alt"] == 58


def test_unit_dict_and_miz_round_trip(tmp_path: Path) -> None:
    mission = Mission(Caucasus())
    usa = mission.country("USA")
    group = mission.flight_group_inflight(
        usa,
        "DTC Test",
        FA_18C_hornet,
        mission.terrain.airports["Kutaisi"].position,
        altitude=6000,
        group_size=2,
    )
    attach_cartridge_to_unit(group.units[0], "Test FA-18C")

    lead = group.units[0].dict()
    wing = group.units[1].dict()
    assert lead["DTC"] == {
        "Cartridges": [{"default": True, "name": "Test FA-18C"}],
        "AutoLoad": True,
    }
    assert "DTC" not in wing

    miz = tmp_path / "dtc_test.miz"
    mission.save(str(miz))
    cartridge = DtcCartridge(
        name="Test FA-18C",
        unit_type="FA-18C_hornet",
        terrain="Caucasus",
        data={"COMM": {}, "type": "FA-18C_hornet"},
    )
    append_cartridges_to_miz(miz, [cartridge])

    with zipfile.ZipFile(miz) as zf:
        raw = zf.read("DTC/Test FA-18C.dtc")
        payload = json.loads(raw)
        assert payload["name"] == "Test FA-18C"
        mission_lua = zf.read("mission").decode("utf-8")
        assert '"AutoLoad"' in mission_lua
        assert '"Cartridges"' in mission_lua
        assert "Test FA-18C" in mission_lua

    # A miz carrying DTC data must still load cleanly (campaign mizzes may be
    # authored with cartridges; pydcs ignores the extra unit key + zip entry).
    reloaded = Mission(Caucasus())
    reloaded.load_file(str(miz))


def _generator(game: Any, flights: list[Any]) -> DtcGenerator:
    return DtcGenerator(
        SimpleNamespace(),  # type: ignore[arg-type]
        game,
        _mission_data(flights),
    )


def test_generator_builds_only_blue_client_supported_flights(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built = []

    def fake_builder(flight: Any, md: Any, game: Any, name: str) -> DtcCartridge:
        built.append(name)
        return DtcCartridge(name, "FA-18C_hornet", "Caucasus", {})

    monkeypatch.setitem(CARTRIDGE_BUILDERS, "FA-18C_hornet", fake_builder)

    flights = [
        _flight(callsign="Wizard 1"),
        _flight(callsign="Wizard 1"),  # same callsign: name must dedupe
        _flight(callsign="Dodge 1", blue=False),
        _flight(callsign="Uzi 1", clients=0),
        _flight(callsign="Chevy 1", dcs_id="F-14B"),
    ]
    generator = _generator(_game(), flights)
    generator.generate()
    assert built == [
        "Retribution Wizard 1 FA-18C_hornet",
        "Retribution Wizard 1 FA-18C_hornet 2",
    ]
    assert len(generator.cartridges) == 2


def test_generator_respects_the_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        CARTRIDGE_BUILDERS,
        "FA-18C_hornet",
        lambda *args: pytest.fail("builder must not run when the setting is off"),
    )
    generator = _generator(_game(dtc_on=False), [_flight()])
    generator.generate()
    assert generator.cartridges == []


def test_generator_survives_a_builder_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(*args: Any) -> DtcCartridge:
        raise RuntimeError("boom")

    monkeypatch.setitem(CARTRIDGE_BUILDERS, "FA-18C_hornet", broken)
    generator = _generator(_game(), [_flight()])
    generator.generate()
    assert generator.cartridges == []


def test_per_flight_override_beats_the_campaign_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_builder(f: Any, md: Any, g: Any, name: str) -> DtcCartridge:
        return DtcCartridge(name, "FA-18C_hornet", "Caucasus", {})

    monkeypatch.setitem(CARTRIDGE_BUILDERS, "FA-18C_hornet", fake_builder)
    # Campaign OFF, flight forced ON -> builds.
    generator = _generator(
        _game(dtc_on=False),
        [_flight(callsign="Force On", dtc_options=DtcOptions(enabled=True))],
    )
    generator.generate()
    assert len(generator.cartridges) == 1
    # Campaign ON, flight forced OFF -> skipped.
    generator = _generator(
        _game(),
        [_flight(callsign="Force Off", dtc_options=DtcOptions(enabled=False))],
    )
    generator.generate()
    assert generator.cartridges == []


def test_all_sections_off_builds_no_cartridge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        CARTRIDGE_BUILDERS,
        "FA-18C_hornet",
        lambda *args: pytest.fail("an empty cartridge must not be built"),
    )
    bare = DtcOptions(
        comms=False,
        route=False,
        nav_aids=False,
        flot_and_zones=False,
        friendly_orbits=False,
        threat_rings=False,
        destinations=False,
        jdam_targets=False,
    )
    generator = _generator(_game(), [_flight(dtc_options=bare)])
    generator.generate()
    assert generator.cartridges == []


def test_hornet_sections_are_omitted_when_off() -> None:
    flight, mission_data, game = _hornet_fixture()
    flight.dtc_options = DtcOptions(
        comms=False, route=False, friendly_orbits=False, threat_rings=False
    )
    cartridge = build_hornet_cartridge(flight, mission_data, game, "Trimmed")
    data = json.loads(cartridge.to_json())["data"]
    assert "COMM" not in data
    # nav_aids stays on: WYPT present with the boat tuned but no steerpoints.
    assert data["WYPT"]["NAV_PTS"] == []
    assert data["WYPT"]["NAV_SETTINGS"]["TACAN"]["OnOff"] is True
    # flot_and_zones stays on: SA present, but no CAP orbits and no MEZ rings.
    assert data["SA"]["CAP_PTS"] == []
    assert data["SA"]["MEZ_THRTS"] == []
    assert len(data["SA"]["FAOR_FLOT"]["FLOT"]) == 0  # fake game has no fronts

    flight.dtc_options = DtcOptions(
        nav_aids=False, flot_and_zones=False, friendly_orbits=False, threat_rings=False
    )
    cartridge = build_hornet_cartridge(flight, mission_data, game, "Route Only")
    data = json.loads(cartridge.to_json())["data"]
    assert "SA" not in data
    assert len(data["WYPT"]["NAV_PTS"]) == 2  # kneeboard rows 1..N
    assert data["WYPT"]["NAV_SETTINGS"]["TACAN"]["OnOff"] is False


def test_viper_sections_are_omitted_when_off() -> None:
    flight, mission_data, game = _hornet_fixture()
    flight.aircraft_type = SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-16C_50"))
    flight.dtc_options = DtcOptions(comms=False, route=False, destinations=False)
    cartridge = build_viper_cartridge(flight, mission_data, game, "Anchors Only")
    data = json.loads(cartridge.to_json())["data"]
    assert "COMM" not in data
    # Route off, friendly orbits on: only the support anchors load.
    assert [p["note"] for p in data["MPD"]["NAV_PTS"]] == ["TKR ARCO"]

    flight.dtc_options = DtcOptions(
        comms=False,
        route=False,
        nav_aids=False,
        flot_and_zones=False,
        friendly_orbits=False,
        threat_rings=True,
        destinations=False,
    )
    cartridge = build_viper_cartridge(flight, mission_data, game, "Threats Only")
    data = json.loads(cartridge.to_json())["data"]
    assert data["MPD"]["NAV_PTS"] == []
    assert data["MPD"]["GEO_LINES"] == []
    assert len(data["MPD"]["THREAT_PTS"]) == 1


def test_flot_populates_when_a_front_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    """The FLOT half of option 4 -- every other test runs a game with no fronts
    (conflicts() == []), so the front-line geometry reaching FAOR_FLOT (Hornet)
    and GEO_LINES (Viper) was never exercised. flot_segments itself mirrors the
    trusted F10 frontline drawing; this locks the builders consuming it."""
    flight, mission_data, game = _hornet_fixture()
    segments = [
        ("Front A", [(1000.0, 2000.0), (3000.0, 4000.0)]),
        ("Front B", [(5000.0, 6000.0), (7000.0, 8000.0)]),
    ]
    monkeypatch.setattr(
        "game.missiongenerator.dtc.hornet.flot_segments", lambda g: segments
    )
    monkeypatch.setattr(
        "game.missiongenerator.dtc.viper.flot_segments", lambda g: segments
    )

    hornet = json.loads(
        build_hornet_cartridge(flight, mission_data, game, "H").to_json()
    )["data"]
    flot = hornet["SA"]["FAOR_FLOT"]["FLOT"]
    assert [line["note"] for line in flot] == ["Front A", "Front B"]
    assert flot[0]["id"] == "FLOT_1"
    assert flot[0]["num"] == 1
    assert [(p["x"], p["y"]) for p in flot[0]["points"]] == [
        (1000.0, 2000.0),
        (3000.0, 4000.0),
    ]

    flight.aircraft_type = SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-16C_50"))
    viper = json.loads(
        build_viper_cartridge(flight, mission_data, game, "V").to_json()
    )["data"]
    geo = viper["MPD"]["GEO_LINES"]
    # Two 2-point fronts = 4 points, tagged to consecutive HSD line sets.
    assert len(geo) == 4
    assert geo[0]["note"] == "Front A"
    assert geo[0]["L1"] is True and geo[0]["L2"] is False
    assert geo[2]["note"] == "Front B"
    assert geo[2]["L2"] is True and geo[2]["L1"] is False


def _track(callsign: str, cx: float, cy: float, course: float, length: float) -> Any:
    half = length / 2.0
    dx = math.cos(math.radians(course)) * half
    dy = math.sin(math.radians(course)) * half
    return SupportTrack(
        callsign=callsign,
        kind="CAP",
        start=Pt(cx - dx, cy - dy),  # type: ignore[arg-type]
        end=Pt(cx + dx, cy + dy),  # type: ignore[arg-type]
    )


def test_wave_relief_duplicates_collapse_to_stations() -> None:
    # The nine CAP entries a flown 2026-07-19 miz actually carried (center
    # x/y, course, length): three stations flown as three jittered waves
    # each, which filled all nine Hornet SA slots and squeezed out every
    # tanker/AWACS orbit -- the reported "missing quite a few race tracks".
    waves = [
        _track("FORD", -24468, -404462, 56, 43244),
        _track("FORD", -4741, -383779, 62, 60018),
        _track("JEDI", 40, -406873, 74, 60759),
        _track("UZI", -25732, -406336, 56, 59938),
        _track("UZI", -2637, -379822, 62, 35138),
        _track("DODGE", 5270, -388631, 74, 44069),
        _track("PONTI", -20464, -398527, 56, 59184),
        _track("UZI", -1618, -377906, 62, 34482),
        _track("COLT", 1501, -401777, 74, 62656),
    ]
    stations = dedupe_stations(waves)
    assert [s.callsign for s in stations] == ["FORD", "FORD", "JEDI"]


def test_distinct_stations_survive_dedupe() -> None:
    far_apart = [
        _track("ALPHA", 0, 0, 90, 20000),
        _track("BRAVO", 60000, 0, 90, 20000),  # 60 km away: its own station
        _track("CHARL", 0, 100, 0, 20000),  # co-located but perpendicular
    ]
    assert len(dedupe_stations(far_apart)) == 3


def test_other_flights_cap_stations_never_appear() -> None:
    """However many CAP stations the ATO flies, none of them is this jet's
    business: the page carries its own orbit and the support orbits only."""
    flight, mission_data, game = _hornet_fixture()
    for callsign, x in (("Colt 2", -17000), ("Ford 1", 30000), ("Uzi 1", 50000)):
        mission_data.flights.append(
            _support_flight(FlightType.BARCAP, callsign, Pt(x, 6500), Pt(x, 26500))
        )
    cartridge = build_hornet_cartridge(flight, mission_data, game, "Crowded")
    caps = json.loads(cartridge.to_json())["data"]["SA"]["CAP_PTS"]
    assert [c["note"] for c in caps] == ["ARCO"]


def test_own_racetrack_leads_and_is_preselected() -> None:
    """A flight that flies a racetrack gets it as CAP point 1, selected at
    spawn; the tanker follows; the other flight's COLT station never appears."""
    flight, mission_data, game = _hornet_fixture()
    flight.flight_type = FlightType.BARCAP
    flight.waypoints = list(flight.waypoints) + [
        _waypoint(
            "RACETRACK START", FlightWaypointType.PATROL_TRACK, -40000, 5000, 6000, None
        ),
        _waypoint(
            "RACETRACK END", FlightWaypointType.PATROL, -40000, 25000, 6000, None
        ),
    ]
    cartridge = build_hornet_cartridge(flight, mission_data, game, "Own CAP")
    data = json.loads(cartridge.to_json())["data"]["SA"]
    assert [c["note"] for c in data["CAP_PTS"]] == ["WIZAR", "ARCO"]
    assert data["CAP_PTS"][0]["course"] == pytest.approx(90.0)
    assert data["Default_CAP_Point"] == 1


def _with_hold(flight: Any) -> None:
    flight.waypoints = (
        [flight.waypoints[0]]
        + [_waypoint("HOLD", FlightWaypointType.LOITER, 15000, 15000, 6000, None)]
        + list(flight.waypoints[1:])
    )


def test_a_flight_without_an_orbit_gets_a_track_at_its_hold() -> None:
    """Not a true orbiting plan, so instead of no track at all the page gets
    one at the hold point -- the minimum-length racetrack, selected at spawn."""
    flight, mission_data, game = _hornet_fixture()
    _with_hold(flight)
    cartridge = build_hornet_cartridge(flight, mission_data, game, "Hold")
    data = json.loads(cartridge.to_json())["data"]["SA"]
    caps = data["CAP_PTS"]
    assert [c["note"] for c in caps] == ["WIZAR", "ARCO"]
    assert (caps[0]["x"], caps[0]["y"]) == (15000, 15000)
    assert caps[0]["length"] == pytest.approx(3704.0)
    assert data["Default_CAP_Point"] == 1


def test_the_hold_stand_in_reaches_the_viper_and_tomcat_too() -> None:
    flight, mission_data, game = _hornet_fixture()
    _with_hold(flight)
    flight.aircraft_type = SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-16C_50"))
    nav_pts = json.loads(
        build_viper_cartridge(flight, mission_data, game, "Hold").to_json()
    )["data"]["MPD"]["NAV_PTS"]
    # The route takes 1-3 (hold, target, landing); the anchors follow.
    assert [p["note"] for p in nav_pts[3:]] == ["HOLD WIZAR", "TKR ARCO"]

    flight.aircraft_type = SimpleNamespace(
        dcs_unit_type=SimpleNamespace(id=TOMCAT_UNIT_TYPE)
    )
    points = json.loads(
        build_tomcat_cartridge(flight, mission_data, game, "Hold").to_json()
    )["data"]["NAV"][0]["additional_points"]
    assert [p["name"] for p in points] == ["WIZAR", "ARCO", "SA2"]


def test_viper_dest_paints_the_enemy_field_being_worked_over() -> None:
    """An OCA Viper wants the target field on the HSD, and only the DEST
    partition draws an airfield: it lands right after the briefed divert."""
    flight, mission_data, game = _hornet_fixture()
    flight.aircraft_type = SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-16C_50"))
    flight.divert = _runway("Batumi")
    # The target is at (60000, 80000); the red field sits 5 km from it.
    game.theater.controlpoints = [
        _airbase_cp("Batumi", -9000, 3000),
        _airbase_cp("Kutaisi", 0, 0),
        _airbase_cp("Senaki", 62000, 84000, red=True),
        _airbase_cp("Sukhumi", 200000, 200000, red=True),
    ]
    dest = json.loads(
        build_viper_cartridge(flight, mission_data, game, "OCA").to_json()
    )["data"]["MPD"]["DEST"]
    assert [d["note"] for d in dest] == ["Batumi", "Senaki", "Kutaisi"]
    assert dest[1]["id"] == "DEST82"


def test_old_saves_default_the_flight_options() -> None:
    from game.ato.flight import Flight
    from game.settings import Settings

    flight = object.__new__(Flight)
    state = {"squadron": SimpleNamespace(settings=Settings()), "roster": None}
    flight.__setstate__(state)
    assert isinstance(flight.dtc_options, DtcOptions)
    assert flight.dtc_options.enabled is None
    assert flight.dtc_options.any_content


def test_generator_skips_a_builder_that_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(CARTRIDGE_BUILDERS, "FAKE-JET", lambda *args: None)
    flight = _flight(dcs_id="FAKE-JET", callsign="Rhino 1")
    generator = _generator(_game(), [flight])
    generator.generate()
    assert generator.cartridges == []
    assert not hasattr(flight.client_units[0], "retribution_dtc")


def test_super_hornets_take_no_cartridge() -> None:
    """Removed 2026-08-22: the mod's descriptor has no SA table, and the comm
    presets and route already reach the jet through the miz."""
    for dcs_id in ("FA-18E", "FA-18F", "EA-18G", "FA-18ET", "FA-18FT"):
        assert dcs_id not in CARTRIDGE_BUILDERS


def _tomcat_fixture() -> tuple[Any, Any, Any]:
    flight, mission_data, game = _hornet_fixture()
    flight.aircraft_type = SimpleNamespace(
        dcs_unit_type=SimpleNamespace(id=TOMCAT_UNIT_TYPE)
    )
    flight.callsign = "Dodge 1"
    flight.waypoints = [
        _waypoint(
            "TAKEOFF", FlightWaypointType.TAKEOFF, 0, 0, 0, datetime(1988, 7, 15, 7, 5)
        ),
        _waypoint(
            "INGRESS",
            FlightWaypointType.INGRESS_STRIKE,
            40000,
            40000,
            6096,
            datetime(1988, 7, 15, 7, 25),
            targets=[object()],
        ),
        _waypoint(
            "POWER PLANT",
            FlightWaypointType.TARGET_POINT,
            80000,
            40000,
            6096,
            datetime(1988, 7, 15, 7, 30),
            targets=[object()],
        ),
        _waypoint(
            "LANDING",
            FlightWaypointType.LANDING_POINT,
            0,
            0,
            0,
            datetime(1988, 7, 15, 8, 10),
        ),
        _waypoint("BULLSEYE", FlightWaypointType.BULLSEYE, 5000, 5000, 0, None),
        _waypoint("BATUMI", FlightWaypointType.DIVERT, -9000, 3000, 0, None),
    ]
    mission_data.flights[0] = flight
    return flight, mission_data, game


def test_tomcat_is_registered_but_the_plain_f14b_is_not() -> None:
    """F14/Entry/F-14B.lua sets DTC only for the F-14BU rewrite, so a cartridge
    bound to any other Tomcat would have nothing to read it."""
    assert CARTRIDGE_BUILDERS[TOMCAT_UNIT_TYPE] is build_tomcat_cartridge
    assert "F-14B" not in CARTRIDGE_BUILDERS
    assert "F-14A-135-GR" not in CARTRIDGE_BUILDERS


def test_tomcat_leaves_plan_one_waypoints_to_the_me_route() -> None:
    """Plan 1 IS the miz route -- the editor greys its waypoint fields out for
    that reason, so the cartridge adds only what a route cannot carry."""
    flight, mission_data, game = _tomcat_fixture()
    cartridge = build_tomcat_cartridge(flight, mission_data, game, "Test F-14BU")
    payload = json.loads(cartridge.to_json())
    assert payload["type"] == TOMCAT_UNIT_TYPE
    data = payload["data"]
    assert data["type"] == TOMCAT_UNIT_TYPE
    assert data["cartridge_name"] == "DODGE1"

    plans = data["NAV"]
    assert len(plans) == 12
    assert plans[0]["waypoints"] == []
    # An empty name keeps the editor's own "1: ME Route" label.
    assert plans[0]["name"] == ""
    assert plans[0]["route_as_line"] is False
    # Plan 2 is ours; 3-12 stay untouched.
    assert all(plan == _EMPTY_PLAN for plan in plans[2:])


#: What an untouched plan looks like -- createFlightPlan() in the descriptor.
_EMPTY_PLAN = {
    "name": "",
    "waypoints": [],
    "lines": [],
    "additional_points": [],
    "route_as_line": False,
}


def test_tomcat_route_lands_on_plan_two_with_the_jets_name_codes() -> None:
    """The ED-authored cartridge in hand puts the flown route on plan 2 with
    route_as_line set, TOTs rather than speeds, and names carrying the codes
    (IPORCXIP). Plan 1 is left to the mission editor."""
    flight, mission_data, game = _tomcat_fixture()
    cartridge = build_tomcat_cartridge(flight, mission_data, game, "Test F-14BU")
    route = json.loads(cartridge.to_json())["data"]["NAV"][1]
    assert route["name"] == "ROUTE 1"
    assert route["route_as_line"] is True
    # Waypoint 0 is the spawn, so plan 2's n matches the kneeboard's n.
    # Bare uppercase alphanumerics, like every name in the authored cartridge.
    assert [w["name"] for w in route["waypoints"]] == [
        "INGREXIP",
        "POWERPLA",
        "LANDIXHB",
    ]
    # 07:25 local on a UTC+4 map is 03:25Z.
    assert route["waypoints"][0]["tot"] == "03:25:00"
    # A speed and a TOT are mutually exclusive in the editor.
    assert route["waypoints"][0]["spd"] == 0
    # The reference layer rides both plans, so selecting plan 2 loses nothing.
    assert route["additional_points"] == (
        json.loads(cartridge.to_json())["data"]["NAV"][0]["additional_points"]
    )


def test_tomcat_references_carry_the_jets_name_codes() -> None:
    """The NAV tab documents the trailing codes: XB types a point as a bullseye
    reference, XD as a destination, and every name caps at 8 characters."""
    flight, mission_data, game = _tomcat_fixture()
    cartridge = build_tomcat_cartridge(flight, mission_data, game, "Test F-14BU")
    points = json.loads(cartridge.to_json())["data"]["NAV"][0]["additional_points"]
    names = [point["name"] for point in points]
    # The base name gives way to the code, never the other way round.
    assert names[:2] == ["BULLSEXB", "BATUMIXD"]
    # Then the tanker; COLT is another flight's station and stays out.
    assert names[2:] == ["ARCO", "SA2"]
    assert all(len(name) <= 8 for name in names)
    bullseye = points[0]
    assert (bullseye["x"], bullseye["y"]) == (5000, 5000)
    assert bullseye["lat"] == pytest.approx(5000 / DEG_M)
    assert bullseye["lon"] == pytest.approx(5000 / DEG_M)


def test_tomcat_front_line_rides_the_plot_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same shape as the ED-authored cartridge's plot line, open rather than
    closed because a front is a segment, not an area."""
    monkeypatch.setattr(
        tomcat,
        "flot_segments",
        lambda game: [("Front", [(1000.0, 2000.0), (5000.0, 6000.0)])],
    )
    flight, mission_data, game = _tomcat_fixture()
    data = json.loads(
        build_tomcat_cartridge(flight, mission_data, game, "Lines").to_json()
    )["data"]
    line = data["NAV"][0]["lines"][0]
    assert line["closed"] is False
    assert sorted(line["points"][0]) == ["elev", "lat", "lon", "x", "y"]
    # The route plan repeats it, so switching plans does not lose the front.
    assert data["NAV"][1]["lines"] == data["NAV"][0]["lines"]


def test_tomcat_threat_points_ride_the_recon_fog() -> None:
    flight, mission_data, game = _tomcat_fixture()
    flight.dtc_options = DtcOptions(route=False, friendly_orbits=False)
    cartridge = build_tomcat_cartridge(flight, mission_data, game, "Threats")
    points = json.loads(cartridge.to_json())["data"]["NAV"][0]["additional_points"]
    assert [point["name"] for point in points] == ["SA2"]

    fogged = _game(controlpoints=[_sam_cp(known=False)])
    cartridge = build_tomcat_cartridge(flight, mission_data, fogged, "Fogged")
    assert json.loads(cartridge.to_json())["data"]["NAV"][0]["additional_points"] == []


def test_tomcat_reference_points_stop_at_the_descriptors_budget() -> None:
    flight, mission_data, game = _tomcat_fixture()
    game.theater.controlpoints = [_sam_cp() for _ in range(40)]
    cartridge = build_tomcat_cartridge(flight, mission_data, game, "Crowded")
    points = json.loads(cartridge.to_json())["data"]["NAV"][0]["additional_points"]
    assert len(points) == MAX_ADDITIONAL_POINTS


def test_tomcat_jdam_points_load_every_station() -> None:
    """Four stations of eight, the same ordered list on each: the crew picks
    the index rather than the generator guessing which bomb goes where."""
    flight, mission_data, game = _tomcat_fixture()
    cartridge = build_tomcat_cartridge(flight, mission_data, game, "Test F-14BU")
    stations = json.loads(cartridge.to_json())["data"]["JDAM"]["stations"]
    assert len(stations) == 4
    assert all(len(station["targets"]) == 8 for station in stations)
    assert all(
        station["targets"][0] == stations[0]["targets"][0] for station in stations
    )

    target = stations[0]["targets"][0]
    assert target["active"] is True
    assert target["name"] == "POWERPLA"
    # Run-in heading from the ingress point: due north on this fixture.
    assert target["attack_heading"] == pytest.approx(0.0)
    assert target["drop_alt"] == pytest.approx(20000.0)
    assert target["lar_rmax_nmi"] > target["lar_rmin_nmi"] > 0

    # The ingress waypoint carries the same target list for the task setup, and
    # it is not an aimpoint -- only the target point is planned.
    assert stations[0]["targets"][1]["active"] is False

    empty = stations[0]["targets"][1]
    assert empty["active"] is False
    assert empty["name"] == ""
    # An unplaced slot carries no coordinates at all, like createJDAMTarget.
    assert "lat" not in empty and "x" not in empty


def test_tomcat_elevations_use_each_sections_own_unit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NAV writes metersToFeet(getAltitude(...)); JDAM stores the raw metres and
    converts only for display. Mixing them is a 3.28x error."""
    monkeypatch.setattr(tomcat, "steerpoint_elevation", lambda waypoint, game: 100.0)
    flight, mission_data, game = _tomcat_fixture()
    data = json.loads(
        build_tomcat_cartridge(flight, mission_data, game, "Units").to_json()
    )["data"]
    assert data["JDAM"]["stations"][0]["targets"][0]["elev"] == 100
    assert data["NAV"][1]["waypoints"][0]["elev"] == 328


def test_tomcat_waypoints_carry_the_altitude_their_one_field_expects() -> None:
    """The Tomcat waypoint has a single altitude field where the Hornet has two,
    so it takes the field elevation at the route's ends and the planned altitude
    in between -- the way the authored cartridge fills it."""
    flight, mission_data, game = _tomcat_fixture()
    route = json.loads(
        build_tomcat_cartridge(flight, mission_data, game, "Alt").to_json()
    )["data"]["NAV"][1]["waypoints"]
    # 6096 m planned on the ingress leg.
    assert route[0]["elev"] == 20000
    # The target is ground-marked for players, so the miz puts it on the deck
    # and the cartridge has to agree.
    assert route[1]["elev"] == 0
    # Landing takes the field's own elevation, which this fixture puts at 0.
    assert route[2]["elev"] == 0


def test_tomcat_lar_table_matches_the_descriptor() -> None:
    """Ported table: the corners clamp to the published cells, and the jet
    reads these cached scalars straight out of the cartridge."""
    slow_low = lookup_jdam_lar(100.0, 1.0)
    assert slow_low == pytest.approx((0.87, 1.50, 20.00))
    fast_high = lookup_jdam_lar(2000.0, 60.0)
    assert fast_high == pytest.approx((3.87, 15.27, 45.00))
    # A mid-table lookup lands between its neighbours, not on a corner.
    middle = lookup_jdam_lar(450.0, 20.0)
    assert 1.0 < middle[0] < 2.5
    assert 3.0 < middle[1] < 9.0


def test_tomcat_tis_sends_to_the_package() -> None:
    """Package mates only, six characters, blank-padded -- sanitizeTISCallsign."""
    flight, mission_data, game = _tomcat_fixture()
    package = SimpleNamespace(frequency=None)
    flight.package = package
    mate = _flight(callsign="Uzi 1-1", dcs_id=TOMCAT_UNIT_TYPE)
    mate.package = package
    red = _flight(callsign="Ivan 1", blue=False)
    red.package = package
    mission_data.flights = [flight, mate, red]

    tis = json.loads(
        build_tomcat_cartridge(flight, mission_data, game, "TIS").to_json()
    )["data"]["TIS"]
    assert tis["send_to_callsigns"] == ["UZI11 "]
    assert tis["use_mission_callsign"] is True
    assert tis["add_wingmen_to_list"] is True
    assert tis["own_callsign"] == "      "


def test_tomcat_sections_off_carry_the_editors_reset_state() -> None:
    """This descriptor cannot take a partial cartridge -- setData's tail calls
    init_CMDS(), which indexes data.CMDS.CMDSProgramSettings outright (the ME
    import of 2026-08-22 died there). So every section is always present, and
    an off section looks exactly like an untouched cartridge's."""
    flight, mission_data, game = _tomcat_fixture()
    flight.dtc_options = DtcOptions(
        comms=False,
        route=False,
        flot_and_zones=False,
        friendly_orbits=False,
        threat_rings=False,
        jdam_targets=False,
    )
    data = json.loads(
        build_tomcat_cartridge(flight, mission_data, game, "Bare").to_json()
    )["data"]
    assert sorted(data) == [
        "CMDS",
        "JDAM",
        "NAV",
        "TIS",
        "cartridge_name",
        "name",
        "type",
    ]
    assert len(data["NAV"]) == 12
    assert all(plan == _EMPTY_PLAN for plan in data["NAV"])
    stations = data["JDAM"]["stations"]
    assert len(stations) == 4
    assert all(
        len(s["targets"]) == 8 and not any(t["active"] for t in s["targets"])
        for s in stations
    )
    assert data["TIS"] == {
        "use_mission_callsign": True,
        "own_callsign": "      ",
        "add_wingmen_to_list": True,
        "send_to_callsigns": [],
    }


def test_tomcat_cmds_is_eds_stock_table() -> None:
    """Always written, never campaign-tuned: the values the editor itself saves
    for an untouched cartridge, checked against an authored one."""
    flight, mission_data, game = _tomcat_fixture()
    cmds = json.loads(
        build_tomcat_cartridge(flight, mission_data, game, "CMDS").to_json()
    )["data"]["CMDS"]
    assert cmds["CMDSBingoSettings"] == {
        "ChaffNum": 10,
        "FlaresNum": 10,
        "Other1Num": 0,
        "Other2Num": 0,
    }
    assert cmds["CMDSAutoPrograms"]["SAM"] == {"Program": 5, "Threshold": 3}
    assert cmds["CMDSAutoOverrides"] == []
    programs = cmds["CMDSProgramSettings"]
    assert [programs[f"PROG_{i}"]["Priority"] for i in range(1, 9)] == [
        2,
        0,
        0,
        0,
        1,
        1,
        0,
        0,
    ]
    assert programs["PROG_1"]["Chaff"] == {
        "BurstQuantity": 2,
        "BurstInterval": 0.2,
        "SalvoQuantity": 8,
        "SalvoInterval": 1,
    }
    assert programs["PROG_5"]["Other2"] == {
        "BurstQuantity": 0,
        "BurstInterval": 0,
        "SalvoQuantity": 0,
        "SalvoInterval": 0,
    }


def test_tomcat_flight_gets_a_cartridge_bound_to_its_clients() -> None:
    flight, mission_data, game = _tomcat_fixture()
    generator = DtcGenerator(Mission(Caucasus()), game, mission_data)
    generator.generate()
    assert len(generator.cartridges) == 1
    cartridge = generator.cartridges[0]
    assert cartridge.unit_type == TOMCAT_UNIT_TYPE
    assert getattr(flight.client_units[0], "retribution_dtc")["AutoLoad"] is True


def _field_cp(name: str, x: float, y: float, airport_id: str) -> Any:
    cp = _airbase_cp(name, x, y)
    cp.airport = SimpleNamespace(id=airport_id)
    return cp


def test_en_route_elevation_is_the_nearest_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The campaign's only height data is per airfield, so a steerpoint reads
    the nearest one's: an estimate, but closer than 0 everywhere."""
    from game.missiongenerator.kneeboard_recon import airport_imagery

    known = {"kutaisi": 45.0, "senaki": 12.0, "sukhumi": None}
    monkeypatch.setattr(
        airport_imagery,
        "field_elevation_for_airport",
        lambda terrain, airport: known[airport.id],
    )
    game = _game(
        controlpoints=[
            _field_cp("Kutaisi", 0, 0, "kutaisi"),
            _field_cp("Senaki", 60000, 80000, "senaki"),
            # Nearest to the hold, but with no record: it must not answer 0.
            _field_cp("Sukhumi", 1500, 1500, "sukhumi"),
            _sam_cp(),
        ]
    )
    hold = _waypoint("HOLD", FlightWaypointType.LOITER, 1000, 1000, 6000, None)
    target = _waypoint(
        "TGT", FlightWaypointType.TARGET_POINT, 62000, 84000, 0, None, targets=[1]
    )
    landing = _waypoint("LAND", FlightWaypointType.LANDING_POINT, 0, 0, 33.5, None)
    assert steerpoint_elevation(hold, game) == 45.0
    assert steerpoint_elevation(target, game) == 12.0
    # The fields themselves keep their own exact number.
    assert steerpoint_elevation(landing, game) == 33.5
    # No field with a record anywhere: the honest 0.
    assert steerpoint_elevation(hold, _game(controlpoints=[_sam_cp()])) == 0.0


def test_an_ingress_carrying_the_target_list_is_still_an_ip() -> None:
    """Retribution attaches the target list to the ingress point so the task
    can be built. That must not make it the target on the HSD or the route."""
    flight, mission_data, game = _hornet_fixture()
    flight.waypoints = [
        _waypoint("TAKEOFF", FlightWaypointType.TAKEOFF, 0, 0, 0, None),
        _waypoint(
            "IP", FlightWaypointType.INGRESS_STRIKE, 100, 100, 3000, None, targets=[1]
        ),
        _waypoint(
            "TARGET", FlightWaypointType.TARGET_POINT, 200, 200, 0, None, targets=[1]
        ),
        _waypoint("LANDING", FlightWaypointType.LANDING_POINT, 0, 0, 0, None),
    ]
    route = json.loads(
        build_hornet_cartridge(flight, mission_data, game, "IP").to_json()
    )["data"]["WYPT"]["NAV_ROUTE"][0]
    assert route["STPT1"]["TGT"] is False
    assert route["STPT2"]["TGT"] is True

    flight.aircraft_type = SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-16C_50"))
    nav_pts = json.loads(
        build_viper_cartridge(flight, mission_data, game, "IP").to_json()
    )["data"]["MPD"]["NAV_PTS"]
    assert [p["type"] for p in nav_pts[:3]] == ["IP", "TGT", "STPT"]


def test_a_ground_marked_target_carries_the_ground_as_its_altitude(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Viper's DED shows routeAltitude as the steerpoint ELEV, and nothing
    honours the AGL tag (the editor's transformAltitude is a no-op). A target
    written as "0 AGL" read ELEV 0 in the jet; it now carries the ground
    estimate in MSL, and an AGL-planned leg is converted the same way."""
    from game.missiongenerator.kneeboard_recon import airport_imagery

    monkeypatch.setattr(
        airport_imagery, "field_elevation_for_airport", lambda terrain, airport: 700.0
    )
    flight, mission_data, game = _hornet_fixture()
    game.theater.controlpoints = [_field_cp("Kirkuk", 0, 0, "kirkuk")]
    flight.aircraft_type = SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-16C_50"))
    flight.waypoints = [
        _waypoint("TAKEOFF", FlightWaypointType.TAKEOFF, 0, 0, 0, None),
        _waypoint(
            "LOW",
            FlightWaypointType.INGRESS_STRIKE,
            100,
            100,
            150,
            None,
            alt_type="RADIO",
        ),
        _waypoint(
            "DEAD", FlightWaypointType.TARGET_GROUP_LOC, 200, 200, 0, None, targets=[1]
        ),
        _waypoint("LANDING", FlightWaypointType.LANDING_POINT, 0, 0, 0, None),
    ]
    nav_pts = json.loads(
        build_viper_cartridge(flight, mission_data, game, "DED").to_json()
    )["data"]["MPD"]["NAV_PTS"]
    low, dead = nav_pts[0], nav_pts[1]
    assert dead["routeAltitude"] == pytest.approx(700.0)
    assert dead["altitudeType"] == 1
    assert dead["alt"] == pytest.approx(700.0)
    # 150 m AGL over 700 m ground is written as 850 m MSL.
    assert low["routeAltitude"] == pytest.approx(850.0)
    assert low["altitudeType"] == 1
