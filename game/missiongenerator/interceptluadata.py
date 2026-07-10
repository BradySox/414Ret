from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable
from uuid import UUID

from game.utils import Distance, nautical_miles

if TYPE_CHECKING:
    from game.data.doctrine import Doctrine
    from game.missiongenerator.luagenerator import LuaData
    from game.theater import ConflictTheater


#: Fallback backstop-EWR DCS type per coalition. These are stock EWR units that
#: ship with the base game; the Lua skips a base's backstop if the type is not
#: present in the running DCS build (see intercept-config.lua).
DEFAULT_BACKSTOP_EWR_TYPE = {"BLUE": "FPS-117", "RED": "55G6 EWR"}

#: GCI-ambush scramble radius cap (Vietnam W5). An ambush-doctrine side scrambles
#: LATE -- the raid is already deep when the MiGs launch, so the intercept happens
#: near the strike package's target instead of duelling the sweep at the border.
#: The stock setting still applies when it is tighter.
AMBUSH_GCI_RADIUS_NM = 40

#: Forward-defense reach: with ``qra_forward_defense`` on, the ceiling on how far a
#: raid may be from a base and still make that base eligible to scramble for it.
#:
#: Widening the reach does NOT cause a mass launch. Moose's GCI loop
#: (``AI_A2A_DISPATCHER``, Moose.lua) walks every squadron, keeps the one with the
#: shortest *intercept* distance among those inside ``GciRadius``, and only reaches
#: back to a farther squadron once the closer one's alert is spent. So a wide reach
#: buys an echelon -- the front field answers, the rear fields backfill -- and this
#: ceiling is what keeps a genuinely deep-rear field (300 NM back) at home.
QRA_FORWARD_REACH_NM = 200

#: How far *past* the FLOT a front-anchor CP's defended-airspace circle reaches. The
#: circle grows to ``distance(cp, front) + this`` so the contested airspace is always
#: inside the defended zone however far behind the line the anchor sits. This is the
#: only place a side's defended airspace crosses into enemy territory.
FRONT_FORWARD_MARGIN_NM = 25

#: Slack over (reach + engage) for the home-base disengage leash. Moose aborts a
#: defender once ``DistanceFromHomeBase > DisengageRadius`` (default 300 km ~= 162 NM),
#: so without this a base at the far edge of its reach would launch and then turn
#: around mid-transit.
DISENGAGE_MARGIN_NM = 20


@dataclass(frozen=True)
class DispatcherTuning:
    """The per-side radii the Lua hands to ``AI_A2A_DISPATCHER``."""

    #: Moose ``SetEngageRadius``: how far a defender chases a target.
    engage_nm: int
    #: Moose ``SetGciRadius``: how far from a base a raid may be and still scramble it.
    scramble_nm: int
    #: Moose ``SetDisengageRadius``: how far from home a defender may get before it
    #: aborts. ``0`` leaves Moose's own default (or, under ambush, the Lua's tight
    #: hit-and-run leash) in place.
    disengage_nm: int
    ambush: bool


def dispatcher_tuning(
    doctrine: "Doctrine",
    engagement_range_nm: int,
    gci_max_radius_nm: int,
    forward_defense: bool = False,
) -> DispatcherTuning:
    """Resolve one side's QRA dispatcher radii.

    A ``gci_ambush`` doctrine (Vietnam W5) wins outright: it shrinks the engage radius
    to the doctrine's own close-fight ``cap_engagement_range`` (the P1c era number),
    caps the scramble radius at :data:`AMBUSH_GCI_RADIUS_NM`, and leaves ``disengage_nm``
    at 0 so the Lua applies its tighter hit-and-run leash instead. The late, close GCI
    slash is the whole point of that posture -- forward defense must not widen it.

    Otherwise, with ``forward_defense`` on, the scramble radius opens to
    :data:`QRA_FORWARD_REACH_NM` so rear fields can answer a raid at the front, and the
    disengage leash opens with it. What stops those defenders chasing deep into enemy
    airspace is *geography*, not reach: the border zones from
    :func:`defense_zone_entries` mean the dispatcher never sees a target outside its own
    defended airspace. Turning forward defense off passes the raw settings through, which
    is byte-identical to pre-feature behaviour.
    """
    if getattr(doctrine, "gci_ambush", False):
        return DispatcherTuning(
            engage_nm=min(
                engagement_range_nm, round(doctrine.cap_engagement_range.nautical_miles)
            ),
            scramble_nm=min(gci_max_radius_nm, AMBUSH_GCI_RADIUS_NM),
            disengage_nm=0,
            ambush=True,
        )
    if forward_defense:
        scramble_nm = max(gci_max_radius_nm, QRA_FORWARD_REACH_NM)
        return DispatcherTuning(
            engage_nm=engagement_range_nm,
            scramble_nm=scramble_nm,
            disengage_nm=scramble_nm + engagement_range_nm + DISENGAGE_MARGIN_NM,
            ambush=False,
        )
    return DispatcherTuning(
        engage_nm=engagement_range_nm,
        scramble_nm=gci_max_radius_nm,
        disengage_nm=0,
        ambush=False,
    )


@dataclass(frozen=True)
class DefenseZoneEntry:
    """One circle of a coalition's defended airspace (a Moose ``ZONE_RADIUS``).

    The union of a side's circles becomes its dispatcher's *accept zones* via
    ``AI_A2A_DISPATCHER:SetBorderZone`` -> ``DETECTION_BASE:SetAcceptZones``. Moose drops
    any detected object outside every accept zone, so the dispatcher cannot scramble
    against -- or keep engaging -- a target beyond this airspace.
    """

    name: str
    coalition: str  # "BLUE" or "RED"
    x: float
    y: float
    radius_m: float


def defense_zone_entries(
    theater: "ConflictTheater", depth: Distance
) -> list[DefenseZoneEntry]:
    """A circle of defended airspace around each side's control points.

    Radius is ``depth`` for a rear CP. A CP that anchors an active front gets a circle
    grown to reach ``FRONT_FORWARD_MARGIN_NM`` past its own FLOT, so the contested
    airspace is always defended no matter how far back the anchor sits -- which is what
    lets rear fields' QRA fight over the front at all.

    Defaulting ``depth`` to the stock ``qra_gci_max_radius_nm`` makes this
    non-regressive: the set of raids that used to trigger a GCI (within that radius of
    *some* base) is exactly the union of the circles.
    """
    from game.theater import OffMapSpawn

    forward_margin = nautical_miles(FRONT_FORWARD_MARGIN_NM).meters

    # A front anchor's circle must reach past its own FLOT. A CP can anchor more than
    # one front; take the reach of the farthest.
    anchor_reach: dict[UUID, float] = {}
    for front in theater.conflicts():
        for cp in (front.blue_cp, front.red_cp):
            reach = cp.position.distance_to_point(front.position) + forward_margin
            anchor_reach[cp.id] = max(anchor_reach.get(cp.id, 0.0), reach)

    zones: list[DefenseZoneEntry] = []
    for cp in theater.controlpoints:
        if isinstance(cp, OffMapSpawn):
            # Off-map spawns are not real airspace.
            continue
        if cp.captured.is_neutral:
            continue
        zones.append(
            DefenseZoneEntry(
                name=f"QRA Defense {cp.name}",
                coalition="BLUE" if cp.captured.is_blue else "RED",
                x=cp.position.x,
                y=cp.position.y,
                radius_m=max(depth.meters, anchor_reach.get(cp.id, 0.0)),
            )
        )
    return zones


@dataclass(frozen=True)
class PlayerAlertEntry:
    """A base with a player-manned QRA alert flight (§1, player-manning).

    Drives the "raid inbound — scramble" cue: the Lua scans for hostile aircraft
    within ``scramble_radius_nm`` (+ a lead margin so a cold start has time) of the
    base and calls the player to scramble. Separate from ``InterceptEntry`` because
    a base can be *fully* player-manned (no AI dispatcher entry at all).
    """

    airbase_name: str
    coalition: str  # "BLUE" or "RED" (player QRA is BLUE today)
    #: The AI scramble (GCI) radius in NM; the player cue fires a margin beyond it.
    scramble_radius_nm: int


@dataclass(frozen=True)
class InterceptEntry:
    squadron_id: str
    squadron_name: str
    airbase_name: str
    template_prefix: str
    coalition: str  # "BLUE" or "RED"
    resource_count: int
    #: Aircraft launched per QRA scramble (1 or 2). Rolled per squadron toward a
    #: distributed-QRA posture; the Lua falls back to 2 if absent.
    grouping: int
    engagement_range_nm: int
    gci_max_radius_nm: int
    comms_enabled: bool
    #: DCS country id, used by the Lua to spawn the per-base backstop EWR in the
    #: correct coalition.
    country_id: int
    #: DCS unit type for the per-base backstop EWR.
    backstop_ewr_type: str
    #: GCI-ambush posture (Vietnam W5): the Lua leashes this side's defenders
    #: (small disengage radius + high fuel threshold = hit-and-run). Defaulted so
    #: pre-W5 callers/tests are unaffected.
    ambush: bool = False
    #: Moose ``SetDisengageRadius`` in NM; 0 leaves Moose's default (~162 NM) alone.
    #: Set alongside a widened ``gci_max_radius_nm`` under forward defense, since a
    #: base at the far edge of its reach would otherwise abort mid-transit.
    disengage_radius_nm: int = 0


def populate_intercept_lua(
    root: "LuaData",
    entries: Iterable[InterceptEntry],
    player_alert_entries: Iterable[PlayerAlertEntry] = (),
    defense_zones: Iterable[DefenseZoneEntry] = (),
) -> None:
    """Build the ``dcsRetribution.Intercept`` subtree (mirrors the IADS pattern).

    Always creates BLUE, RED, PLAYER_ALERT, and ZONES buckets so the Lua side can
    iterate them unconditionally, then appends one record per reserved squadron (AI
    dispatcher), one per player-manned alert base, and one per defended-airspace circle.
    An empty ZONES bucket means "no border zone" -- the Lua skips ``SetBorderZone``, and
    the dispatcher engages wherever it detects, exactly as before the feature.
    """
    intercept = root.add_item("Intercept")
    buckets = {
        "BLUE": intercept.get_or_create_item("BLUE"),
        "RED": intercept.get_or_create_item("RED"),
    }
    for entry in entries:
        record = buckets[entry.coalition].add_item()
        record.add_key_value("squadronId", entry.squadron_id)
        record.add_key_value("squadronName", entry.squadron_name)
        record.add_key_value("airbaseName", entry.airbase_name)
        record.add_key_value("templatePrefix", entry.template_prefix)
        record.add_key_value("resourceCount", str(entry.resource_count))
        record.add_key_value("grouping", str(entry.grouping))
        record.add_key_value("engagementRangeNm", str(entry.engagement_range_nm))
        record.add_key_value("gciMaxRadiusNm", str(entry.gci_max_radius_nm))
        record.add_key_value("commsEnabled", "true" if entry.comms_enabled else "false")
        record.add_key_value("countryId", str(entry.country_id))
        record.add_key_value("backstopEwrType", entry.backstop_ewr_type)
        record.add_key_value("ambushPosture", "true" if entry.ambush else "false")
        record.add_key_value("disengageRadiusNm", str(entry.disengage_radius_nm))

    alerts = intercept.get_or_create_item("PLAYER_ALERT")
    for alert in player_alert_entries:
        record = alerts.add_item()
        record.add_key_value("airbaseName", alert.airbase_name)
        record.add_key_value("coalition", alert.coalition)
        record.add_key_value("scrambleRadiusNm", str(alert.scramble_radius_nm))

    zones = intercept.get_or_create_item("ZONES")
    zone_buckets = {
        "BLUE": zones.get_or_create_item("BLUE"),
        "RED": zones.get_or_create_item("RED"),
    }
    for zone in defense_zones:
        record = zone_buckets[zone.coalition].add_item()
        record.add_key_value("name", zone.name)
        record.add_key_value("x", f"{zone.x:.1f}")
        record.add_key_value("y", f"{zone.y:.1f}")
        record.add_key_value("radiusM", f"{zone.radius_m:.1f}")
