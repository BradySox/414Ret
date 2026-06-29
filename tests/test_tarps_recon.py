"""Tests for the F-14 TARPS photo-recon flight type and its target gate.

TARPS is a recon/BDA overflight auto-paired with Strike/DEAD packages. These
tests lock in the two design-critical pieces that are cheap to verify without a
full game fixture: the tight post-strike TOT offset, and the ``warrants_recon``
target gate that decides which targets get a TARPS pass.
"""

from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from dcs.mapping import Point

from game.ato.flighttype import FlightType
from game.ato.package import Package
from game.ato.flightplans.tarps import TarpsFlightPlan
from game.dcs.aircrafttype import AircraftType
from game import persistency
from game.theater.controlpoint import OffMapSpawn, Player
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import (
    BuildingGroundObject,
    EwrGroundObject,
    SamGroundObject,
    TheaterGroundObject,
)
from game.utils import Heading

TOMCAT_VARIANT_IDS: tuple[str, ...] = (
    "F-14A Tomcat (AI)",
    "F-14A Tomcat (Block 135-GR Late)",
    "F-14A Tomcat (Block 135-GR Early)",
    "F-14B Tomcat",
)

# Vietnam-era dedicated photo-recon birds (VWV mod pack). TARPS is their primary
# role — unarmed camera ships, see resources/units/aircraft/vwv_{rf101b,ra-5}.yaml.
VIETNAM_RECON_VARIANT_IDS: tuple[str, ...] = (
    "RF-101B Voodoo",
    "RA-5C Vigilante",
)


def test_tarps_flight_type_is_recon_support() -> None:
    # TARPS is a non-combat recon role: neither air-to-air nor air-to-ground.
    assert not FlightType.TARPS.is_air_to_air
    assert not FlightType.TARPS.is_air_to_ground
    assert FlightType.TARPS.is_primary_package_task
    assert FlightType.TARPS.entity_type.name == "RECONNAISSANCE"


def test_tarps_tot_offset_is_post_strike() -> None:
    # The whole point of the feature: overfly the target a short hop behind the
    # strikers for a post-strike BDA pass. Kept tight (2 min, not 5) so the
    # unarmed recon bird ingresses within the package's escort window instead of
    # trailing in alone where MiGs pick it off (checklist G19). Still strictly
    # post-strike (positive offset).
    plan = object.__new__(TarpsFlightPlan)
    offset = plan.default_tot_offset()
    assert offset == timedelta(minutes=2)
    assert offset > timedelta(0)


def test_tarps_only_package_identifies_tarps_as_primary_task() -> None:
    package = Package(target=MagicMock(), db=MagicMock())
    package.flights.append(MagicMock(flight_type=FlightType.TARPS))
    assert package.primary_task is FlightType.TARPS


@pytest.mark.parametrize(
    "variant_id",
    TOMCAT_VARIANT_IDS,
)
def test_all_tomcat_variants_can_plan_tarps(variant_id: str, tmp_path: Path) -> None:
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16880)
    assert AircraftType.named(variant_id).capable_of(FlightType.TARPS)


@pytest.mark.parametrize("variant_id", VIETNAM_RECON_VARIANT_IDS)
def test_vietnam_recon_planes_can_plan_tarps(variant_id: str, tmp_path: Path) -> None:
    # The Vietnam-era recon birds were extended from the F-14 to fly TARPS too, so
    # the auto-planner can pair them with Strike/DEAD packages in period campaigns.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16880)
    assert AircraftType.named(variant_id).capable_of(FlightType.TARPS)


@pytest.mark.parametrize("variant_id", VIETNAM_RECON_VARIANT_IDS)
def test_vietnam_recon_planes_are_tarps_only(variant_id: str, tmp_path: Path) -> None:
    # These are UNARMED photo birds (weaponless loadout). The planner must never
    # task them to attack or escort -- they'd spawn empty and fly an aborting
    # pattern. Guards against re-adding combat tasks to their YAMLs, which (via the
    # ARMED_RECON enrich on CAS/BAI) is what put them on Armed Recon. See G19.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16880)
    bird = AircraftType.named(variant_id)
    for task in (
        FlightType.ARMED_RECON,
        FlightType.STRIKE,
        FlightType.CAS,
        FlightType.BAI,
        FlightType.BARCAP,
        FlightType.ESCORT,
    ):
        assert not bird.capable_of(task), f"{variant_id} should not be {task}"


@pytest.mark.parametrize("variant_id", TOMCAT_VARIANT_IDS)
def test_tomcats_do_not_plan_sead_or_sead_sweep(
    variant_id: str, tmp_path: Path
) -> None:
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16880)
    tomcat = AircraftType.named(variant_id)
    assert not tomcat.capable_of(FlightType.SEAD)
    assert not tomcat.capable_of(FlightType.SEAD_SWEEP)


@pytest.fixture
def enemy_objects(monkeypatch: pytest.MonkeyPatch) -> Any:
    location = PresetLocation(
        name="loc", position=Point(0, 0, None), heading=Heading(0)  # type: ignore
    )
    control_point = OffMapSpawn(
        name="cp",
        position=Point(0, 0, None),  # type: ignore
        theater=None,  # type: ignore
        starts_blue=Player.BLUE,
    )
    # Treat every target as enemy so mission_types yields the offensive set.
    # (The TGO's own is_friendly is what mission_types calls; patching it here
    # avoids needing a fully-initialized ControlPoint/coalition.)
    monkeypatch.setattr(TheaterGroundObject, "is_friendly", lambda self, player: False)
    return location, control_point


def _building(location: Any, control_point: Any, category: str) -> BuildingGroundObject:
    return BuildingGroundObject(
        name="test",
        category=category,
        location=location,
        control_point=control_point,
        task=None,
    )


def test_air_defenses_warrant_recon(enemy_objects: Any) -> None:
    location, control_point = enemy_objects

    sam = SamGroundObject(
        name="sam", location=location, control_point=control_point, task=None
    )
    assert sam.warrants_recon
    assert FlightType.TARPS in list(sam.mission_types(for_player=Player.RED))

    ewr = EwrGroundObject(name="ewr", location=location, control_point=control_point)
    assert ewr.warrants_recon
    assert FlightType.TARPS in list(ewr.mission_types(for_player=Player.RED))


@pytest.mark.parametrize("category", ["factory", "commandcenter"])
def test_strategic_buildings_warrant_recon(enemy_objects: Any, category: str) -> None:
    location, control_point = enemy_objects
    building = _building(location, control_point, category)
    assert building.warrants_recon
    assert FlightType.TARPS in list(building.mission_types(for_player=Player.RED))


@pytest.mark.parametrize("category", ["ammo", "fuel", "ware", "power"])
def test_mundane_buildings_do_not_warrant_recon(
    enemy_objects: Any, category: str
) -> None:
    location, control_point = enemy_objects
    building = _building(location, control_point, category)
    # No strategic category and no scenery units -> not worth a recon pass.
    assert not building.warrants_recon
    assert FlightType.TARPS not in list(building.mission_types(for_player=Player.RED))
