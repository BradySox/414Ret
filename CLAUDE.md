# 414Ret — Claude Code Guide

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
- [docs/dev/414th-early-systems-decision-ledger.md](docs/dev/414th-early-systems-decision-ledger.md) —
  the **2026-07-18 deep-audit verdicts** on the early-systems core (bar: "changes decisions in
  play"), with the empirical self-play evidence (`tools/system_probe.py` — the reusable probe
  harness: ignore-cost vs engage-payoff per system, intervention scripts, gate step-throughs).
  Headlines: cache throttle measured 4:1, re-infiltration flip verified end-to-end, IED
  ignore-cost ~1.8 mandate/turn, §50 ambush a silent no-op on both COIN campaigns (blue
  convoys never run), the ER trail an unbounded +20 armor/turn pump, concealment
  amber-blankets strongholds (9 circles on Tarinkot). No kills recommended; the 4 squadron
  calls were decided + shipped same day (garrison-skim blue columns, trail destination cap,
  HVT escape priced, and the concealment **density cloud** — per-member circles whose
  stacked stroke-less fills darken where units bunch, `TgoJs.concealed_cluster_size`;
  the first-cut identical-geometry merge was reworked off the flown squadron feedback).
- [docs/dev/414th-feature-debt-register.md](docs/dev/414th-feature-debt-register.md) — the
  **verification plan / debt register** (2026-07-15 look-back at ~600 commits): the triage of
  every half-cooked item and exactly where it gets verified — the pre-regen action items, the
  post-regen **app-side sweep**, the **Aug-1 M2 fly-card**, the mid-window private-session card,
  the Vietnam/COIN/SP queues, the rework-invalidated ledger, and the deliberate-deferrals list.
  Archive once the Aug-1 wave is processed.
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
  - `414th-red-tide-campaign-notes.md` — Red Tide campaign laydown + `.miz`/faction edits.
    **🔒 FEATURE LOCK effective FRIDAY NIGHT 2026-07-17** (user correction 2026-07-12 — the
    earlier "locked 2026-07-11" was the intent, not the date): until the Friday-night
    regeneration (new build + a turn 1 processed from the M1 session JSON), new features and
    Red Tide preseeds MAY land; from then on, no new features/laydown/balance (bug fixes +
    in-game-pass verification + tuning-to-intended still OK); the banner atop that note is
    the source of truth. **S-300 regiment restructure 2026-07-12 (landed pre-lock; recorded
    at the time as a lock-override go-ahead):** the three rear S-300 hubs
    (Sperenberg/Kastrup/Schönefeld) were restructured into **3-battalion regiments +
    shared EWR** (the reference implementation of the SAM-belt STANDARD) — single-radar battalions
    via the `Russia 1980 (Red Tide)` faction fork (§60 reverted for RT's S-300/SA-5 only; front
    legacy SAMs keep §60 doubling). NEW game required; tests in `test_red_tide_sam_regiments.py`.
    **Lock-override #2 same day (user call off the roster era-audit):** the fork faction gained the
    **SA-15 Tor + SA-19 Tunguska** (era-correct '86/'82) so the regiments' point defense can actually
    intercept ARMs under the MANTIS SHORAD link (G30) — red's roster was otherwise IR-only SA-9/13 +
    the Osa, none of which DCS tasks against missiles. Roster otherwise audited era-clean vs July
    1988; guards in `tests/fourteenth/test_red_tide_faction_era.py`. NEW game required.
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
  - `414th-tanker-war-campaign-notes.md` — **Persian Gulf "The Tanker War (1988)"** (the 1987–88
    Gulf-shipping war built to an Operation Praying Mantis climax on the WRL Noisy Cricket Redux
    geography: US Navy 1985 CVW vs Iran 1988 + an Iraqi Exocet flavor; ships-not-territory via
    the warship will feed, an authored phase arc + shipping-lane ROE corridor, coastal Silkworm
    sites (fire-window missions only — vanilla Silkworm hardware is §49-immobile, so it fires
    but never scoots), and AAA gun forts on the 15 oil platforms. Phases 1–3 BUILT +
    headless-verified 2026-07-07; laydown CI-locked in `tests/fourteenth/test_tanker_war.py`;
    registered 2026-07-18 (the maintenance sweep found it shipped silent — no checklist row or
    docs entries); in-game pass = checklist T2, the platform-AAA on-deck render the riskiest bit)
  - `414th-desert-storm-campaign-notes.md` — **Iraq "Umm al-Ma'arik (Desert Storm 1991)"**
    (the DM's homemade DS91 campaign fixed + modernized + promoted 2026-07-19: the KARI IADS
    as the Red Tide static-trio pattern (ADOC + 3 SOCs + relays at every red base + a P-37/1L13
    EWR chain, MANTIS range-mode, 86 nodes), the Great Scud Hunt (7 authored Scud batteries ×
    §49), a 10-route real-highway supply graph (`tools/supply_route_geo.py` mode
    `iraq_desert_storm`), the Instant Thunder → Scud Hunt → ground-offensive arc with a
    permanent Baghdad no-strike circle, the Coalition-cohesion will profile, and the
    Dictator-universe scenery names inherited from the Aladeen miz renamed to the real 1991
    CENTAF target set. Fixed in passing: 6 silent squadron substitutions (a missing yaml list
    marker had dissolved the whole MiG-25 squadron) and the escort-starvation blue OOB; the
    NATO Desert Storm faction gained the A-10C Suite 7 + CH-47F Block I the DM authored
    (era-clamped by the date-gate preseeds). CI-locked in `tests/fourteenth/test_desert_storm.py`;
    in-game pass = checklist T3. NEW game required)
  - `414th-red-tide-supply-routes-notes.md` — YAML supply routes + Kastrup preset patch
  - `414th-comms-jam-notes.md` — enemy comms jamming off the IADS comms nodes (§51): why the
    in-game `radioTransmission` path beat SRS injection, the anti-grief guardrails, tuning levers
  - `414th-iads-c2-consequences-notes.md` — the IADS C2 family beyond comms (§52 Feature A LANDED —
    command-center kills degrade enemy planning; Feature B power→radar-blackout is mostly MANTIS
    already + legibility, deferred; records why datalink/GPS jamming is NOT feasible in DCS)
  - `414th-cruise-missile-raids-notes.md` — ship-launched cruise missile raids (§63 LANDED
    2026-07-15): the no-rearm campaign magazine debited only by the debrief report, emitter-time
    raid planning, the curated LACM hull set, and the deferred Tier-3 right-click/SITREP surfacing
  - `414th-comint-notes.md` — **blue-side COMINT** (§70, the §51 mirror; all 5 squadron calls
    RESOLVED 2026-07-18 — keep ambient tier · pin reveal · collectors = C-130 + drones ·
    UHF-first band plan off the DF-module audit (Hornet/Tomcat/Phantom/Tiger all home,
    F-16/A-10 listen-only) · CW beeps v1). **The full C0–C2 arc LANDED 2026-07-18** =
    feature §70: C0 the campaign take, C1 the audible UHF red net (`rednet` plugin), C2 the
    clandestine stations (concealed COIN spawns transmit on the hunt schedule) + the
    kneeboard active-nets listing; the authored static field-site TGO stays deferred until
    a campaign wants the loader convention
  - `414th-carrier-deck-decor-notes.md` — **carrier deck decorations** (§72): the OCN 2
    extraction, the Tacview-measured parking-spot anchors + safe-envelope rationale,
    what was dropped and why, and the non-Nimitz-hull deferral
  - `414th-red-flag-81-campaign-notes.md` — **Red Flag 81-2 Nevada campaign** (real-exercise study +
    laydown + the Vietnam-mechanics wiring; the `.miz` is GENERATED by `tools/build_red_flag_81_2_miz.py`
    — edit the laydown tables there and re-run, never hand-edit the miz; laydown RE-POINTED 2026-07-02
    at the commercial 81-2 reference miz set (note §3a: raw-Lua cross-mission clustering — SA-6/SON-9/
    SA-8 joined the red faction, KS-19/Fire Can flak belts, 4 mock airfields, the Smoky belt as SHORAD;
    NEW game required); loader gotcha found in passing, **FIXED 2026-07-12**: `MizCampaignLoader` read
    ships/SAM/EWR/missile/coastal markers from the RED country block only (a blue-block marker silently
    dropped — 22 authored markers across 7 campaigns never generated) and bound markers to the nearest
    CP coalition-blind (Red Tide's "414th Red EWR 1" landed on blue Frankfurt and never spawned). The
    loader now walks the BLUE block for every marker class and binds blue-block markers to the nearest
    BLUE CP; red-block markers keep nearest-any proximity — the convention by which blue defenses are
    authored as red-block markers near blue fields. Tests `tests/test_miz_marker_binding.py`;
    upstream-carve candidate. **SCOPED + BOUNDED 2026-07-17** (found debugging Red Tide's "why blue"
    save): #590's blue-CP preference was unbounded and applied to EVERY object class, but the blue
    block also holds the **economy** objects (armor/factories/ammo/strike, authored blue-side by
    convention) — so 782 red economy objects across the campaigns were re-owned to distant blue fields
    (Sperenberg's factory → Frankfurt 408 km away; every red ammo depot → a blue base across the map).
    The preference is now **scoped** to the marker classes it was written for (`objective_info`'s
    `prefer_blue` param, passed only by the SAM/EWR/missile/coastal/ship/offshore callers) and
    **bounded** by `MizCampaignLoader.BLUE_BLOCK_MAX_DETOUR` (50 km): a blue-block marker prefers the
    nearest blue CP only when it isn't dramatically farther than the marker's nearest field (legit
    near-field markers like Dynamo's evacuation flotilla ≈30 km stay; a marker sitting on an enemy
    base 55–420 km from any blue field binds by proximity). Economy classes bind by pure proximity,
    byte-identical to the pre-#590 baseline)
  - `414th-campaign-maker-notes.md` — blank-start campaign maker (**landed through Increment D**,
    not "in progress": the wizard's "Build your own (blank canvas — experimental)" entry →
    all-airfields-neutral map paint (left/right-click cycles gray→blue→red) → **Finalize**
    (prunes unpainted bases, derives fronts, seeds air defenses + economy, staffs airwings) →
    play → **Save as Campaign** (a `.miz`-less `blank_canvas` YAML that reloads from the New
    Game list). Create/paint/finalize app-verified 2026-06-24 (checklist BC-A/B/C + the BC-D
    build half); still owed = the fly-side rows (BC-D fly, BC-E/F/G/H) + the deferred D.4
    polish (layout fidelity, FUEL/OIL round-trip, squadron presets, `base.armor` inventory
    seeding))
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
    client) + `uncertainty_radius_m` (4 km), and the web map draws a dashed amber "suspected
    activity" circle (amber since the §28 UI audit — dashed red is ROE-only) with the marker's
    click/right-click contract (frag TARPS/CAS onto it);
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
| In-mission framework | **MOOSE** (bundled `Moose.lua`; some plugins vendor classes verbatim) — the standard. **MIST is RETIRED** (MIST → MOOSE consolidation complete, 2026-06-25): `base/plugin.json`'s `"mist"` work-order now loads `resources/plugins/base/mist_moose_shim.lua` — a vanilla-DCS shim implementing the 44 `mist.*` symbols the consumers (CTLD, SCAR, intercept glue, core `dcs_retribution.lua`, and the upstream land/water relocate scripts) actually call, so `mist_4_5_126.lua` no longer loads. **When merging upstream Lua, grep it for `mist.` — a symbol the shim lacks dies at runtime, not in CI** (the 2026-07-05 sync needed a new `mist.getGroupData` for `land_relocate.lua`/`water_relocate.lua`, checklist U1; the 2026-07-10 sync's escort-leash fix needed `mist.DBs.groupsById` — the rule keeps catching real ones). The old `mist_4_5_126.lua` file was **deleted 2026-07-10** (the final cleanup — the shim flew clean across campaigns, checklist G7); rollback = restore it from git history and re-point `plugin.json`'s `"mist"` work-order at it. Do NOT re-point the work-order without reason. See `414th-mist-moose-shim-notes.md`. MOOSE API docs (bookmark): https://flightcontrol-master.github.io/MOOSE_DOCS_DEVELOP/Documentation/index.html |
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
   **QRA forward defense** (2026-07-09, `qra_forward_defense` default ON + `qra_defense_depth_nm`):
   `SetGciRadius` is ONE radius measured from EVERY base, so widening it to let rear fields answer a
   raid at the front equally lets the front field chase deep into enemy airspace. The two are split by
   giving each dispatcher a **border zone** — `SetBorderZone(zones)` → `Detection:SetAcceptZones`, which
   makes Moose **drop any detected object outside the zones**, so a side literally cannot see (scramble
   against, or keep engaging) a target beyond its own airspace. Geography then bounds *where* a side
   fights, and `SetGciRadius` bounds only *how far a base launches* (opened to `QRA_FORWARD_REACH_NM`
   = 200 NM). **`SetDisengageRadius` must open with it** (Moose aborts a defender past
   `DistanceFromHomeBase > DisengageRadius`, default 300 km ≈ 162 NM) or the far fields launch and turn
   around — the non-obvious half. A wide reach does NOT mass-launch: Moose's GCI loop picks the
   **closest** eligible squadron and only reaches back when its alert is spent (front field answers,
   rear fields backfill). Zones = one circle per non-neutral, non-`OffMapSpawn` CP at
   `qra_defense_depth_nm` (60), a front anchor's grown to `dist(cp, front) + 25 NM` — the only place a
   side's airspace crosses the line. `depth == qra_gci_max_radius_nm` makes it **non-regressive** (the
   union of circles == the old per-base GCI set). An **ambush doctrine wins outright** (Vietnam's late
   40 NM slash is never widened), and the **player scramble cue keeps the narrow radius**
   (`min(reach, setting)`) so a human alert flight isn't cued for bandits 200 NM out. Emitter
   `defense_zone_entries` → `dcsRetribution.Intercept.ZONES`; empty ⇒ Lua skips `SetBorderZone` ⇒
   pre-feature behaviour. Checklist A5 — needs an in-game pass (the accept-zone release of an
   already-engaged defender, and whether the 150 NM transit really flies, are DCS-only unknowns).
   **PR #782 drift port (2026-07-16)**: the Moose `FilterPrefixes` Lua-pattern escape lands in
   `intercept-config.lua` — parenthesized IADS group names never matched, so QRA detection was
   riding the paren-free backstop EWRs ONLY; the escape (the mantis `escape_prefix` fix) opens the
   real EWR network (fold into the A5 fly). QRA now also scrambles **only against air-to-ground
   taskings** (Strike/BAI/OCA-Runway/OCA-Aircraft/Anti-ship/Armed Recon — no DEAD/Air Assault;
   parsed from the group name, whose first `|`-field now keeps the task even for custom-named
   flights), the PLAYER_ALERT cue stays deliberately task-blind, reserve edits hit the planner
   pool live (`Squadron.set_intercept_reserve` through all five writers, spinners capped at the
   unplanned airframes, clamped by the §53 fuel-readiness ceiling + re-clamping
   `qra_player_manned`), and a cratered runway fields no QRA (templates, cue, and the base-card
   count all suppressed until repair).
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
   **The tag-along never paces the package (2026-07-19 fix, the flown Scenic kneeboard "times and
   speeds are getting weird")**: `Package.formation_speed` min'ed over EVERY formation plan — the
   TARPS drone included — so an MQ-9 riding a 4-Hornet DEAD package dragged every formation leg to
   ~169 kt (kneeboard GSPD 161, a 34-min egress) and the structural-vs-forward clock drift ate the
   hold dwell (hold departure before arrival, join before nav, a −725 kt row).
   `Package.formation_speed` now skips a non-primary TARPS flight (a pure recon package still paces
   its escort to the drone), both formation `speed_between_waypoints` sites cap each flight at its
   own capability (the excluded drone keeps its own 169-kt schedule; no-op for real members), and
   the kneeboard guards non-positive leg times with "-". Headless-verified on the flown save: the
   package re-plans at 422 kt (the AV-8B, the slowest real member), positive hold dwell, monotonic
   rows, TOT untouched. Same-day follow-up: the divert/bullseye kneeboard rows drop Time/GSPD
   entirely (reference steerpoints, not flown legs — the chained ETA past the landing point is
   "if you kept flying after landing" noise; Fuel already blanked these rows). Tests
   `tests/ato/flightplans/test_formationattack.py` +
   `tests/missiongenerator/test_flightplan_fuel_column.py`.
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
   unstacked FLOT units. **A front anchor is never abandoned** (2026-07-09):
   `ObjectiveFinder._offensive_roll` still lets OPFOR abandon a *rear* CP to free fighters
   for offense, but never a CP holding the FLOT — on a single-front theater the roll deleted
   the only CAP over the front (Red Tide: Haina, the sole anchor and the theater's densest
   orbit at 2 threat-weighted rounds, abandoned ~1 turn in 5, leaving red's whole BARCAP
   layer 126–188 NM behind the FLOT around Berlin).
7. **Auto-hide mobile SAMs on MFD** — SHORAD/AAA/MANPAD hidden from datalink, including
   escorts inside armor/missile groups; standalone MERAD/LORAD stay visible for SEAD.
8. **Robustness / crash fixes** — flight-exit IndexError, AWACS/tanker orbit, malformed mod
   payload Lua. **AI helo terrain CFIT trio (2026-07-12, the flown Red Tide M1 finding):** helo
   cruise waypoints now use the previously-dead `heli_cruise_alt_agl` (not the combat AGL), long
   AI-helo RADIO legs are subdivided with ≤5 NM "TERRAIN" re-anchor points
   (`MAX_HELO_ANCHOR_SPACING` in `waypointgenerator.py` — DCS interpolates straight between AGL
   waypoints, so 40–110 km treetop legs were commanded through the Harz ridge lines), and both
   air-start spawner paths stamp `unit.alt_type` (pydcs leaves units "BARO", and DCS spawns from
   the unit record — a 500 m-AGL intent spawned 500 m MSL below a 600 m FARP). Upstream-shared;
   checklist C8. **Carrier-recovery stagger (2026-07-16, the flown Scenic Route midair):** DCS
   flies the whole carrier pattern itself (no mission-authored approach leg exists — the last
   waypoint is a `Land` task ON the boat), so two AI packages sent into the same recovery window
   converged co-altitude in the DCS overhead and collided 2.7 NM from CVN-71 (blue's only losses
   of the mission). `MissionScheduler._deconflict_carrier_recoveries` now spaces same-boat
   package landings ≥ `CARRIER_RECOVERY_INTERVAL` (5 min) apart by delaying TOTs — only "spread"
   AI packages move; player/CAP/AEW&C/SCAR/ASAP packages claim their recovery slots as FIXED
   entries the movable ones space around (the human's recovery is never rescheduled), and the
   recovery-tanker ETAs are collected after the stagger so tankers time against the real
   landings. Always-on (no setting — arrival-time-only, like the §62 modex). Upstream-shared;
   checklist C9.
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
    rescue package (**1 King (C-130) + helo(s) + 2–4 Sandy**) is now **player-planned** off the FLOT —
    the auto-fragged standing orbit is retired (§21 on-demand rework 2026-07-06), so the AI-spawn path
    fields the helo only (an on-demand Sandy clone is the §21 v2). A **player-package AI-crewed** Sandy
    is still **dynamically diverted** at runtime
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
    to save, or the pilot is **CAPTURED** (`combat_sar_captures` state global) and held as a **POW**.
    **Hardened 2026-07-09** (diagnosed from a user hang): the snatch party is REAL infantry on
    DCS's single scripting/sim thread, so `capturePartySize`/`captureTeams` are **hard-clamped at
    load** (≤ 12 infantry / ≤ 4 teams) — a saved 40/4 override had spawned 80 soldiers across two
    ejections on a heavy Red Tide map and hung the sim (log stopped mid-`GetVec3` flood, no crash
    dump) — and the survivor ledger now **drops dead references** (`advanceCapture` prunes killed
    teams + reads via a first-alive-unit helper; `tick` reaps a ground-killed pilot via the
    designed-but-unused `dead` state) to kill the MOOSE dead-object poll flood. Test
    `tests/lua/test_combatsar_capture_cap.py`; no save/`.miz`/New-Game requirement. A capture holds the pilot as a **POW**
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
    Rescue is **player-plannable** (King + helo + Sandy off the FLOT) or an **on-demand AI helo**
    (`auto_combat_sar`, **default ON**) — no more standing orbit (§21 on-demand rework).
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
21. **Combat SAR** — pilot-rescue flight type (`FlightType.COMBAT_SAR`): a rescue helo (CH-47/UH-1)
    + a C-130 "King" (air-tracking **TACAN-only** beacon — no ADF — + F10 LARS survivor-locator) +
    a Sandy (SCAR, §15) escort, driven at runtime by the plugin's **survivor ledger** (`combatsar`
    plugin). **Two ways rescue happens (on-demand rework 2026-07-06):** (1) the player **plans their
    own package** off the FLOT (`FrontLine.mission_types` offers COMBAT_SAR + SCAR — a C-130 + helo(s)
    + A-10 Sandys, human or AI-crewed seats), or (2) with **no player package fragged**, the runtime
    **spawns an on-demand AI rescue** when a pilot goes down — sourced, in preference order, from
    (a) a **real untasked rescue helo already parked cold on the ramp** (`_spawn_unused_for`, in the
    `UnitMap`) — started in place and flown into the OPSTRANSPORT pickup, so it's a **tracked**
    airframe whose loss is recorded — else (b) a **cold late-activation clone template**
    (`AircraftGenerator.spawn_combat_sar_templates`, the QRA-reserve pattern) SPAWN-cloned as the
    fallback when the ramp is bare (perf toggle / fully-tasked wing; the clone is untracked). Both go
    straight into the pickup (the clone-into-mission path that works). **The retired standing orbit**
    (auto-fragged `PlanCombatSar` + the commandeer-an-**airborne**-helo dispatch) is **removed** — the
    orbiting helo never reliably flew the pickup (checklist G21); commandeering a *parked* helo instead
    of an *airborne, already-routed* one is the fix. The gate (**narrowed 2026-07-15**, squadron call off the flown
    Red Tide M1 where one bare player Sandy escort silently disabled ALL rescue): only a
    **rescue-capable** player flight — a CSAR **helo** — suppresses the AI spawn ("we've got it
    covered"); a bare Sandy or King can't pick anyone up, so it **draws** the AI helo and
    escorts/tracks it; nothing fragged ⟹ AI spawns. `auto_combat_sar` (**default ON**) drives the on-demand spawn, not an orbit. **Emit
    contract:** `dcsRetribution.CombatSAR` carries `autoSpawn` (bool) + `parkedHelos` (preferred) +
    `heloTemplate`/`farp` (fallback) when auto-spawning, alongside `pilotTemplate`/`rescueHelos`/
    `kings`/`sandys`. **Testing aids (2026-07-09):** the enemy snatch-party spawn default dropped **2 NM
    → 0.75 NM** so a capture can complete in a mission window (the 2 NM march ⇒ captures ~never fired),
    plus two **default-OFF** test toggles (Campaign Management → HQ Automation) emitted as scalar flags on
    the node — `combat_sar_test_force_capture` (`testForceCapture`: every ejection → a fast guaranteed
    **capture → POW**, unlocking the §51 capture-gated comms jam; the reliable way to exercise G28 + S4)
    and `combat_sar_test_easy_rescue` (`testEasyRescue`: capture off + forgiving pickup/delivery; exercises
    G10 King / G23 Sandy / the pickup loop). The plugin applies them after the normal options (force-capture
    wins if both set); OFF ⇒ node unchanged. **Non-combatant capture race (2026-07-17 night-fly fix):**
    the first at-scale run (12 snatch parties) captured NOBODY — DCS infantry ballistics resolved every
    race before the capture dwell could (the M249 survivor outguns AK teams; teams that closed shot the
    survivor dead). Both the survivor group and every snatch team now spawn **ROE weapons-hold +
    alarm-green** (`setNonCombatant`; the survivor via the MOOSE spawn's real `#001` group name), so the
    capture clock + airpower against the party decide the race, never small arms; garrison units near the
    ejection can still kill an evader. Pinned in `tests/lua/test_combatsar_ledger.py`.
    **Persistent evaders + the always-run snatch (2026-07-10,
    squadron call — the flown jamming test found "no rescue asset ⇒ the plugin skips entirely", which
    silently killed the snatch race + the capture→POW→§51 chain + even the emitted force-capture flag):**
    the blue node is now **always emitted** (the player-package/auto-spawn early-return is gone) and the
    plugin's ledger runs with **zero rescue capability** (`canRescue` only shapes the MAYDAY — "no rescue
    assets available. Protect the survivor!"); a pilot nobody can come for is MORE capturable, not immune.
    An un-rescued, un-captured survivor goes **MIA** instead of dying (`combat_sar_persistent_pilots`,
    default ON): the plugin mirrors unresolved survivors into the new `combat_sar_survivors` state global
    → `record_downed_pilots` (`game/fourteenth/downed_pilots.py`) flips the aviator to the new
    `PilotStatus.MIA` + banks them on `game.downed_pilots` → next mission the emitter hands the ledger
    back (`persistentSurvivors`) and the plugin re-spawns each evader at his last position (fresh smoke,
    "EVADER" cue, fresh 50% snatch race, normal rescue paths). At every turn boundary
    (`resolve_downed_pilots` from `finish_turn`) an evader on friendly ground **walks home**; behind the
    lines he rolls a **depth-weighted capture** — 10% within 5 NM of the front, linearly to **90% at
    40 NM+** (the *don't-fly-deep* incentive; a hit is the normal POW chain, with the ledger resolving
    the pilot in `record_pow_captures`). **Deliberately no death clock** — the roll is the clock.
    Surfaced on the SITREP band ("MIA: … — evading near … (N turns down)") + the squadron roster +
    **the campaign map (2026-07-18)**: a default-ON "Downed pilots" layer (`DownedPilotJs` →
    `client/src/components/downedpilots/`) draws each MIA evader rescue-orange at his last known
    position and each POW gray at the holding field, so the host plans the rescue from the map; the
    gate covers only *creation* of MIA entries so a mid-campaign toggle never strands an evader.
    Checklist G29. **Pilot recovery surge LANDED 2026-07-17** (the flown Scenic Route Merged finding —
    "after 1.4 h the rescue helos are just getting to the pilots": both on-demand paths fired live
    (3 parked Khasab UH-60s launched, the clone flew) but survivors sat 115–370 km from the rescue
    sources, so nothing arrived before mission end; same-mission rescue cannot beat helo transit):
    the **next turn opens with the recovery op already airborne**. `plan_pilot_recovery_surge`
    (`game/fourteenth/csar_surge.py`, hooked in `Coalition.plan_missions` BEFORE the commander —
    "drop everything") frags ONE coordinated package at a `PilotRecoveryZone` centred on the MIA
    evaders — required Jolly + optional second Jolly/King/2-ship Sandy/A2A escort — via the engine's
    own `PackageFulfiller` (ASAP, `ignore_range`), and the existing `PackageBuilder` rule
    **air-starts** AI COMBAT_SAR flights, so the op is on station at mission start and the package
    helo suppresses the on-demand clone. **Gate: once per downed pilot** (`DownedPilot.surge_turn`
    stamp — a failed surge falls back to the normal paths, never re-surges on later turns), so it is
    an event, not a fixture. Gated `combat_sar_surge` (default ON,
    `enabled_when=combat_sar_persistent_pilots`; the five CSAR settings moved to their own Campaign
    Management → "Combat search & rescue" section). Tests `tests/fourteenth/test_csar_surge.py`;
    checklist G31. **Rescue scoring closes the loop:** delivering a downed pilot to a friendly field
    spares the aviator at debrief (airframe still lost) — the plugin's `OnAfterBoarded`/`OnAfterRescued`
    hooks append the ejected unit name to `combat_sar_rescues`, and `commit_air_losses` skips that
    pilot's kill (fail-safe: empty list = pre-scoring behaviour). **v2 (deferred):** on-demand Sandy +
    King launches (a Sandy needs the payload configurator pass, a King its TACAN-beacon setup — neither
    a parked untasked airframe nor a cold template carries those) and multi-survivor chained pickup
    ("grab the other guy on the way"). The parked-helo *start-in-place* runtime path (`StartUncontrolled`
    + OPSTRANSPORT) is the fly-critical unknown; it degrades to the proven clone if it misbehaves.
    Distinct from the shelved POW-recovery raid (§15). (`game/ato/flighttype.py`, `game/missiongenerator/aircraft/aircraftgenerator.py`,
    `game/missiongenerator/luagenerator.py`, `game/sim/missionresultsprocessor.py`,
    `game/fourteenth/downed_pilots.py`, `game/squadrons/pilot.py`,
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
24. **Date-gated aircraft properties** — era-defining payload-editor *properties* gated by campaign
    date, under their **own `restrict_props_by_date` toggle** (2026-07-15, split from
    `restrict_weapons_by_date` off the upstream #843 review — enforce either or both). Curated
    gates: **JHMCS** (F/A-18C + F-16C, ~2003), **Scorpion HMCS** (A-10C II, ~2012), **HMS**
    (MiG-29, 1983) — hidden from the dropdown and clamped to the baseline visor at generation.
    The era data lives **in each aircraft's own data file** (a `date_gated_properties` block in
    `resources/units/aircraft/<type>.yaml` — pydcs carries no property dates) and loads into
    `AircraftType.property_date_gate`, one frozen `PropertyDateGate` (zero globals); keyed by value
    *label* so a pydcs rename degrades to "not gated" (a label-pin test catches it) — SURA Visor
    dropped, no pydcs airframe exposes it (the Su-30 is a mod). UI filters the dropdown; the
    generator (`degrade_props_for_date`) is authoritative and resolves against the unit-type
    default so the defaulted-JHMCS case is caught. (`game/dcs/aircraftproperties.py`,
    `game/dcs/aircrafttype.py`, `game/missiongenerator/aircraft/flightgroupconfigurator.py`,
    `qt_ui/windows/mission/flight/payload/propertycombobox.py`; features doc §24, checklist I3.)
25. **Compact 3-4 page kneeboard deck** — RETIRED (2026-07-05, the kneeboard back-to-basics rework):
    the compact folding machinery (`compact_kneeboard`, `_compact_kneeboard_pages`, the
    `CombatIntelPage`/`CommsCoordPage`/`FlexReferencePage` composites, `_draw_section_if_fits`, the
    adaptive flex page) was the fork's biggest `kneeboard.py` churn vs upstream and is deleted. The
    **2026-07-13 back-to-upstream rework** (§30/§31 retirements) finished the arc: the deck is now
    upstream's page set (Mission Info → Support Info → Notes → task page + the setting-gated extras)
    with the kept 414th info folded into those pages; the colour palette + the threat cards survive
    (`generate_threat_intel_kneeboard` default ON). The fuel ladder is **folded into the
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
    `client_flights_by_airframe` + `_build_index_page` + `KneeboardIndexPage`. (Was briefly a section on
    the §30 cover page; standalone again since the 2026-07-13 back-to-upstream rework.)
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
    features doc §28, checklist K1.) **Dependency greying + detail summarisation (2026-07-10, UI
    audit follow-up):** `OptionDescription` gained a keyword-only `enabled_when=(master, value)` (bare
    `"master"` ⇒ `(master, True)`; normalized by `normalize_enabled_when`, threaded through every
    `*_option` factory) — keyword-only so the frozen subclasses' positional fields are undisturbed.
    `AutoSettingsLayout` stores each field's label + greys a child's **control + label** whenever
    `settings.<master> != value` (live per-section wiring + initial state + post-preset refresh); ~21
    pairs wired (the `red_intent_*`/`coin_*`/qra/motorpool/squadron/etc. dependents, incl. the **inverse**
    `default_front_line_stance` ← `("automate_front_line_stance", False)`). A `detail` over
    `INLINE_DETAIL_MAX` (150) now shows its first sentence inline + the full text on hover (the dead
    `tooltip` field), so dense pages stop being walls of text. Guard + offscreen-Qt greying tests in
    `tests/test_settings_dependencies.py`. Shipped with the **UI-audit bug fixes**: the defeat-shows-
    "Victory!" `onEndGame` enum-truthiness bug, the inverted Air-Wing player-slots caption, the shared
    `self.dialog` window-GC bug, the `QGroundObjectMenu` repair list-mutation, the web `TgosLayer`
    key-by-name → `tgo.id`, the upstream→fork Help/About/Releases links, and dead-component/duplicate-CSS
    cleanup. **Web-map tracks 3+4 (2026-07-10):** a shared semantic palette
    (`client/src/theme/mapColors.ts` — named `friendly`/`enemy`/`flot`/`suspected`/`offLimits`/
    `weaponsFree`/`supply*`/`route*` tokens the overlays import instead of inline hexes), reconciling the
    two look-alike dashed circles (the concealed "suspected activity" circle moved **red→amber** so it no
    longer reads as the red ROE off-limits circle) and lifting the near-invisible navy friendly supply
    route to a legible blue; a collapsible **map legend** (`components/legend/MapLegend`); and **right-click
    discoverability** — a `.map-interactive` `cursor:pointer` + hover hints on the front line / supply route
    / suspected-activity circle so the hidden fragging right-clicks are findable. Client-only (not CI
    type-checked; validated via `tsc` + the `FrontLine` test mock). The four tracks came off the
    56-finding UI audit; deferred: a full right-click context menu + Leaflet-tooltip theming + the deeper
    flow reworks. **Suspected-circle contrast pass (2026-07-19, the flown Inherent Resolve "circles are
    really hard to see"):** amber-on-desert-tan washed the concealment circles out — the lone
    "suspected activity" ring now draws a **dark dashed contrast casing** (`mapColors.strokeCasing`,
    weight 6 under the amber weight-2.5 dash, aligned dashes, `interactive: false`) so it reads on any
    imagery, and the fills rose (lone 0.18→0.25, cluster member 0.12→0.16). The cluster **density cloud
    stays stroke-less** (flown squadron decision, not re-litigated) and the hue stays amber (orange would
    collide with the FLOT token). `Tgo.tsx` + `mapColors.ts`; tsc+jest green; needs the CI client rebuild.
    **Dialogs are clamped to the screen (2026-07-19, the "windows are clipping / UI scaled screwed
    up" report):** the Edit Flight dialog opened with its **title bar above the top of the display**
    and carried ~260 px of dead space under the form. Measured offscreen on the reported 1440p @150 %
    panel (**928 logical px** usable): the dialog wanted **1115 px**, because (a) `QTabWidget.sizeHint`
    expands over EVERY page, so it was sized for the tallest *hidden* tab (Payload 1080) while showing
    the General tab (856) — `QFlightPlanner.sizeHint()` now substitutes the **current** page's height
    (the usual `Ignored` size-policy recipe does NOT work — probe-verified, `QTabWidget::sizeHint`
    ignores policy; only `minimumSizeHint` honours it), worst case **1119 → 899 px**; and (b) of 34
    `QDialog` subclasses only two ever consulted `availableGeometry` (the main window + the settings
    dialog's ad-hoc clamp), and several declare minimums that cannot fit a small display at all
    (`AirWingConfigurationDialog` 1024x768 vs 672 px on 1080p @150 %). New **`qt_ui/screenfit.py`** —
    `fitted_geometry` (pure shrink-then-move) + `fit_to_available_screen` (relaxes an over-tall
    **minimum size** first, or Qt silently ignores the resize; chrome-aware; logs a warning when even
    the layout minimum can't fit) + `ScreenFitFilter`, an app event filter installed once in `main.py`
    that fits every dialog on show (no per-dialog wiring; no-op when it already fits). Verified
    end-to-end offscreen: every flight's dialog lands at 835–893 px inside 1706x928, and a 3000 px
    test dialog is clamped fully on-screen. Tests `tests/test_screenfit.py`. Deliberately NOT done:
    the stylesheet's 139 `px` rules (Qt scales them by DPR; a font-preference wart, not the clipping
    cause). **The Payload tab goes wide (same day, the re-flown report "you prefer tall over
    wide")**: the clamp fired but bit **below** that tab's layout minimum — the assumption that every
    layout minimum fits once clamped was wrong (F-15E: 962 wanted, **901 minimum**, 880 available),
    and since `fit_to_available_screen` *relaxes* a minimum, the shortfall came out of the pylon
    rows, clipping the store names. The tab was one tall column inside an already-1508-px-wide
    dialog, so it is now **two columns** (aircraft knobs left, loadout right — as tall as the taller
    column, not both), the **pylon list scrolls** rather than being squeezed (the gotcha, and why an
    earlier attempt was reverted for "showing only a few rows": **`QScrollArea::sizeHint` is
    hard-capped at 24 font-heights** ≈360 px, so a scroll can only grow into space something else
    claimed — `AdjustToContents` + the column's stretch is what shows a full loadout), and
    **dropdowns stop demanding the width of their longest entry** (`qt_ui/widgets/dropdownwidth.py`
    `bound_dropdown_width` caps the hint but pins the popup to its natural width; two columns of
    un-bounded store names pushed the dialog to 2269 px). Result across every airframe in the
    reporter's save: **up to 2269x962 (min 901) → a uniform 1553 wide × 332–552 tall (min 346–360)**,
    dialog width unchanged. Tests `tests/test_payload_tab_layout.py` (drives the real
    `QLoadoutEditor` on real pydcs pylon data, worst case picked by measurement). `qt_ui` is not CI
    type-checked — needs an app-side eyeball, checklist B27.
29. **Campaign SITREP kneeboard band** — a "what happened last turn" digest on the next mission's
    kneeboard (a cockpit intel brief). `MissionResultsProcessor.commit()` gets a final
    `record_sitrep` step that reads the debriefing it already has — per-side losses (`loss_counts`),
    base captures (the cached pre-commit snapshot), Combat SAR rescues — into a `Sitrep`
    (`game/sitrep.py`) stored as `game.last_sitrep` (pickled, `__setstate__` default None). Enemy
    losses are framed as **"claimed"** to respect the recon-fog model. The SITREP renders as a
    "SITREP — Turn N" section at the **bottom of the Mission Info page** (back where the band first
    shipped — the §30 cover page that hosted it 2026-06→07 is retired), gated by `sitrep_for_kneeboard`;
    hidden on turn 1 / a quiet turn / when the `generate_sitrep_kneeboard` toggle (Kneeboards page,
    default ON) is off. v1 covers losses/captures/rescues; front movement + SCAR commander capture are
    deferred. **App-side parity 2026-07-18** (UI audit — the band had quietly become the fork's only
    status screen, trapped in the cockpit): the same `kneeboard_lines()` digest now also renders on
    the web ribbon's **LAST TURN** panel (`CampaignStatusJs.sitrep_lines`) and the Qt debrief's
    **Campaign consequences** box. (`game/sitrep.py`, `game/sim/missionresultsprocessor.py`, `game/game.py`,
    `game/missiongenerator/kneeboard.py`, `game/settings/settings.py`; features doc §29,
    checklist K2.)
30. **Dedicated kneeboard cover page** — RETIRED (2026-07-13, the kneeboard back-to-upstream rework;
    user markup pass on a flown Scenic Route Merged deck struck the whole page). `CoverPage`,
    `_build_cover_page` and the CAMPAIGN PHASE/ROE band it carried are deleted; the deck opens straight
    on the stock Mission Info page. The SITREP (§29) moved back to the Mission Info page bottom; the
    flight index (§27) is a standalone conditional page again; the phase/ROE keep their non-kneeboard
    surfaces (client ribbon, map zone drawings, Qt ROE warning — §40, with `roe_summary_lines` kept in
    `phases.py` for any future surface). Do not restore the cover — new kneeboard info folds into an
    existing stock page. (features doc §30.)
31. **One-page Brief Sheet + deck-wide colour scheme** — RETIRED (2026-07-13, the kneeboard
    back-to-upstream rework): the user's markup struck the Brief Sheet's MISSION/ROUTE/GAME PLAN/
    BULLSEYE/FIELDS/WX/LASER rows (each duplicated a stock page) and the Comms & Brevity card except
    its code words; `BriefSheetPage`/`BriefSheetData`/`BrevityCard` + the route/mission/game-plan/
    laser/freq/weather/fields helpers + `game/data/brevity_reference.py` are deleted. **Survivors,
    folded into upstream's pages:** the Mission Info **BLUF** gained the compact THREATS AIR/SAM lines,
    a one-line LOADOUT summary and the SAR if-down drill (`_brief_air_threats`/`_brief_sam_threats`/
    `_brief_loadout`/`_brief_sar`; the verbose TOP THREAT line and the BLUF's duplicate BULLSEYE line
    are gone — upstream's post-flight-plan `Bullseye:` line returns), and the **Support Info page**
    gained the colour-keyed **Code Words block** (`CodeWordsBlock`/`_render_code_words`, gated by
    `enable_package_code_words`). The theme-aware four-colour palette + `text_runs` primitive stay on
    `KneeboardPageWriter` (threat cards + code words + the amber RTB margin still use them).
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
    single 3-vehicle column). `operation_velvet_thunder.yaml` shipped with
    **no red→red `supply_routes`** (its red bases are spread across islands), so the toggle was a documented
    no-op there — until the §50 batch passes gave it a BLUE Guam road (batch 1) and red **island-internal**
    roads (batch 2: Saipan's Middle Road + Tinian's Broadway), so red convoys now exist to interdict, per
    island. So interdicting the trail now
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
    (`game/ato/flightplans/armedrecon.py`). **The search point stands off the target FOB (2026-07-06,
    flown-test finding):** the fly-over waypoint sat dead-centre on the Shirqat FOB's SA-13/ZU-23 garrison;
    `Builder._stand_off_search_point` now pulls it back along the target→ingress bearing — the target CP's
    longest TGO threat ring + 2 NM, floored at 5 NM, capped at the engage-zone radius (the target area stays
    inside the hunt zone, which centres on this waypoint) and the ingress distance. Standoff tests in
    `tests/test_armed_recon_planning.py`.
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
    with a reach defaulting to `ARTILLERY_FRONT_REACH_M` (35 km — real gun range off the FLOT, vs the
    Vietnam siege's theater-wide 200 km), so conventional campaigns can put their frontline strips under
    fire; **Red Tide preseeds it** (the Fulda FARP + red's Haina both sit on the front — "the Gap is not a
    safe ramp"). **The reach is campaign-tunable (2026-07-10)** via `artillery_harassment_reach_km` (default
    35, `enabled_when=artillery_base_harassment`) — the flown 2026-07-10 turn-1 test found the turn-0
    Fulda↔Haina front sits ~39 km from BOTH Fulda and Haina, ~4 km past the 35 km default, so neither was
    shelled on a fresh game; **Red Tide preseeds 42 km** (BM-27 Uragan reach ~35 km) so both fire from turn 1.
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
    returning detachment, so no pre-debit/return). **Losses-only, no delivery credit (2026-07-07 design call):**
    the earlier "delivered run credits the outpost a small ground-strength boost" is dropped — an airframe's
    *absence* from the kill list means "survived and delivered" OR "never spawned at all" (player ended the
    mission before the launch delay), indistinguishable without a runtime "delivered" signal the plugin does not
    emit (adding one would need exactly the Lua/debrief-schema change this module set out to avoid), so a clean
    run is simply free. No base-Lua / debrief-schema change: the spawned units already fire the DCS death events
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
    "Interdiction — enemy IADS 22% · air threat low · front static") on
    a **client campaign-status ribbon** (`CampaignStatusBar` over the map, fed by `GameJs.campaign_status`
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
46. **Route-aware fuel-tank planning (fuel-first)** — fuel is a first-class planning input: build the package
    normally, then — once the sortie route is known — fit the tanks the sortie needs, and only then decide the
    tanker passes ("if the plane can't make it to the objective it doesn't matter how many missiles they
    carry"). **Fuel-first rework 2026-07-12** (user call off a flown SEAD Viper carrying two wing bags + a
    centerline ALQ-184 that was planned pre- AND post-vul refueling): the pre/post-vul tanker decision
    (`FormationAttackBuilder._refuel_tasking`) ran on *internal fuel only* — the bags were invisible — and the
    generation-time top-up could never fit a third bag on the occupied centerline. Now (1) **the decision
    counts the bags**: `full_fuel = internal + external` (a top-off refills externals too), external read from
    the **driest member's** loadout (`flight_external_fuel_lbs`), and the kneeboard **fuel ladder** starts from
    internal + external for the same reason; (2) `plan_sortie_fuel` (`game/fourteenth/range_fuel.py`) runs
    inside `_refuel_tasking` before `decide_refuel_tasking`, **mutating the members' persisted loadouts in
    place** (shared objects mutated once, `is_custom` never touched, idempotent across rebuilds, both
    coalitions) — **tier 1** fills empty tank-capable stations while the sortie's burn (real per-leg
    climb/combat/cruise rates via `sortie_fuel_split`) outruns the fuel carried (§46's original fill, moved
    ahead of the decision), **tier 2** trades a **`WeaponType.JAMMER`-typed pod** on a tank-capable station for
    a tank — ONLY when the extra bag strictly reduces the tanker-pass count (BOTH → one pass → NONE), or on a
    plain shortfall when no tanker exists at all (the bags are then the only gas). The Viper case: ALQ-184 off,
    300 gal bag on, one post-vul pass. The trade is JAMMER-only because everything else is untypeable
    (`WeaponType.UNKNOWN` — a Sidewinder and a JDAM look identical), and OFFENSIVE_JAMMER/DECOY/TGP stay
    protected; tanks are detected by DCS display-name (narrow regex; capacity parsed from gallons/liters/kg).
    The **generation-time top-up** `add_range_fuel_tanks` (in `flightgroupconfigurator.setup_payload`) stays as
    the safety net for non-formation flights (ferries, CAPs, old saves) with its original contract: fills
    empties only, never removes a store, never mutates the persisted loadout. TARCAP's doctrinal refuel
    waypoint is untouched. Gated `auto_range_fuel_tanks` (Mission Generation → Loadouts, **default ON**) +
    `fuel_tanks_over_jammers` (same section, **default ON**, `enabled_when=auto_range_fuel_tanks` — the tier-2
    kill switch); the tank-aware decision itself is unconditional (it just reads the real loadout). Tests
    `tests/fourteenth/test_range_fuel.py` (the trade's gates on the real F-16C tables + the gen-time
    never-removes contract on the real F/A-18C) + `tests/ato/flightplans/test_fuel_first_tanking.py` (the
    Viper case end-to-end: BOTH → POST_VUL with the pod traded). **The in-app fuel-plan readout** (same day):
    `game/fourteenth/fuel_brief.py` (`fuel_brief_for` — the same per-leg walk via the flight plan's
    `fuel_consumption_between_points`, REFUEL top-offs, stops at the landing point, driest-member external
    default) renders live on the Edit-flight **Payload tab** under the fuel slider ("burns ~X · carries Y
    (internal + N tanks) · N tanker passes · RTB margin ±Z", amber + "short of getting home" when negative,
    "(estimated)" on the synthesised model), refreshed on fuel-slider/loadout/custom/member changes + every
    pylon edit (new `QPylonEditor.pylon_changed` signal) + tab `showEvent`; tests
    `tests/fourteenth/test_fuel_brief.py`. **The racetrack burn (2026-07-19, the flown "19 GSPD is
    impossible" BARCAP kneeboard):** the patrol leg's schedule time is on-station dwell, but the fuel walk
    charged only its straight-line length — so a 45-min BARCAP's whole orbit burn (~8,000 lb on the flown
    Hornet) was missing from the ladder (RTB margin read +8,488; honestly ~+830) and the kneeboard's derived
    GSPD divided track length by dwell (19 kt). New `FlightPlan.fuel_burn_distance_between_points` hook,
    overridden by `PatrollingFlightPlan` to charge `patrol_speed × patrol_duration` (floored at the track
    length) — every consumer inherits (ladder, margin, fuel brief, sim estimates); formation-attack holds
    deliberately untouched so the ladder can't drift from the `sortie_fuel_split` tanker decision. The
    racetrack-end kneeboard row now shows the **planned patrol speed** (`FlightData.patrol_speed`) instead of
    dist/dwell, and a patrol flight's plan prints the **on-station endurance call-out** ("On station 45 min
    planned; fuel supports ~50 min before bingo") — the planned dwell stays doctrine
    (`desired_barcap_mission_duration` + the §6 wave relief), the line answers "stay until bingo" for the
    pilot; amber when the gas cuts the planned station short. Deliberately deferred: fuel-capped patrol
    durations and dwell-aware tank fitting (fleet-wide loadout shift). Tests
    `tests/ato/flightplans/test_patrol_timing.py` +
    `tests/missiongenerator/test_flightplan_fuel_column.py`. (`game/fourteenth/range_fuel.py`,
    `game/fourteenth/fuel_brief.py`, `game/ato/flightplans/formationattack.py`,
    `game/ato/flightplans/flightplan.py`, `game/ato/flightplans/patrolling.py`,
    `game/missiongenerator/aircraft/waypoints/waypointgenerator.py`,
    `game/missiongenerator/aircraft/flightgroupconfigurator.py`, `game/missiongenerator/kneeboard.py`,
    `qt_ui/windows/mission/flight/payload/QFlightPayloadTab.py`, `game/settings/settings.py`; features doc §46,
    checklist S1 — needs an in-game pass + an in-app pass for the readout.)
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
    precedent). Inert unless a campaign actually places a missile TGO: **Red Tide** is the first to on
    purpose (2 red SS-1C Scud-B batteries off Haina + near Wittstock, added to the `.miz`; preseeds the
    setting + the `mobilemissiles` plugin). Tests `tests/missiongenerator/test_mobilemissileluadata.py` +
    `tests/lua/test_mobilemissiles_runtime.py` + `tests/fourteenth/test_campaign_plugin_preseed.py`;
    features doc §49, checklist S2 — **VERIFIED 2026-07-10** (flown Red Tide re-fly: all 6 launchers in
    both batteries relocated ~1.5 km net inside the scoot anchor, escorts with them, no SAM site moved,
    alarm-green held). **Movement bug fixed 2026-07-09** (the first flown test: launchers never moved,
    Tacview-confirmed stationary, no error): `driveTo` issued a **1-waypoint** `mist.goRoute`, but a DCS
    ground group needs its route to START at its current position or there's no leg to drive (MIST's own
    `groupToRandomZone` uses 2 WPs) — now a 2-WP route `{current, dest}`. **The identical bug + fix apply
    to the COIN mover** `coin-config.lua` (§P4/P8), which still owes its own COIN-campaign fly.
    **Fire-vs-scoot clobber fixed 2026-07-16** (flown Scenic Route finding): the upstream missile-site
    fire task (`Hold → FireAtPoint` on waypoint 0) and the scoot were mutually destructive —
    `mist.goRoute`'s `setTask` replaced a pending fire mission (12/13 batteries silently never fired) and
    a battery that fired first sat pinned on the spent task, never scooting. Now **fire first, THEN
    scoot**: `MissileSiteGenerator` records each fire-tasked group's hold deadline on
    `MissionData.missile_fire_missions`, the emitter forwards them (`fireHoldGroups`/`fireHoldS`), and
    the plugin holds those groups until deadline + `fireMarginS` (300 s), then routes with a
    `resetTask()` first. **The 2026-07-17 turn-2 re-fly proved the fire half** (9/10 fire-tasked
    batteries launched full volleys ~12–15 s after their forwarded deadlines — 18 SCUD + 45 Shahed —
    holds released on schedule, zero tick errors, and COUGAR/LAMPREY fired *then* scooted) **but
    found the residual pin**: a bare `FireAtPoint` has no round limit and no stop condition, so a
    dry battery's task never ends, the launchers never leave their deployed fire state, and
    `resetTask()` recovered only 2 of 9 fired batteries (all 4 never-fired groups drove fine; the
    sitters' escorts crept 20–80 m into formation and stalled against the pinned launchers).
    **Fixed same day:** the generator wraps the fire task too — `ControlledTask(FireAtPoint)` with
    `stop_after_time(hold + MISSILE_FIRE_WINDOW_S)` (240 s; flown volleys complete within ~40 s of
    the deadline) so the task ends through the normal completion path before the plugin's 300 s
    margin routes the group; the window/margin coupling is pinned by
    `test_fire_window_stays_inside_the_plugin_scoot_margin`. Re-fly owed (S2 stays PARTIAL).
    **Single-digit-FPS storm found + fixed 2026-07-17** (the first flown test on the fixed build,
    a fresh 39-site game): every site armed at the same moment, so ALL sites routed **in the same
    frame** every interval (continuous DCS ANTIFREEZE from the first scoot tick — before any drone
    launched), and the coastal Silkworm hardware (`hy_launcher`/`Silkworm_SR`) is a **fixed
    emplacement with no drive physics** — routing it produced zero movement and a per-frame
    `GT.maxDeviationRoll` ground-AI storm (~15k log events in the first tick minute). Fixes: the
    emitter's `IMMOBILE_UNIT_IDS` drops any group carrying such a unit (vanilla Silkworm batteries
    are never routed — `coastal_missile_relocation` now only matters for mod sites with genuinely
    mobile launchers), and the plugin **staggers each site's loop** by `(i-1)·interval/N` so route
    pushes spread across the interval instead of landing together. Tests
    `test_immobile_silkworm_hardware_is_never_routed` +
    `test_site_loops_are_staggered_across_the_interval`. **The flown 39-site Tacview (same day)
    proved the fire-window fix on vanilla hardware** — 13/13 fired Scud_B batteries scooted after
    their volleys (S2's SCUD half closed) — **and found the residual: all 8 fired `CH_Shahed136`
    sites stay pinned post-salvo** (the never-fired ones drive fine; a mod-side post-fire state
    DCS won't drive out of — `resetTask`/alarm-green don't clear it). Mitigation: the plugin
    **gives up** on a group after 2 consecutive dry route pushes (<100 m progress; movement resets
    the count) — a spent battery is left alone (its magazine is empty; the scoot protects *loaded*
    launchers) instead of drawing futile pushes all mission. Tests
    `test_stuck_group_is_given_up_after_dry_pushes` + `test_moving_group_is_never_given_up`.
    The same flown test drove the
    **no-front support-orbit fix** (a front-less naval map marched red's A-50 200 NM AWAY from the
    fleet — `support_orbit_anchor` now skips the AI depth march with no FLOT; features doc §8-adjacent
    support-orbit section) and the **S-3B DEAD cleanup** (no ARM on the airframe; the SLAM "DEAD"
    preset + the yaml `DEAD: 280` the loadout-integrity sweep missed are removed).
50. **Convoy ambush (a chance, never telegraphed) + ambient supply convoys** — the **mirror of the §35
    interdiction**: where
    interdiction gives the player *enemy* convoys to hunt, this gives the player *friendly* convoys that
    might need protecting. Real, tracked BLUE supply convoys run the roads behind the front, and —
    **sometimes; a chance roll, never a certainty** — hidden, real RED ambush teams dig in along the route:
    one contact, or a gauntlet of five or six down the same road. **Nothing is telegraphed in the UI**
    (reworked 2026-07-06 from the original always-one-ambush + auto-fragged-escort design, per the squadron
    call): the convoy looks like any other friendly convoy, the teams have no map presence at all, and no
    escort package appears in the ATO — the first sign is the in-mission "TROOPS IN CONTACT" call, and
    supporting the column (or not) is the player's decision. **No phantom spawns** (the §35/§37 lesson):
    the convoy is a real `coalition.transfers` transfer (its loss = units that never arrive, reconciled in
    `commit_convoy_losses`, which already iterates *both* coalitions' convoys) and each ambush team is a
    real red TGO placed by `spawn_red_ground_at` (killing it is a real red ground loss recorded natively) —
    so both sides' losses count and the Lua plugin owns **no** kills. Total hiding rides a new visibility
    leaf, **`TheaterGroundObject.map_hidden`** (pickle-safe): stronger than the §3 `concealed` circle,
    `hidden_on_player_map` returns True unconditionally for an enemy viewer (no reveal key, unlike the SCAR
    command posts), the SSE event stream now filters hidden TGOs (`GameUpdateEventsJs.from_events` — a
    debrief-time unit kill would otherwise have pushed it to the map), and
    `BattlePositions.for_control_point` skips it so no AI-planned package can reveal it either.
    **Standardized to all campaigns 2026-07-06 with the ambient-convoy layer**
    (`game/fourteenth/ambient_convoys.py` `ensure_ambient_convoys`, from `finish_turn` after the §35 trail
    top-up): every turn EACH side's convoy flow is topped up to a **randomized** `randint(1, 3)` real
    columns on **randomly chosen DISTINCT** same-side road corridors (`_RNG.sample`, one column per road,
    capped at the road count; never forced, organic/§35 convoys count toward the target), oriented rear→front
    off the shared `_reference_points` (fronts, or opposing CPs on a front-less laydown); each column carries
    the units actually in its rear base's roster. **Distinct roads, one transfer per corridor (2026-07-07 S5
    fix):** the convoy map keys transports by `(origin, destination)` (`TransportMap.add`), so two transfers
    on the SAME corridor **coalesce into one oversized group** that line-spawns into unauthored positions and
    **deadlocks** at mission start (the flown S5 regression — a 24-vehicle blue column parked at Baghdad, which
    also blocked the §50 ambush spring); sampling distinct corridors keeps every column a separate driveable
    group (trading away the never-achievable "some share a road" texture — a shared road was one parked blob).
    **Skim-only, no free unit seeding (2026-07-07 design call):**
    ambient columns **relocate units that already exist** (`_skim_units`) and never `commission_units` free ones
    — generalizing the §35 trail's external-supply free-seed to every campaign on both sides would inject
    un-budgeted reinforcements into both armies every turn, which the squadron never asked for (it asked for
    *traffic*). A rear base too thin to skim (< 2 armor) yields no column that turn (the §35 Vietnam trail keeps
    its own documented, red-only, Vietnam-gated seeding). This **replaces the old blue-only `ensure_blue_escort_convoy`** —
    the ambush chance rolls over every blue convoy whatever created it. Gated `ambient_supply_convoys`
    (Mission Generation → Battlefield life, default **ON**); a side with no same-side road (island maps,
    all-red graphs) is a silent no-op. `seed_convoy_ambushes` (from `finish_turn` right after) despawns
    last turn's teams, then rolls each active blue convoy against `AMBUSH_CHANCE` 0.5; a hit seeds
    `randint(1, 6)` teams of `AMBUSH_TEAM_SIZE` via `_ambush_points` — stratified-random slots interpolated
    **along the route polyline**, 15 % end-margins, so a big roll reads as a spread gauntlet — recording
    the pairings on `game.convoy_ambush_state`; the dice live in module `_RNG`s so tests script them. The
    old `plan_convoy_escort` auto-frag is **deleted**. The emitter `game/missiongenerator/convoyambushluadata.py`
    (`dcsRetribution.convoyAmbush`) lists each live pairing's ambush-team group names + centre + the targeted
    convoy's group name, and the `resources/plugins/convoyambush/` plugin **springs** each dug-in team:
    alarm-green/weapons-hold until a convoy unit closes inside the trigger radius (6 km) — then weapons-free +
    a "TROOPS IN CONTACT" cue + an F10 mark, after a startup grace; a team its convoy never reaches **stays
    dug in and silent** (the max-hold "spring anyway" fallback is removed — it would telegraph a fight nobody
    drove into). **ROE/cue only** — the firefight is reconciled in the turn-boundary force model, so a mover
    shot down is recorded natively (the §35/§37/§49 discipline). Gated `convoy_ambush` (Mission Generation →
    Battlefield life, default **ON** since the 2026-07-06 standardization — the §49 kill-switch precedent;
    existing saves keep their stored choice), still preseeded ON + the plugin preseeded ON (the §36
    saved-default-off lesson) in COIN Enduring/Inherent Resolve, 1968 Yankee Station, and Red Tide. **A
    blue→blue supply road is the hard prerequisite** (2026-07-05 flown-test finding: both COIN campaigns
    shipped all-red graphs, so the blue convoy silently never existed) — the blue rear corridors are
    geo-authored per the driveable-corridor standard (`tools/supply_route_geo.py`: ER Kandahar↔Camp Bastion
    up Highway 1, the literal ambush alley; IR Baghdad↔Balad + Baghdad↔Al-Taquddum; the tool gained the
    `iraq_inherent_resolve` mode). The **2026-07-06 survey** found **27 of the 67 campaigns** bind a
    blue→blue road natively, and the **same-day batch-1 corridor pass** (`BATCH1_BLUE_REAR` in the tool —
    real highways traced by lat/lon, spliced into the campaign yamls, headless-verified to bind their
    intended blue pairs) **authored 21 more** across ten maps (Tbilisi/west-Georgia/Anapa on Caucasus, the
    Turkish O-52/E91 + the H4↔H3 pipeline highway on Syria, US-95 on Nevada, the UAE E11 on PG, Israel
    route 40 + the Egyptian Delta on Sinai, the Baghdad ring, Kandahar↔Bastion on Shattered Dagger, Guam's
    Marine Corps Drive on Velvet Thunder, the New Forest A-roads on Normandy, the Swedish/Norwegian
    E10/E45/E6 chain on Kola) — **48 of 67 now field the feature**; the 19 left are genuine geography
    no-ops (0–1 blue land CPs, or a blue pair split by sea/strait; Syrian Shield / Caucasus_Multi_Russia
    deferred — their only corridor would cross the red heartland). The full set is CI-locked as
    `ROAD_BEARING_CAMPAIGNS` in `test_road_bearing_campaign_keeps_its_blue_road`, which loads each theater
    so a laydown edit can't silently drop a road (+ `test_batch1_corridor_campaigns_are_in_the_inventory`
    keeps the tool and the inventory in lockstep). **Batch 2 (2026-07-07) did the same for RED**: the nine
    campaigns with no red→red road (so red's ambient convoys — the player's interdiction targets — silently
    never existed) got real-road red rear corridors via `BATCH2_RED_REAR` (the Aleppo belt + the Turkish
    FOB line on the two WRL Syria campaigns, the Iranian Bandar-Abbas/Kerman/Shiraz/Bushehr mainland
    highways for both Noisy Crickets, Cyprus's A1/A2/A5 for Aegean Aegis, the Calais N43/E40 for Dynamo on
    TheChannel, the ER ratline reused verbatim for Shattered Dagger, Saipan's Middle Road + Tinian's
    Broadway for Velvet Thunder, and the Guam road — red-owned there — for Pacific Repartee); guarded by
    `test_batch2_campaign_keeps_its_red_road`. Every campaign now fields at least one side's convoys except
    the handful with no two same-side land bases at all. Tests `tests/fourteenth/test_convoy_ambush.py` +
    `tests/fourteenth/test_ambient_convoys.py` + `tests/missiongenerator/test_convoyambushluadata.py` +
    `tests/lua/test_convoyambush_runtime.py`; features doc §50, checklist S3 + S5 — needs an in-game pass.
    **Tuned 2026-07-09** (flown Red Tide: "excessive, and should be light not MBTs"): the ambush teams
    spawned as `GroupTask.FRONT_LINE` **armor** (MBT groups) and could pile up (a 2-convoy turn maxed
    to 12). Now the teams use a **light raider kit** (`coin.ambush_unit_types` — a gun-truck + riflemen
    from the faction's own roster, `CELL_SIDC` infantry symbol) via the `unit_types`/`sidc_override`
    path, and the count is bounded: `MAX_AMBUSHES_PER_ROUTE` 6→3 **plus** a theater-wide
    `MAX_TOTAL_AMBUSHES` (4) so several convoys can't swarm the backline.
51. **Enemy comms jamming (IADS comms nodes)** — the IADS comms nodes, given a voice: with
    `enemy_comms_jamming` on, every alive enemy `comms`/`commandcenter` TGO (the same C2 objects the MANTIS
    degradation graph watches) floods the BLUE side's **briefed** channels with duty-cycled barrage noise via
    `trigger.action.radioTransmission` from the node's map position — real DCS power/distance falloff, and
    **SRS users hear it through their cockpit-tuned radios**, so no SRS-server dependency exists (the
    ExternalAudio path was considered and dropped). Python owns the plan (`plan_comms_jam` →
    `MissionData.comms_jam`, computed before the Lua pass): a positive-list of targets — intra-flight channels
    (human-crewed first) + blue AWACS, GUARD defensively filtered, capped at 10 — **never ATC/ATIS/tankers by
    construction**, plus a freshly-allocated **JAM BACKUP** UHF channel (unjammable because nothing else uses
    it) printed on the kneeboard **Mission Info BLUF** — next to the `PUSH / SUCCESS / ABORT` code words
    (comms-plan data), moved off the Support Info comms ladder where the table borrowed the viewing flight's
    Type/#A/C columns and it read as a phantom 4-ship (the shared `JAM_BACKUP_COMM_NAME` constant keeps the
    `add_comm` producer and the BLUF-line + Support-filter consumers from drifting) — and echoed in the
    first-burst cue. The `commsjam` plugin steps on
    only ~3 channels per jittered burst cycle (rotating window — switching channels is real comms discipline),
    rotates the transmitting node across alive jammers, and uses the MANTIS `node_dead` positive-evidence
    convention (destroyed static / `dead_events`) so a culled node stays "alive" (unkillable this mission =
    standing pressure to frag it next turn). **`maxChannels`** (plugin option, default 10) caps the total
    distinct channels jammed — the Lua keeps the first N of the priority-ordered emit, so a low N pins the
    jamming to the top nets (human flights, then AWACS); paired with a long `burstSec` + short `intervalSec`
    it turns the duty-cycled sweep into near-continuous pressure on a few channels (Red Tide preseeds
    `burstSec 120 / intervalSec 10 / maxChannels 3 / powerW 10000`). **`powerW` is RANGE, not loudness**
    (2026-07-11): DCS models the RF falloff, so wattage sets how far from the node the interference is
    *receivable*, not how loud the static is once received — loudness is the audio clip amplitude
    (`commsjam-noise.wav`, limited to ~-4 dBFS RMS after a played-test "too quiet"; do not chase volume with
    `powerW`). **The intel gate is the default mode** (`comms_jam_requires_capture`,
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
52. **Command-center decapitation degrades enemy planning** — the campaign-layer complement to §51 (design
    note `414th-iads-c2-consequences-notes.md`, Feature A): the IADS **command center** was a data-model
    object (`category == "commandcenter"`, `IadsRole.COMMAND_CENTER`) whose only gameplay was MANTIS's runtime
    SAM-autonomy graph — nothing coupled it to *planning*. Now a side's **auto-planner quality tracks its own
    command-network health**: `game/fourteenth/c2_decapitation.py` `unpredictability_bonus` scales the §17
    planner unpredictability up in proportion to the dead fraction of that side's command centers (linear,
    `MAX_DECAP_UNPREDICTABILITY` 60 pts at full decapitation, clamped to 100), read at plan time through
    `targetorder._unpredictability_for`, so a headless HQ services worse opportunistic targets. **The §17
    boundary holds** — only the offensive/opportunistic shuffle is touched; reactive defensive tasking stays
    deterministic (a decapitated enemy still defends). Legibility via a SITREP band line (`Sitrep.red_c2_status`
    → "Enemy C2 degraded (claimed): 1/3 command posts operational", `c2_status_line`, rides along with real
    news like the will band). **Pure turn-model** — no `.miz`/Lua/DCS, symmetric in code (each side reads its
    own C2 health) but only a side with an HTN auto-planner is affected. Gated `c2_decapitation_effects`
    (Air Doctrine, default **OFF**, **preseeded ON in Red Tide** 2026-07-07 — its advanced-IADS build has a
    real 9-node destroyable red command network for §52 to key on); intact network / C2-less campaign =
    byte-identical no-op (the deterministic planner + its tests preserved). **Phase A2 LANDED
    2026-07-17 — the floored offensive package-count throttle**: `offensive_package_cap` shrinks a
    decapitated side's offensive package ceiling linearly with its dead-CC fraction
    (`FULL_OFFENSIVE_PACKAGE_CAP` 12 → `MIN_OFFENSIVE_PACKAGES` floor 2, never zero), enforced by
    `PlanNextAction._offensive_tempo_exhausted` — once the ATO holds that many unambiguous-offensive
    packages (Strike/BAI/OCA/anti-ship/air assault/armed recon; CAS + SEAD/DEAD excluded, both planned
    defensively too) the HTN root stops offering the offensive middle (trimming, not reordering; the
    reactive prefix + recovery tail are never throttled). Tests `tests/fourteenth/test_c2_decapitation.py` +
    `tests/test_planner_unpredictability.py` + `tests/fourteenth/test_campaign_plugin_preseed.py`; features
    doc §52, checklist B6 — needs an in-game pass.
53. **War economy** — a per-base **materiel supply** economy on top of the money budget, closing the
    "nothing you bomb changes what the enemy fields" gap (design note `414th-war-economy-notes.md`).
    `game/fourteenth/war_economy.py` runs a produce → transport → consume loop from `finish_turn`:
    factories/oil **produce** supply banked in `Base.supply`; it **transports** producer→front over the
    transit graph (`_external_supply_sources` via `transitive_connected_friendly_destinations`) and is
    **consumed** at the front — a front cut off from production drains (the interdiction loop). The **bite**
    (P2) is one `supply_effectiveness(cp)` multiplier `[0.5, 1.0]` applied at three sites: the `+0.2`
    per-turn strength recovery (`game.py`), the deployable-unit cap (`front_line_capacity_with`), and the
    ground-combat `delta` (scaled by the *winner's* supply) — so interdiction visibly slows the enemy's
    advance and recovery. Recursion-safe: `frontline_demand` keys off `base.total_frontline_units` (raw
    force), never the supply-scaled cap. **P3** wires the previously-dead `active_fuel_depots_count`:
    `fuel_readiness(cp)` scales `Squadron.untasked_aircraft` at the turn boundary, so bombing a base's fuel
    grounds part of its air for the AI planner and the human alike. **P4a** surfaces a SITREP front-supply
    band ("Front supply X% -- enemy Y%") so the player reads *why* a front stalled. Exposes
    `coalition_supply_health`/`supply_factor`, consumed read-only by §55 red intent. Symmetric; gated
    `war_economy` + `fuel_air_readiness` (Campaign Management → War economy, both default **OFF**, preseeded
    ON in Red Tide); OFF is a proven exact no-op (regression across the combat/controlpoint/frontline/
    ground-planner suites). **P4b** (landed 2026-07-08, post-merge polish): the base-card (`QBaseMenu2`)
    shows a **Front supply %** line + reconciles the deployable-limit tooltip with the supply multiplier,
    and a client **Supply status** map overlay (`SupplyLayer` + `SupplyNodeJs` on `GameJs`, default-ON in
    the §19 layers panel) draws each BLUE front coloured by materiel readiness + each producer as a blue
    source ring — empty (layer hidden) unless `war_economy` is on, BLUE-only so enemy logistics stay
    fogged. P0–P4a landed via #531 (merged 2026-07-08, alongside §55). Tests
    `tests/fourteenth/test_war_economy.py` + `tests/server/test_supply_nodes.py`; features doc §53 — needs
    an in-game pass (multi-turn FLOT response + fuel grounding) + the CI client rebuild for the overlay.
54. **Munitions availability** — the **air axis** of the war economy (§53): an airfield out of a scarce
    munition can't load it. A curated, **hand-audited** scarce-munitions taxonomy (`_SCARCE_MUNITIONS` in
    `game/data/weapons.py` — 5 families `a2a_medium`/`arm`/`pgm_bomb`/`standoff`/`guided_asm`, keyed by
    exact `WeaponGroup.name` with a dead-name guard test) drives `WeaponGroup.scarce_family` (M0). Each base
    holds a per-family stock (`Base.munitions`) **debited by what the ATO loaded** — a once-per-turn
    turn-boundary step, NOT a per-generation debit, so mission re-generation never double-counts — and
    **rearmed** toward capacity scaled by supply health (M1). The **gate** (M2): `Loadout.degrade_for_stock`
    in `setup_payload` swaps a depleted scarce store down to the first stocked/non-scarce fallback (JDAM →
    dumb bomb) or clears the pylon (authoritative), and the payload editor greys out + labels
    "(out of stock)" the depleted stores (guidance). Gated `restrict_weapons_by_stock` (Mission Generation →
    Loadouts, default **OFF**); OFF is an exact no-op. **M3** (landed 2026-07-08, post-merge polish): the
    base-card (`QBaseMenu2`) shows a per-family **Munitions** stock readout (`N/24`, "(low)" at zero), driven
    by the shared `SCARCE_FAMILY_LABELS` map, friendly bases only. M0–M2 landed via #531 (merged 2026-07-08).
    Tests `tests/fourteenth/test_munitions_gate.py` + `tests/fourteenth/test_scarce_munitions.py` +
    `tests/fourteenth/test_war_economy.py`; features doc §54 — the loadout grey-out + base-card readout need
    an in-app pass.
55. **Red Intent — adaptive enemy posture** — the "thinking red opponent": the mirror of the
    BLUE campaign-phases arc (§40) for RED, and unlike the blue arc it carries *memory* across
    turns. Each turn `game/fourteenth/red_intent.py` resolves a RED **posture** —
    `CONSOLIDATE` / `ATTRITION` / `SURGE` — from live state (ground-force balance, air strength,
    resolve) **plus last-turn deltas** (territorial movement vs a lazily-snapshotted turn-0
    baseline + a base lost last turn) with **asymmetric hysteresis** (dwell to escalate,
    immediate to consolidate), latches it on `Game` (getattr-guarded, recompute-not-pickle like
    the phase pointer), announces transitions, and surfaces it on the SITREP band + a colour-coded
    chip on the campaign-status map ribbon (`CampaignStatusJs.red_posture`). The posture
    then biases the RED commander across **four planner seams** — all no-ops for blue, a stock
    red, or when the toggle is off, so the planner is byte-identical to before until red is
    actively consolidating or surging: (1) **offensive emphasis** — reorders `PlanNextAction`'s
    offensive methods (surge takes ground first, consolidate leans defensive) through the same
    name-keyed indirection the blue phases use (`nextaction._offensive_order`, which resolved
    its "a red arc is deferred" TODO); (2) **unpredictability** — adds to
    `opfor_planner_unpredictability` (attrition keeps red a little erratic, surge focuses it),
    stacking with the §52 C2-decap bonus on the same clamp (`targetorder._unpredictability_for`);
    (3) **aggressiveness** — biases `opfor_autoplanner_aggressiveness` so surge abandons more
    bases to attack and consolidate defends everything (`objectivefinder.effective_aggressiveness`);
    (4) **ground husbanding** — scales the *perceived* ground-force balance the ATTACK stance
    thresholds test (surge commits reserves sooner, consolidate husbands; the defensive/retreat
    stances are untouched, so consolidate never forces a retreat), and **yields** to an active
    authored `red_tempo` pulse so a campaign author's Tet/Easter offensive is never double-driven
    (`frontlinestancetask._posture_commit_factor`). Gated `red_intent` (Air Doctrine, default
    **OFF**); red-only by design (blue's "intent" is the phase arc). **P4 (the §53 war-economy
    supply coupling)** is a read-only drop-in via the locked `coalition_supply_health` contract —
    starved supply will force `CONSOLIDATE` even on a paper advantage — and stays a graceful
    no-op until the sibling §53/§54 economy lands (design note `414th-red-intent-notes.md`).
    **Made smarter 2026-07-10** (the memory the design always described but v1 only stubbed as a
    turn-0 snapshot): (A) **rolling trend memory** — a bounded per-turn `red_intent_history` of
    turn-stable levels (`RedIntentSample`: resolve, front advance, red SAM-site count, both sides'
    fighters, red base count, supply) on `Game` (getattr-guarded + `__setstate__` default, trimmed
    to `MEMORY_LENGTH` 6); the classifier differences the current sample against a `_trend_lookback`
    sample (~2 turns back, None on turn 1, idempotent same-turn record) for `iads_trend` /
    `resolve_trend` / `base_trend` / `front_trend`. (C) **richer battle-reading** — those trends bias
    a *ground-dominant* red to `CONSOLIDATE` (its own IADS/resolve/base attrition digs a winning red
    in, not only the §53 supply meter), and a **blue-air-collapse opportunity window**
    (`blue_air_collapsing`, ≥35 % of blue's air-sup force lost over the window) lets red `SURGE` at a
    lower ground bar (1.2× vs 1.5×). (B) **graduated intensity** — the classifier also yields an
    `intensity` ∈ [0,1] latched as `red_intent_intensity`; the aggressiveness + ground-commit seams
    scale their magnitude by it (a runaway 4:1 surge presses harder / a collapsing regime husbands
    harder), anchored at `DEFAULT_INTENSITY` 0.5 to the v1 midpoints so a typical posture is
    byte-identical and only the extremes move (unpredictability + emphasis stay posture-only). All
    no-ops until real trend/margin data exists, so every prior test held byte-for-byte. **Per-front
    posture + tuning added same day (D + settings):** (D) `_update_front_postures` classifies EACH active
    front from its own ground balance + the shared theater air/resolve/trend read (per-front hysteresis,
    latched `FrontPosture` on `game.red_intent_fronts` keyed by cp-id pair), and the **ground-husbanding
    seam** goes per-front (`stance_commit_factor(game, front)` via `_front_posture_and_intensity`, wired
    from `frontlinestancetask._posture_commit_factor` passing `self.front_line`) — so red commits on the
    front it is winning and husbands on the one it is losing; the other three seams + the UI headline stay
    theater-wide, the per-front breakdown surfaces in the ribbon expander (`front_postures` →
    `CampaignStatusJs.front_postures`, 2+ divergent fronts). Gated `red_intent_per_front` default ON
    (off ⇒ theater fallback). Tuning: a `RedIntentTuning`/`tuning_for` object (default = base constants,
    byte-identical) threads three new Air-Doctrine settings — `red_intent_boldness` (0-100, 50 neutral;
    the master dial: lowers the surge/opportunity/consolidate ground bars + raises the seam magnitude),
    `red_intent_dwell_turns` (escalation stickiness), `red_intent_trend_window` (trend lookback) — through
    the classifier + seams; re-anchored so seam_scale=1 + intensity=0.5 reproduce the v1 numbers. **Surfaced
    visibly (not hover-only):** the
    **kneeboard SITREP** "Enemy posture" line now renders the *detail* — intensity word + trend driver
    ("Surging (all-in) — ground 4.0x · air holding · IADS falling") via `sitrep_posture_detail` +
    `Sitrep.red_posture_detail` (Python-only, no client rebuild); the **web ribbon chip** shows the
    intensity word inline ("ENEMY Surging · all-in", `CampaignStatusJs.red_posture_intensity` via
    `intensity_word`) and the expander gained an "Enemy intent" block with the full `red_posture_detail`
    "why". Tests `tests/fourteenth/test_red_intent.py` + `tests/test_sitrep.py` +
    `tests/test_planner_unpredictability.py`; features doc §55, checklist B7 — needs an in-game pass (does
    red visibly surge when ahead / consolidate when hit / dig in as its IADS is bombed, across a
    multi-turn campaign; the SITREP posture-detail line + the ribbon intensity read correctly).
56. **Strikeable motorpool depots** — **adopted from upstream PR
    [dcs-retribution#859](https://github.com/dcs-retribution/dcs-retribution/pull/859)**
    (geofffranks; cherry-picked verbatim + fork-adapted, the Pretense hunk dropped since the fork
    has no Pretense). A control point's **not-yet-deployed reserve armor** (the slice `plan_groundwar`
    holds back from the front) is projected each turn as a **strikeable depot** the player can bomb —
    attriting the enemy's armor reserve at the motor pool instead of only meeting it at the FLOT. A new
    `MotorpoolGroundObject` (`game/theater/theatergroundobject.py`, category `motorpool`, a
    maintenance-facility map symbol distinct from armor groups, always rendered *present* — an empty
    depot is its resting state, never "destroyed") is placed where a campaign authored a
    `Fortification.Garage_A` (`start_generator.generate_motorpools` / the `migrator` save-inject);
    `MotorpoolPopulator` rebuilds its vehicle groups **ephemerally each mission** from the CP's current
    reserve (`ai_ground_planner.reserve_armor_for`, a `plan_groundwar`-exact split), capped by
    `motorpool_spawn_cap` (10). The vehicles spawn **parked, weapon-hold, unmanned, no datalink**
    (`MotorpoolGenerator`) — present and strikeable but inert. **1:1 grind, no economy**: each killed
    reserve vehicle decrements `base.armor` by one via a **distinct loss category**
    (`UnitMap.motorpool_units` → `Debriefing` → `missionresultsprocessor.commit_motorpool_losses`), so
    a depot strike forces a repurchase next turn but — unlike a front-line casualty — **never shifts the
    front line**; losses show on the debrief ("Motorpool units lost" + "`<type>` from motorpool"). Gated
    `motorpool_enabled` (Campaign Management, default **ON**) + `motorpool_spawn_cap`. **Red Tide authors
    one** near **Haina** (the forward Soviet base at the Fulda Gap — "bomb the motor pool before its armor
    reaches the front"; headless-verified: the `Garage_A` binds to Haina/RED and materialises one
    `MotorpoolGroundObject`, its parked vehicles filling as red procures armor since `base.armor` is the
    purchase stock, empty at turn 0); every other campaign is **inert until it places a `Garage_A`**. The
    §3 recon fog leaves the depot an **exact** marker (category `motorpool` isn't concealable). Not
    supported in Pretense. Tests `tests/**/test_motorpool_*.py` + `tests/ground_forces/test_reserve_armor.py`
    + `tests/fourteenth/test_red_tide_motorpool.py`; features doc §56, checklist B8 — needs an in-game
    pass (Red Tide, a couple of turns in for red to stock reserve).
57. **Air-droppable minefields (convoy interdiction)** — DCS has no mine object, so the 414th
    **fakes** area mining: a blue jet air-drops a **CBU-99** cluster dispenser (the **"Aerial
    Minefield"** loadout on the A-7E / F/A-18C / AV-8B — every dispenser pylon verified pydcs-legal;
    CBU-99 was freed from the A-7E CAS loadout so it is the *exclusive* dispenser) and the impact
    area becomes a **scripted proximity minefield** — a periodic scan for enemy (RED) ground within
    a radius → `trigger.action.explosion` at the tripping unit. Mines work **the same mission** they
    are laid (mine the road just ahead of an inbound convoy to stop it now); each crossing vehicle
    trips at most one mine, a field clears when its charges are spent, and every active field carries
    a friendly-only F10 mark. **No phantom spawns**: the explosion kills a real, tracked convoy unit,
    so the loss is recorded natively at debrief (units that never arrive) — the plugin
    (`resources/plugins/minefields/`, opt-in `defaultValue` false) owns no kills beyond the
    explosion. Blue-only v1. **Cross-turn persistence** (`air_droppable_minefields`, Mission
    Generation → Battlefield life, default **OFF**): a field left undisturbed at mission end is
    carried across the turn — the plugin mirrors every managed field's `{id, x, z, radius, charges}`
    into the new `minefields_state` Lua→Python channel (declared in `dcs_retribution.lua` + the
    serialized `game_state`, `dirty_state`-flagged), `game/debriefing.py` parses it,
    `MissionResultsProcessor.commit_minefields` → `game/fourteenth/minefields.py`
    `reconcile_minefields` folds it into `game.minefields` (a known field takes the plugin's
    authoritative charge count / is removed when exhausted; a surviving newly-laid field is promoted
    to a fresh-id record; an un-reported field is left untouched — a field nobody drove over does not
    decay), and `game/missiongenerator/minefieldluadata.py` (`populate_minefields_lua`) re-emits the
    survivors as `dcsRetribution.minefields` so the plugin re-arms them next mission, exactly where
    they were. Same-turn mining works with just the plugin enabled; the setting adds the persistence.
    The Lua harness gained a `WeaponFake` + `fire_shot` (the snake-and-nape SHOT path had none).
    **Auto-plan** (`auto_plan_minefields`, default **OFF**, preseeded ON in Red Tide, which fields
    the Hornet): `game/fourteenth/convoy_mining.py` `plan_convoy_mining` (hooked in `plan_missions`
    before the commander) frags one BAI sortie a turn **at an enemy convoy**, flown by a blue
    A-7E/Hornet/Harrier with the `"Aerial Minefield"` dispenser loadout **forced by name** onto the
    flight's members — the AI (or player) drops the CBU-99 and the plugin lays the field on the
    convoy's road. **Web overlay (LANDED):** `MinefieldJs` on `GameJs` (BLUE-only, empty when off) +
    the client `minefieldSlice`/`MinefieldsLayer` (a gold dashed marker per live field in the
    map-layers panel — a "Minefields" toggle, default on, Friendly group); generated-TS hand-added,
    validated with `tsc` + the client jest suite (scratchpad-copy + node_modules-junction workaround,
    the §53 `SupplyLayer` pattern). The `.miz` drawing is intentionally skipped (the plugin's live F10
    marks track fields as they deplete, which a static drawing can't). Needs the CI client rebuild.
    (`resources/plugins/minefields/`, `game/fourteenth/minefields.py`,
    `game/fourteenth/convoy_mining.py`, `game/missiongenerator/minefieldluadata.py`,
    `game/missiongenerator/luagenerator.py`, `game/debriefing.py`, `game/coalition.py`,
    `game/sim/missionresultsprocessor.py`, `game/game.py`, `game/settings/settings.py`; features doc
    §57, checklist B9 — needs an in-game pass.)
58. **Mission-start briefing popup** — the on-screen greeting the professional DCS campaigns show
    when you slot in, brought to the dynamic campaign. When a pilot enters an aircraft, a short card
    appears for ~12 s: **campaign name · Mission N · date · mission time**, then that pilot's own
    **callsign · aircraft · task · departure field** — so you always know what you're flying before
    opening a kneeboard — and a **second card is flashed right after it** (held the same duration):
    the startup/taxi instruction, `<callsign> — Get started up, Contact ground @ 249.50 when ready
    to taxi` (249.50 is a fixed squadron freq, a plugin option). A **short beep plays as each card
    flashes** (`outSoundForGroup` — which, unlike `outPicture*`, DOES have a per-group variant, so
    the beep is per-pilot on their slot-in), from an **original** `briefing-beep.wav` bundled with
    the plugin (`otherResourceFiles`) — NOT lifted from any paid campaign; a `playSound` option mutes
    it. **Display only** — no gameplay-model change, no `.miz` object, nothing persisted; the plugin
    owns nothing but the text (+ the one bundled sound).
    **It is TEXT, not a styled image, by DCS constraint:** the Lua API has `outTextForGroup` (per
    flight) but **no `outPictureForGroup`/`outPictureForUnit`** — pictures only go to *all* players
    or a *whole coalition* ([ED wishlist](https://forum.dcs.world/topic/371036-outpicturefor-lua-mission-scripting-functions/);
    0 `outPicture*` calls in MOOSE/plugins vs 31 `outTextForGroup`). A per-pilot styled card is
    therefore impossible in MP (the pro campaigns get the image look only because they are hand-built
    *single-flight* missions where `outPicture`-to-all == the one pilot). The emitter
    (`game/missiongenerator/briefingluadata.py`, `populate_briefing_lua`, wired in `luagenerator.py`)
    emits `dcsRetribution.briefing` — a shared **header** (campaign / mission = **raw `game.turn`**,
    so the number matches the kneeboard's turn numbering — `turn+1` was confusing, card "Mission
    2" next to the kneeboard's "Turn 1"; 0-indexed, so a fresh campaign reads "Mission 0" / "Turn 0"
    alike; since the §30 cover retired 2026-07-13 this popup is the deck's only op/turn/date banner
    / date = `game.current_day` / clock = `game.conditions.start_time`) + one **record per
    player-crewed flight** (`client_units` non-empty), keyed by `FlightData.group_name` — only when
    `mission_briefing_popup` is on and the mission has a player-crewed flight (else no node ⇒ the
    plugin no-ops). All fields are single-line strings; the Lua composes the multi-line card with
    real newlines (`escape_string_for_lua` doesn't escape `\n`, and a literal newline inside a Lua
    5.1 `"..."` is a parse error — the reason it is NOT pre-formatted in Python). The new
    `resources/plugins/briefing/` plugin shows each pilot their own cards: an **`S_EVENT_BIRTH`
    handler** (fires whenever a pilot slots in — mission start in SP, any slot-in / rejoin on a
    server; **players only**, `getPlayerName() ~= nil`, so AI births are ignored) plus a **one-shot
    mission-start sweep** after a short grace (catches a pilot already seated whose birth fired before
    the handler registered), the two deduped by a small per-unit debounce (> grace, so a genuine
    re-slot still re-shows); the whole sequence waits a **`startDelayS` (default 5 s) delay after
    slot-in** before the first card + beep (so it doesn't slam up the instant the pilot takes the
    seat), and the **taxi card is scheduled `DURATION` s after the briefing card** (nested
    `timer.scheduleFunction`, each re-fetching the group by name so a pilot who left is skipped).
    Symmetric in code but effectively BLUE-only (players are blue). The Lua harness gained
    `outTextForGroup` + `UnitFake:getGroup()` / `getPlayerName()` + a `fireBirth` helper. Gated
    `mission_briefing_popup` (Mission Generation → Battlefield life, default **ON**; the plugin's own
    `defaultValue` is also ON). Card duration, startup grace, the **slot-in delay** (`startDelayS`,
    default 5), the taxi **ground frequency** (`groundFreq`, default "249.50"), and the **beep toggle**
    (`playSound`, default true) are plugin options. Tests
    `tests/missiongenerator/test_briefingluadata.py` + `tests/lua/test_briefing_runtime.py` (the
    harness gained an `outSoundForGroup` stub). **First MP fly FAILED (2026-07-11 Red Tide M1) —
    root-caused + reworked same session:** on a paused dedicated server every pre-start slot-in
    shares frozen sim t=0, so all cards fire ~5 s after UNPAUSE (intended-by-physics — the sandbox
    has no wall clock; documented in the plugin header), and the beep that should make pilots look
    up was silently dead — an in-miz sound resolves ONLY via its `l10n/DEFAULT/` archive path, and
    the plugin passed the bare basename (fails with no error). Fixed: beep path prefixed, every
    card/taxi fire now logs `BRIEFING|: card -> <group> gid=<id>` (the "sent but unseen" vs "never
    sent" discriminator), a skipped fire clears the debounce, and a nil `getPlayerName` at BIRTH
    gets one +2 s re-check (the MOOSE #806 timing race). (`game/missiongenerator/briefingluadata.py`,
    `game/missiongenerator/luagenerator.py`, `resources/plugins/briefing/`,
    `game/settings/settings.py`; features doc §58, checklist B10 — **VERIFIED 2026-07-15**, the
    reworked cards + beep confirmed working by user report; a dynamic-slot pilot gets no card, by
    design — dynamic-slot jets aren't player-crewed ATO flights.)
59. **Ground AI sleep (graduated culling)** — the middle tier the binary cull model lacks (the
    2026-07-12 "cull settings feel all or nothing" MP-performance complaint): with
    `perf_ground_ai_sleep` on, rear-area **garrison** vehicle groups keep existing (visible,
    strikeable, kills record natively — the map and debrief can't tell) but their DCS controller is
    switched **off** (`setOnOff(false)`, the primitive under MOOSE `GROUP:SetAIOnOff`) while no
    aircraft is near, and **woken** whenever any aircraft — either side's, human or AI — closes
    inside the wake radius (15 NM, floored at 10 NM so a garrison's embedded SHORAD escorts are
    awake long before their envelope), with 1.25× sleep hysteresis and an `S_EVENT_HIT` immediate
    wake so a standoff shot never lands on a group that can't react. **Safety is decided in Python
    as a positive list** (`game/missiongenerator/aisleepluadata.py` → `dcsRetribution.aiSleep`):
    only `armor`-category TGO groups with alive vehicles, minus `concealed`/`map_hidden` TGOs —
    exactly the COIN/ambush scripted movers whose routes a sleeping controller would kill; air
    defense (`aa`/`ewr` — MANTIS's, plus the runtime-SAM-toggle crash history), `missile`/`coastal`
    (§49 movers), ships, motorpool (already inert) and buildings are never emitted, and
    FLOT/convoys/Combat-SAR spawns aren't TGOs so the walk can't touch them. The `aisleep` plugin
    polls every 30 s after a 60 s grace (radius/cadence/grace are plugin options; plugin
    `defaultValue` ON so the setting is the only gate, the §36 lesson). Composes with culling
    (untouched, the far tier): sleep what you keep, cull what should never exist. Default **OFF**
    until flown; NOT preseeded in Red Tide (feature-locked) — flip it for the next MP event. Tests
    `tests/missiongenerator/test_aisleepluadata.py` + `tests/lua/test_aisleep_runtime.py` (the
    harness gained a `ControllerFake` + `aiOnOff` records + `fire_hit`).
    **AAA gun sites added 2026-07-19** (`perf_aaa_site_sleep`, default **OFF**,
    `enabled_when=perf_ground_ai_sleep`) — off a "10 fps on the ground" report, the flown 1968
    Yankee Station miz measured **2–4× every other campaign** (738 ground vehicles / **367 AAA** /
    1085 statics / 1328 groups vs Red Tide's 185/29/133/433), with AAA at **4–12×**, while the
    emitter managed **16 of 121** vehicle groups — because the mass is `aa`-category. (Diagnosis
    that ruled out the rest: **13 objects within 25 km** of the player spawn, and ANTIFREEZE from
    ~1 min in while cold-starting on that empty ramp ⇒ global sim load, not scenery or GPU. The
    density itself is deliberate Vietnam doctrine; nobody had measured its cost.) `aa` sites now
    join the list behind **two independent guards** (`_air_defense_group_may_sleep`): every alive
    unit's DCS `detection_range` ≤ `AAA_SLEEP_MAX_DETECTION` (10 km) — comfortably inside the
    plugin's 10 NM (18 520 m) wake **floor**, so a site is always awake before anything reaches the
    edge of its own sensor envelope and both its IADS contribution and its trigger moment are
    unchanged (era guns report 5 km, KS-19 0; **Gepard 15 km / Tor 25 km / every search-track radar
    35–300 km stay awake**; an unmeasurable unit fails safe) — **and** the group's `IadsRole` must
    not be in `MANTIS_MANAGED_ROLES` (`SAM`/`SAM_AS_EWR`/`POINT_DEFENSE`), the roles MANTIS *writes*
    alarm state/EMCON to. It only *reads* the rest, which is why an **EWR-role** gun site is
    eligible — and since `GroupTask.AAA` → `IadsRole.EWR`, that is the case carrying the whole win.
    Dedicated `ewr` sites stay ineligible outright, and the category gate still excludes the §49
    `missile`/`coastal` movers — load-bearing, since their launchers report detection 0 and would
    pass the sensor guard. Measured: Yankee Station's sleep set 26 → ~54 groups (~400 units); Red
    Tide correctly keeps its Tor/Gepard groups thinking. Same-day sibling fix: the §33 flak
    gauntlet's tick was calling `getPoint()` per (aircraft × gun) — ~1,100 DCS API calls per
    aircraft per 2.5 s tick at 367 guns — now positions are cached at the 30 s AAA refresh and the
    arithmetic range test gates the liveness calls (~6), behavior identical.
    (`game/missiongenerator/aisleepluadata.py`, `game/missiongenerator/luagenerator.py`,
    `resources/plugins/aisleep/`, `resources/plugins/vietnamops/`, `game/settings/settings.py`;
    features doc §59, checklist B11 — needs an in-game pass.)
60. **SAM guidance-radar redundancy (two track radars per site)** — the 2026-07-12 Red Tide
    finding: every SAM layout fielded exactly ONE engagement radar, so a single HARM on it was a
    functional site kill (launchers alive but blind). Every SAM layout now fields **two** guidance
    radars — the Track Radar slots (generic 2/4/6-launcher + SA-2 ×4 / SA-3 ×2 / SA-5 ×2 / S-350 /
    NASAMS-3), the S-300/HQ-22 `S-300 Site TR`, **both channels** of the SA-2/SA-3 mixed site
    (its Fan Song rides the `S-300 Site CP` slot), the SA-6's combined 1S91 STR, and the NASAMS
    Sentinel / Sky Sabre Giraffe (their engagement radar lives in the "Search Radar" slot); the
    Patriot family already fielded 2 STRs, now CI-locked. Pure layout data — `unit_count: 2` in
    `resources/layouts/anti_air/*.yaml` + a second radar **position** added to the shared `.miz`
    templates (8/6-launcher circles + semicircle, 2_Launcher, S-300 site; 45–121 m from the
    primary, ≥25 m from everything — one HARM blast can't take both), because `generate_units`
    hard-caps at the template's position count. Buy menu maxes/defaults follow automatically;
    site price rises by one radar. Deliberate limitation: presets routing a lone STR through a
    *generic* layout's Search Radar slot (NASAMS-B/C, IRIS-T SLM, THAAD) keep a single engagement
    radar — doubling that shared slot would double every generic site's pure search radars too.
    TELAR systems (SA-11/17, Roland, SHORAD) never had the single point of failure. No setting,
    no plugin; NEW game required. Tests `tests/armedforces/test_sam_radar_redundancy.py`.
    **Balance abstraction, not TO&E**: a real legacy fire unit fields ONE engagement radar, so the
    doubling is a deliberate anti-single-HARM-kill call, closest to reality on the strategic systems
    (S-300/S-400, Patriot); the faithful regiment-of-single-radar-fire-units alternative + two other
    realism directions (revetment geometry, acquisition-radar separation + decoys) are worked out
    with verdicts in `docs/dev/design/414th-sam-site-realism-notes.md` (which also records the
    don't-stack-them tension: never run §60 doubling AND a regiment model on the same system).
    (`resources/layouts/anti_air/`; features doc §60, checklist B12 — needs an in-game pass.)
61. **Host red-interceptor scramble (F10 bandit spawner)** — the game master's "give the boys
    something to shoot" button (the M1 "quiet after the first wave" debrief): with
    `host_red_scramble` on, the mission carries cold late-activation **clone templates of the
    red faction's fighters** (one 2-ship per distinct type, best BARCAP airframe first, capped
    at 4 — built by `AircraftGenerator.spawn_red_scramble_templates`, the QRA pattern,
    `claim_inv=False`) and an F10 **"HOST: Red Scramble"** menu that SPAWN-clones a **2/4-ship
    at any red airfield** (menu lists up to 9, nearest-front first) or — one **EMERGENCY**
    press — at the base nearest the airborne blue players. Spawn default = the QRA **air-spawn
    scramble profile** (field elev + 760 m AGL, 300 kt; ground spawns die on packed ramps —
    the intercept-plugin history; `takeoff` hot/runway are options), weapons-free at spawn,
    then a GCI loop **re-vectors every live bandit onto the nearest airborne BLUE fighter**
    (players outrank nearer AI) via a hard `AttackGroup` task until dead. **Menu visibility is
    the plugin's `hostPlayers` option** — comma-separated names or **fragments**, a
    case-insensitive plain-substring match (no Lua patterns — names carry magic chars), so the
    414th's changing-prefix convention `"<flight> 1-x | Flash"` gates on the static `Flash`
    tag alone → per-group menu on slot-in/sweep, the §58 pattern; empty = all-BLUE coalition
    menu, and the `REDSCRAMBLE|` log line says which mode armed. **Spawns are untracked event
    content by design** (the §20 drop-spawn cheat precedent, NOT a §35/§37 violation —
    deliberate host action, default-OFF setting): red pays nothing, a dead clone changes
    nothing at the turn boundary; bandit kills of players record natively. Gated
    `host_red_scramble` (Mission Generation → "Host & event tools", default **OFF**),
    preseeded ON + the `redscramble` plugin preseeded ON + `redscramble.hostPlayers: Flash`
    in **Red Tide** (the §36 lesson) ahead of the Friday 2026-07-17 regeneration.
    Tests `tests/missiongenerator/test_redscrambleluadata.py` +
    `tests/lua/test_redscramble_runtime.py` (the harness gained group F10 menus,
    `coalition.getPlayers`, `Controller:setTask` recording, and AIRBASE/SPAWN fakes).
    (`game/missiongenerator/redscrambleluadata.py`,
    `game/missiongenerator/aircraft/aircraftgenerator.py`, `resources/plugins/redscramble/`,
    `game/settings/settings.py`; features doc §61, checklist B14 — needs an in-game pass.)
62. **Squadron-sequenced Hornet/Tomcat board numbers (modex)** — pydcs deals every aircraft a
    **random** three-digit `onboard_num` (an unordered `set.pop()`), so Navy jets wore nonsense
    modexes. `ModexAllocator` (`game/missiongenerator/aircraft/modex.py`, held by
    `AircraftGenerator`) gives each **Hornet/Tomcat** squadron a modex block (100, 200, 300, …;
    per coalition, air-wing order, **Tomcats first** — the CVW fighter-block convention; wraps
    after nine squadrons) and numbers the squadron's jets **sequentially** within it — first jet
    X00, second X01 — in generation order (tasked flights take the low numbers, then the QRA/§61
    templates, then the ramp queens). The squadron's whole block is reserved with its pydcs
    `Country` on first use so a later same-country random draw can't collide. Curated
    `MODEX_AIRCRAFT_IDS` (FA-18C module + AI F/A-18A/C, the Heatblur F-14 variants + AI F-14A —
    Iranian Tomcats sequence too); everything else keeps the stock number. Per-mission numbering
    (the campaign has no per-airframe identity); pure generation behavior — no setting, no
    plugin, no save change. Tests `tests/missiongenerator/test_modex.py`; features doc §62,
    checklist B15 — **VERIFIED 2026-07-16** (user visual confirmation on the flown Scenic Route
    turn-3 test: DCS paints the mission's `onboard_num`, incl. the Heatblur F-14 whose
    livery-driven BORT rendering was the row's specific doubt).
63. **Ship-launched cruise missile raids** — LACM warships (the vanilla Burke/Ticonderoga
    Tomahawk shooters + the CurrentHill Kalibr `*_LACM`/`_CMP` hulls, curated in
    `LACM_SHIP_DCS_IDS`) strike shore targets via a scripted `FireAtPoint` push with the
    cruise-missile weapon flag. **Real weapons from real, tracked ships** — kills record
    natively, sinking the shooter ends the raids, the plugin owns no kills/spawns (the §35/§37
    discipline). Each launching
    group carries a **persisted campaign magazine** (`game.cruise_missile_magazines`, per-hull
    table: Burke 24 / Kalibr corvette 8, **no rearm**) debited ONLY from what the plugin
    reports fired via the new `cruise_missiles_state` Lua→Python channel (the §57 pattern —
    generation never debits, so mission re-generation is free). Two fire paths share the
    budget: **auto raids** (`plan_cruise_raids` in `game/fourteenth/cruise_raids.py` — at most
    one per side per turn, C2-first target priority then the §53 economy buildings, ≤250 NM,
    BLUE ROE-gated via §40 `roe_blocks_target`, never ships/`map_hidden`; the plugin fires
    after a launch delay with a vague "LAUNCH WARNING" cue to the defender) and a **player F10
    "Cruise Missile Strike" menu** per owning coalition (salvo onto the last F10 map marker
    from the nearest capable ship, the §34 marker pattern; **marker text `#N`/`N` sizes the
    salvo**, magazine-capped; + a "Magazine status" readout).
    Symmetric — `redfor_current`/`redfor_russia_2020` field Kalibr hulls today. Gated
    `cruise_missile_strikes` (master) + `cruise_missile_auto_raids` (Mission Generation →
    Naval strike, both default **OFF**). Tests `tests/fourteenth/test_cruise_raids.py` +
    `tests/missiongenerator/test_cruisemissileluadata.py` +
    `tests/lua/test_cruisemissiles_runtime.py`.
    (`game/fourteenth/cruise_raids.py`, `game/missiongenerator/cruisemissileluadata.py`,
    `resources/plugins/cruisemissiles/`, `game/debriefing.py`,
    `game/sim/missionresultsprocessor.py`, `game/settings/settings.py`; features doc §63,
    checklist B16 — **core loop VERIFIED 2026-07-16** (flown Persian Gulf "Scenic Route" test):
    the scripted FireAtPoint+cruise-flag push fires the exact commanded quantity on BOTH vanilla
    hulls (the "least certain" Ticonderoga flew the raid — 6 BGM-109C shots, C2 target killed
    natively; a Burke group flew the F10 call-for-fire), the raid launched inside the [240,900] s
    stagger window, and the magazine loop closed end-to-end (debrief "6 fired, 10 remaining" →
    save debited 16→10 → next turn re-targets the next command center). **OBSERVED GAP: no
    defender ever woke for a cruise raid** — 2 alive SA-15s 250 m from the impact sat idle
    through the salvo (vanilla groups run ALARM AUTO, which never goes hot for a *weapon*
    object; MANTIS EMCON detection scans units, never weapons; the MOOSE SHORAD wake lists
    carry no BGM_109/Kalibr). **Closed same day by the plugin's defender launch wake**: every
    launch sets opposing ground AD groups within 8 NM of the aimpoint alarm-RED (alarm state
    only, never `enableEmission`) for ~flight time + 300 s, then restores AUTO; options
    `defenderWake`/`defenderWakeRadiusNm`/`defenderWakeExtraS`; harness-pinned. The wake is
    unflown — re-fly criteria in `414th-cruise-missile-raids-notes.md` "The intercept gap".
    A second flown test (turn 3, pre-wake build) confirmed the linked-PD variant in the air
    AND that **naval AD intercepts natively** — a red Krivak pair killed 2/6 Tomahawks with
    SA-N-4s (ships are always hot), so the saturation game works wherever a defender can
    shoot; the wake gives ground PD the same chance (link-dark is alarm-GREEN in this fork's
    bridge, so the alarm-RED override reaches it). Still unflown: `#N` marker salvo sizing,
    CH Kalibr hulls, red-side raids.)
64. **Carrier deck spawn policy (six-pack last resort + MP slot timing)** — the 2026-07-16
    supercarrier finding: AI taxiing to the cats jam against the player, because the old
    `player_flights_sixpack` boolean (ON) parked the **slowest** thing on deck (a human,
    10-minute cold start) on the **six-pack** — the first-filled spots, squarely in the taxi
    lane to the bow catapults — while the AI spawned in the far spots and squeezed past. DCS's
    only deck-parking lever is **spawn timing** (the mission-start wave fills the six-pack;
    anything activated ≥1 s later is placed elsewhere — the dcs_liberation#1309 trick that
    already kept AI off it), so the boolean became the **`CarrierDeckPolicy` enum** (§16
    boolean→enum migration pattern; ON→`SIXPACK_FIRST`, OFF→`LAST_RESORT`): under the new
    **`LAST_RESORT` default**, player carrier ground starts take the same 1 s placement
    activation as AI — parked clear of the taxi flow, the six-pack left as overflow capacity —
    and `SIXPACK_FIRST` keeps the legacy behavior. **The MP slot-timing fix rides along** (both
    modes): a TOT-delayed client carrier COLD flight was late-activated its FULL delay, so its
    slots didn't exist in the MP slot list until push time ("your flight is delayed to start");
    it now spawns **uncontrolled** like its airfield counterpart (slots live from ~mission
    start, `StartCommand` holds only the AI members to the push, + the 1 s placement activation
    under last-resort). WARM/RUNWAY delayed clients keep full-delay late activation (a hot jet
    can't wait), AI keep late activation (deck crowding). **Single player ignores the
    immediate-spawn setting (2026-07-18, user call):** `never_delay_player_flights` ("Spawn
    player flights immediately") is an MP option — it keeps every slot selectable from mission
    start — so a mission with **fewer than two player slots** (the `AircraftGenerator.use_client`
    predicate, now threaded into the delay decision as `WaypointGenerator`'s `multiplayer`)
    ignores it: the lone player flight is delayed to its planned start time like the AI, with
    cold starts **late-activating at their planned engine-start time** (the uncontrolled-at-t=0
    path exists only for MP slot availability and would leave the lone player idling in the pit
    anyway); warm/runway keep the existing full-delay late activation, the ten-minute short-hold
    rule survives, MP + AI byte-identical. Taxi *routing* itself is engine AI —
    no mission-level control (the AI F-14A's forced cat starts are the precedent) — and
    same-group wingmen tailgating the player is unfixable at mission level. No plugin/Lua.
    Tests `tests/missiongenerator/test_carrier_deck_policy.py` +
    `tests/settings/test_carrier_deck_policy.py`.
    (`game/missiongenerator/aircraft/waypoints/waypointgenerator.py`,
    `game/settings/settings.py`; features doc §64, checklist B17 + B26 — needs an in-game pass:
    does DCS overflow delayed spawns INTO the six-pack once the deck is full, deck
    behavior with several client flights parked uncontrolled from mission start, and where
    DCS puts the SP pilot while a late-activated Player-skill flight waits to materialize.)
65. **Curated carrier comms (CV Operations Data cleanup)** — DCS auto-renders the yellow "CV
    Operations Data" kneeboard page straight from the miz (it cannot be restyled, only fed better
    data), and the generator fed it allocator junk: the boat "named" `0796 | CVN-71 …` on the
    Callsign line, TACAN **1X** with a `random.choice` ident re-rolled every mission, Link 4 on a
    random inter-flight UHF (255.0), a fresh random ATC every turn. Now every vanilla hull carries
    a curated **boat card** (`game/data/carrier_comms.py`, keyed by pydcs ship id — the pro-campaign
    "Mother card" convention off the cataloged Raven One kneeboards): TACAN = **hull number** where
    T/R-legal (CVN-71→71X `TRO` … CVN-75→75X `HST`; Forrestal 59→64X `FID`, Tarawa→41X `TAR`,
    Kuznetsov 35X/36X `KUZ`), hull-keyed ICLS (11–15, Forrestal 9, Tarawa 1), Link 4 in the real
    ACLS **336 MHz band**, stable per-hull ATC (304–312). Resolved in
    `GenericCarrierGenerator._resolve_*` with stored-values-win precedence (base-dialog/persisted
    values untouched); a map-owned channel degrades via `TacanRegistry.alloc_near` to the **nearest
    valid free neighbor** (Bagram owns 74X on Afghanistan ⇒ the ER Stennis gets 73X), never to 1X;
    ICLS moved to a shared-pool `IclsAllocator`; **every value persists to the control point** so
    the card is stable across turns (ATC/Link4/ICLS used to re-roll). The flagship unit is named by
    its hull name (named before `_register_theater_unit` so kill-tracking keys the same string;
    duplicate-class boats keep the unique prefixed name). Mod carriers keep the legacy path.
    **CP naming follows the hull (2026-07-17):** the carrier CP name (drawn at game start from the
    faction pool) keys the supercarrier upgrade, and a name outside the map ("CVN-74 John C.
    Stennis" has no Supercarrier model) sailed a mislabeled CVN-71 (the flown Scenic Merged boat) —
    `hull_consistent_carrier_name` (`start_generator.py`) now deals a supercarrier game only names
    the upgrade maps (`STENNIS_SUPERCARRIER_UPGRADES`, the name picks WHICH supercarrier) and
    otherwise prefers the hull's own display name (free Stennis = CVN-74, Tarawa = LHA-1); pool
    fallback preserved, unmapped names keep the legacy CVN-71 upgrade so existing saves keep their
    boat. New games only; tests `tests/test_carrier_naming.py`. Pure
    generation behavior — no setting, no plugin, no save change; headless-verified end-to-end on
    Enduring Resolve. Tests `tests/test_carrier_comms.py`; features doc §65, checklist B18 — needs
    an in-game pass (the CV page renders the card; the beacons radiate for a recovery).
66. **Generated-mission archive** — every turn generates to one fixed path
    (`Missions/retribution_nextturn.miz`, hardcoded in `QTopPanel.launch_mission`), so each
    **Take off** overwrote the mission just flown — lossy for a fork that root-causes its
    in-game findings *from the flown miz* + its Tacview, and the DM's `Missions` folder had
    already grown the workaround by hand (`Red Tide M1.miz`, `… Backup.miz`). **The fixed
    output does not move** (the wiki/bug template/server workflow all name it, and nothing
    downstream ever depended on the name: DCS writes `state.json` to a fixed path of its own
    and the debrief poll matches by **mtime vs `miz_generated_at`**, never by filename).
    `game/fourteenth/mission_archive.py` `archive_mission` **additionally** copies each
    generation to `Missions/Retribution Archive/<campaign>_turn<NN>_<stamp>.miz` — under
    `Missions/` (not the `Retribution/` tree) because DCS's mission browser lists those
    subfolders, so an archived turn opens straight from the game; the turn is the raw
    `game.turn` (the §58 briefing card's numbering) and **the timestamp is what stops the
    clobber** — re-generating a turn writes a new archive instead of overwriting the flown
    copy. Hooked in `MissionSimulation.generate_miz` (engine-side, not the Qt button).
    **Never breaks Take off** (best-effort; an unwritable disk or a headless
    `persistency.setup()`-less run is logged and swallowed — the original is already written)
    and **only ever prunes its own output** (keeps the newest `KEEP_ARCHIVED_MISSIONS` = 20,
    scoped by a regex matching only generated names, so a hand-named miz in the folder is
    never deleted). No setting — a bounded ring buffer, and a toggle you can forget defeats
    the point (§42/§43 precedent). Tests `tests/fourteenth/test_mission_archive.py`; features
    doc §66 — no in-game pass needed (a file copy, no DCS runtime).
67. **Weather-aware auto-planning** — the theater commander reads the sky (§47 gave the
    campaign an evolving weather system; the planner never consulted it — zero references to
    weather/night anywhere in `game/commander/`). `game/fourteenth/weather_planning.py` +
    two couplings, both coalitions (same sky): **rain/storm suppresses the automatic TARPS/
    drone recon add-on** (`recon_suppressed` gates `PackageFulfiller._maybe_plan_tarps_recon`
    — cameras photograph cloud deck; same never-scrubs contract as a missing squadron;
    player-planned recon untouched), and **a thunderstorm demotes low-level visual attack**
    (`demote_weather_hostile_methods` moves `PlanFrontLineCas`/`AttackBattlePositions`/
    `InterdictReinforcements` to the offensive tail in `PlanNextAction._offensive_order`,
    AFTER the §40/§55 emphasis — soft demotion, nothing removed; rain does not demote).
    **Night is deliberately absent** — no per-airframe night-capability data exists, and
    demoting night CAS would ground an A-10C II alongside an A-1. Gated
    `weather_aware_planning` (Air Doctrine, default **ON** — clear skies are byte-identical).
    Tests `tests/fourteenth/test_weather_planning.py` + the storm case in
    `tests/test_armed_recon_planning.py`; features doc §67, checklist B19 — needs an
    in-game pass.
68. **Adaptive procurement (posture-coupled spending + SAM repair)** — the AI economy reads
    the war (`game/fourteenth/adaptive_procurement.py`; `ProcurementAi` was a fixed slider +
    doctrine ratios + `random.choice`, coupled to nothing built since). Three couplings:
    **(1) posture/phase budget split** — a surging RED shifts auto-spend toward ground
    (+0.15 at the §55 intensity midpoint, scaled 0.5+intensity), a consolidating RED
    husbands ground and rebuilds air (−0.15); BLUE leans air-first under Tier-0 `rollback`
    (−0.10), ground-first under `offensive` (+0.10); no signal = byte-identical split;
    **(2) air-defense site repair** (own gate `auto_repair_air_defenses`, default **OFF**) —
    nothing ever rebuilt a dead SAM, so Rollback was a one-way ratchet; each side's AI now
    repairs ≤ `MAX_AIR_DEFENSE_REPAIRS_PER_TURN` (2) dead units/turn at surviving `aa`/`ewr`
    TGOs at full unit price (the player's base-card repair), degraded sites + radars first,
    with the threat-poly invalidation and wreck-marker cleanup the flip needs; **command
    centers/comms are never repaired** (§51/§52 kills stay permanent); BLUE only auto-spends
    when `automate_runway_repair` delegated repairs, RED always; shows as its own Finances
    row; **(3) price-weighted ground-unit choice** (capability proxy — T-72s over gun trucks,
    still a weighted roll). Gated `adaptive_procurement` (Campaign Management → Commander
    economy, default **ON**); NOT preseeded (Red Tide feature-locked). Tests
    `tests/fourteenth/test_adaptive_procurement.py`; features doc §68, checklist B20 — needs
    an in-game pass.
69. **Cross-package SEAD-before-strike coordination** — packages were timed independently,
    so a strike could arrive at a defended target half an hour BEFORE the SEAD package
    tasked against the SAM covering it. `MissionScheduler._coordinate_sead_windows` (after
    TOT assignment, before the §8 carrier stagger) retimes every movable AI strike-class
    package (`STRIKE`/`BAI`/`OCA_*` — Armed Recon/AIR ASSAULT deliberately stay spread)
    whose target sits inside a threat ring a SEAD/DEAD package is servicing into the window
    just behind the **latest** covering suppressor (`coordinated_strike_tot`:
    `SEAD_WINDOW_LEAD` 2 min after the provider TOT, `SEAD_WINDOW_DURATION` 8 min; naked
    strikes delay in, far-late strikes pull back, in-window TOTs keep, physics always win
    via `TotEstimator.earliest_tot`). Several strikes mass behind one SEAD — the push is
    the point. The §8 discipline holds: player/ASAP packages never move, but a
    **player-flown SEAD still opens a window the AI pushes behind** (providers read-only);
    symmetric per coalition. Gated `sead_strike_coordination` (Air Doctrine, default
    **ON**). Tests `tests/test_sead_strike_coordination.py`; features doc §69, checklist
    B21 — needs an in-game pass.
70. **COMINT collection (blue-side communications intelligence)** — the §51 mirror (design
    note `414th-comint-notes.md`; this is its **C0**, the campaign take — DCS exposes no way
    to intercept real comms, so COMINT is a presentation+gating layer over ground truth, the
    §3 fog shape): blue reads the enemy's emitting C2 net. Sources = alive red
    `comms`/`commandcenter` TGOs (the same objects §51 jams from and §52 decapitates —
    **bomb-it-or-tap-it is emergent**, never special-cased) + alive concealed COIN spawns
    (insurgents run on radios, so the take works on the front-less COIN laydowns). **Tier 0**
    (net silent) ⇒ nothing; **Tier 1** (net up) ⇒ the ambient take — the §55 posture *detail*
    is now EARNED (`gated_posture_detail` wraps the `record_sitrep` feed; a silenced net dries
    it up; the coarse posture chip stays free); **Tier 2** (a blue collector — a §2 JAMMING
    flight or any drone, "a drone is always listening" — flew last mission and survived,
    stamped by `record_comint_collection` at debrief commit; a shot-down collector banks
    nothing) ⇒ a **tasking leak** (the most threatening red offensive package flying THIS
    mission — Strike > OCA > BAI > Anti-ship class rank then mass, a pure sort so regeneration
    never rerolls — coarsened to class/size/objective/TOT ± 30 min) + a **reveal**
    (`apply_comint_reveal` at `initialize_turn` snaps ONE concealed enemy site within 60 km of
    an alive source to exact via the normal discovery flip + `events.update_tgo`; `map_hidden`
    §50 ambush teams are NEVER eligible; a per-turn stamp keeps re-inits from snapping a
    second). Surfaced as a **COMINT block under the Mission Info SITREP band** (the §30
    no-new-pages rule; Python-only, no client rebuild). Zero planner coupling (§3 `viewer=None`
    discipline — informs the human only), zero force-model change; BLUE-only. Gated
    `comint_collection` (Campaign Management → Campaign features, default **OFF**; NOT
    preseeded — Red Tide is locked; post-M2 candidates = Red Tide + both COIN campaigns).
    **C1 LANDED same day — the audible UHF red net**: `plan_red_net`
    (`game/missiongenerator/rednetluadata.py`, the §51 plan slot) assigns each alive enemy
    C2 node a **deterministic x.500 MHz UHF AM frequency** (crc32 off the node name — same
    spot on the dial every mission; off the whole-MHz blue-allocation grid by construction,
    GUARD's slot skipped, registry-reserved, collisions probed in sorted-name order) and the
    `rednet` plugin (`defaultValue` ON, the §36 lesson) keys **windowed, staggered** (§49)
    looped CW traffic — an original synthesized morse clip (`rednet-cw.wav` via
    `otherResourceFiles` → `l10n/DEFAULT/`, the §58 lesson) — from the node's position via
    named `radioTransmission`/`stopRadioTransmission`: tune it to hear the enemy, home on it
    in the DF fleet (F-4E / F-14 ARC-182 DF / F/A-18C UFC ADF / F-5E), and a killed node goes
    off the air (vendored MANTIS `node_dead`). `powerW` = range not loudness (§51). Gated
    `red_comms_net` (Mission Generation → **Comms war** — the §51 pair + this moved to their
    own FIELD_LAYOUT section, Battlefield life was at the §28 13-field cap; default **OFF**).
    **C2 LANDED same day — the clandestine hunt + the findability tie**: concealed COIN
    spawns (cells/IED teams/HVT — `coin_spawned`+`concealed`; `map_hidden` §50 teams
    hard-excluded from BOTH the emitter and `comint_sources`) and any authored concealed
    comms TGO transmit as **clandestine stations** on a short-window/long-gap hunt schedule
    (`clandestineWindowSec` 20 / `clandestineGapSec` 480) — the §3 circle is the search
    area, the needle cut closes it, the COIN campaigns field it with zero authoring — and
    the COMINT kneeboard block (Tier ≥1) **briefs the active nets** (fixed stations by
    name + freq + area; clandestine ones as "suspected clandestine net @ … — <area> area",
    never the identity; capped 5 + "+N more") via `MissionData.red_net` →
    `KneeboardGenerator(red_net=…)`. **The design note's C0–C2 arc is COMPLETE** (an
    authored static field-site TGO stays deferred until a campaign wants the loader
    convention). Tests `tests/fourteenth/test_comint.py` +
    `tests/missiongenerator/test_rednetluadata.py` + `tests/lua/test_rednet_runtime.py`;
    features doc §70, checklist B22 (in-app) + B23 (in-game).
71. **Expanded F-4E Weapons Pack (AGM-78/-88 Weasel fits)** — the upstream #663/#733 mod
    support (DSplayer's community weapons pack for the Heatblur F-4E), restored to the
    curated wizard Mods page (the fork's scrub had dropped the checkbox + `ModSettings`
    pass-through while the `pydcs_extensions` module and the faction inject/eject wiring
    stayed — `eject_F4E()` ran on every game since, so the OFF path is battle-tested) and
    actually **utilized**: the pack's two big ARMs are wired into loadouts with the
    **AGM-78B Standard preferred** (user calls 2026-07-18 — first HARM-only, then "make
    [the AGM-78] the preferred one"; the rest of the arsenal stays payload-editor-only).
    New **expanded-weapons payload convention** in `Loadout`: fits named with
    `EXPANDED_WEAPONS_SUFFIX` (`" (XW)"`) are tried FIRST for their task
    (`default_loadout_names_for` prepends `"Retribution <task> (XW)"` — a no-op for
    airframes shipping none) but picked only while `pylons_allow` verifies every store
    against the **live pydcs pylon tables** that `inject_F4E`/`eject_F4E` mutate (via
    `Faction.apply_mod_settings` at generation + load) — pylon legality IS the mod
    signal — and the payload editor hides an (XW) fit whose stores don't currently mount
    (without the gate, DCS silently strips un-mountable stores at spawn = a naked
    Weasel). Fits in `customized_payloads/F-4E-45MC.lua`: "Retribution SEAD/SEAD
    Escort/SEAD Sweep (XW)" — the Shrike fits' exact skeletons with the ARM stations
    swapped to the pack's **AGM-78B** (`{LAU_77_AGM_78B}`) on the injected stations (4 on
    1/3/11/13; the tanked Escort 2 on 3/11) — plus the editor-only **"Retribution SEAD
    HARM (XW)"** (4× stock AGM-88C, `...C93` clsid; same gate, never in a task name
    chain); the stock Shrike fits are untouched and are the automatic fallback (Tanker
    War et al. byte-identical). Era + economy free: the AGM-78A/B yamls were already
    first-class (1968/1969 dates, Shrike fallback, per-target **seeker-band
    `target_overrides`** from the upstream #733 seeker work), the AGM-88C is dated at
    the family's 1984 IOC (test-tripwired), and §54 scarcity already tracks Standards +
    Shrikes + HARMs under `arm`. **Preseeded
    NOWHERE — the DM's personal option** (user call 2026-07-18, reversing a same-day Red
    Tide preseed: the real Red Tide build stays mod-free; the no-preseed + the
    no-authored-F-4E-squadron calls are pinned/recorded — the host checks the Mods-page
    box by hand on a personal game, and the air-wing dialog is the squadron path). F-4E
    SEAD task priority stays the deliberate 120 (host-frag/overflow Weasel, never
    out-competing the HTS jets). NEW game required; no plugin/Lua/Settings field
    (`ModSettings`, the §10 pattern). Tests
    `tests/fourteenth/test_f4e_expanded_weapons.py` + the Red Tide no-preseed pin;
    features doc §71, checklist B24 — needs an in-game pass (does the installed mod
    accept the generated stations; AI ARM employment; the mod-off stripped-stores
    signature).
72. **Carrier deck decorations (OCN 2 deck dressing)** — every Nimitz-family carrier
    (Stennis + SC CVN-71/72/73/75) gets its deck dressed with **ship-linked static gear
    and crew**: tow tractors / P-25 crash truck / Hyster forklift / deck hands along the
    island "street" + the 4-figure LSO platform team — placements **verbatim from the
    OCN 2 campaign's 13 missions** (Sedlo's deck dressing, extracted from the linked
    statics in the miz files), rotating between 4 curated street variants per
    (carrier, turn) crc32 seed. **The hard constraint is parking — and no static may
    stand ON a spot, ever**: the SC manual's "blocked spot is skipped" claim was
    FALSIFIED in the first flown mission for late-activated groups (Retribution's
    dominant §64 spawn path) — a CVN-73 late-activated A-6E pair spawned **INTO** the
    briefly-shipped permanent Seahawk statics (2026-07-18), so the permanent
    aircraft class was removed same day and only two provably parking-free envelopes
    ship — the LSO sponson (off-deck) and the island street (no documented/observed
    spot) — validated against **Tacview-measured spawn spots** (six-pack row
    +1/−11.5 @ y+34 on a 12 m pitch, port-quarter −84.5/−96.5 @ y−34, the Airboss
    rescue-helo spot +58.5/−31.4) plus the **clip-learned aft spots** (junkyard
    ≈ −134/−123 @ y+27/+28, the El-3 shoulder ≈ −99 @ +30 — exactly where OCN parks
    aircraft; `KNOWN_PARKING_SPOTS` + footprint-aware clearance floors are
    guard-tested against every table entry, and a guard asserts the permanent layout
    contains no Planes/Helicopters static). Cats stay clear (a cat static is a player
    collision hazard the AI clips through anyway), and **non-Nimitz decks
    (Kuz/Tarawa/Forrestal) are excluded** until their own spot evidence exists. Three-level link serialization (`linkUnit` on the
    route point / `linkOffset` on the group / `offsets` on the unit — pydcs subclasses),
    hooked in `GenericCarrierGenerator.generate()` after the §65 pass; all static types
    are base-game (`CoreMods`), no plugin/Lua/save change — existing campaigns pick it
    up next mission. Six street variants (M3/6/9/10/11/12, incl. the M6/M9 crane
    accents). Gated `carrier_deck_decorations` (Mission Generation → Carrier,
    default **ON**); the second toggle `carrier_deck_decorations_aircraft` (default
    **OFF**, user call 2026-07-18) adds the **LAUNCH-PHASE corridor dressing**: the
    round-down E-2C (M8/M1 positions) + the port junk row (M4's 5-piece set or M5's
    pair) standing ONLY during the launch cycle (the arc: shipped static → the user's
    screenshot caught it menacing the ramp crossing same day ("how can planes land
    with the E2 there?" — 5.6 m tall, 17.6 m long at the ramp; the static E-2C renders
    FOLDED, user-corrected) → cut → restored per "move the E-2 after the launch is
    over" / "we could fill the round down within reason": statics can't drive, so the
    new **`deckdecor` plugin strikes them below** (`StaticObject:destroy` = the
    elevator ride) when friendly fixed-wing traffic **genuinely runs in** low astern
    (4.5 NM/**1000 ft**/±50° cone off the emitted BRC + **ship-relative closing
    ≥30 kt** + a **400 m deck-stamp floor** + a **600 s outbound roster** (a unit
    seen on/over this deck is its own launch traffic, never a "recovery") + a
    **2-poll debounce** — the cone was falsified twice flown 2026-07-18: first the
    ~5-min launch-turnback trip, then the night re-fly struck BOTH boats early
    (GW t+74 s pre-fix / TR t+171 s on the hardened build) and the Tacview showed
    the **aft parking rows themselves** qualifying — parked jets ride the steaming
    boat 130–170 m astern of the pivot, DCS reports moving-deck units as `inAir()`,
    world-frame closing = boat speed; hardened twice, 4 harness pins) or a 35-min
    fallback timer, whichever first —
    **and the Airboss tie-in**: the sibling `airboss` plugin (default ON) opens its
    recovery window at +30 min AND steers the boat into wind while it's open, so when
    its options are present deckdecor pulls the deadline to window start −
    `airbossMarginS` (300 s) by reading the shared options table (zero MOOSE
    coupling; never the last-boat-wins `AIRBOSS` global) — with a
    "deck respotted" cue; emitter `deckdecorluadata.py` → `dcsRetribution.deckDecor`
    off `MissionData.deck_decor`; despawn only, no spawns). Guard-tested class rules:
    permanent placements never stand in `LANDING_AREA_KEEP_OUT` (stern threshold +
    wires), ONLY launch-phase may; launch-phase is aft-only (x ≤ −100 — never in the
    bow-cat taxi flow); EVERY class clears every MEASURED spot with per-type
    **footprint margins**. Non-Nimitz dressing offered and DECLINED same day. Tests
    `tests/missiongenerator/test_carrier_deck_decor.py` +
    `tests/missiongenerator/test_deckdecorluadata.py` +
    `tests/lua/test_deckdecor_runtime.py`; features
    doc §72, checklist B25 — needs an in-game pass (statics ride the steaming deck; a
    max-density spawn still fills every spot; AI recovery taxi vs the street gear;
    the corridor set vanishes cleanly before recovery).
73. **Per-airframe default loadout for a task** — "make every F-4E planned as CAS use
    *this* loadout", as one click. Retribution resolves a planned flight's loadout **by
    name** (`Loadout.default_for` → `default_loadout_names_for(task)` → the first preset the
    airframe supplies), and `qt_ui.main` registers the user's
    `Saved Games/DCS/MissionEditor/UnitPayloads` as pydcs's **preferred** payload directory
    with the repo's `resources/customized_payloads` behind it — so a user payload saved
    under the name a task resolves to already overrode the shipped fit for every future
    flight. That was **undiscoverable**: the Save Payload dialog pre-fills `Custom <task>`,
    a name nothing ever resolves, so the obvious action produced a preset the planner would
    never pick. `game/fourteenth/loadout_defaults.py` makes it first-class — a **"Set as
    default for &lt;task&gt;"** + **"Clear default"** pair under the pylon list (mirroring the
    §43 fuel/properties pair on the aircraft box) that resolves the winning name, writes the
    edited loadout there, and can strip it back out so the shipped fit takes over again.
    `override_name_for` returns the name that **currently wins** rather than a hardcoded
    `Retribution <task>`, so it still lands in the right slot when a higher-priority
    candidate exists (the §71 `(XW)` fits sort ahead of the plain name) and stays idempotent
    once written. Scope is spelled out in the confirm dialog because it is broad and easy to
    forget: the override is **global** like the `UnitPayloads` file it lives in — **both
    coalitions** (an enemy flight of the same airframe+task resolves the same name),
    **every campaign** until cleared, and **newly planned flights only**. Writes back the
    file up first (`_retribution_backups`) and only ever touch the single named entry, so a
    hand-authored Mission Editor payload in the same file survives; a file that exists but
    **cannot be parsed is left completely alone** (rewriting it would destroy every other
    payload for that airframe) and the save is refused with a warning. No Settings field —
    on-disk content is the switch (§42/§43 precedent). Shipped alongside a payload-tab
    cleanup pass: the laser-code rows now **hide when the loadout has no use for a code**
    (reusing `Loadout.uses_laser_code()`, the same predicate gating the kneeboard Laser Code
    page — so a jet on Snakeyes and Rockeyes stops being shown a TGP code row, while the
    stock Pave Spike + GBU-12 fit still gets one); the loadout dropdown stops **reading as
    the stock fit while a custom loadout is loaded** (a `(customised)` flag — the selection
    itself is load-bearing, since unticking "Use custom loadout" adopts it, so it is
    annotated rather than changed, and member-switching now syncs it with signals blocked so
    it cannot overwrite a custom loadout); the fuel spinner and the §46 fuel-plan line
    **agree** (both convert `flight.fuel` with `KG_TO_LBS` instead of the spinner
    re-rounding the integer slider through a duplicated constant — the flown "12147 lbs" vs
    "12,149 internal" gap); truncated store names get a **hover tooltip**; saving over an
    existing payload name **replaces** its dropdown entry instead of stacking a duplicate; a
    new payload entry can no longer **collide with a live key** in a file whose keys don't
    start at 1 (`len() + 1` → `max(key) + 1`); the `WeaponLaserCodeSelector`'s AI guard
    (`setDisabled(True)` immediately undone by an unconditional `setEnabled(True)`, plus a
    wrong "AI does not use laser codes" label — AI *does* need a weapon code to drop LGBs on
    a JTAC's designation) is resolved in favour of the working behaviour; three
    `QMessageBox.information(QWidget(), ...)` throwaway parents become `self` (the §28
    window-GC class of bug); and the Edit Flight dialog **names its flight** in the title
    instead of a bare "Edit flight" for every window.
    (`game/fourteenth/loadout_defaults.py`,
    `qt_ui/windows/mission/flight/payload/QLoadoutEditor.py`,
    `qt_ui/windows/mission/flight/payload/QFlightPayloadTab.py`,
    `qt_ui/windows/mission/flight/payload/QPylonEditor.py`,
    `qt_ui/windows/mission/flight/payload/weaponlasercodeselector.py`,
    `qt_ui/windows/mission/QEditFlightDialog.py`; features doc §73, checklist Q2 — needs an
    in-app pass.)

---

## Repo & Branch Layout

- This repo (`bradyccox/414Ret`) `main` = the consolidated, most-up-to-date 414th build.
- Upstream is `dcs-retribution/dcs-retribution`; the 414th's PR fork is
  `bradyccox/dcs-retribution`.
- The 414th's primary "all features" working branch in the dev checkout is
  `414th-all-features`; `main` here = that + the Iran pack + a Black/mypy lint pass.

### Upstream PR ledger (**refreshed live 2026-07-16** via `gh pr list --author bradyccox --state all` — 36 PRs: 11 open / 5 merged / 20 closed. Still re-verify with `gh` before acting; this goes stale fast.)

Carved out of this work, against `dcs-retribution/dcs-retribution` (all authored by `bradyccox`):

- **Open (awaiting review):**
  - [#874](https://github.com/dcs-retribution/dcs-retribution/pull/874) curated carrier comms (**draft**) — §65 verbatim (per-hull boat cards feeding the DCS-rendered CV Operations Data page: hull-number TACAN + boat ident with `alloc_near` nearest-neighbor degrade, hull-keyed ICLS via a shared `IclsAllocator`, 336-band Link 4, stable persisted ATC, flagship named by hull name). NO fork couplings; the port adds only the Pretense allocator-type adaptation (behavior untouched). On dev @ `ef576acc`; pytest/Black/mypy green — opened 2026-07-16. Fork side = [414Ret#611](https://github.com/bradyccox/414Ret/pull/611). See upstreaming-inventory item 19.
  - [#873](https://github.com/dcs-retribution/dcs-retribution/pull/873) culling: keep scenery-objective kill tracking in culled regions (**draft**) — opened 2026-07-16; `MERGEABLE`. (Added by the 2026-07-16 live refresh; it had never been recorded here. Fork-side context not yet written up.)
  - [#872](https://github.com/dcs-retribution/dcs-retribution/pull/872) ship-launched cruise missile strikes (**draft**) — generic core of fork [414Ret#599](https://github.com/bradyccox/414Ret/pull/599) (Tomahawk/Kalibr shore attack: F10 call-for-fire with marker-text salvo sizing, optional auto raids, persisted no-rearm magazine debited via the `cruise_missiles_state` debrief channel). NO fork couplings (no ROE-zone gate/`map_hidden`/`enabled_when`). Rebased onto dev @ `ef576acc`; pytest/Black/mypy green — opened 2026-07-15. See upstreaming-inventory item 18.
  - [#854](https://github.com/dcs-retribution/dcs-retribution/pull/854) per-squadron DCS country for nation-specific voiceovers + nation-aware pilot names (§23) — resolves upstream issue [#627](https://github.com/dcs-retribution/dcs-retribution/issues/627). Ports `CountryAssigner` + `pilotnames.py` + both test files verbatim; the §23 wiring hunks re-applied to upstream `missiongenerator.py`/`aircraftgenerator.py`/`squadron.py` (the fork's QRA `spawn_intercept_templates` is NOT upstream, so only `generate_flights`+`spawn_unused_aircraft` take the assigner). Pretense is standalone/overrides the touched methods → unaffected. NO 414th content (Iran faction wiring stays fork-side). §23 was NOT previously in the carve queue. Black/mypy/pytest/ts all green — opened 2026-07-03.
  - [#843](https://github.com/dcs-retribution/dcs-retribution/pull/843) era-gate payload-editor options: JHMCS property gating (§24) + targeting-pod era data (re-does withdrawn #786) (carve queue item 11) — opened 2026-06-27; `MERGEABLE`. **Druss99 CHANGES_REQUESTED addressed 2026-06-29**: helmet-cueing dates moved to `resources/aircraftproperties/helmets/*.yaml` (mirroring the weapons era model, per his ask) + extended to Soviet HMS/SURA Visor & A-10C HMCS; CI green. ⚠️ **Owes a reviewer re-request** — Druss99 is NOT in the re-request list, so the PR sits blocked with no signal for him to re-review. ⚠️ **Scope overlap to check:** #871 *"Targeting-pod era data: introduction years + missing CLSIDs"* **merged 2026-07-15** — i.e. the pod half of this PR may already be upstream. Re-scope #843 to the JHMCS/helmet half before pushing it further.
  - [#828](https://github.com/dcs-retribution/dcs-retribution/pull/828) recon fog-of-war (§3) — the flagship carve (**draft**). ⚠️ **`CONFLICTING` as of 2026-07-16 — needs a rebase on current `dev`** (the ledger previously called it "mergeable"; that is no longer true).
  - [#806](https://github.com/dcs-retribution/dcs-retribution/pull/806) configurable cruise/patrol altitude.
  - [#805](https://github.com/dcs-retribution/dcs-retribution/pull/805) bulk waypoint altitude UI — Druss99's CHANGES_REQUESTED **addressed** (verified 2026-06-29): `DIVERT`/`TARGET_POINT` + `REFUEL`/`RECOVERY_TANKER` (and target-group/ship, pickup/dropoff, cargo-stop, bullseye) now in the `BULK_ALTITUDE_SKIP_TYPES` skip-list. Druss99 **re-requested** — awaiting his re-review; no further action owed.
  - [#794](https://github.com/dcs-retribution/dcs-retribution/pull/794) hide mobile SAM in combined groups (§7).
  - [#792](https://github.com/dcs-retribution/dcs-retribution/pull/792) wind override UI.
  - [#788](https://github.com/dcs-retribution/dcs-retribution/pull/788) inflight final-waypoint crash (§8).
  - Mergeability as of the 2026-07-16 refresh: **all open PRs are `MERGEABLE` except #828 (`CONFLICTING`)**. This supersedes the old "several created mid-June show `mergeable: UNKNOWN` — likely need a rebase" note; only #828 actually needs one.
- **Merged (5):** [#871](https://github.com/dcs-retribution/dcs-retribution/pull/871) targeting-pod era data — introduction years + missing CLSIDs (merged 2026-07-15; **was never in this ledger** — see the #843 overlap flag above) · [#841](https://github.com/dcs-retribution/dcs-retribution/pull/841) plugin `descriptionInUI` field (§14) · [#793](https://github.com/dcs-retribution/dcs-retribution/pull/793) building-card placeholder (§4) — both came back with the 2026-07-05 upstream/dev sync merge · [#826](https://github.com/dcs-retribution/dcs-retribution/pull/826) weapons coverage/repairs · [#789](https://github.com/dcs-retribution/dcs-retribution/pull/789) inverted OPFOR aggressiveness fix.
- **Closed unmerged — NEWLY CLOSED since the 2026-06-27 snapshot (⚠️ the ledger had all four listed as "open, awaiting review"; the *reason* each closed was NOT investigated — check the PR before re-carving):**
  - [#851](https://github.com/dcs-retribution/dcs-retribution/pull/851) High Digit SAMs **Ultimate Compilation** support (§41's generic core) — retargets the HDS toggle to the maintained mod: renamed-radar re-points, retired-unit tombstones, the 42 new units + 7 presets + SAMP/T layout, and the `remove_vehicle` id-vs-name strip fix. NO 414th faction enrichment (P-37/SA-7/S-400 wiring stays fork-side). Opened 2026-07-01. Landed on the fork as [414Ret#382](https://github.com/bradyccox/414Ret/pull/382), so the fork keeps it either way.
  - [#847](https://github.com/dcs-retribution/dcs-retribution/pull/847) F-4E-45MC (Heatblur) loadout rebuild **+** Maverick date-fallback fix (period AIM-7E2/9L baseline; AGM-65 date-fallback rerouted Walleye → Mk-20 Rockeye). Opened 2026-06-28; **consolidated the former #845 + #846** (both also closed). Landed on the fork as [414Ret#322](https://github.com/bradyccox/414Ret/pull/322) + [#325](https://github.com/bradyccox/414Ret/pull/325).
  - [#842](https://github.com/dcs-retribution/dcs-retribution/pull/842) landmap prepared-index perf (carve queue item 1) — opened 2026-06-27.
  - [#791](https://github.com/dcs-retribution/dcs-retribution/pull/791) SAM site layouts + EWR pool.
- **Self-withdrawn (NOT rejected, NOT upstream):** [#784](https://github.com/dcs-retribution/dcs-retribution/pull/784) Iran pack · [#786](https://github.com/dcs-retribution/dcs-retribution/pull/786) AAQ-33 era restriction · [#790](https://github.com/dcs-retribution/dcs-retribution/pull/790) orbit deconfliction. The Iran pack and AAQ-33 fix are therefore **still fork-only** — re-carve if wanted.
- **Closed, superseded (the 2025-11-27 + 2026-06-09→11 early carve attempts; no action owed):** #621, #622 (the initial uploads) · #774/#776 (final-waypoint crash, superseded by #788) · #775/#777 (AWACS orbit flip) · #778/#781/#783 (SCRAMBLE/scramble-logic flight types — the retired ramp-scramble line, see §1) · #779/#780 (C-130J JAMMING, §2) · #845/#846 (folded into #847).
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
- **SAM belts: legacy → §60 doubling, strategic → regiment-by-authoring (STANDARD, 2026-07-12).**
  When you lay out a **new campaign's** air defenses, choose the redundancy model by system class —
  don't just drop fat single-site batteries:
  - **Legacy / mobile systems** (SA-2, SA-3, SA-6, Hawk, and the generic launcher sites) — a lone
    site is realistic and the §60 two-guidance-radar doubling already baked into their layouts is the
    right fix (defeats the single-HARM kill). Place them as normal; nothing extra to do.
  - **Strategic belts** (S-300 / S-400 / SA-10/20/21, Patriot, the long-range LORAD systems) — prefer
    the **regiment-by-authoring** pattern: place **several single-radar fire units + a shared EWR/
    acquisition site** on the CP and let MANTIS net them into one IADS, rather than one doubled fat
    site. That is the historically faithful survivability model (kill one battalion's radar, the
    regiment fights on) and it's what the engine + MANTIS already represent when you place multiple
    sites.
  - **Guardrail — never double-count radars.** §60 doubling and a regiment layout both add engagement
    radars. If a future engine "regiment" construct ever lands for a strategic system, revert §60's
    doubling for that system, and **record which systems are regiment-modeled vs §60-doubled** the day
    that starts. Rationale + the deferred directions (geometry, acquisition separation, decoys) live in
    [docs/dev/design/414th-sam-site-realism-notes.md](docs/dev/design/414th-sam-site-realism-notes.md).
  - **Reference implementation:** Red Tide's three rear S-300 hubs (2026-07-12) — 3 clustered
    single-radar S-300 battalions + a shared EWR per hub, netted by range-mode advanced IADS, with §60
    reverted only for that campaign's S-300/SA-5 via the `Russia 1980 (Red Tide)` faction fork (the
    front's legacy MERAD screen keeps §60 doubling). See `414th-red-tide-campaign-notes.md`.
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
