"""§77 sea-supply convoys + coastal anti-ship engagement.

Part 1 -- a sea shipment sails as a CONVOY of cargo ships whose cargo is partitioned
across the hulls, so sinking k of N hulls denies proportionally k/N of the reinforcement
(and the feature-off / one-unit path is the legacy single-hull all-or-nothing loss).

Part 2 -- coastal anti-ship batteries are set weapons-free + red alarm so they actually
fire on passing enemy ships (only when the setting is on, and only for coastal sites).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from dcs.task import OptAlarmState, OptROE

from game.missiongenerator.cargoshipgenerator import CargoShipGenerator, UNITS_PER_SHIP
from game.missiongenerator.tgogenerator import GroundObjectGenerator
from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.theater.player import Player
from game.theater.theatergroundobject import (
    CoastalSiteGroundObject,
    MissileSiteGroundObject,
)
from game.transfers import CargoShip, TransferOrder
from game.unitmap import CargoShipUnit


def _cp(name: str) -> SimpleNamespace:
    return SimpleNamespace(
        position=SimpleNamespace(x=0.0, y=0.0), captured=Player.RED, name=name
    )


def _ship(units: dict[str, int]) -> CargoShip:
    origin, dest = _cp("Bandar Abbas"), _cp("Qeshm")
    ship = CargoShip(origin, dest)  # type: ignore[arg-type]
    ship.add_units(TransferOrder(origin, dest, dict(units)))  # type: ignore[arg-type]
    return ship


def _generator(convoys: bool = True, cap: int = 5) -> CargoShipGenerator:
    gen = object.__new__(CargoShipGenerator)
    settings = SimpleNamespace(cargo_ship_convoys=convoys, cargo_ship_convoy_max=cap)
    setattr(gen, "game", SimpleNamespace(settings=settings))
    return gen


def _total(manifests: Any) -> int:
    return sum(count for manifest in manifests for _, count in manifest)


# ---- Part 1: convoy partitioning -------------------------------------------------


def test_shipment_spreads_across_multiple_hulls() -> None:
    manifests = _generator()._manifests_for(_ship({"T-72": 4, "BMP-2": 2}))
    # 6 units at ~2/ship -> 3 hulls, cargo conserved.
    assert len(manifests) == 3
    assert _total(manifests) == 6


def test_convoy_is_capped() -> None:
    manifests = _generator(cap=5)._manifests_for(_ship({"T-72": 20}))
    assert len(manifests) == 5
    assert _total(manifests) == 20  # every unit still shipped


def test_single_unit_shipment_is_one_hull() -> None:
    assert len(_generator()._manifests_for(_ship({"T-72": 1}))) == 1


def test_feature_off_is_one_hull_carrying_everything() -> None:
    manifests = _generator(convoys=False)._manifests_for(_ship({"T-72": 4, "BMP-2": 2}))
    assert len(manifests) == 1
    assert _total(manifests) == 6  # the whole transfer, legacy all-or-nothing loss


def test_hull_count_matches_units_per_ship() -> None:
    # A 5-unit shipment at UNITS_PER_SHIP=2 rounds up to 3 hulls.
    expected = min(5, 5, -(-5 // UNITS_PER_SHIP))
    assert len(_generator()._manifests_for(_ship({"T-72": 5}))) == expected


# ---- Part 1: proportional losses -------------------------------------------------


def _debrief(hulls: list[CargoShipUnit]) -> Any:
    return SimpleNamespace(cargo_ship_losses=hulls)


def test_sinking_one_hull_denies_only_its_share() -> None:
    ship = _ship({"T-72": 4, "BMP-2": 2})  # size 6
    manifests = _generator()._manifests_for(ship)
    sunk = CargoShipUnit(manifests[0], ship)

    MissionResultsProcessor.commit_cargo_ship_losses(_debrief([sunk]))

    lost = sum(count for _, count in manifests[0])
    assert ship.size == 6 - lost
    assert ship.size > 0  # the rest of the convoy still delivers


def test_sinking_every_hull_denies_the_whole_shipment() -> None:
    ship = _ship({"T-72": 4, "BMP-2": 2})
    manifests = _generator()._manifests_for(ship)
    hulls = [CargoShipUnit(m, ship) for m in manifests]

    MissionResultsProcessor.commit_cargo_ship_losses(_debrief(hulls))

    assert ship.size == 0


def test_commit_is_safe_when_types_overlap_across_hulls() -> None:
    # All units the same type: every hull's manifest is ({T-72: k}); killing more than
    # remain must not raise (guarded KeyError), and the total lost is exactly the size.
    ship = _ship({"T-72": 6})
    manifests = _generator()._manifests_for(ship)
    hulls = [CargoShipUnit(m, ship) for m in manifests]

    MissionResultsProcessor.commit_cargo_ship_losses(_debrief(hulls))

    assert ship.size == 0


# ---- Part 2: coastal battery engagement ------------------------------------------


def _coastal_generator(enabled: bool, ground_object: object) -> GroundObjectGenerator:
    gen = object.__new__(GroundObjectGenerator)
    setattr(gen, "ground_object", ground_object)
    settings = SimpleNamespace(coastal_batteries_engage_ships=enabled)
    setattr(gen, "game", SimpleNamespace(settings=settings))
    return gen


def _group() -> Any:
    return SimpleNamespace(points=[SimpleNamespace(tasks=[])])


def test_coastal_battery_is_set_weapons_free_when_enabled() -> None:
    coastal = object.__new__(CoastalSiteGroundObject)
    group = _group()
    _coastal_generator(True, coastal).set_coastal_engagement(group)
    tasks = group.points[0].tasks
    assert any(isinstance(t, OptAlarmState) for t in tasks)
    assert any(isinstance(t, OptROE) for t in tasks)


def test_coastal_engagement_is_a_no_op_when_disabled() -> None:
    coastal = object.__new__(CoastalSiteGroundObject)
    group = _group()
    _coastal_generator(False, coastal).set_coastal_engagement(group)
    assert group.points[0].tasks == []


def test_non_coastal_site_is_untouched() -> None:
    missile = object.__new__(MissileSiteGroundObject)
    group = _group()
    _coastal_generator(True, missile).set_coastal_engagement(group)
    assert group.points[0].tasks == []
