# 414th Feature Debt Register & Verification Plan

**Written 2026-07-15** (the ~600-commit look-back, session `gallant-panini-5485e7`).
**Timeline it serves:** Friday night **2026-07-17** — Red Tide regeneration + feature lock →
**2026-08-01** — the next squadron event (the Red Tide **M2** fly).

This is the triage of everything "half-cooked" at 600 commits: what is broken, what was
verified-then-reworked, what has never been flown, and **exactly where each item gets its
verification**. It complements — never replaces — the row-level tracker
[414th-ingame-pass-checklist.md](414th-ingame-pass-checklist.md): statuses live THERE; this doc
is the *plan* that drains it. Archive or delete this file once the Aug-1 wave is processed and
its rows are adjudicated.

Board snapshot at the session start: **71 verified · 49 untested · 16 partial · 2 live-regressed**
(B10, G23). B10 flipped ☑ VERIFIED during the look-back (2026-07-15 user pass), leaving **G23 the
only live ✗** — and it is deliberately frozen (see the decisions log).

---

## 0. The structural finding

The fork does **not** have abandoned features — it has a **verification backlog with a build rate
~3× the fly rate since ~2026-07-05**. Two process facts fall out of the look-back:

1. **The demotion discipline works.** Every "verified, then reworked" case was demoted in the
   checklist *the day the rework landed* (M1, S1, K2/H10/H12, P4/P5, G9, L9, B10). Nothing was
   silently trusted. The failure mode is only that the re-verify queue drains at squadron events,
   which are scarce, while reworks are cheap and daily.
2. **Two clusters are "verified on retired architecture"** — the 2026-06-28 kneeboard passes
   (deck replaced 2026-07-13; the honest row is now H12) and the 2026-06-25/26 Combat SAR G-rows
   (arming path replaced 2026-07-06/07-10; the core ledger has fresh flown M1 evidence, the
   rescue-*launch* path is G9). The headline verified count slightly overstates live coverage;
   H12 and G9 are the rows that matter for those areas.

**The standing fix this register institutes:** (a) a **post-regen app-side sweep** (§3 below) —
roughly half of every "needs a fly" row has an app-side observable that passes or dies with no
DCS involved; (b) **queue-matched sessions** — Red Tide rows ride Red Tide events, Vietnam rows
need a Vietnam night, COIN rows a COIN night, SP rows an SP session. A row parked on the wrong
queue ages forever (G23 sat 12 days waiting for an MP event that could never exercise it).

---

## 1. Decisions log (2026-07-15)

- **B10 briefing popup — ☑ VERIFIED** (user pass: the 2026-07-11 rework works, "just fine, no
  issues"). By design: a DCS **dynamic-slot** pilot gets no card (not a player-crewed ATO flight).
- **G23 Sandy divert — scoped SINGLE-PLAYER; stays frozen.** Squadron call: the AI-crewed-Sandy
  divert exists for solo CSAR play; the 414th's events are MP DM-style (the user builds the
  campaign, the squadron crews the seats), so an MP event was never its arbiter. Pass-or-delete
  stands with an **SP re-fly** as the arbiter (see §5). Do not delete for lack of MP exercise.
- **Next squadron event = 2026-08-01** — two weeks of runway after the Friday 7/17 regen for
  sweeps and mid-window testing. No scramble required.

---

## 2. Before the Friday 7/17 regen (the landing window)

Items that shape the new game and therefore must be handled **before** regeneration:

- [x] **`auto_combat_sar` "AI-rescue off" — RESOLVED + FIXED 2026-07-15.** NOT the saved-defaults layer: the emitter's designed **player-package suppression
  gate** did it (`luagenerator.py` `player_package = bool(blue_rescue or blue_kings or
  blue_sandys)` — the recorded §21 squadron call, "a player CSAR/SCAR flight in the ATO ⟹ we've
  got it covered, no AI spawn"). M1's ATO carried a **bare player Sandy** (`0 King(s), 1
  Sandy(s)` in the ledger log) — a SCAR escort with no rescue helo — which suppressed the AI
  helo even though a Sandy can't pick anyone up, leaving M1 with **zero rescue capability**
  (capture race only). **DECIDED + IMPLEMENTED same day (squadron call, option 1):** the gate is
  narrowed to **rescue-capable flights only** — a player CSAR *helo* suppresses the AI spawn; a
  bare Sandy/King now **draws** the AI helo and escorts/tracks it (`luagenerator.py`
  `player_rescue_helo`; tests `test_bare_sandy_does_not_suppress_autospawn` +
  `test_bare_king_does_not_suppress_autospawn`). Lands before the Friday lock, so the
  regenerated campaign carries it — G9 stays exercisable at Aug 1 even if someone frags a Sandy.
- [ ] **§59 ground AI sleep — decide.** Default OFF, deliberately not preseeded. Options: leave
  OFF for Aug 1 (safe), or trial it in the mid-window private session (§5) and preseed only if
  clean. Do **not** first-fly it on the squadron.
- [ ] **Server `RETRIBUTION_EXPORT_DIR` — the runbook (mechanism confirmed in
  `resources/plugins/base/dcs_retribution.lua` `discoverDebriefingFilePath`):** the export path
  resolves (1) `RETRIBUTION_EXPORT_DIR` → (2) the miz-embedded builder install path (doesn't
  exist on the server) → (3) `TEMP` → (4) cwd — which is why the server fell to
  `C:\Users\admin.dcs\AppData\Local\Temp\state.json` (the L6/L9 blocker, and the near-miss with
  a stale June-20 export). On the dedicated host, as admin:
  ```powershell
  New-Item -ItemType Directory -Force C:\Retribution-Exports
  [Environment]::SetEnvironmentVariable("RETRIBUTION_EXPORT_DIR", "C:\Retribution-Exports", "Machine")
  # optional but recommended -- per-mission stamped files (state-<unixtime>.json), no overwrites,
  # kills the stale-file trap for good:
  [Environment]::SetEnvironmentVariable("RETRIBUTION_EXPORT_STAMPED_STATE", "1", "Machine")
  ```
  then **restart the DCS server process** (machine-level env vars load at process start).
  **Verify** in the server `dcs.log` at the next mission load:
  `The state.json file will be created in RETRIBUTION_EXPORT_DIR : (C:\Retribution-Exports\state….json)`.
  Turn processing then pulls from that folder (newest stamped file = the flown mission). Needed
  before Aug 1's post-mission processing (the 7/17 regen itself consumes the saved M1 JSON).

---

## 3. Post-regen app-side sweep (no DCS needed, ~30–60 min)

Run right after the Friday regeneration + processing turn 1 from the M1 JSON, against the
generated M2 mission + save:

| # | Check | What good looks like | Adjudicates |
|---|---|---|---|
| 1 | Open a SEAD Viper and a strike Hornet in Edit Flight → Payload | The §46 fuel readout renders sane numbers; the jammer-pod→tank trade fired **only** where it reduced tanker passes; TGP / OFFENSIVE_JAMMER / DECOY never traded; re-generating the mission leaves loadouts identical (idempotent) | **S1** (the 2026-07-12 fuel-first rework — highest-risk item on the board: default ON, all campaigns, mutates persisted loadouts) |
| 2 | Unzip the generated `.miz`, eyeball the kneeboard images | Upstream page set; Mission Info BLUF carries the THREATS/LOADOUT/SAR lines; Fuel column + amber RTB margin; **SITREP band at the Mission Info bottom**; code words on Support Info; the index page appears iff 2+ client flights share an airframe | **H12, K2, H10, H11** (the 2026-07-13 back-to-upstream deck) |
| 3 | Load the miz on the server, read dcs.log arming lines | `BRIEFING\|: armed` · `COMMSJAM\|: intel gate armed … dormant` · `Minefields armed` · `REDSCRAMBLE\|` host-mode armed on `Flash` · mobile-missiles armed · convoy-ambush armed · Combat SAR ledger with **`AI-rescue on`** (see §2) | §58, S4-arming, B9-arming, B14-arming, §49, S3, **G9** |
| 4 | Read the ATO | A fragged **mining sortie** against a red convoy exists (`auto_plan_minefields` preseed); QRA reserves intact | **B9** auto-plan leg |
| 5 | Read the map + SITREP | Motorpool symbol at Haina; concealed forces draw **amber dashed** circles; the three S-300 hubs read as 3 battalions + shared EWR; SITREP carries the posture/supply/C2 lines | **B8, B13**, G24 (partial), §53/§55 surfaces |

Anything that fails here fails **before** the squadron ever slots in — that is the point.

---

## 4. Aug 1 fly-card (what one Red Tide M2 session adjudicates)

Riding the event organically (all preseeded/armed in Red Tide):

| Row | How it gets exercised | Watch for |
|---|---|---|
| **B14** host red scramble | The DM presses the F10 `HOST: Red Scramble` menu (gated to the `Flash` tag) | Bandits spawn at the picked base on the air profile and press the nearest blue fighters; EMERGENCY spawns near the players |
| **B15** modex | Eyeball Tomcat/Hornet board numbers on the ramp/Tacview | Sequential X00/X01… per squadron; Tomcats in the low block |
| **B12/B13** SAM redundancy + S-300 regiments | SEAD sorties into the belt | A legacy site survives its first HARM (second radar); a regiment keeps fighting after one battalion's radar dies |
| **G30** SHORAD link | The same SEAD play | The point-defense SA-15/SA-19 wake and engage the ARM shot |
| **A6** escort pre-join ROE | Any red escorted package pre-join | Escorts return fire before JOIN instead of dying silent |
| **C8** helo terrain trio | AI helos transiting the Harz | No CFIT on the subdivided TERRAIN-anchored legs |
| **B9** minefields (drop→lay→kill→persist) | **Assign one pilot the fragged mining sortie** | Field lays with a friendly F10 mark; a red convoy crossing it takes debrief-visible convoy losses; un-driven field re-lays next turn |
| **§36/L8** artillery harassment @ 42 km | Automatic | Fulda FARP + Haina both under sporadic fire past the grace; never a player-spawn field |
| **S3** ambush spring | Escort a blue convoy route | "TROOPS IN CONTACT" + F10 mark only when the column actually drives into it |
| **A5** QRA forward defense | Opportunistic | A rear field launches to answer a front raid and completes the long transit |
| **G29** MIA/evader arc | Opportunistic — needs a real tracked blue shoot-down left unrescued | MIA on the roster/SITREP; the evader respawns next mission |
| **S4** comms jamming | **Organic only if a capture happens** (the snatch race now always runs) | "AIRCREW CAPTURED" → static on briefed channels → JAM BACKUP clean → striking the node silences it |
| **B6/B7 + §53/§54** C2-decap, red intent, war economy | Turn-2 partial reads only | SITREP posture-detail/supply/C2 lines read correctly; real behavioral verdicts need turns 3+ |

Not riding Aug 1: **B16 cruise raids** — not preseeded and era-wrong for 1988 (no LACM hulls);
needs a modern-faction scratch campaign (§5).

*Headless de-risk ran 2026-07-15* (a 15-turn AI-vs-AI Red Tide self-play through the real
GameGenerator build): the campaign is **multi-turn stable** with the whole preseeded stack live;
the **§55 posture classifier transitioned on real state** (Attrition → "Surging (all-in)" with the
"enemy air spent" opportunity window, then 13 turns of hysteresis-stable latch), **§56 reserve armor
actually stocks** (Haina 0 → 59 by turn 14 — the depot has vehicles to bomb from turn ~2), and the
**§47 clock/weather march held its contract** (3–7 h steps, midnight rolls, adjacent-rung weather
systems). Details + caveats on the **B7 / B8 / T1 rows**. One standing caution from both probes:
the §26 abstract resolver's war diverges wildly from flown DCS results (it inverted M1's 34:0 air
war) — **never adjudicate balance or pacing off fast-forwarded turns**, on any campaign.

---

## 5. Mid-window private session card (DM solo / one buddy, before Aug 1 — high value)

One private dedicated-server evening burns down the rows that need contrived conditions no
squadron event should host:

- [ ] **S4 capture→jam moment**: flip the `[TEST] force capture` toggle → eject → snatch →
  capture → **hear** the jamming on a tuned radio → strike the comms node → silence. One loop
  covers S4 + the G28 POW surface + the G29 capture leg.
- [ ] **B9 persistence leg**: mine a road deliberately, end the mission with the field
  un-driven, process the turn, confirm the re-laid field next mission.
- [ ] **§59 AI sleep trial** (only if considering it for Aug 1): garrisons sleep at distance,
  wake on approach/hit, invisible to the players.
- [ ] **B16 cruise raids**: a scratch modern campaign (`redfor_current`-class faction with the
  Kalibr/Burke hulls); auto raid fires with the LAUNCH WARNING, the F10 marker salvo works, the
  magazine debits only at debrief.
- [ ] **G23 SP re-fly — the pass-or-delete arbiter**: a *single-player* session, frag the rescue
  package (King + helo + **AI-crewed** Sandy), force an ejection, watch whether the Sandy
  physically leaves the racetrack, holds over the survivor, and releases back. Pass → frozen
  as-is forever; fail → the divert is deleted (a player-flown Sandy is untouched either way).

---

## 6. Parked queues (can't ride Red Tide — need their own nights)

**Vietnam night (1968 Yankee Station):** M1 will-pacing (the 2026-07-04 morale-ratchet redo has
never been played) · M6 red tempo · M9 commitment ceiling · L9 Super Gaggle loss-accounting
confirm (armed: 2 dead F-4Es await the debrief once the export path is fixed) · L11 AI
snake-and-nape leg · G19 Vietnam recon-bird re-fly. *The headless de-risk RAN 2026-07-15* (projector
re-run + a 20-turn real-engine AI-vs-AI self-play): the shipped weights still hit the documented
8/16/11 archetype pacing, the ratchet / escalation taxes / will-coupled phase acceleration / M9
ceiling all fired live, and no death spiral manifested even from will 0.4 at the budget floor. Two
balance watch-items flagged for the played pass — auto-resolved (unflown) turns are drastically
bloodier than DCS-flown ones, and the claimed-MiG-kill restore can grind a no-loss turtle win.
Full detail on the **M1 + M9 checklist rows**.

**COIN night (Enduring Resolve, plus an Inherent Resolve hop):** P1 living insurgency · P3
re-infiltration · **P4/P5 third-rework re-flies** (static IED emplacement + HVT convoy patrol) ·
P6 dispersed cells · P8 liveliness (movers + FOB indirect fire) · P7 Inherent Resolve laydown ·
the **S3/S5 IR re-fly** where the parked-Baghdad-column bug actually occurred · the COIN mover
2-WP `goRoute` fix (proven on the SCUDs, unflown on COIN).

**App-side / client-rebuild, any time at the desk:** Q1 per-aircraft flight defaults (Qt) · O1
local map tiles · G24 concealment circles read · K3 settings greying + map legend · §53 supply
overlay · §57 minefields overlay.

---

## 7. Rework-invalidated ledger (the "quiet invalidation" set — all tracked, none silent)

| Item | Was verified | Invalidated by | Re-verifies at |
|---|---|---|---|
| S1 fuel planning | 2026-07-04 ("S1 good I think") | 2026-07-12 fuel-first rework | **Sweep §3 #1** (+ Aug 1 tanker behavior) |
| Kneeboard K2/H10/H12 | 2026-06-28 deck pass | 2026-07-13 back-to-upstream rework | **Sweep §3 #2** |
| G9 Combat SAR rescue | 2026-06-28 (old orbit — moot) | 2026-07-06 on-demand rework | §2 setting check + **Aug 1** (an ejection with a parked helo) |
| M1 political will | 2026-07-04 ("M1 good") | Same-day morale-ratchet redo | **Vietnam night** (headless sim as interim) |
| L9 Super Gaggle | 2026-07-01/02 runs | 2026-07-03 launch-delay rework + unconfirmed loss leg | **Vietnam night** + the §2 export fix |
| P4/P5 COIN IED/HVT | 2026-07-04 ("good but needs reworked") | Three reworks, 2026-07-04/05 | **COIN night** |

---

## 8. Deliberate deferrals (documented halves — parked on purpose, kept findable)

- §21 v2 — on-demand **Sandy + King** launches (payload-configurator / TACAN-setup gap) +
  multi-survivor chained pickup.
- §52 Phase A2 — red offensive package-count throttle under decapitation.
- §63 Tier-3 — cruise-raid right-click/SITREP surfacing.
- §37 — Super Gaggle delivery credit (needs a runtime "delivered" signal; losses-only for now)
  + red-side symmetry.
- §20 — drop-spawn polish: terrain ring overlay, pending markers, FOB establishment, relocate,
  budget refund on remove.
- Aircraft task-priority rebalance — the full "tighten everywhere" pass held pending in-game
  scramble/CAP validation.
- §40 — per-phase whitelist deltas, `front_line_stance`, the 3 wiki-campaign authored arcs;
  the **strike-escort famine lever** ("reserve a fighter ahead of BARCAP" — M4 observed all
  strike escorts pruning at Linebacker tempo).
- §38 FAC(A) — marking only, no auto-assignment of strikers.
- §34 NGFS — JTAC auto-lase → auto fire-mission coupling.
- §50 — off-road ambush positions; red-convoy ambush symmetry.
- Campaign maker — increment B (server + map-paint wizard glue) in progress.
- Design-only drafts: scenery-import strike targets, turnless exploration, the
  mission-planning wiki rework, the MOOSE `Ops.*` adoption map (the post-MIST phase).

None of these are regressions; they are the recorded edges of shipped v1s. Promote one only
with a design pass, not as a drive-by.
