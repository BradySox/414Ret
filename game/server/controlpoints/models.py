from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from game.fourteenth.region_priorities import priority_of
from game.server.leaflet import LeafletPoint

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint


class ControlPointJs(BaseModel):
    id: UUID
    name: str
    blue: bool
    position: LeafletPoint
    mobile: bool
    destination: LeafletPoint | None
    sidc: str
    # Comms/nav summary for the hover tooltip. None when not applicable
    # (e.g. enemy control point, or no TACAN allocated yet).
    tacan: str | None
    atc_frequency: str | None
    units: list[str]
    threat_ranges: list[float]
    detection_ranges: list[float]
    # §90 rung A: SUPPLIED / AIRLIFTED / ISOLATED, or None when the gate is off
    # or this is not our base. Whether a base can still be reinforced decides
    # whether it recovers strength at all, and it had no surface anywhere --
    # a player whose base stopped rebuilding had no way to find out why.
    supply_status: str | None
    # §93 region priorities: the BLUE planning emphasis for this CP's targets
    # (emphasized/normal/deprioritized/ignored), or None when the setting is
    # off. Set from the base dialog; the planner weight reads the same field.
    region_priority: str | None

    class Config:
        title = "ControlPoint"

    @staticmethod
    def for_control_point(
        control_point: ControlPoint,
        supply: dict[ControlPoint, str] | None = None,
    ) -> ControlPointJs:
        destination = None
        if control_point.target_position is not None:
            destination = control_point.target_position.latlng()
        if control_point.captured.is_blue:
            blue = True
        else:
            blue = False
        tacan, atc_frequency = _comms_summary(control_point)

        # Carrier/LHA control points carry their ship groups (the carrier and
        # its escorts) as an is_control_point ground object that is
        # intentionally not emitted as a standalone TGO. Surface the surviving
        # units and their air-defense ranges on the control point itself so the
        # map can show the escort detail and threat rings the same way it does
        # for ordinary naval groups.
        units: list[str] = []
        threat_ranges: list[float] = []
        detection_ranges: list[float] = []
        from game.theater import Player

        for tgo in control_point.ground_objects:
            if not tgo.is_control_point:
                continue
            # Recon intel-fog applies here exactly as it does to standalone
            # TGOs (TgoJs.for_tgo): an un-engaged enemy carrier group keeps its
            # composition and threat rings hidden. Friendly groups (and engaged
            # enemy ones) list every unit with its " [DEAD]" tag, matching
            # ordinary naval groups.
            if not tgo.known_for(Player.BLUE):
                continue
            units.extend(unit.display_name for unit in tgo.units)
            for group in tgo.groups:
                threat = group.max_threat_range().meters
                if threat:
                    threat_ranges.append(threat)
                detection = group.max_detection_range().meters
                if detection:
                    detection_ranges.append(detection)

        return ControlPointJs(
            id=control_point.id,
            name=control_point.name,
            blue=blue,
            position=control_point.position.latlng(),
            mobile=control_point.moveable and control_point.captured.is_blue,
            destination=destination,
            sidc=str(control_point.sidc()),
            tacan=tacan,
            atc_frequency=atc_frequency,
            units=units,
            threat_ranges=threat_ranges,
            detection_ranges=detection_ranges,
            # Only look up when there is something to look up: the lookup
            # hashes the control point, and callers that pass no supply map
            # must not be made to require a hashable one.
            supply_status=supply.get(control_point) if supply else None,
            # getattr chain: model tests hold duck-typed CPs with no
            # coalition, and priority_of getattr-guards the field itself.
            region_priority=(
                priority_of(control_point).value
                if getattr(
                    getattr(getattr(control_point, "coalition", None), "game", None),
                    "settings",
                    None,
                )
                and control_point.coalition.game.settings.region_priorities
                else None
            ),
        )

    @staticmethod
    def all_in_game(game: Game) -> list[ControlPointJs]:
        supply = _blue_supply_statuses(game)
        return [
            ControlPointJs.for_control_point(cp, supply)
            for cp in game.theater.controlpoints
        ]


def _blue_supply_statuses(game: Game) -> dict[ControlPoint, str]:
    """Supply tier per blue control point, or empty when the gate is off.

    Blue only: how well the enemy can reinforce is not something planning should
    hand the player. Computed once per request rather than per control point --
    the tiering walks the transit network, so doing it per base would re-walk it
    once for every base on every poll of /game.
    """
    if not game.settings.supply_gated_reinforcement:
        return {}
    from game.theater.supply import supply_statuses

    points = game.theater.player_points()
    return {
        cp: status.name
        for cp, status in supply_statuses(points, game.blue.transit_network).items()
    }


def _comms_summary(cp: ControlPoint) -> tuple[str | None, str | None]:
    """Return (tacan, atc_frequency) strings for the tooltip, or None if N/A.

    Only resolved for friendly (blue) airfields, since the tooltip shows our
    own bases' comms — enemy details are not exposed in planning.
    """
    from game.atcdata import AtcData
    from game.radio.TacanContainer import TacanContainer
    from game.theater.controlpoint import Airfield

    if not cp.captured.is_blue:
        return None, None

    tacan: str | None = None
    if isinstance(cp, TacanContainer) and cp.tacan is not None:
        if cp.tcn_name:
            tacan = f"{cp.tacan} ({cp.tcn_name})"
        else:
            tacan = str(cp.tacan)

    atc: str | None = None
    if isinstance(cp, Airfield):
        atc_radio = AtcData.from_pydcs(cp.airport)
        if atc_radio is not None and atc_radio.uhf is not None:
            atc = str(atc_radio.uhf)

    return tacan, atc
