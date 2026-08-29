# Reading `dcs.log` — what is ours and what is not

First written 2026-08-29 from a 7-minute Afghanistan turn (DCS 2.9.29.27278). Purpose:
stop the same lines being re-investigated every time someone opens the log.

`dcs.log` collapses repeats. A written line count understates the truth — recover the
real volume by attributing each `WARNING LOG (N): X duplicate message(s) skipped.` to the
distinct message immediately above it. In the reference session, 7,569 written lines hid
7,863 further copies.

## Not ours — do not investigate again without new evidence

| Line | Source | Evidence |
|---|---|---|
| `ERROR FLIGHT: INVALID ATC <name>` | ED terrain data | Fires during terrain init, **before** `MissionSpawn:initScript`, for helipads that are not in our `.miz` at all. Afghanistan names FOB Thunder / Camp Dubs / Clark; Syria names HC01–HC06, HI01–HI06, Gulechoba, Nicosia; Germany Cold War names H FRG 01–10. Present in every archived log across three maps (Syria alone throws 144–724 per session). |
| `WARNING FLIGHT: NO ATC COMM HELIPAD + <name>:127500000` | DCS ATC, every map | Fires ~4 s after the player spawns, once per helipad in the mission, on Syria and Germany Cold War as well as Afghanistan. 127.5 MHz is **pydcs's `BaseFARP` default** — `control_point.frequency` is only ever populated for carriers (`tgogenerator._resolve_atc`), so every generated FOB pad ships the default. Since ED's own map-native helipads throw ATC errors too, there is no evidence the frequency is what DCS objects to. Assigning FOB frequencies is a defensible change on its own merits; **do not sell it as a fix for this warning** without an in-game before/after. |
| `ERROR wInfo: negative weight/drag of payload "..."` | Mod and ED payload files | 287 in the reference session. Origins include ED's own `CoreMods/aircraft/A-6E`, `MiG-21bis`, `AV8BNA`, `OH-58D`, `F-4E`, `F14`, plus the CJS Super Hornet mod (152 of them). Load-time only. |
| `ERROR Scripting: plugin: <pack> unit replace <id> not allowed` | CurrentHill packs vs base DCS | ED integrated the Currenthill units into `CoreMods/tech/Currenthill Assets Pack`; the standalone packs lose the race for those ids. Known since the 2026-07-20 CH wave. |
| `ERROR APP: Unit [X]: Corrupt damage model` / `ERROR WORLDGENERAL: No property record for segment` | ED unit models | Su-25T, Su-24M, Mi-8MT, JF-17. |
| `ERROR ED_SOUND: source_add(...): can't find proto` | ED / mod sound banks | 100 in the reference session, mostly Mi-24P cockpit. |
| `ERROR woCar: can't load destroyed model 'Ural-375_p_1' for '55G6 EWR'` | ED unit data | Cosmetic: the 55G6 leaves no wreck. We field the unit but do not own the model. |
| `UNKNOWN UnitsLayer:: m_obj2ctl.find(obj) != m_obj2ctl.end()` | DCS internal | Once per player module load. |
| `WARNING APP: task "<X>" still exists` | Mission unload | 128 in the reference session, all after the mission ends. |
| `ERROR EDCORE: Failed to load ...SouthAtlantic.dll: (127)` | DCS install | South Atlantic assets unavailable. Not mission-dependent. |
| `[VWV] A-37`: `attempt to index global 'LockOn_Options'`, `unit a37_dragonfly not found` | VWV A-37 mod on 2.9.29 | Load-time. Matters only if a Vietnam campaign fields the A-37. |

## Ours — the lines worth reading

| Line | Owner | Status |
|---|---|---|
| `EVENT00000.onEvent((WARNING: Could not get EVENTMETA data for event ID=61 ...))` | vendored `Moose.lua` | **Fixed 2026-08-29.** 6,807 occurrences in the reference session (11,861 in an archived Germany Cold War log). See `414th-framework-consolidation-notes.md`, *Local patches to the vendored `Moose.lua`*. |
| `OnBeforeArrived: unit is stuck; retrying move without roads` | §9 TIC | **Open.** 846 in 7 minutes, correlated with the ANTIFREEZE cluster. Diagnostic added 2026-08-29 (name + per-unit count); behaviour unchanged pending a re-fly. See `414th-tic-dynamic-fronts-notes.md`. |
| `ERROR EDCORE: Can't open file '...UnitPayloads//_retribution_backups'` | §73 | **Fixed 2026-08-29** — the backup store moved to `Retribution/PayloadBackups`. |
| `DCSRetribution\|MANTIS-IADS plugin - ... resolved N/N SAM` | MANTIS | Health check, not an error. A non-zero *name match failed* count means those SAMs run vanilla with no EMCON. |
| `WARNING WORLD: ModelTimeQuantizer: ANTIFREEZE ENABLED` | DCS, but load-driven | Frame the sim could not deliver on time. Cluster it against the scripting stream — that is how the TIC correlation above was found. |

## Method

1. Split startup from in-mission at the `Dispatcher (Main): loadMission` line. Startup
   errors are almost entirely mod/DB load and almost never ours.
2. Bucket `ERROR`/`WARNING` by subsystem before reading any individual line.
3. Attribute the collapsed duplicates before ranking anything by volume.
4. Compare against the archived logs in the flown-test capture folders before calling a
   line map-specific or campaign-specific — that is what settled the ATC rows above.
