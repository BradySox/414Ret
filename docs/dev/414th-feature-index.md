# 414th Feature Index

> **Generated** from `game/fourteenth/features.py` — do not edit by hand.
> Regenerate with `python -m game.fourteenth.features`; CI fails if stale.

Every numbered feature in the CLAUDE.md "Features at a Glance" list (§N in
[`414th-features.md`](414th-features.md)) is registered here, plus the
always-on engine plugins. The wiring columns show the Lua plugin and
`Settings` fields that run/gate each feature. A test (`tests/fourteenth/`)
fails CI if a reference is stale, a numbered feature is missing, an in-game-
pass checklist `§N` is unregistered, or this table drifts.

| § | Feature | Plugin | Settings |
| --- | --- | --- | --- |
| §1 | QRA intercept reserve | `intercept` | — |
| §2 | JAMMING flight type | `c130j` | — |
| §3 | TARPS recon + BDA fog-of-war | — | `recon_intel_fog`, `concealed_enemy_forces` |
| §4 | UI transparency | — | — |
| §5 | Player target location precision | — | — |
| §6 | Air-defense planning rework | — | — |
| §7 | Auto-hide mobile SAMs on MFD | — | — |
| §8 | Robustness / crash fixes | — | — |
| §9 | TIC — Troops In Contact | `tic` | — |
| §10 | CurrentHill Iran assets pack | — | — |
| §11 | Native DCS DTC cartridge export _(retired)_ | — | — |
| §12 | TARS recon engine | `tars` | — |
| §13 | Flight Control ATC _(retired)_ | — | — |
| §14 | Plugin Options UI | — | — |
| §15 | SCAR — RESCAP "Sandy" rescue escort | `combatsar` | `scar_command_post_intel` |
| §16 | Settings QOL audit | — | — |
| §17 | Auto-planner target unpredictability | — | `ownfor_planner_unpredictability`, `opfor_planner_unpredictability` |
| §18 | Fog-of-war overview toggle | — | — |
| §19 | Unified map layers panel | — | — |
| §20 | Drop-spawn: map right-click unit placement | — | `enable_unit_placement`, `enable_free_unit_placement` |
| §21 | Combat SAR | `combatsar` | `auto_combat_sar`, `combat_sar_persistent_pilots` |
| §22 | Kneeboard space-utilisation + custom import | — | — |
| §23 | Per-squadron DCS country | — | — |
| §24 | Date-gated aircraft properties | — | `restrict_weapons_by_date` |
| §25 | Compact 3-4 page kneeboard deck _(retired)_ | — | — |
| §26 | Off-mission combat fidelity + PLAYER_AT_IP fix | — | — |
| §27 | Shared-airframe kneeboard index | — | — |
| §28 | Settings IA reorg + difficulty presets | — | — |
| §29 | Campaign SITREP kneeboard band | — | `generate_sitrep_kneeboard` |
| §30 | Dedicated kneeboard cover page | — | — |
| §31 | One-page Brief Sheet + deck-wide colour scheme | — | — |
| §32 | Arc Light heavy-bomber Strike carpet | `vietnamops` | `vietnam_arc_light` |
| §33 | AAA flak gauntlet | `vietnamops` | `vietnam_flak_gauntlet` |
| §34 | Naval gunfire support | `vietnamops` | `vietnam_naval_gunfire` |
| §35 | Convoy interdiction (Steel Tiger) | — | `vietnam_convoy_interdiction` |
| §36 | Airbase harassment (rocket/mortar siege) | `vietnamops` | `vietnam_airbase_harassment`, `artillery_base_harassment` |
| §37 | Super Gaggle hilltop resupply | `vietnamops` | `vietnam_super_gaggle` |
| §38 | FAC(A) willie-pete target marking | `vietnamops` | `vietnam_fac_marking` |
| §39 | Snake and nape (napalm CAS) | `vietnamops` | `vietnam_snake_and_nape` |
| §40 | Campaign phases (inferred arc + planner emphasis) | — | `campaign_phases` |
| §41 | High Digit SAMs Ultimate Compilation support | — | — |
| §42 | Local DCS chart base layers (map tiles) | — | — |
| §43 | Per-aircraft flight defaults (save fuel + properties) | — | — |
| §44 | Long-range carrier ops | — | `long_range_carrier_ops` |
| §45 | Support-package F10 orbit markers | — | — |
| §46 | Route-aware fuel-tank top-up | — | `auto_range_fuel_tanks` |
| §47 | Continuous campaign clock & weather | — | `continuous_campaign_clock` |
| §48 | Commitment ceiling (will-coupled war budget) | — | `vietnam_commitment_ceiling` |
| §49 | Mobile missile relocation (the SCUD hunt) | `mobilemissiles` | `mobile_missile_relocation`, `coastal_missile_relocation` |
| §50 | Convoy ambush (a chance, never telegraphed) + ambient supply convoys | `convoyambush` | `convoy_ambush`, `ambient_supply_convoys` |
| §51 | Enemy comms jamming (IADS comms nodes) | `commsjam` | `enemy_comms_jamming`, `comms_jam_requires_capture` |
| §52 | Command-center decapitation degrades enemy planning | — | `c2_decapitation_effects` |
| §53 | War economy | — | `war_economy`, `fuel_air_readiness` |
| §54 | Munitions availability | — | `restrict_weapons_by_stock` |
| §55 | Red Intent — adaptive enemy posture | — | `red_intent` |
| §56 | Strikeable motorpool depots | — | `motorpool_enabled`, `motorpool_spawn_cap` |
| §57 | Air-droppable minefields | `minefields` | `air_droppable_minefields`, `auto_plan_minefields` |
| §58 | Mission-start briefing popup | `briefing` | `mission_briefing_popup` |
| §59 | Ground AI sleep (graduated culling) | `aisleep` | `perf_ground_ai_sleep` |
| §60 | SAM guidance-radar redundancy (two track radars per site) | — | — |
| §61 | Host red-interceptor scramble (F10 bandit spawner) | `redscramble` | `host_red_scramble` |
| — | MANTIS IADS engine | `mantisiads` | — |
| — | Splash Damage (414th tuned) | `splashdamage3` | — |
| — | AI recon BDA capture (§3 TARPS) | `airecon` | — |
