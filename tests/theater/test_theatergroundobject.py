from types import SimpleNamespace
from typing import Any

import pytest
from dcs.mapping import Point

from game.ato.flighttype import FlightType
from game.sidc import StandardIdentity, Status
from game.theater.controlpoint import OffMapSpawn, Player
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import (
    BuildingGroundObject,
    CarrierGroundObject,
    LhaGroundObject,
    MissileSiteGroundObject,
    CoastalSiteGroundObject,
    SamGroundObject,
    VehicleGroupGroundObject,
    EwrGroundObject,
    ShipGroundObject,
    IadsBuildingGroundObject,
    TheaterGroundObject,
)
from game.utils import Heading


def test_mission_types_friendly(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test the mission types that can be planned against friendly Theater Ground Objects
    """
    # Set up dummy inputs
    dummy_location = PresetLocation(
        name="dummy_location", position=Point(0, 0, None), heading=Heading(0)  # type: ignore
    )
    dummy_control_point = OffMapSpawn(
        name="dummy_control_point",
        position=Point(0, 0, None),  # type: ignore
        theater=None,  # type: ignore
        starts_blue=Player.BLUE,
    )

    # Patch is_friendly as it's difficult to set up a proper ControlPoint.
    # mission_types calls self.is_friendly on the TGO, so patch it there.
    monkeypatch.setattr(TheaterGroundObject, "is_friendly", lambda self, player: True)

    # These constructors no longer take a `task` argument (Carrier/LHA/Ship and
    # the missile/coastal/EWR sites hard-code their own GroupTask); SAM and the
    # vehicle group still do. Build each with its real signature.
    ground_objects = [
        CarrierGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
        LhaGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
        MissileSiteGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
        CoastalSiteGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
        SamGroundObject(
            name="test",
            location=dummy_location,
            control_point=dummy_control_point,
            task=None,
        ),
        VehicleGroupGroundObject(
            name="test",
            location=dummy_location,
            control_point=dummy_control_point,
            task=None,
        ),
        EwrGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
        ShipGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
    ]
    for ground_object in ground_objects:
        mission_types = list(ground_object.mission_types(for_player=Player.BLUE))
        assert mission_types == [FlightType.BARCAP]

    for ground_object_type in [BuildingGroundObject, IadsBuildingGroundObject]:
        ground_object = ground_object_type(
            name="test",
            category="ammo",
            location=dummy_location,
            control_point=dummy_control_point,
            task=None,
        )
        mission_types = list(ground_object.mission_types(for_player=Player.BLUE))
        assert mission_types == [FlightType.BARCAP]


def test_mission_types_enemy(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test the mission types that can be planned against enemy Theater Ground Objects
    """
    # Set up dummy inputs
    dummy_location = PresetLocation(
        name="dummy_location", position=Point(0, 0, None), heading=Heading(0)  # type: ignore
    )
    dummy_control_point = OffMapSpawn(
        name="dummy_control_point",
        position=Point(0, 0, None),  # type: ignore
        theater=None,  # type: ignore
        starts_blue=Player.BLUE,
    )

    # Patch is_friendly as it's difficult to set up a proper ControlPoint.
    # mission_types calls self.is_friendly on the TGO, so patch it there.
    monkeypatch.setattr(TheaterGroundObject, "is_friendly", lambda self, player: False)

    # Strategic-recon gate: air defenses (SAM/EWR/IADS) get a TARPS BDA pass;
    # mundane targets (ammo dumps, armor, ships, missile/coastal sites) do not.
    building = BuildingGroundObject(
        name="test",
        category="ammo",
        location=dummy_location,
        control_point=dummy_control_point,
        task=None,
    )
    mission_types = list(building.mission_types(for_player=Player.RED))
    assert len(mission_types) == 9
    assert FlightType.STRIKE in mission_types
    assert FlightType.REFUELING in mission_types
    assert FlightType.ESCORT in mission_types
    assert FlightType.TARCAP in mission_types
    assert FlightType.SEAD_ESCORT in mission_types
    assert FlightType.SEAD_SWEEP in mission_types
    assert FlightType.ARMED_RECON in mission_types
    # SCAR is the "Sandy" rescue-escort now, scoped to the FLOT -- generic ground
    # targets (an ammo dump here) no longer expose it (rescue rework).
    assert FlightType.SCAR not in mission_types
    assert FlightType.SWEEP in mission_types
    assert FlightType.JAMMING in mission_types
    assert FlightType.TARPS not in mission_types  # ammo does not warrant recon

    iads_building = IadsBuildingGroundObject(
        name="test",
        category="ammo",
        location=dummy_location,
        control_point=dummy_control_point,
        task=None,
    )
    mission_types = list(iads_building.mission_types(for_player=Player.RED))
    assert len(mission_types) == 10
    assert FlightType.STRIKE in mission_types
    assert FlightType.DEAD in mission_types
    assert FlightType.REFUELING in mission_types
    assert FlightType.ESCORT in mission_types
    assert FlightType.TARCAP in mission_types
    assert FlightType.SEAD_ESCORT in mission_types
    assert FlightType.SEAD_SWEEP in mission_types
    assert FlightType.ARMED_RECON in mission_types
    assert FlightType.SCAR not in mission_types
    assert FlightType.SWEEP in mission_types
    assert FlightType.JAMMING in mission_types
    assert FlightType.TARPS not in mission_types  # ammo does not warrant recon

    ground_object: TheaterGroundObject
    naval_objects = [
        CarrierGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
        LhaGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
        ShipGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
    ]
    for ground_object in naval_objects:
        mission_types = list(ground_object.mission_types(for_player=Player.RED))
        assert len(mission_types) == 11
        assert FlightType.ANTISHIP in mission_types
        assert FlightType.SEAD in mission_types
        assert FlightType.STRIKE in mission_types
        assert FlightType.REFUELING in mission_types
        assert FlightType.ESCORT in mission_types
        assert FlightType.TARCAP in mission_types
        assert FlightType.SEAD_ESCORT in mission_types
        assert FlightType.SEAD_SWEEP in mission_types
        assert FlightType.ARMED_RECON in mission_types
        assert FlightType.SCAR not in mission_types
        assert FlightType.SWEEP in mission_types
        assert FlightType.JAMMING in mission_types
        assert FlightType.TARPS not in mission_types

    sam = SamGroundObject(
        name="test",
        location=dummy_location,
        control_point=dummy_control_point,
        task=None,
    )
    mission_types = list(sam.mission_types(for_player=Player.RED))
    assert len(mission_types) == 12
    assert FlightType.DEAD in mission_types
    assert FlightType.SEAD in mission_types
    assert FlightType.STRIKE in mission_types
    assert FlightType.REFUELING in mission_types
    assert FlightType.TARPS in mission_types  # +TARPS: air defenses warrant recon
    assert FlightType.ESCORT in mission_types
    assert FlightType.TARCAP in mission_types
    assert FlightType.SEAD_ESCORT in mission_types
    assert FlightType.SEAD_SWEEP in mission_types
    assert FlightType.ARMED_RECON in mission_types
    assert FlightType.SCAR not in mission_types
    assert FlightType.SWEEP in mission_types
    assert FlightType.JAMMING in mission_types

    ewr = EwrGroundObject(
        name="test",
        location=dummy_location,
        control_point=dummy_control_point,
    )
    mission_types = list(ewr.mission_types(for_player=Player.RED))
    assert len(mission_types) == 11
    assert FlightType.DEAD in mission_types
    assert FlightType.STRIKE in mission_types
    assert FlightType.REFUELING in mission_types
    assert FlightType.TARPS in mission_types  # +TARPS: air defenses warrant recon
    assert FlightType.ESCORT in mission_types
    assert FlightType.TARCAP in mission_types
    assert FlightType.SEAD_ESCORT in mission_types
    assert FlightType.SEAD_SWEEP in mission_types
    assert FlightType.ARMED_RECON in mission_types
    assert FlightType.SCAR not in mission_types
    assert FlightType.SWEEP in mission_types
    assert FlightType.JAMMING in mission_types

    site_objects = [
        CoastalSiteGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
        MissileSiteGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
    ]
    for ground_object in site_objects:
        mission_types = list(ground_object.mission_types(for_player=Player.RED))
        assert len(mission_types) == 10
        assert FlightType.BAI in mission_types
        assert FlightType.STRIKE in mission_types
        assert FlightType.REFUELING in mission_types
        assert FlightType.ESCORT in mission_types
        assert FlightType.TARCAP in mission_types
        assert FlightType.SEAD_ESCORT in mission_types
        assert FlightType.SEAD_SWEEP in mission_types
        assert FlightType.ARMED_RECON in mission_types
        assert FlightType.SCAR not in mission_types
        assert FlightType.SWEEP in mission_types
        assert FlightType.JAMMING in mission_types
        assert FlightType.TARPS not in mission_types

    vehicles = VehicleGroupGroundObject(
        name="test",
        location=dummy_location,
        control_point=dummy_control_point,
        task=None,
    )
    mission_types = list(vehicles.mission_types(for_player=Player.RED))
    assert len(mission_types) == 10
    assert FlightType.BAI in mission_types
    assert FlightType.STRIKE in mission_types
    assert FlightType.REFUELING in mission_types
    assert FlightType.ESCORT in mission_types
    assert FlightType.TARCAP in mission_types
    assert FlightType.SEAD_ESCORT in mission_types
    assert FlightType.SEAD_SWEEP in mission_types
    assert FlightType.ARMED_RECON in mission_types
    assert FlightType.SCAR not in mission_types
    assert FlightType.SWEEP in mission_types
    assert FlightType.JAMMING in mission_types
    assert FlightType.TARPS not in mission_types


def _vehicle_group_tgo(monkeypatch: pytest.MonkeyPatch) -> VehicleGroupGroundObject:
    # standard_identity + sidc_status_for read control_point.captured (needs a live
    # coalition, awkward to build here). Patch both — neither the identity digit nor
    # the status digit is what these SIDC tests assert on (symbol set / entity only).
    monkeypatch.setattr(
        TheaterGroundObject,
        "standard_identity",
        property(lambda self: StandardIdentity.HOSTILE_FAKER),
    )
    monkeypatch.setattr(
        TheaterGroundObject,
        "sidc_status_for",
        lambda self, viewer=None: Status.PRESENT,
    )
    dummy_location = PresetLocation(
        name="dummy_location", position=Point(0, 0, None), heading=Heading(0)  # type: ignore
    )
    dummy_control_point = OffMapSpawn(
        name="dummy_control_point",
        position=Point(0, 0, None),  # type: ignore
        theater=None,  # type: ignore
        starts_blue=Player.BLUE,
    )
    return VehicleGroupGroundObject(
        name="test",
        location=dummy_location,
        control_point=dummy_control_point,
        task=None,
    )


def test_sidc_entity_override_repoints_the_map_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The COIN layer spawns cells / IEDs / HVTs as vehicle groups but re-points their
    map symbol via ``sidc_entity_override`` so they don't all render as tank platoons.
    Guards the real serialization path (``sidc_for`` -> the SIDC string sent to the
    client) against a regression in the shipped ``coin.py`` symbol constants.
    """
    from game.fourteenth.coin import CELL_SIDC, HVT_SIDC, IED_SIDC

    # The SIDC string is positional: symbol set at [4:6], entity at [10:16].
    tgo = _vehicle_group_tgo(monkeypatch)
    default = str(tgo.sidc_for(None))
    assert default[4:6] == "10"  # LAND_UNIT
    assert default[10:16] == "120500"  # ARMOR — the vehicle-group class default

    tgo.sidc_entity_override = CELL_SIDC
    cell = str(tgo.sidc_for(None))
    assert cell[4:6] == "10"  # LAND_UNIT
    assert cell[10:16] == "121100"  # INFANTRY

    tgo.sidc_entity_override = IED_SIDC
    ied = str(tgo.sidc_for(None))
    assert ied[4:6] == "40"  # ACTIVITY_EVENT
    assert ied[10:16] == "110300"  # IED

    tgo.sidc_entity_override = HVT_SIDC
    hvt = str(tgo.sidc_for(None))
    assert hvt[4:6] == "27"  # DISMOUNTED_INDIVIDUAL
    assert hvt[10:16] == "110220"  # individual leader


def test_sidc_override_absent_on_old_saves_falls_back_to_class_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A pre-feature pickle has no ``sidc_entity_override``; ``__setstate__`` heals it
    to ``None`` and the symbol falls back to the vehicle-group class default."""
    tgo = _vehicle_group_tgo(monkeypatch)
    state = tgo.__getstate__()
    del state["sidc_entity_override"]
    tgo.__setstate__(state)
    assert tgo.sidc_entity_override is None
    assert str(tgo.sidc_for(None))[10:16] == "120500"  # ARMOR


def test_sidc_identity_suspect_until_reconned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """COIN "suspect until reconned": an insurgent contact (carrying a map-symbol
    override, coin_insurgency on) the player hasn't discovered reads as SUSPECT
    (identity digit 5), flipping to HOSTILE (6) once reconned. Ground truth
    (viewer=None, the AI/planner) is never fogged. Identity digit is at SIDC[3:4]."""
    from game.fourteenth.coin import CELL_SIDC

    tgo = _vehicle_group_tgo(monkeypatch)
    settings = SimpleNamespace(coin_insurgency=True)
    cp: Any = tgo.control_point
    cp._coalition = SimpleNamespace(game=SimpleNamespace(settings=settings))
    tgo.sidc_entity_override = CELL_SIDC

    # Un-reconned -> SUSPECT to the human; ground truth stays confirmed HOSTILE.
    monkeypatch.setattr(
        TheaterGroundObject, "known_for", lambda self, viewer=None: False
    )
    assert str(tgo.sidc_for(Player.BLUE))[3:4] == "5"  # SUSPECT_JOKER
    assert str(tgo.sidc_for(None))[3:4] == "6"  # HOSTILE_FAKER (AI never fogged)

    # Reconned -> flips to HOSTILE.
    monkeypatch.setattr(
        TheaterGroundObject, "known_for", lambda self, viewer=None: True
    )
    assert str(tgo.sidc_for(Player.BLUE))[3:4] == "6"

    # No override (a non-COIN contact) is never suspect, even un-reconned.
    monkeypatch.setattr(
        TheaterGroundObject, "known_for", lambda self, viewer=None: False
    )
    tgo.sidc_entity_override = None
    assert str(tgo.sidc_for(Player.BLUE))[3:4] == "6"

    # COIN-scoped: with coin_insurgency off, an override alone doesn't fog affiliation.
    tgo.sidc_entity_override = CELL_SIDC
    settings.coin_insurgency = False
    assert str(tgo.sidc_for(Player.BLUE))[3:4] == "6"


def test_sof_insert_is_never_offered(monkeypatch: pytest.MonkeyPatch) -> None:
    """The SOF capture economy was removed 2026-07-01: no target offers a SOF
    insert any more ("SOF Insert" isn't even a live FlightType value)."""
    dummy_location = PresetLocation(
        name="dummy_location", position=Point(0, 0, None), heading=Heading(0)  # type: ignore
    )
    dummy_control_point = OffMapSpawn(
        name="dummy_control_point",
        position=Point(0, 0, None),  # type: ignore
        theater=None,  # type: ignore
        starts_blue=Player.BLUE,
    )
    monkeypatch.setattr(TheaterGroundObject, "is_friendly", lambda self, player: False)

    building = BuildingGroundObject(
        name="test",
        category="ammo",
        location=dummy_location,
        control_point=dummy_control_point,
        task=None,
    )
    mission_types = list(building.mission_types(for_player=Player.RED))
    assert "SOF Insert" not in [task.value for task in mission_types]


def test_faction_color_follows_the_owning_player() -> None:
    """captured is the Player enum -- truthiness made every TGO read BLUE."""
    from game.theater.theatergroundobject import TheaterGroundObject

    fget = TheaterGroundObject.faction_color.fget
    assert fget is not None
    red = SimpleNamespace(control_point=SimpleNamespace(captured=Player.RED))
    blue = SimpleNamespace(control_point=SimpleNamespace(captured=Player.BLUE))
    assert fget(red) == "RED"
    assert fget(blue) == "BLUE"
