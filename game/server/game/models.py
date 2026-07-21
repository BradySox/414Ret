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
    plus, on Vietnam campaigns, the political-will meters and, when configured,
    the §75 victory rows -- ride in on this small payload. The will fields are
    None outside `vietnam_political_will` campaigns and the client hides whatever
    is absent. `will_history` (the sparkline) and `events` (the turn feed) follow
    the same rule: empty means the client renders nothing.
    """

    campaign_name: str | None
    turn: int
    date: str
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
    #: §75 custom victory conditions: one row per configured win/lose entry with
    #: live-value prose, empty (block + chip hidden) unless the campaign authors
    #: a `victory:` block or a domination/attrition knob is on. The optional
    #: description is the authored header ("Liberate Abkhazia").
    victory: list[VictoryConditionJs]
    victory_description: str | None
    #: (turn, blue, red) per flown turn, most recent last; capped for payload size.
    will_history: list[tuple[int, float, float]]
    events: list[CampaignEventJs]
    #: §29 SITREP parity (2026-07-18 UI audit): the per-turn Sitrep digest the
    #: kneeboard band renders (losses, POWs, MIA, rescues, will movers, posture),
    #: previously readable only in the cockpit. None/empty on a quiet turn.
    sitrep_turn: int | None
    sitrep_lines: list[str]
    #: COIN HVT window countdown (the "invisible clock" audit finding): the live
    #: leader's name + turns left to strike. None when no HVT is up. The name is
    #: already-announced intel; the concealed map position stays fogged.
    hvt_name: str | None
    hvt_turns_left: int | None

    @staticmethod
    def from_game(game: Game) -> CampaignStatusJs:
        from game.fourteenth.political_will import ledger_notes, will_profile_for
        from game.fourteenth.victory import victory_description, victory_overview

        victory_rows = [
            VictoryConditionJs(
                text=str(row["text"]), met=bool(row["met"]), defeat=bool(row["defeat"])
            )
            for row in victory_overview(game)
        ]
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
        # "what just happened" (base captures, will moves, Hanoi's response)
        # without shipping the whole campaign log on every /game pull.
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
            blue_supply=blue_supply,
            red_supply=red_supply,
            red_c2=red_c2,
            blue_will=blue_will,
            red_will=red_will,
            blue_will_label=blue_will_label,
            red_will_label=red_will_label,
            blue_will_note=blue_will_note,
            red_will_note=red_will_note,
            victory=victory_rows,
            victory_description=victory_description(game),
            will_history=history,
            events=events,
            sitrep_turn=sitrep_turn,
            sitrep_lines=sitrep_lines,
            hvt_name=hvt_name,
            hvt_turns_left=hvt_turns_left,
        )


class SupplyNodeJs(BaseModel):
    """§53 P4b: one BLUE (player) control point on the supply-flow overlay.

    Either a *front* consumer -- coloured by its materiel readiness -- or a
    *producer* source (factory/oil). Emitted only when ``war_economy`` is on; empty
    otherwise, which hides the layer (the restricted-zones pattern). BLUE-only:
    enemy logistics stay fogged.
    """

    name: str
    position: LeafletPoint
    #: Materiel readiness in ``[0, 1]`` (``supply_factor``). ``1.0`` for a producer or
    #: a quiet CP with no front to starve.
    supply: float
    #: Supply produced per turn here (``0`` for a pure consumer).
    production: float
    #: True when this CP has an active front consuming supply.
    is_front: bool

    @staticmethod
    def all_in_game(game: Game) -> list[SupplyNodeJs]:
        if not game.settings.war_economy:
            return []
        from game.fourteenth.war_economy import production_rate, supply_factor

        nodes: list[SupplyNodeJs] = []
        for cp in game.theater.control_points_for(game.blue.player):
            prod = production_rate(cp)
            is_front = cp.has_active_frontline
            if prod <= 0.0 and not is_front:
                continue
            nodes.append(
                SupplyNodeJs(
                    name=cp.name,
                    position=cp.position.latlng(),
                    supply=supply_factor(cp),
                    production=prod,
                    is_front=is_front,
                )
            )
        return nodes


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


class DownedPilotJs(BaseModel):
    """§21 downed BLUE aviators on the map: MIA evaders at their last known
    position, POWs at their holding enemy field.

    The between-turns host plans next turn's rescue from here — this state was
    previously readable only on the in-cockpit SITREP band (the 2026-07-18 UI
    audit's top finding). Emitted whenever ledger entries exist (the systems
    that create them carry their own gates); empty hides the layer. BLUE-only
    by construction — both ledgers are blue aviators, so nothing is fogged.
    """

    name: str
    position: LeafletPoint
    #: "mia" (evading, at last known position) or "pow" (at the holding field).
    status: str
    #: Player-facing detail mirroring the SITREP wording: "evading (2 turns
    #: down)" / "held at Mozdok (2 turns left)" / "held at Mozdok (held)".
    detail: str

    @staticmethod
    def all_in_game(game: Game) -> list[DownedPilotJs]:
        pilots: list[DownedPilotJs] = []
        for downed in getattr(game, "downed_pilots", None) or []:
            name = downed.pilot.name if downed.pilot is not None else "Downed aviator"
            turns = max(int(game.turn) - int(getattr(downed, "turn_downed", 0)), 0)
            plural = "s" if turns != 1 else ""
            pilots.append(
                DownedPilotJs(
                    name=name,
                    position=game.point_in_world(downed.x, downed.y).latlng(),
                    status="mia",
                    detail=f"evading ({turns} turn{plural} down)",
                )
            )
        will_economy = bool(getattr(game.settings, "vietnam_political_will", False))
        for entry in game.blue.pending_pow_recoveries:
            name = entry.pilot.name if entry.pilot is not None else "Downed aviator"
            where = "an unknown location"
            position = game.point_in_world(entry.x, entry.y)
            if entry.holding_cp_id is not None:
                try:
                    cp = game.theater.find_control_point_by_id(entry.holding_cp_id)
                    where = cp.name
                    position = cp.position
                except KeyError:
                    pass
            if will_economy:
                clock = "held"
            else:
                turns_left = max(entry.turns_remaining, 0)
                clock = f"{turns_left} turn{'s' if turns_left != 1 else ''} left"
            pilots.append(
                DownedPilotJs(
                    name=name,
                    position=position.latlng(),
                    status="pow",
                    detail=f"held at {where} ({clock})",
                )
            )
        return pilots


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
    # Campaign-status ribbon: turn/date/campaign (+ political will on Vietnam
    # campaigns, + §75 victory rows when configured).
    campaign_status: CampaignStatusJs
    # War-economy supply-flow overlay (§53 P4b): BLUE fronts + producers with their
    # materiel readiness. Empty unless war_economy is on, which hides the layer.
    supply_nodes: list[SupplyNodeJs]
    # §57 air-dropped minefields: BLUE-only live fields (dashed circles). Empty unless
    # air_droppable_minefields is on, which hides the layer; the enemy never sees them.
    minefields: list[MinefieldJs]
    # §21 downed BLUE aviators: MIA evaders at their last known position + POWs at
    # their holding field. Empty when nobody is down, which hides the layer.
    downed_pilots: list[DownedPilotJs]

    class Config:
        title = "Game"

    @staticmethod
    def from_game(game: Game) -> GameJs:
        return GameJs(
            blank_canvas_setup=game.blank_canvas_setup,
            enable_unit_placement=game.settings.enable_unit_placement,
            campaign_status=CampaignStatusJs.from_game(game),
            supply_nodes=SupplyNodeJs.all_in_game(game),
            minefields=MinefieldJs.all_in_game(game),
            downed_pilots=DownedPilotJs.all_in_game(game),
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
