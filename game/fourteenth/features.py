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
        settings_fields=("auto_combat_sar",),
    ),
    Feature(
        "kneeboard_custom_import", "Kneeboard space-utilisation + custom import", 22
    ),
    Feature("per_squadron_country", "Per-squadron DCS country", 23),
    Feature(
        "date_gated_aircraft_properties",
        "Date-gated aircraft properties",
        24,
        settings_fields=("restrict_weapons_by_date",),
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
    Feature("kneeboard_cover_page", "Dedicated kneeboard cover page", 30),
    Feature(
        "brief_sheet_kneeboard",
        "One-page Brief Sheet + deck-wide colour scheme",
        31,
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
        "Route-aware fuel-tank top-up",
        46,
        settings_fields=("auto_range_fuel_tanks",),
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
