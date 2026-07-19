# 414th — Community Contribution Roadmap (the long view)

> **POLICY (2026-07-19, squadron directive): everything is upstreamable.** There is no
> permanent "fork-only" category — a thing either goes back clean and correct, or it
> waits in the queue until it can. "Can't half-ass it" is the bar: every carve ships
> with its rationale, its tests, and its in-game evidence. Carve *difficulty* is a
> sequencing input, never an exclusion. The old "⛔ NEVER" list is retired; its
> survivors are re-filed under **the last-mile queue** below with what each one needs.

The [upstreaming inventory](414th-upstreaming-inventory.md) is the tactical carve
queue (per-PR mechanics). This doc is the strategy: what goes back, in what order,
and what each item still owes.

**Where this stands (2026-07-19):** the door is open. **8 fork PRs are merged
upstream** — three of them (#805 bulk waypoint altitude, #843 JHMCS era gating, #854
per-squadron country) in a single day — and the maintainers merged geofffranks' #859
motorpool, which the fork had pre-adopted as §56. The fork is a recognized
contributor. The `sync/upstream-dev-2026-07-19` merge is the reference
implementation of **reconcile-on-merge** (see Workstream 1).

## The two axes

- **Community value** — would a stock-Retribution player, on any theater, want this?
  For nearly everything here the answer is *yes*.
- **Carve difficulty** — how hard to extract cleanly and get a maintainer to take it:
  - **Pure-Python / data** — easy. Lua-free, CI-checkable, usually already tested.
  - **Client (React)** — easy-ish; must land in upstream's own UI surfaces.
  - **Vendored Lua** — hard. Upstream takes on script ownership; needs a default-OFF
    gate, an in-game pass, and a sympathetic Lua maintainer.
  - **Content / defaults** — needs *packaging*: an identity-strip pass for campaigns,
    a written rationale for tuned values. Work, not exclusion.

## The three workstreams

1. **Reconcile-on-merge (standing discipline).** Every time a fork PR (or a feature
   the fork pre-adopted) merges upstream, the fork **deletes or aligns its variant to
   upstream's exact merged shape** in the next sync — prefer-upstream on conflicts,
   documented divergences only where the fork's design genuinely differs (e.g. the
   #879 alarm-state adaptation to the fork's MANTIS-owned EMCON). This is how the
   fork's delta shrinks: not by rebasing, by draining.
2. **Drain the queue.** Keep the open-PR set healthy (rebase what goes stale,
   graduate drafts) and keep feeding the inventory's 🟢 READY items. Sequencing:
   lowest difficulty first, crowded zones coordinated (review others' PRs instead of
   opening rivals), runtime features only after their in-game pass.
3. **Package the last mile.** The former "never" items each get their upstream story
   (below) and enter the queue when packaged.

---

## The last-mile queue (formerly "genuinely 414th — the thin layer")

Nothing here is fork-only by nature. Each row states what the clean-and-correct
upstream PR looks like.

| Item | Upstream story | Status |
|---|---|---|
| **Splash Damage tuned build** | **A fix to shipping defaults, not identity.** Upstream's shipped config turned out internally broken (raw ×130 rockets, 3% scaling double-divided in the bomblet path, static boost 2000, test mode enabled); the 414th's flown values replace them in upstream's own config architecture. | 🔵 **Pushed as [PR #880](https://github.com/dcs-retribution/dcs-retribution/pull/880)** (2026-07-19) — inventory item 21 |
| **[CH] Iran 2020 faction + pack** | Mod-dependent factions are normal upstream (HDS, CurrentHill assets elsewhere). #784 was **self-withdrawn, never rejected** — re-carve behind the existing mod toggle. | Re-carve candidate |
| **Doctrine default *values*** (QRA radii, engagement ranges, `QRA_SINGLE_SHIP_PROBABILITY`) | The mechanisms are largely upstream (#782 et al.). Propose the tuned numbers as defaults **with the flown rationale**; if upstream prefers different defaults, fine — defaults are their call, the proposal costs one PR. | Rides the QRA-family carves |
| **C-130J EW physics constants** (spoof curve, burn-through) | Ship **with** the C-130J framework carve as its tested tuning, constants documented (the HANDOFF doc's rationale travels with the PR). Not separable from the framework — sequenced behind it. | Rides the Tier-3 C-130 carve |
| **TIC stance tuning** | Same shape: the stance profiles are the tested tuning of the TIC engine; they travel with the TIC carve as defaults-with-rationale. | Rides the Tier-3 TIC carve |
| **Campaign content** (Red Tide, the COIN pair, Tanker War, Desert Storm 91, Yankee Station, Red Flag 81-2, Velvet Thunder edits) | Content PRs after an **identity-strip pass** (the Red Tide payload in `docs/dev/upstreaming/red-tide/` is the worked template — 414th naming/preseeds stripped, validated headless on upstream dev). One campaign per PR; each needs its feature dependencies upstream first (a COIN campaign without the COIN engine is a shell — sequence content behind capability). | Red Tide: **payload READY** (inventory item 14). Others: after their features land upstream |
| **Campaign preseeds** | Preseeds of fork-only settings ride each campaign's PR trimmed to the settings upstream actually has at that point. | Mechanical, per-campaign |

**Standing fork divergences that are *merge discipline*, not upstreamability calls**
(preserve on every dev-pull; they don't belong to this queue): the #823 frontline
merge divergences (TIC movement-ownership guard, `total_frontline_units`
denominator), the AGM-65A → Rockeye fallback (upstream **rejected** the change on
#847 — respect the verdict, keep the fork's value locally), and the #879 alarm-state
adaptation (the fork's #231 IADS-owned EMCON design).

---

## The feature ledger

Readiness marks reuse the inventory legend (🟢 READY · 🟡 NEAR · 🟠 CARE · 🔵 DONE/IN
REVIEW). "Strip" = the 414th slice to remove for a clean PR.

### Already upstream (reconcile-on-merge applies)

| Feature | Upstream PR |
|---|---|
| Plugin `descriptionInUI` (§14) | #841 merged |
| Building-card placeholder (§4 slice) | #793 merged |
| Weapons coverage/repairs | #826 merged |
| OPFOR aggressiveness fix | #789 merged |
| Targeting-pod era data | #871 merged |
| Bulk waypoint altitude UI | #805 merged 2026-07-19 |
| JHMCS / props era gating (§24) | #843 merged 2026-07-19 |
| Per-squadron country + pilot names (§23) | #854 merged 2026-07-19 |
| Motorpool depots (§56) | #859 (geofffranks) merged 2026-07-19 — fork pre-adoption reconciled |

### In review (keep healthy)

| Feature | PR | Owes |
|---|---|---|
| Recon fog-of-war (§3 PR #1) | #828 | ✅ Rebased + un-drafted 2026-07-19 (one commit on dev @ `acf02b75`, 451 tests green) — awaiting maintainer review |
| Splash Damage coherent defaults (item 21) | #880 | Opened 2026-07-19 — awaiting maintainer review (offer to split bug-fixes from tuning stands in the PR body) |
| Cruise missile strikes (§63 core) | #872 | ✅ Ready for review 2026-07-19 — the DM flew the full loop locally ("works 10/10") and the defender launch wake was ported into the PR (Skynet-adapted comments), un-drafted |
| Curated carrier comms (§65) | #874 (draft) | Un-draft after B18 in-game pass |
| Culled-region kill tracking | #873 (draft) | Un-draft when validated |
| Cruise/patrol altitude | #806 | Review response |
| MFD SAM hiding (§7) | #794 | Review response |
| Wind override UI | #792 | Review response |
| Final-waypoint crash (§8 slice) | #788 | Review response |

### Tier 1 — pure-Python / data (easy carve)

Everything from the original Tier-1 table still applies (planner unpredictability
§17, target precision §5, weapon dates, settings QOL §16, drop-spawn §20, campaign
maker, DEAD gate, support orbit, despawn accounting, kneeboard pagination). New
since the last revision (§29–§73):

| Feature | Value | Strip | Readiness |
|---|---|---|---|
| §29 SITREP digest (`game/sitrep.py` + surfaces) | High | none | 🟢 |
| §35 convoy interdiction (engine side — real-convoy top-up) | High | Vietnam framing → generic "trail logistics" | 🟢 |
| §40 campaign phases (Tier-0 inference + planner emphasis + authored arcs) | **Very high** | 414th campaign arcs stay per-campaign | 🟡 (client ribbon = Tier 2 half) |
| §43 per-aircraft flight defaults | High | none | 🟢 (Q1 pass owed) |
| §44 long-range carrier ops | Medium | campaign preseeds | 🟡 P2 |
| §45 F10 support-orbit markers | High | none | 🟡 R1 |
| §46 route-aware fuel planning + fuel brief | **Very high** | none | 🟡 S1 |
| §47 continuous clock & weather | High | none | 🟡 T1 |
| §48 commitment ceiling | Medium | sequenced behind the will economy | 🟡 |
| §52 C2 decapitation → planner degradation | High | none | 🟡 B6 |
| §53 war economy | **Very high** | Red Tide preseeds | 🟡 (multi-turn pass owed) |
| §54 munitions availability | High | scarce-list is curated data — travels | 🟡 |
| §55 red intent (adaptive posture) | **Very high** | none | 🟡 B7 |
| §60 SAM radar redundancy | Medium — **balance opinion, needs the realism-notes rationale attached** | none | 🟡 B12 |
| §62 squadron-sequenced modex | High | none (note: parked per-pilot branch is the *upstream* #862/#863 answer) | 🟢 B15 ☑ |
| §64 carrier deck spawn policy | High | none | 🟡 B17/B26 |
| §66 generated-mission archive | Medium | none | 🟢 |
| §67 weather-aware planning | High | none | 🟡 B19 |
| §68 adaptive procurement | High | none | 🟡 B20 |
| §69 SEAD-before-strike coordination | **Very high** | none | 🟡 B21 |
| §70 COMINT (campaign take, C0) | Medium/High | C1/C2 Lua halves → Tier 3 | 🟡 B22 |
| §71 F-4E expanded weapons (XW convention) | Medium | none (mod-gated by design) | 🟡 B24 |
| §73 loadout default-for-task | High | none | 🟡 Q2 |
| Will economy + profiles (Vietnam layer W1–W6, generalized `will:`) | High | Vietnam campaign arcs stay per-campaign | 🟡 M-rows |
| COIN engine family (C1–C4: regen, re-infiltration, IED, HVT, dispersed, concealment) | High (a whole COIN mode) | campaign content + preseeds | 🟡 P-rows — carve as a family once flown |

### Tier 2 — client (React)

Unified map layers panel (§19), fog overview toggle client half, drop-spawn dialog,
campaign-status ribbon (§40), supply overlay (§53), minefields overlay (§57), downed
pilots layer (§21), stroke-signature system (§28) — all must land in upstream's own
map-control surfaces, shipped alongside their Python halves.

### Tier 3 — vendored-Lua features (high value, hard carve)

The original five (SCAR/TARS/TIC/QRA/C-130J) plus, from §29–§73:

| Feature | Value | Note |
|---|---|---|
| Vietnam Ops suite (§32–§39: Arc Light, flak, NGFS, harassment, gaggle, FAC, snake-nape) | High | One plugin, per-feature toggles already default-OFF |
| §49 mobile missile relocation (SCUD hunt) | High | S2 flown ✓; fire-window + stagger hardened |
| §50 convoy ambush + ambient convoys | High | engine side Tier 1; plugin side here |
| §51 comms jamming / §70 C1–C2 red net | Medium/High | pair them — one comms-war story |
| §57 air-droppable minefields | High | B9 pass owed |
| §58 briefing popup | High | B10 ☑ VERIFIED |
| §59 ground-AI sleep | **Very high** (MP perf) | B11 pass owed |
| §61 host red scramble | Medium | host/event tool |
| §72 carrier deck decorations | Medium/High | B25 pass owed |
| §21 Combat SAR family (+ §15 Sandy, MIA/POW) | High | the biggest single loop; carve after the G-row queue drains |
| MANTIS IADS engine + bridge | **Very high** | the fork's flagship runtime; needs an upstream Lua champion — propose after a track record of smaller Lua carves lands |

---

## The wave program (updated 2026-07-19)

Waves 0–2 of the original program are **done** (#841, #842*, #828 pushed; *#842
closed unmerged — re-carve candidate). The standing crowded-zone rule holds: check
`gh pr list` for the surface first; when someone else owns it, contribute by
reviewing their PR.

- **Wave R (standing): reconcile-on-merge.** Runs forever. The 2026-07-19 sync is
  the template (reconciled §23/§24/§56/#805 to upstream's merged shapes same-day).
- **Wave 3 (now): finish the open set + the ready fixes.** ✅ #828 rebased + un-drafted;
  ✅ Splash Damage #880 pushed (both 2026-07-19). Still open: fly B16/B18
  and un-draft #872/#874. Push the 🟢 READY inventory items with no crowd collision:
  blue-block miz markers (item 17), helo CFIT trio (item 16, C8), F-14A payload
  `unitType` fix (item 20), empty-`aircraft:` crash (item 12), landmap perf re-carve
  (item 1 / #842 closed). **Red Tide campaign publication (item 14)** — the payload
  is built; push it.
- **Wave 4: the big pure-Python systems.** §40 phases → §55 red intent → §53/§54
  economy → §46 fuel → §69 SEAD coordination → §67/§68 → §47 clock → the rest of
  Tier 1. Each its own default-preserving PR, flown first where a checklist row
  exists.
- **Wave 5: the Lua features.** Cheapest, best-evidenced first (§58 briefing ✓,
  §49 SCUD ✓, §59 sleep after B11) → the Vietnam Ops suite → §50/§57 → the
  CSAR family → MANTIS last, with the track record behind it.
- **Wave 6: content + last-mile.** Campaign publications (Red Tide first), the
  Splash Damage defaults PR, the Iran pack re-carve, doctrine-defaults proposals.

**The honest read stands, minus the old carve-out:** ship it back — *all* of it —
just not as one monolithic push. The seam between capability and identity is
sharp in the code; the identity layer is small and it, too, travels as content
and defaults-with-rationale. The work is carving patiently, lowest-difficulty
first, with the in-game-pass checklist as the gate.

---

## Cross-references

- [414th-upstreaming-inventory.md](414th-upstreaming-inventory.md) — the tactical
  carve queue + per-PR mechanics (now including the last-mile items).
- [414th-ingame-pass-checklist.md](414th-ingame-pass-checklist.md) — the gate; a row
  reaching ☑ VERIFIED is what clears a runtime feature for its wave.
- [414th-features.md](414th-features.md) — per-feature engineering internals.
- `docs/dev/upstreaming/fog-of-war/` + `docs/dev/upstreaming/red-tide/` — the worked
  carve-kit examples (capability and content respectively).
