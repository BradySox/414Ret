from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import ClassVar

from game.ato.flighttype import FlightType
from game.commander.tasks.compound.attackairinfrastructure import (
    AttackAirInfrastructure,
)
from game.commander.tasks.compound.attackbattlepositions import AttackBattlePositions
from game.commander.tasks.compound.attackbuildings import AttackBuildings
from game.commander.tasks.compound.attackmotorpools import AttackMotorpools
from game.commander.tasks.compound.attackships import AttackShips
from game.commander.tasks.compound.capturebases import CaptureBases
from game.commander.tasks.compound.defendbases import DefendBases
from game.commander.tasks.compound.degradeiads import DegradeIads
from game.commander.tasks.compound.frontlinecas import PlanFrontLineCas
from game.commander.tasks.compound.interdictreinforcements import (
    InterdictReinforcements,
)
from game.commander.tasks.compound.protectairspace import ProtectAirSpace
from game.commander.tasks.compound.recoverysupport import RecoverySupport
from game.commander.tasks.compound.theatersupport import TheaterSupport
from game.commander.theaterstate import TheaterState
from game.htn import CompoundTask, Method, Task


@dataclass(frozen=True)
class PlanNextAction(CompoundTask[TheaterState]):
    aircraft_cold_start: bool

    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        # Reactive/support methods keep their fixed lead order regardless of any
        # campaign phase (the §17 boundary: reactive defense stays deterministic).
        yield [TheaterSupport()]
        yield [ProtectAirSpace()]
        yield [DefendBases()]
        # The offensive tail is where the campaign phase (W3) applies its soft
        # emphasis: the active phase reorders these methods, which shifts which
        # objectives get first claim on the limited offensive aircraft. No phase
        # (setting off, red coalition, or pre-phase save) yields the stock order.
        # §52 A2: a decapitated command network also THROTTLES the offensive
        # middle -- once this side's offensive package count reaches its C2-health
        # cap, the offensive methods stop being offered (trimming, not
        # reordering). Reactive prefix and recovery tail are never throttled.
        if not self._offensive_tempo_exhausted(state):
            for name in self._offensive_order(state):
                yield [self._OFFENSIVE_FACTORIES[name](self)]
        yield [RecoverySupport()]  # for recovery tankers

    # PlanNextAction's offensive methods by class name, in stock priority order.
    # The name-keyed indirection exists for the campaign-phase emphasis
    # (game/fourteenth/phases.py keeps orderings as names so it never imports the
    # commander); a test locks the two modules in sync.
    _OFFENSIVE_FACTORIES: ClassVar[
        dict[str, Callable[["PlanNextAction"], Task[TheaterState]]]
    ] = {
        "InterdictReinforcements": lambda self: InterdictReinforcements(),
        "AttackBattlePositions": lambda self: AttackBattlePositions(),
        "CaptureBases": lambda self: CaptureBases(),
        # CAS decoupled from the capture/ground-stance decision: plan CAS on any
        # front still contested after CaptureBases (incl. fronts where we're
        # winning the ground war and only set an aggressive stance). Runs after
        # CaptureBases so losing fronts keep first claim on the CAS/escort jets.
        "PlanFrontLineCas": lambda self: PlanFrontLineCas(),
        "AttackAirInfrastructure": lambda self: AttackAirInfrastructure(
            self.aircraft_cold_start
        ),
        "AttackBuildings": lambda self: AttackBuildings(),
        "AttackMotorpools": lambda self: AttackMotorpools(),
        "AttackShips": lambda self: AttackShips(),
        "DegradeIads": lambda self: DegradeIads(),
    }

    # The package types the §52 A2 throttle counts against the C2-health cap.
    # Deliberately only the unambiguous offensive taskings: CAS is excluded
    # (planned defensively by FrontLineDefense), and SEAD/DEAD are excluded so a
    # threat-reactive IADS response is never starved by the throttle (the §17
    # boundary errs conservative in both directions).
    _OFFENSIVE_PACKAGE_TYPES: ClassVar[frozenset[FlightType]] = frozenset(
        {
            FlightType.STRIKE,
            FlightType.BAI,
            FlightType.OCA_RUNWAY,
            FlightType.OCA_AIRCRAFT,
            FlightType.ANTISHIP,
            FlightType.AIR_ASSAULT,
            FlightType.ARMED_RECON,
        }
    )

    def _offensive_tempo_exhausted(self, state: TheaterState) -> bool:
        """True when the §52 A2 throttle says this side may plan no more offense.

        The cap comes from the side's own command-network health (None = no
        throttle: feature off, network intact, or no command centers -- the
        byte-identical default). Counted against the packages already added to
        this coalition's ATO this planning run, so the throttle closes the
        offensive middle mid-run once the cap is reached.
        """
        from game.fourteenth.c2_decapitation import offensive_package_cap

        coalition = state.context.coalition
        cap = offensive_package_cap(
            coalition, state.context.theater, state.context.settings
        )
        if cap is None:
            return False
        planned = sum(
            1
            for package in coalition.ato.packages
            if package.primary_task in self._OFFENSIVE_PACKAGE_TYPES
        )
        return planned >= cap

    def _offensive_order(self, state: TheaterState) -> list[str]:
        """The offensive method order for this planning run.

        BLUE follows the *campaign's* arc (§40 campaign phases — "roll back the enemy
        IADS" describes blue's intent); RED follows its adaptive posture (§55 red
        intent — consolidate/attrition/surge). Each side yields an emphasis ordering
        over the offensive methods; absent one (feature off, no phase/posture, or the
        neutral default) the stock order stands, so the planner is byte-identical to
        pre-feature behaviour until a side's layer is active.
        """
        from game.fourteenth.weather_planning import demote_weather_hostile_methods

        stock = list(self._OFFENSIVE_FACTORIES)
        coalition = state.context.coalition
        if coalition.player.is_blue:
            from game.fourteenth.phases import active_phase

            phase = active_phase(coalition.game)
            emphasis = phase.emphasis if phase is not None else None
        else:
            from game.fourteenth.red_intent import offensive_emphasis

            emphasis = offensive_emphasis(coalition.game)
        if not emphasis:
            # §67: the weather has the last word for both sides -- a thunderstorm
            # demotes the low-level visual-attack methods to the tail (soft, like
            # the emphasis itself; any other sky is a no-op).
            return demote_weather_hostile_methods(coalition.game, stock)
        # Guard against a stale/authored emphasis naming an unknown method, and
        # against one omitting a method: unknown names are dropped, missing ones
        # keep their stock relative order at the tail.
        order = [name for name in emphasis if name in self._OFFENSIVE_FACTORIES]
        order.extend(name for name in stock if name not in order)
        return demote_weather_hostile_methods(coalition.game, order)
