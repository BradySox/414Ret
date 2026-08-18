"""What reveals an enemy site, and how completely.

Two rules, both set 2026-08-18, both pinned here:

* **Engagement reveals.** Ordnance on the site, or any ground-attack sortie that
  reached it. A recon/TARPS overflight does NOT -- "hidden until scouted" is the
  rule this replaced.
* **A revealed site is revealed in full.** No BDA confirmation step sits behind
  the reveal; the damage a strike did reads the moment it lands.

The composition-fog gate itself (``known_for``) is covered in
``test_recon_intel_fog.py``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
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
    def __init__(self, ground_object: SamGroundObject) -> None:
        self.ground_object = ground_object
        self.alive = True
        self.is_anti_air = True
        self.is_static = False
        self.icon = "missing"
        self.repairable = False
        self.type = SimpleNamespace(id="fake-sam", name="Fake SAM")

    def kill(self, events: GameUpdateEvents) -> None:
        self.alive = False
        self.ground_object.invalidate_threat_poly()
        events.update_tgo(self.ground_object)

    def threat_range(self) -> Any:
        return meters(25_000) if self.alive else meters(0)

    def detection_range(self) -> Any:
        return meters(40_000) if self.alive else meters(0)


class FakeGroup:
    def __init__(self, ground_object: SamGroundObject, unit: FakeUnit) -> None:
        self.ground_object = ground_object
        self.units = [unit]

    @property
    def unit_count(self) -> int:
        return len(self.units)

    def alive_units(self) -> int:
        return sum(unit.alive for unit in self.units)

    def max_threat_range(self, radar_only: bool = False) -> Any:
        return max((unit.threat_range() for unit in self.units), default=meters(0))

    def max_detection_range(self) -> Any:
        return max((unit.detection_range() for unit in self.units), default=meters(0))


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


def _debrief(unit: FakeUnit | None = None) -> Debriefing:
    debriefing = Debriefing.__new__(Debriefing)
    losses = (
        []
        if unit is None
        else [
            TheaterUnitMapping(
                theater_unit=cast(Any, unit), dcs_unit=cast(Any, MagicMock())
            )
        ]
    )
    debriefing.ground_losses = GroundLosses(enemy_ground_objects=losses)
    debriefing.air_losses = AirLosses(player=[], enemy=[])
    return debriefing


def _package(target: Any, flight_type: FlightType) -> Any:
    return SimpleNamespace(
        target=target, flights=[SimpleNamespace(flight_type=flight_type, count=1)]
    )


def test_a_strike_reveals_the_site_and_its_damage_at_once() -> None:
    tgo, unit = _enemy_sam()
    processor = _processor_with_packages()

    processor.commit_ground_losses(_debrief(unit), GameUpdateEvents())

    assert tgo.discovered_by_player
    # Nothing lags behind the reveal: the kill reads immediately, from any angle.
    assert not unit.alive
    assert tgo.is_dead()
    assert tgo.max_threat_range() == meters(0)


def test_an_offensive_sortie_reveals_the_site_with_no_kills() -> None:
    tgo, _ = _enemy_sam()
    processor = _processor_with_packages(_package(tgo, FlightType.STRIKE))

    processor.commit_ground_losses(_debrief(), GameUpdateEvents())

    assert tgo.discovered_by_player


def test_every_ground_attack_task_reveals() -> None:
    """A task missing from the offensive set would be a site the player could
    never learn about short of destroying it -- recon no longer covers the gap."""
    for flight_type in (
        FlightType.DEAD,
        FlightType.SEAD,
        FlightType.SEAD_SWEEP,
        FlightType.SEAD_ESCORT,
        FlightType.ANTISHIP,
        FlightType.BAI,
        FlightType.CAS,
        FlightType.ARMED_RECON,
    ):
        tgo, _ = _enemy_sam()
        processor = _processor_with_packages(_package(tgo, flight_type))
        processor.commit_ground_losses(_debrief(), GameUpdateEvents())
        assert tgo.discovered_by_player, flight_type


def test_recon_overflight_does_not_reveal() -> None:
    """The point of the rework: scouting is not a reveal key."""
    tgo, _ = _enemy_sam()
    processor = _processor_with_packages(_package(tgo, FlightType.TARPS))

    processor.commit_ground_losses(_debrief(), GameUpdateEvents())

    assert not tgo.discovered_by_player


def test_a_flight_that_did_not_come_home_reveals_nothing() -> None:
    tgo, _ = _enemy_sam()
    processor = _processor_with_packages(_package(tgo, FlightType.STRIKE))
    debriefing = _debrief()
    debriefing.air_losses = cast(
        Any, SimpleNamespace(surviving_flight_members=lambda flight: 0)
    )

    processor.commit_ground_losses(debriefing, GameUpdateEvents())

    assert not tgo.discovered_by_player
