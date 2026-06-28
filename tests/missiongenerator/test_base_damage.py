"""Battle damage at depleted bases scales with strength, respects the threshold + toggle,
and only ever ADDS cosmetic objects (no runway impact)."""

from __future__ import annotations

import pytest
from dcs.countries import USA
from dcs.mapping import Point
from dcs.mission import Mission

import math

from game.missiongenerator.basedamage import (
    APRON_OFFSET_M,
    DAMAGE_THRESHOLD,
    FIRE_SPREAD_M,
    BaseDamageGenerator,
)


class _FakeSlot:
    def __init__(self, position: Point) -> None:
        self.position = position


class _FakeBase:
    def __init__(self, strength: float) -> None:
        self.strength = strength


class _FakeCp:
    is_carrier = False
    is_lha = False
    captured = None  # the fake coalition_for ignores it

    def __init__(
        self, cp_id: int, strength: float, position: Point, n_slots: int
    ) -> None:
        self.id = cp_id
        self.base = _FakeBase(strength)
        self.position = position
        self.parking_slots = [
            _FakeSlot(Point(position.x + i * 40, position.y, position._terrain))
            for i in range(n_slots)
        ]


class _Country:
    name = USA.name


class _Coalition:
    class faction:
        country = _Country


class _Settings:
    def __init__(self, on: bool) -> None:
        self.base_battle_damage = on


class _Theater:
    def __init__(self, cps: list[_FakeCp]) -> None:
        self.controlpoints = cps


class _Game:
    def __init__(self, cps: list[_FakeCp], on: bool = True) -> None:
        self.settings = _Settings(on)
        self.theater = _Theater(cps)

    def coalition_for(self, _player: object) -> _Coalition:
        return _Coalition()


def _mission_with_usa() -> Mission:
    mission = Mission()
    mission.coalition["blue"].add_country(USA())
    return mission


def _wreck_count(mission: Mission) -> int:
    return sum(
        1
        for group in mission.country(USA.name).static_group
        if group.name.startswith("BaseDamage-")
    )


def _fire_triggers(mission: Mission) -> int:
    return sum(
        1 for t in mission.triggerrules.triggers if "battle damage" in (t.comment or "")
    )


def test_besieged_base_gets_fires_and_wreckage() -> None:
    mission = _mission_with_usa()
    cp = _FakeCp(1, 0.25, Point(-284887, 683859, mission.terrain), n_slots=10)
    BaseDamageGenerator(mission, _Game([cp])).generate()  # type: ignore[arg-type]
    assert _wreck_count(mission) > 0
    assert _fire_triggers(mission) == 1


def test_healthy_base_gets_nothing() -> None:
    mission = _mission_with_usa()
    cp = _FakeCp(1, DAMAGE_THRESHOLD + 0.1, Point(-284887, 683859, mission.terrain), 10)
    BaseDamageGenerator(mission, _Game([cp])).generate()  # type: ignore[arg-type]
    assert _wreck_count(mission) == 0
    assert _fire_triggers(mission) == 0


def test_more_depleted_base_takes_more_damage() -> None:
    light = _mission_with_usa()
    heavy = _mission_with_usa()
    pos_l = Point(-284887, 683859, light.terrain)
    pos_h = Point(-284887, 683859, heavy.terrain)
    BaseDamageGenerator(light, _Game([_FakeCp(1, 0.5, pos_l, 10)])).generate()  # type: ignore[arg-type]
    BaseDamageGenerator(heavy, _Game([_FakeCp(1, 0.1, pos_h, 10)])).generate()  # type: ignore[arg-type]
    assert _wreck_count(heavy) > _wreck_count(light)


def test_toggle_off_disables_everything() -> None:
    mission = _mission_with_usa()
    cp = _FakeCp(1, 0.1, Point(-284887, 683859, mission.terrain), 10)
    BaseDamageGenerator(mission, _Game([cp], on=False)).generate()  # type: ignore[arg-type]
    assert _wreck_count(mission) == 0
    assert _fire_triggers(mission) == 0


def test_fires_spread_around_the_base_not_clustered() -> None:
    # Fires must ring the field, not knot up at one spot. Even a single-anchor FOB (the worst
    # case -- no parking slots) should spread its fires well past the old tight ring.
    import random

    generator = BaseDamageGenerator.__new__(BaseDamageGenerator)
    fob_anchor = [(-284042.0, 673895.0)]
    fires = generator._fire_positions(random.Random(1), fob_anchor, 5)
    spread = max(math.hypot(a[0] - b[0], a[1] - b[1]) for a in fires for b in fires)
    assert spread > FIRE_SPREAD_M  # > 600 m apart, vs the old ~360 m ring


def test_damage_stays_within_apron_band_of_a_slot() -> None:
    # Every wreck must sit within the apron offset band of some parking slot -- i.e. on the
    # field footprint, not on the runway centre or out in the countryside.
    mission = _mission_with_usa()
    pos = Point(-284887, 683859, mission.terrain)
    cp = _FakeCp(1, 0.0, pos, n_slots=12)
    BaseDamageGenerator(mission, _Game([cp])).generate()  # type: ignore[arg-type]
    slots = [s.position for s in cp.parking_slots]
    for group in mission.country(USA.name).static_group:
        if not group.name.startswith("BaseDamage-"):
            continue
        wp = group.units[0].position
        nearest = min(wp.distance_to_point(s) for s in slots)
        assert nearest <= APRON_OFFSET_M[1] + 1.0
