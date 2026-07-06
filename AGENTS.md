# AGENTS.md — 414Ret Claude Code Guide

The **414th Joint Fighter Group's fork of DCS Retribution** — a turn-based dynamic
campaign generator for DCS World, plus the 414th's air-defense, electronic-warfare,
recon, frontline, and assets-pack features on top of upstream.

- Base: upstream `dcs-retribution/dcs-retribution` `dev` @ `dce851ea`.
- GitHub (this fork): https://github.com/bradyccox/414Ret
- Read this before touching anything. The human-friendly overview is [`README.md`](README.md).

---

## Session Startup & Documentation Hygiene

**GitHub:** https://github.com/bradyccox/414Ret

**At the start of every new thread**, sync with GitHub before touching any code or docs:

```powershell
git fetch origin
git pull
git log origin/main -5 --oneline   # scan for new commits since last session
```

If the current branch is behind `main`, merge or rebase before editing anything — a branch
cut from a stale base produces exactly the duplicate-work + conflict mess that sinks a PR.
Never derive the state of the codebase from memory; always read the current files.

**Keeping docs in sync** — when a feature lands or changes, update in this order:

1. Relevant `docs/dev/design/` file — design rationale and technical details
2. Matching section in `docs/dev/414th-features.md` — engineering deep-dive, file paths, gotchas
3. `README.md` — if the change is player-visible
4. `CLAUDE.md` / `docs/dev/CLAUDE-architecture.md` — if the tech stack, architecture patterns, or feature list changed
5. `AGENTS.md` — sync to mirror `CLAUDE.md` (see Conventions)
6. `docs/dev/414th-ingame-pass-checklist.md` — add a row for any feature with runtime behavior that CI can't exercise

A push that moves code past its docs is a broken push.

---

## Project Docs

The per-feature engineering internals and design rationale live in `docs/`, not in this
file. This guide is the map; those are the territory.

- [docs/dev/414th-features.md](docs/dev/414th-features.md) — **the deep dive**: every 414th
  feature with file paths, gotchas, tests, and deferred work. Read the relevant section
  before editing a feature.
- [docs/dev/414th-feature-index.md](docs/dev/414th-feature-index.md) — the generated **feature
  index**: a table of every numbered "Features at a Glance" feature (plus the engine plugins)
  with its plugin and `Settings` wiring. Source of truth is the **feature registry**
  `game/fourteenth/features.py` (regenerate with `python -m game.fourteenth.features`); a test
  (`tests/fourteenth/`) fails CI if a setting/plugin reference goes stale, the registry and the
  feature list fall out of sync, a checklist row points at an unregistered feature, or this doc
  drifts. **Register every new feature there** (add its §N) so the list, catalog, and checklist
  stay in lockstep.
- [docs/dev/414th-ingame-pass-checklist.md](docs/dev/414th-ingame-pass-checklist.md) — the
  **in-game pass tracker**: every "needs an in-game pass" item with an observable pass
  criterion + the fail signature to watch for. Update status when you fly it; clear the tag
  in `414th-features.md` when it reaches VERIFIED.
- [docs/dev/414th-upstreaming-inventory.md](docs/dev/414th-upstreaming-inventory.md) — the
  **upstreaming queue**: which generic fixes to carve toward `bradyccox/dcs-retribution`
  (priority-ordered, with readiness marks) and which fork-specific bits must NEVER go upstream.
- [docs/dev/414th-community-contribution-roadmap.md](docs/dev/414th-community-contribution-roadmap.md) —
  the **long view**: a two-axis (community-value × carve-difficulty) re-classification of
  *every* feature, separating the thin genuinely-414th content/identity/economy layer from the
  large generic-capability set, with a strip-list per feature and the ordered contribution waves
  for giving the rest back upstream.
- [docs/dev/design/](docs/dev/design/) — per-feature design notes (read before touching the
  matching code):
  - `414th-air-defense-planning-notes.md` — CAP/BARCAP/QRA planning intent
  - `414th-tic-dynamic-fronts-notes.md` — TIC stance/cadence movement design
  - `414th-tars-recon-notes.md` — TARS recon engine
  - `414th-c130-ew-isr-notes.md` — C-130J EW/ISR source of truth + retired `ewrj` warning
  - `414th-csar-notes.md` — **the one CSAR doc** (vision, shipped survivor-ledger architecture,
    and the 2026-07-03 rescope: `auto_combat_sar` default ON, the AI-drama layer frozen, the POW
    recovery raid shelved). Supersedes the eight earlier CSAR/SCAR notes (each is bannered).
  - `414th-aircraft-task-rebalance-rubric.md` — aircraft task-priority rebalance rubric
  - `414th-red-tide-campaign-notes.md` — Red Tide campaign laydown + `.miz`/faction edits
  - `414th-inherent-resolve-campaign-notes.md` — **the Iraq / Mosul COIN campaign** (the Battle
    of Mosul 2016-17 on the DCS Iraq map; the 414th's **second COIN campaign**, sibling of Enduring
    Resolve on the same `coin.py` stack). New factions `CJTF-OIR 2016` (blue coalition) + `Islamic
    State 2016` (red, cloned from Toyota Al Gaib with the crust trimmed to SA-6/8/9/13). Laydown tuned
    across playtests to **6 airfields total** (from "a tiny red area" → a 13-airfield belt "this is a
    ton" → this middle ground): RED holds **3 airfields** (Mosul the anchor + SA-6, Erbil, Kirkuk + SA-6)
    and carries the rest of its presence via **10 FOBs** — the Highway-1 corridor (Tikrit, Bayji, Shirqat,
    Qayyarah), the Nineveh ring (Hammam al-Alil, Bartella, Tal Afar), and the eastern belt (Hawija,
    Makhmur, Gwer) — each **furnished** (2 garrisons + AAA + SHORAD + strongpoint + caches; Mosul/Kirkuk
    the SA-6). BLUE holds **3 southern airfields** (Balad the forward player field — **Q-West dropped** —
    + Al-Taquddum strike + Baghdad support) and grinds north on **one front up Highway 1** (Balad → Tikrit
    → Mosul); a 14-route red supply graph (corridor + ring + NE belt + Makhmur/Hawija bridges + Tal
    Afar/Syria ratline); the 3-phase Isolate → East Mosul → West Mosul/Old City arc with a permanent Mosul
    positive-control box (+ a tight Old City box in the last phase). **Drone wing added 2026-07-05**
    (user call off the installed-inventory audit): Baghdad hosts RQ-1A Predator ×4 `primary: TARPS`
    (persistent ISR — the `airecon` plugin banks AI drone overflights as confirmed BDA, so the drones
    localize the concealed IED/cell circles) + MQ-9 Reaper ×4 `primary: BAI`; the shared unit yamls
    gained `TARPS: 700` + honest `max_range` (800/400 NM) and both drones joined the faction
    `aircrafts` (the MQ-9 was previously only its JTAC unit). **The miz is now the ER
    decorate-a-base pattern**: the user hand-positioned the laydown in the ME → committed as
    `iraq_inherent_resolve_base.miz` (the source of truth — edit it in the ME, NOT the generator);
    `tools/build_iraq_inherent_resolve_miz.py` only ADDS the in-between `NEW_FOBS` to it. Headless-verified
    (16 CPs — RED 13 / BLUE 3 — furnishing + 14 routes all bind); CI-locked in
    `tests/fourteenth/test_inherent_resolve.py`; needs an in-game pass. NEW game required.
  - `414th-red-tide-supply-routes-notes.md` — YAML supply routes + Kastrup preset patch
  - `414th-comms-jam-notes.md` — enemy comms jamming off the IADS comms nodes (§51): why the
    in-game `radioTransmission` path beat SRS injection, the anti-grief guardrails, tuning levers
  - `414th-red-flag-81-campaign-notes.md` — **Red Flag 81-2 Nevada campaign** (real-exercise study +
    laydown + the Vietnam-mechanics wiring; the `.miz` is GENERATED by `tools/build_red_flag_81_2_miz.py`
    — edit the laydown tables there and re-run, never hand-edit the miz; laydown RE-POINTED 2026-07-02
    at the commercial 81-2 reference miz set (note §3a: raw-Lua cross-mission clustering — SA-6/SON-9/
    SA-8 joined the red faction, KS-19/Fire Can flak belts, 4 mock airfields, the Smoky belt as SHORAD;
    NEW game required); loader gotcha found in passing: `MizCampaignLoader` reads MERAD/SHORAD markers
    from the RED country block only, so a blue SAM marker silently drops)
  - `414th-campaign-maker-notes.md` — blank-start campaign maker (policy core landed; glue/wizard in progress)
  - `414th-weapon-dates-proposal.md` — weapon-coverage completion plan + the modern-weapon date-gating rule
  - **MIST → MOOSE consolidation & IADS engine** (✅ COMPLETE 2026-06-25 — MIST retired; read before
    touching IADS/plugins):
    `414th-mantis-iads-HANDOFF.md` (**start here** — MANTIS G6 in-game pass PASSED 2026-06-24
    (routing + networking + C2); MANTIS is the default IADS engine),
    `414th-framework-consolidation-notes.md` (the MIST-retirement roadmap + per-phase plan, now done),
    `414th-mantis-migration-notes.md` + `414th-mantis-vs-skynet-iads-parity.md` (the Skynet → MANTIS
    IADS engine migration, now **complete**: **MANTIS is the sole IADS engine — Skynet is removed**
    (the `skynetiads` plugin, the `iads_engine` selector, and the dual-engine wiring are all dropped;
    a tiny `IadsEngine` enum stub remains only so pre-removal saves unpickle before the value is
    migrated out). The shared IADS data model — `IadsNetwork`, `IadsRole`, `IadsProperties` and the
    `Skynet*` back-compat aliases — stays; MANTIS consumes it),
    `414th-moose-ops-opportunity-map.md` (which MOOSE `Ops.*` modules to adopt vs. keep in Python —
    e.g. `Ops.Chief` stays out; **the next phase now that MIST is gone**), and the per-plugin decisions
    `414th-ewrs-retirement-decision.md`, `414th-dismounts-decision.md` (both retired),
    `414th-mist-moose-shim-notes.md` (**the shim that retired MIST** — a vanilla-DCS `mist` compat shim
    live in `base/plugin.json`, replacing the shelved `414th-ctld-mantis-style-port-scope.md` `Ops.CTLD` port)
  - Drafts / not-yet-landed (design only): `414th-mission-planning-wiki-rework.md`
    (upstream wiki rewrite), `414th-scenery-import-notes.md` (scenery strike targets),
    `turnless.md` (turnless-campaign exploration),
    `414th-coin-HANDOFF.md` (**start here for the COIN line** — the next-session pickup:
    where C1–C3 stand (all merged), the P1 fly-script, the tuning levers, and the
    build-order for C1.5/C4) + `414th-coin-insurgent-replenishment-notes.md` (**the COIN campaign direction** —
    squadron pick 2026-07-02, Korea dropped; base = a fork of Operation Shattered Dagger
    whose zeroed enemy income confirms the gap. Free, anchored-cap insurgent cell
    regeneration from `finish_turn` — real units via `Base.commission_units`, never
    phantom spawns — throttled by destroyable ammo-cache TGOs, whitelisted to
    infantry/technicals/AAA, gated `coin_insurgency` default OFF; will coupling inverts
    the Vietnam weights (body count ≈ worthless, caches/ROE/patience decide) via the
    `will:` profiles + a planned inert-by-default `red_cache_lost` weight (C2, landed); the §35 trail
    machinery is the ratline. Delivery: **C1 regen core LANDED 2026-07-02**
    (`game/fourteenth/coin.py` + `coin_insurgency` (Campaign Management, default OFF) +
    the `finish_turn` hook + `tests/fourteenth/test_coin.py`; whitelist = class set +
    price ≤ 10 ceiling, because the unit data classes the insurgent technicals as IFV —
    the ceiling, not the class, is what keeps BMPs/Grads out; caches bind by TGO-to-CP
    ownership; state pickles as `game.coin_state`, getattr-guarded) → **C1.5
    re-infiltration LANDED 2026-07-03** (`414th-coin-reinfiltration-notes.md` —
    a staged, announced, counterable pipeline: real cell TGO → seeded ammo-cache TGO →
    engine-native `ControlPoint.capture` flip + a weak `REINFIL_GARRISON` C1 re-anchor,
    under a **conservation bound** (relocate, never grow — red CP count never exceeds
    turn 0) with the §36 player-field exclusion, projection gated on the source
    stronghold's C1 cache health, will handoff = a labeled `blue_base_lost`-weight
    move via `consume_reinfiltration_flips` in `update_political_will`; the 4 §8
    squadron calls resolved to the proposed defaults (HOLD_THRESHOLD=4, 2+2 timers,
    one attempt theater-wide, neutral+lost scope). `advance_reinfiltration(game,
    events)` in `coin.py` runs from `finish_turn` right after regen; gated
    `coin_reinfiltration` default OFF, preseeded ON in the campaign. **Engine-forced
    change vs the sketch**: TGO allegiance follows the parent CP's owner, so the red
    cell/cache attach to the **source red stronghold** (positioned near the target via
    `_infiltration_point`) and **reparent to the target on flip** (`_reparent`) — they
    become the new stronghold's militia + first cache. Tests
    `tests/fourteenth/test_coin_reinfiltration.py`; in-game pass = checklist P3) → C2 will feed → C3
    campaign fork → C4 dispersed cells (C2 LANDED 2026-07-02: `WillWeights.red_cache_lost` default 0.0 + the
    `_red_caches_destroyed` fully-dead per-TGO feed in `political_will.py`; **C3 LANDED
    2026-07-02**: the campaign **"Afghanistan - Operation Enduring Resolve (COIN)"** —
    miz GENERATED by `tools/build_coin_enduring_resolve_miz.py` (Shattered Dagger + 28
    ammo-cache markers on the 13 strongholds, never hand-edit), the inverted `will:`
    profile, the Disrupt→Clear and Hold→Break the Momentum arc, full-stack preseeds;
    C3 also added the **TGO revival channel** to `coin.py` — the laydown has NO front
    lines, so regen revives the strongholds' dead whitelist-eligible TGO cell units
    toward the `tgo_cap` anchor, armor channel first, recon fog untouched; engine-probe
    verified, CI-locked, checklist P1); §7 squadron calls RESOLVED 2026-07-02: 25 %
    cache floor, `ammo`-only caches, re-infiltration deferred-with-commitment.
    **COIN roadside IEDs LANDED 2026-07-03** (`game/fourteenth/coin_ied.py` — the third
    COIN direction): hidden IED emplacements on the insurgent ratline (the red-to-red
    `convoy_routes` graph), recon-fogged 1-unit red TGOs the player must TARPS + CAS
    within `FUSE_TURNS` (3) or they detonate and drain the mandate. `advance_roadside_ieds`
    from `finish_turn` after C1/C1.5; `MAX_ACTIVE_IEDS` (2) on distinct roads, placed on
    the road-waypoint nearest the front via the §35 picker pattern, attached to the
    forward red stronghold (allegiance). New `WillWeights.blue_ied_detonation` (default
    0.0, campaign-priced 2.5) consumed via `consume_ied_detonations` in
    `update_political_will`; reuses the shared `coin.spawn_red_ground_at` (refactored out
    of the C1.5 spawn) + `_tgo_by_id`/`_despawn`. Gated `coin_ied` default OFF, preseeded
    ON. Tests `tests/fourteenth/test_coin_ied.py`; in-game pass = checklist P4.
    **COIN high-value targets LANDED 2026-07-03** (`game/fourteenth/coin_hvt.py` — the
    fourth COIN direction): a rotating named insurgent leader surfaces near the
    most-contested red stronghold as a recon-fogged 3-unit red TGO, live for
    `HVT_WINDOW_TURNS` (4); killing him inside the window drops red momentum, letting it
    close is a free miss. `advance_hvt` from `finish_turn` after C1/C1.5/IED; one HVT at a
    time + `HVT_COOLDOWN_TURNS` (3); new `WillWeights.red_hvt_killed` (default 0.0,
    campaign-priced 4.0) consumed via `consume_hvt_kills` in `update_political_will`'s RED
    feed. **The CDE dilemma is emergent, not special-cased**: a stronghold on a
    population-center ring puts the HVT inside a §40 restricted zone, so his kill is *both*
    the momentum blow *and* a `count_roe_violations` mandate hit — the player chooses a
    dirty shot, a clean one, or a pass. Reuses the shared `coin.spawn_red_ground_at`.
    Gated `coin_hvt` default OFF, preseeded ON. Tests `tests/fourteenth/test_coin_hvt.py`;
    in-game pass = checklist P5.
    **COIN dispersed cells LANDED 2026-07-03** (`game/fourteenth/coin_dispersed.py` — the
    fifth COIN direction, C4): the insurgency in the open countryside between strongholds
    (not anchored to a CP like C1/C1.5/IED/HVT). Up to `MAX_FIELD_CELLS` (3) recon-fogged
    2-unit red cells seed on the stronghold→coalition line ≥ `MIN_FIELD_DIST_M` (12 km)
    off every CP, one per stronghold (spread, not stacked). **Distinct hook, no will
    weight**: an un-hunted cell that survives `MATURE_TURNS` (3) **coalesces into its home
    stronghold and revives a dead ammo cache** (re-opening the C1 regen throttle the player
    worked to shut off) — or, with no dead cache, revives ≤ `COALESCE_REVIVE` (2) dead
    militia bounded by the C1 `tgo_cap` anchor (never grows past turn 0). Killing a cell is
    ordinary attrition that denies the resupply — the reward is denial, not a meter.
    `advance_dispersed_cells` from `finish_turn` after C1/C1.5/IED/HVT; reuses
    `coin.spawn_red_ground_at` + the C1 revival machinery (`_revive`/`_revivable_units`/
    `_alive_cell_count`/`_ensure_anchors`). Gated `coin_dispersed_cells` default OFF,
    preseeded ON. Tests `tests/fourteenth/test_coin_dispersed.py`; in-game pass = checklist P6).
    **COIN fiction-kit + in-mission movement rework LANDED 2026-07-04** (`game/fourteenth/coin.py`
    + the new `coin` plugin — the COIN objects stop being re-skinned armor and start moving; only
    Enduring Resolve is tuned for now): **(1) Fiction-kit retype** — every COIN spawn funneled
    through `coin.spawn_red_ground_at(GroupTask.FRONT_LINE, sidc_override=…)`, which overrode only
    the *map symbol* and left the faction's front-line **armor** underneath (a BMP-1 wearing an IED
    icon). `spawn_red_ground_at` now takes a `unit_types` list; `_retype_units` re-points the trimmed
    units' DCS *type* (+ name; drops the stale armor threat ring) to kit selected from the **red
    faction's own resolved roster** (`_pick_faction_unit` + `ied_/hvt_/cell_unit_types` — anti-air
    excluded, price-capped, name-hint-first, never a hardcoded id): a VBIED = a lone soft **supply
    truck**, an HVT = a small **convoy** (leader jeep + armed technical + 2 rifles; `HVT_UNITS` 3→4),
    a cell (C1.5 + C4) = an armed **technical + infantry**. On Enduring Resolve (Toyota Al Gaib) →
    Ural-375 / UAZ-469+2×Insurgent-AK / DShK-gun-truck+Insurgent-AK (headless-verified end-to-end on
    real `TheaterUnit`s); degrades to the generated group if a role can't be filled, so no faction
    dependency. **The static IED was re-shaped 2026-07-05** (user call: back to the proposed static
    object, with guys around it): `ied_emplacement_unit_types` = an emplaced **device** — a vanilla
    `Fortification.Oil_Barrel` **static object**, faction-independent so it never degrades — guarded
    by a 2-man security team from the faction's own infantry (`IED_EMPLACEMENT_UNITS` 3, sized down
    to the kit so a rifle-less faction gets one barrel, never cycled copies; the mixed static+infantry
    group splits correctly in `tgogenerator`). **Clearing is device-anchored** (`_ied_intact`):
    killing the device clears the bomb even if the team survives (they melt away); killing the team
    alone leaves the fuse ticking; a VBIED (and pre-rework saves' vehicle emplacements, which carry no
    static) stays any-unit-alive. Real-roster verified: Oil Barrel + 2×Insurgent-AK / Ural-375.
    **(2) IED variety** — each plant deterministically alternates that **static roadside
    IED** (`FUSE_TURNS` 3) and a **mobile VBIED** (`VBIED_FUSE_TURNS` 2 — a suicide vehicle racing the
    nearest blue CP, `_nearest_blue_cp`); same fuse→detonation→`ied_detonations`→mandate consequence,
    distinct "intercept it"/"reached friendly lines" messaging. **(3) In-mission movement** — COIN's
    **first Lua runtime**: the emitter `game/missiongenerator/coinluadata.py` (`populate_coin_lua`,
    wired in `luagenerator.py`) emits `dcsRetribution.coin` — the live HVT convoy + each mobile VBIED
    as a DCS `TheaterGroup.group_name` + centre (+ the VBIED's target base) — **only** when a mover
    exists, and the new `resources/plugins/coin/` plugin drives them via `mist.goRoute` (alarm-green so
    they relocate, not fight): the HVT patrols a random loop within `hvtPatrolRadiusM` of its area, each
    VBIED beelines its target, both after a startup grace; **one-way drives (VBIED, infiltrator) are
    PACED to the 90-minute rule** (user call 2026-07-05 — an intercept must survive a slow player
    start: each repath sets speed = remaining distance / time left to `minJourneyS` (5,400 s), capped
    at the configured speed, floored at a 5 km/h crawl; loop movers never end so they already comply;
    continuous pacing, never a range trigger). **Movement only** — the kill/window/fuse
    consequence stays in the turn-boundary force model, so a mover shot down is recorded natively (the
    §35/§37 no-phantom-spawn lesson; a decapitated HVT / intercepted VBIED just stops being routed).
    Tests `tests/fourteenth/test_coin_units.py` + `tests/fourteenth/test_coin_ied.py` +
    `tests/missiongenerator/test_coinluadata.py` + `tests/lua/test_coin_runtime.py`; in-game pass =
    checklist P4/P5 (the moving convoy/VBIED + the retyped reads are Lua/cockpit-only).
    **COIN concealed map presence LANDED 2026-07-05** (the "markers dead on top of them" fix): an
    un-reconned hidden insurgent object (IED/VBIED, HVT, dispersed/re-infiltration cell — caches/
    garrisons stay exact) no longer draws an exact marker; `spawn_red_ground_at(concealed=True)` →
    `TheaterGroundObject.concealed` (pickle-safe) → the server TGO model (`concealed_uncertainty`
    in `game/server/tgos/models.py`) sends a **deterministically jittered centre** (seeded from the
    TGO id, offset 15–60% of the radius so the truth stays inside; exact coords never reach the
    client) + `uncertainty_radius_m` (4 km), and the web map draws a dashed red "suspected
    activity" circle with the marker's click/right-click contract (frag TARPS/CAS onto it);
    TARPS/attack discovery (or fog-off/reveal) snaps it to the exact symbol via `known_for`.
    **Road-pinned IEDs (2026-07-05, user call — "we know what highway it's on but not which
    street"):** an IED/VBIED's circle centre slides **far ALONG its supply road** (5–25 km on the
    polyline via `TheaterGroundObject.concealed_route`, set at plant; deterministic, clamped to
    the road) instead of the radial offset — the truth may sit OUTSIDE the circle, the highway is
    the search domain; degenerate/pre-feature routes fall back radial.
    Tests `tests/fourteenth/test_coin_concealment.py`; in-app pass = the P3 checklist concealment
    bullet (covers P3–P6, needs the CI client rebuild).
    **COIN in-mission liveliness pass LANDED 2026-07-05** (the "systems feel static" thread,
    part 3 — after the concealment fix + the static-IED emplacement): **(1) the insurgency
    shoots back** — new `coin_harassment` (Campaign Management → Insurgency, default OFF,
    preseeded ON in both COIN campaigns): blue airfields/FARPs/FOBs within
    `HARASS_STRONGHOLD_REACH_M` (40 km) of a red stronghold draw sporadic in-mission
    rocket/mortar barrages — the §36 airbase-harassment shape (emitter filters every
    player-spawn field, the hard anti-grief guarantee, + an `excludedBases` Lua double-guard;
    startup grace; small dispersed `trigger.action.explosion`s), but **stronghold-proximity
    based**, so it works on the front-less Enduring Resolve laydown where the preseeded
    front-based §36 toggle silently no-ops (kept on Inherent Resolve, where the two
    complement). Cosmetic pressure only — no force-model change; clearing the strongholds is
    what silences the fire. **(2) the cells move** — C4 dispersed field cells wander a small
    loop of their patch (`cells` movers) and the live C1.5 re-infiltration cell creeps toward
    the base it is taking (`infiltrators` movers), both through the coin plugin's existing
    `mist.goRoute` machinery (alarm-green, movement only — the coalesce/flip consequences stay
    in the turn model; a killed cell just stops being routed). `populate_coin_lua` extended
    (a `coin` node now also emits with harassment alone); plugin options cover the cell/infil
    speeds + cadences and the harass interval/rounds/dispersion/power/grace. Tests
    `tests/missiongenerator/test_coinluadata.py` + `tests/lua/test_coin_runtime.py`; in-game
    pass = checklist P8),
    `414th-vietnam-political-will-roe-notes.md` (**the Vietnam campaign layer** — the approved
    month-scale rework, spec of record: (1) a symmetric **political-will economy** (BLUE
    Political Will / RED Regime Resolve on `Coalition`, fed from the existing `Debriefing` —
    weighted airframe losses with a B-52 multiplier, POWs draining per turn held, ROE
    violations, trail-logistics attrition for RED) with a **negotiation win/loss**
    (`check_win_loss` branch: break Hanoi's resolve before Washington's patience breaks —
    territory win stays) and (2) **ROE / Route-Package escalation** riding the campaign-phases
    spec's P0–P2 + two authored extensions (`restricted_zones` soft-enforced by will penalties,
    `target_release` gates with RESTRICTED map badges, a Rolling Thunder → Linebacker II arc
    for the 4 Vietnam campaigns; sanctuary airfields fall out of zones). Delivery W1–W5, one PR
    each (W5 = the thin QRA→GCI ambush adaptation). **W1 + W2 landed** — W1 = the observe-only
    will (`Coalition.political_will` + the `vietnam_political_will` toggle + the
    `record_political_will` debrief feed in `game/fourteenth/political_will.py` + the SITREP
    will band); W2 = the **negotiation ending** (`negotiation_verdict` backing a gated
    `check_win_loss` branch ahead of the territory checks — RED resolve exhausted → WIN "Hanoi
    agrees to terms", BLUE will exhausted → LOSS "Washington orders withdrawal", BLUE-loss
    precedence on a simultaneous collapse; territory victory untouched — plus once-only
    era-framed exhaustion banners and the 4 Vietnam campaigns preseeding the toggle; weight
    balance = checklist M1); **W2b landed** = the **static front** (`vietnam_static_front`,
    preseeded ×4 — `game/fourteenth/static_front.py` clamps each front's position to a ±10 %
    band around its campaign-start anchor via a `FrontLine._blue_route_progress` clamp hook,
    so the strength battle bends the line + feeds will but never sweep-captures a base; Air
    Assault stays the one territorial lever; armed/disarmed idempotently from
    `Game.initialize_turn`; in-game pass = checklist M2); **W3 landed** = campaign-phases P0+P1
    (feature §40 — generic, all campaigns, `campaign_phases` default ON); **W4 landed** = the ROE
    escalation layer (authored `phases:` arcs ×4 Vietnam campaigns — Rolling Thunder → Bombing
    Halt → Linebacker → Linebacker II — with `restricted_zones` soft-enforced by will penalties,
    `locked_targets` target-release gates + RESTRICTED badges, the red dashed map layer, and
    will-coupled `advance_when` escalation; in-game pass = checklist M4); **W5 landed** = the
    GCI-ambush adaptation (`Doctrine.gci_ambush` → late-scramble/close-engage dispatcher tuning
    + the intercept Lua's hit-and-run leash; sanctuary basing falls out of the W4 zones;
    checklist M5); **W6 landed** = phase-coupled red tempo (design note
    `414th-vietnam-red-tempo-notes.md` — Hanoi *answers* the arc: an authored per-phase `red_tempo:`
    block (`game/fourteenth/red_tempo.py` + the `phases.py` parse) gives the Bombing Halt a
    `trail_surge` logistics window (2 concurrent, bigger trail convoys + `resolve_regen` 1.5/turn so
    waiting out the halt costs Washington leverage) and Linebacker a 3-turn Tet/Easter
    `ground_offensive` stance pulse (raise-only to AGGRESSIVE, still bounded by the W2b clamp —
    pressure on the will economy, never sweep-captures; the pulse implies the ≥2.0 trail surge);
    authored-only so Tier-0/generic campaigns are untouched; hook = `apply_red_tempo` in
    `initialize_turn` after the coalitions plan; checklist M6). **The campaign-layer arc W0–W6 is
    COMPLETE.** **The will economy generalized 2026-07-02** (design note
    `414th-will-generalization-notes.md`): the Washington/Hanoi framing + every feed weight are now
    only the *defaults* of a campaign-authorable **will profile** — a `will:` YAML block (sibling of
    `phases:`) re-labels the meters/exhaustion banners and re-weights the feeds, parsed by
    `parse_will_profile`/`will_profile_for` on the phases-S5 rederive-never-pickle rule, degrading to
    the Vietnam defaults on any failure (the 4 Vietnam campaigns carry no block ⇒ byte-identical);
    plus a new **warship feed** (`blue_ship_lost` 4.0 / `red_ship_lost` 0.5 via `TheaterUnit.is_ship`,
    ships subtracted from RED's generic attrition pool — the Falklands prerequisite). Any-era survey +
    the COIN direction (squadron pick; blocked on a COIN laydown + insurgent-replenishment design
    pass; Korea dropped) live in that note. The
    Vietnam pieces stay default-off (`vietnam_political_will`/`vietnam_static_front` gated); no
    debrief-schema changes anywhere in the arc),
    `414th-campaign-phases-notes.md` (**campaign phases** — a thin doctrine-like *phase*
    layer, active per turn-range, that biases the auto-planner's offensive intent + shows in
    the UI/kneeboard; three authoring tiers over one `CampaignPhase` object — **Tier 0
    inference is the default for all 66 campaigns** (a turn-by-turn classifier reads live IADS
    ratio / air threat / front momentum / territory via existing accessors → rollback →
    interdiction → offensive, with hysteresis), Tier 1 = YAML-tuned, Tier 2 = authored arcs
    for the 3 hand-built campaigns; rides the `VIETNAM_DOCTRINE` override precedent, composes
    with doctrine, never a commander rewrite; reactive defense stays deterministic (§17
    boundary). A **6-campaign inference pilot** (4 modern + 2 Vietnam) is done — see
    `414th-campaign-phases-pilot.md` + the reusable `tools/campaign_phase_laydown.py`
    (`--lite` raw-`.miz` parse / `--engine` real pipeline); it surfaced two threshold
    refinements now in the spec: an **absolute long+medium-SAM floor** gate and EWR
    de-weighting. The **all-66 draft table is now `--engine`-authoritative** (re-run
    2026-07-01 on the real install) — `tools/campaign_phase_classify.py` (the offline §3.2
    classifier reference impl; `--laydown` consumes a saved engine dump) +
    `414th-campaign-phases-all66-draft.md` (57 Rollback / 5 Air Superiority / 4 Interdiction).
    The engine run closed all three `--lite` blind spots (mod-SAM undercount, auto-assign air,
    and the newly found **generator-filled AA slots**) and corrected the pilot's headline:
    **Khe Sanh actually fields 4 generated SA-2/SA-3 batteries ⇒ opens Rollback**; the genuine
    below-floor cases are Shattered Dagger / No Man's Land / Valley of Rotary / Northern
    Guardian, with Velvet Thunder exactly at the floor (3 sites, keeps Rollback). SAM banding
    reads TGO `GroupTask` LORAD/MERAD (the DEAD planner's own target set) — `IadsRole` can't
    band it (its SAM role swallows SHORAD). **P0+P1 LANDED** as feature §40 / Vietnam campaign
    layer W3 — Tier-0 inference + hysteresis + the HTN soft emphasis + the kneeboard/client
    status surfaces are live for all campaigns (`campaign_phases`, default ON; the runtime
    classifier bands by the same LORAD/MERAD set). **P2 + first P3 arcs LANDED** (Vietnam W4):
    the `phases:` YAML authoring tier, `advance_when` conditions, the ROE zones/release payload
    + planner gate, and the 4 Vietnam Rolling Thunder → Linebacker II arcs; still open =
    objectives checklist, per-phase whitelist deltas, `front_line_stance`, the 3 wiki-campaign
    arcs),
    `414th-airwar-planner-consolidation-notes.md` (behavior-preserving consolidation of the
    air-war planner's threat-field + standoff geometry onto one `AirspaceGeometry` service;
    keeps the brain in Python, Tier-C/`Ops.Chief` explicitly out of scope),
    `414th-csar-notes.md` (see the design-notes list above — the authoritative CSAR doc since the
    2026-07-03 rescope; the old `414th-scar-king-fac-notes.md` / `414th-combat-sar-normal-task-notes.md`
    entries are superseded into it),
    **Vietnam campaign-set consolidation (2026-07-03):** the three standalone Caucasus Vietnam
    campaigns (`1968_Yankee_Station`, `khe_sanh_niagara`, `steel_tiger`) were merged into the one
    **`1968_Yankee_Station`** — the Steel Tiger trail OOB tilt (BAI/armed-recon squadrons on the Ho
    Chi Minh Trail) and the Khe Sanh Operation-Niagara *siege* (a depleted `Sochi-Adler` starting the
    DMZ front pressed in via `control_point_strengths`, plus the airbase-harassment + Super-Gaggle
    preseeds it already had) are folded into Yankee Station's features/scenario; `khe_sanh_niagara`
    + `steel_tiger` `.yaml`/`.miz` are removed. The live Caucasus Vietnam set is now
    `1968_Yankee_Station` + `operation_velvet_thunder` (plus `red_flag_81_2` on Nevada); the
    `414th-khe-sanh-campaign-notes.md` design note is bannered SUPERSEDED and the Khe-Sanh
    wiki (`docs/wiki/Khe-Sanh-*.md`) + handbook (`docs/campaigns/khe-sanh-*.md`) player pages were
    deleted. Historical development counts
    below ("the 4/5 Vietnam campaigns") are left intact as the record of what happened at the time.
    NEW game required. Guards live in `tests/test_vietnam_content.py` (repointed onto the
    `yankee_station` fixture) + `tests/fourteenth/test_red_tempo.py`.
    `414th-vietnam-ops-notes.md` (**Vietnam Ops suite** — a `Vietnam Ops` settings page gating five
    opt-in period mechanics: Arc Light as a heavy-bomber Strike *effect*, AAA flak gauntlet, naval
    gunfire support, Armed-Recon truck-convoy interdiction, Super Gaggle resupply; Tier-A runtime only,
    default OFF / campaign-flipped ON; **Phases 1–4 landed** = the settings page + §32 Arc Light + §33
    flak gauntlet + §34 naval gunfire + §35 convoy interdiction (the Steel Tiger trail; spawn Lua
    **verified 2026-06-30**, checklist L6); phase 5 (Super Gaggle) is blocked on an auto-plannable CTLD
    cargo run the engine lacks),
    `414th-vietnam-airbase-harassment-notes.md` (**Vietnam Ops §F — airbase harassment**: scoped-only
    sapper/mortar/rocket standoff fire on opposing-occupied fields, following the §33 flak runtime
    pattern; hard requirement = never target a player-spawn field + a startup grace period. **LANDED** as
    CLAUDE.md §36 — the emitter + plugin runtime are in; needs an in-game pass, checklist L8),
    `414th-vietnam-retribution-notes.md` (**"Vietnam Retribution" mode** — the *framing* layer the Ops
    suite lives inside: three thin layers over the one engine — a New Game "Vietnam" shell + content
    filter + a doctrine profile (`VIETNAM_DOCTRINE`) that renames taskings (MiGCAP/Iron Hand/Alpha
    Strike/Sandy) via a display-only override on `Doctrine` (never the persisted enum) and gates the
    planner whitelist — split 2026-07-01 into the offensive `VIETNAM_DOCTRINE` (BLUE + the what-if USSR
    bomber faction) and `VIETNAM_AIR_DEFENSE_DOCTRINE` for Hanoi's factions (NVA/Vietcong/North Vietnam ×5):
    same era identity (renames/knife-fight ranges/`gci_ambush`) minus BLUE's offensive levers (no
    Alpha Strike fan, no forced strike escorts, **no strike-escort reserve trimming the defensive BARCAP** —
    red's air force IS its BARCAP, and the reserve was stealing MiGs from the W5 ambush posture) **and a
    narrower tasking whitelist** (2026-07-02: a played 1968 Yankee Station turn 1 caught red Air Assaulting
    `Maykop-Khanskaya`, the Ubon/"Thailand" rear base, purely because it had no garrison TGO — the generic
    `PlanAirAssault` task has no front-proximity/sanctuary awareness, and nothing stopped red from proposing
    it; `VIETNAM_AIR_DEFENSE_DOCTRINE` now also drops `AIR_ASSAULT` from its whitelist, a mass/insertion
    mission the GCI-only ambush force never flew — BAI/CAS/Strike/Armed Recon stay whitelisted for red's
    *helo* squadrons, and Armed-Recon-vs-CP is generic engine behaviour every doctrine shares). **The bulk
    of that same playtest's "red aggression" was campaign squadron-role authoring, not the doctrine**: red
    MiG-17F/21 fast-mover squadrons carried `primary: BAI` / an `air-to-ground` secondary, auto-assigning them
    to Interdiction/Strike (which the QRA reserve can't touch — it only governs BARCAP-auto-assignable
    squadrons). Fixed at the campaign layer across **all 5 Vietnam campaigns** (Yankee Station / Steel Tiger /
    Khe Sanh [already clean] / Red Flag 81-2 / Velvet Thunder): every red MiG/aggressor fighter squadron is
    now `primary: BARCAP` + `secondary: air-to-air` (defensive auto-set only), and each campaign seeds
    `opfor_default_qra_reserve: 4` (was the global 2) so more MiGs sit on reactive hot-alert than standing
    forward BARCAP orbits — the genuine GCI-ambush posture, which also activates the re-roled fast movers'
    previously-dead reserve (QRA seeding keys off airframe BARCAP capability). OWNFOR unchanged; NEW game
    required. Guards: `test_vietnam_red_fighters_are_defensively_tasked` +
    `test_vietnam_campaign_seeds_opfor_qra_reserve`.
    **P0 (era tags) + P1 (doctrine model + 10-faction repoint) + P1b (display read-path)
    + P1c (period-authentic planner *numbers*: A2A engagement ranges shortened to the early-missile/gun era
    — `cap_engagement_range` 35→22 NM, `escort_engagement_range` 20→10 NM so MiGCAP/escort fight close not
    BVR; `rtb_speed` 450→400 kt; and a `VIETNAM_GROUND_PROCUREMENT` OOB that is infantry/artillery/AAA-heavy
    with light armour and **no ATGM/IFV** — the ATGM-decisive war was Yom Kippur, not Vietnam. So the doctrine
    now makes the era *play* differently, not just read differently; rebadge-equality test extended + range/
    speed/ground-ratio tests added. **P1c addendum 2026-07-02 — the low-level attack profile**:
    `Doctrine.low_level_attack_altitude` (Vietnam = 500 ft, both doctrines) presses CAS/BAI/Armed-Recon combat
    legs onto the deck — RADIO/AGL waypoints via `WaypointBuilder.get_combat_altitude` + the CAS track-floor
    bypass — so AI attack flights can trip the §39 snake-and-nape release gate (500 ft = the `napeCeilingFt`
    default) and fly inside the §33 flak envelope; Strike (Alpha Strike dives + B-52 Arc Light), helos, and
    heavies exempt (`HEAVY_BOMBER_DCS_IDS` moved to `game/data/units.py`); the AI's actual release altitude is
    the remaining L11 flown check, NEW game required)
    + P2 era pre-seed (Vietnam campaigns auto-enable the Ops mechanics on select) + P2 New-Game "Vietnam" card
    (Intro `vietnamMode` radio → `TheaterConfiguration` filters the list to `era: vietnam` via
    `Campaign.matches_era`; needs an in-app pass) + P3 strike-deadlock fix + P3 tasking whitelist + P3 Alpha
    Strike sizing landed** — the design's phases are now all in (Iron Hand = Shrike-vs-emitter is moot now SEAD
    is dropped). **P3 strike-deadlock**: Vietnam has no SEAD, so
    retribution's "suppress the air defense before you strike" rule deadlocked the whole offensive fleet
    (0/28 strike + 0/13 BAI plannable — an upstream-shared behaviour, not a fork bug); two additive
    default-False `Doctrine` flags (`strike_through_air_defense_threat`, `plan_strikes_without_full_escort`)
    let Vietnam strike into threatened areas + fly unescorted (headless-verified 7→19 BLUE packages; needs a
    NEW game). **P3 tasking whitelist**: `VIETNAM_DOCTRINE.tasking_whitelist` drops SEAD/SEAD_ESCORT/
    SEAD_SWEEP/DEAD/ANTISHIP, gated in `PackagePlanningTask.fulfill_mission` (disallowed primary scrubs the
    package; disallowed escort is just dropped) — fixes era jets on wrong tasks (an A-1 on SEAD Sweep) and
    headless-verified SEAD/DEAD/anti-ship 13→0 while STRIKE 1→5 / BAI 6→13 rose. **P3 Alpha Strike**:
    `Doctrine.strike_flight_count` (default 1) can fan N coordinated, shared-TOT STRIKE sections onto one
    target in `PlanStrike` (reads the *planner's* doctrine via `target.coalition.opponent.doctrine` — the
    target is enemy-owned). Vietnam masses a **surge deck-load: up to 4 sections + a forced fighter escort**
    on ONE target — the real Alpha Strike (`strike_flight_count=4` + `always_escort_strikes`, which forces
    the A2A escort "needed" in `check_needed_escorts` even with no detected air threat; still pruned when no
    fighter is free). Only the first section is required — the rest are **surge sections**
    (`ProposedFlight.optional`, honored in `plan_mission`): they plan when a squadron has the jets and drop
    silently when not (no scrub, no purchase order), so the top-priority target absorbs the strike fleet and
    later strikes shrink toward single sections (replay: `WOLVERINE: STRIKE x2 ×4 + ESCORT x2 + TARPS`, 11
    aircraft on one target, while `NEWT` flies the leftover single section). The fan was briefly reverted to
    1 when the sections flew naked; restored once the fighter-economy levers held.
    The **"Alpha Strike" label is earned, not flat** (user playtest caught four separate 2-ships each
    wearing the name): `Package.is_massed_strike` (≥2 STRIKE sections totalling ≥4 bombers) gates the era
    rename at all three display sites (`package_description`, `Flight.task_display_name`,
    `FlightData.task_display_name`) — a lone section (or a pair of single-ships) reads plain "Strike".
    **No solo strikers**: strike section size is floored at 2 for every doctrine (1-unit targets were
    producing single A-4s flying strikes alone; a tiny target now draws a real 2-ship section or nothing). The
    **fighter-economy levers** landed after
    the Linebacker naked-B-52 playtest (2026-07-01): `Doctrine.escort_support_aircraft=False` (Vietnam) drops
    the AEWC/tanker fighter escorts that consumed 8 of 10 fighters before any strike planned
    (`fulfill_mission` filter), and `Doctrine.strike_escort_reserve=4` +
    `AirspaceGeometry.trim_rounds_for_escort_reserve` trims BARCAP volume (coldest CPs first, down to
    abandoning low-threat coverage but never the hottest location) so the fighter force escorts the
    *shooters* — save-replan verified: support escorts 8→0 jets, BARCAP 10→2. The reserve is also **fenced**
    (`PackageFulfiller.escort_reserve_withholds`, the strike-first escort priority): a non-STRIKE package
    (BAI, OCA, even CAS in a true famine) is refused its A2A escort whenever planning it would dip the live
    `AirWing.untasked_fighters()` pool below the reserve — only a STRIKE-led package may spend those last
    airframes, so the freed fighters actually reach the bombers instead of the first BAI section planned. A
    withheld escort is not a shortage (the package flies unescorted, no procurement order). Doctrines are
    pickled by value — a NEW game carries the new numbers. The Ops suite's Arc
    Light/flak/NGFS are this design's P4 flavor, already built)
- [README.upstream.md](README.upstream.md) — unmodified upstream project README (setup,
  dependencies, wiki links).
- `AGENTS.md` mirrors this file — see **Conventions** below for the sync process.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Campaign engine | Python 3.11 (`game/`). Python library catalog (bookmark, reference-only — nothing to adopt now; browse if a new library is ever needed): https://github.com/vinta/awesome-python |
| UI | PyQt (`qt_ui/`) + React/Leaflet client (`client/`) — client NOT type-checked in CI |
| Mission scripting | **Lua 5.1** sandbox plugins (`resources/plugins/`) — no `os`/`io`, no `goto`, definition order matters |
| In-mission framework | **MOOSE** (bundled `Moose.lua`; some plugins vendor classes verbatim) — the standard. **MIST is RETIRED** (MIST → MOOSE consolidation complete, 2026-06-25): `base/plugin.json`'s `"mist"` work-order now loads `resources/plugins/base/mist_moose_shim.lua` — a vanilla-DCS shim implementing the 43 `mist.*` symbols the consumers (CTLD, SCAR, intercept glue, core `dcs_retribution.lua`, and the upstream land/water relocate scripts) actually call, so `mist_4_5_126.lua` no longer loads. **When merging upstream Lua, grep it for `mist.` — a symbol the shim lacks dies at runtime, not in CI** (the 2026-07-05 upstream sync needed a new `mist.getGroupData` for `land_relocate.lua`/`water_relocate.lua`; checklist U1). The old `mist_4_5_126.lua` file is **kept in the repo as a one-line rollback** (revert `plugin.json`) until the shim has been flown across more campaigns; delete it as the final cleanup. Do NOT re-point the work-order back without reason. See `414th-mist-moose-shim-notes.md`. MOOSE API docs (bookmark): https://flightcontrol-master.github.io/MOOSE_DOCS_DEVELOP/Documentation/index.html |
| Units / mission format | pydcs; CurrentHill mod packs in `pydcs_extensions/` |
| CI gates | Black + mypy + pytest + **Lua syntax gate** (`lua-lint.yml`, blocking) + advisory luacheck |
| Release | PyInstaller → rolling `latest` pre-release on GitHub |

---

## Key Architecture Patterns

**Planner / Lua split.** Python plans and spawns the mission (flight plans, ROE, templates);
runtime behavior (EW, ISR, recon scoring, frontline firefights) is driven by the Lua
plugins. When a feature has both, the Python side sets up and the Lua side executes — don't
move runtime logic into the planner or vice versa.

**Plugin script injection (the uniform late-init pass).** Most 414th plugins are normal
work-order plugins. TIC, TARS, and SCAR additionally need their main script loaded **after**
every plugin's config table exists (their init reads `dcsRetribution.plugins.<name>` / MOOSE
at file scope) — an ordering the per-plugin work-order pass can't express. They are `LuaPlugin`
subclasses (`game/plugins/{tic,tars,scar}.py`, registered in `manager.py`'s `_PLUGIN_CLASSES`)
declaring `late_init_files()` / `late_init_preamble()` / `should_late_init()`; `inject_plugins()`
runs a **second pass** that calls `inject_late_init()` on each after the normal config pass. A
missing/renamed init file is now caught by a test (`game/plugins/tests/test_late_init.py`)
instead of the feature silently never starting. (Replaces the old hand-injected
`_inject_*_script()` "scramble pattern".)

**Viewer-aware visibility layer (recon fog).** One layer drives two player-facing fog rules.
AI planning and threat math always use ground truth (`viewer=None`); only the human (BLUE)
map/UI are fogged. `TheaterUnit.alive_for(viewer)` handles BDA damage lag;
`TheaterGroundObject.known_for(viewer)` handles recon intel-fog; `hidden_on_player_map(viewer)`
fully hides enemy command posts for the SCAR commander-capture feature (gated by
`scar_command_post_intel`, now default ON for new campaigns; §15). Every
accessor takes `viewer: Optional[Player] = None` defaulting to truth; consumers gate at the edge.
Do **not** reintroduce the old `_for_player`/`_for` method twins — that collapse is finished.
A runtime **overview toggle** (`game/theater/fogofwar.py`, transient/never-pickled) short-circuits
those three fog leaves (`alive_for`, `known_for`, `hidden_on_player_map`) to ground truth for any
viewer, so the *whole* render path + intel dialogs un-fog with **no** server-model changes. It is
a checkbox in the custom map layers panel (`MapLayersControl`, §18), driven by a state
`useEffect` (not a Leaflet add/remove layer — unmount doesn't reliably fire `remove`) that
`PUT`s `/fog-of-war/reveal` then re-pulls `/game`.
(`game/theater/theatergroup.py`, `theatergroundobject.py`; see features doc §3.)

**Save migration.** Removed/renamed enum *values* migrate in **one place**:
`FlightType._missing_` (`game/ato/flighttype.py`) maps legacy persisted strings to live
members via the `_LEGACY_FLIGHT_TYPE_VALUES` table. The unpickler (`persistency.py`
`_handle_flight_type`) calls `FlightType(value)`, which routes through `_missing_`, so it
carries **no** parallel remap table — only unknown-value tolerance (degrade to BARCAP).
Other persisted state (e.g. fog) migrates in each class's `__setstate__`. When you rename a
persisted enum value, add the entry to `_LEGACY_FLIGHT_TYPE_VALUES` only.

**Lua plugin discipline.** Lua 5.1 only, vanilla DCS units only (no HighDigitSAMs etc.),
define functions before first use. The `lua-lint.yml` CI workflow runs `luac5.1 -p` over
every `resources/plugins/**/*.lua` as a blocking syntax gate — it catches parse-time errors.
On top of that, the **headless Lua plugin harness** (`tests/lua/`, design note
`414th-lua-plugin-harness-notes.md`) runs the real plugin scripts on Lua 5.1 via `lupa`
against a faked DCS sandbox inside the normal pytest run — catching the "script errors at
runtime and the feature silently never starts" class + pinning safety invariants (grace
periods, exclusion lists, one-shot latches). First coverage: `vietnamops`. It models no DCS
AI/physics, so real behavior still needs an in-game pass (see the in-game-pass checklist).

---

## Features at a Glance

Full internals for each are in [docs/dev/414th-features.md](docs/dev/414th-features.md)
(section numbers below).

1. **QRA intercept reserve** — per-squadron alert reserve feeding the upstream PR #782 Moose
   `AI_A2A_DISPATCHER`. Base-defense posture by default. (Old ramp-scramble is retired.)
   **Player-manned QRA**: `Squadron.qra_player_manned` carves N of the reserve into a
   cold-start, home-field base-defense BARCAP (`HomeBaseDefenseZone`) fragged for the human at
   planning (`Coalition._plan_player_qra`, BLUE only); those airframes are debited from the AI
   dispatcher (`ai_qra_resource_count`) so a jet is never both manned and air-spawned. A
   Phase-3 **scramble cue** (`PlayerAlertEntry` → `dcsRetribution.Intercept.PLAYER_ALERT` →
   `intercept-config.lua`) calls the player to scramble when a raid closes inside the GCI
   radius + a lead margin. Design note `414th-qra-player-manning-notes.md`; checklist A3/A4
   (need an in-game pass). **GCI-ambush posture** (Vietnam campaign layer W5):
   `Doctrine.gci_ambush` (VIETNAM only) makes a side's dispatcher fly era hit-and-run GCI —
   engage radius shrunk to the doctrine's 22 NM cap range, scramble capped at 40 NM (late
   launch, slash the strike package near its target), and a Lua-side leash (disengage 50 NM
   from home + RTB at 35 % fuel) so MiGs hit once and recover; other doctrines pass the QRA
   settings through unchanged (`dispatcher_tuning` in `interceptluadata.py`; checklist M5).
2. **JAMMING flight type** — C-130J as EC-130H/RC-130H EW+ISR platform (`c130j` plugin);
   the old generic `ewrj` fighter-pod jammer is retired and must not be restored.
3. **TARPS recon + BDA fog-of-war** — player F-14 photo recon; viewer-aware fog (damage lag +
   recon intel-fog) makes recon worth flying. **Concealed field forces (2026-07-05)**: with
   `concealed_enemy_forces` (Difficulty & Realism, default ON), an un-scouted enemy *field* force —
   mobile SAM (MERAD/SHORAD/AAA), deployed vehicle group, missile site — draws a dashed
   "suspected activity" **uncertainty circle** (centre deterministically jittered off the truth,
   exact coords never sent to the client) instead of an exact marker; LORAD/EWR/buildings/ships
   stay exact, discovery snaps it to the real symbol, and the COIN insurgent spawns conceal
   intrinsically via `TheaterGroundObject.concealed` (`concealed_uncertainty` in
   `game/server/tgos/models.py`; checklist G24). **AI recon BDA capture** (`airecon` plugin, added
   2026-07-01) closes the G19 gap that the MOOSE TARS film path is **player-only** (its birth
   handler drops any non-player unit), so auto-paired *AI* recon flights confirmed nothing:
   `populate_ai_recon_lua` (`aireconluadata.py`) emits each AI-flown, player-coalition (BLUE)
   **recon-capable** flight + its target; the `airecon` plugin watches each and, when it survives to
   overfly (within a trigger range of the target), records the enemy ground units there into the same
   `tars_recon_captures` ledger the player film menu feeds — so the debrief
   (`debriefing.py`→`tars_reconned_tgos`) treats an AI recon capture identically. A shot-down /
   aborting recon flight confirms nothing (one-shot). Player-crewed flights are never emitted (still
   the F10 film path); blue-only. Emitter-tested; runtime Lua needs an in-game pass (checklist G19).
   **A drone is always filming (2026-07-05, 414th rule)**: `_feeds_ai_recon` counts a flight as recon
   if it is TARPS-tasked (any airframe) **OR a drone** (`UAV_DCS_IDS` in `game/data/units.py` — a
   curated set; DCS has no UAV flag, `category` buckets drones as generic "Air") **regardless of the
   drone's tasked mission**. A UAV is a sensor first — solo recon, JTAC overwatch on a strike, or CAS,
   it still banks BDA on what it overflies; a manned combat jet only feeds it when actually tasked TARPS.
   **Recon drone in each Armed Recon package (2026-07-05, 414th call)**: the auto-recon hook
   (`PackageFulfiller._maybe_plan_tarps_recon`, gated by `auto_add_tarps_recon`) now also frags one
   optional TARPS flight into **Armed Recon** packages (not just Strike/DEAD); `TarpsFlightPlan` was
   widened to accept a `ControlPoint` target (armed recon sweeps a CP corridor, not a TGO). On a
   UAV-fielding faction the TARPS bird IS the drone, so OIR gets a Predator/Reaper in every armed
   recon package (and the `airecon` loop banks its overflight as BDA). Armed recon primary is now a
   fixed 4-ship (`PlanArmedRecon.ARMED_RECON_FLIGHT_SIZE`); with the threat-gated 2-ship SEAD escort
   resolving to the Viper, the package reads 1 drone + 2 SEAD Vipers + 4 recon. Optional/gated (drops
   if no drone free, never scrubs). Tests `tests/test_armed_recon_planning.py`; checklist G25.
   **Role-aware TOT (2026-07-05 de-jumble)**: `TarpsFlightPlan.default_tot_offset` was a flat +2 min
   (BDA-only reasoning) applied to every package. It now reads the package primary — **+2 min** behind
   a Strike/DEAD shooter for a **post-strike BDA** look, but **0** on an Armed Recon package (or a
   standalone recon), a **find/overwatch** pass on station with the shooters, not two minutes behind a
   strike moment that never happens. The `configure_tarps` behavior (flyover, ReturnFire) is unchanged;
   only the timing is now role-split.
   **Packaged drone is a lasing JTAC (2026-07-05, 414th call)**: the old FLOT auto-JTAC (a `jtac_unit`
   MQ-9 glued to the front line) was ripped out — `JtacInfo` went unproduced, `jtac_unit` dormant — but
   the CTLD autolase runtime + kneeboard/radio consumers stayed live. `AircraftGenerator._maybe_configure_jtac`
   revives it on the **packaged drone**: an AI flight of the faction's `jtac_unit` in an A/G package
   (`_JTAC_PACKAGE_PRIMARIES` = Armed Recon/CAS/BAI/Strike — option 1, may narrow to {Armed Recon, CAS})
   is emitted as a `JtacInfo` → `dcsRetribution.JTACs` → `ctld.JTACAutoLase` (autolase + smoke default ON),
   so it lazes/marks for the shooters + shows on the kneeboard/radio. No DCS task added (CTLD does the
   designation); blue + AI only; a real (killable) asset, not invisible/immortal. Laser code allocated per
   JTAC (or 1113 on `ctld.fc3LaserCode`). Tests `tests/missiongenerator/test_drone_jtac.py`; checklist G26
   (the loiter-vs-overfly runtime question is the open in-game item).
   **Auto-fielding the JTAC drone squadron (2026-07-05)**: the packaged JTAC only fires if a drone
   squadron exists, but squadrons come only from a campaign's `squadrons:` block — so the ~55 campaigns
   without a drone would show no JTAC. `ensure_jtac_drone_squadron` (`game/fourteenth/jtac_drone.py`,
   hooked in `Coalition.configure_default_air_wing` after the campaign's own assignment) auto-fields one
   small (2-ship) TARPS-tasked drone squadron at the **rear-most** blue airfield for any blue side whose
   faction declares a **drone** `jtac_unit` (`UAV_DCS_IDS`, TARPS-capable) and doesn't **already field a
   drone** (so OIR and other hand-placed-drone campaigns are untouched). The auto-recon hook frags it
   forward → drone-JTAC + always-films. Gated `auto_jtac_drone` (default ON, kill switch) + **era-gated**
   (`_UAV_SERVICE_YEAR` — 12 Cold-War factions carry a lazy default MQ-9 jtac_unit; a 1988 campaign like
   Red Tide never auto-fields a 2007 Reaper). Tests `tests/fourteenth/test_jtac_drone.py`; checklist G27.
4. **UI transparency** — Target Intel panel, Mission Impact debrief summary, package context
   bar, flight-creation context, building-card cleanup.
5. **Player target location precision** — `Approximate` mode offsets steerpoints + hides exact
   marks/coords so players must visually acquire.
6. **Air-defense planning rework** — overlapping/jittered BARCAP waves, forward CAP line,
   threat-weighted BARCAP volume, a map-scaled **red forward-middle BARCAP layer** (added,
   not relocated; via a `ForwardBarcapZone` target), front-line navmesh routing hazard,
   unstacked FLOT units.
7. **Auto-hide mobile SAMs on MFD** — SHORAD/AAA/MANPAD hidden from datalink, including
   escorts inside armor/missile groups; standalone MERAD/LORAD stay visible for SEAD.
8. **Robustness / crash fixes** — flight-exit IndexError, AWACS/tanker orbit, malformed mod
   payload Lua.
9. **TIC — Troops In Contact** — scripted frontline firefights with per-stance movement +
   414th ambient-fire extension (plugin, default ON).
10. **CurrentHill Iran assets pack** — Shahed-136, IRGCN FAC, `[CH] Iran 2020` faction.
11. **Native DCS DTC cartridge export** — RETIRED (2026-06-26): half-baked; never
    pre-loaded reliably and ED is shipping native DTC. Do not restore. (§11)
12. **TARS recon engine** — MOOSE Ops.TARS runtime for TARPS, feeds confirmed BDA (default ON).
13. **Flight Control ATC** — RETIRED (2026-06-26): half-baked MOOSE FLIGHTCONTROL tower
    comms plugin; removed. Do not restore. (§13)
14. **Plugin Options UI** — `descriptionInUI` field + label/default polish across all plugins.
15. **SCAR — RESCAP "Sandy" rescue escort** — repurposed (rescue rework, design note
    `414th-scar-rescue-rework-notes.md`) from the **retired** armor-hunt task into the rescue-escort
    role of the **Combat SAR package** (`FlightType.SCAR`, A-10C/AH-64D, scoped to the FLOT). The
    standing package = **1 King (C-130) + 1 Jolly Green (helo) + 2–4 Sandy**; Sandy's racetrack is
    planned once at generation, but an **AI-crewed** Sandy is now **dynamically diverted** at runtime
    (`combatsar` plugin, added 2026-07-01; **route-push rework 2026-07-02** — the original
    `SetTask(TaskCombo)` divert was flown and confirmed a no-op: `EngageTargetsInZone` is an en-route
    task the DCS controller silently rejects inside a main-task combo. The divert is now a transit
    waypoint + a hold waypoint over the survivor carrying the orbit + engage as *waypoint* tasks, and
    the release routes the Sandy back to its recorded station) off that racetrack to hold + actively
    engage near a live ejection once one occurs, freeing again once the
    survivor is resolved — a player-flown Sandy is untouched (voice/SRS coordination). "Walking the
    rescue helo in" itself is still voice-first only, not scripted, for either. features doc §15,
    checklist G23 (**FROZEN, pass-or-delete** per the 2026-07-03 rescope: the re-fly passes and the
    divert stays as-is, or it fails and the divert is deleted — no third rework). **Enemy-capture race**
    (`combatsar` plugin): on ejection an enemy snatch party (several small dispersed teams, spawned
    under the opposing faction's country) may race to seize the survivor — kill it
    to save, or the pilot is **CAPTURED** (`combat_sar_captures` state global) and held as a **POW**
    (`PendingPowRecovery`, holding field resolved at capture). **POW mechanics reworked 2026-07-06**
    (design note `414th-csar-notes.md` "POW mechanics rework"): a capture flips the aviator to the new
    **`PilotStatus.POW`** (`pilot.capture()`) so the squadron stops scheduling them while captive (they
    leave `active_pilots`); **recapturing the holding field** frees them (`repatriate()` → Active); the
    hold is the **4-turn clock on a normal campaign but INDEFINITE when `vietnam_political_will` is on**
    (the §48 running sore drains until freed or the war ends), with a **Homecoming**
    (`resolve_pows_at_game_end` from `process_win_loss`) that repatriates all held blue POWs on a
    negotiated win and writes them off on a withdrawal loss. Every write-off routes through `_write_off`,
    which **respects the built-in `invulnerable_player_pilots` setting** (a player POW is repatriated, not
    killed — also fixing a latent bug where the old clock killed invulnerable players). A POW is surfaced
    on the **SITREP band** (name @ holding field + clock/"held") and the **squadron roster** status. **The
    POW recovery *raid* is SHELVED (2026-07-03 rescope)** — the `CSAR` raid flight type
    (persisted saves degrade to TRANSPORT), the dynamic `CapturedPilotGroundObject` map objective
    (tombstoned; `purge_pow_objectives` sweeps old saves), and `commit_pow_recoveries` are removed;
    capture is a campaign consequence, not a plannable mission.
    Standing package via `auto_combat_sar` (King + Jolly + 1 Sandy), **default ON** since the rescope.
    The old armor-hunt scenario + its auto-planner are **deleted** (2026-06-27: `scarluadata.py`, the
    `scar` plugin, `PlanScarHunts`/`PlanScar`, `scar_autoplan*`); the CSAR recovery plumbing was
    repurposed for the POW path. The **dormant SOF capture economy was removed 2026-07-01**
    (`FlightType.SOF`, the commander-capture reveal/refund, stranded-team objectives, the plugin's
    SOFRESCUE channel, `scar_misid_penalty` — save-compat tombstones in `game/scar_rescue.py`);
    the command-post fog (`scar_command_post_intel`) stays live. Design source of truth:
    `414th-csar-notes.md`. features doc §15.
16. **Settings QOL audit** — dead/duplicate setting cleanup (four fields removed), AI-radio
    booleans consolidated into the `AiRadioBehavior` enum with deterministic save migration,
    plugin wording, and a UI-layer grouping/dependency handoff
    ([docs/dev/settings-qol-audit.md](docs/dev/settings-qol-audit.md)).
17. **Auto-planner target unpredictability** — opt-in, per-side
    (`ownfor_/opfor_planner_unpredictability`, default 0) weighted-random reordering of the
    HTN's *opportunistic* offensive targets (strike/OCA/BAI/anti-ship/non-threatening DEAD)
    so red stops hitting the same things every turn; reactive threat response stays strictly
    deterministic. The low-risk in-Python alternative to a runtime MOOSE `Ops.Chief` red
    rewrite (`game/commander/tasks/targetorder.py`; features doc §17).
18. **Fog-of-war overview toggle** — a transient **"Reveal fog of war"** checkbox in the unified
    map layers panel (#19, "Enemy intel" group) that short-circuits the three recon-fog
    leaves to ground truth, un-fogging the whole map + intel dialogs (enemy composition, threat
    rings, hidden command posts) with no server-model changes. `PUT /fog-of-war/reveal` flips the
    flag, then the client re-pulls `/game`. Never persisted; defaults off
    (`game/theater/fogofwar.py`, `game/server/fogofwar/`; features doc §3).
19. **Unified map layers panel** — one custom, dark-themed Leaflet control
    (`client/src/components/maplayers/MapLayersControl.tsx`) replacing both stock layer controls:
    collapsible grouped sections (advanced groups start collapsed), preset views (Default / SEAD /
    Recon / Clean), and choices persisted to the campaign save (localStorage-cached), except the
    transient fog overview (`GET`/`PUT /game/map-layers` → `Game.client_map_layers`). The
    old top-left threat-zone/navmesh/terrain control is folded in; side-effect toggles run via
    `useEffect`, not Leaflet add/remove. Client-only; needs the CI client rebuild (features doc §18).
20. **Drop-spawn: map right-click unit placement** — right-click blank map space → Qt dialog
    (coalition / category / unit-type picker from all 66 named `LAYOUTS` / unit rows / deploy-timing
    / respawn) → `place_unit_group()` validates terrain + 200 km range, creates TGO, fires SSE so
    the marker appears immediately. Right-click a user-placed TGO to remove it (`DELETE /tgos/{id}`).
    Deploy Next Turn queues a `PendingUnitPlacement` materialised at turn start. Two cheat settings:
    `enable_unit_placement` (unlock) + `enable_free_unit_placement` (no cost).
    (`game/theater/unitplacement.py`, `qt_ui/windows/groundobject/QPlaceUnitGroupDialog.py`,
    `client/src/components/liberationmap/MapContextMenu.tsx`; features doc §20.)
21. **Combat SAR** — bespoke pilot-rescue flight type (`FlightType.COMBAT_SAR`): a CH-47
    orbits the FLOT as the rescuer, a C-130 flies the HC-130 "King" overhead orbit (air-tracking
    **TACAN-only** beacon — no ADF — + F10 LARS survivor-locator), driven at runtime by the plugin's
    **survivor ledger** (`combatsar` plugin). AI standing alert `auto_combat_sar` — **default ON**
    since the 2026-07-03 rescope (existing saves keep their stored choice); rescue is a normal,
    standing task. **Rescue scoring closes the loop:** delivering a downed pilot to a friendly field spares the
    aviator at debrief (airframe still lost) — the `combatsar` plugin's `OnAfterBoarded`/`OnAfterRescued`
    hooks append the ejected unit name to the `combat_sar_rescues` state global, and
    `commit_air_losses` skips that pilot's kill (fail-safe: empty list = pre-scoring behaviour).
    Distinct from the POW-recovery `FlightType.CSAR` raid (§15). (`game/ato/flighttype.py`,
    `game/commander/tasks/primitive/combatsar.py`, `game/sim/missionresultsprocessor.py`,
    `resources/plugins/combatsar/`; features doc §21, design doc `414th-csar-notes.md`.)
22. **Kneeboard space-utilisation + custom import** — sparse kneeboard pages (Combat SAR,
    Support, Mission Info) restyled to fill the page with a *light* heading + underline-rule +
    whitespace layout (no boxes), and the Friendly Packages list flows into two columns when
    long (`KneeboardPageWriter.rule()`/`vspace()`/`table_two_column_paginated()`). Plus a
    **custom-kneeboard import** UI (`QCustomKneeboardsWindow`, *Kneeboards* toolbar action):
    import an image once → stored in the campaign save as `game.custom_kneeboards`
    (`CustomKneeboard` = name + PNG bytes + optional `airframe_id`) → injected into every client
    flight (or one airframe) at generation by `KneeboardGenerator._inject_custom_kneeboards()`.
    Per-campaign (no cross-campaign leak like the global `Kneeboards/` folder); old saves migrate
    via `__setstate__`. (`game/customkneeboard.py`, `game/missiongenerator/kneeboard.py`,
    `qt_ui/windows/kneeboards/QCustomKneeboardsWindow.py`; features doc §4, checklist H1/H2/H4.)
23. **Per-squadron DCS country** — each squadron's air units spawn under their own DCS *country*
    (`squadron.country`, already set by preset YAML / inherited from the faction) so a mixed-nation
    CJTF side gets nation-specific voiceovers/comms instead of one shared faction voice. A
    `CountryAssigner` (`game/missiongenerator/countryassigner.py`) resolves the country per
    squadron, registers every per-side nation on the coalition, and enforces the DCS one-country-
    per-coalition rule (blue claims first; colliding red squadrons fall back to the red faction
    country) while interning one canonical `Country` instance per id (pydcs attaches groups to the
    instance). No-op for single-nation factions (the squadron loader already restricts them to the
    faction country). Implements upstream issue #627. **Nation-aware pilot names** complete the
    arc: `Squadron.faker` now draws from the squadron's own DCS country (a curated country→Faker-
    locale table in `game/squadrons/pilotnames.py`) instead of the shared faction locale, so the
    Greek squadron rosters with Greek names, the Iranian with Persian, etc.; unmapped/multinational
    countries fall back to the faction faker (never breaks generation), and the logic is fully
    unit-tested (`tests/squadrons/test_pilotnames.py`). (`game/missiongenerator/missiongenerator.py`,
    `game/missiongenerator/aircraft/aircraftgenerator.py`, `game/squadrons/pilotnames.py`;
    features doc §23, checklist I1/I5.)
24. **Date-gated aircraft properties** — extends the existing `restrict_weapons_by_date` toggle from
    weapons to era-defining payload-editor *properties*. First curated gate: **JHMCS** helmet cueing
    (fielded ~2003) is hidden from the dropdown and clamped to the baseline visor when generating a
    pre-2003 mission. A small hand-authored table (pydcs carries no property dates) keyed by value
    *label* — so the F/A-18/F-16 "JHMCS" is gated but the Su-30/Su-35 "SURA Visor" (same id) is not —
    scoped to the helmet-device identifiers. UI filters the dropdown; the generator
    (`degrade_props_for_date`) is authoritative and resolves against the unit-type default so the
    defaulted-JHMCS case is caught. (`game/dcs/aircraftproperties.py`,
    `game/missiongenerator/aircraft/flightgroupconfigurator.py`,
    `qt_ui/windows/mission/flight/payload/propertycombobox.py`; features doc §24, checklist I3.)
25. **Compact 3-4 page kneeboard deck** — RETIRED (2026-07-05, the kneeboard back-to-basics rework):
    the compact folding machinery (`compact_kneeboard`, `_compact_kneeboard_pages`, the
    `CombatIntelPage`/`CommsCoordPage`/`FlexReferencePage` composites, `_draw_section_if_fits`, the
    adaptive flex page) was the fork's biggest `kneeboard.py` churn vs upstream and is deleted. The
    squadron-picked keepers survive on the stock **full deck**, now the only assembly path: the cover
    page (§30) + the Brief Sheet (§31) leading each flight's block + the colour palette + the threat
    cards (`generate_threat_intel_kneeboard` default flipped ON). The fuel ladder is **folded into the
    flight plan** (2026-07-05, user call): a `Fuel` column + a one-line RTB margin call-out on Mission
    Info — the standalone Fuel Ladder page + `generate_fuel_ladder_kneeboard` are deleted. Do not
    restore the folding machinery. (features doc §4, checklist H9 retired → H12.)
26. **Off-mission combat fidelity + PLAYER_AT_IP fix** — the sim auto-resolves engagements the player
    doesn't fly. Abstract combat was numbers-only coin flips (more flights win; survivors die 50/50; SAMs a
    flat 50%), so obsolete jets beat modern ones and SEAD meant nothing. `game/sim/combat/capability.py`
    now weights A2A by best A2A `task_priority` × count (win = strength share, survivor loss scales with
    margin, clamped ≤ legacy 0.5) and SAM survival by SEAD role/capability + engaging-site count; `aircombat.py`
    / `defendingsam.py` call it (`SKIP` untouched). Separately, **"Player at IP"** was silently defeated by
    the default `PAUSE` resolution ending the fast-forward at the first combat *anywhere* before a
    ground-started player reached its IP; `AircraftSimulation._combat_pauses_fast_forward` now lets AI-only
    combats keep resolving during a `PLAYER_AT_IP` fast-forward (only player-involving combats pause).
    (`game/sim/combat/`, `game/sim/aircraftsimulation.py`; features doc §26, checklist J1/J2.)
27. **Shared-airframe kneeboard index** — DCS scopes kneeboards per *airframe*, so every pilot of a type
    sees all that type's flight decks stacked. `KneeboardGenerator.generate` keeps each flight's pages a
    contiguous, callsign-sorted block and prepends a one-page **index** (callsign / task / start page) only
    when 2+ client flights share the airframe (a lone flight is unchanged). `pages_by_airframe` →
    `client_flights_by_airframe` + `_build_kneeboard_index` + `KneeboardIndexPage`.
    (`game/missiongenerator/kneeboard.py`; features doc §27, checklist H10.)
28. **Settings IA reorg + difficulty presets** — the settings dialog + New Game wizard are
    100% metadata-driven (they walk `Settings.pages()/sections()/fields()`), so a single ordered
    `FIELD_LAYOUT` table (`game/settings/settings.py`, from `_LAYOUT_SPEC`) now drives the whole
    layout — no field declarations moved, no behaviour change, no save migration. It kills the two
    34/37-item "General"/"Gameplay" grab-bags, regroups everything into six focused pages
    (**Difficulty & Realism · Air Doctrine · Campaign Management · Mission Generation · Kneeboards ·
    Performance**), and centralises scattered difficulty knobs onto Difficulty & Realism. On top of
    that, **difficulty presets** (`game/settings/difficultypreset.py`: `DifficultyPreset` Casual/
    Normal/Veteran/Ace + `apply_preset`/`detect_preset`) — a one-click `DifficultyPresetBar` atop the
    Difficulty & Realism page sets 12 difficulty-defining fields together (Normal == stock defaults);
    every setting stays hand-editable after. The classmethods fall back to a field's own
    `page=`/`section=` metadata for anything absent from FIELD_LAYOUT, so nothing is ever dropped.
    **Second IA pass 2026-07-05 (the New Game wizard audit)**: the wizard's Generator page's
    world-shaping options (no-carrier/navy checkboxes, squadrons-start-full, budgets) moved onto the
    **Theater** page ("Forces & Budget", campaign-reseeded on select; field names unchanged), leaving
    a dedicated grouped **Mods** page (Aircraft/Asset packs/Air defense — the curated 16 of ~50
    `ModSettings`); legacy sweep (Vietnam card's deleted-Khe-Sanh text, "Advanced IADS (WIP)" →
    "(MANTIS)", the stale `Default.zip` subtitle, `TIME_PERIODS` chronologically sorted + named
    default, dead `SettingNames.py` deleted, OH-6 checkbox relabeled ground-objects-only); and a
    section regroup (Campaign Management gets a "Campaign features" opener + "Commander economy";
    Mission Generation splits out "Battlefield life"; Air Doctrine's 13-field threat wall becomes 4
    focused sections). FIELD_LAYOUT-only — 7 pages, 174 fields, walk-verified.
    (`game/settings/settings.py`, `game/settings/difficultypreset.py`,
    `qt_ui/windows/settings/QSettingsWindow.py`, `qt_ui/windows/newgame/`, `qt_ui/uiconstants.py`;
    features doc §28, checklist K1.)
29. **Campaign SITREP kneeboard band** — a "what happened last turn" digest on the next mission's
    kneeboard cover page (a cockpit intel brief). `MissionResultsProcessor.commit()` gets a final
    `record_sitrep` step that reads the debriefing it already has — per-side losses (`loss_counts`),
    base captures (the cached pre-commit snapshot), Combat SAR rescues — into a `Sitrep`
    (`game/sitrep.py`) stored as `game.last_sitrep` (pickled, `__setstate__` default None). Enemy
    losses are framed as **"claimed"** to respect the recon-fog model. The SITREP renders on the
    always-present **cover page (§30)** as a "SITREP — Turn N" section, gated by `sitrep_for_kneeboard`;
    hidden on turn 1 / a quiet turn / when the `generate_sitrep_kneeboard` toggle (Kneeboards page,
    default ON) is off. v1 covers losses/captures/rescues; front movement + SCAR commander capture are
    deferred. (`game/sitrep.py`, `game/sim/missionresultsprocessor.py`, `game/game.py`,
    `game/missiongenerator/kneeboard.py`, `game/settings/settings.py`; features doc §29,
    checklist K2.)
30. **Dedicated kneeboard cover page** — a single front sheet that **always** leads a flight's deck,
    consolidating three things: the **operation/turn/date header** (new — every deck opens telling you
    what op + turn), the previous turn's **SITREP** (§29, moved off the briefing-page band so it stops
    crowding the flight plan), and the shared-airframe **flight index** (§27, was a separate conditional
    page). `CoverPage`
    (`_build_cover_page`) is always prepended in `KneeboardGenerator.generate`, replacing the conditional
    `KneeboardIndexPage` and the `BriefingPage` SITREP band. The cover is page 1 so decks start on page 2
    (the §27 start-page math is preserved); the index section appears only for 2+ shared-airframe flights,
    the SITREP section only when there's something to report. (The retired compact mode briefly parked
    the friendly-package list here; the list lives only on its standalone `FriendlyPackagesPage` now.)
    (`game/missiongenerator/kneeboard.py`, `game/sitrep.py`; features doc §30, checklist K2/H10.)
31. **One-page Brief Sheet + deck-wide colour scheme** — every flight's block leads with a single
    scannable **Brief Sheet** (`BriefSheetPage`) modelled on the squadron's printed Appendix A one-pager
    (Red Tide handbook): header, mission, the **full labelled route — every steerpoint with number +
    planned time** (`HOLD 1 12:32 → TKR 2 12:38 → JOIN 3 12:49 → TGT 5-8 13:01 → LAND 10`; consecutive
    strike points collapse to a range), admin, threats (air + SAM), game plan, comms, code words,
    bullseye, fields (RWY/ATC/TCN), WX (departure-field QNH/QFE + surface wind), loadout, laser,
    Combat SAR — **auto-filled** by
    `_build_brief_sheet_data` (route from waypoints, loadout from the jet's pylons cleaned to ordnance, air
    threats from the enemy faction's fighters, the rest re-surfaced). Since the back-to-basics rework it
    *fronts* the stock deck — the Game Plan/BLUF + steerpoint table follow it. Empty fields render a
    `______` **fill-in blank**
    (`_blank_line`) like the printed template — the layout never collapses — plus a `NOTES` blank. A new
    **theme-aware four-colour semantic palette** on `KneeboardPageWriter` (+ a `text_runs` inline-colour
    primitive) — blue nav/comms, amber threats/fuel, green success, red abort — is applied across the
    Brief Sheet, the **threat cards** (amber MEZ/Detect, blue HARM/cues; their Threat Intel Brief page is
    default ON) and the **code words card** (push blue, SUCCESS
    green, ABORT red) so the whole deck reads as one product. Loadout/laser validated against a real `.miz`.
    (`game/missiongenerator/kneeboard.py`; features doc §31, checklist H12.)
32. **Arc Light heavy-bomber Strike carpet** — the first **Vietnam Ops suite** feature (design note
    `414th-vietnam-ops-notes.md`; settings page §28 "Vietnam Ops"). Reframes Arc Light as an *effect of the
    Strike task*, **not** a new `FlightType`: when a heavy bomber (B-52H/B-1B/Tu-95MS/Tu-142/Tu-160/Tu-22M3)
    flies a `STRIKE`, the runtime walks a carpet of explosions across the target at the run-in instead of a
    single aimpoint, modelling Operation Niagara. Tier-A config bridge — Python emits `dcsRetribution.VietnamOps.arcLight`
    (each eligible bomber group + its target centre) only when the `vietnam_arc_light` toggle is on, and the
    `vietnamops` plugin watches each bomber, then on reaching the release range walks a box of `trigger.action.explosion`
    impacts oriented along the bomber's bearing-to-target (carpet length/width/power/release-range are plugin
    options). A bomber shot down before the run-in never fires — losses stay native; tactical strikers are
    untouched. (`game/missiongenerator/vietnamopsluadata.py`, `game/missiongenerator/luagenerator.py`,
    `resources/plugins/vietnamops/`, `game/settings/settings.py`; features doc §32, checklist L1.)
33. **AAA flak gauntlet** — the second **Vietnam Ops suite** feature: recreates the AAA-heavy Vietnam
    threat environment (the standing "real threat = AAA, not SAMs/MiGs" gap). With `vietnam_flak_gauntlet`
    on, the `vietnamops` plugin discovers AAA guns at **runtime** by the DCS `AAA` unit attribute (frontline
    ZSU/Shilka belts + airfield guns), and any opposing aircraft within an alive gun's range and below the
    effective ceiling draws **barrage flak bursts** (`trigger.action.explosion` airbursts at altitude). A
    steady, predictable heading+altitude **tightens** the bursts (and a sustained predictable run draws the
    occasional close "tracking" round); jinking/varying altitude widens them — atmospheric pressure to
    manoeuvre, mostly visual with a modest tunable bite, **not** a hidden hard-kill SAM. Python emits only an
    on-marker (`dcsRetribution.VietnamOps.flak`); range/ceiling/miss-distances/power are plugin options.
    Symmetric (both sides' AAA). (`game/missiongenerator/vietnamopsluadata.py`, `resources/plugins/vietnamops/`,
    `game/settings/settings.py`; features doc §33, checklist L2.)
34. **Naval gunfire support** — the third **Vietnam Ops suite** feature: offshore gun ships shell shore
    targets. Python (`_populate_naval_gunfire`) emits each naval gun ship (CRUISER/DESTROYER/FRIGATE — the
    VWV battleship New Jersey is class Destroyer, so it's covered) + its coalition; the `vietnamops` plugin
    runs **two modes** off that list: a **player F10 "Naval Fire Mission"** menu fires the nearest in-range
    friendly gun ship on the coalition's last F10 map marker (`world.getMarkPanels`), and an **automatic
    coastal bombardment** where each gun ship shells the nearest opposing ground target within gun range every
    cadence (`MOOSE TaskFireAtPoint`, the TIC artillery path). **Coastal by construction** — with no enemy
    ground (or no marker) in a ship's range nothing fires, so inland campaigns (Khe Sanh) no-op. Range/rounds/
    salvo/auto-cadence are plugin options. (`game/missiongenerator/vietnamopsluadata.py`,
    `resources/plugins/vietnamops/`, `game/settings/settings.py`; features doc §34, checklist L3.)
35. **Convoy interdiction (Steel Tiger)** — the fourth **Vietnam Ops suite** feature: a moving enemy supply
    column on the road behind the FLOT (Steel Tiger / Ho Chi Minh Trail), surfaced through Armed Recon. **Now a
    real, tracked convoy in the force model, not a phantom runtime spawn** (reworked 2026-07-01 to eliminate a
    "free non-existent unit" — the old `coalition.addGroup` trucks existed only in the `.miz`, so killing them
    cost the enemy nothing and no loss was recorded). Retribution already models convoys
    (`coalition.transfers.convoys` carry real ground units, spawn as road-moving groups via `ConvoyGenerator`,
    are Armed-Recon/BAI targets, and their loss is recorded as `enemy_convoy` so the units never arrive), so the
    feature now just **ensures enough are flowing**: `ensure_enemy_trail_convoy` (`game/fourteenth/vietnam_convoy.py`,
    run once per turn from `finish_turn`) — when `vietnam_convoy_interdiction` is on and the opfor is under its
    concurrent-convoy budget (`BASE_MAX_CONVOYS` 2, `SURGE_MAX_CONVOYS` 3 under a W6 trail surge) — moves a few
    of the opfor's **real** rear-area ground units toward a road corridor nearest the front, debited from the
    source base (`new_transfer` → `commit_losses`). **Reworked 2026-07-03 (twice, same day)** off flown-session
    feedback ("only 3 vehicles, only 1 convoy"): baseline concurrent convoys 1→2 (surge 2→3), and
    `_pick_trail_corridor` gained `exclude_sources` so filling the budget **prefers distinct roads** rather than
    stacking extra columns on the single best one — several campaigns (Yankee Station/Steel Tiger's full trail
    network, Khe Sanh's two rear feeders, Red Flag 81-2's aggressor corridors) genuinely have more than one
    opfor-opfor road to spread onto; a single-corridor map still caps at one convoy (no regression). **The real
    gate turned out to be an empty rear economy, not the cap**: a headless engine load found every rear opfor
    CP's `Base.armor` at zero at turn 0 (it's the coalition's production/income stock, not a garrison), so
    `_seed_trail_source` now tops a picked source to a standing stock (2× a convoy load, same bound as the
    pre-existing COIN ratline) from the coalition's own `Faction.frontline_units` roster, framed as **external
    logistics support** — the Ho Chi Minh Trail's actual historical character (matériel from China/the USSR,
    not local production). `MAX_CONVOY_UNITS` raised 4→10 accordingly. **Engine-verified**: Yankee Station and
    Khe Sanh each spawn 2 convoys of 10 units on 2 distinct roads at turn 1 (20 vehicles total, vs. the old
    single 3-vehicle column). `operation_velvet_thunder.yaml` has
    **no `supply_routes` at all** (its Marianas island geography has no roads between bases), so the toggle is a
    documented no-op there regardless of the seeding rework — flagged, not fixed. So interdicting the trail now
    denies the enemy real reinforcements (kill it and they never reach the line; let it through and they do),
    and the kill is recorded natively. Fully guarded (no front / no road corridor / budget full / no unit pool
    ⇒ no-op; the engine's organic convoys still serve). **No `vietnamops` plugin runtime** any longer — the
    emitter and the Lua convoy section are removed. (`game/fourteenth/vietnam_convoy.py`, `game/game.py`,
    `game/settings/settings.py`; features doc §35; checklist L6.)
    **Right-click planning (added per playtest):** the player **right-clicks an enemy supply route** on the
    map to frag the interdiction package — `SupplyRoute.tsx` `contextmenu` → `POST /qt/create-package/supply-route/{route_id}`
    → `interdiction_target_for_route_id` resolves the route (its id now encodes the two CP ids) to the enemy
    end (contested CP first) → the Qt package dialog opens there **pre-selected on Armed Recon** (the add-flight dialog auto-opens); friendly routes 404.
    Supersedes the old "no right-click" design stance; still an Armed Recon frag, just discoverable on the
    route. The client API hook is hand-added to the generated `_liberationApi.ts` (codegen unavailable
    locally). (`game/server/qt/routes.py`, `game/server/supplyroutes/models.py`,
    `client/src/components/supplyroute/SupplyRoute.tsx`; test `tests/server/test_supply_route_interdiction.py`;
    checklist L7 — needs an in-app pass + the CI client rebuild.) **Armed Recon is an AREA search again
    (2026-07-05):** the earlier "sweep the hunted road" plan (`_search_track` SEARCH START/MID/END down the
    convoy polyline) was reverted — the runtime engage zone is already ~18.5 km (10 NM
    `armed_recon_engagement_range_distance`), so a single `armed_recon_area` overflight blankets the corridor
    ("look in the area and find them"), and marching a specific road wasn't that. The right-click frag still
    lands an Armed Recon on the road's enemy end; the flight now area-searches that end. Road-follow
    overrides + `armed_recon_point` + `test_armed_recon_track.py` removed
    (`game/ato/flightplans/armedrecon.py`).
36. **Airbase harassment (rocket/mortar siege)** — the fifth **Vietnam Ops suite** feature (design note
    `414th-vietnam-airbase-harassment-notes.md`, §F): forward, opposing-occupied airfields draw sporadic
    standoff rocket/mortar fire near the ramp, recreating the near-constant siege of Bien Hoa/Da Nang/the Khe
    Sanh strip — "the rear isn't a safe area." Same shape as §33 flak: Python emits a small target list and the
    `vietnamops` plugin runs the runtime. `_populate_airbase_harassment` (`vietnamopsluadata.py`) walks the
    airfield/FARP control points and emits each one that is **occupied** (non-neutral), **forward** (within
    `HARASSMENT_FRONT_REACH_M` ≈ 200 km of a front — so a deep-rear or peacetime field is never shelled; no
    front ⇒ no node ⇒ plugin no-ops), and **not a player-spawn field this mission** (departure/arrival/divert of
    any client flight — the hard anti-grief guarantee, filtered in Python so an excluded field can never become
    a target; the exclude set is also emitted under `excludedFields` as a Lua-side double-guard). Each record is
    `{ name, x, y, coalition }`. The plugin schedules a per-field loop that, **after a startup grace period**
    (default 300 s, so nobody is shelled mid-alignment), lands a small dispersed `trigger.action.explosion`
    barrage near the parking centroid on a randomized cadence — mostly noise/smoke with a modest, tunable bite,
    not precision counter-air. Symmetric (whichever side's forward fields qualify). Plugin options: interval,
    rounds/event, dispersion, per-blast power, grace. **Generic artillery mode added 2026-07-05**: the new
    `artillery_base_harassment` setting (Mission Generation, default OFF) drives the same emitter+runtime
    with a tight `ARTILLERY_FRONT_REACH_M` (35 km — real gun range off the FLOT, vs the Vietnam siege's
    theater-wide 200 km), so conventional campaigns can put their frontline strips under fire; **Red Tide
    preseeds it** (the Fulda FARP + red's Haina both sit on the front — "the Gap is not a safe ramp").
    All §36 guarantees carry over (player-spawn exclusion, grace, forward-only, symmetric).
    **Plugin dependency (user-caught 2026-07-05): the runtime is the vietnamops PLUGIN** — a saved
    default of "Vietnam Ops" unticked silently kills the setting, so Red Tide also preseeds
    `plugins: {vietnamops: true}` (campaign plugins layer over saved defaults in the wizard), the
    plugin is renamed "Vietnam Ops & standoff harassment", and both toggles state the coupling;
    guard `tests/fourteenth/test_campaign_plugin_preseed.py`.
    (`game/missiongenerator/vietnamopsluadata.py`,
    `resources/plugins/vietnamops/`, `game/settings/settings.py`; features doc §36, checklist L8 — needs an
    in-game pass; the artillery mode = the L8 artillery bullet.)
37. **Super Gaggle hilltop resupply** — the sixth **Vietnam Ops suite** feature (design note
    `414th-vietnam-ops-notes.md`, §E): a formation of transport helos (+ a fast-mover AAA-suppression flight)
    runs supplies into a cut-off forward friendly outpost while the player can fly escort — the Khe Sanh "Super
    Gaggle." **Drawn from real BLUE squadrons + losses tracked, not a phantom spawn** (reworked 2026-07-01 to
    eliminate free airframes — the old `coalition.addGroup` helos were unaccounted units on an **unbounded
    respawn loop**, so losing them cost nothing). The gaggle is now planned once per turn from **real squadrons**:
    `plan_super_gaggle` (`game/fourteenth/super_gaggle.py`, run from `finish_turn`) picks the besieged BLUE
    FOB/FARP near a front + a rear launch field, a **real BLUE helo squadron** to fly the run + a **real BLUE
    attack squadron** for the suppressors, and records a `SuperGaggleCommitment` (persisted on the game: the
    squadrons + the exact per-airframe unit names + geometry). `_populate_super_gaggle` emits that commitment; the
    `vietnamops` plugin spawns **exactly those** airframes, by name, **once** (no respawn — airframes are bounded
    to the commitment). At debrief, `reconcile_super_gaggle` (`missionresultsprocessor.commit_super_gaggle`) charges
    each committed unit name found in the debrief's killed units back to its squadron (`owned_aircraft -= lost`,
    `destroyed_aircraft += lost`) — a **real airframe loss**, exactly like any other; survivors cost nothing (a
    returning detachment, so no pre-debit/return), and a delivered run credits the outpost a small ground-strength
    boost. No base-Lua / debrief-schema change: the spawned units already fire the DCS death events
    `dcs_retribution.lua` records, so their names land in the debrief killed lists (as untracked ground units,
    since they aren't in the `UnitMap`) and are matched by name. Fully guarded (feature off / no outpost / no
    launch / no helo squadron with airframes ⇒ no commitment ⇒ no node ⇒ plugin no-ops). Blue-only (symmetry
    deferred). Plugin options are speed/altitudes/launch-delay (type/count come from the squadrons). **Findability pass
    2026-07-02** (the "half-baked" complaint — "Escort welcome" with no location, so the run played out unseen
    unless the player was already over the launch field): the plugin now keeps **one live F10 map mark** on the
    lead helo, refreshed each poll and removed on delivery/loss (`markToCoalition`/`removeMark`), and the spawn
    cue reads "Marked on the F10 map"; the stale "re-rolling on a cadence" setting copy is corrected to the real
    single-run-per-turn behavior. **Launch-delay rework (2026-07-03):** a flown session found the whole run
    over by t≈306s — the spawn fired at mission-config load (t=0), before a cold-starting player could
    plausibly be airborne to escort it. The entire spawn (helos, suppressors, cue, F10-mark tick) is now
    wrapped in a local `spawnGaggle()` fired via `timer.scheduleFunction(..., timer.getTime() + DELAY)`
    instead of immediately; `DELAY` defaults to 600s (`gaggleDelaySec` plugin option). The "armed … launching
    in Ns" log line still fires immediately so ops get config confirmation without waiting. Same F10-hook bar
    as the naval-gunfire feature. (`game/fourteenth/super_gaggle.py`,
    `game/game.py`, `game/sim/missionresultsprocessor.py`, `game/missiongenerator/vietnamopsluadata.py`,
    `resources/plugins/vietnamops/`, `game/settings/settings.py`; features doc §37, checklist L9 — the
    2026-07-02 flown run passed, the 2026-07-03 launch-delay rework needs a re-fly.)
38. **FAC(A) willie-pete target marking** — the seventh **Vietnam Ops suite** feature: the iconic Vietnam
    forward air controller. An airborne OV-10 Bronco loitering over the battle area marks nearby enemy ground
    with **white-phosphorus smoke** so the player (and AI strikers) can visually acquire the target and roll in
    — the ground JTAC (which *lases*, stationary) already exists, so this is the distinct *airborne, smoke*
    half. Same shape as §33 flak (an on-marker + runtime discovery): Python emits only
    `dcsRetribution.VietnamOps.fac = { enabled }` (`_populate_fac`); the `vietnamops` plugin discovers airborne
    friendly units of the FAC type (default `Bronco-OV-10A`) at runtime and, on a cadence, drops white smoke
    (`trigger.action.smoke`, willie pete) on the target + a "cleared hot" cue. **Findability pass 2026-07-02**
    (the "half-baked" complaint — a bare unlocated "cleared hot" text, and the smoke was indistinguishable from
    the Bronco's own WP rockets): it now marks the **largest enemy ground concentration** in range (not whatever
    lone truck was nearest — `bestEnemyGround`), and lays a **named, live F10 map mark** at it (e.g. "FAC(A):
    BTR-60 x6 — willie pete, cleared hot", one per FAC unit, refreshed each tick via
    `markToCoalition`/`removeMark`) so the target is findable from anywhere and unambiguously the FAC (rockets
    make no F10 mark); the text names the target + points at the F10. Same F10-hook bar as the naval-gunfire
    feature. Symmetric (only OV-10 owners have FACs, so blue-effective in practice); needs a friendly OV-10
    airborne over the front, or it no-ops. Runtime-cosmetic (a marker, no gameplay-model change). Plugin
    options: FAC type, spot/mark range, mark cadence. (`game/missiongenerator/vietnamopsluadata.py`,
    `resources/plugins/vietnamops/`, `game/settings/settings.py`; features doc §38, checklist L10 —
    VERIFIED 2026-07-02, the named F10 mark confirmed in a flown session.)
39. **Snake and nape (napalm CAS)** — the eighth **Vietnam Ops suite** feature: the iconic low-level napalm
    CAS delivery ("snake" = Snakeye retarded bombs, "nape" = napalm). **Detonation-anchored (reworked
    2026-07-02)**: Python still emits only `dcsRetribution.VietnamOps.snakeNape = { enabled }`
    (`_populate_snake_nape`); the `vietnamops` plugin now hooks **`S_EVENT_SHOT`**, catches each **eligible
    retarded-bomb release** (weapon type name vs a comma-separated pattern option, default `SNAKEYE`) made
    from a qualifying **release profile** (≤ ceiling AGL + ≥ min ground speed — the "pressed in on the deck"
    gate), **tracks the weapon to impact** (`land.getIP` on the last sample, the Splash Damage pattern) and
    lays **one `trigger.action.effectSmokeBig` fire (auto-stopped after a burn time) + a modest
    `trigger.action.explosion` bite at each real impact point** — the wall of fire emerges from the actual
    ripple; a dry pass lays nothing, a miss burns where it missed; one cue per salvo. **Mk-77 fire bombs are
    excluded** (the locked Splash Damage build renders real napalm — no double-render). Unlike the flak
    gauntlet (which *punishes* predictable flight), this *rewards* pressing the CAS run in on the deck.
    Symmetric (any side's qualifying release; no aircraft-attribute gate — the ordnance is the eligibility).
    Plugin options: release ceiling, min release speed, `napeWeaponPatterns`, per-impact power (the v1
    proximity heuristic + its drop-range/swath/node options are retired).
    (`game/missiongenerator/vietnamopsluadata.py`, `resources/plugins/vietnamops/`,
    `game/settings/settings.py`; features doc §39, checklist L11 — needs an in-game pass.)
40. **Campaign phases (inferred arc + planner emphasis)** — every campaign (all 66, zero authoring) knows what
    *phase* of the air war it is in, the UI shows it, and the auto-planner biases its offensive intent to match
    (spec `414th-campaign-phases-notes.md`; this is its **P0+P1**, landed as Vietnam campaign layer W3). A
    turn-by-turn Tier-0 classifier (`game/fourteenth/phases.py`) reads live state via existing accessors —
    alive enemy long+medium SAM **sites** (TGO `GroupTask` LORAD/MERAD, the DEAD planner's own set — the
    #379-corrected banding, never `IadsRole`) vs. a lazily-snapshotted turn-0 `PhaseBaseline`, enemy
    air-superiority airframes, mean front movement, last turn's captures — and picks **Air Superiority →
    Interdiction → Offensive** with the pilot's **absolute-SAM-floor gate** (a genuinely belt-less theater
    skips Rollback — Shattered Dagger/Valley of Rotary et al., NOT Khe Sanh, which the generator fills with
    SA-2/SA-3), a peer-fight guard, min-dwell hysteresis, and monotonic-forward defaulting
    (regression is authored-only, P2). The active phase reorders **only the offensive middle** of
    `PlanNextAction`'s HTN root methods (BLUE only; the reactive prefix + tail are fixed — the §17 boundary),
    shifting which objectives get first claim on offensive jets. Always explains itself (§3.4 legibility:
    "Interdiction — enemy IADS 22% · air threat low · front static") on the kneeboard **cover-page band**
    (which also **spells the ROE out** — OFF LIMITS zones / LOCKED classes / CLEARED classes via
    `roe_summary_lines`) and
    a new **client campaign-status ribbon** (`CampaignStatusBar` over the map, fed by `GameJs.campaign_status`
    — which also carries campaign name/turn/date, previously never sent to the client, + the political-will
    meters on Vietnam campaigns). Gated by `campaign_phases` (default **ON** — [DECIDED] Tier-0 inference is
    the default; the toggle is the kill switch). **W4 added the authored tier (P2) + the ROE escalation
    layer**: a campaign `phases:` YAML block overrides Tier 0 (`parse_phases`/`authored_arc_for`, re-derived
    at load, never pickled) with `min_turn`-scheduled + `advance_when`-accelerated transitions
    (`blue_will_below` couples escalation to the will economy), **restricted zones** (AI planner gate
    `roe_blocks_target` in `PackagePlanningTask.fulfill_mission`, BLUE-only; sanctuary airfields fall out;
    the player is never hard-blocked — zone kills drain will via `count_roe_violations` +
    `BLUE_ROE_VIOLATION`), **target release** (`locked_targets` classes, RESTRICTED — ROE badge on the TGO
    tooltip instead of vanishing), a red dashed **map layer** (`GameJs.restricted_zones` →
    `RestrictedZonesLayer`, Enemy intel group, default ON), and the authored **Rolling Thunder → Bombing
    Halt → Linebacker → Linebacker II arcs in all 4 Vietnam campaigns** (Kutaisi/Sukhumi/Saipan play Hanoi
    per laydown; the Yankee Station/Steel Tiger coastal-ladder recast also keeps a permanent Tbilisi "PRC
    border" ring in every phase). **The 2026-07-02 legibility pass** made the *dynamics* readable:
    **transition transparency** (the arc expander spells out how the arc leaves each phase — authored
    `advance_when` with live values on the current phase, Tier-0 classifier thresholds otherwise), the P2
    **objectives checklist** (`PhaseObjective` + `done_when` live ticks; Tier-0 built-ins + `objectives:`
    authored in the 4 Vietnam arcs; `PhaseCondition` gains `red_resolve_below`/`capture_cp`, usable in
    `advance_when` too), the **will-attribution ledger** (`political_will.py` `WillLedgerEntry` on
    `Game.will_ledger`, capped 60 — labeled per-feed movers surfaced on the meter hover, the expander
    notes, the SITREP "Will movers" lines, and the per-turn message; the instrument for the M1 pacing
    pass), and a **pre-flight ROE warning** in the Qt package dialog (`update_roe_warning` via
    `roe_restriction_reason` — never blocks, just prices the choice). **The 2026-07-02 ROE-zone-shape rework
    (Path A)** generalized restricted zones from circle-only to `RestrictedZone.kind` = `circle | box |
    corridor` (a rotatable rectangle for the "Nevada box"/Route-Package rectangles; a shapely
    buffered-polyline lane for ingress routes/the Ho Chi Minh trail), parsed by `_parse_restricted_zone` (a
    legacy `{center, radius_nm}` block still parses to a circle byte-identically — the 4 Vietnam arcs are
    unchanged). One `ResolvedZone.contains` (shapely for box/corridor, distance for circle) gates both the
    planner and the will-penalty; the zones are now **painted into the generated `.miz`'s F10/ME map**
    (`DrawingsGenerator.generate_restricted_zones` — `add_circle` / `add_freeform_polygon` of the outline,
    alongside the always-on frontline/route/CP drawings) and the web layer draws a `<Circle>` or `<Polygon>`
    by kind (both share `active_restricted_zones`, so cockpit map == web map). **Path B (2026-07-03) LANDED** —
    a `restricted_zones` entry can be `{from_drawing: "<name>"}`, hanging the zone off a shape the author
    *drew* in the campaign `.miz`'s Mission Editor instead of typed coordinates: `game/fourteenth/zone_drawings.py`
    (`read_zone_drawings`) normalizes the loaded mission's drawings into named `DrawnZone`s (v1: Circle → circle,
    FreeFormPolygon → polygon; Rectangle/Oval/TextBox/unnamed skipped — Rectangle/Oval convention unverified,
    the polygon tool covers box/corridor), `MizCampaignLoader.populate_theater` stashes them on
    `theater.zone_drawings` (pickled, getattr-guarded for old saves), and `_resolve_drawing_zone` builds the
    same `ResolvedZone`. Real `.miz` write/reload/read probe-verified. **Free-fire zones (2026-07-03) LANDED —
    inverted ROE, the COIN kill boxes**: a phase authoring `free_fire_zones` (same shape system) flips the
    polarity — the whole map goes **weapons-hold for fixed strikes** except inside the pockets (the OIR
    Blue-Kill-Box model, per the Rampagers reference). Gate adds "outside the weapons-free area" for a
    class-carrying target outside every pocket (front-line/convoys never gated; a `restricted_zone` still
    carves a no-strike hole inside a pocket); `count_roe_violations` counts kills outside the pockets;
    `roe_summary_lines` leads with a WEAPONS FREE row; painted dashed **green** (vs red restricted) on both
    the F10/ME map and the web layer (`GameJs.free_fire_zones`). The free-fire capability stays in the engine,
    but the **COIN campaign no longer uses it** — see the ROE-shape note below. (`game/fourteenth/phases.py`,
    `game/fourteenth/zone_drawings.py`, `game/theater/conflicttheater.py`,
    `game/campaignloader/mizcampaignloader.py`, `game/game.py`,
    `game/commander/tasks/compound/nextaction.py`, `game/commander/tasks/packageplanningtask.py`,
    `game/fourteenth/political_will.py`, `game/missiongenerator/kneeboard.py`,
    `game/missiongenerator/drawingsgenerator.py`, `game/server/game/models.py`,
    `game/server/tgos/models.py`, `client/src/components/campaignstatus/`,
    `client/src/components/restrictedzones/`; features doc §40, checklist M3 + M4 + M7 + M8 — need an in-game pass +
    the CI client rebuild.)
    **COIN ROE-shape rework (2026-07-03):** replaced the COIN campaign's earlier 9 town-ring restricted
    circles + whole-map free-fire inversion with **4 big box/corridor no-strike "positive-control valleys"**
    over the real populated river valleys (2 corridors — the Helmand Green Zone Kajaki→Marjah and the Musa
    Qala 611 feeder; 2 boxes — the Tarin Kowt bowl and the Delaram junction), shared by all three phases via
    the `&population_centers` YAML anchor. The invisible free-fire inversion is **dropped entirely** (no
    `free_fire_zones` in any phase) — the open desert and the northern gate are simply unrestricted, and a
    fixed strike inside a valley prices CDE into the mandate (violation weight 1.0, pressure not taboo); trail
    convoys / TIC are never gated and air assaults (captures) are never blocked, so the arc still retakes its
    objectives. Exercises both the box and corridor `RestrictedZone.kind` shapes; CI-locked in
    `test_enduring_resolve_campaign_definition` (4 zones/phase, no free-fire).
41. **High Digit SAMs "Ultimate Compilation" support** — the HDS mod support retargeted from the abandoned
    original v1.4.0 to the maintained successor (https://github.com/dcs-sams/HighDigitSAMs-Ultimate-Compilation,
    v1.4.3+), same `high_digit_sams` toggle (wizard label updated). Unit data read from the **installed mod's
    own Database luas**. Absorbs the breaking changes — renamed S-300PS radars (`30N6 MAST tr`/`76N6E sr`/
    `64H6E MOD sr`) re-pointed in the S-300 Site layout + SA-10B preset + `radar_db.py`; dropped HDS
    KS-19/SON-9/SA-24 replaced by vanilla equivalents (retired pydcs classes + unit YAMLs kept as save-compat
    tombstones ONLY — never reference them) — and adds the new families: **S-400/SA-21 + S-300V4 + S-300PT**
    presets on the extended S-300 Site, **SAMP/T** (+NG) on a new Patriot-geometry `SAMP/T Battery` layout,
    **Pantsir-SM** SHORAD, **SA-7/7b manpads**, 4 EWRs (the **P-37 Bar Lock** closes the period red EWR
    blind-net gap across 16 factions), ERO **ZU-23 Toyota technicals** for insurgents. Era-respecting stock
    faction wiring (modern Russia/redfor, france_2005, 70s-80s Middle-East/NK reds get SA-7/7b, Vietnam reds
    the P-37 only — SA-7s dropped from the 4 Vietnam factions per squadron call — insurgents the technicals). MANTIS needs no
    change (the bridge bands SAMs by Retribution's emitted threat range, not MANTIS's unit-name scan). Fixed
    in passing: `Faction.remove_vehicle` matches DCS type **ids**, and the old name-based HDS strips silently
    never removed anything (upstream-carve candidate). (`pydcs_extensions/highdigitsams/`,
    `game/data/radar_db.py`, `game/factions/faction.py`, `resources/{groups,layouts,units,factions}/`;
    features doc §41, checklist N1 — needs an in-game pass.)
42. **Local DCS chart base layers (map tiles)** — locally installed XYZ tile pyramids appear as extra
    base-map choices in the map layers panel (§19), so the campaign map can show a chart of the *DCS*
    terrain (e.g. Flappie's "accurate DCS Caucasus map" GeoTIFF) instead of mismatching real-world Esri
    imagery. Purely local, never bundled (community-chart copyright): `tools/tile_geotiff.py` (standalone
    Pillow, no GDAL) slices an EPSG:3857 GeoTIFF into `Saved Games/Retribution/MapTiles/<name>/{z}/{x}/{y}.png`
    + a `tileset.json` sidecar; game-independent `/map-tiles` routes list/serve whatever exists there
    (traversal-safe name/int params); `MapLayersControl` fetches the list once and adds one segmented
    base-map button per set (`local:<name>`, persisted like the stock choices, Clarity fallback when tiles
    vanish). No Settings toggle — on-disk content is the switch. (`tools/tile_geotiff.py`,
    `game/persistency.py` `map_tiles_dir`, `game/server/maptiles/`,
    `client/src/components/maplayers/MapLayersControl.tsx`; features doc §42, checklist O1 — needs an
    in-app pass + the CI client rebuild.)
43. **Per-aircraft flight defaults (save fuel + properties)** — the Edit-flight → **Payload** tab's aircraft
    knobs (Internal Fuel, Aircraft Condition, Wear & Tear, Spawn Type, and any other property-editor value)
    are re-seeded from the pydcs engine defaults on every new flight, so a player who wants their F/A-18C to
    always spawn hot with 80% fuel had to redo it each package. This adds a **"Save as default"** (+ **"Clear
    default"**) button to that tab that remembers the current fuel + properties **per airframe**, so every new
    flight of that type opens pre-configured — the same persistence the loadout dropdown already has (its
    "Save Payload" button) and the player laser code already has (a campaign-wide setting; this covers the
    *rest* of the box). A JSON store keyed by DCS aircraft id
    (`game/persistency.py` `flight_defaults_path()` → `Saved Games/Retribution/flight_defaults.json`), written
    from the tab and applied in `Flight.__init__` after `initialize_fuel()` — **only for a genuinely fresh
    flight (`roster is None`) on the BLUE coalition** (`coalition.player.is_blue`, never enemy AI, never a
    clone that already carries member edits), fuel clamped to the airframe tank, every step a best-effort
    silent no-op (missing/corrupt store, no entry, headless test). No Settings toggle — on-disk content is the
    switch, like the payloads files; it applies to BLUE AI flights of the type too (intended — "default for
    this aircraft"). (`game/fourteenth/flight_defaults.py`, `game/persistency.py`, `game/ato/flight.py`,
    `qt_ui/windows/mission/flight/payload/QFlightPayloadTab.py`; features doc §43, checklist Q1 — needs an
    in-app pass.)
44. **Long-range carrier ops** — a deterministic carrier strike package for campaigns that park the boat
    far beyond the auto-planner's reach. Enduring Resolve stands the carrier ~800 km off the Helmand AO (the
    real OEF Arabian-Sea cycle); the stock plane range gate (`Squadron.capable_of` vs `max_mission_range_planes`)
    hard-rejects every carrier squadron at 400-500 NM, so the Hornets, the A-6 tankers, and the E-2 all sat on
    the deck while the land air fought the whole war. Two-part fix: the campaign preseeds a wider
    `max_mission_range_planes` so the carrier air is *assignable* (the commander then flies spare Hornets on
    SEAD), and `plan_carrier_strike` (`game/fourteenth/carrier_ops.py`, gated `long_range_carrier_ops` default
    OFF, campaign-preseeded, BLUE only) frags **one** package a turn from the boat's own squadrons — a Hornet
    **STRIKE** section (`STRIKE_SECTION_SIZE`) + an A-6E tanker + an E-2 on AEW&C — pinned via
    `ProposedFlight.preferred_type` and forced through the range gate with `ignore_range=True` via the engine's
    own `PackageFulfiller` (proper flight plans, waypoints, fuel, shared TOT). The tanker + E-2 ride as
    **primary** package flights, not escorts: `EscortType.Refuel` is a dead end (`check_needed_escorts` never
    marks refuel "needed" so an escort tanker always prunes), and an AEWC escort prunes the same way — as
    primaries the A-6 gets a tanker orbit off the boat (launch + recovery gas) and the E-2 an AEWC orbit. The
    hook runs in `Coalition.plan_missions` **before** `TheaterCommander` so the boat's Hornets are claimed for
    this package first; `_nearest_legal_strike_target` picks the nearest alive, non-ROE-blocked enemy TGO
    (preferring ammo caches — the COIN throttle). A **second post-planning pass**
    (`route_carrier_flights_to_buddy_tanker`, run **after** `TheaterCommander`) fixes the boat's *other* carrier
    flights: the commander frags SEAD Sweep/Escort Hornets off the deck in their own tanker-less packages, whose
    stock REFUEL waypoint lands at the package's far end (~500+ NM from the A-6, no tanker there). The pass pins
    each such carrier flight's refuel point onto the A-6's held orbit (`Flight.refuel_point_override`, honored by
    the 3 refuel-waypoint builders via `Flight.refuel_waypoint_position`), so they tank from the boat's own held
    tanker on their launch/recovery route — mirroring `reposition_theater_tankers` but pinning the *receivers* to
    the pinned buddy tanker instead of moving a theater tanker. Guarded at every step (no carrier / no Hornets /
    no legal target / no buddy tanker ⇒ no-op). (`game/fourteenth/carrier_ops.py`, `game/coalition.py`,
    `game/ato/flight.py`, `game/ato/flightplans/{formationattack,tarcap,escort}.py`, `game/settings/settings.py`,
    `resources/campaigns/coin_enduring_resolve.yaml`; features doc §44, checklist P2 — needs an in-game pass.)
45. **Support-package F10 orbit markers** — at generation, each **blue tanker + AEW&C** orbit is painted onto
    the F10 / Mission-Editor map as a **cyan dashed racetrack + a label** (callsign · type · radio freq · TACAN),
    so a pilot can find their tanker/AWACS in the cockpit — the reliable, **DTC-free** answer to "where's my
    gas?". `DrawingsGenerator.generate_support_orbits` reads `MissionData` (populated by `generate_air_units`
    *before* the drawings pass): it matches each `REFUELING`/`AEWC` blue `FlightData` to its `TankerInfo`/
    `AwacsInfo` (by `group_name`) for the freq/TACAN label, pulls the racetrack ends from the flight's
    `PATROL_TRACK` (start) + `PATROL` (end) waypoints, and draws an `add_oblong` capsule (or `add_circle` if the
    ends coincide) + an `add_text_box` label. Always-on like the other map drawings (no toggle — a possible
    follow-up); no-op when no `mission_data` is passed. `MissionData` is now threaded into `DrawingsGenerator`.
    (`game/missiongenerator/drawingsgenerator.py`, `game/missiongenerator/missiongenerator.py`; features doc
    §45, checklist R1 — needs an in-game pass.)
46. **Route-aware fuel-tank top-up** — at mission generation, adds drop tanks to a flight's **empty,
    tank-capable stations** when its planned route needs more fuel than internal (plus any tanks already on the
    loadout) can cover — so far-AO campaigns fly with enough gas (the motivating case: the COIN Enduring Resolve
    carrier sits ~800 km off the Helmand AO, so a Hornet Strike always comes out with its **third bag** on the
    empty centerline). **Deliberately conservative — it never removes a store.** Weapon *type* data can't tell a
    self-defense Sidewinder from a primary JDAM (both resolve to `WeaponType.UNKNOWN`), so a "swap low-value
    ordnance for a tank" step can't be made safe by default (it would risk stripping a TGP/ECM pod/bomb) — so
    only **empty** tank stations are filled; a fully-loaded jet (e.g. the F-16, whose only free tank station
    holds ECM) is left untouched. `add_range_fuel_tanks` (`game/fourteenth/range_fuel.py`) runs in
    `flightgroupconfigurator.setup_payload` **after** the date-degrade, **before** the pylons are equipped:
    `_required_fuel_lbs` (taxi + cruise·route-NM + reserve, from the airframe's measured `fuel_consumption` or
    the synthesised `estimated_fuel_consumption` that every airframe has — tankers on the route are ignored, we
    over-fuel rather than under-fuel) vs. `_available_fuel_lbs` (internal `max_fuel` + parsed capacity of tanks
    already carried); short → return unchanged, else fill empty tank stations (matching a tank already on the
    jet, else the largest compatible) until the requirement clears or no stations remain. Fuel tanks are
    detected by DCS display-name (no fuel-tank `WeaponType`; a narrow regex so a "Color Oil Tank"/fuel-air bomb
    is never mistaken for a drop tank) and their capacity parsed from the name (gallons/liters/kg). It returns a
    new `Loadout` for the `.miz` and **never mutates the persisted ATO loadout** (re-evaluated each turn as
    routes move; saves untouched), skips **player-customised** loadouts (`is_custom` — explicit edits are
    honored) and empty/clean loadouts. Gated by `auto_range_fuel_tanks` (Mission Generation → Loadouts,
    **default ON** — inert on short routes where internal + stock tanks already cover the leg). Tests
    `tests/fourteenth/test_range_fuel.py` pin the safety contract (never removes/replaces a store) against the
    real F/A-18C pylon tables. (`game/fourteenth/range_fuel.py`,
    `game/missiongenerator/aircraft/flightgroupconfigurator.py`, `game/settings/settings.py`; features doc §46,
    checklist S1 — needs an in-game pass.)
47. **Continuous campaign clock & weather** — a stock turn re-rolled time and weather from scratch: the
    time-of-day rotated through a fixed Dawn→Day→Dusk→Night slot cycle (one slot/turn) with the actual clock a
    **random hour inside that band** (so consecutive turns teleported ~4–8 h), the date ticked only every 4
    turns (`start_date + turn // 4`), and weather was an **independent, memoryless draw** each turn (thunderstorm
    → clear → rain, no fronts). Nothing carried forward, so a campaign never read as one timeline. This ties
    date, time-of-day, and weather to **one marched clock** anchored to the campaign's start date. Two levers:
    (1) `Conditions.advance` carries `start_time` forward a jittered **3–7 whole hours** each turn
    (`MIN/MAX_TURN_ADVANCE_HOURS`; a sortie+turnaround, whole hours keep the "starts on the hour" property),
    **derives** time-of-day from the marched clock (`daytime_map.best_guess_time_of_day_at`), and rolls the date
    at midnight — the season (weather table + temp/pressure) updates as the calendar marches; (2)
    `generate_weather(previous=...)` → `_evolve_weather_type`, a **Metropolis-Hastings** step on the
    `_WEATHER_LADDER` (Clear→Cloudy→Rain→Storm): a near-rung *proposal* from `_WEATHER_PERSISTENCE_KERNEL`
    (`{0:3, 1:1, 2:0.3, 3:0.1}`) *accepted* against the seasonal chances, so systems move through gradually
    **and the long-run marginal stays exactly the seasonal climatology** (a plain seasonal×kernel reweight —
    the first cut — autocorrelates but skews the mix toward calm, measured halving Caucasus-summer rain 9.9→4.7%;
    MH keeps the skew ≤~1pp; a zero seasonal chance stays unreachable). `Game.continuous_clock_active` gates it (`continuous_campaign_clock`
    setting **and** `night_day_missions == DayAndNight` — day-only/night-only opt out of the natural cycle and
    fall back to the rotation); `current_day`/`current_turn_time_of_day` become authoritative off
    `self.conditions` when active (getattr-guarded for the turn-0 seed), else the legacy formulas; `finish_turn`
    calls `advance_conditions()` for `turn > 1`. **Seamless mid-campaign** on load: the last conditions were
    generated from the `turn // 4` date, so `conditions.start_time.date()` already equals it — the clock reads
    the same date and marches on (no jump, no migration). Composes with campaign phases (§40), which advance
    over turns; the calendar now advances in step. Gated `continuous_campaign_clock` (Campaign Management →
    Campaign clock & weather, **default ON**). Tests `tests/weather/test_continuous_campaign_clock.py`.
    (`game/weather/conditions.py`, `game/game.py`, `game/settings/settings.py`; features doc §47, checklist T1
    — needs an in-game pass.)
48. **Commitment ceiling (will-coupled war budget)** — the capstone of the **2026-07-04 "morale ratchet"
    will-economy redo** on 1968 Yankee Station (design note `414th-vietnam-political-will-roe-notes.md` §8),
    which rebuilt the whole political-will layer around the canonical *Vietnam 1965-1975* wargame model: BLUE
    Political Will is a near-one-way **ratchet** (war weariness + a per-turn **POW running-sore** — the one lever
    the GCI-ambush enemy has to pressure Washington — with restores too small to grind a win, so *body count is a
    trap*); RED Regime Resolve is **broadened past the trail** (`red_ground_unit_lost` up so CAS/BAI/**Arc Light**
    all bleed it, the campaign-ending convoy weight trimmed 1.5→1.0); an **escalation tax**
    (`CampaignPhase.blue_will_on_entry`, charged once per phase entry via `phases.consume_phase_escalation_cost`
    into the will ledger — Linebacker −3, the Linebacker II "Christmas bombing" −5) makes *widening the war* cost
    Washington will even when sanctioned (an elite player who folds Hanoi early never pays it); and a **richer
    opening** (`red_tempo.trail_surge 1.5` under Rolling Thunder — 15-truck convoys from turn 1). This feature
    itself is the **commitment ceiling**: as BLUE will falls below 60, `Coalition.end_turn` scales the BLUE war
    budget down linearly toward a 0.5× floor (`game/fourteenth/commitment_ceiling.py` `will_budget_multiplier` /
    `apply_commitment_ceiling`) — a losing war is starved of replacements (the VG "commitment can't exceed
    morale"), gentle by design (full funding above 60, the floor never zeroes procurement), BLUE-only, gated
    `vietnam_commitment_ceiling` (default OFF, preseeded ON) **and** `vietnam_political_will`. The numbers were
    derived offline with `tools/will_pacing_model.py` (a standalone projector marching both meters over the arc
    from play archetypes; its default weights are drift-guarded against the real `WillWeights`): elite folds
    Hanoi ~turn 8, average rides to a Linebacker II negotiated win ~turn 16, a floundering war loses Washington
    ~turn 11. (`game/fourteenth/commitment_ceiling.py`, `game/coalition.py`, `game/fourteenth/phases.py`,
    `game/fourteenth/political_will.py`, `game/settings/settings.py`, `resources/campaigns/1968_Yankee_Station.yaml`;
    features doc §48, checklist M1 + M9 — needs an in-game pass.)
49. **Mobile missile relocation (the SCUD hunt)** — mobile theater-missile sites (SCUD/SSM TGOs,
    `category == "missile"` — **never** the MANTIS-run SAM network, coastal sites, or buildings) drive
    **shoot-and-scoot** during the mission: the new emitter `game/missiongenerator/mobilemissileluadata.py`
    lists each side's live vehicle-carrying missile sites (`dcsRetribution.mobileMissiles`), and the new
    `resources/plugins/mobilemissiles/` plugin relocates every alive group to a fresh point within the
    scoot radius (4 km) of the site's **campaign-map centre** every ~8 min (alarm-green + weapons-hold,
    startup grace 120 s) — so the launcher is never quite where the last recon photo froze it, and with §3
    concealment on, the SCUD hunt is finally a hunt. **Movement only** (the Combat-SAR/COIN mover
    discipline): kills record natively, the site never migrates past its scoot radius (threat rings + the
    turn model stay honest), a dead site stops being routed. Symmetric. Gated `mobile_missile_relocation`
    (Mission Generation → World & systems, default **ON** — the toggle is the kill switch, the §40
    precedent). Tests `tests/missiongenerator/test_mobilemissileluadata.py` +
    `tests/lua/test_mobilemissiles_runtime.py`; features doc §49, checklist S2 — needs an in-game pass.
50. **Convoy escort / ambush** — the **mirror of the §35 interdiction**: where interdiction gives the
    player *enemy* convoys to hunt, this gives the player *friendly* convoys to **protect**. Real, tracked
    BLUE supply convoys run the roads behind the front, and concealed, real RED ambush teams dig in along
    their route; left un-escorted the ambush wears a convoy down and the supplies never arrive, so the player
    flies CAS/BAI to clear the ambushers and get the column through. **No phantom spawns** (the §35/§37
    lesson): the convoy is a real `coalition.transfers` transfer (its loss = units that never arrive,
    reconciled in `commit_convoy_losses`, which already iterates *both* coalitions' convoys) and each ambush
    team is a real, **concealed** (§3) red TGO placed by `spawn_red_ground_at` (killing it is a real red
    ground loss recorded natively) — so both sides' losses count and the Lua plugin owns **no** kills.
    `game/fourteenth/convoy_ambush.py` runs three steps: `ensure_blue_escort_convoy` (the symmetric analog
    of `ensure_enemy_trail_convoy` — reuses that module's coalition-generic corridor/seed/skim helpers to top
    the player's own convoy flow up to a small budget so an escortable convoy reliably exists — "spawn more
    blue convoys") + `seed_convoy_ambushes` (despawns last turn's ambush teams, then drops a small
    `AMBUSH_TEAM_SIZE` concealed red TGO on a **mid-route waypoint** of each active blue convoy, recording the
    pairing on `game.convoy_ambush_state`), both from `finish_turn` after the enemy-trail top-up; and
    `plan_convoy_escort` (from `Coalition.plan_missions`, **before** the commander so it claims its jets
    first) which **auto-frags one BAI escort package per ambushed convoy** onto the ambush TGO via the
    engine's own `PackageFulfiller` (`FlightType.BAI` is the tasking the commander itself uses against a
    vehicle group — `PlanBai`/`PlanConvoyInterdiction`), so the escort exists in the ATO and the AI flies it
    if the player doesn't. The emitter `game/missiongenerator/convoyambushluadata.py`
    (`dcsRetribution.convoyAmbush`) lists each live pairing's ambush-team group names + centre + the escorted
    convoy's group name, and the new `resources/plugins/convoyambush/` plugin **springs** the dug-in team:
    alarm-green/weapons-hold until a convoy unit closes inside the trigger radius (6 km) — then weapons-free +
    a "TROOPS IN CONTACT" cue + an F10 mark; a team no convoy reaches opens up after a max hold so a passing
    player still finds a fight, all after a startup grace. **ROE/cue only** — the firefight is reconciled in
    the turn-boundary force model, so a mover shot down is recorded natively (the §35/§37/§49 discipline).
    Gated `convoy_ambush` (Mission Generation → Battlefield life, default **OFF**), preseeded ON + the plugin
    preseeded ON (the §36 saved-default-off lesson) in COIN Enduring/Inherent Resolve, 1968 Yankee Station,
    and Red Tide. **A blue→blue supply road is the hard prerequisite** (2026-07-05 flown-test finding: both
    COIN campaigns shipped all-red graphs, so the escort convoy silently never existed) — the blue rear
    corridors are now geo-authored per the driveable-corridor standard (`tools/supply_route_geo.py`: ER
    Kandahar↔Camp Bastion up Highway 1, the literal ambush alley; IR Baghdad↔Balad + Baghdad↔Al-Taquddum;
    the tool gained the `iraq_inherent_resolve` mode) and CI-locked by
    `test_preseeded_campaigns_have_a_blue_to_blue_road`, which loads every preseeding campaign's theater.
    Tests `tests/fourteenth/test_convoy_ambush.py` +
    `tests/missiongenerator/test_convoyambushluadata.py` + `tests/lua/test_convoyambush_runtime.py`; features
    doc §50, checklist S3 — needs an in-game pass.
51. **Enemy comms jamming (IADS comms nodes)** — the IADS comms nodes, given a voice: with
    `enemy_comms_jamming` on, every alive enemy `comms`/`commandcenter` TGO (the same C2 objects the MANTIS
    degradation graph watches) floods the BLUE side's **briefed** channels with duty-cycled barrage noise via
    `trigger.action.radioTransmission` from the node's map position — real DCS power/distance falloff, and
    **SRS users hear it through their cockpit-tuned radios**, so no SRS-server dependency exists (the
    ExternalAudio path was considered and dropped). Python owns the plan (`plan_comms_jam` →
    `MissionData.comms_jam`, computed before the Lua pass): a positive-list of targets — intra-flight channels
    (human-crewed first) + blue AWACS, GUARD defensively filtered, capped at 10 — **never ATC/ATIS/tankers by
    construction**, plus a freshly-allocated **JAM BACKUP** UHF channel (unjammable because nothing else uses
    it) printed on the kneeboard comms ladder and echoed in the first-burst cue. The `commsjam` plugin steps on
    only ~3 channels per jittered burst cycle (rotating window — switching channels is real comms discipline),
    rotates the transmitting node across alive jammers, and uses the MANTIS `node_dead` positive-evidence
    convention (destroyed static / `dead_events`) so a culled node stays "alive" (unkillable this mission =
    standing pressure to frag it next turn). **The intel gate is the default mode** (`comms_jam_requires_capture`,
    default ON — squadron call 2026-07-06): red can only jam channels it *knows*, learned from a **captured
    aircrew's comms plan** via the §15/§21 Combat SAR capture race — the plugin stays dormant until either a
    live capture (`combat_sar_captures` poll → "AIRCREW CAPTURED" cue → bursts after a `captureReactionS`
    exploitation delay) or a POW held whose comms plan is still exploitable (`pending_pow_recoveries`
    captured within `COMMS_COMPROMISE_TURNS` → `activeFromStart`, the "COMMS COMPROMISED" story; freeing the
    POW or the compromise window lapsing ends it — time-boxed off the POW's `captured_turn` so an
    indefinitely-held POW doesn't jam forever). Win the SAR race and
    the net stays clean; gate off = ambient always-on-while-node-alive. **Audio pressure only** — no
    force-model change, the plugin owns
    no kills: silencing the jamming is an ordinary IADS strike with its MANTIS C2 consequence untouched. Gated
    `enemy_comms_jamming` (Mission Generation → Battlefield life, default **OFF**), preseeded ON + the plugin
    preseeded ON (the §36 saved-default-off lesson) in Red Tide. Tests
    `tests/missiongenerator/test_commsjamluadata.py` + `tests/lua/test_commsjam_runtime.py`; features doc §51,
    checklist S4 — needs an in-game pass.

---

## Repo & Branch Layout

- This repo (`bradyccox/414Ret`) `main` = the consolidated, most-up-to-date 414th build.
- Upstream is `dcs-retribution/dcs-retribution`; the 414th's PR fork is
  `bradyccox/dcs-retribution`.
- The 414th's primary "all features" working branch in the dev checkout is
  `414th-all-features`; `main` here = that + the Iran pack + a Black/mypy lint pass.

### Upstream PR ledger (snapshot 2026-06-27 — re-verify with `gh pr list`, don't trust this stale)

Carved out of this work, against `dcs-retribution/dcs-retribution` (all authored by `bradyccox`):

- **Open (awaiting review):**
  - [#854](https://github.com/dcs-retribution/dcs-retribution/pull/854) per-squadron DCS country for nation-specific voiceovers + nation-aware pilot names (§23) — resolves upstream issue [#627](https://github.com/dcs-retribution/dcs-retribution/issues/627). Ports `CountryAssigner` + `pilotnames.py` + both test files verbatim; the §23 wiring hunks re-applied to upstream `missiongenerator.py`/`aircraftgenerator.py`/`squadron.py` (the fork's QRA `spawn_intercept_templates` is NOT upstream, so only `generate_flights`+`spawn_unused_aircraft` take the assigner). Pretense is standalone/overrides the touched methods → unaffected. NO 414th content (Iran faction wiring stays fork-side). §23 was NOT previously in the carve queue. Black/mypy/pytest/ts all green — opened 2026-07-03.
  - [#851](https://github.com/dcs-retribution/dcs-retribution/pull/851) High Digit SAMs **Ultimate Compilation** support (§41's generic core) — retargets the HDS toggle to the maintained mod: renamed-radar re-points, retired-unit tombstones, the 42 new units + 7 presets + SAMP/T layout, and the `remove_vehicle` id-vs-name strip fix. NO 414th faction enrichment (P-37/SA-7/S-400 wiring stays fork-side). Validated headless against upstream dev — opened 2026-07-01. Landed on the fork as [414Ret#382](https://github.com/bradyccox/414Ret/pull/382).
  - [#847](https://github.com/dcs-retribution/dcs-retribution/pull/847) F-4E-45MC (Heatblur) loadout rebuild **+** Maverick date-fallback fix — all 13 F-4E presets re-sourced from the module's built-in loadouts (period AIM-7E2/9L A2A baseline vs the old all-modern AIM-7M), **and** the AGM-65 family's date-fallback rerouted AGM-62 Walleye → Mk-20 Rockeye (Mavericks were degrading to Walleyes on pre-1972 campaigns). Data-only (2 files), validated headless against upstream (CLSID-resolve + station-legal + task-resolution + weapon-DB load) — opened 2026-06-28; **consolidates the former #845 + #846**. Landed on the fork as [414Ret#322](https://github.com/bradyccox/414Ret/pull/322) + [#325](https://github.com/bradyccox/414Ret/pull/325).
  - [#843](https://github.com/dcs-retribution/dcs-retribution/pull/843) era-gate payload-editor options: JHMCS property gating (§24) + targeting-pod era data (re-does withdrawn #786) (carve queue item 11) — opened 2026-06-27. **Druss99 CHANGES_REQUESTED addressed 2026-06-29**: helmet-cueing dates moved to `resources/aircraftproperties/helmets/*.yaml` (mirroring the weapons era model, per his ask) + extended to Soviet HMS/SURA Visor & A-10C HMCS; CI green. ⚠️ **Owes a reviewer re-request** — Druss99 is NOT in the re-request list, so the PR sits blocked with no signal for him to re-review.
  - [#842](https://github.com/dcs-retribution/dcs-retribution/pull/842) landmap prepared-index perf (carve queue item 1) — opened 2026-06-27.
  - [#828](https://github.com/dcs-retribution/dcs-retribution/pull/828) recon fog-of-war (§3) — the flagship carve, mergeable.
  - [#806](https://github.com/dcs-retribution/dcs-retribution/pull/806) configurable cruise/patrol altitude.
  - [#805](https://github.com/dcs-retribution/dcs-retribution/pull/805) bulk waypoint altitude UI — Druss99's CHANGES_REQUESTED **addressed** (verified 2026-06-29): `DIVERT`/`TARGET_POINT` + `REFUEL`/`RECOVERY_TANKER` (and target-group/ship, pickup/dropoff, cargo-stop, bullseye) now in the `BULK_ALTITUDE_SKIP_TYPES` skip-list. Druss99 **re-requested** — awaiting his re-review; no further action owed.
  - [#794](https://github.com/dcs-retribution/dcs-retribution/pull/794) hide mobile SAM in combined groups (§7).
  - [#792](https://github.com/dcs-retribution/dcs-retribution/pull/792) wind override UI.
  - [#791](https://github.com/dcs-retribution/dcs-retribution/pull/791) SAM site layouts + EWR pool.
  - [#788](https://github.com/dcs-retribution/dcs-retribution/pull/788) inflight final-waypoint crash (§8).
  - Several created mid-June show `mergeable: UNKNOWN` — **likely need a rebase on current `dev`**.
- **Merged:** [#841](https://github.com/dcs-retribution/dcs-retribution/pull/841) plugin `descriptionInUI` field (§14) · [#793](https://github.com/dcs-retribution/dcs-retribution/pull/793) building-card placeholder (§4) — both came back with the 2026-07-05 upstream/dev sync merge · [#826](https://github.com/dcs-retribution/dcs-retribution/pull/826) weapons coverage/repairs · [#789](https://github.com/dcs-retribution/dcs-retribution/pull/789) inverted OPFOR aggressiveness fix.
- **Self-withdrawn (NOT rejected, NOT upstream):** [#784](https://github.com/dcs-retribution/dcs-retribution/pull/784) Iran pack · [#786](https://github.com/dcs-retribution/dcs-retribution/pull/786) AAQ-33 era restriction · [#790](https://github.com/dcs-retribution/dcs-retribution/pull/790) orbit deconfliction. The Iran pack and AAQ-33 fix are therefore **still fork-only** — re-carve if wanted.
- **Era-gate payload options — DONE (opened 2026-06-27 as #843):** the combined **"era-gate payload-editor options"** PR = JHMCS property gating (§24) **+** a redo of the withdrawn #786 AAQ-33 pod fix. Self-contained, no 414th deps, builds on the upstream `restrict_weapons_by_date` toggle; Black/mypy/pytest validated locally before push. See upstreaming-inventory item 11.

**Crowded upstream zones — do NOT carve into these without coordinating** (active non-414th PRs):
- Planning revamps — prokop7 [#676](https://github.com/dcs-retribution/dcs-retribution/pull/676) BARCAP, [#674](https://github.com/dcs-retribution/dcs-retribution/pull/674) SEAD/DEAD, [#678](https://github.com/dcs-retribution/dcs-retribution/pull/678) BAI, [#677](https://github.com/dcs-retribution/dcs-retribution/pull/677) attack-infra.
- QRA — geofffranks [#782](https://github.com/dcs-retribution/dcs-retribution/pull/782) (our reserve *feeds* this; don't resubmit).
- Frontline — geofffranks [#823](https://github.com/dcs-retribution/dcs-retribution/pull/823) (already adopted into the fork), Druss99 [#681](https://github.com/dcs-retribution/dcs-retribution/pull/681).
- SEAD — geofffranks [#772](https://github.com/dcs-retribution/dcs-retribution/pull/772).
- Kneeboard — geofffranks [#754](https://github.com/dcs-retribution/dcs-retribution/pull/754) (wait for it to land before carving §25/§27/§29).
- ATC — fully saturated ([#821](https://github.com/dcs-retribution/dcs-retribution/pull/821)/[#692](https://github.com/dcs-retribution/dcs-retribution/pull/692)/[#564](https://github.com/dcs-retribution/dcs-retribution/pull/564)/[#568](https://github.com/dcs-retribution/dcs-retribution/pull/568)); the 414th retired its ATC, so nothing to give here.

---

@docs/dev/CLAUDE-ci.md

---

## PINNED — do not modify

**`latest` git tag** — owned by `softprops/action-gh-release@v2` inside `414th-latest.yml`.
Do NOT delete it or manually push it — breaking it breaks the URL the squadron bookmarks.

**`414th-latest.yml`** — the sole rolling-release mechanism. Do NOT modify it without
understanding the impact. Test in a branch and verify the `latest` release after merging.
Do NOT add Discord webhook or other org-level secrets — the workflow uses only `GITHUB_TOKEN`.

**Local Python runtime** — before deleting anything under `tmp/`, inspect `.venv/pyvenv.cfg`.
The current Windows virtual environment may have
`home = ...\tmp\uv-python\cpython-3.11.15-windows-x86_64-none`; when it does,
that `tmp/uv-python` directory is the base interpreter for `.venv`, **not a disposable
cache**. Deleting it breaks `run_retribution.bat` with "No Python at ...". Either preserve
the directory or rebuild `.venv` against a permanent Python 3.11 installation first.
Cleanup scripts and agents must never recursively delete `tmp/` without this check.

**`resources/plugins/splashdamage3/Splash_Damage_3.4.2_414th.lua`** — the 414th's
buddy-tuned Splash Damage build (`overall_scaling=0.6`, `rocket_multiplier=0.8`,
`static_damage_boost=1`, shaped-charge rocket flags, `game_messages=true`). Do NOT overwrite
it from upstream. Settings are LOCKED by design: `plugin.json` has no `specificOptions` and
`sd3-config.lua` was removed. Don't reintroduce the config layer.

---

## Conventions

- **Highlight questions to the user.** Whenever you need a decision or answer from the
  user, make the question visually prominent — never bury it mid-paragraph or at the tail of
  a wall of prose. Put it in its own block at the **end** of the message, set off with a bold
  marker and a blockquote, e.g.:
  > ❓ **Need your call:** <the question>

  When you offer choices, **number them (1, 2, 3, …)** and lead with your recommended option,
  so the user can reply with just a number. List multiple questions as a short numbered set so
  each can be answered individually. Use **plain highlighted markdown only** (bold + blockquote)
  — do NOT build a widget or visualization for this. (The `AskUserQuestion` tool already renders
  prominently and satisfies the convention; otherwise it is for free-text questions in ordinary
  replies.)
- **Supply lines follow the driveable corridor (STANDARD, 2026-07-03).** Every authored
  `supply_routes:` / shipping-lane drawing must trace the corridor you would actually *drive*
  between the two points — the road, the river valley, the pass — never a straight line across a
  ridgeline. Retribution binds a route to its CPs by the **first and last** waypoint only, so
  intermediate waypoints are free: use enough of them (3–5) to follow the real corridor. On
  real-world-coordinate maps (Afghanistan, Syria, Sinai, PG, Kola, Normandy, Caucasus…) author the
  intermediates from the **real road network's lat/lon** via `tools/supply_route_geo.py`
  (`Point.from_latlng` → terrain XY; calibrated to ~1–5 km on Afghanistan). For fictional-overlay
  campaigns (e.g. Vietnam-on-Caucasus) trace the on-map roads/valleys visually instead. The tool is
  **multi-campaign** (`python tools/supply_route_geo.py [coin|red_flag_81_2|caucasus_trail_fixes]`);
  the COIN campaign (`coin_enduring_resolve.yaml`, Highway 1 / Route 611 / the Uruzgan road) and Red
  Flag 81-2 (`red_flag_81_2.yaml`, real US-95 / US-6 / the NTS interior) are the reference
  implementations. The built campaigns were audited against this standard 2026-07-03 (see the
  supply-routes design note "Roll-out to the built campaigns"): Nevada re-traced, the worst
  Caucasus-trail defects fixed, the deep-mountain trail FOBs (Yankee Station / Steel Tiger R6–R13)
  left for an in-app by-eye pass, Germany already compliant.
- Match the surrounding code's style; run the three validation commands (in `CLAUDE-ci.md`) before pushing.
- Keep the doc faces in sync: when a feature lands or changes, update **both**
  [`README.md`](README.md) (player-facing) and the relevant section of
  [docs/dev/414th-features.md](docs/dev/414th-features.md) (engineering), plus this map if the
  shape changed. A push that moves the code past its docs is a broken push.
- Keep player-facing plugin behavior and any overview docs in sync with code changes.
- **AGENTS.md sync** — `AGENTS.md` is a byte-identical mirror of this file (CLAUDE.md is
  authoritative; only line 1, the title, differs). After editing CLAUDE.md or any `@`-imported
  file, resync it: `cp CLAUDE.md AGENTS.md` then Edit line 1 back to `# AGENTS.md ...`
  (do NOT use `sed -i`; it flattens CRLF). The imported files (`docs/dev/CLAUDE-architecture.md`,
  `docs/dev/CLAUDE-ci.md`) are shared — both CLAUDE.md and AGENTS.md reference the same files.
