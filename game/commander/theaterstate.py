from __future__ import annotations

import dataclasses
import itertools
import math
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Union, Dict

from game.commander.battlepositions import BattlePositions
from game.commander.objectivefinder import ObjectiveFinder
from game.db import GameDb
from game.ground_forces.combat_stance import CombatStance
from game.htn import WorldState
from game.profiling import MultiEventTracer
from game.settings import Settings
from game.theater import (
    ConflictTheater,
    ControlPoint,
    FrontLine,
    MissionTarget,
    Player,
)
from game.theater.theatergroundobject import (
    BuildingGroundObject,
    IadsGroundObject,
    NavalGroundObject,
    TheaterGroundObject,
    VehicleGroupGroundObject,
)
from game.threatzones import ThreatZones

if TYPE_CHECKING:
    from game import Game
    from game.coalition import Coalition
    from game.transfers import Convoy, CargoShip


# Threat-weighted BARCAP volume. barcap_rounds (duration-derived) is the
# baseline wave count; a defended CP at the theater's peak air threat gets up to
# BARCAP_THREAT_CEILING * baseline waves, while the quietest defended CP drops to
# BARCAP_MIN_ROUNDS so the airwing isn't spread thin over cold flanks.
BARCAP_MIN_ROUNDS = 1
BARCAP_THREAT_CEILING = 2
# A CP that anchors the front always rates at least this fraction of the peak,
# since raids ingress across the line even when the nearest enemy airfield sits
# just beyond airbase_threat_range.
BARCAP_FRONTLINE_MIN_FACTOR = 0.5


def barcap_coverage_rounds(
    mission_duration: float,
    barcap_duration: float,
    barcap_overlap: float,
) -> int:
    """Minimum overlapping BARCAP waves to span the mission window.

    Waves are spaced ``barcap_duration - barcap_overlap`` apart starting at the
    mission open, so ``N`` waves cover up to ``(N - 1) * (barcap_duration -
    barcap_overlap) + barcap_duration``. This returns the smallest ``N`` making
    that reach ``mission_duration``.

    This is the floor used to keep a quiet sector from being trimmed below the
    point where it can no longer cover a *long* mission, while still allowing a
    single wave when the on-station time already spans the whole mission. The
    unavoidable front-of-mission gap while the first wave transits/jitters is
    deliberate (anti-"wait-it-out") and is a separate concern from wave count.
    """
    effective_coverage = max(barcap_duration - barcap_overlap, 60.0)
    needed = mission_duration - barcap_duration
    if needed <= 0:
        return BARCAP_MIN_ROUNDS
    return math.ceil(needed / effective_coverage) + 1


def threat_weighted_barcap_rounds(
    baseline_rounds: int,
    threat_score: float,
    max_threat_score: float,
    is_fleet: bool,
    has_active_frontline: bool,
    min_rounds: int = BARCAP_MIN_ROUNDS,
) -> int:
    """Scales the baseline BARCAP wave count by relative enemy air threat.

    A defended CP at the theater's peak threat gets ``BARCAP_THREAT_CEILING *
    baseline_rounds`` waves; the quietest drops to ``min_rounds`` (the per-CP
    tail-coverage floor from :func:`barcap_coverage_rounds`). Front-line CPs are
    floored at ``BARCAP_FRONTLINE_MIN_FACTOR`` of the peak. Fleet CPs keep their
    legacy 2x multiplier on top of the scaled count.

    With no measurable threat anywhere (``max_threat_score <= 0``) every defended
    CP falls back to ``baseline_rounds``, reproducing the legacy flat allocation.
    """
    if max_threat_score <= 0:
        rounds = baseline_rounds
    else:
        factor = threat_score / max_threat_score
        if has_active_frontline:
            factor = max(factor, BARCAP_FRONTLINE_MIN_FACTOR)
        ceil_rounds = baseline_rounds * BARCAP_THREAT_CEILING
        rounds = round(min_rounds + factor * (ceil_rounds - min_rounds))
    rounds = max(min_rounds, rounds)
    return 2 * rounds if is_fleet else rounds


@dataclass(frozen=True)
class PersistentContext:
    game_db: GameDb
    coalition: Coalition
    theater: ConflictTheater
    turn: int
    now: datetime
    settings: Settings
    tracer: MultiEventTracer


@dataclass
class TheaterState(WorldState["TheaterState"]):
    context: PersistentContext
    barcaps_needed: dict[ControlPoint, int]
    active_front_lines: list[FrontLine]
    front_line_stances: dict[FrontLine, Optional[CombatStance]]
    vulnerable_front_lines: list[FrontLine]
    aewc_targets: list[MissionTarget]
    refueling_targets: list[MissionTarget]
    recovery_targets: dict[ControlPoint, int]
    enemy_air_defenses: list[IadsGroundObject]
    threatening_air_defenses: list[Union[IadsGroundObject, NavalGroundObject]]
    detecting_air_defenses: list[Union[IadsGroundObject, NavalGroundObject]]
    enemy_convoys: list[Convoy]
    enemy_shipping: list[CargoShip]
    enemy_ships: list[NavalGroundObject]
    enemy_battle_positions: dict[ControlPoint, BattlePositions]
    oca_targets: list[ControlPoint]
    strike_targets: list[TheaterGroundObject]
    enemy_barcaps: list[ControlPoint]
    threat_zones: ThreatZones
    vulnerable_control_points: list[ControlPoint]
    control_point_priority_queue: list[ControlPoint]
    priority_cp: Optional[ControlPoint]

    def _rebuild_threat_zones(self) -> None:
        """Recreates the theater's threat zones based on the current planned state."""
        self.threat_zones = ThreatZones.for_threats(
            self.context.theater,
            self.context.coalition.opponent.doctrine,
            barcap_locations=self.enemy_barcaps,
            air_defenses=itertools.chain(self.enemy_air_defenses, self.enemy_ships),
        )

    def eliminate_air_defense(self, target: IadsGroundObject) -> None:
        if target in self.threatening_air_defenses:
            self.threatening_air_defenses.remove(target)
        if target in self.detecting_air_defenses:
            self.detecting_air_defenses.remove(target)
        self.enemy_air_defenses.remove(target)
        self._rebuild_threat_zones()

    def eliminate_ship(self, target: NavalGroundObject) -> None:
        if target in self.threatening_air_defenses:
            self.threatening_air_defenses.remove(target)
        if target in self.detecting_air_defenses:
            self.detecting_air_defenses.remove(target)
        self.enemy_ships.remove(target)
        self._rebuild_threat_zones()

    def has_battle_position(self, target: VehicleGroupGroundObject) -> bool:
        return target in self.enemy_battle_positions[target.control_point]

    def eliminate_battle_position(self, target: VehicleGroupGroundObject) -> None:
        self.enemy_battle_positions[target.control_point].eliminate(target)

    def ammo_dumps_at(
        self, control_point: ControlPoint
    ) -> Iterator[BuildingGroundObject]:
        for target in self.strike_targets:
            if target.control_point != control_point:
                continue
            if target.is_ammo_depot:
                assert isinstance(target, BuildingGroundObject)
                yield target

    def clone(self) -> TheaterState:
        # Do not use copy.deepcopy. Copying every TGO, control point, etc is absurdly
        # expensive.
        return TheaterState(
            context=self.context,
            barcaps_needed=dict(self.barcaps_needed),
            active_front_lines=list(self.active_front_lines),
            front_line_stances=dict(self.front_line_stances),
            vulnerable_front_lines=list(self.vulnerable_front_lines),
            aewc_targets=list(self.aewc_targets),
            refueling_targets=list(self.refueling_targets),
            recovery_targets=dict(self.recovery_targets),
            enemy_air_defenses=list(self.enemy_air_defenses),
            enemy_convoys=list(self.enemy_convoys),
            enemy_shipping=list(self.enemy_shipping),
            enemy_ships=list(self.enemy_ships),
            enemy_battle_positions={
                cp: dataclasses.replace(g)
                for cp, g in self.enemy_battle_positions.items()
            },
            oca_targets=list(self.oca_targets),
            strike_targets=list(self.strike_targets),
            enemy_barcaps=list(self.enemy_barcaps),
            threat_zones=self.threat_zones,
            # Persistent properties are not copied. These are a way for failed subtasks
            # to communicate requirements to other tasks. For example, the task to
            # attack enemy battle_positions might fail because the target area has IADS
            # protection. In that case, the preconditions of PlanBai would fail, but
            # would add the IADS that prevented it from being planned to the list of
            # IADS threats so that DegradeIads will consider it a threat later.
            threatening_air_defenses=self.threatening_air_defenses,
            detecting_air_defenses=self.detecting_air_defenses,
            vulnerable_control_points=self.vulnerable_control_points,
            control_point_priority_queue=self.control_point_priority_queue,
            priority_cp=self.priority_cp,
        )

    @classmethod
    def from_game(
        cls, game: Game, player: Player, now: datetime, tracer: MultiEventTracer
    ) -> TheaterState:
        coalition = game.coalition_for(player)
        finder = ObjectiveFinder(game, player)
        ordered_capturable_points = finder.prioritized_points()
        air_assault_capturable_points = finder.air_assault_targets()

        context = PersistentContext(
            game.db,
            coalition,
            game.theater,
            game.turn,
            now,
            game.settings,
            tracer,
        )

        # Plan enough rounds of CAP that the target has coverage over the expected
        # mission duration. Waves overlap by barcap_overlap_time, so each wave only
        # contributes (duration - overlap) of *fresh* coverage; plan enough rounds
        # to span the mission even with overlapping handoffs.
        mission_duration = game.settings.desired_player_mission_duration.total_seconds()
        barcap_duration = game.settings.desired_barcap_mission_duration.total_seconds()
        barcap_overlap = game.settings.barcap_overlap_time.total_seconds()
        effective_coverage = max(barcap_duration - barcap_overlap, 60.0)
        barcap_rounds = math.ceil(mission_duration / effective_coverage)

        battle_postitions: Dict[ControlPoint, BattlePositions] = {
            cp: BattlePositions.for_control_point(cp)
            for cp in air_assault_capturable_points
        }

        vulnerable_control_points = [
            cp
            for cp, bp in battle_postitions.items()
            if not bp.blocking_capture or cp.is_fleet
        ]

        aewc_targets = [cp for cp in finder.friendly_control_points() if cp.is_carrier]
        aewc_targets.append(finder.farthest_friendly_control_point())

        vulnerable_cps = list(finder.vulnerable_control_points())
        barcap_threat_scores = {
            cp: finder.air_threat_score(cp) for cp in vulnerable_cps
        }
        max_barcap_threat = max(barcap_threat_scores.values(), default=0.0)

        # Even a quiet sector needs enough waves to span the mission: a single
        # wave covers a 60-min mission but not a 150-min one. This floor lets the
        # threat weighting trim cold flanks to one wave on short missions without
        # leaving a long mission's tail uncovered.
        coverage_floor = barcap_coverage_rounds(
            mission_duration, barcap_duration, barcap_overlap
        )

        return TheaterState(
            context=context,
            barcaps_needed={
                cp: threat_weighted_barcap_rounds(
                    barcap_rounds,
                    barcap_threat_scores[cp],
                    max_barcap_threat,
                    cp.is_fleet,
                    cp.has_active_frontline,
                    min_rounds=coverage_floor,
                )
                for cp in vulnerable_cps
            },
            active_front_lines=list(finder.front_lines()),
            front_line_stances={f: None for f in finder.front_lines()},
            vulnerable_front_lines=list(finder.front_lines()),
            aewc_targets=list(aewc_targets),
            refueling_targets=[finder.closest_friendly_control_point()],
            recovery_targets={cp: 0 for cp in finder.friendly_naval_control_points()},
            enemy_air_defenses=list(finder.enemy_air_defenses()),
            threatening_air_defenses=[],
            detecting_air_defenses=[],
            enemy_convoys=list(finder.convoys()),
            enemy_shipping=list(finder.cargo_ships()),
            enemy_ships=list(finder.enemy_ships()),
            enemy_battle_positions=battle_postitions,
            oca_targets=list(
                finder.oca_targets(
                    min_aircraft=game.settings.oca_target_autoplanner_min_aircraft_count
                )
            ),
            strike_targets=list(finder.strike_targets()),
            enemy_barcaps=list(game.theater.control_points_for(player.opponent)),
            threat_zones=game.threat_zone_for(player.opponent),
            vulnerable_control_points=vulnerable_control_points,
            control_point_priority_queue=ordered_capturable_points,
            priority_cp=(
                ordered_capturable_points[0] if ordered_capturable_points else None
            ),
        )
