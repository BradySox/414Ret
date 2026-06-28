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
| §3 | TARPS recon + BDA fog-of-war | — | — |
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
| §21 | Combat SAR | `combatsar` | `auto_combat_sar` |
| §22 | Kneeboard space-utilisation + custom import | — | — |
| §23 | Per-squadron DCS country | — | — |
| §24 | Date-gated aircraft properties | — | `restrict_weapons_by_date` |
| §25 | Compact 3-4 page kneeboard deck | — | `compact_kneeboard` |
| §26 | Off-mission combat fidelity + PLAYER_AT_IP fix | — | — |
| §27 | Shared-airframe kneeboard index | — | — |
| §28 | Settings IA reorg + difficulty presets | — | — |
| §29 | Campaign SITREP kneeboard band | — | `generate_sitrep_kneeboard` |
| §30 | Dedicated kneeboard cover page | — | — |
| §31 | One-page Brief Sheet + deck-wide colour scheme | — | `compact_kneeboard` |
| — | MANTIS IADS engine | `mantisiads` | — |
| — | Splash Damage (414th tuned) | `splashdamage3` | — |
