from collections.abc import Iterator
from typing import Optional

from game.ato.flighttype import FlightType
from game.commander.tasks.primitive.combatsar import PlanCombatSar
from game.commander.theaterstate import TheaterState
from game.dcs.aircrafttype import AircraftType
from game.htn import CompoundTask, Method


class PlanCombatSarSupport(CompoundTask[TheaterState]):
    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        king = self._king_aircraft(state)
        for target in state.combat_sar_targets:
            yield [PlanCombatSar(target, king_aircraft=king)]

    @staticmethod
    def _king_aircraft(state: TheaterState) -> Optional[AircraftType]:
        # The "King" is a C-130 (non-helicopter) Combat SAR airframe the coalition
        # owns; field one as the on-scene commander alongside the rescue helo when
        # available, else None (no King flight).
        for squadron in state.context.coalition.air_wing.iter_squadrons():
            aircraft = squadron.aircraft
            if aircraft.capable_of(FlightType.COMBAT_SAR) and not aircraft.helicopter:
                return aircraft
        return None
