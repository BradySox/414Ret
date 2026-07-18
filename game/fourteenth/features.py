"""The 414th feature registry — one self-describing entry per feature.

The fork carries ~30 features layered on upstream Retribution. The "what features
exist and how is each wired" knowledge (which Lua plugin runs it, which
``Settings`` toggle gates it, which features-doc section documents it) used to live
only in prose that drifts as code changes. This module makes it a *data structure*
that the docs and CI are checked against:

* Every numbered feature in the CLAUDE.md "Features at a Glance" list is a
  :class:`Feature` in :data:`FEATURES` (plus the always-on engine plugins).
* :func:`render_feature_index` renders the registry to the committed Markdown
  catalog ``docs/dev/414th-feature-index.md``.
* ``tests/fourteenth/test_features_registry.py`` makes drift a CI failure: every
  plugin/``Settings`` reference must resolve, the registry must cover exactly the
  numbered feature list, every in-game-pass checklist ``§N`` must be registered,
  and the generated catalog must be current.

The registry deliberately does **not** duplicate the prose descriptions or the
checklist's hand-authored pass criteria/status — those are human knowledge. It
owns the *structure* (the feature set + wiring) and keeps the prose honest.

Regenerate the catalog after editing this file::

    python -m game.fourteenth.features
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Feature:
    """One 414th feature and its concrete wiring.

    ``key`` is a stable slug (never user-facing); ``title`` matches the CLAUDE.md
    "Features at a Glance" entry. ``doc_section`` is the §N in
    ``docs/dev/414th-features.md`` (None for features documented only in design
    notes, e.g. the engine plugins). ``plugin_id`` is a ``resources/plugins/<id>``
    directory; ``settings_fields`` are ``Settings`` dataclass field names that gate
    the feature. ``retired`` marks a feature kept in the list as a tombstone.
    """

    key: str
    title: str
    doc_section: int | None = None
    plugin_id: str | None = None
    settings_fields: tuple[str, ...] = ()
    retired: bool = False


# THE registry. One entry per numbered "Features at a Glance" item (§1-30), plus
# the always-on engine plugins (no numbered section) at the end. Wiring fields are
# filled where a feature has a plugin and/or a Settings toggle; pure-behavior
# features carry none. The tests keep every reference honest and the set complete.
FEATURES: tuple[Feature, ...] = (
    Feature("qra_intercept_reserve", "QRA intercept reserve", 1, plugin_id="intercept"),
    Feature("jamming_c130j", "JAMMING flight type", 2, plugin_id="c130j"),
    Feature(
        "tarps_recon_fog",
        "TARPS recon + BDA fog-of-war",
        3,
        settings_fields=("recon_intel_fog", "concealed_enemy_forces"),
    ),
    Feature("ui_transparency", "UI transparency", 4),
    Feature("target_location_precision", "Player target location precision", 5),
    Feature("air_defense_planning", "Air-defense planning rework", 6),
    Feature("auto_hide_mobile_sams", "Auto-hide mobile SAMs on MFD", 7),
    Feature("robustness_fixes", "Robustness / crash fixes", 8),
    Feature("tic", "TIC — Troops In Contact", 9, plugin_id="tic"),
    Feature("currenthill_iran_pack", "CurrentHill Iran assets pack", 10),
    Feature(
        "dtc_cartridge_export",
        "Native DCS DTC cartridge export",
        11,
        retired=True,
    ),
    Feature("tars_recon_engine", "TARS recon engine", 12, plugin_id="tars"),
    Feature("flight_control_atc", "Flight Control ATC", 13, retired=True),
    Feature("plugin_options_ui", "Plugin Options UI", 14),
    Feature(
        "scar_rescue",
        'SCAR — RESCAP "Sandy" rescue escort',
        15,
        plugin_id="combatsar",
        settings_fields=("scar_command_post_intel",),
    ),
    Feature("settings_qol_audit", "Settings QOL audit", 16),
    Feature(
        "planner_unpredictability",
        "Auto-planner target unpredictability",
        17,
        settings_fields=(
            "ownfor_planner_unpredictability",
            "opfor_planner_unpredictability",
        ),
    ),
    Feature("fog_overview_toggle", "Fog-of-war overview toggle", 18),
    Feature("map_layers_panel", "Unified map layers panel", 19),
    Feature(
        "drop_spawn_placement",
        "Drop-spawn: map right-click unit placement",
        20,
        settings_fields=("enable_unit_placement", "enable_free_unit_placement"),
    ),
    Feature(
        "combat_sar",
        "Combat SAR",
        21,
        plugin_id="combatsar",
        settings_fields=(
            "auto_combat_sar",
            "combat_sar_persistent_pilots",
            "combat_sar_surge",
        ),
    ),
    Feature(
        "kneeboard_custom_import", "Kneeboard space-utilisation + custom import", 22
    ),
    Feature("per_squadron_country", "Per-squadron DCS country", 23),
    Feature(
        "date_gated_aircraft_properties",
        "Date-gated aircraft properties",
        24,
        settings_fields=("restrict_props_by_date",),
    ),
    Feature(
        "compact_kneeboard",
        "Compact 3-4 page kneeboard deck",
        25,
        retired=True,
    ),
    Feature("off_mission_combat", "Off-mission combat fidelity + PLAYER_AT_IP fix", 26),
    Feature("shared_airframe_kneeboard", "Shared-airframe kneeboard index", 27),
    Feature("settings_ia_reorg", "Settings IA reorg + difficulty presets", 28),
    Feature(
        "sitrep_kneeboard",
        "Campaign SITREP kneeboard band",
        29,
        settings_fields=("generate_sitrep_kneeboard",),
    ),
    Feature(
        "kneeboard_cover_page",
        "Dedicated kneeboard cover page",
        30,
        retired=True,
    ),
    Feature(
        "brief_sheet_kneeboard",
        "One-page Brief Sheet + deck-wide colour scheme",
        31,
        retired=True,
    ),
    Feature(
        "vietnam_arc_light",
        "Arc Light heavy-bomber Strike carpet",
        32,
        plugin_id="vietnamops",
        settings_fields=("vietnam_arc_light",),
    ),
    Feature(
        "vietnam_flak_gauntlet",
        "AAA flak gauntlet",
        33,
        plugin_id="vietnamops",
        settings_fields=("vietnam_flak_gauntlet",),
    ),
    Feature(
        "vietnam_naval_gunfire",
        "Naval gunfire support",
        34,
        plugin_id="vietnamops",
        settings_fields=("vietnam_naval_gunfire",),
    ),
    Feature(
        # Convoy interdiction is a force-model feature (a real, tracked enemy convoy created
        # in game/fourteenth/vietnam_convoy.py from finish_turn), not a vietnamops plugin
        # behaviour -- hence no plugin_id.
        "vietnam_convoy_interdiction",
        "Convoy interdiction (Steel Tiger)",
        35,
        settings_fields=("vietnam_convoy_interdiction",),
    ),
    Feature(
        # The generic artillery_base_harassment setting reuses this same
        # emitter+runtime with a tight FLOT-gun-range reach (conventional
        # campaigns; Red Tide preseeds it for the Fulda FARP).
        "vietnam_airbase_harassment",
        "Airbase harassment (rocket/mortar siege)",
        36,
        plugin_id="vietnamops",
        settings_fields=("vietnam_airbase_harassment", "artillery_base_harassment"),
    ),
    Feature(
        "vietnam_super_gaggle",
        "Super Gaggle hilltop resupply",
        37,
        plugin_id="vietnamops",
        settings_fields=("vietnam_super_gaggle",),
    ),
    Feature(
        "vietnam_fac_marking",
        "FAC(A) willie-pete target marking",
        38,
        plugin_id="vietnamops",
        settings_fields=("vietnam_fac_marking",),
    ),
    Feature(
        "vietnam_snake_and_nape",
        "Snake and nape (napalm CAS)",
        39,
        plugin_id="vietnamops",
        settings_fields=("vietnam_snake_and_nape",),
    ),
    Feature(
        # Pure engine feature (no Lua): the Tier-0 phase classifier + the HTN soft
        # emphasis + the status surfaces, in game/fourteenth/phases.py.
        "campaign_phases",
        "Campaign phases (inferred arc + planner emphasis)",
        40,
        settings_fields=("campaign_phases",),
    ),
    Feature(
        # Gated by the ModSettings/New Game `high_digit_sams` toggle (a wizard
        # field, not a Settings dataclass field) -- hence no settings_fields.
        "hds_ultimate_compilation",
        "High Digit SAMs Ultimate Compilation support",
        41,
    ),
    Feature(
        # No plugin, no Settings toggle: availability is on-disk content (a
        # tileset under Saved Games/Retribution/MapTiles, sliced by
        # tools/tile_geotiff.py and served by game/server/maptiles).
        "local_map_tiles",
        "Local DCS chart base layers (map tiles)",
        42,
    ),
    Feature(
        # No plugin, no Settings toggle: on-disk content is the switch (a JSON
        # store under Saved Games/Retribution, written from the payload tab by
        # game/fourteenth/flight_defaults.py, applied in Flight.__init__).
        "flight_defaults",
        "Per-aircraft flight defaults (save fuel + properties)",
        43,
    ),
    Feature(
        "long_range_carrier_ops",
        "Long-range carrier ops",
        44,
        settings_fields=("long_range_carrier_ops",),
    ),
    Feature(
        # No plugin, no Settings toggle: always-on like the other F10/ME map
        # drawings (frontlines/routes/CPs/ROE zones). Painted at generation by
        # game/missiongenerator/drawingsgenerator.py from the MissionData support
        # info; a toggle is a possible follow-up.
        "support_orbit_markers",
        "Support-package F10 orbit markers",
        45,
    ),
    Feature(
        "auto_range_fuel_tanks",
        "Route-aware fuel-tank planning (fuel-first)",
        46,
        settings_fields=("auto_range_fuel_tanks", "fuel_tanks_over_jammers"),
    ),
    Feature(
        "continuous_campaign_clock",
        "Continuous campaign clock & weather",
        47,
        settings_fields=("continuous_campaign_clock",),
    ),
    Feature(
        # Pure engine feature (no Lua): couples the will economy to the BLUE war
        # budget in game/fourteenth/commitment_ceiling.py, hooked in
        # Coalition.end_turn. Needs vietnam_political_will as well.
        "vietnam_commitment_ceiling",
        "Commitment ceiling (will-coupled war budget)",
        48,
        settings_fields=("vietnam_commitment_ceiling",),
    ),
    Feature(
        "mobile_missile_relocation",
        "Mobile missile relocation (the SCUD hunt)",
        49,
        plugin_id="mobilemissiles",
        settings_fields=("mobile_missile_relocation", "coastal_missile_relocation"),
    ),
    Feature(
        "convoy_ambush",
        "Convoy ambush (a chance, never telegraphed) + ambient supply convoys",
        50,
        plugin_id="convoyambush",
        settings_fields=("convoy_ambush", "ambient_supply_convoys"),
    ),
    Feature(
        "enemy_comms_jamming",
        "Enemy comms jamming (IADS comms nodes)",
        51,
        plugin_id="commsjam",
        settings_fields=("enemy_comms_jamming", "comms_jam_requires_capture"),
    ),
    Feature(
        # Pure turn-model (no plugin): couples a side's command-network health to
        # its auto-planner unpredictability in game/fourteenth/c2_decapitation.py,
        # read at plan time through targetorder._unpredictability_for.
        "c2_decapitation",
        "Command-center decapitation degrades enemy planning",
        52,
        settings_fields=("c2_decapitation_effects",),
    ),
    Feature(
        # The materiel supply economy (game/fourteenth/war_economy.py): factories/oil
        # produce supply that flows over the transit graph to the front and is consumed
        # there; a starved front recovers less, deploys fewer, and gains less ground
        # (P2), the SITREP shows why (P4a), and fuel depots gate air readiness (P3).
        # Symmetric; coalition_supply_health/supply_factor feed §55 red intent.
        "war_economy",
        "War economy",
        53,
        settings_fields=("war_economy", "fuel_air_readiness"),
    ),
    Feature(
        # The air axis: a per-base scarce-munitions stock (curated taxonomy in
        # game/data/weapons.py) debited by what the ATO loads and supply-coupled on
        # rearm; the loadout gate (Loadout.degrade_for_stock + the payload-editor
        # grey-out) swaps a store the base is out of down to a stocked fallback.
        "munitions_availability",
        "Munitions availability",
        54,
        settings_fields=("restrict_weapons_by_stock",),
    ),
    Feature(
        # Pure engine feature (no Lua): a per-turn RED posture (consolidate/attrition/
        # surge) in game/fourteenth/red_intent.py that biases the offensive HTN
        # ordering, the target-shuffle unpredictability, the offensive-commit roll, and
        # the ground-stance thresholds. Red-only; observe-only until enabled. §53/§54
        # are the sibling war-economy pair (a separate branch); the §53 supply coupling
        # (P4) is a read-only drop-in.
        "red_intent",
        "Red Intent — adaptive enemy posture",
        55,
        settings_fields=("red_intent",),
    ),
    Feature(
        # Adopted from upstream PR dcs-retribution#859 (geofffranks). No plugin,
        # no Lua: a control point's not-deployed reserve armor is rendered as a
        # strikeable depot by MotorpoolPopulator + MotorpoolGenerator at mission
        # generation; each kill decrements base.armor 1:1
        # (game/sim/missionresultsprocessor.py commit_motorpool_losses), tracked
        # separately from front-line losses so a depot strike never shifts the
        # front. Inert until a campaign authors a Fortification.Garage_A depot.
        "motorpool_depots",
        "Strikeable motorpool depots",
        56,
        settings_fields=("motorpool_enabled", "motorpool_spawn_cap"),
    ),
    Feature(
        # §57 air-droppable minefields. Same-turn tactical mining is the `minefields`
        # Lua plugin (detect a blue CBU-99 drop -> scripted proximity field -> detonate
        # real convoy units, recorded natively); air_droppable_minefields adds cross-turn
        # persistence (game/fourteenth/minefields.py reconciles the minefields_state
        # debrief channel; minefieldluadata re-arms the survivors next mission). Blue-only.
        "air_droppable_minefields",
        "Air-droppable minefields",
        57,
        plugin_id="minefields",
        settings_fields=("air_droppable_minefields", "auto_plan_minefields"),
    ),
    Feature(
        # §58 mission-start briefing popup. Pure display: briefingluadata emits a
        # shared header (campaign/mission/date/time) + one record per player-crewed
        # flight (callsign/aircraft/task/field); the `briefing` plugin shows each
        # pilot their own card on S_EVENT_BIRTH (slot-in). No gameplay-model change.
        "mission_briefing_popup",
        "Mission-start briefing popup",
        58,
        plugin_id="briefing",
        settings_fields=("mission_briefing_popup",),
    ),
    Feature(
        # §59 ground AI sleep -- the graduated alternative to binary culling.
        # aisleepluadata.py emits a positive list of rear-area garrison ("armor")
        # vehicle groups (never air defense / missiles / ships / the concealed
        # scripted movers); the `aisleep` plugin sleeps each group's controller
        # (setOnOff false) while no aircraft is inside the wake radius and wakes
        # it on approach or on a hit. Performance only -- units keep existing,
        # kills record natively, no gameplay-model change.
        "ground_ai_sleep",
        "Ground AI sleep (graduated culling)",
        59,
        plugin_id="aisleep",
        settings_fields=("perf_ground_ai_sleep",),
    ),
    Feature(
        # §60 SAM guidance-radar redundancy -- every SAM site layout fields TWO
        # engagement radars (track radar / combined STR) so a single HARM cannot
        # blind the whole site (Red Tide finding 2026-07-12). Pure layout data:
        # unit_count 2 in resources/layouts/anti_air/*.yaml + a second radar
        # position in the shared .miz templates. No setting, no plugin -- the
        # contract is CI-locked in tests/armedforces/test_sam_radar_redundancy.py.
        "sam_radar_redundancy",
        "SAM guidance-radar redundancy (two track radars per site)",
        60,
    ),
    Feature(
        # §61 host red-interceptor scramble -- the game master's "give the boys
        # something to shoot" button (the M1 "it felt quiet after the first wave"
        # debrief). redscrambleluadata.py emits cold late-activation red fighter
        # clone templates (the QRA pattern, built in
        # AircraftGenerator.spawn_red_scramble_templates) + the red airfields
        # nearest-front first; the `redscramble` plugin builds a host-only F10
        # menu (per-player-name, or all-BLUE when unconfigured) that SPAWN-clones
        # a 2/4-ship at any listed base and GCI-vectors it onto the nearest
        # airborne blue fighters. Spawns are untracked event content by design
        # (the §20 drop-spawn cheat precedent).
        "host_red_scramble",
        "Host red-interceptor scramble (F10 bandit spawner)",
        61,
        plugin_id="redscramble",
        settings_fields=("host_red_scramble",),
    ),
    Feature(
        # pydcs deals random three-digit board numbers (an unordered set.pop);
        # ModexAllocator (game/missiongenerator/aircraft/modex.py) gives each
        # Hornet/Tomcat squadron a 100/200/300 block (Tomcats first, the CVW
        # convention) and numbers its jets sequentially X00, X01, ... in
        # generation order. Pure generation behavior — no setting, no plugin.
        "squadron_modex",
        "Squadron-sequenced Hornet/Tomcat board numbers",
        62,
    ),
    Feature(
        # §63 ship-launched cruise missile raids: LACM warships (the Burke's
        # Tomahawks, the CurrentHill Kalibr hulls -- the curated LACM_SHIP_DCS_IDS
        # set) strike shore targets via a FireAtPoint task with the cruise-missile
        # weapon flag. game/fourteenth/cruise_raids.py owns the persisted per-group
        # magazines (debited only from the plugin's cruise_missiles_state debrief
        # report) + the one-raid-per-side-per-turn auto planner (C2-first target
        # pick, ROE-gated for BLUE); cruisemissileluadata.py emits ships + raids;
        # the `cruisemissiles` plugin fires the raids after a delay and serves the
        # per-coalition F10 call-for-fire menu. Real weapons from tracked ships --
        # kills record natively, point defense intercepts, no phantom spawns.
        "cruise_missile_raids",
        "Ship-launched cruise missile raids",
        63,
        plugin_id="cruisemissiles",
        settings_fields=("cruise_missile_strikes", "cruise_missile_auto_raids"),
    ),
    Feature(
        # §64 carrier deck spawn policy + MP slot timing: DCS's only deck-parking
        # lever is spawn timing -- the mission-start wave fills the six-pack (the
        # taxi lane to the bow catapults) first, and a group activated even one
        # second later is placed elsewhere on deck (dcs_liberation#1309). The
        # CarrierDeckPolicy enum (replacing the player_flights_sixpack boolean,
        # save-migrated) defaults to LAST_RESORT: player carrier flights take the
        # same one-second placement activation AI always take, so nobody with a
        # ten-minute cold start parks in the AI taxi flow and the six-pack only
        # fills as overflow once the rest of the deck is full. TOT-delayed client
        # carrier flights also stop being late-activated for their full delay
        # (which removed their slots from the MP slot list until the push time):
        # they spawn uncontrolled like their airfield counterparts, with the
        # StartCommand holding only the AI members to the planned push.
        # waypointgenerator.set_takeoff_time / needs_deck_placement_delay.
        "carrier_deck_policy",
        "Carrier deck spawn policy (six-pack last resort + MP slot timing)",
        64,
        settings_fields=("carrier_deck_policy",),
    ),
    Feature(
        # §65 curated carrier comms: DCS auto-renders a "CV Operations Data"
        # kneeboard page straight from the miz, and the generator used to feed
        # it allocator junk (TACAN 1X + a random ident re-rolled every turn,
        # Link 4 on a random UHF, a fresh random ATC each mission, the boat
        # named "0796 | ..."). game/data/carrier_comms.py curates a per-hull
        # boat card (hull-number TACAN + boat ident, hull-keyed ICLS, Link 4
        # in the ACLS 336 MHz band, a stable ATC) applied with
        # stored-values-win / taken-channel-degrades-to-neighbor precedence in
        # GenericCarrierGenerator, which also names the flagship unit by its
        # hull name and persists every value so the card is stable across
        # turns. Pure generation behavior -- no setting, no plugin.
        "carrier_comms",
        "Curated carrier comms (CV Operations Data cleanup)",
        65,
    ),
    Feature(
        # §66 generated-mission archive: every turn generates to the one fixed
        # path retribution_nextturn.miz (the name the wiki/bug template/server
        # workflow all use), so each Take off overwrote the mission just flown --
        # and this fork root-causes its in-game findings from the flown miz.
        # game/fourteenth/mission_archive.py leaves that output alone and also
        # copies each generation to Missions/Retribution Archive/ under a
        # campaign_turnNN_stamp name (a folder DCS's mission browser lists).
        # Best-effort (never breaks Take off) and prunes only its own output.
        # Hooked in MissionSimulation.generate_miz. No setting -- a bounded ring
        # buffer, and a toggle would defeat the point (§42/§43 precedent).
        "mission_archive",
        "Generated-mission archive",
        66,
    ),
    Feature(
        # §67 weather-aware planning: the theater commander reads game.conditions
        # (game/fourteenth/weather_planning.py). Rain/storm suppresses the
        # automatic TARPS/drone recon add-on (PackageFulfiller); a thunderstorm
        # demotes the low-level visual-attack HTN methods (front-line CAS,
        # battle-position BAI, convoy interdiction) to the offensive tail
        # (PlanNextAction._offensive_order). Both coalitions -- same sky; clear
        # weather is byte-identical. Night is deliberately out: no per-airframe
        # night-capability data exists to gate on.
        "weather_aware_planning",
        "Weather-aware auto-planning",
        67,
        settings_fields=("weather_aware_planning",),
    ),
    Feature(
        # §68 adaptive procurement (game/fourteenth/adaptive_procurement.py):
        # the AI economy reads the war. The auto-spend ground share shifts with
        # the side's strategic read (§55 red posture / §40 blue phase), ground
        # buys are price-weighted instead of uniform random, and -- its own
        # gate -- each side's commander repairs a couple of destroyed SAM/EWR
        # units per turn at surviving sites (full price, degraded sites and
        # radars first; C2/comms stay permanently dead), so a rolled-back IADS
        # stops being a one-way ratchet.
        "adaptive_procurement",
        "Adaptive procurement (posture-coupled spending + SAM repair)",
        68,
        settings_fields=("adaptive_procurement", "auto_repair_air_defenses"),
    ),
    Feature(
        # §69 cross-package coordination (MissionScheduler._coordinate_sead_windows):
        # packages were timed independently, so a strike could arrive at a
        # defended target long before the SEAD tasked against the SAM covering
        # it. Movable AI strike/BAI/OCA packages whose target sits inside a
        # threat ring a SEAD/DEAD package is servicing are retimed into the
        # window just behind the latest covering suppressor -- SEAD opens, the
        # strikes push, several packages massing behind one window. Player
        # packages never move (a player SEAD still opens a window); the §8
        # carrier stagger runs after and only delays.
        "sead_strike_coordination",
        "Cross-package SEAD-before-strike coordination",
        69,
        settings_fields=("sead_strike_coordination",),
    ),
    Feature(
        "comint_collection",
        "COMINT collection (blue-side communications intelligence)",
        70,
        plugin_id="rednet",
        settings_fields=("comint_collection", "red_comms_net"),
    ),
    # Always-on engine plugins — major 414th machinery documented in design notes
    # rather than a numbered "Features at a Glance" entry.
    Feature("mantis_iads", "MANTIS IADS engine", plugin_id="mantisiads"),
    Feature("splash_damage", "Splash Damage (414th tuned)", plugin_id="splashdamage3"),
    Feature("ai_recon_capture", "AI recon BDA capture (§3 TARPS)", plugin_id="airecon"),
)

# Path (relative to repo root) of the generated feature-catalog doc.
FEATURE_INDEX_DOC = "docs/dev/414th-feature-index.md"


def _sorted_features() -> list[Feature]:
    """Numbered features by section ascending, then the unnumbered engines."""
    return sorted(
        FEATURES,
        key=lambda f: (f.doc_section is None, f.doc_section or 0),
    )


def render_feature_index() -> str:
    """Render :data:`FEATURES` to the Markdown catalog (a stable string)."""
    lines = [
        "# 414th Feature Index",
        "",
        "> **Generated** from `game/fourteenth/features.py` — do not edit by hand.",
        "> Regenerate with `python -m game.fourteenth.features`; CI fails if stale.",
        "",
        'Every numbered feature in the CLAUDE.md "Features at a Glance" list (§N in',
        "[`414th-features.md`](414th-features.md)) is registered here, plus the",
        "always-on engine plugins. The wiring columns show the Lua plugin and",
        "`Settings` fields that run/gate each feature. A test (`tests/fourteenth/`)",
        "fails CI if a reference is stale, a numbered feature is missing, an in-game-",
        "pass checklist `§N` is unregistered, or this table drifts.",
        "",
        "| § | Feature | Plugin | Settings |",
        "| --- | --- | --- | --- |",
    ]
    for feature in _sorted_features():
        section = f"§{feature.doc_section}" if feature.doc_section is not None else "—"
        title = feature.title + (" _(retired)_" if feature.retired else "")
        plugin = f"`{feature.plugin_id}`" if feature.plugin_id else "—"
        if feature.settings_fields:
            settings = ", ".join(f"`{name}`" for name in feature.settings_fields)
        else:
            settings = "—"
        lines.append(f"| {section} | {title} | {plugin} | {settings} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    from pathlib import Path

    out = Path(FEATURE_INDEX_DOC)
    out.write_text(render_feature_index(), encoding="utf-8", newline="\n")
    print(f"wrote {out}")
