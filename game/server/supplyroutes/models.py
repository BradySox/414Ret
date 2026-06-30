from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING
from uuid import UUID

from dcs import Point
from pydantic import BaseModel

from game.server.leaflet import LeafletPoint

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint
    from game.transfers import MultiGroupTransport, TransportMap


class TransportFinder:
    def __init__(
        self, game: Game, control_point_a: ControlPoint, control_point_b: ControlPoint
    ) -> None:
        self.game = game
        self.control_point_a = control_point_a
        self.control_point_b = control_point_b

    def find_in_transport_map(
        self, transport_map: TransportMap[Any]
    ) -> list[MultiGroupTransport]:
        transports = []
        transport = transport_map.find_transport(
            self.control_point_a, self.control_point_b
        )
        if transport is not None:
            transports.append(transport)
        transport = transport_map.find_transport(
            self.control_point_b, self.control_point_a
        )
        if transport is not None:
            transports.append(transport)
        return transports

    def find_transports(self, sea_route: bool) -> list[MultiGroupTransport]:
        if sea_route:
            return self.find_in_transport_map(
                self.game.blue.transfers.cargo_ships
            ) + self.find_in_transport_map(self.game.red.transfers.cargo_ships)
        return self.find_in_transport_map(
            self.game.blue.transfers.convoys
        ) + self.find_in_transport_map(self.game.red.transfers.convoys)

    def describe_active_transports(self, sea_route: bool) -> list[str]:
        transports = self.find_transports(sea_route)
        if not transports:
            return []

        descriptions = []
        for transport in transports:
            units = "units" if transport.size > 1 else "unit"
            descriptions.append(
                f"{transport.size} {units} transferring from {transport.origin} to "
                f"{transport.destination}"
            )
        return descriptions


class SupplyRouteJs(BaseModel):
    id: str
    points: list[LeafletPoint]
    front_active: bool
    is_sea: bool
    blue: bool
    active_transports: list[str]

    class Config:
        title = "SupplyRoute"

    @staticmethod
    def for_link(
        game: Game, a: ControlPoint, b: ControlPoint, points: list[Point], sea: bool
    ) -> SupplyRouteJs:
        if a.captured.is_blue:
            blue = True
        else:
            blue = False
        return SupplyRouteJs(
            # Unique, stable list key for the frontend, encoding the two control-point
            # ids ("<cp_a_id>:<cp_b_id>") so the supply-route interdiction endpoint
            # (game/server/qt/routes.py) can resolve the route back to its CPs.
            # https://reactjs.org/docs/lists-and-keys.html#keys
            id=f"{a.id}:{b.id}",
            points=[p.latlng() for p in points],
            front_active=not sea and a.front_is_active(b),
            is_sea=sea,
            blue=blue,
            active_transports=TransportFinder(game, a, b).describe_active_transports(
                sea
            ),
        )

    @staticmethod
    def all_in_game(game: Game) -> list[SupplyRouteJs]:
        seen = set()
        routes = []
        for control_point in game.theater.controlpoints:
            seen.add(control_point)
            for destination, route in control_point.convoy_routes.items():
                if destination in seen:
                    continue
                routes.append(
                    SupplyRouteJs.for_link(
                        game, control_point, destination, list(route), sea=False
                    )
                )
            for destination, route in control_point.shipping_lanes.items():
                if destination in seen:
                    continue
                if not destination.is_friendly_to(control_point):
                    continue
                routes.append(
                    SupplyRouteJs.for_link(
                        game, control_point, destination, list(route), sea=True
                    )
                )
        return routes


def interdiction_target_for_route_id(
    game: Game, route_id: str
) -> Optional[ControlPoint]:
    """Resolve a supply-route id ("<cp_a_id>:<cp_b_id>") to the enemy control point a
    blue player would interdict: the red end of the road, preferring the contested end
    (one feeding an active front) so the Armed Recon is fragged where the convoy runs.
    Returns None for a malformed id or an all-friendly route (nothing to interdict).
    """
    parts = route_id.split(":")
    if len(parts) != 2:
        return None
    try:
        endpoints = [
            game.theater.find_control_point_by_id(UUID(part)) for part in parts
        ]
    except (ValueError, KeyError):
        return None
    enemy = [cp for cp in endpoints if not cp.captured.is_blue]
    if not enemy:
        return None
    enemy.sort(key=lambda cp: 0 if cp.has_active_frontline else 1)
    return enemy[0]
