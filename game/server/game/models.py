from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from game.server.controlpoints.models import ControlPointJs
from game.server.flights.models import FlightJs
from game.server.frontlines.models import FrontLineJs
from game.server.iadsnetwork.models import IadsNetworkJs
from game.server.leaflet import LeafletPoint
from game.server.mapzones.models import (
    ThreatZoneContainerJs,
    UnculledZoneJs,
    MapZonesJs,
)
from game.server.navmesh.models import NavMeshesJs
from game.server.supplyroutes.models import SupplyRouteJs
from game.server.tgos.models import TgoJs

if TYPE_CHECKING:
    from game import Game


class MapLayersJs(BaseModel):
    """The web client's map-layer panel state, persisted with the save.

    `state` is an opaque JSON string the client owns end to end; the backend only
    stores and returns it so the user's layer choices survive turns and reloads.
    """

    state: str | None = None


class CampaignStatusJs(BaseModel):
    """The campaign-status ribbon payload (campaign phases W3).

    GameJs previously carried no turn, date, or campaign name at all; the phase
    (and, on Vietnam campaigns, the political-will meters) ride in on the same
    small payload. The phase fields are None when `campaign_phases` is off and
    the will fields are None outside `vietnam_political_will` campaigns -- the
    client hides whatever is absent.
    """

    campaign_name: str | None
    turn: int
    date: str
    phase_name: str | None
    phase_status: str | None
    phase_narrative: str | None
    blue_will: float | None
    red_will: float | None

    @staticmethod
    def from_game(game: Game) -> CampaignStatusJs:
        from game.fourteenth.phases import active_phase

        phase = active_phase(game)
        blue_will: float | None = None
        red_will: float | None = None
        if getattr(game.settings, "vietnam_political_will", False):
            blue_will = getattr(game.blue, "political_will", None)
            red_will = getattr(game.red, "political_will", None)
        return CampaignStatusJs(
            campaign_name=game.campaign_name,
            turn=game.turn,
            date=game.current_day.isoformat(),
            phase_name=phase.name if phase is not None else None,
            phase_status=getattr(game, "phase_status_line", None),
            phase_narrative=phase.narrative if phase is not None else None,
            blue_will=blue_will,
            red_will=red_will,
        )


class GameJs(BaseModel):
    control_points: list[ControlPointJs]
    tgos: list[TgoJs]
    supply_routes: list[SupplyRouteJs]
    front_lines: list[FrontLineJs]
    flights: list[FlightJs]
    iads_network: IadsNetworkJs
    threat_zones: ThreatZoneContainerJs
    navmeshes: NavMeshesJs
    map_center: LeafletPoint | None
    unculled_zones: list[UnculledZoneJs]
    map_zones: MapZonesJs
    # True while this is a blank-canvas setup game (campaign maker): the player is
    # painting base ownership and the map shows the paint affordances + Finalize.
    blank_canvas_setup: bool
    # Drop-spawn cheat (§20). When off (default), the map right-click must NOT open
    # the Place Unit Group dialog, so the client skips the POST entirely and a plain
    # right-click stays free for package planning.
    enable_unit_placement: bool
    # Campaign-status ribbon (phases W3): turn/date/campaign + the inferred phase
    # (+ political will on Vietnam campaigns).
    campaign_status: CampaignStatusJs

    class Config:
        title = "Game"

    @staticmethod
    def from_game(game: Game) -> GameJs:
        return GameJs(
            blank_canvas_setup=game.blank_canvas_setup,
            enable_unit_placement=game.settings.enable_unit_placement,
            campaign_status=CampaignStatusJs.from_game(game),
            control_points=ControlPointJs.all_in_game(game),
            tgos=TgoJs.all_in_game(game),
            supply_routes=SupplyRouteJs.all_in_game(game),
            front_lines=FrontLineJs.all_in_game(game),
            flights=FlightJs.all_in_game(game, with_waypoints=True),
            iads_network=IadsNetworkJs.from_network(game.theater.iads_network),
            threat_zones=ThreatZoneContainerJs.for_game(game),
            navmeshes=NavMeshesJs.from_game(game),
            map_center=LeafletPoint.from_latlng(
                game.theater.terrain.map_view_default.position.latlng()
            ),
            unculled_zones=UnculledZoneJs.from_game(game),
            map_zones=MapZonesJs.from_game(game),
        )
