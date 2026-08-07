# Settings, Plugins, Performance, Advanced Config (distilled from wiki)

Exact option lists shift between releases — for the current full list of a settings page, clone the live wiki (see SKILL.md) or open the page. This file holds the stable structure, key defaults, and the non-obvious behaviors.

## Settings map (gear icon, per loaded campaign, immediate effect)

| Category | Governs | Highlights |
|---|---|---|
| Difficulty | AI skill, economy, restrictions | All AI skills default High; income multipliers 1.0 (0–5); "player pilots cannot be killed" ON (airframe still lost); labels/F10-map/external-view enforcement |
| Campaign Management | Squadrons, pilots, HQ automation, flight planner | Pilot cap 16, replenish 4/turn; all HQ automations default OFF except AWACS planning, ASAP-for-player-packages, and auto stance management (ON); flight-size weights WF2/3/4 = 50/35/15; primary-task distance weight 75 NM |
| Campaign Doctrine | Auto-planner doctrine, distances | BARCAP/tanker on-station 1h, AWACS 2h (station time ÷ mission duration = sortie count); auto-tankers for Strike/OCA/DEAD ON; aggressiveness 20% both sides (% of threat radius the planner ignores); helo combat/cruise alt 200/500 AGL; **Player startup time 10 min**; doctrine distances incl. max mission range 150 NM planes / 100 NM helos, CAS engagement 10 NM, SEAD Sweep 30 NM |
| Mission Generator | Per-mission build | Fast forward, supercarrier, start types, laser code, mission duration, frontline width, GM/JTAC/observer slots, dynamic slots/cargo, plus the whole Performance section |
| Pretense | Pretense-mode campaigns | Separate mode; motorpools unsupported there |
| LUA Plugins / Plugin Options | Script injection | See below |
| Cheat Menu | Sandbox/testing | Frontline drag, base capture, runway state, instant transfer, air wing adjustments, OPFOR buy/sell, ±money buttons — legitimate tools for campaign TESTING |

Settings can be exported/imported as .zip; a `Default.zip` in the settings directory seeds every new campaign — save your house defaults there. Any setting can also be suggested per-campaign via the campaign YAML `settings:` block.

**"Restrict weapons by date" (WIP)**: keys off the YEAR of the New Game "Time Period" (the season part only sets map textures). Coverage is incomplete. For era-accurate loadouts (no AMRAAMs in Desert Storm etc.) don't rely on it alone — use faction `weapons_introduction_year_overrides` and curated loadouts.

## Plugins (defaults)

ON by default: **base** (mandatory), **CTLD** (needed for Air Assault/airlift zones), **Skynet IADS**. Everything else OFF: Moose Autolase / MarkerOps / Soundhandler / Airboss, Arty Spotter, Mbot Call Artillery, BigEye EWR, EWRS, DCS Dismounts (FPS-killer), EW Jammer 2.0, C-130 cargo (Anubis mod), LotATC Export, Splash Damage.

Skynet trade-off (upstream's own framing): fixes DCS SAM crudeness (networked tracks, radar discipline vs HARMs, engagement logic, performance) but is a large-MP coordination challenge that degrades AI SEAD. Solo/small group → consider turning it off despite the default.

> **414th deltas — this section is upstream's and is materially out of date for the fork:**
> - **Skynet is REMOVED.** MANTIS is the sole IADS engine; there is no engine selector.
> - **MIST is retired** behind a 51-symbol compat shim. Grep merged upstream Lua for `mist.`
>   — a missing symbol dies at runtime, not in CI.
> - The fork ships **~30 plugins**, most of them its own, each gated by a matching setting.
>   **An unticked plugin silently kills its setting** — campaigns must preseed both.
> - `ewrj`, Flight Control ATC and DCS Dismounts are **retired**; Splash Damage is a locked,
>   buddy-tuned build with its config layer deliberately removed.
> - The **settings surface was reorganised** (§28) into 7 metadata-driven pages plus a
>   **414th Features** page holding the per-feature boolean gates, with a search/"only changed"
>   filter bar and basic/advanced disclosure. Category names above are upstream's, not the fork's.
> - **Weapon date-gating is two toggles** in the fork: `restrict_weapons_by_date` and
>   `restrict_props_by_date` (era-gated payload-editor *properties*, e.g. JHMCS), enforceable
>   independently.
> - Pretense is **removed** from the fork.

LotATC export: set `LOTATC_DRAWINGS_DIR` env var on the host (LotATC 2.2+: `C:\users\<you>\LotAtc Data\Server\drawings\`); drawings generate once at mission start per selected faction.

## Performance doctrine (upstream guidance)

1. **Unit count is the #1 FPS killer.** Fewer squadrons, smaller squadrons, lower max frontline units. Rough ceiling: ~150 aircraft per side.
2. Budget drives unit count — lower starting budget / income multipliers if turn 1 already chugs.
3. Distant unit culling helps old full-map campaigns, less so modern ones. Exclusion zones: frontline+its airfields, closest opposing airfields if no frontline, and mission targets (except BARCAP/transport/AEW&C/refueling/recovery-tanker). Air units are NEVER culled — limit them via budget/squadron caps, not basing.
4. Ground pathfinding is CPU-heavy; long convoy legs hurt.
5. Tacview costs real frames; consider off.
6. Local dedicated server no longer helps (DCS is multi-threaded now) — external server is for MP only.

## Advanced (file-based) config

| Feature | Path | Notes |
|---|---|---|
| Forced options | `<DCS Saved Games>\Retribution\forced_options.lua` | Lua defining a `forcedOptions = {}` table with DCS-internal option keys; applied BEFORE Retribution's own settings, so Retribution wins conflicts. Full key list: unpack a .miz, read `options/forcedOptions` |
| Custom kneeboards | `<DCS Saved Games>\Retribution\Kneeboards\` | PNGs; root = all aircraft, subfolder named by DCS type ID (`FA-18C_hornet`, `F-16C_50`, `A-10C_2`) = that airframe only. Retribution's own pages are 960x1080 — match it |

## Modded unit support (11-step process, wiki: Modded Unit Support)

Adding a mod is NOT just a faction-file entry. Chain: pydcs data export (Lua hook in `me_mission.lua` dumps aircraft data) → inject into pydcs → campaign setup → Retribution unit YAML → default payloads + custom weapons → factions → layouts/groups → radar db update → optional UI icons → playtest → release & maintain. Needs the dev environment plus basic Python and Lua. Upstream expects the mod's champion (you) to do and maintain it.
