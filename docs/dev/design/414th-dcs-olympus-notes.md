# 414th — DCS Olympus exploration ("what if?")

> **STATUS: DESIGN ONLY (2026-07-20).** Nothing landed, no feature §N, no setting, no
> registry entry. This note answers the DM's "what if?" +
> [github.com/Pax1601/DCSOlympus](https://github.com/Pax1601/DCSOlympus) link: what Olympus
> is, how it composes with this fork *today* with zero code, what deliberate integration
> could look like, and a recommendation. Web-sourced facts were pulled 2026-07-20 from the
> repo/README/wiki/releases pages; anything marked **[verify]** needs confirmation at
> install time.
>
> **Tier 0 GREEN-LIT same day (DM call "1").** The operational half is written:
> [`docs/dev/414th-olympus-gm-crib.md`](../414th-olympus-gm-crib.md) — Part A the GM crib
> sheet, Part B the compatibility pass card (which also captures this note's `[verify]`
> items as recorded observations). The DM installs on the private-session server; the
> pass card is what gets flown before Olympus touches a squadron event.
>
> **Source-research addendum (same day, post-merge):** the `[verify]` items answerable
> from Olympus's own source are resolved — spawn naming (`Olympus-<n>`, fixed), delete
> semantics (silent AI `destroy()` vs real explosion kill), and the MANTIS adoption
> mechanics (§6b, investigate item closed) — and a **new seam** was found: the shared
> mission-env `mist` global (§3 table). Folded into §3/§6/§8 and the crib sheet.

---

## 1. What Olympus is (as of v2.0.5)

DCS Olympus is a free, open-source mod that gives a running DCS mission a **real-time
RTS-style command layer in a web browser**: a live map on which users spawn units, assign
waypoints and tasks to AI, group/clone/remove units, and deploy effects (smoke, flares,
explosions, napalm, white phosphorus). Three permission roles:

- **Game Master** — everything, both coalitions, ground-truth visibility;
- **Blue / Red Commander** — the same powers scoped to one coalition, with
  **sensor-based fog**: "the blue and red views also only see what their respective
  systems can see" (wiki). Optional spawn budgets exist for commander modes.

Architecture: a **DLL loaded by the DCS instance exposing a REST API** + a Lua hook layer
+ a **webserver executable**; a Manager app installs it against a DCS install. Clients are
**pure browser** — the squadron installs nothing. Runs on a dedicated server (an
`autoexec.cfg` tweak is part of install); browser audio needs HTTPS. The v2 line
(current stable **v2.0.5**; an active `release-candidate` branch trails it — verify
currency at install) added **native SRS integration** (tune/transmit real frequencies from
the browser, assign loudspeakers to units), ground laser targeting, a per-pylon loadout
system for spawns, **Mission Editor drawings rendered on the Olympus map**, and
DCS-sourced map tiles for several terrains.

Their compatibility stance: "we have tried hard to keep Olympus from interfering with
other scripts … we suggest testing with what you have in mind."

**License: none detected.** The repo has no top-level LICENSE file and the README carries
no license section (the project self-describes as "independent and non-profit").
**[verify]** — but until shown otherwise, treat the code as all-rights-reserved by
default: *running* Olympus and talking to its documented REST API is unaffected;
**vendoring its code or its map tiles into this repo is off the table** without asking
Pax1601. (Their DCS-sourced tile sets are adjacent to our §42 local-tiles feature — same
rule: do not lift them.)

## 2. Why this intersects the 414th specifically

The fork has been building the poor man's Olympus for months, one F10 menu at a time:

- **§61 host red scramble** — spawn a bandit 2/4-ship at a red field + a GCI loop to
  steer it. Olympus: spawn anything anywhere and steer it by hand. §61's GCI re-vector
  loop exists *because* an unsteered clone needs one; with Olympus **the human is the GCI
  loop**.
- **§20 drop-spawn** — right-click unit placement, but campaign-side (a persistent TGO
  materialised at generation). Olympus places mission-side, live. Different layers, both
  wanted: §20 = "put it in the campaign", Olympus = "put it in *this* mission".
- **§34 naval gunfire / §63 cruise-missile F10 marker calls** — map-marker call-for-fire.
  Olympus: click the map.
- The COIN movers, §50 ambush springs, §49 scoot, §21 CSAR choreography are scripted
  precisely because nobody is at the wheel mid-mission. Olympus puts a trusted human at
  the wheel.
- **The in-game-pass backlog is the sleeper use case.** The checklist stands at 66
  UNTESTED / 19 PARTIAL rows, and most passes today are flown-then-Tacview-archaeology.
  The Olympus GM view is a purpose-built **observation deck**: live ground-truth map +
  camera control, watching "did the ambush spring / did the SCUD scoot / did the QRA hold
  its border zone" *as it happens*. Zero code, immediate value.
- The fog philosophy maps 1:1: Olympus commander views are sensor-fogged and the GM view
  is ground truth — the same split the fork engineered campaign-side as §3 recon fog +
  the §18 reveal toggle.
- **SRS synergy**: §70 gave the enemy an audible CW net and §51 jams the blue net; the
  fork's events already run SRS. Olympus v2 lets the DM **transmit as the enemy** — voice
  GCI on the discovered red UHF channels, drama on the JAM BACKUP freq — from a browser
  tab. Zero code.

## 3. Compatibility map — running them together, zero code

The two systems touch at the DCS runtime only. Retribution's plugins live inside the miz
trigger scripts (sandboxed mission env); Olympus lives in the hooks/DLL layer and
"works alongside any premade mission". Expected to coexist; the Tier-0 flown pass is the
proof. Per-system analysis:

| Fork system | Interaction | Verdict |
|---|---|---|
| Debrief truth channel (`state.json` via `dcs_retribution.lua`) | GM spawns are not in the `UnitMap` → their deaths are harmless untracked names in the killed lists (the §37 precedent). Anything a GM spawn **kills** is a native, real campaign loss. | ✅ Exactly the §61 doctrine already: untracked event content. |
| GM **delete/despawn** of a *tracked* unit | A scripted `destroy()` fires no death event → the campaign never learns → the unit survives at the turn boundary. Graceful (nothing corrupts), but semantically "this never happened". | ⚠️ GM crib sheet: to make a kill campaign-real, kill it (explosion, combat); despawn = erase. **[verify]** which delete flavors Olympus offers. |
| **MANTIS IADS** (`mantisiads/mantis-config.lua`) | The bridge passes **exact escaped group names** from the Python-emitted IADS table (`collect` → `escape_prefix`); sets are dynamic (`FilterStart`) but only known names match. A GM-spawned SAM therefore **never joins the net**: vanilla DCS AI, radar always-on, no EMCON, no C2/§52 coupling, no §7 MFD hiding, no threat ring, absent from §74 DTC rings. **Source-confirmed both ways (2026-07-20):** Olympus names spawns a fixed `Olympus-<n>` (not user-choosable) so no spawn can ever match a prefix — and conversely MANTIS *would* fully weave in a late birth that did match (`_Check` calls `_RefreshSAMTable` every 3rd detection cycle, rebuilding banding + the SEAD set from the live `FilterStart` set). | ✅ Acceptable for event content — but document it so nobody expects a GM SA-10 to behave like an authored one. ❌ Do NOT "fix" this with a blanket `Olympus` prefix in the SAM set: it would sweep every GM ground spawn into MANTIS management and hold GM tank platoons dark/weapons-green. The clean adoption shape is §6(b). |
| **Shared `mist` global** (found in the 2026-07-20 source pass) | Olympus injects its **own full MIST** into the mission env (`scripts/lua/backend/mist.lua`) and `OlympusCommand.lua` calls symbols outside the fork's 44-symbol shim (`fixedWing.buildWP`, `DBs.MEunitsById`, `DBs.drawingByName`, `DBs.navPoints`). Both inits are additive (shim: `mist = mist or {}`, `mist.DBs = mist.DBs or {}`) and the shim replicates MIST semantics verbatim — so in either load order, colliding symbols are behaviorally-equivalent replicas and each side's extras survive. Installing Olympus effectively un-retires MIST in the mission env. | ⚠️ Expected benign but **unproven** — the pass card's step-1 proof burden: a fork mover routes AND an Olympus spawn accepts a waypoint, same mission. |
| QRA / intercept dispatcher | GM-spawned fighters are not dispatcher-managed; the GM steers them directly. And the **AI QRA reserve never scrambles against a GM raid**: the react filter classifies raids by the Retribution `{target} {task}\|…` group-name format, and a no-`\|` name is non-ATO air, never reacted to (`intercept-config.lua` `qra_group_reacts` — documented, deliberate). Airborne BARCAPs/TARCAPs still engage anything detected; the task-blind PLAYER_ALERT cue may still call a human alert flight **[verify]**. | ✅ Want ground-alert defenders against your raid? Spawn and steer them yourself. |
| Scripted movers (§49 scoot, COIN HVT/VBIED/cells, §50 springs, §21 combatsar divert, CTLD, §9 TIC) | Both sides push tasks/routes at the same controller; the plugins **re-push on a cadence** (§49 every ~8 min, COIN on its poll), so GM re-tasking one of these groups is a tug-of-war the script eventually wins. | ⚠️ GM ROE: hands off script-driven groups unless deliberately accepting the fight. |
| §59 AI sleep | A slept garrison group's controller is **off** — an Olympus task lands on a dead controller until the wake poll (aircraft within ~15 NM, or a hit) restores it. | ⚠️ For GM-heavy events: fly something near it first, or leave `perf_ground_ai_sleep` off. |
| Anti-grief guarantees (§36/§50/§21 player-spawn exclusions, grace periods) | These bound the *automation*. Olympus hands a trusted human unbounded artillery. | ✅ Culture note, not a defect — the guarantees were never about the DM. |
| The two web maps | Retribution client = campaign truth, fogged, turn-scale. Olympus = live truth, mission-scale. Complementary tabs. Bonus: Olympus renders ME drawings, and the fork already paints the FLOT, §40 ROE zones, and §45 support orbits into the miz — **the GM's Olympus map inherits campaign context for free**. **[verify]** which drawing layers render. | ✅ |
| Performance | Heavy laydowns already flirt with ANTIFREEZE (§49/§59 findings; 1968 Yankee Station is the measured stress case). Olympus's DLL + data export adds load of its own. | ⚠️ Measure on the Tier-0 pass. |
| Server infra | `autoexec.cfg` edit (persists across DCS updates? **[verify]**), webserver port(s), HTTPS only if browser audio is wanted, per-instance `WSPort` for SRS. | ⚠️ One-time admin cost. |

## 4. The doctrine

Olympus actions are **untracked event content** — the §20/§61 precedent, explicitly *not*
a §35/§37 no-phantom-spawns violation, because deliberate host action is the sanctioned
exception. The ledger stays honest as long as the GM knows the rules: **GM spawns cost
red nothing and their deaths mean nothing; everything they kill is real; despawns erase.**
That asymmetry is the §61 design ("red pays nothing, blue's losses are real") and it
scales to Olympus unchanged. The Tier-0 deliverable is a one-page **GM crib sheet**
carrying the ROE from §3 above — **written**: `docs/dev/414th-olympus-gm-crib.md`.

## 5. Tier 0 — adopt as event tooling (recommended; zero code)

1. Install on a **private-session server** first (the mid-window private-session card
   culture), not the M2 event.
2. **Compatibility pass** — fly the 11-step pass card in
   `docs/dev/414th-olympus-gm-crib.md` Part B (once on a heavy laydown, once on a COIN
   campaign; it records this note's `[verify]` items as it goes).
3. Try the **SRS voice-GCI** trick on the §70 red net frequencies (pass card step 10).
4. ~~Write the GM crib sheet~~ — written (crib doc Part A).
5. Start using the GM view as the **observation deck for the in-game-pass backlog**.

Not registered as a feature and no checklist row — nothing ships in the repo. If the
squadron adopts it as standing event infrastructure, revisit whether the crib sheet +
server setup deserve a docs/dev page (yes) and a features-doc mention (probably §-less).

## 6. Tier 1 — small optional code (all DEFERRED until a flown event wants them)

- **(a) GM spawn ledger** — watch `S_EVENT_BIRTH` for groups the mission didn't author →
  a `gm_spawns` state channel (the §57/§63 pattern) → the campaign *optionally* accounts
  GM red reinforcements as real. Runs against the §61 "event content is free" doctrine;
  build only if the DM ever wants campaign-real GM reinforcements. **DEFER.**
- **(b) IADS adoption** — let a GM SAM join MANTIS. **Investigate item RESOLVED
  (2026-07-20 source pass):** with the fork's `dynamic=true`, MANTIS's sets are
  `FilterStart()`-live and `MANTIS:_Check` calls `_RefreshSAMTable` every 3rd detection
  cycle, rebuilding range banding + the SEAD set from the live set — a group added to
  `MANTIS.SAM_Group` is fully woven in within ~3 cycles, no restart needed. Olympus
  spawn names are fixed (`Olympus-<n>`), so the prefix route is out (and a blanket
  `Olympus-` prefix stays forbidden — it would sweep GM tank platoons into SAM
  management); the clean shape is an F10 GM **"adopt nearest foreign SAM"** that
  validates the group actually carries SAM radars, then adds it **by object**
  (`SAM_Group:AddGroup(group)`). **Still DEFER** until a flown event wants GM SAMs
  inside the net — but it's now specified, not speculative.
- **(c) Campaign context → Olympus** — already mostly free via ME drawings (§40/§45). If
  gaps appear, extend the fork's drawings pass rather than integrating APIs. **LIKELY
  FREE.**
- **(d) §61 relationship** — keep §61 (zero-infra, works on any server); document
  "Olympus supersedes §61 where installed". **No code.**

## 7. Tier 2 — the turnless tie-in (the deep what-if)

Upstream's own `turnless.md` sketches the hard half of a turnless Retribution: state
capture, frozen combats, continuous replanning. Its late roadmap phases — "add player
options to create new packages after pressing play", "make planning real-time" — describe
building a worse Olympus inside Retribution. The coherent far future is a split:
**Retribution generates and accounts the war; Olympus is the live C2 pane**, and
Olympus's REST API (live positions) is even a candidate feed for turnless's
"track end positions of aircraft" phase. None of that is buildable before the turnless
state-capture work exists. **OUT OF SCOPE — filed here so the thread isn't lost.**

## 8. Risks & unknowns

- **License** (§1) — blocks vendoring, not running. Ask before any code/tile reuse.
- **Version churn** — v2 line active (`release-candidate` branch); pin the event server
  to a known-good build.
- Now **sourced** from `OlympusCommand.lua` (2026-07-20): spawn naming (`Olympus-<n>`,
  fixed) and delete semantics (plain AI delete = silent `destroy()` erase;
  explosive/player delete = real kill) — owed only in-game confirmation. Still
  unverified: which ME drawing layers render, `autoexec.cfg` persistence, perf on the
  heavy laydowns, and the shared-`mist` coexistence proof. All fall out of the Tier-0
  pass.
- Client side is a browser tab — **nothing for the squadron to install**, which is the
  quiet killer feature for adoption.

## 9. Recommendation

**Tier 0 yes** — install on the private-session server, run the compatibility pass,
write the GM crib sheet, and start using the GM view to burn down the in-game-pass
backlog. Every Tier-1 idea stays deferred until a flown event generates the want; the
turnless tie-in stays filed. No repo changes beyond this note until then.
