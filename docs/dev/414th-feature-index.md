# 414th Feature Wiring Map

> **Generated** from `game/fourteenth/features.py` — do not edit by hand.
> Regenerate with `python -m game.fourteenth.features`; CI fails if stale.

Every 414th feature with concrete wiring (a Lua plugin and/or a `Settings`
field) is registered in `FEATURES`. A test asserts each reference below
resolves, so a renamed setting or removed plugin fails CI instead of
silently rotting this map.

| Feature | Features doc | Plugin | Settings |
| --- | --- | --- | --- |
| QRA intercept reserve | §1 | `intercept` | — |
| C-130J EW/ISR (JAMMING) | §2 | `c130j` | — |
| Troops In Contact | §9 | `tic` | — |
| TARS recon engine | §12 | `tars` | — |
| SCAR — Sandy rescue escort | §15 | `scar` | `scar_command_post_intel` |
| Auto-planner target unpredictability | §17 | — | `ownfor_planner_unpredictability`, `opfor_planner_unpredictability` |
| Drop-spawn unit placement | §20 | — | `enable_unit_placement`, `enable_free_unit_placement` |
| Combat SAR | §21 | `combatsar` | `auto_combat_sar` |
| Date-gated aircraft properties | §24 | — | `restrict_weapons_by_date` |
| Compact kneeboard deck | §25 | — | `compact_kneeboard` |
| Campaign SITREP kneeboard | §29 | — | `generate_sitrep_kneeboard` |
| MANTIS IADS engine | — | `mantisiads` | — |
| Splash Damage (414th tuned) | — | `splashdamage3` | — |
