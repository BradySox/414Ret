from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from dcs.mapping import Point
from pydantic import BaseModel

from game.server.controlpoints.models import ControlPointJs
from game.server.downedpilots.models import DownedPilotJs
from game.server.flights.models import FlightJs
from game.server.frontlines.models import FrontLineJs
from game.server.iadsnetwork.models import IadsNetworkJs
from game.server.leaflet import LeafletPoint, LeafletPoly
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


class VictoryConditionJs(BaseModel):
    """One §75 victory/defeat condition for the ribbon's expander block.

    ``text`` is prose with live values ("Enemy air force below 10% of start
    (now 62%)"); ``defeat`` rows render as risks. ``met`` in practice only
    shows once the war is ending (a met condition ends the game at the next
    turn boundary), so the live parentheticals are the working display.
    """

    text: str
    met: bool
    defeat: bool


class CampaignEventJs(BaseModel):
    """One Information message for the map's turn-events feed."""

    turn: int
    title: str
    text: str


class CampaignStatusJs(BaseModel):
    """The campaign-status ribbon payload.

    GameJs previously carried no turn, date, or campaign name at all; those --
    plus, when configured, the §75 victory rows -- ride in on this small payload.
    `events` (the turn feed) is empty when the client should render nothing.
    """

    campaign_name: str | None
    turn: int
    date: str
    #: §52: the enemy command-network status ("1/3 command posts operational") when it
    #: is degraded and c2_decapitation_effects is on -- the ribbon twin of the SITREP
    #: line. None hides the chip.
    red_c2: str | None
    #: §75 custom victory conditions: one row per configured win/lose entry with
    #: live-value prose, empty (block + chip hidden) unless the campaign authors
    #: a `victory:` block or a domination/attrition knob is on. The optional
    #: description is the authored header ("Liberate Abkhazia").
    victory: list[VictoryConditionJs]
    victory_description: str | None
    events: list[CampaignEventJs]
    #: §29 SITREP parity (2026-07-18 UI audit): the per-turn Sitrep digest the
    #: kneeboard band renders (losses, POWs, MIA, rescues), previously readable
    #: only in the cockpit. None/empty on a quiet turn.
    sitrep_turn: int | None
    sitrep_lines: list[str]
    #: COIN HVT window countdown (the "invisible clock" audit finding): the live
    #: leader's name + turns left to strike. None when no HVT is up. The name is
    #: already-announced intel; the concealed map position stays fogged.
    hvt_name: str | None
    hvt_turns_left: int | None

    @staticmethod
    def from_game(game: Game) -> CampaignStatusJs:
        from game.fourteenth.victory import victory_description, victory_overview

        victory_rows = [
            VictoryConditionJs(
                text=str(row["text"]), met=bool(row["met"]), defeat=bool(row["defeat"])
            )
            for row in victory_overview(game)
        ]
        red_c2: str | None = None
        if getattr(game.settings, "c2_decapitation_effects", False):
            from game.fourteenth.c2_decapitation import c2_status_line
            from game.theater.player import Player

            red_c2 = c2_status_line(game, Player.RED)
        # The last two turns' Information messages, newest first: enough for
        # "what just happened" (base captures, Hanoi's response) without
        # shipping the whole campaign log on every /game pull.
        events = [
            CampaignEventJs(turn=info.turn, title=info.title, text=info.text)
            for info in reversed(game.informations)
            if info.turn >= game.turn - 1
        ][:25]
        # SITREP parity: the same digest the kneeboard band renders, via the
        # same renderer, so the app surface can never drift from the cockpit's.
        sitrep_turn: int | None = None
        sitrep_lines: list[str] = []
        sitrep = getattr(game, "last_sitrep", None)
        if sitrep is not None and sitrep.has_news:
            sitrep_turn = sitrep.turn
            sitrep_lines = sitrep.kneeboard_lines()
        from game.fourteenth.coin_hvt import active_hvt_status

        hvt_name: str | None = None
        hvt_turns_left: int | None = None
        hvt_status = active_hvt_status(game)
        if hvt_status is not None:
            hvt_name, hvt_turns_left = hvt_status
        return CampaignStatusJs(
            campaign_name=game.campaign_name,
            turn=game.turn,
            date=game.current_day.isoformat(),
            red_c2=red_c2,
            victory=victory_rows,
            victory_description=victory_description(game),
            events=events,
            sitrep_turn=sitrep_turn,
            sitrep_lines=sitrep_lines,
            hvt_name=hvt_name,
            hvt_turns_left=hvt_turns_left,
        )


class MinefieldJs(BaseModel):
    """§57: one active air-dropped minefield on the friendly (BLUE) map overlay.

    A dashed circle at the field's centre with its radius. Emitted only when
    ``air_droppable_minefields`` is on and BLUE has live fields; empty otherwise, which
    hides the layer (the supply-nodes / restricted-zones pattern). BLUE-only -- the enemy
    never sees where you mined.
    """

    position: LeafletPoint
    radius_m: float
    charges: int

    @staticmethod
    def all_in_game(game: Game) -> list[MinefieldJs]:
        if not getattr(game.settings, "air_droppable_minefields", False):
            return []
        from game.fourteenth.minefields import active_minefields

        return [
            MinefieldJs(
                position=minefield.position.latlng(),
                radius_m=minefield.radius_m,
                charges=minefield.charges,
            )
            for minefield in active_minefields(game)
        ]


class NeutralBorderJs(BaseModel):
    """§96: one neutral country's defended airspace, for the planning map.

    The DCS F10 map draws this at runtime, but by then you are already in the
    cockpit -- the border has to be visible while you are *planning* the route,
    which is the only time you can choose to route around it. Emitted only when
    ``neutral_border_defense`` is on and the theater carries zones (the
    minefields pattern); empty otherwise, which hides the layer. Borders ship
    per terrain, so that is every real-world map, authored or not.

    Not fogged: a national border is public knowledge, and the whole point is
    that the player can see the line they are choosing to cross.
    """

    country: str
    #: Where the alert flight comes from, for the tooltip: a field name, or
    #: "<country> border CAP" for a neutral with no airfield on the map.
    airfield: str
    #: "neutral", "blue" or "red" -- who owns the airspace (the colour family).
    posture: str
    #: Whether BLUE may transit — the map is drawn from the player's side.
    overflight: bool
    #: Altitude below which BLUE is intercepted, or None for any altitude. A
    #: floor means "high transit is tolerated"; a closed country grants none.
    floor_ft: Optional[int]
    #: The border ring as a Leaflet polygon (array-of-arrays, one ring, no holes).
    border: LeafletPoly

    @staticmethod
    def all_in_game(game: Game) -> list[NeutralBorderJs]:
        if not getattr(game.settings, "neutral_border_defense", False):
            return []
        from game.theater.neutralborder import NEUTRAL

        zones = getattr(game.theater, "neutral_border_zones", [])
        borders = []
        for zone in zones:
            posture = zone.posture_in(game.theater)
            permits_blue = zone.permits(game.theater, True)
            # A border only bites if the country can actually put a fighter up.
            # The generator degrades a neutral that cannot to drawn-and-toothless,
            # and this map has to agree with the mission it is planning: 14 of the
            # shipped zones have no era airframe, so Cyprus and Armenia were drawn
            # "closed to you at any altitude" over a mission that let you fly
            # straight through them.
            if posture == NEUTRAL and not zone.can_field_an_interceptor(
                game.current_day
            ):
                permits_blue = True
            ring = [
                LeafletPoint.from_latlng(Point(x, y, game.theater.terrain).latlng())
                for x, y in zone.border
            ]
            borders.append(
                NeutralBorderJs(
                    country=zone.country,
                    airfield=zone.origin_label(posture, enforced=not permits_blue),
                    posture=posture,
                    overflight=permits_blue,
                    floor_ft=zone.floor_for(game.theater, True),
                    border=[ring],
                )
            )
        return borders


class GameJs(BaseModel):
    control_points: list[ControlPointJs]
    tgos: list[TgoJs]
    downed_pilots: list[DownedPilotJs]
    supply_routes: list[SupplyRouteJs]
    front_lines: list[FrontLineJs]
    flights: list[FlightJs]
    iads_network: IadsNetworkJs
    threat_zones: ThreatZoneContainerJs
    navmeshes: NavMeshesJs
    map_center: LeafletPoint | None
    unculled_zones: list[UnculledZoneJs]
    map_zones: MapZonesJs
    # Campaign-status ribbon: turn/date/campaign (+ §75 victory rows when configured).
    campaign_status: CampaignStatusJs
    # §57 air-dropped minefields: BLUE-only live fields (dashed circles). Empty unless
    # air_droppable_minefields is on, which hides the layer; the enemy never sees them.
    minefields: list[MinefieldJs]
    # §96 neutral border defense: the defended airspace of each authored neutral
    # country. Empty unless neutral_border_defense is on, which hides the layer.
    neutral_borders: list[NeutralBorderJs]

    class Config:
        title = "Game"

    @staticmethod
    def from_game(game: Game) -> GameJs:
        return GameJs(
            campaign_status=CampaignStatusJs.from_game(game),
            minefields=MinefieldJs.all_in_game(game),
            neutral_borders=NeutralBorderJs.all_in_game(game),
            control_points=ControlPointJs.all_in_game(game),
            tgos=TgoJs.all_in_game(game),
            downed_pilots=DownedPilotJs.all_in_game(game),
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
