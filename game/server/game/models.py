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
    from game.fourteenth.phases import ResolvedZone


class MapLayersJs(BaseModel):
    """The web client's map-layer panel state, persisted with the save.

    `state` is an opaque JSON string the client owns end to end; the backend only
    stores and returns it so the user's layer choices survive turns and reloads.
    """

    state: str | None = None


class PhaseObjectiveJs(BaseModel):
    """One objectives-checklist row for a phase (live tick in the expander).

    ``done`` is None for display-only guidance the engine can't measure -- the
    client renders a plain bullet instead of a tick box.
    """

    text: str
    done: bool | None


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
    #: How the arc leaves this phase (transition transparency): the authored
    #: ``advance_when`` acceleration spelled out with live values on the current
    #: phase, or the Tier-0 classifier thresholds. Empty = terminal / schedule-only.
    advance: str
    #: The phase's objectives checklist with live done-ticks.
    objectives: list[PhaseObjectiveJs]


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
    #: §55 Red Intent: the enemy commander's current posture ("Surging" /
    #: "Consolidating" / "Attrition") + its legibility line. None when red_intent is
    #: off, so the client hides the chip -- same rule as the phase fields.
    red_posture: str | None
    red_posture_detail: str | None
    #: §53 war economy: front supply health per side, 0-100 (blue = your logistics,
    #: red = the enemy's -- bomb it and a starved red digs in, §55). None when
    #: war_economy is off; the client hides the chips.
    blue_supply: float | None
    red_supply: float | None
    #: §52: the enemy command-network status ("1/3 command posts operational") when it
    #: is degraded and c2_decapitation_effects is on -- the ribbon twin of the SITREP
    #: line. None hides the chip.
    red_c2: str | None
    blue_will: float | None
    red_will: float | None
    #: The campaign's authored will framing (the will-profile labels; Vietnam
    #: defaults) -- the meter tooltips. None whenever the meters are.
    blue_will_label: str | None
    red_will_label: str | None
    #: The latest flown turn's will attribution (the W1 ledger), one rendered
    #: top-movers line per side -- the meter hover / expander note. None when the
    #: ledger is empty or will tracking is off.
    blue_will_note: str | None
    red_will_note: str | None
    phases: list[PhaseArcEntryJs]
    #: (turn, blue, red) per flown turn, most recent last; capped for payload size.
    will_history: list[tuple[int, float, float]]
    events: list[CampaignEventJs]

    @staticmethod
    def from_game(game: Game) -> CampaignStatusJs:
        from game.fourteenth.phases import active_phase, arc_overview
        from game.fourteenth.political_will import ledger_notes, will_profile_for
        from game.fourteenth.red_intent import active_red_intent

        phase = active_phase(game)
        posture = active_red_intent(game)
        red_posture = posture.display if posture is not None else None
        red_posture_detail = (
            getattr(game, "red_intent_status_line", None)
            if posture is not None
            else None
        )
        blue_supply: float | None = None
        red_supply: float | None = None
        if getattr(game.settings, "war_economy", False):
            try:
                from game.fourteenth.war_economy import coalition_supply_health

                blue_supply = coalition_supply_health(game, game.blue) * 100
                red_supply = coalition_supply_health(game, game.red) * 100
            except Exception:
                blue_supply = red_supply = None
        red_c2: str | None = None
        if getattr(game.settings, "c2_decapitation_effects", False):
            from game.fourteenth.c2_decapitation import c2_status_line
            from game.theater.player import Player

            red_c2 = c2_status_line(game, Player.RED)
        blue_will: float | None = None
        red_will: float | None = None
        blue_will_label: str | None = None
        red_will_label: str | None = None
        blue_will_note: str | None = None
        red_will_note: str | None = None
        history: list[tuple[int, float, float]] = []
        if getattr(game.settings, "vietnam_political_will", False):
            blue_will = getattr(game.blue, "political_will", None)
            red_will = getattr(game.red, "political_will", None)
            profile = will_profile_for(game)
            blue_will_label = profile.blue.label
            red_will_label = profile.red.label
            blue_will_note, red_will_note = ledger_notes(game)
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
            red_posture=red_posture,
            red_posture_detail=red_posture_detail,
            blue_supply=blue_supply,
            red_supply=red_supply,
            red_c2=red_c2,
            blue_will=blue_will,
            red_will=red_will,
            blue_will_label=blue_will_label,
            red_will_label=red_will_label,
            blue_will_note=blue_will_note,
            red_will_note=red_will_note,
            phases=[PhaseArcEntryJs(**entry) for entry in arc_overview(game)],
            will_history=history,
            events=events,
        )


class RestrictedZoneJs(BaseModel):
    """An active ROE restricted zone (campaign phases W4) for the map layer.

    ``kind`` selects how the client draws it: ``circle`` uses ``center``/``radius_m``;
    ``box``/``corridor`` use the ``outline`` polygon ring (empty for a circle).
    """

    name: str
    kind: str
    center: LeafletPoint
    radius_m: float
    outline: list[LeafletPoint]
    #: What the ROE locks right now + when it eases (the zone tooltip body).
    detail: str

    @staticmethod
    def _from_resolved(
        game: Game, zones: list[ResolvedZone], detail: str
    ) -> list[RestrictedZoneJs]:
        out = []
        for zone in zones:
            center = game.point_in_world(*zone.center_xy)
            outline = [
                LeafletPoint.from_latlng(game.point_in_world(x, y).latlng())
                for x, y in zone.outline_xy
            ]
            out.append(
                RestrictedZoneJs(
                    name=zone.name,
                    kind=zone.kind,
                    center=LeafletPoint.from_latlng(center.latlng()),
                    radius_m=zone.radius_m,
                    outline=outline,
                    detail=detail,
                )
            )
        return out

    @staticmethod
    def all_in_game(game: Game) -> list[RestrictedZoneJs]:
        from game.fourteenth.phases import active_restricted_zones, zone_detail

        return RestrictedZoneJs._from_resolved(
            game, active_restricted_zones(game), zone_detail(game)
        )

    @staticmethod
    def free_fire_in_game(game: Game) -> list[RestrictedZoneJs]:
        """Active free-fire (weapons-free) pockets -- inverted ROE (COIN)."""
        from game.fourteenth.phases import active_free_fire_zones

        return RestrictedZoneJs._from_resolved(
            game,
            active_free_fire_zones(game),
            "Weapons free -- cleared to engage here. Everywhere else is off-limits.",
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
    # Active ROE restricted zones (phases W4); empty outside authored ROE phases.
    restricted_zones: list[RestrictedZoneJs]
    # Active free-fire (weapons-free) pockets -- inverted ROE (COIN); empty unless a
    # phase authors free_fire_zones. Drawn green, vs the red restricted zones.
    free_fire_zones: list[RestrictedZoneJs]

    class Config:
        title = "Game"

    @staticmethod
    def from_game(game: Game) -> GameJs:
        return GameJs(
            blank_canvas_setup=game.blank_canvas_setup,
            enable_unit_placement=game.settings.enable_unit_placement,
            campaign_status=CampaignStatusJs.from_game(game),
            restricted_zones=RestrictedZoneJs.all_in_game(game),
            free_fire_zones=RestrictedZoneJs.free_fire_in_game(game),
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
