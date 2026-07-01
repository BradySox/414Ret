from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from game.data.doctrine import Doctrine
    from game.missiongenerator.luagenerator import LuaData


#: Fallback backstop-EWR DCS type per coalition. These are stock EWR units that
#: ship with the base game; the Lua skips a base's backstop if the type is not
#: present in the running DCS build (see intercept-config.lua).
DEFAULT_BACKSTOP_EWR_TYPE = {"BLUE": "FPS-117", "RED": "55G6 EWR"}

#: GCI-ambush scramble radius cap (Vietnam W5). An ambush-doctrine side scrambles
#: LATE -- the raid is already deep when the MiGs launch, so the intercept happens
#: near the strike package's target instead of duelling the sweep at the border.
#: The stock setting still applies when it is tighter.
AMBUSH_GCI_RADIUS_NM = 40


def dispatcher_tuning(
    doctrine: "Doctrine", engagement_range_nm: int, gci_max_radius_nm: int
) -> tuple[int, int, bool]:
    """(engage NM, scramble NM, ambush?) for one side's QRA dispatcher (W5).

    A ``gci_ambush`` doctrine (Vietnam) shrinks the engage radius to the doctrine's
    own close-fight ``cap_engagement_range`` (the P1c era number) and caps the
    scramble radius at :data:`AMBUSH_GCI_RADIUS_NM`; the returned flag additionally
    drives the Lua-side hit-and-run leash (fuel threshold + disengage radius).
    Every other doctrine passes the settings through untouched.
    """
    if not getattr(doctrine, "gci_ambush", False):
        return engagement_range_nm, gci_max_radius_nm, False
    ambush_engage = min(
        engagement_range_nm, round(doctrine.cap_engagement_range.nautical_miles)
    )
    ambush_scramble = min(gci_max_radius_nm, AMBUSH_GCI_RADIUS_NM)
    return ambush_engage, ambush_scramble, True


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


def populate_intercept_lua(
    root: "LuaData",
    entries: Iterable[InterceptEntry],
    player_alert_entries: Iterable[PlayerAlertEntry] = (),
) -> None:
    """Build the ``dcsRetribution.Intercept`` subtree (mirrors the IADS pattern).

    Always creates BLUE, RED, and PLAYER_ALERT buckets so the Lua side can iterate
    them unconditionally, then appends one record per reserved squadron (AI
    dispatcher) and one per player-manned alert base.
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

    alerts = intercept.get_or_create_item("PLAYER_ALERT")
    for alert in player_alert_entries:
        record = alerts.add_item()
        record.add_key_value("airbaseName", alert.airbase_name)
        record.add_key_value("coalition", alert.coalition)
        record.add_key_value("scrambleRadiusNm", str(alert.scramble_radius_nm))
