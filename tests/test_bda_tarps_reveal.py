from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional, cast
from unittest.mock import MagicMock

from dcs.mapping import Point

from game.ato.flighttype import FlightType
from game.debriefing import AirLosses, Debriefing, GroundLosses
from game.sim.gameupdateevents import GameUpdateEvents
from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.theater import Player
from game.theater.controlpoint import OffMapSpawn
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import SamGroundObject
from game.unitmap import TheaterUnitMapping
from game.utils import Heading, meters


class FakeUnit:
    def __init__(
        self,
        ground_object: SamGroundObject,
        *,
        alive: bool = True,
        alive_at_last_recon: bool = True,
        threat_meters: int = 25_000,
        detection_meters: int = 40_000,
    ) -> None:
        self.ground_object = ground_object
        self.alive = alive
        self.alive_at_last_recon = alive_at_last_recon
        self.threat_meters = threat_meters
        self.detection_meters = detection_meters
        self.is_anti_air = True
        self.is_static = False
        self.icon = "missing"
        self.repairable = False
        self.type = SimpleNamespace(id="fake-sam", name="Fake SAM")

    def kill(self, events: GameUpdateEvents) -> None:
        self.alive = False
        self.ground_object.invalidate_threat_poly()
        events.update_tgo(self.ground_object)

    def sync_confirmed_status(self) -> None:
        self.alive_at_last_recon = self.alive

    def alive_for(self, viewer: Optional[Player] = None) -> bool:
        if viewer is None or self.ground_object.is_friendly(viewer):
            return self.alive
        return self.alive_at_last_recon

    def display_name_for(self, viewer: Optional[Player] = None) -> str:
        suffix = " [DEAD]" if not self.alive_for(viewer) else ""
        return f"0001 | Fake SAM{suffix}"

    def short_name_for(self, viewer: Optional[Player] = None) -> str:
        suffix = " [DEAD]" if not self.alive_for(viewer) else ""
        return f"<b>Fake SAM</b>{suffix}"

    def threat_range(self, viewer: Optional[Player] = None) -> Any:
        if not self.alive_for(viewer):
            return meters(0)
        return meters(self.threat_meters)

    def detection_range(self, viewer: Optional[Player] = None) -> Any:
        if not self.alive_for(viewer):
            return meters(0)
        return meters(self.detection_meters)


class FakeGroup:
    def __init__(self, ground_object: SamGroundObject, unit: FakeUnit) -> None:
        self.ground_object = ground_object
        self.units = [unit]

    @property
    def unit_count(self) -> int:
        return len(self.units)

    def alive_units(self, viewer: Optional[Player] = None) -> int:
        return sum(unit.alive_for(viewer) for unit in self.units)

    def max_threat_range(
        self, viewer: Optional[Player] = None, radar_only: bool = False
    ) -> Any:
        return max(
            (unit.threat_range(viewer) for unit in self.units),
            default=meters(0),
        )

    def max_detection_range(self, viewer: Optional[Player] = None) -> Any:
        return max(
            (unit.detection_range(viewer) for unit in self.units),
            default=meters(0),
        )


class EnemySamGroundObject(SamGroundObject):
    def is_friendly(self, to_player: Player) -> bool:
        return False


def _enemy_sam() -> tuple[SamGroundObject, FakeUnit]:
    location = PresetLocation(
        name="target",
        position=Point(0, 0, None),  # type: ignore[arg-type]
        heading=Heading(0),
    )
    control_point = OffMapSpawn(
        name="enemy-cp",
        position=Point(0, 0, None),  # type: ignore[arg-type]
        theater=None,  # type: ignore[arg-type]
        starts_blue=Player.RED,
    )
    tgo = EnemySamGroundObject(
        name="Enemy SAM",
        location=location,
        control_point=control_point,
        task=None,
    )
    unit = FakeUnit(tgo)
    tgo.groups = cast(Any, [FakeGroup(tgo, unit)])
    return tgo, unit


def _processor_with_packages(*packages: Any) -> MissionResultsProcessor:
    game = SimpleNamespace(
        blue=SimpleNamespace(ato=SimpleNamespace(packages=list(packages))),
        red=SimpleNamespace(ato=SimpleNamespace(packages=[])),
    )
    return MissionResultsProcessor(game)  # type: ignore[arg-type]


def _debrief_with_ground_loss(
    unit: FakeUnit, air_losses: AirLosses | None = None
) -> Debriefing:
    debriefing = Debriefing.__new__(Debriefing)
    debriefing.ground_losses = GroundLosses(
        enemy_ground_objects=[
            TheaterUnitMapping(
                theater_unit=cast(Any, unit), dcs_unit=cast(Any, MagicMock())
            ),
        ]
    )
    debriefing.air_losses = air_losses or AirLosses(player=[], enemy=[])
    return debriefing


def test_enemy_damage_stays_hidden_without_tarps_recon() -> None:
    tgo, unit = _enemy_sam()
    processor = _processor_with_packages()
    debriefing = _debrief_with_ground_loss(unit)

    processor.commit_ground_losses(debriefing, GameUpdateEvents())

    assert not unit.alive
    assert unit.alive_at_last_recon
    assert tgo.is_dead()
    assert not tgo.is_dead(Player.BLUE)
    assert tgo.max_threat_range(Player.BLUE) > meters(0)
    # Recon intel-fog: attacking the site (units destroyed) reveals it permanently.
    assert tgo.discovered_by_player


def test_surviving_tarps_reveals_true_enemy_damage() -> None:
    tgo, unit = _enemy_sam()
    tarps_flight = SimpleNamespace(flight_type=FlightType.TARPS, count=1)
    tarps_package = SimpleNamespace(target=tgo, flights=[tarps_flight])
    processor = _processor_with_packages(tarps_package)
    debriefing = _debrief_with_ground_loss(unit, AirLosses(player=[], enemy=[]))

    processor.commit_ground_losses(debriefing, GameUpdateEvents())

    assert not unit.alive
    assert not unit.alive_at_last_recon
    assert tgo.is_dead(Player.BLUE)
    assert tgo.max_threat_range(Player.BLUE) == meters(0)
