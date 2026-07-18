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
class CarrierDeckPolicy(Enum):
    """How the carrier six-pack (the first-filled deck spots) is used.

    DCS offers no mission-level control over deck parking beyond spawn timing:
    groups spawning at mission start fill the six-pack first, and anything that
    spawns even one second later is placed elsewhere on deck (the
    dcs_liberation#1309 placement trick the generator already uses to keep AI
    off the six-pack). The six-pack sits in the taxi lane to the bow catapults,
    so a slow-starting player parked there jams every AI jet taxiing to launch.
    """

    SIXPACK_FIRST = "Players spawn on the six-pack"
    LAST_RESORT = "Six-pack is overflow parking (last resort)"


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
    CarrierDeckPolicy,
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
COMBAT_SAR_SECTION = "Combat search & rescue"
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
                    "restrict_props_by_date",
                    "target_intel_precision",
                    "recon_intel_fog",
                    "concealed_enemy_forces",
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
                    "qra_forward_defense",
                    "qra_defense_depth_nm",
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
                    "c2_decapitation_effects",
                    "weather_aware_planning",
                    "sead_strike_coordination",
                    "red_intent",
                    "red_intent_per_front",
                    "red_intent_boldness",
                    "red_intent_dwell_turns",
                    "red_intent_trend_window",
                ],
            ),
            (
                "Recon & SCAR planning",
                [
                    "auto_add_tarps_recon",
                    "auto_jtac_drone",
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
                "Engagement ranges",
                [
                    "airbase_threat_range",
                    "max_threat_range",
                    "cas_engagement_range_distance",
                    "armed_recon_engagement_range_distance",
                ],
            ),
            (
                "SEAD standoff",
                [
                    "sead_sweep_engagement_range_distance",
                    "sead_threat_buffer_min_distance",
                    "sead_loiter_standoff_factor",
                    "sead_loiter_max_window_seconds",
                ],
            ),
            (
                "Support-orbit standoff",
                [
                    "tarcap_threat_buffer_min_distance",
                    "aewc_threat_buffer_min_distance",
                    "tanker_threat_buffer_min_distance",
                ],
            ),
            (
                "Mission range limits",
                [
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
                # The player-facing campaign features, together at the top of the
                # page (they used to be three one-field orphan sections).
                "Campaign features",
                [
                    "campaign_phases",
                    "continuous_campaign_clock",
                    "long_range_carrier_ops",
                    "motorpool_enabled",
                    "motorpool_spawn_cap",
                ],
            ),
            (
                "War economy",
                [
                    "war_economy",
                    "fuel_air_readiness",
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
                    "coin_harassment",
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
                    "automate_front_line_stance",
                    "default_front_line_stance",
                ],
            ),
            (
                "Combat search & rescue",
                [
                    "auto_combat_sar",
                    "combat_sar_persistent_pilots",
                    "combat_sar_surge",
                    "combat_sar_test_force_capture",
                    "combat_sar_test_easy_rescue",
                ],
            ),
            (
                "Commander economy",
                [
                    "adaptive_procurement",
                    "auto_repair_air_defenses",
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
                "Aircraft start types",
                [
                    "default_start_type",
                    "default_start_type_client",
                    "opfor_air_start",
                    "support_air_start",
                ],
            ),
            (
                "Player slots",
                [
                    "dynamic_slots",
                    "dynamic_slots_hot",
                    "dynamic_cargo",
                    "carrier_deck_policy",
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
                ],
            ),
            (
                # In-mission life on the ground: cosmetic siege damage, indirect
                # fire on forward strips, and shoot-and-scoot missile sites.
                "Battlefield life",
                [
                    "base_battle_damage",
                    "artillery_base_harassment",
                    "artillery_harassment_reach_km",
                    "mobile_missile_relocation",
                    "coastal_missile_relocation",
                    "civilian_air_traffic",
                    "ambient_supply_convoys",
                    "convoy_ambush",
                    "air_droppable_minefields",
                    "auto_plan_minefields",
                    "enemy_comms_jamming",
                    "comms_jam_requires_capture",
                    "mission_briefing_popup",
                ],
            ),
            (
                # Ship-launched land-attack fires (§63) -- the finite-magazine
                # cruise missile game, kept out of the (full) Battlefield life
                # grab of in-mission texture toggles.
                "Naval strike",
                [
                    "cruise_missile_strikes",
                    "cruise_missile_auto_raids",
                ],
            ),
            (
                # Game-master levers for hosted multiplayer events -- deliberate
                # host actions, never automatic systems.
                "Host & event tools",
                [
                    "host_red_scramble",
                ],
            ),
            (
                "Loadouts",
                [
                    "auto_range_fuel_tanks",
                    "fuel_tanks_over_jammers",
                    "restrict_weapons_by_stock",
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
                    "generate_dark_kneeboard",
                    "generate_target_recon_kneeboard",
                    "generate_all_packages_kneeboard",
                    "generate_threat_intel_kneeboard",
                    "enable_package_code_words",
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
                    "vietnam_commitment_ceiling",
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
                    "perf_ground_ai_sleep",
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
            "base scrambles its QRA interceptors. Opened up automatically while "
            "'QRA defends the front' is on."
        ),
    )
    qra_forward_defense: bool = boolean_option(
        "QRA defends the front (rear bases answer forward raids)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "Alert fighters at rear bases scramble to fight over the front line "
            "instead of only answering raids near their own runway. Each side is "
            "confined to the airspace over its own bases and its own side of the "
            "front, so defenders never chase deep into enemy territory. The closest "
            "base still answers first; a rear base only launches once the closer "
            "one's alert aircraft are spent. Turn this off for the legacy behaviour, "
            "where a base only ever defends itself."
        ),
    )
    qra_defense_depth_nm: int = bounded_int_option(
        "QRA defended airspace radius (NM)",
        enabled_when="qra_forward_defense",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=60,
        min=10,
        max=200,
        detail=(
            "How far around each of its own bases a side will fight, while 'QRA "
            "defends the front' is on. A base that holds the front line always "
            "defends its stretch of the line too, reaching a little way past it. "
            "Larger values let interceptors push further from home."
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
        "Auto-planner adds a recon flight to Strike/DEAD/Armed Recon packages",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=True,
        invert=False,
        detail=(
            "If checked, the auto-planner appends a single photo-recon flight "
            "(e.g. F-14 TARPS, or a Predator/Reaper drone on a UAV-fielding "
            "faction) to Strike and DEAD packages against high-value targets "
            "(air defenses, factories, command posts, bridges) for a post-strike "
            "BDA pass, and to Armed Recon packages as a scouting overwatch over "
            "the swept corridor. The recon bird overflies the target under the "
            "package's escort window. Requires a TARPS-capable squadron in range; "
            "if none is available the flight is simply skipped (the package is "
            "never scrubbed)."
        ),
    )
    auto_jtac_drone: bool = boolean_option(
        "Auto-field a JTAC drone squadron for the player's side",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=True,
        invert=False,
        detail=(
            "At New Game, if your faction declares a drone JTAC platform "
            "(MQ-9 Reaper / Predator) and the campaign does not already field one, "
            "adds a small ISR drone squadron at your rear-most airfield. The auto-"
            "planner then frags it forward into air-to-ground packages, where it "
            "lazes and marks targets for the shooters (and, being a drone, films "
            "the whole time). Replaces the old front-line auto-JTAC. A campaign that "
            "hand-places its drones is left untouched; turn this off to keep an "
            "air wing exactly as the campaign authored it."
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
    concealed_enemy_forces: bool = boolean_option(
        "Concealed enemy field forces (uncertainty areas until scouted)",
        enabled_when="recon_intel_fog",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=True,
        invert=False,
        detail=(
            "When enabled (and recon intel fog is on), un-scouted enemy FIELD "
            "forces — mobile SAM sites (medium/short-range and AAA), deployed "
            "vehicle groups, and missile sites — do not show an exact map marker "
            "at all: the map draws a dashed 'suspected activity' circle offset "
            "from the true position until recon (TARPS) or an attack localizes "
            "the site. Fixed infrastructure stays exact: airfields, buildings, "
            "long-range strategic SAMs, EWRs (they emit), and ships. The AI "
            "planner and threat math always use full truth. The circle is "
            "clickable like a marker, so you can still plan recon or a strike "
            "against the suspected area."
        ),
    )
    # NB: the field NAME keeps its historical "scar_" prefix (renaming it would
    # orphan the value in every existing save); only the label is current. The
    # commander-capture mechanic the old label referenced was removed 2026-07-01 —
    # what remains is the command-post recon fog itself.
    scar_command_post_intel: bool = boolean_option(
        "Hidden enemy command posts (map the command network by recon)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=True,
        invert=False,
        detail=(
            "Enemy command posts stay hidden on the map until you discover them — "
            "strike near them, scout them, or photograph them on a TARPS pass — so "
            "mapping the enemy command network is itself a reconnaissance task. On "
            "by default for new campaigns; existing campaigns keep whatever they "
            "were saved with. Turn it off to restore plain enemy command-post "
            "visibility."
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
    c2_decapitation_effects: bool = boolean_option(
        "Command-center kills degrade enemy planning",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "Destroying a side's IADS command centers makes its auto-planner "
            "sloppier: as the command network is decapitated, its offensive target "
            "selection gets progressively more unpredictable (the same lever as the "
            "unpredictability sliders above, scaled by how many command posts are "
            "down), and its offensive tempo thins -- a decapitated HQ frags fewer "
            "offensive packages per turn (never zero; the floor keeps some pressure "
            "on). So bombing the enemy HQ is a strategic move, not just a strike "
            "checkbox. Reactive defensive tasking is never affected -- a headless "
            "enemy still defends itself, it just plans worse offense. Applies to "
            "whichever side loses its command posts; a campaign with no command "
            "centers is unaffected."
        ),
    )
    weather_aware_planning: bool = boolean_option(
        "Auto-planner reads the weather",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "The theater commander accounts for the sky when planning (both "
            "sides). In rain or thunderstorms the automatic photo-recon add-on "
            "stays home (cameras photograph cloud deck), and a thunderstorm "
            "pushes low-level visual attack -- front-line CAS, battle-position "
            "BAI, convoy interdiction -- to the back of the offensive plan so "
            "weather-tolerant strikes claim the jets first. Clear skies change "
            "nothing, and player-planned flights are never touched."
        ),
    )
    sead_strike_coordination: bool = boolean_option(
        "Strikes push behind their SEAD window",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "Packages used to be timed independently, so a strike could arrive "
            "at a defended target half an hour before the SEAD package tasked "
            "against the SAM covering it. With this on, each side's AI "
            "strike/BAI/OCA packages whose target sits inside a SAM threat ring "
            "that a SEAD/DEAD package is servicing are retimed into the window "
            "just behind it -- SEAD opens the corridor, then the strikes push, "
            "several packages massing behind one suppressor. Player packages "
            "are never rescheduled, but a player-flown SEAD still opens a "
            "window the AI pushes behind."
        ),
    )
    red_intent: bool = boolean_option(
        "Red plays with intent (adaptive posture)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "The enemy commander reads the war each turn -- ground balance, air "
            "strength, resolve, supply, and how the last turn went -- and adopts a "
            "posture (consolidate / attrition / surge) that carries across turns, "
            "instead of planning the same way every turn. The posture then shapes how "
            "red plans: which offensive missions it prioritises, how predictably it "
            "picks targets, how many bases it strips for offense, and how readily it "
            "commits ground reserves. Shown on the SITREP and the campaign status bar. "
            "Red-only; a campaign with no enemy auto-planner is unaffected."
        ),
    )
    red_intent_per_front: bool = boolean_option(
        "Red intent adapts per front",
        enabled_when="red_intent",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "With Red Intent on, resolve a separate posture for EACH active front from "
            "that front's own ground balance (the shared air/resolve/supply/trend read "
            "still applies), so on a multi-front war red commits its reserves on the "
            "front it is winning and husbands them on the front it is losing, instead "
            "of one theater-wide stance. Off falls back to a single theater-wide "
            "posture. No effect on single-front campaigns or when Red Intent is off."
        ),
    )
    red_intent_boldness: int = bounded_int_option(
        "Red intent boldness",
        enabled_when="red_intent",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=50,
        min=0,
        max=100,
        detail=(
            "Red's temperament dial (50 = the neutral default). Higher makes red bolder "
            "-- it surges at a smaller ground edge, seizes opportunity windows more "
            "readily, digs in only when badly outnumbered, and presses harder once "
            "committed (bigger aggressiveness/reserve-commitment swing). Lower makes it "
            "cautious -- it needs a clear advantage to surge and turtles sooner. Only "
            "affects red when Red Intent is on."
        ),
    )
    red_intent_dwell_turns: int = bounded_int_option(
        "Red intent posture stickiness (turns)",
        enabled_when="red_intent",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=2,
        min=1,
        max=6,
        detail=(
            "How many turns red must hold a posture before it may ESCALATE to a more "
            "aggressive one (attrition -> surge). De-escalation to consolidate is always "
            "immediate -- a command reacts to a setback at once. Higher = a steadier, "
            "less twitchy enemy; lower = quicker to seize a fleeting advantage. Only "
            "affects red when Red Intent is on."
        ),
    )
    red_intent_trend_window: int = bounded_int_option(
        "Red intent trend memory (turns)",
        enabled_when="red_intent",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=2,
        min=1,
        max=5,
        detail=(
            "How many turns back red compares against when reading trends (its IADS "
            "being dismantled, resolve collapsing, bases bleeding, the enemy air force "
            "spent). A longer window makes red react to slower, sustained pressure; a "
            "shorter one to abrupt swings. Only affects red when Red Intent is on."
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
    restrict_props_by_date: bool = boolean_option(
        "Restrict aircraft options by campaign date (incomplete data)",
        page=CAMPAIGN_MANAGEMENT_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "Restricts era-defining aircraft mission options (e.g. the JHMCS helmet "
            "cueing selection) based on the campaign date: gated options are hidden "
            "from the payload editor and clamped to a period-correct value at "
            "mission generation. Independent of the weapons restriction so either "
            "can be enforced alone. Data is curated per airframe and incomplete."
        ),
    )
    war_economy: bool = boolean_option(
        "War economy (supply logistics)",
        page=CAMPAIGN_MANAGEMENT_PAGE,
        section="War economy",
        default=False,
        detail=(
            "Adds a per-base materiel supply stockpile on top of the money economy: "
            "factories and oil/derricks produce supply, it flows to the front and is "
            "consumed there, and a starved front recovers less, deploys fewer units, "
            "and gains less ground -- so bombing the enemy's production and cutting "
            "their supply routes visibly thins their front over several turns. "
            "Symmetric (the enemy interdicts yours too); the SITREP shows each side's "
            "front supply. Intended for campaigns with a real economy laydown "
            "(factories + depots) that preseed it on."
        ),
    )
    fuel_air_readiness: bool = boolean_option(
        "Fuel depots gate air readiness",
        page=CAMPAIGN_MANAGEMENT_PAGE,
        section="War economy",
        default=False,
        detail=(
            "An airfield's alive fuel depots gate how many of its aircraft can sortie "
            "each turn: destroy an enemy base's fuel infrastructure and it flies fewer "
            "packages (down to a floor; a base with no fuel depots is never penalised). "
            "Symmetric -- your own grounded bases fly less too. Independent of the "
            "supply economy above; intended for campaigns with fuel-depot laydowns."
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
        enabled_when="coin_insurgency",
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
        enabled_when="coin_insurgency",
        page=CAMPAIGN_MANAGEMENT_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "The insurgent supply roads are mined. Hidden emplacements appear on the "
            "ratline -- an emplaced device guarded by a small security team, or a "
            "mobile VBIED driving for your lines -- recon-fogged targets you must find "
            "(TARPS/ISR) and strike (CAS/Armed Recon) within a few turns. Destroying "
            "the device clears the bomb (killing the team alone does not); one you "
            "leave un-swept detonates on the coalition and drains your mandate (priced "
            "by the campaign's will profile). Requires COIN replenishment on; intended "
            "for COIN campaigns that preseed it."
        ),
    )
    coin_hvt: bool = boolean_option(
        "COIN high-value targets (hunt the leadership)",
        enabled_when="coin_insurgency",
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
        enabled_when="coin_insurgency",
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
    coin_harassment: bool = boolean_option(
        "COIN indirect fire on forward bases (the FOB war)",
        enabled_when="coin_insurgency",
        page=CAMPAIGN_MANAGEMENT_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "The rear is not a safe area. Friendly airfields, FARPs and FOBs within "
            "mortar reach of an insurgent stronghold draw sporadic rocket/mortar "
            "harassment fire during the mission -- mostly noise and smoke with a "
            "modest bite, pressure rather than precision. Pushing the strongholds "
            "back (or clearing them) is what silences the fire. Never targets a "
            "field a player spawns at or recovers to this mission, and a startup "
            "grace period holds all fire while flights align. Requires COIN "
            "replenishment on; intended for COIN campaigns that preseed it."
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
    motorpool_enabled: bool = boolean_option(
        "Spawn strikeable motorpool reserves",
        page=CAMPAIGN_MANAGEMENT_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "Render each control point's not-yet-deployed reserve armor as a "
            "strikeable motorpool (only where the campaign authored one). "
            "Destroying reserves forces the owner to repurchase."
        ),
    )
    motorpool_spawn_cap: int = bounded_int_option(
        "Maximum motorpool vehicles per turn",
        enabled_when="motorpool_enabled",
        page=CAMPAIGN_MANAGEMENT_PAGE,
        section=GENERAL_SECTION,
        default=10,
        min=0,
        max=25,
        detail=(
            "Caps how many reserve vehicles a control point renders across its "
            "motorpool(s) per turn. Lower this if motorpools hurt mission "
            "performance."
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
    restrict_weapons_by_stock: bool = boolean_option(
        "Restrict munitions to airfield stock (war economy)",
        page=MISSION_GENERATION_PAGE,
        section="Loadouts",
        default=False,
        detail=(
            "Track a per-airfield stock of scarce munitions (PGMs, GPS bombs, "
            "standoff/cruise, anti-radiation, medium/long-range A2A) and rearm it each "
            "turn -- scaled by the base's supply when the war economy is on, so cutting "
            "a base off starves its magazines. When a store runs dry the loadout is "
            "swapped down to the first stocked/non-scarce fallback (JDAM -> dumb bomb) "
            "or the pylon is cleared, and the payload editor greys the depleted store "
            "out. Intended for campaigns with a real economy/logistics laydown."
        ),
    )
    auto_range_fuel_tanks: bool = boolean_option(
        "Add fuel tanks when the route needs the range",
        page=MISSION_GENERATION_PAGE,
        section="Loadouts",
        default=True,
        detail=(
            "Fuel-first planning: once a package is built, drop tanks are fitted to "
            "a flight's EMPTY tank-capable stations when the sortie needs more fuel "
            "than internal (plus any tanks already on the loadout) can cover, BEFORE "
            "the pre/post-vul tanker decision -- which also counts the fuel in the "
            "bags, so a jet carrying tanks stops being sent to the tanker twice when "
            "one pass (or none) covers it. Far-AO campaigns (e.g. the COIN carrier "
            "~800 km off the beach) fly with enough gas; inert on short routes. This "
            "toggle on its own never removes a store (a TGP, ECM pod, or ordnance is "
            "never swapped out; see the jammer-pod trade below). Player-customised "
            "loadouts are left untouched."
        ),
    )
    fuel_tanks_over_jammers: bool = boolean_option(
        "Trade jammer pods for fuel tanks when it saves a tanker pass",
        page=MISSION_GENERATION_PAGE,
        section="Loadouts",
        default=True,
        enabled_when="auto_range_fuel_tanks",
        detail=(
            "When filling empty stations still leaves a sortie needing more tanker "
            "passes, a self-protection JAMMER pod on a tank-capable station gives up "
            "its seat to a drop tank -- but only when the extra bag strictly reduces "
            "the pass count (pre+post-vul refueling becomes one pass, or one pass "
            "becomes none), or when no tanker exists at all and the bags are the only "
            "gas there is. The motivating case: a SEAD Viper with two wing bags and a "
            "centerline ALQ-184 planned through two refuel passes -- three bags and "
            "one pass beat the pod. Only jammer pods are ever traded (never a TGP, "
            "decoy, or ordnance); player-customised loadouts are left untouched."
        ),
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
        enabled_when="enable_squadron_pilot_limits",
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
        enabled_when="enable_squadron_pilot_limits",
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
    continuous_campaign_clock: bool = boolean_option(
        "Continuous time & weather",
        CAMPAIGN_MANAGEMENT_PAGE,
        "Campaign clock & weather",
        detail=(
            "Make the campaign flow as one continuous timeline. The mission "
            "clock marches forward a few hours each turn (a sortie plus "
            "turnaround) and the date rolls over at midnight, instead of "
            "teleporting between disjoint dawn/day/dusk/night bands. Weather "
            "evolves from the previous turn -- fronts roll in and clear over "
            "several turns -- instead of an independent random draw each turn. "
            "Requires day-and-night missions (the day-only / night-only mission "
            "time settings opt out of the natural cycle and fall back to the "
            "per-turn rotation). Turn off for the stock per-turn behaviour."
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
        COMBAT_SAR_SECTION,
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
    combat_sar_persistent_pilots: bool = boolean_option(
        "Downed pilots persist until rescued or captured (MIA)",
        CAMPAIGN_MANAGEMENT_PAGE,
        COMBAT_SAR_SECTION,
        default=True,
        detail=(
            "A pilot who ejects and is neither rescued nor captured by mission end "
            "goes MIA instead of dying: they re-spawn at their last known position "
            "next mission (fresh red smoke, a fresh enemy snatch race, rescuable by "
            "a player package or the automatic rescue), and at every turn boundary "
            "an evader on friendly ground walks home while one behind the lines "
            "rolls a DEPTH-weighted capture -- near the front they usually keep "
            "evading; deep behind the lines enemy search parties almost certainly "
            "find them (-> POW, which can compromise your comms). There is no "
            "death clock; the depth roll is the clock. Turn OFF to return to the "
            "old behaviour (an un-rescued pilot is lost at debrief)."
        ),
    )
    combat_sar_surge: bool = boolean_option(
        "Pilot recovery surge (next-turn coordinated rescue)",
        CAMPAIGN_MANAGEMENT_PAGE,
        COMBAT_SAR_SECTION,
        default=True,
        enabled_when="combat_sar_persistent_pilots",
        detail=(
            "The turn after a pilot goes MIA, open the mission with a coordinated "
            "recovery package already airborne at the evader's last known position: "
            "rescue helo(s), a C-130 'King' on-scene commander, a 'Sandy' escort, "
            "and a fighter escort when threatened -- planned ahead of everything "
            "else, so the rescue force is on station at mission start instead of "
            "transiting for an hour. Fires ONCE per downed pilot (a failed surge "
            "falls back to the normal rescue paths), so it is an event, not an "
            "every-mission fixture. Requires persistent downed pilots (MIA)."
        ),
    )
    combat_sar_test_force_capture: bool = boolean_option(
        "[TEST] Combat SAR: force every downed pilot to be captured",
        CAMPAIGN_MANAGEMENT_PAGE,
        COMBAT_SAR_SECTION,
        default=False,
        detail=(
            "Testing aid (thumb on the scale, default OFF). Rigs the Combat SAR "
            "capture race so every ejection is seized fast: the enemy snatch party "
            "spawns 100% of the time, right on top of the survivor, and captures "
            "within a few seconds -- so you can reliably exercise the POW path and "
            "the capture-gated enemy comms jamming without fighting the RNG (fly, "
            "get a blue pilot down near the front, advance the turn). Overrides the "
            "Combat SAR plugin's capture options. If '[TEST] ... trivially easy' is "
            "also on, capture wins. Leave OFF for normal play."
        ),
    )
    combat_sar_test_easy_rescue: bool = boolean_option(
        "[TEST] Combat SAR: make pilot pickup trivially easy",
        CAMPAIGN_MANAGEMENT_PAGE,
        COMBAT_SAR_SECTION,
        default=False,
        detail=(
            "Testing aid (thumb on the scale, default OFF). Disables the enemy "
            "capture race and widens the pickup tolerances (range/height/speed/"
            "delivery) so a rough landing near the red smoke boards the survivor -- "
            "so you can reliably exercise the King TACAN beacon, the Sandy divert, "
            "and the rescue/delivery loop. Overrides the Combat SAR plugin's pickup "
            "+ capture options. Leave OFF for normal play."
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
        enabled_when=("automate_front_line_stance", False),
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
    adaptive_procurement: bool = boolean_option(
        "AI procurement reads the strategic picture",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        default=True,
        detail=(
            "The AI commander's auto-spend follows its side's strategic read "
            "instead of a fixed split: a surging enemy shifts budget toward the "
            "armor its offensive spends, a consolidating one husbands ground and "
            "rebuilds its air arm, and your own commander leans air-first during "
            "the rollback air war and ground-first in the offensive phase "
            "(rides Red plays with intent / campaign phases -- without those "
            "signals the split is unchanged). Also weights ground-unit buys "
            "toward the side's more capable hardware instead of picking "
            "uniformly at random."
        ),
    )
    auto_repair_air_defenses: bool = boolean_option(
        "AI repairs SAM & EWR sites",
        CAMPAIGN_MANAGEMENT_PAGE,
        HQ_AUTOMATION_SECTION,
        default=False,
        detail=(
            "Each side's AI commander spends budget repairing a couple of "
            "destroyed SAM/EWR units per turn at surviving sites (full unit "
            "price -- the same repair the base card offers you), degraded sites "
            "and radars first. The enemy air-defense belt regenerates unless you "
            "keep pressure on it, so a rolled-back IADS stops being a one-way "
            "ratchet. Command centers and comms nodes are never repaired -- "
            "decapitation stays permanent. For your own side this only runs "
            "when runway repairs are automated."
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
        enabled_when="supercarrier",
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
        default=True,
        detail=(
            "Append a Threat Intel Brief page: the enemy air-defense laydown "
            "(SAM/EWR system, engagement range, HARM ALIC code, bullseye cue and "
            "live/degraded/dead status), modelled on the per-system threat cards in "
            "professional campaign intelligence briefings. Recon-fog aware — an "
            "undiscovered site shows only its intel-tier band ('Unidentified MERAD') "
            "until a TARPS overflight identifies it. On by default."
        ),
    )
    enable_package_code_words: bool = boolean_option(
        "Package code words",
        MISSION_GENERATOR_PAGE,
        KNEEBOARD_SECTION,
        default=False,
        detail=(
            "Give each package three SRS code words (push / success / abort) and surface "
            "them so a briefing can be built before generation: a package tooltip in the "
            "ATO list and a 'PUSH <word>' tag on the join waypoint, plus the code words "
            "on the kneeboard (the flight's own words in the Mission Info BLUF and the "
            "side-wide table on the Support Info page). Human comms aids only — nothing "
            "scripts off them. Off by default."
        ),
    )
    generate_sitrep_kneeboard: bool = boolean_option(
        "Campaign SITREP band on the briefing page",
        MISSION_GENERATOR_PAGE,
        KNEEBOARD_SECTION,
        default=True,
        detail=(
            "Add a short 'what happened last turn' band to the Mission Info "
            "kneeboard page: both sides' losses (enemy as claimed), bases captured or "
            "lost, and downed pilots recovered. Hidden on turn 1 and after a quiet "
            "turn. On by default."
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
    opfor_air_start: bool = boolean_option(
        "Enemy (OPFOR) aircraft start in the air",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=False,
        detail=(
            "When enabled, every AI OPFOR (red) flight spawns airborne regardless of "
            "the AI start type, so the enemy holds the air from mission start and "
            "can't be caught on the ramp. Player and OWNFOR flights are unaffected. "
            "A base that forces a specific start type (e.g. a carrier) still wins."
        ),
    )
    support_air_start: bool = boolean_option(
        "Support aircraft (AWACS/tankers) start in the air",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=False,
        detail=(
            "When enabled, AWACS and tanker flights spawn airborne and on-station "
            "from mission start instead of spending the first several minutes taxiing "
            "and climbing. Applies to both coalitions' AI support flights; "
            "player-crewed flights keep the player start type."
        ),
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
        enabled_when="dynamic_slots",
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
    carrier_deck_policy: CarrierDeckPolicy = choices_option(
        "Carrier six-pack usage",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        choices={v.value: v for v in CarrierDeckPolicy},
        default=CarrierDeckPolicy.LAST_RESORT,
        detail=(
            "The six-pack (the first-filled carrier deck spots) sits in the taxi "
            "lane to the bow catapults, so AI taxiing to launch jam against a "
            "slow-starting player parked there. Last resort spawns player flights "
            "one second after mission start, which makes DCS park them clear of "
            "the six-pack; the six-pack then only fills once the rest of the deck "
            "is full. AI carrier flights always spawn clear of the six-pack."
        ),
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
    artillery_base_harassment: bool = boolean_option(
        "Frontline artillery harassment on forward airbases",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "Airfields and FARPs within enemy tube/rocket artillery reach of a front "
            "line (~20 NM) draw sporadic standoff harassment fire during the mission "
            "-- a FARP sitting on the FLOT is a base under fire, not a safe ramp. "
            "Symmetric (both sides' forward fields). Mostly noise and smoke with a "
            "modest bite; never targets a field a player spawns at or recovers to, "
            "and a startup grace period protects a cold-starting player. Runs via "
            "the 'Vietnam Ops & standoff harassment' LUA plugin -- keep that plugin "
            "enabled or this setting does nothing. (The Vietnam Ops siege toggle is "
            "this same runtime with theater-wide reach.)"
        ),
    )
    artillery_harassment_reach_km: int = bounded_int_option(
        "Frontline artillery harassment reach (km)",
        enabled_when="artillery_base_harassment",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=35,
        min=10,
        max=120,
        detail=(
            "How near a front line an occupied airfield or FARP must be to draw "
            "frontline artillery harassment. The default 35 km is real tube/rocket "
            "reach off the FLOT; raise it for long-range MRLs (or a laydown whose "
            "forward fields sit a little farther back). Only used when 'Frontline "
            "artillery harassment on forward airbases' is on; the Vietnam Ops siege "
            "toggle keeps its own theater-wide reach."
        ),
    )
    mobile_missile_relocation: bool = boolean_option(
        "Mobile missile sites relocate (shoot and scoot)",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "Mobile theater-missile sites (SCUD/SSM groups -- never the radar SAM "
            "network) drive to a new position every few minutes during the mission "
            "instead of parking where your last recon photographed them, so the "
            "SCUD hunt is a hunt for something that moves. Movement only: kills "
            "record normally, the site stays within a few km of its campaign-map "
            "position, and nothing changes at turn end. Applies to both sides."
        ),
    )
    coastal_missile_relocation: bool = boolean_option(
        "Coastal anti-ship sites relocate too (shoot and scoot)",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "Extends the shoot-and-scoot behaviour above to coastal anti-ship "
            "missile sites with genuinely mobile hardware, so a shore battery is "
            "never quite where your last recon photographed it -- the "
            "coastal-missile hunt. The vanilla Silkworm battery is a fixed "
            "emplacement and is never routed (driving it produces no movement, "
            "only a ground-AI storm that tanks the frame rate), so this only "
            "matters for mod coastal sites whose launchers can actually drive. "
            "Off by default; movement only, both sides, same guarantees as above."
        ),
    )
    mission_briefing_popup: bool = boolean_option(
        "Mission-start briefing popup",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "When a pilot slots into an aircraft, show a short on-screen card -- "
            "campaign, mission number, date, mission time, callsign, aircraft, task, "
            "and departure field -- the way the professional DCS campaigns greet you "
            "at mission start. Fires at mission start in single-player and whenever a "
            "pilot slots in or rejoins on a server. Display only: no gameplay change. "
            "Card duration and the startup grace are options on the 'Mission-start "
            "briefing popup' plugin."
        ),
    )
    host_red_scramble: bool = boolean_option(
        "Host tool: F10 red-interceptor scramble menu",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "A game-master lever for multiplayer events: the mission carries cold "
            "clone templates of the enemy's fighters, and an F10 'HOST: Red Scramble' "
            "menu can launch a 2/4-ship from any red airfield and vector it straight "
            "onto the nearest friendly fighters -- the emergency 'give the flight "
            "something to shoot' button for a session gone quiet. Restrict who sees "
            "the menu with the redscramble plugin's 'Host player names' option: "
            "comma-separated DCS names or name fragments (substring match, so a "
            "static tag like 'Flash' covers 'Viper 1-1 | Flash' whatever the flight "
            "prefix); empty shows it to every BLUE client. "
            "Spawned bandits are free and untracked by design -- killing them "
            "changes nothing at the turn boundary; they are event content only."
        ),
    )
    civilian_air_traffic: bool = boolean_option(
        "Civilian background air traffic",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "Neutral civilian aircraft (airliners, freighters, light props and "
            "helicopters) fly multi-leg milk runs between uncontrolled rear-area "
            "airfields for ambient life. They keep ~40 NM clear of the front line "
            "but NOT of deep BVR/intercept corridors, so a campaign whose air war "
            "reaches far behind the lines may want this off: an IL-76 at altitude "
            "is indistinguishable from a military transport on radar (the flown "
            "Red Tide M1 lost a neutral airliner to a long-range Phoenix shot)."
        ),
    )
    ambient_supply_convoys: bool = boolean_option(
        "Ambient supply convoys (both sides' roads have traffic)",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "Every turn, each side's supply-convoy flow is topped up to a small "
            "randomized number of real columns on its own road network -- some "
            "sharing a road, some on different ones -- so there is always traffic "
            "to protect, hunt, and see. The columns are real, tracked units riding "
            "the engine's own convoy system: enemy ones are ordinary Armed Recon/"
            "BAI targets, friendly ones are subject to the convoy-ambush roll, and "
            "every loss counts at debrief. A side with no road between two of its "
            "own bases (island maps) simply gets none."
        ),
    )
    convoy_ambush: bool = boolean_option(
        "Friendly convoy ambushes (support your convoys)",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "Your own supply convoys run the roads behind the lines, and sometimes -- "
            "it is a chance, never a certainty -- hidden enemy ambush teams dig in "
            "along the route: one contact, or a gauntlet of five or six down the same "
            "road. Nothing is telegraphed: the convoy looks like any other friendly "
            "convoy and no objective or escort package appears in the UI -- the first "
            "sign is the TROOPS IN CONTACT call when an ambush springs, and supporting "
            "the column (or not) is your call. Left unsupported, an ambushed convoy is "
            "ground down and the supplies never arrive. The convoy and the ambushers "
            "are real, tracked units -- both sides' losses count. Runs via the 'Convoy "
            "ambush' LUA plugin -- keep that plugin enabled or this setting does "
            "nothing."
        ),
    )
    air_droppable_minefields: bool = boolean_option(
        "Air-droppable minefields (mines persist across turns)",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "A blue jet can air-drop a CBU-99 cluster dispenser (the 'Aerial "
            "Minefield' loadout) and the impact area becomes a scripted proximity "
            "minefield that detonates on enemy convoys crossing it -- the same "
            "mission you drop it. With this on, a field left undisturbed at mission "
            "end is tracked and re-laid into the next mission, depleting as convoys "
            "hit it and clearing once spent; it shows on the F10 map for your side "
            "only. The mines kill real, tracked convoy units, so losses count at "
            "debrief (no phantom spawns); blue-only. Runs via the 'Air-droppable "
            "minefields' LUA plugin -- keep that plugin enabled. The same-turn "
            "mining works with just the plugin on; this setting adds the cross-turn "
            "persistence."
        ),
    )
    auto_plan_minefields: bool = boolean_option(
        "Auto-plan mining sorties ahead of enemy convoys",
        enabled_when="air_droppable_minefields",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "With this on, the auto-planner frags one air-drop mining sortie a turn "
            "against an enemy supply convoy -- a mining-capable jet (one carrying the "
            "'Aerial Minefield' loadout) flies BAI at the convoy and drops the "
            "dispenser, laying a minefield on its road. Fly it yourself or let the AI "
            "take it. Off = only you lay mines, by hand. Needs the 'Air-droppable "
            "minefields' setting on and a blue squadron that can carry the CBU-99 "
            "dispenser (A-7E / Hornet / Harrier)."
        ),
    )
    cruise_missile_strikes: bool = boolean_option(
        "Ship-launched cruise missile strikes",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "Warships that carry land-attack cruise missiles (the Burke's "
            "Tomahawks, the CurrentHill Kalibr ships) can fire them at shore "
            "targets: an F10 'Cruise Missile Strike' menu calls a salvo onto your "
            "last map marker from the nearest ship with missiles left. Each ship "
            "group carries a finite campaign magazine -- there is no rearm, so "
            "every salvo spends stock you never get back. The missiles are real "
            "weapons from a real, tracked ship: kills count at debrief, enemy "
            "point defense can intercept them, and sinking the shooter ends the "
            "raids. Symmetric. Runs via the 'Cruise missile strikes' LUA plugin "
            "-- keep that plugin enabled or this setting does nothing."
        ),
    )
    cruise_missile_auto_raids: bool = boolean_option(
        "Auto-plan cruise missile raids",
        enabled_when="cruise_missile_strikes",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "Each turn, a side with a cruise-missile ship in range commits one "
            "raid: a salvo fired early in the mission at its highest-value "
            "reachable enemy ground object -- command centers and comms first, "
            "then war-industry buildings, then anything strikeable. Your own "
            "raids respect the campaign ROE zones. Watch for the LAUNCH WARNING: "
            "an enemy raid is your point-defense SAMs' problem -- or yours."
        ),
    )
    enemy_comms_jamming: bool = boolean_option(
        "Enemy comms jamming (IADS C2 nodes step on your radios)",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=False,
        detail=(
            "Alive enemy IADS communications and command-center nodes flood your "
            "briefed radio channels with duty-cycled barrage noise during the "
            "mission (intra-flight and AWACS channels only -- never GUARD, never "
            "ATC), transmitted from the node's map position with real power/"
            "distance falloff, so SRS users hear it through their cockpit-tuned "
            "radios. The kneeboard's Mission Info BLUF gains a JAM BACKUP channel "
            "(next to the code words) the jammer never touches; destroying the C2 "
            "node (an ordinary IADS "
            "strike target) silences it for good. Audio pressure only -- no "
            "force-model change. Runs via the 'Comms jamming' LUA plugin -- keep "
            "that plugin enabled or this setting does nothing."
        ),
    )
    comms_jam_requires_capture: bool = boolean_option(
        "Comms jamming needs captured aircrew (the intel gate)",
        enabled_when="enemy_comms_jamming",
        page=MISSION_GENERATION_PAGE,
        section=GENERAL_SECTION,
        default=True,
        detail=(
            "The enemy can only jam channels it knows -- and it learns them from "
            "a captured pilot's comms plan. With this on (the default), comms "
            "jamming stays silent until the Combat SAR capture race is lost: a "
            "pilot captured mid-mission compromises the net within minutes, and "
            "a POW held from an earlier turn means the channels are compromised "
            "from mission start until they are freed or written off (the comms "
            "plan is then rotated). Rescuing your people keeps the net clean. "
            "Turn this off for ambient jamming whenever an enemy C2 node is "
            "alive. No effect unless 'Enemy comms jamming' is on."
        ),
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
    vietnam_commitment_ceiling: bool = boolean_option(
        "Commitment ceiling (will-coupled war budget)",
        VIETNAM_OPS_PAGE,
        "Campaign",
        enabled_when="vietnam_political_will",
        detail=(
            "As your Political Will falls, Congress trims the war budget -- your "
            "income is scaled down toward a floor as the home front turns, so a "
            "flagging war is starved of replacements (the war is taken away from "
            "you, not just lost at the table). Full funding while will stays high; "
            "the cut only bites once patience is already low. Needs Political will "
            "tracking on; affects your coalition only."
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
        enabled_when="perf_smoke_gen",
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
    perf_ground_ai_sleep: bool = boolean_option(
        "Distant ground AI sleeps until aircraft approach",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
        detail=(
            "The graduated alternative to culling: rear-area garrison vehicle groups "
            "keep existing (visible, strikeable, recon/BDA and threat rings stay "
            "honest, kills record normally) but their AI is switched off at mission "
            "start and woken only while an aircraft -- either side's -- is within the "
            "wake radius, cutting the sim cost of hundreds of thinking ground units. "
            "Air defenses, the front line, convoys and every scripted mover are never "
            "touched. Composes with culling: sleep what you keep, cull only what you "
            "never want to exist. Runtime lives in the 'Ground AI sleep' LUA plugin "
            "(wake radius and cadence tunable there)."
        ),
    )
    perf_culling: bool = boolean_option(
        "Culling of distant units enabled",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
    )
    perf_culling_distance: int = bounded_int_option(
        "Culling distance (km)",
        enabled_when="perf_culling",
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

        # The carrier six-pack boolean became the CarrierDeckPolicy enum (§64).
        # ON exempted player flights from the off-six-pack placement delay (so
        # they filled the six-pack); OFF already behaved like the last-resort
        # policy. Preserve whichever the save had; the old key is dropped in the
        # obsolete-key sweep below.
        if (
            "carrier_deck_policy" not in migrated
            and "player_flights_sixpack" in migrated
        ):
            migrated["carrier_deck_policy"] = (
                CarrierDeckPolicy.SIXPACK_FIRST
                if migrated["player_flights_sixpack"]
                else CarrierDeckPolicy.LAST_RESORT
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

        # A save from before the scatter band carried only the symmetric
        # max_plane_altitude_offset. Mirror it into the new minimum so the
        # legacy +/-max spread is preserved exactly: a flat -2 default would
        # re-enable scatter on a save that had set max to 0, and shrink the
        # downward half of a wider band.
        if (
            "min_plane_altitude_offset" not in migrated
            and "max_plane_altitude_offset" in migrated
        ):
            migrated["min_plane_altitude_offset"] = -migrated[
                "max_plane_altitude_offset"
            ]

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
            # Consolidated into the CarrierDeckPolicy enum (value already
            # migrated above).
            "player_flights_sixpack",
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
