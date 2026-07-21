from __future__ import annotations

import itertools
import math
from collections import defaultdict
from typing import TYPE_CHECKING, List, Tuple

from dcs import Mission
from dcs.unitgroup import ShipGroup

from game.dcs.groundunittype import GroundUnitType
from game.transfers import CargoShip
from game.unitmap import UnitMap
from game.utils import knots

if TYPE_CHECKING:
    from game import Game

#: Rough cargo carried per hull when spreading a sea shipment into a convoy. A shipment
#: of N units sails on ceil(N / UNITS_PER_SHIP) hulls, capped by the convoy-size setting
#: and by the unit count (never an empty hull). Small so a normal reinforcement reads as
#: a visible convoy the coastal batteries can whittle down.
UNITS_PER_SHIP = 2

Manifest = Tuple[Tuple[GroundUnitType, int], ...]


class CargoShipGenerator:
    def __init__(self, mission: Mission, game: Game, unit_map: UnitMap) -> None:
        self.mission = mission
        self.game = game
        self.unit_map = unit_map
        self.count = itertools.count()

    def generate(self) -> None:
        # Reset the count to make generation deterministic.
        if not self.game.settings.perf_disable_cargo_ships:
            for coalition in self.game.coalitions:
                for ship in coalition.transfers.cargo_ships:
                    self.generate_cargo_ship(ship)

    def generate_cargo_ship(self, ship: CargoShip) -> ShipGroup:
        coalition = self.game.coalition_for(ship.player_owned)
        waypoints = ship.route

        country = coalition.faction.country
        country = self.mission.country(country.name)

        manifests = self._manifests_for(ship)
        group = self.mission.ship_group(
            country,
            ship.name,
            coalition.faction.cargo_ship.dcs_unit_type,
            position=waypoints[0],
            group_size=len(manifests),
        )
        for waypoint in waypoints[1:]:
            # 12 knots is very slow but it's also nearly the max allowed by DCS for this
            # type of ship. The whole group sails the lane in formation.
            group.add_waypoint(waypoint, speed=knots(12).kph)
        self.unit_map.add_cargo_ship(group, ship, manifests)
        return group

    def _manifests_for(self, ship: CargoShip) -> List[Manifest]:
        """Partition the shipment's units across the convoy's hulls (§77).

        Round-robins the individual units into ``n`` hulls so each carries a mixed
        share, then packs each hull into a ``(unit_type, count)`` manifest. Sinking a
        hull kills exactly its manifest, which is why losses come out proportional. With
        the convoy setting off (or a single-unit shipment) there is one hull carrying
        the whole transfer -- byte-identical to the legacy single-ship behaviour.
        """
        units = list(ship.iter_units())
        total = len(units)
        if not self.game.settings.cargo_ship_convoys or total <= 1:
            return [self._pack(units)]

        max_ships = max(1, self.game.settings.cargo_ship_convoy_max)
        n = min(total, max_ships, max(1, math.ceil(total / UNITS_PER_SHIP)))
        buckets: List[List[GroundUnitType]] = [[] for _ in range(n)]
        for i, unit_type in enumerate(units):
            buckets[i % n].append(unit_type)
        return [self._pack(bucket) for bucket in buckets]

    @staticmethod
    def _pack(unit_types: List[GroundUnitType]) -> Manifest:
        counts: dict[GroundUnitType, int] = defaultdict(int)
        for unit_type in unit_types:
            counts[unit_type] += 1
        return tuple(counts.items())
