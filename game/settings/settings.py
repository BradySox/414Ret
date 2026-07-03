from collections.abc import Iterator
from dataclasses import Field, dataclass, field, fields
from datetime import timedelta
from enum import Enum, unique
from typing import Any, Dict, Optional

from dcs.forcedoptions import ForcedOptions

from .booleanoption import boolean_option
from .boundedfloatoption import bounded_float_option
from .boundedintoption import bounded_int_option
from .choicesoption import choices_option
from .minutesoption import minutes_option
from .optiondescription import OptionDescription, SETTING_DESCRIPTION_KEY
from .skilloption import skill_option
from ..ato.starttype import StartType
from ..ground_forces.combat_stance import CombatStance

Views = ForcedOptions.Views


@unique
class AutoAtoBehavior(Enum):
    Disabled = "Disabled"
    Never = "Never assign player pilots"
    Default = "No preference"
    Prefer = "Prefer player pilots"


@unique
class NightMissions(Enum):
    DayAndNight = "nightmissions_nightandday"
    OnlyDay = "nightmissions_onlyday"
    OnlyNight = "nightmissions_onlynight"


@unique
class FastForwardStopCondition(Enum):
    DISABLED = "Fast forward disabled"
    FIRST_CONTACT = "First contact"
    PLAYER_TAKEOFF = "Player takeoff time"
    PLAYER_TAXI = "Player taxi time"
    PLAYER_STARTUP = "Player startup time"
    PLAYER_AT_IP = "Player at IP"
    MANUAL = "Manual fast forward control"

    @property
    def player_preflight_phase(self) -> int | None:
        """Ordering of the player pre-flight stop conditions, earliest first.

        A player flight should halt the sim at the *earliest* pre-flight state it
        actually occupies whose phase is at or after the configured stop condition.
        This matters when the flight's start type skips earlier phases: a WARM
        (hot-ramp) flight enters at Taxi, so under the PLAYER_STARTUP condition it
        must halt at Taxi rather than fast-forwarding into the air (which would make
        its spawn_type IN_FLIGHT and spawn the player airborne).

        Returns None for conditions that are not player pre-flight phases.
        """
        return {
            FastForwardStopCondition.PLAYER_STARTUP: 0,
            FastForwardStopCondition.PLAYER_TAXI: 1,
            FastForwardStopCondition.PLAYER_TAKEOFF: 2,
        }.get(self)


@unique
class CombatResolutionMethod(Enum):
    PAUSE = "Pause simulation"
    RESOLVE = "Resolve combat"
    SKIP = "Skip combat"


@unique
class TargetIntelPrecision(Enum):
    EXACT = "Exact target coordinates"
    APPROXIMATE = "Approximate target area"


@unique
class AiRadioBehavior(Enum):
    FULL = "Normal callouts"
    LIMITED = "Suppress contact reports"
    SILENT = "Radio silence"


@unique
class DefaultPlayerLaserCode(Enum):
    DEFAULT_1688 = "Default (1688)"
    ALLOCATE_OWN = "Allocate own (unique per flight)"


class IadsEngine(Enum):
    """Save-compat stub. The Skynet IADS engine was removed (MANTIS is now the only
    engine), but the retired ``iads_engine`` setting persisted this enum in older
    campaign saves. The enum is kept *solely* so those saves still unpickle; the
    orphan value is then dropped by ``_migrate_legacy_settings``. No setting reads
    it. Safe to delete once no saved campaign predates the removal."""

    SKYNET = "skynet"
    MANTIS = "mantis"


SERIALIZABLE_ENUM_TYPES = (
    AutoAtoBehavior,
    NightMissions,
    FastForwardStopCondition,
    CombatResolutionMethod,
    TargetIntelPrecision,
    AiRadioBehavior,
    DefaultPlayerLaserCode,
    IadsEngine,
    CombatStance,
    StartType,
    Views,
)
SERIALIZABLE_ENUM_TYPES_BY_NAME = {
    enum_type.__name__: enum_type for enum_type in SERIALIZABLE_ENUM_TYPES
}


DIFFICULTY_PAGE = "Difficulty"

AI_DIFFICULTY_SECTION = "AI Difficulty"
MISSION_DIFFICULTY_SECTION = "Mission Difficulty"
MISSION_RESTRICTIONS_SECTION = "Mission Restrictions"

CAMPAIGN_MANAGEMENT_PAGE = "Campaign Management"

GENERAL_SECTION = "General"
PILOTS_AND_SQUADRONS_SECTION = "Pilots and Squadrons"
HQ_AUTOMATION_SECTION = "HQ Automation"
FLIGHT_PLANNER_AUTOMATION = "Flight Planner Automation"

CAMPAIGN_DOCTRINE_PAGE = "Campaign Doctrine"
DOCTRINE_DISTANCES_SECTION = "Doctrine distances"

MISSION_GENERATOR_PAGE = "Mission Generator"

GAMEPLAY_SECTION = "Gameplay"

KNEEBOARD_SECTION = "Kneeboard"

# TODO: Make sections a type and add headers.
# This section had the header: "Disabling settings below may improve performance, but
# will impact the overall quality of the experience."
PERFORMANCE_SECTION = "Performance"


# ---------------------------------------------------------------------------
# Settings UI information architecture (§28).
#
# The Settings dialog and the New Game wizard are both built entirely by walking
# Settings.pages() -> sections() -> fields(). Historically those followed raw
# field-declaration order, which scattered ~150 settings and left two 30+-item
# "General"/"Gameplay" grab-bag sections. `FIELD_LAYOUT` below is the single
# source of truth for how settings are grouped *and ordered* in the UI:
# field name -> (page, section). Page order = first appearance of a page here;
# section order = first appearance of a section within a page; field order =
# order here. Re-laying-out the UI is editing this table only — no field
# declaration moves, no behaviour change (field names/values/defaults are
# untouched). Any user field NOT listed here falls back to its own
# page=/section= metadata, so nothing is ever dropped.
#
# The legacy per-field page=/section= kwargs on the declarations are retained as
# that fallback; FIELD_LAYOUT overrides them for display.

# Pages (Campaign Management keeps its constant/label; Mission Generation's
# label now matches its existing icon key — see qt_ui/uiconstants.py).
DIFFICULTY_REALISM_PAGE = "Difficulty & Realism"
AIR_DOCTRINE_PAGE = "Air Doctrine"
MISSION_GENERATION_PAGE = "Mission Generation"
KNEEBOARDS_PAGE = "Kneeboards"
# Period-ops suite — Vietnam-era runtime mechanics, opt-in, default OFF globally and
# flipped ON by the Vietnam campaign YAMLs' settings: block. See
# docs/dev/design/414th-vietnam-ops-notes.md.
VIETNAM_OPS_PAGE = "Vietnam Ops"
PERFORMANCE_PAGE = "Performance"

_LAYOUT_SPEC: list[tuple[str, list[tuple[str, list[str]]]]] = [
    (
        DIFFICULTY_REALISM_PAGE,
        [
            (
                "AI skill & economy",
                [
                    "player_skill",
                    "enemy_skill",
                    "enemy_vehicle_skill",
                    "player_income_multiplier",
                    "enemy_income_multiplier",
                ],
            ),
            (
                "Player aids",
                [
                    "invulnerable_player_pilots",
                    "external_views_allowed",
                    "easy_communication",
                    "battle_damage_assessment",
                    "labels",
                    "map_coalition_visibility",
                ],
            ),
            (
                "Realism & restrictions",
                [
                    "manpads",
                    "night_day_missions",
                    "restrict_weapons_by_date",
                    "target_intel_precision",
                    "recon_intel_fog",
                    "scar_command_post_intel",
                    "ai_unlimited_fuel",
                ],
            ),
            (
                "Attrition & replacements",
                [
                    "ai_pilot_levelling",
                    "enable_squadron_pilot_limits",
                    "squadron_pilot_limit",
                    "squadron_replenishment_rate",
                    "enable_squadron_aircraft_limits",
                ],
            ),
        ],
    ),
    (
        AIR_DOCTRINE_PAGE,
        [
            (
                "Air defense & QRA",
                [
                    "ownfor_default_qra_reserve",
                    "opfor_default_qra_reserve",
                    "qra_gci_max_radius_nm",
                    "qra_engagement_range_nm",
                    "qra_comms_enabled",
                ],
            ),
            (
                "CAP & support timing",
                [
                    "desired_barcap_mission_duration",
                    "barcap_overlap_time",
                    "desired_awacs_mission_duration",
                    "desired_tanker_on_station_time",
                    "max_simultaneous_recovery_tankers",
                    "max_carrier_simultaneous_barcaps",
                    "aircraft_per_recovery_tanker",
                ],
            ),
            (
                "Tanker autoplanning",
                [
                    "autoplan_tankers_for_strike",
                    "autoplan_tankers_for_oca",
                    "autoplan_tankers_for_dead",
                ],
            ),
            (
                "Auto-planner behavior",
                [
                    "oca_target_autoplanner_min_aircraft_count",
                    "ownfor_autoplanner_aggressiveness",
                    "opfor_autoplanner_aggressiveness",
                    "ownfor_planner_unpredictability",
                    "opfor_planner_unpredictability",
                ],
            ),
            (
                "Recon & SCAR planning",
                [
                    "auto_add_tarps_recon",
                ],
            ),
            (
                "AI flight behavior",
                [
                    "atflir_autoswap",
                    "ai_jettison_empty_tanks",
                    "ai_vertical_takoff_landing",
                ],
            ),
            (
                "Altitudes",
                [
                    "heli_combat_alt_agl",
                    "heli_cruise_alt_agl",
                    "min_plane_altitude_offset",
                    "max_plane_altitude_offset",
                    "min_patrol_altitude",
                ],
            ),
            (
                "Threat & engagement distances",
                [
                    "airbase_threat_range",
                    "max_threat_range",
                    "cas_engagement_range_distance",
                    "armed_recon_engagement_range_distance",
                    "sead_sweep_engagement_range_distance",
                    "sead_threat_buffer_min_distance",
                    "sead_loiter_standoff_factor",
                    "sead_loiter_max_window_seconds",
                    "tarcap_threat_buffer_min_distance",
                    "aewc_threat_buffer_min_distance",
                    "tanker_threat_buffer_min_distance",
                    "max_mission_range_planes",
                    "max_mission_range_helicopters",
                ],
            ),
        ],
    ),
    (
        CAMPAIGN_MANAGEMENT_PAGE,
        [
            (
                "Campaign phases",
                [
                    "campaign_phases",
                ],
            ),
            (
                "Insurgency",
                [
                    "coin_insurgency",
                    "coin_reinfiltration",
                    "coin_ied",
                    "coin_hvt",
                    "coin_dispersed_cells",
                ],
            ),
            (
                "Carrier operations",
                [
                    "long_range_carrier_ops",
                ],
            ),
            (
                "HQ automation",
                [
                    "automate_runway_repair",
                    "automate_front_line_reinforcements",
                    "automate_aircraft_reinforcements",
                    "auto_ato_behavior",
                    "auto_ato_behavior_awacs",
                    "auto_ato_behavior_tankers",
                    "auto_ato_player_missions_asap",
                    "auto_combat_sar",
                    "automate_front_line_stance",
                    "default_front_line_stance",
                ],
            ),
            (
                "Economy & reserves",
                [
                    "auto_procurement_balance",
                    "frontline_reserves_factor",
                    "reserves_procurement_target",
                    "auto_procurement_balance_red",
                    "frontline_reserves_factor_red",
                    "reserves_procurement_target_red",
                ],
            ),
            (
                "Flight-planner automation",
                [
                    "fpa_2ship_weight",
                    "fpa_3ship_weight",
                    "fpa_4ship_weight",
                    "primary_task_distance_factor",
                ],
            ),
            (
                "Squadrons & loadouts",
                [
                    "squadron_random_chance",
                    "apply_target_overrides_to_loadouts",
                    "use_bandit_clouds",
                ],
            ),
        ],
    ),
    (
        MISSION_GENERATION_PAGE,
        [
            (
                "Simulation & fast-forward",
                [
                    "fast_forward_stop_condition",
                    "combat_resolution_method",
                    "never_delay_player_flights",
                    "use_ai_combat_landing",
                    "desired_player_mission_duration",
                ],
            ),
            (
                "Player slots & start",
                [
                    "default_start_type",
                    "default_start_type_client",
                    "dynamic_slots",
                    "dynamic_slots_hot",
                    "dynamic_cargo",
                    "player_flights_sixpack",
                    "untasked_opfor_client_slots",
                    "game_masters_count",
                    "tactical_commander_count",
                    "jtac_count",
                    "observer_count",
                    "player_startup_time",
                ],
            ),
            (
                "Cockpit & nav aids",
                [
                    "generate_portable_tacans",
                    "generate_marks",
                    "eplrs_enabled",
                    "default_player_laser_code",
                    "switch_baro_fix",
                    "ai_radio_behavior",
                ],
            ),
            (
                "Ground start",
                [
                    "ground_start_ai_planes",
                    "ground_start_scenery_remove_triggers",
                    "ground_start_trucks",
                    "ground_start_ground_power_trucks",
                    "ground_start_airbase_statics_farps_remove",
                ],
            ),
            (
                "Carrier",
                [
                    "supercarrier",
                    "supercarrier_deck_crew",
                ],
            ),
            (
                "World & systems",
                [
                    "max_frontline_width",
                    "use_auto_fog",
                    "base_battle_damage",
                ],
            ),
        ],
    ),
    (
        KNEEBOARDS_PAGE,
        [
            (
                "Kneeboards",
                [
                    "compact_kneeboard",
                    "generate_dark_kneeboard",
                    "generate_target_recon_kneeboard",
                    "generate_all_packages_kneeboard",
                    "generate_threat_intel_kneeboard",
                    "enable_package_code_words",
                    "generate_fuel_ladder_kneeboard",
                    "generate_sitrep_kneeboard",
                    "target_recon_extra_threat_search_nmi",
                ],
            ),
        ],
    ),
    (
        VIETNAM_OPS_PAGE,
        [
            (
                "Campaign",
                [
                    "vietnam_political_will",
                    "vietnam_static_front",
                ],
            ),
            (
                "Fire support",
                [
                    "vietnam_arc_light",
                    "vietnam_naval_gunfire",
                    "vietnam_snake_and_nape",
                ],
            ),
            (
                "Battlefield & interdiction",
                [
                    "vietnam_flak_gauntlet",
                    "vietnam_convoy_interdiction",
                    "vietnam_airbase_harassment",
                    "vietnam_super_gaggle",
                    "vietnam_fac_marking",
                ],
            ),
        ],
    ),
    (
        PERFORMANCE_PAGE,
        [
            (
                "World detail",
                [
                    "perf_smoke_gen",
                    "perf_smoke_spacing",
                    "perf_artillery",
                    "generate_fire_tasks_for_missile_sites",
                    "perf_moving_units",
                    "convoys_travel_full_distance",
                    "perf_disable_convoys",
                    "perf_disable_cargo_ships",
                    "perf_frontline_units_prefer_roads",
                    "perf_frontline_units_max_supply",
                    "perf_infantry",
                    "perf_destroyed_units",
                ],
            ),
            (
                "Culling & untasked units",
                [
                    "perf_disable_untasked_blufor_aircraft",
                    "perf_disable_untasked_opfor_aircraft",
                    "perf_culling",
                    "perf_culling_distance",
                    "perf_do_not_cull_threatening_iads",
                    "perf_do_not_cull_carrier",
                    "perf_ai_despawn_airstarted",
                ],
            ),
        ],
    ),
]

# Flattened field -> (page, section). Insertion order (and thus UI order) is the
# spec order above.
FIELD_LAYOUT: dict[str, tuple[str, str]] = {
    name: (page, section)
    for page, sections in _LAYOUT_SPEC
    for section, names in sections
    for name in names
}


@dataclass
class Settings:
    version: Optional[str] = None

    # Difficulty settings
    # AI Difficulty
    player_skill: str = skill_option(
        "Player coalition skill",
        page=DIFFICULTY_PAGE,
        section=AI_DIFFICULTY_SECTION,
        default="High",
    )
    enemy_skill: str = skill_option(
        "Enemy coalition skill",
        page=DIFFICULTY_PAGE,
        section=AI_DIFFICULTY_SECTION,
        default="High",
    )
    enemy_vehicle_skill: str = skill_option(
        "Enemy AA and vehicles skill",
        page=DIFFICULTY_PAGE,
        section=AI_DIFFICULTY_SECTION,
        default="High",
    )
    player_income_multiplier: float = bounded_float_option(
        "Player income multiplier",
        page=DIFFICULTY_PAGE,
        section=AI_DIFFICULTY_SECTION,
        min=0,
        max=5,
        divisor=10,
        default=1.0,
    )
    enemy_income_multiplier: float = bounded_float_option(
        "Enemy income multiplier",
        page=DIFFICULTY_PAGE,
        section=AI_DIFFICULTY_SECTION,
        min=0,
        max=5,
        divisor=10,
        default=1.0,
    )
    invulnerable_player_pilots: bool = boolean_option(
        "Player pilots cannot be killed",
        page=DIFFICULTY_PAGE,
        section=AI_DIFFICULTY_SECTION,
        detail=(
            "Aircraft are vulnerable, but the player's pilot will be returned to the "
            "squadron at the end of the mission"
        ),
        default=True,
    )
    # Mission Difficulty
    manpads: bool = boolean_option(
        "MANPADS on front lines",
        page=DIFFICULTY_PAGE,
        section=MISSION_DIFFICULTY_SECTION,
        default=True,
    )
    night_day_missions: NightMissions = choices_option(
        "Mission time of day",
        page=DIFFICULTY_PAGE,
        section=MISSION_DIFFICULTY_SECTION,
        choices={
            "Generate night and day missions": NightMissions.DayAndNight,
            "Only generate day missions": NightMissions.OnlyDay,
            "Only generate night missions": NightMissions.OnlyNight,
        },
        default=NightMissions.DayAndNight,
    )
    # Mission Restrictions
    labels: str = choices_option(
        "In-game labels",
        page=DIFFICULTY_PAGE,
        section=MISSION_RESTRICTIONS_SECTION,
        choices=["Full", "Abbreviated", "Dot Only", "Neutral Dot", "Off"],
        default="Full",
    )
    map_coalition_visibility: Views = choices_option(
        "Map visibility options",
        page=DIFFICULTY_PAGE,
        section=MISSION_RESTRICTIONS_SECTION,
        choices={
            "All": Views.All,
            "Fog of war": Views.Allies,
            "Allies only": Views.OnlyAllies,
            "Own aircraft only": Views.MyAircraft,
            "Map only": Views.OnlyMap,
        },
        default=Views.All,
    )
    external_views_allowed: bool = boolean_option(
        "Allow external views",
        DIFFICULTY_PAGE,
        MISSION_RESTRICTIONS_SECTION,
        default=True,
    )

    easy_communication: Optional[bool] = choices_option(
        "Easy communications",
        page=DIFFICULTY_PAGE,
        section=MISSION_RESTRICTIONS_SECTION,
        choices={"Player preference": None, "Enforced on": True, "Enforced off": False},
        default=None,
    )

    battle_damage_assessment: Optional[bool] = choices_option(
        "Battle damage assessment",
        page=DIFFICULTY_PAGE,
        section=MISSION_RESTRICTIONS_SECTION,
        choices={"Player preference": None, "Enforced on": True, "Enforced off": False},
        default=None,
    )

    # CAMPAIGN DOCTRINE
    desired_barcap_mission_duration: timedelta = minutes_option(
        "Desired BARCAP on-station time",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=timedelta(minutes=60),
        min=30,
        max=150,
        detail=(
            "Also determines how many BARCAP waves are planned: mission duration "
            "divided by desired on-station time."
        ),
    )
    barcap_overlap_time: timedelta = minutes_option(
        "BARCAP wave overlap",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=timedelta(minutes=15),
        min=0,
        max=60,
        detail="How long consecutive BARCAP waves overlap on-station. Higher values"
        " plan more, more-frequent waves so coverage has no handoff gap and the"
        " first wave's timing is less predictable. 0 restores back-to-back,"
        " non-overlapping waves (the legacy behaviour).",
    )
    ownfor_default_qra_reserve: int = bounded_int_option(
        "Default QRA reserve per OWNFOR interceptor squadron",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=0,
        min=0,
        max=12,
        detail=(
            "At new-game start, seeds this many QRA (hot-alert intercept) aircraft "
            "for each BARCAP-capable OWNFOR squadron. Per-squadron values can be "
            "edited afterward and are saved with the campaign."
        ),
    )
    opfor_default_qra_reserve: int = bounded_int_option(
        "Default QRA reserve per OPFOR interceptor squadron",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=0,
        min=0,
        max=12,
        detail=(
            "At new-game start, seeds this many QRA (hot-alert intercept) aircraft "
            "for each BARCAP-capable OPFOR squadron. Lets OPFOR lean on interception "
            "independently of OWNFOR. Per-squadron values can be edited afterward."
        ),
    )
    qra_gci_max_radius_nm: int = bounded_int_option(
        "QRA GCI max scramble radius (NM)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=60,
        min=1,
        max=400,
        detail=(
            "Caps how close a detected raid must be to a defended base before that "
            "base scrambles its QRA interceptors."
        ),
    )
    qra_engagement_range_nm: int = bounded_int_option(
        "QRA interceptor engagement range (NM)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=38,
        min=1,
        max=200,
        detail=(
            "How far a scrambled interceptor chases a target (Moose SetEngageRadius) "
            "before disengaging."
        ),
    )
    qra_comms_enabled: bool = boolean_option(
        "QRA radio scramble callouts",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "Enables the dispatcher's defender-POV radio/text callouts (scramble, "
            "wheels up, engaging, RTB) on the coalition F10 menu and radio TTS."
        ),
    )
    desired_awacs_mission_duration: timedelta = minutes_option(
        "Desired AWACS on-station time",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=timedelta(minutes=120),
        min=60,
        max=300,
        detail=(
            "Also determines how many AWACS flights are planned: mission duration "
            "divided by desired on-station time."
        ),
    )
    desired_tanker_on_station_time: timedelta = minutes_option(
        "Desired tanker on-station time",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=timedelta(minutes=60),
        min=30,
        max=150,
        detail=(
            "Also determines how many tanker flights are planned: mission duration "
            "divided by desired on-station time."
        ),
    )
    max_simultaneous_recovery_tankers: int = bounded_int_option(
        "Max simultaneous carrier recovery tankers",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=2,
        min=1,
        max=8,
        detail=(
            "Caps how many recovery (RECOVERY task) tankers may be on-station over a "
            "carrier at the same time. Extra recovery tankers are queued to start once "
            "an earlier one departs."
        ),
    )
    max_carrier_simultaneous_barcaps: int = bounded_int_option(
        "Max simultaneous carrier BARCAP waves",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=2,
        min=1,
        max=8,
        detail=(
            "How many BARCAP waves a carrier stacks on-station simultaneously before "
            "queueing the next wave to launch after the current ones recover. Land "
            "bases use overlapping waves instead (see BARCAP wave overlap)."
        ),
    )
    autoplan_tankers_for_strike: bool = boolean_option(
        "Auto-planner plans refueling flights for Strike packages",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=True,
        invert=False,
        detail=(
            "If checked, the auto-planner will include tankers in Strike packages, "
            "provided the faction has access to them."
        ),
    )
    autoplan_tankers_for_oca: bool = boolean_option(
        "Auto-planner plans refueling flights for OCA packages",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=True,
        invert=False,
        detail=(
            "If checked, the auto-planner will include tankers in OCA packages, "
            "provided the faction has access to them."
        ),
    )
    autoplan_tankers_for_dead: bool = boolean_option(
        "Auto-planner plans refueling flights for DEAD packages",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=True,
        invert=False,
        detail=(
            "If checked, the auto-planner will include tankers in DEAD packages, "
            "provided the faction has access to them."
        ),
    )
    auto_add_tarps_recon: bool = boolean_option(
        "Auto-planner adds TARPS recon flights to Strike/DEAD packages",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=True,
        invert=False,
        detail=(
            "If checked, the auto-planner appends a single photo-recon flight "
            "(e.g. F-14 TARPS) to Strike and DEAD packages against high-value "
            "targets (air defenses, factories, command posts, bridges). The recon "
            "bird overflies the target a couple of minutes behind the strikers "
            "for a post-strike BDA pass (kept tight so it stays under the package "
            "escort window). Requires a TARPS-capable squadron in range; if "
            "none is available the flight is simply skipped (the strike is never "
            "scrubbed)."
        ),
    )
    recon_intel_fog: bool = boolean_option(
        "Recon intel fog (hide enemy site composition until scouted)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=True,
        invert=False,
        detail=(
            "When enabled, enemy ground sites appear on the map as targets you can "
            "plan against, but what is actually there — unit types, counts, damage "
            "state, and threat/detection rings — stays hidden until the site is "
            "attacked, scouted by recon/TARPS, or has a unit destroyed. The AI "
            "planner and threat math always use full truth, so auto-planning is "
            "unaffected. Existing campaigns keep everything revealed; the fog "
            "applies to new campaigns."
        ),
    )
    scar_command_post_intel: bool = boolean_option(
        "SCAR command-post intel (hide enemy command posts until a commander is captured)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=True,
        invert=False,
        detail=(
            "When enabled, enemy command posts stay hidden on the map until you "
            "discover them the normal way — strike near them, scout them, or "
            "photograph them on a TARPS pass — so mapping the enemy command "
            "network is itself a reconnaissance task. On by default for new "
            "campaigns; existing campaigns keep whatever they were saved with. "
            "Turn it off to restore plain enemy command-post visibility."
        ),
    )
    aircraft_per_recovery_tanker: int = bounded_int_option(
        "Number of aircraft per recovery tanker",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=4,
        min=2,
        max=12,
        detail=(
            "A higher number will force the autoplanner to generate less recovery tankers."
        ),
    )
    oca_target_autoplanner_min_aircraft_count: int = bounded_int_option(
        "Minimum number of aircraft (at vulnerable airfields) for auto-planner to plan OCA packages against",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=20,
        min=0,
        max=100,
        detail=(
            "How many aircraft there has to be at an airfield for "
            "the auto-planner to plan an OCA strike against it."
        ),
    )
    ownfor_autoplanner_aggressiveness: int = bounded_int_option(
        "OWNFOR auto-planner aggressiveness (%)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=20,
        min=0,
        max=100,
        detail=(
            "Ratio of the threat-radius that will be ignored by the OWNFOR "
            "AI-autoplanner. 0% means the entire threat-radius is considered, "
            "while 100% would have the autoplanner completely ignore OPFOR air defences."
        ),
    )
    opfor_autoplanner_aggressiveness: int = bounded_int_option(
        "OPFOR auto-planner aggressiveness (%)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=20,
        min=0,
        max=100,
        detail=(
            "Ratio of the threat-radius that will be ignored by the OPFOR "
            "AI-autoplanner. 0% means the entire threat-radius is considered, "
            "while 100% would have the autoplanner completely ignore OWNFOR air defences."
        ),
    )
    ownfor_planner_unpredictability: int = bounded_int_option(
        "OWNFOR auto-planner unpredictability (%)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=0,
        min=0,
        max=100,
        detail=(
            "How much the OWNFOR auto-planner varies which opportunistic targets "
            "(strikes, OCA, BAI, anti-ship, non-threatening SAMs) it services first. "
            "0% keeps the deterministic, strict-priority planner; higher values let "
            "it sometimes service a lower-priority target first so its offensive "
            "target selection is less repetitive turn to turn. Reactive defensive "
            "tasking is unaffected."
        ),
    )
    opfor_planner_unpredictability: int = bounded_int_option(
        "OPFOR auto-planner unpredictability (%)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=0,
        min=0,
        max=100,
        detail=(
            "How much the OPFOR auto-planner varies which opportunistic targets "
            "(strikes, OCA, BAI, anti-ship, non-threatening SAMs) it services first. "
            "0% keeps the deterministic, strict-priority planner; higher values let "
            "it sometimes service a lower-priority target first so red's offensive "
            "target selection is less repetitive turn to turn. Reactive defensive "
            "tasking is unaffected."
        ),
    )
    heli_combat_alt_agl: int = bounded_int_option(
        "Helicopter combat altitude (feet AGL)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=200,
        min=1,
        max=10000,
        detail=(
            "Altitude for helicopters in feet AGL while flying between combat waypoints."
            " Combat waypoints are considered INGRESS, CAS, TGT, EGRESS & SPLIT."
            " In campaigns in more mountainous areas, you might want to increase this "
            "setting to avoid the AI flying into the terrain."
        ),
    )
    heli_cruise_alt_agl: int = bounded_int_option(
        "Helicopter cruise altitude (feet AGL)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=500,
        min=1,
        max=10000,
        detail=(
            "Altitude for helicopters in feet AGL while flying between non-combat waypoints."
            " In campaigns in more mountainous areas, you might want to increase this "
            "setting to avoid the AI flying into the terrain."
        ),
    )
    atflir_autoswap: bool = boolean_option(
        "Auto-swap ATFLIR to LITENING",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "Automatically swaps ATFLIR to LITENING pod for newly generated land-based F/A-18 flights "
            "without having to change the payload. <u>Takes effect after current turn!</u>"
        ),
    )
    ai_jettison_empty_tanks: bool = boolean_option(
        "Enable AI empty fuel tank jettison",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail="AI will jettison their fuel tanks as soon as they're empty.",
    )
    ai_vertical_takoff_landing: bool = boolean_option(
        "AI helicopters use vertical takeoff and landing",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail="AI will use vertical takeoff and landing instead of combat takeoff and landing.",
    )
    min_plane_altitude_offset: int = bounded_int_option(
        "Altitude scatter - lowest (x1000 ft)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        min=-5,
        max=5,
        default=-2,
        detail=(
            "AI flights are nudged off their planned altitude by a random amount so "
            "they don't all stack at the same height. This is the lowest nudge (use a "
            "negative value for below). Set lowest and highest to the same value to "
            "turn scatter off - both 0 for none."
        ),
    )
    max_plane_altitude_offset: int = bounded_int_option(
        "Altitude scatter - highest (x1000 ft)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        min=-5,
        max=5,
        default=2,
        detail=(
            "The highest nudge (positive is above the planned altitude). Examples: "
            "lowest -2 / highest +2 scatters within 2,000 ft; lowest 0 / highest +4 "
            "only ever climbs."
        ),
    )
    min_patrol_altitude: int = bounded_int_option(
        "Minimum patrol altitude (x1000 ft)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        min=0,
        max=40,
        default=0,
        detail=(
            "Raises CAP and patrol flights that would otherwise fly below this. "
            "Flights already planned higher are left alone. 0 turns it off (each "
            "aircraft uses its preferred altitude). Example: 28 keeps all CAP at "
            "28,000 ft or above."
        ),
    )

    player_startup_time: int = bounded_int_option(
        "Player startup allowance (minutes)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=10,
        min=0,
        max=100,
        detail=(
            "Time reserved for player startup before taxi (AI uses 2 minutes). "
            "Re-plan packages after changing this value."
        ),
    )

    # Doctrine Distances Section
    airbase_threat_range: int = bounded_int_option(
        "Airbase threat range (NM)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=DOCTRINE_DISTANCES_SECTION,
        default=100,
        min=0,
        max=300,
        detail=(
            "Will impact both defensive (BARCAP) and offensive flights. Also has a performance impact, "
            "lower threat range generally means less BARCAPs are planned."
        ),
    )
    max_threat_range: int = bounded_int_option(
        "Maximum threat range (NM)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=DOCTRINE_DISTANCES_SECTION,
        default=200,
        min=60,
        max=500,
        detail=(
            "Provides an upper limit to threat-ranges to avoid partial nav-meshes, which leads to errors. "
            "Lower this setting further if the map's bounds aren't covered by the nav-mesh."
        ),
    )
    cas_engagement_range_distance: int = bounded_int_option(
        "CAS engagement range (NM)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=DOCTRINE_DISTANCES_SECTION,
        default=15,
        min=0,
        max=100,
    )
    armed_recon_engagement_range_distance: int = bounded_int_option(
        "Armed Recon engagement range (NM)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=DOCTRINE_DISTANCES_SECTION,
        default=10,
        min=0,
        max=25,
    )
    sead_sweep_engagement_range_distance: int = bounded_int_option(
        "SEAD Sweep engagement range (NM)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=DOCTRINE_DISTANCES_SECTION,
        default=30,
        min=0,
        max=100,
    )
    sead_threat_buffer_min_distance: int = bounded_int_option(
        "SEAD Escort/Sweep threat buffer distance (NM)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=DOCTRINE_DISTANCES_SECTION,
        default=5,
        min=0,
        max=100,
        detail=(
            "How close to known threats will the SEAD Escort / SEAD Sweep engagement zone extend."
        ),
    )
    sead_loiter_standoff_factor: float = bounded_float_option(
        "SEAD loiter standoff factor (× threat range)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=DOCTRINE_DISTANCES_SECTION,
        default=0.8,
        min=0.1,
        max=2,
        divisor=10,
        detail=(
            "How far a loitering SEAD flight holds from its target, as a multiple of the "
            "target's threat range. 0.8 keeps it close (inside the engagement ring); raise "
            "toward/above 1.0 for a safer standoff if SEAD takes losses loitering. Only "
            "applies to targets with known threat-range data; others fall back to the flat "
            "sead_threat_buffer_min_distance."
        ),
    )
    sead_loiter_max_window_seconds: int = bounded_int_option(
        "SEAD loiter backstop window (seconds)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=DOCTRINE_DISTANCES_SECTION,
        default=1200,
        min=0,
        max=3600,
        detail=(
            "Fallback on-station time for a SEAD loiter when its package has no other "
            "flights to pace against. Normally the loiter holds until the last package "
            "member leaves the target area, then RTBs (or earlier when it runs out of "
            "ARMs); this value only applies to lone SEAD packages."
        ),
    )
    tarcap_threat_buffer_min_distance: int = bounded_int_option(
        "TARCAP threat buffer distance (NM)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=DOCTRINE_DISTANCES_SECTION,
        default=20,
        min=0,
        max=100,
        detail=("How close to known threats will the TARCAP racetrack extend."),
    )
    aewc_threat_buffer_min_distance: int = bounded_int_option(
        "AEW&C threat buffer distance (NM)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=DOCTRINE_DISTANCES_SECTION,
        default=80,
        min=0,
        max=300,
        detail=(
            "How far, at minimum, will AEW&C racetracks be planned "
            "to known threat zones."
        ),
    )
    tanker_threat_buffer_min_distance: int = bounded_int_option(
        "Theater tanker threat buffer distance (NM)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=DOCTRINE_DISTANCES_SECTION,
        default=70,
        min=0,
        max=300,
        detail=(
            "How far, at minimum, will theater tanker racetracks be "
            "planned to known threat zones."
        ),
    )
    max_mission_range_planes: int = bounded_int_option(
        "Auto-planner maximum mission range for airplanes (NM)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=DOCTRINE_DISTANCES_SECTION,
        default=150,
        min=150,
        max=1000,
        detail=(
            "The maximum mission distance that's used by the auto-planner for airplanes. "
            "This setting won't take effect when a larger "
            "range is defined in the airplane's yaml specification."
        ),
    )
    max_mission_range_helicopters: int = bounded_int_option(
        "Auto-planner maximum mission range for helicopters (NM)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=DOCTRINE_DISTANCES_SECTION,
        default=100,
        min=50,
        max=1000,
        detail=(
            "The maximum mission distance that's used by the auto-planner for helicopters. "
            "This setting won't take effect when a larger "
            "range is defined in the helicopter's yaml specification."
        ),
    )

    # Campaign management
    # General
    squadron_random_chance: int = bounded_int_option(
        "Generated-squadron aircraft randomization (%)",
        page=CAMPAIGN_MANAGEMENT_PAGE,
        section=GENERAL_SECTION,
        default=50,
        min=0,
        max=100,
        detail=(
            "Aircraft type selection is governed by the campaign and the squadron definitions available to "
            "Retribution. Squadrons are generated by Retribution if the faction does not have access to the campaign "
            "designer's squadron/aircraft definitions. Use the above to increase/decrease aircraft variety by making "
            "some selections random instead of picking aircraft types from a priority list."
        ),
    )
    restrict_weapons_by_date: bool = boolean_option(
        "Restrict weapons by campaign date (incomplete data)",
        page=CAMPAIGN_MANAGEMENT_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "Restricts weapon availability based on the campaign date. Data is "
            "extremely incomplete so does not affect all weapons."
        ),
    )
    coin_insurgency: bool = boolean_option(
        "COIN insurgent replenishment",
        page=CAMPAIGN_MANAGEMENT_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "The enemy fights as an insurgency: its strongholds freely regenerate a "
            "small trickle of irregular units each turn (infantry, technicals, AAA "
            "-- never armor or SAMs), refilling toward their campaign-start garrison "
            "but never growing. The rate is throttled by each stronghold's ammo "
            "caches -- find and destroy them to collapse the trickle to a residual "
            "floor. Body count alone cannot win; caches, the supply trail, and "
            "patience decide. Intended for COIN campaigns that preseed it on."
        ),
    )
    coin_reinfiltration: bool = boolean_option(
        "COIN re-infiltration (insurgency retakes ground)",
        page=CAMPAIGN_MANAGEMENT_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "The insurgency can retake ground you cleared but did not hold. Over "
            "several turns an under-garrisoned base near a healthy stronghold draws "
            "a staged, announced infiltration -- a cell appears, then a supply cache, "
            "then the base changes hands -- each stage a real unit on the map you can "
            "strike to stop it. Garrison it, kill the cell or cache, or strangle the "
            "source stronghold's caches to break the attempt. Total insurgent bases "
            "never exceed the campaign start (relocate, never grow); a completed flip "
            "drains your mandate like any lost base. Requires COIN replenishment on; "
            "intended for COIN campaigns that preseed it."
        ),
    )
    coin_ied: bool = boolean_option(
        "COIN roadside IEDs (sweep the trail)",
        page=CAMPAIGN_MANAGEMENT_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "The insurgent supply roads are mined. Hidden IED emplacements appear on "
            "the ratline -- ordinary recon-fogged targets you must find (TARPS/ISR) and "
            "strike (CAS/Armed Recon) within a few turns. An IED you clear costs the "
            "insurgency nothing but the device; one you leave un-swept detonates on the "
            "coalition and drains your mandate (priced by the campaign's will profile). "
            "Requires COIN replenishment on; intended for COIN campaigns that preseed it."
        ),
    )
    coin_hvt: bool = boolean_option(
        "COIN high-value targets (hunt the leadership)",
        page=CAMPAIGN_MANAGEMENT_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "The war is a manhunt. A named insurgent leader periodically surfaces near "
            "a stronghold for a limited strike window -- a real recon-fogged target. "
            "Killing him inside the window is a blow to the insurgency's momentum, but "
            "he often shelters among his people (a stronghold on a population ring), so "
            "the strike carries the collateral-damage dilemma the rings price: take the "
            "shot dirty (a momentum blow AND a mandate-draining ROE violation), wait for "
            "a clean one, or let the window close. Requires COIN replenishment on; "
            "intended for COIN campaigns that preseed it."
        ),
    )
    coin_dispersed_cells: bool = boolean_option(
        "COIN dispersed cells (patrol the countryside)",
        page=CAMPAIGN_MANAGEMENT_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "The insurgency operates between the strongholds, not just in them. Small "
            "recon-fogged cells appear out in the open countryside -- patrol for them "
            "(TARPS + CAS), don't just hit known positions. A cell you leave alone "
            "matures and slips into its home stronghold, bringing a destroyed ammo cache "
            "back into operation (re-opening the regeneration you worked to shut off), "
            "or reinforcing its garrison. Hunting the field cells is how you keep a "
            "stronghold starved. Requires COIN replenishment on; intended for COIN "
            "campaigns that preseed it."
        ),
    )
    long_range_carrier_ops: bool = boolean_option(
        "Long-range carrier strike package",
        page=CAMPAIGN_MANAGEMENT_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "For campaigns whose carrier stands off far beyond the auto-planner's "
            "reach (e.g. the Arabian-Sea cycle ~800 km from Afghanistan): frag one "
            "deterministic carrier strike package each turn from the boat's own "
            "squadrons -- a Hornet section on the nearest legal target, an A-6 tanker "
            "escorting the route (ingress/egress), and an E-2 on AEWC -- which the "
            "stock range-gated planner would otherwise leave on the deck. Also raise "
            "'Auto-planner maximum mission range for airplanes' so the carrier air is "
            "assignable to the wider war. Intended for campaigns that preseed it on."
        ),
    )
    apply_target_overrides_to_loadouts: bool = boolean_option(
        "Apply target-based weapon settings to player loadouts",
        page=CAMPAIGN_MANAGEMENT_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "When enabled, applies target-specific weapon settings from weapon "
            "configurations to player-controlled aircraft. AI aircraft always receive "
            "target-based settings. This includes settings for degraded loadouts."
        ),
    )
    use_bandit_clouds: bool = boolean_option(
        "Use Bandit's clouds",
        page=CAMPAIGN_MANAGEMENT_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=("If checked, Bandit's cloud presets will become available."),
    )

    # Pilots and Squadrons
    ai_pilot_levelling: bool = boolean_option(
        "Allow AI pilot leveling",
        CAMPAIGN_MANAGEMENT_PAGE,
        PILOTS_AND_SQUADRONS_SECTION,
        default=True,
        detail=(
            "Set whether or not AI pilots will level up after completing a number of"
            " sorties. Since pilot level affects the AI skill, you may wish to disable"
            " this, lest you face an Ace!"
        ),
    )
    #: Feature flag for squadron limits.
    enable_squadron_pilot_limits: bool = boolean_option(
        "Enable per-squadron pilot limits",
        CAMPAIGN_MANAGEMENT_PAGE,
        PILOTS_AND_SQUADRONS_SECTION,
        default=True,
        detail=(
            "If set, squadrons will be limited to a maximum number of pilots and dead "
            "pilots will replenish at a fixed rate, each defined with the settings "
            "below. Auto-purchase may buy aircraft for which there are no pilots"
            "available, so this feature is still a work-in-progress."
        ),
    )
    #: The maximum number of pilots a squadron can have at one time. Changing this after
    #: the campaign has started will have no immediate effect; pilots already in the
    #: squadron will not be removed if the limit is lowered and pilots will not be
    #: immediately created if the limit is raised.
    squadron_pilot_limit: int = bounded_int_option(
        "Maximum number of pilots per squadron",
        CAMPAIGN_MANAGEMENT_PAGE,
        PILOTS_AND_SQUADRONS_SECTION,
        default=16,
        min=6,
        max=72,
        detail=(
            "Sets the maximum number of pilots a squadron may have active. "
            "Changing this value will not have an immediate effect, but will alter "
            "replenishment for future turns."
        ),
    )
    #: The number of pilots a squadron can replace per turn.
    squadron_replenishment_rate: int = bounded_int_option(
        "Squadron pilot replenishment rate",
        CAMPAIGN_MANAGEMENT_PAGE,
        PILOTS_AND_SQUADRONS_SECTION,
        default=4,
        min=1,
        max=20,
        detail=(
            "Sets the maximum number of pilots that will be recruited to each squadron "
            "at the end of each turn. Squadrons will not recruit new pilots beyond the "
            "pilot limit, but each squadron with room for more pilots will recruit "
            "this many pilots each turn up to the limit."
        ),
    )
    # Feature flag for squadron limits.
    enable_squadron_aircraft_limits: bool = boolean_option(
        "Enable per-squadron aircraft limits",
        CAMPAIGN_MANAGEMENT_PAGE,
        PILOTS_AND_SQUADRONS_SECTION,
        default=False,
        detail=(
            "If set, squadrons will not be able to buy more aircraft than the configured maximum."
        ),
    )

    # Campaign phases (W3, docs/dev/design/414th-campaign-phases-notes.md). Tier-0
    # inference is the DECIDED default for every campaign; this is the kill switch.
    campaign_phases: bool = boolean_option(
        "Campaign phases",
        CAMPAIGN_MANAGEMENT_PAGE,
        "Campaign phases",
        detail=(
            "The campaign tracks what phase of the air war it is in -- Air "
            "Superiority (roll back the SAM belt, blunt enemy fighters), "
            "Interdiction (choke reinforcement and logistics), then the Offensive "
            "(take ground) -- inferred each turn from the live IADS, air threat, and "
            "front movement. The phase shows on the kneeboard and status band, and "
            "the auto-planner leans its offensive tasking to match. Reactive defense "
            "is never affected. Turn off for the phase-blind stock planner."
        ),
        default=True,
    )

    # HQ Automation
    automate_runway_repair: bool = boolean_option(
        "Automate runway repairs",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        default=False,
    )
    automate_front_line_reinforcements: bool = boolean_option(
        "Automate front-line purchases",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        default=False,
    )
    automate_aircraft_reinforcements: bool = boolean_option(
        "Automate aircraft purchases",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        default=False,
    )
    auto_ato_behavior: AutoAtoBehavior = choices_option(
        "Automatic package planning behavior",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        default=AutoAtoBehavior.Default,
        choices={v.value: v for v in AutoAtoBehavior},
        detail=(
            "Aircraft auto-purchase is directed by the auto-planner, so disabling "
            "auto-planning disables auto-purchase."
        ),
    )
    auto_ato_behavior_awacs: bool = boolean_option(
        "Automatic AWACS package planning",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        default=True,
    )
    auto_ato_behavior_tankers: bool = boolean_option(
        "Automatic theater-tanker package planning",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        default=False,
    )
    auto_ato_player_missions_asap: bool = boolean_option(
        "Automatically generated packages with players are scheduled ASAP",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        default=True,
    )
    auto_combat_sar: bool = boolean_option(
        "Automatic Combat SAR (pilot-rescue) standing alert",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        default=True,
        detail=(
            "Auto-plan a Combat SAR package (King + rescue helo + Sandy) near each "
            "active front so a downed pilot can be rescued even with no player CSAR "
            "flown -- rescue is a normal, standing task. Requires a rescue-helo-"
            "capable squadron; a human can always fly the rescue instead. Turn OFF "
            "to only fly rescues manually. (Default ON since the 2026-07-03 CSAR "
            "rescope; existing campaigns keep their saved choice.)"
        ),
    )
    automate_front_line_stance: bool = boolean_option(
        "Automatically manage front line stances",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        default=True,
    )
    default_front_line_stance: CombatStance = choices_option(
        "Default front line stance",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        # RETREAT is intentionally omitted -- never a sensible standing default.
        choices={
            "Aggressive": CombatStance.AGGRESSIVE,
            "Defensive": CombatStance.DEFENSIVE,
            "Ambush": CombatStance.AMBUSH,
            "Elimination": CombatStance.ELIMINATION,
            "Breakthrough": CombatStance.BREAKTHROUGH,
        },
        default=CombatStance.AGGRESSIVE,
        detail=(
            "Starting stance for your front lines at campaign start and after a "
            "capture. Only applies when 'Automatically manage front line stances' "
            "is off; otherwise the AI commander chooses the stance."
        ),
    )
    auto_procurement_balance: int = bounded_int_option(
        "AI ground unit procurement budget ratio (%) for OWNFOR",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        min=0,
        max=100,
        default=50,
        detail=(
            "Ratio (larger number -> more budget for ground units) "
            "that indicates how the AI procurement planner should "
            "spend its budget."
        ),
    )
    frontline_reserves_factor: int = bounded_int_option(
        "AI ground unit front-line reserves factor (%) for OWNFOR",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        min=0,
        max=1000,
        default=130,
        detail=(
            "Factor to be multiplied with the control point's unit count limit "
            "to calculate the procurement target for reserve troops at front-lines."
        ),
    )
    reserves_procurement_target: int = bounded_int_option(
        "AI ground unit reserves procurement target for OWNFOR",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        min=0,
        max=1000,
        default=10,
        detail=(
            "The number of units that will be bought as reserves for applicable control points."
        ),
    )
    auto_procurement_balance_red: int = bounded_int_option(
        "AI ground unit procurement budget ratio (%) for OPFOR",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        min=0,
        max=100,
        default=50,
        detail=(
            "Ratio (larger number -> more budget for ground units) "
            "that indicates how the AI procurement planner should "
            "spend its budget."
        ),
    )
    frontline_reserves_factor_red: int = bounded_int_option(
        "AI ground unit front-line reserves factor (%) for OPFOR",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        min=0,
        max=1000,
        default=130,
        detail=(
            "Factor to be multiplied with the control point's unit count limit "
            "to calculate the procurement target for reserve troops at front-lines."
        ),
    )
    reserves_procurement_target_red: int = bounded_int_option(
        "AI ground unit reserves procurement target for OPFOR",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        min=0,
        max=1000,
        default=10,
        detail=(
            "The number of units that will be bought as reserves for applicable control points."
        ),
    )

    # Flight Planner Automation
    #: The weight used for 2-ships.
    fpa_2ship_weight: int = bounded_int_option(
        "2-ship weight factor (WF2)",
        CAMPAIGN_MANAGEMENT_PAGE,
        FLIGHT_PLANNER_AUTOMATION,
        default=50,
        min=0,
        max=100,
        detail=(
            "Used as a distribution to randomize 2/3/4-ships for BARCAP, CAS, OCA & ANTI-SHIP flights. "
            "The weight W_i is calculated according to the following formula: &#10;&#13;"
            "W_i = WF_i / (WF2 + WF3 + WF4)"
        ),
    )
    #: The weight used for 3-ships.
    fpa_3ship_weight: int = bounded_int_option(
        "3-ship weight factor (WF3)",
        CAMPAIGN_MANAGEMENT_PAGE,
        FLIGHT_PLANNER_AUTOMATION,
        default=35,
        min=0,
        max=100,
        detail="Relative weight used with WF2 and WF4; see the 2-ship setting.",
    )
    fpa_4ship_weight: int = bounded_int_option(
        "4-ship weight factor (WF4)",
        CAMPAIGN_MANAGEMENT_PAGE,
        FLIGHT_PLANNER_AUTOMATION,
        default=15,
        min=0,
        max=100,
        detail="Relative weight used with WF2 and WF3; see the 2-ship setting.",
    )
    primary_task_distance_factor: int = bounded_int_option(
        "Primary task distance weight (NM)",
        CAMPAIGN_MANAGEMENT_PAGE,
        FLIGHT_PLANNER_AUTOMATION,
        default=75,
        min=10,
        max=250,
        detail="A larger number will force the auto-planner to stick with squadrons that have a matching primary task."
        " A smaller number will ignore squadrons with a matching primary task that are too far out.",
    )

    # Mission Generator
    # Gameplay
    fast_forward_stop_condition: FastForwardStopCondition = choices_option(
        "Fast forward until",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=FastForwardStopCondition.PLAYER_STARTUP,
        choices={
            "No fast forward": FastForwardStopCondition.DISABLED,
            "Player startup time": FastForwardStopCondition.PLAYER_STARTUP,
            "Player taxi time": FastForwardStopCondition.PLAYER_TAXI,
            "Player takeoff time": FastForwardStopCondition.PLAYER_TAKEOFF,
            "Player at IP": FastForwardStopCondition.PLAYER_AT_IP,
            "First contact": FastForwardStopCondition.FIRST_CONTACT,
            "Manual": FastForwardStopCondition.MANUAL,
        },
        detail=(
            "Determines when fast forwarding stops: "
            "No fast forward: disables fast forward. "
            "Player startup time: fast forward until player startup time. "
            "Player taxi time: fast forward until player taxi time. "
            "Player takeoff time: fast forward until player takeoff time. "
            "First contact: fast forward until first contact between blue and red units. "
            "Manual: manually control fast forward. Show manual controls with --show-sim-speed-controls."
        ),
    )
    combat_resolution_method: CombatResolutionMethod = choices_option(
        "Combat encountered during fast-forward",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=CombatResolutionMethod.PAUSE,
        choices={
            "Pause": CombatResolutionMethod.PAUSE,
            "Resolving combat (WIP)": CombatResolutionMethod.RESOLVE,
            "Skipping combat": CombatResolutionMethod.SKIP,
        },
        detail=(
            "Pause stops fast-forward so the combat can be flown. Resolve uses the "
            "rudimentary campaign simulation and can cause heavy losses. Skip ignores "
            "the combat. This may stop fast-forward before the selected stop condition."
        ),
    )
    supercarrier: bool = boolean_option(
        "Use supercarrier module",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=False,
    )
    supercarrier_deck_crew: bool = boolean_option(
        "Use supercarrier deck-crew",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
    )
    generate_portable_tacans: bool = boolean_option(
        "Place portable TACAN beacons at blue airfields",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=False,
        detail=(
            "Automatically places a portable TACAN beacon at blue-captured "
            "airfields that don't already have a built-in TACAN from the "
            "terrain data. An unused X-band channel is assigned to each."
        ),
    )
    generate_marks: bool = boolean_option(
        "Put objective markers on the map",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
    )
    target_intel_precision: TargetIntelPrecision = choices_option(
        "Player target location precision",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        choices={
            "Exact target coordinates": TargetIntelPrecision.EXACT,
            "Approximate target area": TargetIntelPrecision.APPROXIMATE,
        },
        default=TargetIntelPrecision.EXACT,
        detail=(
            "Approximate mode offsets player-facing target steerpoints into a nearby "
            "search area, suppresses objective F10 map marks, and removes exact "
            "target coordinates from strike/SEAD kneeboards."
        ),
    )
    eplrs_enabled: bool = boolean_option(
        "Enable EPLRS",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
    )
    generate_dark_kneeboard: bool = boolean_option(
        "Generate dark kneeboard",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=False,
        detail=(
            "Dark kneeboard for night missions. This will likely make the kneeboard on "
            "the pilot leg unreadable."
        ),
    )
    compact_kneeboard: bool = boolean_option(
        "Compact kneeboard (3-4 pages)",
        MISSION_GENERATOR_PAGE,
        KNEEBOARD_SECTION,
        default=True,
        detail=(
            "Consolidate the player kneeboard into at most four pages — Game Plan "
            "(BLUF + route + fuel + fields + weather), Threats & Targets (enemy "
            "air-defense cards + target ALIC), Comms & Coordination (radios + "
            "AWACS/tanker/JTAC + code words + brevity + friendly packages), and an "
            "adaptive flex page: the recon target photo when target-recon imagery is "
            "enabled, otherwise the Fuel Ladder + the full friendly-package list. The "
            "optional kneeboard sections below fold into these pages instead of adding "
            "their own, and the flex page only appears when it has content. The "
            "theater/package-targets map is not generated in this mode. Turn off for "
            "the full multi-page deck."
        ),
    )
    generate_target_recon_kneeboard: bool = boolean_option(
        "Generate target recon kneeboard pages",
        MISSION_GENERATOR_PAGE,
        KNEEBOARD_SECTION,
        default=False,
        detail=(
            "Generate target/airfield reconnaissance pages for player flights with "
            "air-to-ground tasks, showing aimpoints, threat rings, and target area "
            "context over satellite imagery. Off by default: the marker overlays do "
            "not reliably line up with the underlying satellite tiles."
        ),
    )
    generate_all_packages_kneeboard: bool = boolean_option(
        "Generate friendly packages kneeboard page",
        MISSION_GENERATOR_PAGE,
        KNEEBOARD_SECTION,
        default=False,
        detail=(
            "Append page(s) listing every friendly package with its TOT (strike "
            "tasks) or patrol window (CAP, tanker, AWACS), for cross-package "
            "coordination. Off by default: adds a Friendly Packages section to the "
            "Mission Info page plus a package-targets map, which can spill onto "
            "continuation pages on busy theaters."
        ),
    )
    generate_threat_intel_kneeboard: bool = boolean_option(
        "Generate threat intel brief kneeboard page",
        MISSION_GENERATOR_PAGE,
        KNEEBOARD_SECTION,
        default=False,
        detail=(
            "Append a Threat Intel Brief page: the enemy air-defense laydown "
            "(SAM/EWR system, engagement range, HARM ALIC code, bullseye cue and "
            "live/degraded/dead status), modelled on the per-system threat cards in "
            "professional campaign intelligence briefings. Recon-fog aware — an "
            "undiscovered site shows only its intel-tier band ('Unidentified MERAD') "
            "until a TARPS overflight identifies it. Off by default."
        ),
    )
    enable_package_code_words: bool = boolean_option(
        "Package code words & comms/brevity card",
        MISSION_GENERATOR_PAGE,
        KNEEBOARD_SECTION,
        default=False,
        detail=(
            "Give each package three SRS code words (push / success / abort) and surface "
            "them so a briefing can be built before generation: a package tooltip in the "
            "ATO list and a 'PUSH <word>' tag on the join waypoint, plus a Comms & "
            "Brevity kneeboard page (the code words + a task-filtered brevity crib). "
            "Human comms aids only — nothing scripts off them. Off by default."
        ),
    )
    generate_fuel_ladder_kneeboard: bool = boolean_option(
        "Generate fuel ladder kneeboard page",
        MISSION_GENERATOR_PAGE,
        KNEEBOARD_SECTION,
        default=False,
        detail=(
            "Append a Fuel Ladder page: the planned fuel remaining vs. the minimum to "
            "RTB at each steerpoint, plus the margin between them and Bingo/Joker. The "
            "burn model is an estimate, so treat the numbers as planning figures. Off "
            "by default."
        ),
    )
    generate_sitrep_kneeboard: bool = boolean_option(
        "Campaign SITREP band on the briefing page",
        MISSION_GENERATOR_PAGE,
        KNEEBOARD_SECTION,
        default=True,
        detail=(
            "Add a short 'what happened last turn' band to the briefing/Game Plan "
            "kneeboard page: both sides' losses (enemy as claimed), bases captured or "
            "lost, and downed pilots recovered. Hidden on turn 1 and after a quiet "
            "turn, and only drawn when it fits under the flight plan. On by default."
        ),
    )
    target_recon_extra_threat_search_nmi: int = bounded_int_option(
        "Extra threat search radius (nmi)",
        MISSION_GENERATOR_PAGE,
        KNEEBOARD_SECTION,
        default=0,
        min=0,
        max=50,
        detail=(
            "Additional nautical miles beyond the default search radius to include "
            "threats on the target recon kneeboard. 0 uses the default radius only."
        ),
    )
    never_delay_player_flights: bool = boolean_option(
        "Spawn player flights immediately (keep planned TOT)",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
        detail=(
            "Does not adjust package waypoint times. Should not be used if players "
            "have runway or in-air starts."
        ),
        tooltip=(
            "Always spawns player aircraft immediately, even if their start time is "
            "more than 10 minutes after the start of the mission. <strong>This does "
            "not alter the timing of your mission. Your TOT will not change. This "
            "option only allows the player to wait on the ground.</strong>"
        ),
    )
    untasked_opfor_client_slots: bool = boolean_option(
        "Convert untasked OPFOR aircraft into client slots",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=False,
        detail=(
            "Warning: Enabling this will significantly reduce the number of "
            "targets available for OCA/Aircraft missions."
        ),
    )
    default_start_type: StartType = choices_option(
        "Default start type for AI aircraft",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        choices={v.value: v for v in StartType},
        default=StartType.COLD,
        detail=(
            "Warning: Options other than Cold will significantly reduce the number of "
            "targets available for OCA/Aircraft missions, and OCA/Aircraft flights "
            "will not be included in automatically planned OCA packages."
        ),
    )
    default_start_type_client: StartType = choices_option(
        "Default start type for player flights",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        choices={v.value: v for v in StartType},
        default=StartType.COLD,
        detail="Default start type for flights containing Player/Client slots.",
    )
    default_player_laser_code: DefaultPlayerLaserCode = choices_option(
        "Default laser code for Player flights",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        choices={v.value: v for v in DefaultPlayerLaserCode},
        default=DefaultPlayerLaserCode.ALLOCATE_OWN,
        detail=(
            "Allocate own gives every newly-created player flight a unique TGP/"
            "weapon laser code. Default (1688) leaves the code unset so bombs "
            "and the cockpit TGP fall back to 1688. Affects newly-created "
            "flights only; existing flights are unchanged."
        ),
    )
    switch_baro_fix: bool = boolean_option(
        "Use AMSL helicopter waypoints over water (DCS workaround)",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=True,  # TODO: set to False or remove this when DCS is fixed?
        detail=(
            "Works around DCS treating over-water AGL altitude as relative to the sea "
            "floor, which can send low-flying helicopters below the surface."
        ),
    )
    ai_radio_behavior: AiRadioBehavior = choices_option(
        "AI wingman radio behavior in player flights",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        choices={behavior.value: behavior for behavior in AiRadioBehavior},
        default=AiRadioBehavior.LIMITED,
        detail=(
            "Controls AI wingmen in flights containing human slots. Normal keeps "
            "standard DCS calls; Suppress contact reports removes target-detection "
            "spam; Radio silence suppresses all AI calls. AWACS flights are unaffected."
        ),
    )
    use_ai_combat_landing: bool = boolean_option(
        "Use AI combat landing waypoint task",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=False,
        detail="Turns the combat landing flag on in the landing waypoint task.",
    )
    # Mission specific
    desired_player_mission_duration: timedelta = minutes_option(
        "Desired mission duration",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=timedelta(minutes=60),
        min=30,
        max=150,
    )
    max_frontline_width: int = bounded_int_option(
        "Maximum frontline width (km)",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=80,
        min=1,
        max=100,
    )
    game_masters_count: int = bounded_int_option(
        "Game Master slots per coalition",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=1,
        min=0,
        max=10,
        detail=(
            "The number of game master slots to generate for each side. "
            "Game masters can see, control & direct all units in the mission."
        ),
    )
    tactical_commander_count: int = bounded_int_option(
        "Tactical Commander slots per coalition",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=3,
        min=0,
        max=10,
        detail=(
            "The number of tactical commander slots to generate for each side. "
            "Tactical commanders can control & direct friendly units."
        ),
    )
    jtac_count: int = bounded_int_option(
        "JTAC slots per coalition",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=3,
        min=0,
        max=10,
        detail=(
            "The number of JTAC controller slots to generate for each side. "
            "JTAC operators can only control friendly units."
        ),
    )
    observer_count: int = bounded_int_option(
        "Observer slots per coalition",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=0,
        min=0,
        max=10,
        detail=(
            "The number of observer slots to generate for each side. "
            'Use this to allow spectators when disabling "Allow external views".'
        ),
    )
    ground_start_ai_planes: bool = boolean_option(
        "AI fixed-wing aircraft can use roadbases / bases with only ground spawns",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=False,
        detail=(
            "If enabled, AI can use roadbases or airbases which only have ground spawns. "
            "AI will always air-start from these bases (due to DCS limitation)."
        ),
    )
    ground_start_scenery_remove_triggers: bool = boolean_option(
        "Generate SCENERY REMOVE OBJECTS ZONE triggers at roadbase first waypoints",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
        detail=(
            "Can be used to remove lightposts and other obstacles from roadbase runways. "
            "Might not work in DCS multiplayer."
        ),
    )
    ground_start_trucks: bool = boolean_option(
        "Spawn supply trucks at ground starts instead of FARP statics",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=False,
        detail=(
            "Applies to both airbases and roadbases. "
            "Might have a negative performance impact."
        ),
    )
    ground_start_ground_power_trucks: bool = boolean_option(
        "Spawn ground power trucks at ground starts",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
        detail=(
            "Applies to both airbases and roadbases. Needed to cold-start some "
            "aircraft types. Might have a performance impact."
        ),
    )
    ground_start_airbase_statics_farps_remove: bool = boolean_option(
        "Remove ground spawn statics, including invisible FARPs, at airbases",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
        detail=(
            "Ammo and fuel statics and invisible FARPs should be unnecessary when creating "
            "additional spawns for players at airbases. This setting will disable them and "
            "potentially grant a marginal performance benefit."
        ),
    )
    ai_unlimited_fuel: bool = boolean_option(
        "AI flights have unlimited fuel",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
        detail=(
            "AI aircraft have unlimited fuel applied at start, removed at join/racetrack start,"
            " and reapplied at split/racetrack end for applicable flights. "
        ),
    )
    dynamic_slots: bool = boolean_option(
        "Enable dynamic player slots",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=False,
        detail=(
            "Enables dynamic slots. Please note that losses from dynamic slots won't be registered."
        ),
    )
    dynamic_slots_hot: bool = boolean_option(
        "Allow hot starts in dynamic slots",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
        detail=("Enables hot start for dynamic slots."),
    )
    dynamic_cargo: bool = boolean_option(
        "Enable DCS dynamic cargo",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
        detail=("Enables dynamic cargo for airfields, ships, FARPs & warehouses."),
    )
    player_flights_sixpack: bool = boolean_option(
        "Player flights can spawn on the sixpack",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
    )
    use_auto_fog: bool = boolean_option(
        "Use DCS' automatic fog setting",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
    )

    base_battle_damage: bool = boolean_option(
        "Battle damage at depleted bases (fires, smoke, wreckage)",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        detail=(
            "A base's ground strength drives how battered it looks: a besieged, ground-down "
            "field gets scattered fires, smoke and destroyed-building wreckage so it reads as "
            "under siege, while staying fully operational (cosmetic only -- the runway is "
            "untouched). Costs some FPS; turn off if a heavily-hit base impacts performance."
        ),
        default=True,
    )

    # Vietnam Ops (period-ops suite) -- opt-in Vietnam-era runtime mechanics. All
    # default OFF globally; the Vietnam campaign YAMLs flip the relevant ones ON via
    # their settings: block. These are SCAFFOLD toggles: each gates a feature that
    # lands on its own branch (see docs/dev/design/414th-vietnam-ops-notes.md). Until
    # that feature lands, the toggle is inert.
    vietnam_arc_light: bool = boolean_option(
        "Arc Light area bombing (heavy bombers)",
        VIETNAM_OPS_PAGE,
        "Fire support",
        detail=(
            "Heavy-bomber (B-52) Strike missions saturate the target area with a walking "
            "carpet of bombs at time-on-target instead of a single aimpoint, modelling the "
            "Operation Niagara Arc Light strikes. Tactical strikers (F-4/A-4) are unaffected."
        ),
        default=False,
    )
    vietnam_naval_gunfire: bool = boolean_option(
        "Naval gunfire support",
        VIETNAM_OPS_PAGE,
        "Fire support",
        detail=(
            "Offshore gun ships (battleship/cruiser main batteries) deliver call-for-fire "
            "bombardment against coastal targets. Coastal campaigns only -- has no effect "
            "inland (e.g. Khe Sanh), where naval gunfire never reached."
        ),
        default=False,
    )
    vietnam_political_will: bool = boolean_option(
        "Political will tracking",
        VIETNAM_OPS_PAGE,
        "Campaign",
        detail=(
            "Track each side's political capital for the war -- your Political Will "
            "(drained by airframe losses -- a heavy bomber is a national event -- "
            "POWs taken and held, warships sunk, and lost ground) versus the enemy's "
            "Regime Resolve (drained by logistics strangulation and attrition). "
            "Decides the war at the negotiating table: break the enemy's resolve "
            "before your will runs out, or run dry first and be ordered home. "
            "Territory victory still applies. Framing and feed weights default to "
            "the Vietnam layer (Washington vs Hanoi); a campaign's will: block can "
            "re-label and re-weight them for any era."
        ),
        default=False,
    )
    vietnam_static_front: bool = boolean_option(
        "Static front (bounded siege line)",
        VIETNAM_OPS_PAGE,
        "Campaign",
        detail=(
            "The ground front holds as a siege line: it bends with the strength "
            "battle inside a narrow band around where the campaign started, but "
            "never sweeps onto a base to capture it -- Vietnam's ground war was "
            "attrition in place, not maneuver. Deliberate Air Assault operations "
            "still capture bases (the one territorial lever), and attrition still "
            "pays out through Political Will, where the war is decided."
        ),
        default=False,
    )
    vietnam_snake_and_nape: bool = boolean_option(
        "Snake and nape (napalm CAS)",
        VIETNAM_OPS_PAGE,
        "Fire support",
        detail=(
            "An attack aircraft making a low, fast pass over enemy ground lays a wall of "
            "fire across the target -- the iconic Vietnam 'snake and nape' CAS delivery "
            "(retarded bombs + napalm). Rewards flying the run in low and on the deck; "
            "both sides' attack jets get it. Needs an attacker down low over enemy troops, "
            "or it has no effect."
        ),
        default=False,
    )
    vietnam_flak_gauntlet: bool = boolean_option(
        "AAA flak gauntlet",
        VIETNAM_OPS_PAGE,
        "Battlefield & interdiction",
        detail=(
            "Enemy anti-aircraft artillery throws barrage flak bursts and tracer streams "
            "across the target area and thickens against predictable run-in lines, recreating "
            "the AAA-heavy Vietnam threat environment. Atmospheric pressure to jink -- not a "
            "new invisible-SAM lethality model."
        ),
        default=False,
    )
    vietnam_convoy_interdiction: bool = boolean_option(
        "Truck-convoy interdiction",
        VIETNAM_OPS_PAGE,
        "Battlefield & interdiction",
        detail=(
            "Armed Recon missions over enemy road corridors find a moving supply convoy that "
            "scatters and hides when hunted; destroying it dents enemy logistics. Models Ho "
            "Chi Minh Trail / Steel Tiger interdiction."
        ),
        default=False,
    )
    vietnam_airbase_harassment: bool = boolean_option(
        "Airbase harassment (rocket/mortar siege)",
        VIETNAM_OPS_PAGE,
        "Battlefield & interdiction",
        detail=(
            "Forward, occupied airfields draw sporadic standoff rocket/mortar fire near the "
            "ramp -- the near-constant siege of Bien Hoa/Da Nang/Khe Sanh -- so the rear "
            "isn't a safe area. Your own active spawn fields are never targeted, and a "
            "startup grace period protects a cold-starting player. Mostly atmospheric with a "
            "modest, tunable bite."
        ),
        default=False,
    )
    vietnam_super_gaggle: bool = boolean_option(
        "Super Gaggle hilltop resupply",
        VIETNAM_OPS_PAGE,
        "Battlefield & interdiction",
        detail=(
            "A formation of transport helos runs one supply run per turn into a cut-off "
            "forward friendly outpost (launch field -> outpost -> back), tracked live on the "
            "F10 map so you can find it and fly escort -- modelling the Khe Sanh 'Super "
            "Gaggle'. Needs a friendly forward outpost near the front, or it has no effect."
        ),
        default=False,
    )
    vietnam_fac_marking: bool = boolean_option(
        "FAC(A) willie-pete target marking",
        VIETNAM_OPS_PAGE,
        "Battlefield & interdiction",
        detail=(
            "Airborne forward air controllers (OV-10 Broncos loitering near the front) mark "
            "the nearest enemy ground concentration with white-phosphorus smoke AND a named "
            "F10 map mark (e.g. 'BTR-60 x6'), so you can find the target and roll in -- the "
            "iconic Vietnam FAC. Needs a friendly OV-10 airborne over the battle area, or it "
            "has no effect."
        ),
        default=False,
    )

    # Performance
    perf_smoke_gen: bool = boolean_option(
        "Front-line smoke effects",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=True,
    )
    perf_smoke_spacing: int = bounded_int_option(
        "Smoke generator spacing (higher means less smoke)",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=1600,
        min=800,
        max=24000,
    )
    perf_artillery: bool = boolean_option(
        "Artillery strikes",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=True,
    )
    generate_fire_tasks_for_missile_sites: bool = boolean_option(
        "Generate fire tasks for missile sites",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        detail=(
            "If enabled, missile sites like V2s and Scuds will fire on random targets "
            "at the start of the mission."
        ),
        default=True,
    )
    perf_moving_units: bool = boolean_option(
        "Moving ground units",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=True,
    )
    convoys_travel_full_distance: bool = boolean_option(
        "Convoys drive the full distance between control points",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=True,
    )
    perf_disable_convoys: bool = boolean_option(
        "Disable land convoys",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
    )
    perf_disable_cargo_ships: bool = boolean_option(
        "Disable cargo-ship convoys",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
    )
    perf_frontline_units_prefer_roads: bool = boolean_option(
        "Front line troops prefer roads",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
    )
    perf_frontline_units_max_supply: int = bounded_int_option(
        "Maximum ground units deployed per frontline by faction",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=60,
        min=10,
        max=300,
        causes_expensive_game_update=True,
    )
    perf_infantry: bool = boolean_option(
        "Generate infantry squads alongside vehicles",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=True,
    )
    perf_destroyed_units: bool = boolean_option(
        "Generate carcasses for units destroyed in previous turns",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=True,
    )
    perf_disable_untasked_blufor_aircraft: bool = boolean_option(
        "Disable untasked OWNFOR aircraft at airfields",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
    )
    perf_disable_untasked_opfor_aircraft: bool = boolean_option(
        "Disable untasked OPFOR aircraft at airfields",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
    )
    # Performance culling
    perf_culling: bool = boolean_option(
        "Culling of distant units enabled",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
    )
    perf_culling_distance: int = bounded_int_option(
        "Culling distance (km)",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=100,
        min=10,
        max=10000,
        causes_expensive_game_update=True,
    )
    perf_do_not_cull_threatening_iads: bool = boolean_option(
        "Do not cull threatening IADS",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=True,
    )
    perf_do_not_cull_carrier: bool = boolean_option(
        "Do not cull carrier's surroundings",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=True,
        causes_expensive_game_update=True,
    )
    perf_ai_despawn_airstarted: bool = boolean_option(
        "Despawn airstarted AI over base on RTB",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
        detail=(
            "If enabled, AI flights will de-spawn over their base "
            "if the start type was manually changed to In Flight."
        ),
    )

    # Cheating. Not using auto settings because the same page also has buttons which do
    # not alter settings.
    enable_frontline_cheats: bool = False
    enable_base_capture_cheat: bool = False
    enable_transfer_cheat: bool = False
    enable_runway_state_cheat: bool = False
    enable_air_wing_adjustments: bool = False
    enable_enemy_buy_sell: bool = False
    enable_unit_placement: bool = False
    enable_free_unit_placement: bool = False

    # LUA Plugins system
    plugins: Dict[str, bool] = field(default_factory=dict)

    # Marker for the one-time TARS default-on migration (see __setstate__; the
    # retired Flight Control plugin was flipped by the same marker). True on a fresh
    # Settings so new campaigns are never re-migrated; only legacy saves that lack
    # the marker get the one-time flip.
    applied_recon_plugins_default: bool = True

    @staticmethod
    def plugin_settings_key(identifier: str) -> str:
        return f"{identifier}"

    def initialize_plugin_option(self, identifier: str, default_value: Any) -> None:
        try:
            self.plugin_option(identifier)
        except KeyError:
            self.set_plugin_option(identifier, default_value)

    def plugin_option(self, identifier: str) -> Any:
        return self.plugins[self.plugin_settings_key(identifier)]

    def set_plugin_option(self, identifier: str, value: Any) -> None:
        self.plugins[self.plugin_settings_key(identifier)] = value

    def __setstate__(self, state: dict[str, Any]) -> None:
        # __setstate__ is called with the dict of the object being unpickled. We
        # can provide save compatibility for new settings options (which
        # normally would not be present in the unpickled object) by creating a
        # new settings object, updating it with the unpickled state, and
        # updating our dict with that.
        migrated_state = self._migrate_legacy_settings(
            self.deserialize_state_dict(state)
        )
        new_state = Settings().__dict__
        new_state.update(migrated_state)
        self.__dict__.update(new_state)

        # One-time migration: the TARS plugin ships enabled by default, but a save
        # created before it existed (or before it was flipped to default-on) can
        # have it recorded as off. Force it on once for such saves. Keyed on the
        # marker being absent from the *raw* unpickled state, so an already-migrated
        # save or a new campaign that has deliberately turned it off is never
        # re-stomped. (The retired Flight Control plugin was also flipped here; its
        # dead option keys are pruned below.)
        if "applied_recon_plugins_default" not in state:
            for plugin_id in ("tars",):
                self.set_plugin_option(plugin_id, True)
        self.applied_recon_plugins_default = True

        # Drop retired plugin option keys so dead configuration does not persist
        # across a load/save cycle. The obsolete Anubis "herculescargo" plugin and
        # its option keys were removed in favor of the official C-130J-30. The old
        # generic EW/Jammer Script ("ewrj") was retired in favor of the C-130J
        # JAMMING flight + c130j mission-systems plugin. The "dismounts" and "ewrs"
        # plugins were retired during the MIST -> MOOSE framework consolidation:
        # dismounts was a default-off, FPS-heavy MIST-only plugin with no MOOSE
        # successor, and ewrs is superseded by the MOOSE Ops.INTEL-based "bigeye"
        # EWR (see docs/dev/design/414th-dismounts-decision.md and
        # 414th-ewrs-retirement-decision.md). The "flightcontrol" MOOSE
        # FLIGHTCONTROL ATC plugin was retired as a half-baked feature. The "arty"
        # (CG ArtySpotter) and "artymbot" (Mbot Call-Artillery) player fire-support
        # scripts were retired as unused: both had been silently dropped from the
        # active plugin list and their directories are now removed.
        for plugin_key in [
            key
            for key in self.plugins
            if key == "herculescargo"
            or key.startswith("herculescargo.")
            or key == "ewrj"
            or key.startswith("ewrj.")
            or key == "dismounts"
            or key.startswith("dismounts.")
            or key == "ewrs"
            or key.startswith("ewrs.")
            or key == "flightcontrol"
            or key.startswith("flightcontrol.")
            or key == "arty"
            or key.startswith("arty.")
            or key == "artymbot"
            or key.startswith("artymbot.")
        ]:
            del self.plugins[plugin_key]

        from game.plugins import LuaPluginManager

        LuaPluginManager().load_settings(self)

    @staticmethod
    def _migrate_legacy_settings(state: dict[str, Any]) -> dict[str, Any]:
        migrated = dict(state)

        # The per-base-type ground-start truck toggles were consolidated: the old
        # roadbase-specific options folded into the single airbase+roadbase
        # toggles. Preserve intent -- a save that had trucks enabled at *either*
        # base type keeps them enabled. The obsolete roadbase keys are dropped
        # in the obsolete-key sweep below.
        if "ground_start_trucks_roadbase" in migrated:
            migrated["ground_start_trucks"] = bool(
                migrated.get("ground_start_trucks", False)
                or migrated.get("ground_start_trucks_roadbase", False)
            )
        if "ground_start_ground_power_trucks_roadbase" in migrated:
            migrated["ground_start_ground_power_trucks"] = bool(
                migrated.get("ground_start_ground_power_trucks", True)
                or migrated.get("ground_start_ground_power_trucks_roadbase", True)
            )

        if "ai_radio_behavior" not in migrated:
            silence_ai_radios = migrated.get("silence_ai_radios", False)
            limit_ai_radios = migrated.get("limit_ai_radios", True)
            if silence_ai_radios:
                behavior = AiRadioBehavior.SILENT
            elif limit_ai_radios:
                behavior = AiRadioBehavior.LIMITED
            else:
                behavior = AiRadioBehavior.FULL
            migrated["ai_radio_behavior"] = behavior

        for obsolete_key in (
            "limit_ai_radios",
            "silence_ai_radios",
            "prefer_squadrons_with_matching_primary_task",
            "pretense_num_of_cargo_planes",
            "pretense_maxdistfromfront_distance",
            "pretense_controllable_carrier",
            "pretense_carrier_steams_into_wind",
            "pretense_carrier_zones_navmesh",
            "pretense_extra_zone_connections",
            "pretense_sead_flights_per_cp",
            "pretense_cas_flights_per_cp",
            "pretense_bai_flights_per_cp",
            "pretense_strike_flights_per_cp",
            "pretense_barcap_flights_per_cp",
            "pretense_ai_aircraft_per_flight",
            "pretense_player_flights_per_type",
            "pretense_ai_cargo_planes_per_side",
            "nevatim_parking_fix",
            "only_player_takeoff",
            "generate_dtc",
            # Removed once MANTIS/Skynet became the SAM-emissions owner: the IADS
            # engine sets each networked SAM's alarm state at runtime, so a global
            # "SAM starts in red alert" toggle just fought the engine. Non-IADS
            # groups now fall to DCS AUTO. See 414th-mantis-migration-notes.md.
            "perf_red_alert_state",
            # The IADS-engine selector was removed when Skynet was dropped and MANTIS
            # became the sole engine. Drop the persisted value (the IadsEngine stub
            # only exists so the old enum still unpickles before this pop).
            "iads_engine",
            # Consolidated into the single airbase+roadbase ground-start truck
            # toggles (value already merged above).
            "ground_start_trucks_roadbase",
            "ground_start_ground_power_trucks_roadbase",
            # The SCAR mis-ID budget penalty died with the SOF capture economy
            # (dead code removed 2026-07-01; nothing wrote scar_misid since the
            # armor-hunt plugin was deleted).
            "scar_misid_penalty",
        ):
            migrated.pop(obsolete_key, None)

        return migrated

    @staticmethod
    def deserialize_state_dict(state: dict[str, Any]) -> dict[str, Any]:
        # restore Enum & timedelta types
        s = Settings()
        Settings._migrate_legacy_fast_forward(state)
        for key, value in list(state.items()):
            default = s.__dict__.get(key)
            if isinstance(default, Enum):
                # Restore the stored member, falling back to the field default
                # for any value that no longer resolves to a member of this
                # field's enum -- a stale/renamed choice, or a legacy non-enum
                # value such as None or a bool. Otherwise the bad value crashes
                # the load and later the settings UI via text_for_value.
                restored = Settings._restore_enum(value, type(default))
                state[key] = restored if restored is not None else default
            elif isinstance(default, timedelta) and isinstance(value, int):
                state[key] = timedelta(minutes=value)
            elif isinstance(value, dict):
                state[key] = s.obj_hook(value)
        return state

    @staticmethod
    def _restore_enum(value: Any, enum_cls: type[Enum]) -> Optional[Enum]:
        """Resolve a serialized value to a member of enum_cls, or None if it no
        longer maps to one (stale, renamed, or a legacy non-enum value).

        Parsing goes through the safe ``_deserialize_enum`` registry (no
        ``eval``), so a crafted save cannot execute code here -- see
        ``test_object_hook_rejects_untrusted_enum_payloads``. Returning None on
        any unresolved value lets the caller fall back to the field default
        instead of crashing the load (upstream #755 robustness)."""
        if isinstance(value, enum_cls):
            return value
        # Accept the JSON form {"Enum": "EnumName.MEMBER"} and the bare
        # "EnumName.MEMBER" string; ignore anything that does not resolve to a
        # member of this field's enum.
        expr: Optional[str] = None
        if isinstance(value, dict):
            inner = value.get("Enum")
            if isinstance(inner, str):
                expr = inner
        elif isinstance(value, str):
            expr = value
        if expr is not None:
            try:
                restored = Settings._deserialize_enum(expr, expected_type=enum_cls)
            except ValueError:
                return None
            if isinstance(restored, enum_cls):
                return restored
        return None

    @staticmethod
    def _migrate_legacy_fast_forward(state: dict[str, Any]) -> None:
        """Map pre-#684 fast-forward settings onto the current enums.

        Before #684 fast-forward was three separate fields::

            fast_forward_to_first_contact: bool          # was it enabled
            player_mission_interrupts_sim_at: Optional[StartType]
                # None=Never, COLD=startup, WARM=taxi, RUNWAY=takeoff
            auto_resolve_combat: bool

        #684 replaced them with ``fast_forward_stop_condition`` /
        ``combat_resolution_method``. Translate old saves so the user keeps an
        equivalent setting instead of crashing on load, and normalize the legacy
        "Never"/None sentinel (which has no enum member) to "no fast forward".
        """
        legacy_ff = state.pop("fast_forward_to_first_contact", None)
        legacy_interrupt = state.pop("player_mission_interrupts_sim_at", None)
        legacy_auto = state.pop("auto_resolve_combat", None)

        if "fast_forward_stop_condition" not in state and legacy_ff is not None:
            if not legacy_ff:
                state["fast_forward_stop_condition"] = FastForwardStopCondition.DISABLED
            else:
                interrupt = Settings._resolve_start_type(legacy_interrupt)
                if interrupt is None:
                    state["fast_forward_stop_condition"] = (
                        FastForwardStopCondition.FIRST_CONTACT
                    )
                else:
                    state["fast_forward_stop_condition"] = {
                        StartType.COLD: FastForwardStopCondition.PLAYER_STARTUP,
                        StartType.WARM: FastForwardStopCondition.PLAYER_TAXI,
                        StartType.RUNWAY: FastForwardStopCondition.PLAYER_TAKEOFF,
                    }.get(interrupt, FastForwardStopCondition.FIRST_CONTACT)

        if "combat_resolution_method" not in state and legacy_auto is not None:
            state["combat_resolution_method"] = (
                CombatResolutionMethod.RESOLVE
                if legacy_auto
                else CombatResolutionMethod.PAUSE
            )

        # A "none"/"Never"/None value stored directly under the new key has no
        # matching enum member; treat that family as "no fast forward".
        ff = state.get("fast_forward_stop_condition")
        if ff is None and "fast_forward_stop_condition" in state:
            state["fast_forward_stop_condition"] = FastForwardStopCondition.DISABLED
        elif isinstance(ff, str) and ff.strip().lower() in {"none", "never", ""}:
            state["fast_forward_stop_condition"] = FastForwardStopCondition.DISABLED

    @staticmethod
    def _resolve_start_type(value: Any) -> Optional[StartType]:
        """Coerce a serialized legacy value to a StartType member, or None."""
        if isinstance(value, StartType):
            return value
        if isinstance(value, str):
            name = value.rsplit(".", 1)[-1]
            for member in StartType:
                if name == member.name or value == member.value:
                    return member
        return None

    @classmethod
    def _field_description(cls, settings_field: Field[Any]) -> OptionDescription:
        return settings_field.metadata[SETTING_DESCRIPTION_KEY]

    @classmethod
    def _effective_layout(
        cls, name: str, description: OptionDescription
    ) -> tuple[str, str]:
        # FIELD_LAYOUT is the curated UI grouping; fall back to the field's own
        # page=/section= metadata for anything not listed there.
        return FIELD_LAYOUT.get(name, (description.page, description.section))

    @classmethod
    def _ordered_user_fields(cls) -> list[Field[Any]]:
        # Walk user fields in FIELD_LAYOUT order first (the curated layout), then
        # append any field missing from the table in declaration order so a
        # field is never dropped from the UI.
        by_name = {f.name: f for f in cls._user_fields()}
        ordered: list[Field[Any]] = []
        seen: set[str] = set()
        for name in FIELD_LAYOUT:
            settings_field = by_name.get(name)
            if settings_field is not None:
                ordered.append(settings_field)
                seen.add(name)
        for settings_field in cls._user_fields():
            if settings_field.name not in seen:
                ordered.append(settings_field)
                seen.add(settings_field.name)
        return ordered

    @classmethod
    def pages(cls) -> Iterator[str]:
        seen: set[str] = set()
        for settings_field in cls._ordered_user_fields():
            description = cls._field_description(settings_field)
            page, _section = cls._effective_layout(settings_field.name, description)
            if page not in seen:
                yield page
                seen.add(page)

    @classmethod
    def sections(cls, page: str) -> Iterator[str]:
        seen: set[str] = set()
        for settings_field in cls._ordered_user_fields():
            description = cls._field_description(settings_field)
            field_page, section = cls._effective_layout(
                settings_field.name, description
            )
            if field_page == page and section not in seen:
                yield section
                seen.add(section)

    @classmethod
    def fields(cls, page: str, section: str) -> Iterator[tuple[str, OptionDescription]]:
        for settings_field in cls._ordered_user_fields():
            description = cls._field_description(settings_field)
            field_page, field_section = cls._effective_layout(
                settings_field.name, description
            )
            if field_page == page and field_section == section:
                yield settings_field.name, description

    @classmethod
    def _user_fields(cls) -> Iterator[Field[Any]]:
        for settings_field in fields(cls):
            if SETTING_DESCRIPTION_KEY in settings_field.metadata:
                yield settings_field

    @staticmethod
    def default_json(obj: Any) -> Any:
        # Known types that don't like being serialized,
        # so we introduce our own implementation...
        if isinstance(obj, Enum):
            return {"Enum": str(obj)}
        elif isinstance(obj, timedelta):
            return {"timedelta": round(obj.seconds / 60)}
        return obj

    @staticmethod
    def obj_hook(obj: Any) -> Any:
        if (value := obj.get("Enum")) is not None:
            return Settings._deserialize_enum(value)
        elif (value := obj.get("timedelta")) is not None:
            return timedelta(minutes=value)
        else:
            return obj

    @staticmethod
    def _deserialize_enum(value: Any, expected_type: type[Enum] | None = None) -> Enum:
        if not isinstance(value, str):
            raise ValueError("Serialized enum value must be a string")

        try:
            type_name, member_name = value.split(".", maxsplit=1)
        except ValueError as ex:
            raise ValueError(f"Invalid serialized enum value: {value!r}") from ex

        enum_type = SERIALIZABLE_ENUM_TYPES_BY_NAME.get(type_name)
        if enum_type is None or (
            expected_type is not None and enum_type is not expected_type
        ):
            raise ValueError(f"Unsupported serialized enum type: {type_name!r}")

        try:
            return enum_type[member_name]
        except KeyError as ex:
            raise ValueError(
                f"Unknown {enum_type.__name__} member: {member_name!r}"
            ) from ex
