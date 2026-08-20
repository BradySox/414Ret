"""What reveals an enemy site, and how completely.

Two rules, both set 2026-08-18, both pinned here:

* **Engagement reveals.** Ordnance on the site, or any ground-attack sortie that
  reached it. A recon/TARPS overflight does NOT -- "hidden until scouted" is the
  rule this replaced.
* **A revealed site is revealed in full.** No BDA confirmation step sits behind
  the reveal; the damage a strike did reads the moment it lands.

Recon's one remaining job is the third block: finding enemy command posts, which are
hidden from the map outright and so cannot be engaged in the first place.

The composition-fog gate itself (``known_for``) is covered in
``test_recon_intel_fog.py``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import uuid4

from dcs.mapping import Point

from game.ato.flighttype import FlightType
from game.debriefing import AirLosses, Debriefing, GroundLosses
from game.sim.missionresultsprocessor import TARPS_POD_RADIUS_NM
from game.sim.gameupdateevents import GameUpdateEvents
from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.theater import Player
from game.theater.controlpoint import OffMapSpawn
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import SamGroundObject
from game.unitmap import TheaterUnitMapping
from game.utils import Heading, meters, nautical_miles


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


def _processor_with_packages(
    *packages: Any, control_points: list[Any] | None = None
) -> MissionResultsProcessor:
    game = SimpleNamespace(
        blue=SimpleNamespace(ato=SimpleNamespace(packages=list(packages))),
        red=SimpleNamespace(ato=SimpleNamespace(packages=[])),
        theater=SimpleNamespace(controlpoints=control_points or []),
        message=lambda title, text: None,
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


# --- Recon's one job: the outright-hidden command posts -------------------------


class FakeCommandPost:
    """The bits reveal_scouted_command_posts touches on a hidden command post."""

    def __init__(
        self,
        *,
        x: float = 0.0,
        hidden: bool = True,
        map_hidden: bool = False,
        category: str = "commandcenter",
    ) -> None:
        self.id = uuid4()
        self.name = "Enemy HQ"
        self.category = category
        self.map_hidden = map_hidden
        self.discovered_by_player = False
        self._hidden = hidden
        self.position = Point(x, 0, None)  # type: ignore[arg-type]
        self.control_point = SimpleNamespace(name="enemy-cp")

    def is_friendly(self, to_player: Player) -> bool:
        return False

    def hidden_on_player_map(self, viewer: Player | None = None) -> bool:
        return self._hidden and not self.discovered_by_player


def _cp_with(*tgos: Any) -> Any:
    return SimpleNamespace(connected_objectives=list(tgos))


def _recon_run(post: Any, *, target_x: float = 0.0, flight_type: Any = None) -> None:
    target = SimpleNamespace(position=Point(target_x, 0, None))  # type: ignore[arg-type]
    package = _package(target, flight_type or FlightType.TARPS)
    processor = _processor_with_packages(package, control_points=[_cp_with(post)])
    processor.reveal_scouted_command_posts(_debrief(), GameUpdateEvents())


def test_recon_finds_a_hidden_command_post() -> None:
    """Without this the site is unreachable: it has no marker, so a hand-planner
    cannot frag anything at it, and engagement is the only other reveal."""
    post = FakeCommandPost()
    _recon_run(post)
    assert post.discovered_by_player


def test_recon_does_not_reach_a_distant_command_post() -> None:
    post = FakeCommandPost(x=nautical_miles(TARPS_POD_RADIUS_NM).meters * 2)
    _recon_run(post)
    assert not post.discovered_by_player


def test_only_a_recon_tasking_finds_one() -> None:
    for flight_type in (FlightType.STRIKE, FlightType.DEAD, FlightType.BAI):
        post = FakeCommandPost()
        _recon_run(post, flight_type=flight_type)
        assert not post.discovered_by_player, flight_type


def test_a_recon_flight_lost_on_the_pass_finds_nothing() -> None:
    post = FakeCommandPost()
    target = SimpleNamespace(position=Point(0, 0, None))  # type: ignore[arg-type]
    processor = _processor_with_packages(
        _package(target, FlightType.TARPS), control_points=[_cp_with(post)]
    )
    debriefing = _debrief()
    debriefing.air_losses = cast(
        Any, SimpleNamespace(surviving_flight_members=lambda flight: 0)
    )
    processor.reveal_scouted_command_posts(debriefing, GameUpdateEvents())
    assert not post.discovered_by_player


def test_ambush_teams_are_never_revealed_by_recon() -> None:
    """§50's map_hidden teams exist to be a surprise in the mission, not on the
    map -- recon must not telegraph them."""
    post = FakeCommandPost(map_hidden=True)
    _recon_run(post)
    assert not post.discovered_by_player


def test_recon_does_not_touch_ordinary_hidden_sites() -> None:
    """A non-command-post site is already on the map; only its composition is
    fogged, and lifting that is engagement's job, not recon's."""
    post = FakeCommandPost(category="aa")
    _recon_run(post)
    assert not post.discovered_by_player
