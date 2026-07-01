from dataclasses import dataclass, field, replace
from datetime import timedelta
from typing import FrozenSet, Mapping, Optional

from game.ato.flighttype import FlightType
from game.data.units import UnitClass
from game.settings import Settings
from game.utils import Distance, feet, nautical_miles, Speed, knots


@dataclass
class GroundUnitProcurementRatios:
    ratios: dict[UnitClass, float]

    def for_unit_class(self, unit_class: UnitClass) -> float:
        try:
            return self.ratios[unit_class] / sum(self.ratios.values())
        except KeyError:
            return 0.0


@dataclass(frozen=True)
class Doctrine:
    name: str

    cas: bool
    cap: bool
    sead: bool
    strike: bool
    antiship: bool

    #: The minimum distance between the departure airfield and the hold point.
    hold_distance: Distance

    #: The minimum distance between the hold point and the join point.
    push_distance: Distance

    #: The distance between the join point and the ingress point. Only used for the
    #: fallback flight plan layout (when the departure airfield is near a threat zone).
    join_distance: Distance

    #: The maximum distance between the ingress point (beginning of the attack) and
    #: target.
    max_ingress_distance: Distance

    #: The minimum distance between the ingress point (beginning of the attack) and
    #: target.
    min_ingress_distance: Distance

    min_patrol_altitude: Distance
    max_patrol_altitude: Distance

    min_cruise_altitude: Distance
    max_cruise_altitude: Distance

    min_combat_altitude: Distance
    max_combat_altitude: Distance

    #: The duration that CAP flights will remain on-station.
    cap_duration: timedelta

    #: The minimum length of the CAP race track.
    cap_min_track_length: Distance

    #: The maximum length of the CAP race track.
    cap_max_track_length: Distance

    #: The minimum distance between the defended position and the *end* of the
    #: CAP race track.
    cap_min_distance_from_cp: Distance

    #: The maximum distance between the defended position and the *end* of the
    #: CAP race track.
    cap_max_distance_from_cp: Distance

    #: The engagement range of CAP flights. Any enemy aircraft within this range
    #: of the CAP's current position will be engaged by the CAP.
    cap_engagement_range: Distance

    cas_duration: timedelta

    sweep_distance: Distance

    ground_unit_procurement_ratios: GroundUnitProcurementRatios

    rtb_speed: Speed

    sead_escort_spacing: Distance

    escort_spacing: Distance

    sead_escort_engagement_range: Distance

    escort_engagement_range: Distance

    #: Per-doctrine display-name overrides for taskings, e.g. ``{BARCAP: "MiGCAP"}``.
    #: A *display layer only* -- it does NOT touch the persisted ``FlightType`` value,
    #: so saves stay compatible (see the Vietnam Retribution design note). Empty (the
    #: default) means every tasking uses ``FlightType.value``, the existing behaviour.
    task_display_names: Mapping[FlightType, str] = field(default_factory=dict)

    #: The taskings the auto-planner may produce under this doctrine. ``None`` (the
    #: default) means no restriction -- the existing behaviour. Used to drop era-
    #: inappropriate taskings (e.g. DEAD/ANTISHIP under Vietnam doctrine) at the
    #: planner edge.
    tasking_whitelist: Optional[FrozenSet[FlightType]] = None

    #: When True, Strike/BAI may be planned into target areas still covered by enemy
    #: air defenses instead of waiting for a SEAD/DEAD suppression first. Needed for
    #: eras with no reliable SEAD (Vietnam): otherwise dense AAA/SAM coverage blocks
    #: every offensive target and the whole attack fleet deadlocks. The threat is still
    #: recorded for DEAD targeting; the planner just stops *blocking* on it. A simple
    #: ``= False`` default (not ``field(...)``) so old pickled doctrines fall back to it.
    strike_through_air_defense_threat: bool = False

    #: When True, an offensive package whose required A2A/SEAD escort cannot be
    #: allocated (no fighter free) is flown UNESCORTED rather than scrubbed. Needed for
    #: eras with too few fighters to escort everything (Vietnam: the handful of fighters
    #: are consumed escorting AWACS/tankers + BARCAP, so without this every Strike/BAI/CAS
    #: scrubs on its missing escort). Pairs with strike_through_air_defense_threat to
    #: unblock the offensive fleet. Simple ``= False`` default (save-safe class attr).
    plan_strikes_without_full_escort: bool = False

    #: How many coordinated STRIKE sections an "Alpha Strike" fans onto one target.
    #: The default 1 is the stock single-section strike. Raising it (> 1) concentrates
    #: more aircraft on the same aimpoint at a *shared TOT* -- a real Alpha Strike -- so
    #: each struck target is hit harder, at the cost of covering fewer separate targets
    #: per turn (same total air effort, fewer/harder strikes; aircraft scarcity is the
    #: limiter either way). Simple ``= 1`` default (save-safe class attr); clamped to
    #: >= 1 at the planner edge.
    strike_flight_count: int = 1

    #: When True, a STRIKE-led package always plans an A2A fighter escort even when the
    #: planner detects no air threat on the route -- the era's MiG presence is sparse and
    #: unpredictable and the bombers are the most exposed asset, so they should not fly
    #: naked. The escort is still pruned when no fighter is free (can_plan_escort), and
    #: the package then flies unescorted under plan_strikes_without_full_escort. Simple
    #: ``= False`` default (save-safe class attr).
    always_escort_strikes: bool = False

    #: GCI-ambush posture (Vietnam campaign layer W5, will-note section 6). When True,
    #: this side's QRA intercept dispatcher flies era GCI hit-and-run instead of the
    #: modern duel: the engage radius shrinks to ``cap_engagement_range`` (the P1c
    #: close-fight number), the scramble (GCI) radius tightens so MiGs launch LATE and
    #: slash the strike package near its target instead of meeting the sweep far out,
    #: and the Lua side leashes the defenders (small disengage radius + a high fuel
    #: threshold) so they hit, run, and recover rather than fight to destruction.
    #: Simple ``= False`` default (save-safe class attr).
    gci_ambush: bool = False

    def display_name_for(self, flight_type: FlightType) -> str:
        """The doctrine's display label for a tasking (the rename layer)."""
        return self.task_display_names.get(flight_type, flight_type.value)

    def allows(self, flight_type: FlightType) -> bool:
        """Whether the auto-planner may produce this tasking under this doctrine."""
        return self.tasking_whitelist is None or flight_type in self.tasking_whitelist

    def from_settings(self, settings: Settings) -> "Doctrine":
        # not sure if we're actually going to need this one,
        # let it be for the time being, perhaps we'll make doctrines configurable...
        return Doctrine(
            name=self.name,
            cap=self.cap,
            cas=self.cas,
            sead=self.sead,
            strike=self.strike,
            antiship=self.antiship,
            hold_distance=self.hold_distance,
            push_distance=self.push_distance,
            join_distance=self.join_distance,
            max_ingress_distance=self.max_ingress_distance,
            min_ingress_distance=self.min_ingress_distance,
            min_patrol_altitude=self.min_patrol_altitude,
            max_patrol_altitude=self.max_patrol_altitude,
            min_cruise_altitude=self.min_cruise_altitude,
            max_cruise_altitude=self.max_cruise_altitude,
            min_combat_altitude=self.min_combat_altitude,
            max_combat_altitude=self.max_combat_altitude,
            cap_duration=settings.desired_barcap_mission_duration,
            cap_min_track_length=self.cap_min_track_length,
            cap_max_track_length=self.cap_max_track_length,
            cap_min_distance_from_cp=self.cap_min_distance_from_cp,
            cap_max_distance_from_cp=self.cap_max_distance_from_cp,
            cap_engagement_range=self.cap_engagement_range,
            cas_duration=self.cas_duration,
            sweep_distance=self.sweep_distance,
            ground_unit_procurement_ratios=self.ground_unit_procurement_ratios,
            rtb_speed=self.rtb_speed,
            sead_escort_spacing=self.sead_escort_spacing,
            escort_spacing=self.escort_spacing,
            sead_escort_engagement_range=self.sead_escort_engagement_range,
            escort_engagement_range=self.escort_engagement_range,
            task_display_names=self.task_display_names,
            tasking_whitelist=self.tasking_whitelist,
            strike_through_air_defense_threat=self.strike_through_air_defense_threat,
            plan_strikes_without_full_escort=self.plan_strikes_without_full_escort,
            strike_flight_count=self.strike_flight_count,
            always_escort_strikes=self.always_escort_strikes,
            gci_ambush=self.gci_ambush,
        )


MODERN_DOCTRINE = Doctrine(
    "modern",
    cap=True,
    cas=True,
    sead=True,
    strike=True,
    antiship=True,
    hold_distance=nautical_miles(25),
    push_distance=nautical_miles(20),
    join_distance=nautical_miles(20),
    max_ingress_distance=nautical_miles(45),
    min_ingress_distance=nautical_miles(10),
    min_patrol_altitude=feet(15000),
    max_patrol_altitude=feet(33000),
    min_cruise_altitude=feet(10000),
    max_cruise_altitude=feet(40000),
    min_combat_altitude=feet(1000),
    max_combat_altitude=feet(35000),
    cap_duration=timedelta(minutes=30),
    cap_min_track_length=nautical_miles(15),
    cap_max_track_length=nautical_miles(40),
    cap_min_distance_from_cp=nautical_miles(10),
    cap_max_distance_from_cp=nautical_miles(40),
    cap_engagement_range=nautical_miles(50),
    cas_duration=timedelta(minutes=30),
    sweep_distance=nautical_miles(60),
    ground_unit_procurement_ratios=GroundUnitProcurementRatios(
        {
            UnitClass.TANK: 3,
            UnitClass.ATGM: 2,
            UnitClass.APC: 2,
            UnitClass.IFV: 3,
            UnitClass.ARTILLERY: 1,
            UnitClass.SHORAD: 2,
            UnitClass.RECON: 1,
        }
    ),
    rtb_speed=knots(500),
    sead_escort_spacing=feet(1000),
    escort_spacing=feet(2000),
    sead_escort_engagement_range=nautical_miles(40),
    escort_engagement_range=nautical_miles(30),
)

COLDWAR_DOCTRINE = Doctrine(
    name="coldwar",
    cap=True,
    cas=True,
    sead=True,
    strike=True,
    antiship=True,
    hold_distance=nautical_miles(15),
    push_distance=nautical_miles(10),
    join_distance=nautical_miles(10),
    max_ingress_distance=nautical_miles(30),
    min_ingress_distance=nautical_miles(10),
    min_patrol_altitude=feet(10000),
    max_patrol_altitude=feet(24000),
    min_cruise_altitude=feet(10000),
    max_cruise_altitude=feet(30000),
    min_combat_altitude=feet(1000),
    max_combat_altitude=feet(25000),
    cap_duration=timedelta(minutes=30),
    cap_min_track_length=nautical_miles(12),
    cap_max_track_length=nautical_miles(24),
    cap_min_distance_from_cp=nautical_miles(8),
    cap_max_distance_from_cp=nautical_miles(25),
    cap_engagement_range=nautical_miles(35),
    cas_duration=timedelta(minutes=30),
    sweep_distance=nautical_miles(40),
    ground_unit_procurement_ratios=GroundUnitProcurementRatios(
        {
            UnitClass.TANK: 4,
            UnitClass.ATGM: 2,
            UnitClass.APC: 3,
            UnitClass.IFV: 2,
            UnitClass.ARTILLERY: 1,
            UnitClass.SHORAD: 2,
            UnitClass.RECON: 1,
        }
    ),
    rtb_speed=knots(450),
    sead_escort_spacing=feet(500),
    escort_spacing=feet(1000),
    sead_escort_engagement_range=nautical_miles(25),
    escort_engagement_range=nautical_miles(20),
)

WWII_DOCTRINE = Doctrine(
    name="ww2",
    cap=True,
    cas=True,
    sead=False,
    strike=True,
    antiship=True,
    hold_distance=nautical_miles(10),
    push_distance=nautical_miles(5),
    join_distance=nautical_miles(5),
    max_ingress_distance=nautical_miles(7),
    min_ingress_distance=nautical_miles(5),
    min_patrol_altitude=feet(4000),
    max_patrol_altitude=feet(15000),
    min_cruise_altitude=feet(5000),
    max_cruise_altitude=feet(30000),
    min_combat_altitude=feet(1000),
    max_combat_altitude=feet(10000),
    cap_duration=timedelta(minutes=30),
    cap_min_track_length=nautical_miles(8),
    cap_max_track_length=nautical_miles(18),
    cap_min_distance_from_cp=nautical_miles(0),
    cap_max_distance_from_cp=nautical_miles(5),
    cap_engagement_range=nautical_miles(20),
    cas_duration=timedelta(minutes=30),
    sweep_distance=nautical_miles(10),
    ground_unit_procurement_ratios=GroundUnitProcurementRatios(
        {
            UnitClass.TANK: 3,
            UnitClass.ATGM: 3,
            UnitClass.APC: 3,
            UnitClass.ARTILLERY: 1,
            UnitClass.SHORAD: 3,
            UnitClass.RECON: 1,
        }
    ),
    rtb_speed=knots(300),
    sead_escort_spacing=feet(100),
    escort_spacing=feet(200),
    sead_escort_engagement_range=nautical_miles(10),
    escort_engagement_range=nautical_miles(5),
)

# Vietnam-era tasking renames (the "Vietnam Retribution" mode display layer). Keys are
# the persisted FlightType members; values are the era display labels shown in the UI /
# kneeboard. Only the iconic, unambiguous renames are mapped -- everything unmapped keeps
# its canonical FlightType.value. NB: this is display-only; the enum values are untouched.
VIETNAM_TASK_DISPLAY_NAMES: Mapping[FlightType, str] = {
    FlightType.BARCAP: "MiGCAP",
    FlightType.INTERCEPTION: "GCI Intercept",
    FlightType.SEAD: "Iron Hand",
    FlightType.SEAD_ESCORT: "Iron Hand Escort",
    FlightType.SEAD_SWEEP: "Weasel Sweep",
    FlightType.STRIKE: "Alpha Strike",
    FlightType.BAI: "Interdiction",
    FlightType.OCA_RUNWAY: "Airfield Strike",
    FlightType.OCA_AIRCRAFT: "Airfield Strike",
    FlightType.TARPS: "Photo Recon",
    FlightType.SCAR: "Sandy",
    FlightType.JAMMING: "Standoff Jamming",
    FlightType.AEWC: "College Eye",
    FlightType.TRANSPORT: "Airlift",
}

# Taskings the Vietnam auto-planner must never produce. Vietnam air wings have no
# reliable SEAD (the current campaigns field no Wild Weasel) and no naval threat worth
# an anti-ship strike, and the strike planner already punches through air defenses
# without suppression (strike_through_air_defense_threat). Leaving these in only wastes
# planning attempts the faction can't fulfill AND mis-assigns era jets to roles they
# never flew -- e.g. an A-1 Skyraider grabbed for a "SEAD Sweep" because its DCS task
# list happens to include SEAD. DEAD/ANTISHIP are package *primaries* (dropping them
# scrubs the whole package); the SEAD trio only ever appears as *escorts* (dropping
# them flies the package unescorted, which pairs with plan_strikes_without_full_escort).
VIETNAM_DROPPED_TASKINGS: FrozenSet[FlightType] = frozenset(
    {
        FlightType.DEAD,
        FlightType.SEAD,
        FlightType.SEAD_ESCORT,
        FlightType.SEAD_SWEEP,
        FlightType.ANTISHIP,
    }
)

# The allowed set is computed from the whole enum minus the drops, so a newly added
# FlightType defaults to allowed (fail-open) rather than being silently gated out.
VIETNAM_TASKING_WHITELIST: FrozenSet[FlightType] = frozenset(
    set(FlightType) - VIETNAM_DROPPED_TASKINGS
)

# Period-authentic Vietnam ground order of battle. The Cold War Central-Front ratio is an
# armour + ATGM + IFV fist (TANK:4, ATGM:2, IFV:2); the Vietnam ground war was the opposite
# -- infantry-dominant, artillery-heavy, with only light/late armour and NO meaningful ATGM
# or IFV presence (the ATGM-decisive war was Yom Kippur, not Vietnam). This buys the two
# sides a genuinely different ground force to strike/defend: mass infantry + guns + mobile
# AAA (SHORAD) instead of tank divisions. ATGM/IFV are omitted (ratio 0 -> never procured;
# see procurement.most_needed_unit_class). Applies to every faction on VIETNAM_DOCTRINE.
VIETNAM_GROUND_PROCUREMENT = GroundUnitProcurementRatios(
    {
        UnitClass.INFANTRY: 4,
        UnitClass.APC: 3,
        UnitClass.ARTILLERY: 2,
        UnitClass.TANK: 2,
        UnitClass.SHORAD: 2,
        UnitClass.RECON: 1,
    }
)

# Vietnam doctrine. The era identity is the display-name layer + the P3 behaviour changes
# (strike_through_air_defense_threat -- Vietnam has no reliable SEAD, so the modern "suppress
# before you strike" rule otherwise deadlocks the whole offensive fleet, root-caused
# 2026-06-28: 0/28 strike + 0/13 BAI plannable; the tasking whitelist that drops
# SEAD/DEAD/anti-ship; a single-section STRIKE (strike_flight_count=1) that always pulls a
# fighter escort (always_escort_strikes)) -- PLUS the period-authentic planner *numbers* that
# make the era play differently, not just read differently:
#   * A2A engagement ranges are knife-fight, not BVR: the early Sparrow (AIM-7E, unreliable)
#     and short IR Sidewinder (AIM-9B/D) + guns fight close, so MiGCAP/escort engage far
#     nearer than the modern standoff -- cap 35->22 NM, escort 20->10 NM (between WWII 20/5
#     and Cold War 35/20). This turns intercepts into visual merges instead of BVR shots.
#   * rtb_speed drops to the subsonic period cruise (450 -> 400 kt).
#   * the ground OOB above (infantry/artillery/AAA-heavy, no ATGM/IFV).
# See docs/dev/design/414th-vietnam-retribution-notes.md.
VIETNAM_DOCTRINE = replace(
    COLDWAR_DOCTRINE,
    name="vietnam",
    task_display_names=VIETNAM_TASK_DISPLAY_NAMES,
    tasking_whitelist=VIETNAM_TASKING_WHITELIST,
    strike_through_air_defense_threat=True,
    plan_strikes_without_full_escort=True,
    strike_flight_count=1,
    always_escort_strikes=True,
    gci_ambush=True,
    cap_engagement_range=nautical_miles(22),
    escort_engagement_range=nautical_miles(10),
    rtb_speed=knots(400),
    ground_unit_procurement_ratios=VIETNAM_GROUND_PROCUREMENT,
)

ALL_DOCTRINES = [
    COLDWAR_DOCTRINE,
    MODERN_DOCTRINE,
    WWII_DOCTRINE,
    VIETNAM_DOCTRINE,
]
