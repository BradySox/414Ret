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
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

import pytest
from dcs.mission import Mission
from dcs.planes import FA_18C_hornet
from dcs.terrain import Caucasus

from game.ato.dtcoptions import DtcOptions
from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.dtc import DtcGenerator
from game.missiongenerator.dtc.cartridge import (
    DtcCartridge,
    append_cartridges_to_miz,
    attach_cartridge_to_unit,
)
from game.missiongenerator.dtc.common import (
    known_enemy_threat_sites,
    sanitize_short_name,
    seconds_of_day,
)
from game.missiongenerator.dtc.generator import CARTRIDGE_BUILDERS
from game.missiongenerator.dtc.hornet import build_hornet_cartridge
from game.missiongenerator.dtc.viper import build_viper_cartridge


class Pt:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def distance_to_point(self, other: "Pt") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


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
            conflicts=lambda: [],
            controlpoints=controlpoints or [],
        ),
    )


@pytest.fixture(autouse=True)
def _no_restricted_zones(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "game.fourteenth.phases.active_restricted_zones", lambda game: []
    )


def _sam_cp(*, known: bool = True, hidden: bool = False) -> Any:
    tgo = SimpleNamespace(
        name="SAM SA-2 Site",
        category="aa",
        map_hidden=hidden,
        known_for=lambda viewer: known,
        max_threat_range=lambda viewer: SimpleNamespace(meters=43000.0),
        position=Pt(120000, -30000),
        groups=[SimpleNamespace(units=[SimpleNamespace(type="SA-2 launcher")])],
    )
    return SimpleNamespace(captured=SimpleNamespace(is_red=True), ground_objects=[tgo])


def test_channel_names_pass_the_dtc_filter() -> None:
    assert sanitize_short_name("CVN-71") == "CVN71"
    assert sanitize_short_name("Overlord 1-1") == "OVERL"
    assert sanitize_short_name("Arco") == "ARCO"


def test_eta_is_seconds_since_midnight() -> None:
    game = _game()
    assert seconds_of_day(game, datetime(1988, 7, 15, 7, 19, 13)) == 26353
    assert seconds_of_day(game, None) == 0


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

    # Waypoints: numbered, named, on route 1 in order.
    nav_pts = data["WYPT"]["NAV_PTS"]
    assert [w["wypt_num"] for w in nav_pts] == [1, 2, 3]
    assert [w["text_note"] for w in nav_pts] == ["TAKEOFF", "TARGET", "LANDING"]
    assert all(w["R1"] for w in nav_pts)
    assert [w["R1_order"] for w in nav_pts] == [1, 2, 3]

    # Route sequence: ETA absolute seconds, target flagged, routes 2/3 empty.
    route = data["WYPT"]["NAV_ROUTE"]
    assert route[1] == [] and route[2] == []
    assert route[0]["STPT2"]["ETA"] == 7 * 3600 + 30 * 60
    assert route[0]["STPT2"]["TGT"] is True
    assert route[0]["STPT1"]["TGT"] is False

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
    assert nav_settings["Home_Waypoint"] == {"FPAS_HOME_WP": 3}

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

    # SA: CAP + tanker racetracks, the SAM ring, styles visible.
    caps = data["SA"]["CAP_PTS"]
    assert [c["note"] for c in caps] == ["COLT", "ARCO"]
    assert caps[0]["id"] == "CAP_PTS_1"
    assert caps[0]["course"] == pytest.approx(90.0)  # along +y = east
    assert caps[1]["course"] == pytest.approx(0.0)  # along +x = north
    assert caps[1]["length"] == pytest.approx(20000.0)
    mez = data["SA"]["MEZ_THRTS"]
    assert len(mez) == 1
    assert mez[0]["threat_type"] == "Custom"
    assert mez[0]["text"] == "2"
    assert mez[0]["threat_ring_radius"] == pytest.approx(23.2)
    assert data["SA"]["Default_FLOT_Line"] == 1


def test_viper_cartridge_shape() -> None:
    flight, mission_data, game = _hornet_fixture()
    flight.aircraft_type = SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-16C_50"))
    cartridge = build_viper_cartridge(flight, mission_data, game, "Test F-16C")
    data = json.loads(cartridge.to_json())["data"]

    nav_pts = data["MPD"]["NAV_PTS"]
    # Route first, then the tanker + CAP anchors as extra steerpoints.
    assert [p["note"] for p in nav_pts] == [
        "TAKEOFF",
        "TARGET",
        "LANDING",
        "TKR ARCO",
        "CAP COLT",
    ]
    assert nav_pts[1]["TOS"] == 7 * 3600 + 30 * 60
    assert nav_pts[1]["isTOSEnabled"] is True
    assert nav_pts[3]["R1"] is False

    threat = data["MPD"]["THREAT_PTS"]
    assert len(threat) == 1
    assert threat[0]["threatName"] == "Custom"
    assert threat[0]["radius"] == pytest.approx(43000.0)
    assert threat[0]["id"] == "THREAT_PTS56"

    comm1 = data["COMM"]["COMM1"]
    assert comm1["Channel_2"] == {"freq": 251.0, "modulation": 1}
    assert "name" not in comm1["Channel_1"]


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
    assert len(data["WYPT"]["NAV_PTS"]) == 3
    assert data["WYPT"]["NAV_SETTINGS"]["TACAN"]["OnOff"] is False


def test_viper_sections_are_omitted_when_off() -> None:
    flight, mission_data, game = _hornet_fixture()
    flight.aircraft_type = SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-16C_50"))
    flight.dtc_options = DtcOptions(comms=False, route=False)
    cartridge = build_viper_cartridge(flight, mission_data, game, "Anchors Only")
    data = json.loads(cartridge.to_json())["data"]
    assert "COMM" not in data
    # Route off, friendly orbits on: only the support anchors load.
    assert [p["note"] for p in data["MPD"]["NAV_PTS"]] == ["TKR ARCO", "CAP COLT"]

    flight.dtc_options = DtcOptions(
        comms=False,
        route=False,
        nav_aids=False,
        flot_and_zones=False,
        friendly_orbits=False,
        threat_rings=True,
    )
    cartridge = build_viper_cartridge(flight, mission_data, game, "Threats Only")
    data = json.loads(cartridge.to_json())["data"]
    assert data["MPD"]["NAV_PTS"] == []
    assert data["MPD"]["GEO_LINES"] == []
    assert len(data["MPD"]["THREAT_PTS"]) == 1


def test_old_saves_default_the_flight_options() -> None:
    from game.ato.flight import Flight
    from game.settings import Settings

    flight = object.__new__(Flight)
    state = {"squadron": SimpleNamespace(settings=Settings()), "roster": None}
    flight.__setstate__(state)
    assert isinstance(flight.dtc_options, DtcOptions)
    assert flight.dtc_options.enabled is None
    assert flight.dtc_options.any_content
