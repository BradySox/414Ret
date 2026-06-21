# Settings quality-of-life audit

This is the implementation handoff for the settings UI pass. The underlying settings
model and every active plugin setting were audited on 2026-06-18; this document keeps
UI decisions separate from save-format and mission-generation behavior.

## Audit result

- Core campaign settings inspected: **154** metadata-backed fields.
- Active mission plugins inspected: **14** plugin definitions from
  `resources/plugins/plugins.json`.
- Every core field was traced to its Python consumers. Two visible fields had no
  consumer at all, one hidden legacy field was still serialized, and one DCS parking
  workaround was permanently forced off during save migration.
- Plugin mnemonics and defaults remain unchanged. Splash Damage remains locked exactly
  as required by `CLAUDE.md`.

## Removed or consolidated

| Old setting | Result | Compatibility |
|---|---|---|
| `prefer_squadrons_with_matching_primary_task` | Removed. It had no consumer; `primary_task_distance_factor` is the live control for the same planner preference. | Old values are discarded on load. |
| `pretense_num_of_cargo_planes` | Removed. It was a duplicate, unused field; `pretense_ai_cargo_planes_per_side` is the live Pretense generator control. | Old values are discarded on load. |
| `nevatim_parking_fix` | Removed with its Nevatim/Ramon restricted-slot code. New games defaulted it off and `Migrator` forcibly disabled it on loaded games. | Old values are discarded on load. |
| `only_player_takeoff` | Removed. It was an undocumented, unused legacy serialization field. | Old values are discarded on load. |
| `limit_ai_radios` + `silence_ai_radios` | Replaced by `ai_radio_behavior`: Normal callouts, Suppress contact reports, or Radio silence. | Old boolean combinations migrate deterministically. |

No other setting was deleted merely because it was old, experimental, or narrowly
used. A low reference count is normal for generator switches.

## Recommended UI taxonomy

The existing page names can remain, but the large General and Gameplay sections should
be broken into these smaller concepts. This is display-only guidance; field keys should
not change.

### Difficulty

- Coalition AI: player coalition skill, enemy coalition skill, enemy vehicle/AA skill.
- Economy pressure: player and enemy income multipliers.
- Mission environment: MANPADS and day/night generation.
- DCS enforced options: labels, map visibility, external views, easy communications,
  and DCS battle-damage assessment.

### Campaign Doctrine

- Air defense: BARCAP duration/overlap, QRA reserves/radii/callouts, airbase threat
  range, patrol altitude floor, and altitude scatter.
- Support aircraft: AWACS/tanker duration, recovery tanker ratio, and support-flight
  threat buffers.
- Package composition: task-specific tanker automation and TARPS follow-up.
- Intelligence: recon intel fog and experimental SCAR command-post intelligence.
- Planner behavior: OCA threshold, OWNFOR/OPFOR aggressiveness, mission ranges, and
  primary-task distance weight.
- Aircraft behavior: helicopter altitudes, ATFLIR swap, AI tank jettison, vertical
  takeoff/landing, startup allowance, and AI radio behavior.
- Engagement geometry: CAS, armed-recon, SEAD sweep, SEAD loiter, TARCAP, AEW&C, and
  tanker distances.

### Campaign Management

- Campaign generation: generated-squadron variety, date-restricted weapons, target
  weapon overrides, and Bandit cloud presets.
- Squadron limits: pilot leveling, pilot cap/replenishment, and aircraft limits.
- OWNFOR automation: runway repair, reinforcement, aircraft purchase, package planning,
  support planning, ASAP player scheduling, and stance management.
- Procurement: OWNFOR and OPFOR ground budget/reserve controls.
- Formation planning: 2/3/4-ship weights and primary-task distance weight.

### Mission Generator

- Mission flow: fast-forward stop condition, fast-forward combat handling, and desired
  mission duration.
- Modules and mission data: Supercarrier, deck crew, portable TACAN, EPLRS, DTC,
  kneeboard theme, map marks, target precision, and weather fog.
- Player and controller access: start type, immediate player spawn, OPFOR client slots,
  dynamic slots/cargo, sixpack use, and Game Master/Tactical Commander/JTAC/Observer
  counts.
- AI behavior: AI start type, unlimited fuel, combat landing, and radio behavior.
- Ground starts: AI roadbase use, scenery removal, truck/FARP choices, and ground-power
  support.
- Front line and ambient activity: width, smoke, artillery, missile fire, moving units,
  infantry, road preference, and deployed-unit cap.
- Logistics traffic: convoy generation/travel, shipping convoys, and destroyed-unit
  carcasses.
- Performance culling: master culling switch, distance, IADS/carrier exclusions, idle
  aircraft, and airstarted-AI despawn.
- Legacy workaround: helicopter AMSL-over-water waypoint conversion. Keep this advanced
  until the DCS behavior is revalidated in-game.

## Dependency rules for the UI layer

These controls remain persisted independently, but their editors should be disabled or
visually nested when the parent feature is off:

- `enable_squadron_pilot_limits` → `squadron_pilot_limit`,
  `squadron_replenishment_rate`.
- `fast_forward_stop_condition != DISABLED` → `combat_resolution_method`.
- `supercarrier` → `supercarrier_deck_crew`.
- `dynamic_slots` → `dynamic_slots_hot`.
- `perf_smoke_gen` → `perf_smoke_spacing`.
- `not perf_disable_convoys` → `convoys_travel_full_distance`.
- `perf_culling` → `perf_culling_distance`,
  `perf_do_not_cull_threatening_iads`, `perf_do_not_cull_carrier`.
- Plugin enabled → all of that plugin's specific options.
- TARS `scoring` → `scoreValue`; TARS `srs` → `srsPort`.
- Airboss `enableRescueHelo` → rescue distance/duration/zone/mod options.
- Skynet `actMobile` and `actMobile_merad` → their respective movement tunables.
- Skynet `adjustGoLiveRange` → per-SAM go-live percentages.

## Settings that need explicit warning treatment

These are live settings, not deletion candidates:

- `restrict_weapons_by_date`: incomplete weapon-date data.
- `combat_resolution_method = RESOLVE`: intentionally rudimentary and loss-heavy.
- `scar_command_post_intel`: experimental, default off.
- `dynamic_slots`: dynamic-slot losses are not registered.
- `untasked_opfor_client_slots` and non-cold AI starts: reduce OCA/Aircraft targets.
- `switch_baro_fix`: DCS helicopter-over-water workaround.
- Dismounts plugin: performance-heavy.
- Debug plugin options: advanced troubleshooting only.

## Plugin wording cleanup

The obsolete Anubis C-130 Hercules mod and its `herculescargo` cargo plugin were removed
in favor of the official DCS `C-130J-30`, so the only remaining C-130J entry is the 414th
EW/ISR mission system (`c130j` plugin). Splash Damage now explicitly says its squadron
tuning is locked. The hidden QRA runtime plugin now explains that its user-facing controls
live under Campaign Doctrine.

