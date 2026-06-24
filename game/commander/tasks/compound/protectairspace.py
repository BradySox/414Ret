from collections.abc import Iterator

from game.commander.tasks.primitive.barcap import PlanBarcap
from game.commander.tasks.primitive.forwardbarcap import PlanForwardBarcap
from game.commander.theaterstate import TheaterState
from game.htn import CompoundTask, Method


class ProtectAirSpace(CompoundTask[TheaterState]):
    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        for cp, needed in state.barcaps_needed.items():
            if needed > 0:
                yield [PlanBarcap(cp, needed)]
        # Added forward-middle BARCAP screens (414th red forward-BARCAP layer); the
        # dict is empty except on large maps with a red active front, so this is a
        # no-op otherwise and the rear BARCAP above is unchanged.
        for zone, needed in state.forward_barcaps_needed.items():
            if needed > 0:
                yield [PlanForwardBarcap(zone, needed)]
