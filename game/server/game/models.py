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


class PhaseArcEntryJs(BaseModel):
    """One phase of the campaign's arc, for the ribbon's expander panel."""

    key: str
    name: str
    narrative: str
    #: Scheduled escalation turn; 0 = not turn-pinned (Tier-0 arcs are adaptive).
    min_turn: int
    #: Target classes locked while this phase is active.
    locked: list[str]
    #: Restricted-zone display names active in this phase.
    zones: list[str]
    current: bool


class CampaignEventJs(BaseModel):
    """One Information message for the map's turn-events feed."""

    turn: int
    title: str
    text: str


class CampaignStatusJs(BaseModel):
    """The campaign-status ribbon payload (campaign phases W3).

    GameJs previously carried no turn, date, or campaign name at all; the phase
    (and, on Vietnam campaigns, the political-will meters) ride in on the same
    small payload. The phase fields are None when `campaign_phases` is off and
    the will fields are None outside `vietnam_political_will` campaigns -- the
    client hides whatever is absent. `phases` (the arc expander), `will_history`
    (the sparkline), and `events` (the turn feed) follow the same rule: empty
    means the client renders nothing.
    """

    campaign_name: str | None
    turn: int
    date: str
    phase_name: str | None
    phase_status: str | None
    phase_narrative: str | None
    blue_will: float | None
    red_will: float | None
    phases: list[PhaseArcEntryJs]
    #: (turn, blue, red) per flown turn, most recent last; capped for payload size.
    will_history: list[tuple[int, float, float]]
    events: list[CampaignEventJs]

    @staticmethod
    def from_game(game: Game) -> CampaignStatusJs:
        from game.fourteenth.phases import active_phase, arc_overview

        phase = active_phase(game)
        blue_will: float | None = None
        red_will: float | None = None
        history: list[tuple[int, float, float]] = []
        if getattr(game.settings, "vietnam_political_will", False):
            blue_will = getattr(game.blue, "political_will", None)
            red_will = getattr(game.red, "political_will", None)
            # The will trend rides game_stats' per-turn series (one record per
            # turn, deduped across re-inits) -- the same source the Qt Stats
            # window charts, covering skipped turns as flat segments.
            history = [
                (turn, blue, red)
                for turn, (blue, red) in enumerate(
                    (
                        getattr(data.allied_units, "political_will", None),
                        getattr(data.enemy_units, "political_will", None),
                    )
                    for data in game.game_stats.data_per_turn
                )
                if blue is not None and red is not None
            ][-40:]
        # The last two turns' Information messages, newest first: enough for
        # "what just happened" (phase transitions, ROE violations, will moves)
        # without shipping the whole campaign log on every /game pull.
        events = [
            CampaignEventJs(turn=info.turn, title=info.title, text=info.text)
            for info in reversed(game.informations)
            if info.turn >= game.turn - 1
        ][:25]
        return CampaignStatusJs(
            campaign_name=game.campaign_name,
            turn=game.turn,
            date=game.current_day.isoformat(),
            phase_name=phase.name if phase is not None else None,
            phase_status=getattr(game, "phase_status_line", None),
            phase_narrative=phase.narrative if phase is not None else None,
            blue_will=blue_will,
            red_will=red_will,
            phases=[PhaseArcEntryJs(**entry) for entry in arc_overview(game)],
            will_history=history,
            events=events,
        )


class RestrictedZoneJs(BaseModel):
    """An active ROE restricted zone (campaign phases W4) for the map layer."""

    name: str
    center: LeafletPoint
    radius_m: float
    #: What the ROE locks right now + when it eases (the zone tooltip body).
    detail: str

    @staticmethod
    def all_in_game(game: Game) -> list[RestrictedZoneJs]:
        from game.fourteenth.phases import active_restricted_zones, zone_detail

        detail = zone_detail(game)
        return [
            RestrictedZoneJs(
                name=name,
                center=LeafletPoint.from_latlng(center.latlng()),  # type: ignore[attr-defined]
                radius_m=radius_m,
                detail=detail,
            )
            for name, center, radius_m in active_restricted_zones(game)
        ]


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
    # Active ROE restricted zones (phases W4); empty outside authored ROE phases.
    restricted_zones: list[RestrictedZoneJs]

    class Config:
        title = "Game"

    @staticmethod
    def from_game(game: Game) -> GameJs:
        return GameJs(
            blank_canvas_setup=game.blank_canvas_setup,
            enable_unit_placement=game.settings.enable_unit_placement,
            campaign_status=CampaignStatusJs.from_game(game),
            restricted_zones=RestrictedZoneJs.all_in_game(game),
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
