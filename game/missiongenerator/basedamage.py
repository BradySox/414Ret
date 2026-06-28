"""Cosmetic battle damage at depleted bases.

A base's abstract ground ``strength`` (0..1) drives how *battered* it looks: a besieged,
ground-down field gets scattered fires, smoke and destroyed-building wreckage, so it reads
as "under siege" instead of pristine -- while staying fully operational (we only *add*
cosmetic objects clear of the runway/parking; the runway-damage model is untouched).

Python plans the damage (it has ``base.strength`` and the airbase geometry); MOOSE places the
fires at mission start (``COORDINATE:BigSmokeAndFire``). Wreckage is spawned as dead pydcs
statics. Regenerated every mission, so the look tracks strength turn by turn.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from dcs.mapping import Point
from dcs.mission import Mission
from dcs.statics import Fortification
from dcs.unitgroup import StaticGroup

if TYPE_CHECKING:
    from game.game import Game

# A base at/above this strength looks clean; below it, damage ramps to full at strength 0.
DAMAGE_THRESHOLD = 0.6
MAX_FIRES_PER_BASE = 8
MAX_WRECKS_PER_BASE = 6
# Keep damage in the field footprint but off the operational core: offset from a parking
# slot (apron edge) by this band, or ring this far out from a runway-less FOB centre.
APRON_OFFSET_M = (70.0, 220.0)
FOB_RING_M = (80.0, 360.0)

# Vanilla building statics that read well as rubble when spawned dead. All ship with base DCS.
_WRECK_TYPES = [
    Fortification.Workshop_A,
    Fortification.Hangar_A,
    Fortification.Hangar_B,
    Fortification.Tech_hangar_A,
]


@dataclass(frozen=True)
class _FirePoint:
    x: float
    y: float
    preset: int  # MOOSE BIGSMOKEPRESET: 1-4 smoke+fire (small..huge), 5-6 smoke only
    density: float


class BaseDamageGenerator:
    def __init__(self, mission: Mission, game: "Game") -> None:
        self.mission = mission
        self.game = game

    def generate(self) -> None:
        if not self.game.settings.base_battle_damage:
            return
        fires: list[_FirePoint] = []
        wreck_id = 0
        for cp in self.game.theater.controlpoints:
            if cp.is_carrier or cp.is_lha:
                continue  # no scorched-deck look on ships
            intensity = self._intensity(cp.base.strength)
            if intensity <= 0:
                continue
            rng = random.Random(hash((cp.id, "basedamage")) & 0xFFFFFFFF)
            anchors = self._anchor_points(cp)
            if not anchors:
                continue
            country = self.mission.country(
                self.game.coalition_for(cp.captured).faction.country.name
            )
            for _ in range(round(intensity * MAX_WRECKS_PER_BASE)):
                wreck_id += 1
                x, y = self._scatter(rng, anchors)
                self._spawn_wreck(rng, country, f"BaseDamage-{cp.id}-{wreck_id}", x, y)
            for _ in range(round(intensity * MAX_FIRES_PER_BASE)):
                x, y = self._scatter(rng, anchors)
                fires.append(self._fire_point(rng, intensity, x, y))
        if fires:
            self._inject_fire_script(fires)

    @staticmethod
    def _intensity(strength: float) -> float:
        if strength >= DAMAGE_THRESHOLD:
            return 0.0
        return max(0.0, min(1.0, (DAMAGE_THRESHOLD - strength) / DAMAGE_THRESHOLD))

    @staticmethod
    def _anchor_points(cp: object) -> list[tuple[float, float]]:
        slots = [s for s in getattr(cp, "parking_slots", [])]
        if slots:
            return [(s.position.x, s.position.y) for s in slots]
        pos = getattr(cp, "position", None)
        return [(pos.x, pos.y)] if pos is not None else []

    def _scatter(
        self, rng: random.Random, anchors: list[tuple[float, float]]
    ) -> tuple[float, float]:
        ax, ay = rng.choice(anchors)
        lo, hi = APRON_OFFSET_M if len(anchors) > 1 else FOB_RING_M
        r = rng.uniform(lo, hi)
        a = rng.uniform(0, 2 * math.pi)
        return ax + r * math.cos(a), ay + r * math.sin(a)

    @staticmethod
    def _fire_point(
        rng: random.Random, intensity: float, x: float, y: float
    ) -> _FirePoint:
        # Bigger, denser fires the more depleted the base; some points smoulder (smoke only).
        if rng.random() < 0.25:
            preset = rng.choice([5, 6])  # smoke only
        else:
            preset = 1 + min(3, int(intensity * 3 + rng.random()))  # 1..4 smoke+fire
        return _FirePoint(x, y, preset, round(0.4 + 0.5 * intensity, 2))

    def _spawn_wreck(
        self,
        rng: random.Random,
        country: object,
        name: str,
        x: float,
        y: float,
    ) -> StaticGroup:
        wreck_type = rng.choice(_WRECK_TYPES)
        return self.mission.static_group(
            country=country,
            name=name,
            _type=wreck_type,
            position=Point(x, y, self.mission.terrain),
            dead=True,
            heading=rng.randint(0, 359),
        )

    def _inject_fire_script(self, fires: list[_FirePoint]) -> None:
        from dcs.action import DoScript
        from dcs.triggers import TriggerStart
        from dcs.translation import String

        rows = ",".join(
            f"{{{f.x:.1f},{f.y:.1f},{f.preset},{f.density}}}" for f in fires
        )
        # 2 s delay so MOOSE (COORDINATE) is loaded before we place the fires.
        lua = (
            "-- 414th base battle damage: persistent fires at depleted bases "
            "(cosmetic; runway untouched)\n"
            f"local F={{{rows}}}\n"
            "timer.scheduleFunction(function()\n"
            "  for _,p in ipairs(F) do\n"
            "    COORDINATE:NewFromVec2({x=p[1],y=p[2]}):BigSmokeAndFire(p[3],p[4])\n"
            "  end\nend, nil, timer.getTime()+2)\n"
        )
        trigger = TriggerStart(comment="414th base battle damage")
        trigger.add_action(DoScript(String(lua)))
        self.mission.triggerrules.triggers.append(trigger)
