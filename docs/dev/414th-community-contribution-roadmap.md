# 414th — Community Contribution Roadmap (the long view)

> **Last verified against live upstream state: 2026-08-02.** PR numbers and statuses
> below were checked with `gh pr view`/`gh pr list` on that date — re-verify before
> trusting a status more than a couple weeks old; this doc drifts fast (nine "in
> review" rows had gone stale — mostly closed — over the ~13 days since the prior
> revision).

> **POLICY (2026-07-19, squadron directive): everything is upstreamable.** There is no
> permanent "fork-only" category — a thing either goes back clean and correct, or it
> waits in the queue until it can. "Can't half-ass it" is the bar: every carve ships
> with its rationale, its tests, and its in-game evidence. Carve *difficulty* is a
> sequencing input, never an exclusion. The old "⛔ NEVER" list is retired; its
> survivors are re-filed under **the last-mile queue** below with what each one needs.

The [upstreaming inventory](414th-upstreaming-inventory.md) is the tactical carve
queue (per-PR mechanics). This doc is the strategy: what goes back, in what order,
and what each item still owes.

**Where this stands (refreshed 2026-08-02):** the door is open and staying open. **8
fork PRs are merged upstream** (793, 805, 826, 841, 843, 854, 871, and **#889** —
merged since the last revision) — three of them (#805 bulk waypoint altitude, #843
JHMCS era gating, #854 per-squadron country) in a single day back on 2026-07-19 —
plus the maintainers merged geofffranks' #859 motorpool, which the fork had
pre-adopted as §56. The fork is a recognized contributor. The
`sync/upstream-dev-2026-07-19` merge is the reference implementation of
**reconcile-on-merge** (see Workstream 1).

**The honest churn since 7/19:** review is genuinely happening, not stalling — but a
striking number of PRs closed without merging in the last two weeks, several as
recently as *today*. None read as a maintainer rejection of the idea; each is either
a design redirect (do it a different way), a scope fold-in (join a bigger effort),
a self-close pending rework, or simply superseded by a follow-up PR. See the "In
review" table below for the current, verified state of every open item — don't
trust an older snapshot of this table.

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
| **[CH] Iran 2020 faction + pack** | Mod-dependent factions are normal upstream (HDS, CurrentHill assets elsewhere). #784 was **self-withdrawn, never rejected** — re-carved clean behind a new `iranmilitaryassetspack` toggle, the exact pattern of the six CH packs upstream already carries. | 🔵 **Pushed as [PR #886](https://github.com/dcs-retribution/dcs-retribution/pull/886)** — un-drafted, open, awaiting maintainer review |
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

Verified live 2026-08-02. Nine rows from the prior revision had gone stale — mostly
closed, one superseded by a follow-up PR — since 2026-07-20.

| Feature | PR | Status |
|---|---|---|
| Fixed-wing CTLD paradrop (§76 core) | #884 | 🟢 OPEN, not draft — awaiting maintainer review |
| VWV v3.2.0 registration (item 22) | #881 | 🟢 OPEN, not draft — awaiting maintainer review |
| [CH] Iran 2020 pack (last-mile queue) | #886 | 🟢 OPEN, not draft — awaiting maintainer review |
| Squadron country + Air Wing selector (§23 follow-on, answers the #854/#627 Discord ask) | #896 | 🟢 OPEN, not draft — trimmed to Druss99's request (yaml pin + selector, no default-behavior change); awaiting merge |
| Cruise missile strikes (§63 core) | #872 | 🟢 OPEN, not draft — the DM flew the full loop locally ("works 10/10"), defender launch wake ported in; awaiting merge |
| Curated carrier comms (§65) | #874 | 🟢 OPEN, not draft — un-drafted; awaiting merge |
| Splash Damage coherent defaults (item 21) | #880 | 🟡 OPEN, still draft — active review thread on the offer to split bug-fixes from tuning |
| Sborka "Dog Ear" acquisition radar (item 23, new since last revision) | #887 | 🟡 OPEN, draft — vanilla-unit SHORAD radar fix, un-draft call open |
| Bulk-altitude for target/refuel legs (§805 follow-up, new since last revision) | #920 | 🟡 OPEN, draft — opened 2026-07-31 |
| Real per-aircraft patrol altitude yaml values (new since last revision) | #925 | 🟡 OPEN, draft — opened 2026-08-02, **supersedes #806** below (Druss99's suggested direction) |
| Recon fog-of-war (§3 PR #1) | ~~#828~~ | 🔴 **CLOSED** 2026-07-20 — Druss99: fold into a larger optional-script recon-mission-type effort first; re-scope before re-opening |
| Lua plugin test harness (the fork's `tests/lua/`) | ~~#882~~ | 🔴 **CLOSED** 2026-08-02 — self-closed, no successor yet; the Wave-5 enabler needs a decision on why/whether to re-open |
| MIST 51-symbol shim (was stacked on #882) | ~~#883~~ | 🔴 **CLOSED** 2026-07-20 — stack partner closed; needs re-basing once #882's fate is decided |
| Custom victory conditions (§75 core) | ~~#885~~ | 🔴 **CLOSED** 2026-07-20 — Druss99 has his own local branch and is taking it over; drift-watch only, not a re-carve candidate |
| Culled-region kill tracking | ~~#873~~ | 🔴 **CLOSED** 2026-07-21 — Starfire13 raised a correctness question (culled-region strike-target tracking) the fork's own investigation partly answered; needs the fix folded in before re-opening |
| SAM site layout variety + EWR pool (item, refresh of old #791) | ~~#892~~ | 🔴 **CLOSED** 2026-08-02 — active review (geofffranks AI-review pass addressed, Ramius007 raised default-layout-size feedback on SA-11/17/BUK-M3) then self-closed same day; needs a decision on the layout-size feedback before re-opening |
| SAM guidance-radar redundancy (§60) | ~~#893~~ | 🔴 **CLOSED** 2026-08-02 — active review (Starfire13 asked about AI/SEAD handling of the double radar, a companion guard test was added per geofffranks' review) then self-closed same day alongside #892; same needs-a-decision status |
| Cruise/patrol altitude (§scatter band) | ~~#806~~ | 🔴 **CLOSED** 2026-08-02 — closed in favor of **#925** above (Druss99's suggested per-aircraft-yaml direction) |
| Blue-block miz markers (item 17) | ~~#891~~ | 🔴 **CLOSED** 2026-07-20 — self-closed on Starfire13's Normandy-density + block-consistency review; re-carve owed (see last-mile queue) — **no re-carve opened yet** |
| MFD SAM hiding (§7) | #794 | 🟢 OPEN, not draft — awaiting review |
| Wind override UI | #792 | 🟢 OPEN, not draft — awaiting review |
| Final-waypoint crash (§8 slice) | #788 | 🟢 OPEN, not draft — awaiting review |

**Pattern worth naming:** four of the six 2026-08-02 closures (#882, #883, #892,
#893) closed the *same day*, mid-review-thread, with no stated reason and no
successor PR yet opened. That's not "rejected" — it reads as a batch
housekeeping/reset — but it also means those four need an explicit decision
(re-open as-is, fold in the outstanding review feedback first, or drop) rather than
being carried forward on autopilot next revision.

### Tier 1 — pure-Python / data (easy carve)

Everything from the original Tier-1 table still applies (planner unpredictability
§17, target precision §5, weapon dates, settings QOL §16, drop-spawn §20, campaign
maker, DEAD gate, support orbit, despawn accounting, kneeboard pagination). New
since the last revision (§29–§73):

> **REMOVED FROM THE FORK 2026-07-21 — do not carve, these no longer exist:** §40
> campaign phases, §48 commitment ceiling, §53 war economy, §54 munitions
> availability, and §55 red intent (adaptive posture), along with the political-will
> economy they were built on (`WillWeights`, the `will:` campaign profiles, the
> negotiation-verdict ending). All five were in the prior revision's table as active
> 🟡 carve candidates; that was stale even at the time the fork's own docs already
> recorded the removal. Verified 2026-08-02: no live code references remain outside
> save-migration tombstones in `game/persistency.py` (so a pre-removal save still
> unpickles). If any of this is ever wanted again it would be a fresh design, not a
> resurrection — see CLAUDE.md's §40/§48/§53/§54/§55 entries for the removal record.

| Feature | Value | Strip | Readiness |
|---|---|---|---|
| §29 SITREP digest (`game/sitrep.py` + surfaces) | High | none | 🟢 |
| §35 convoy interdiction (engine side — real-convoy top-up) | High | Vietnam framing → generic "trail logistics" | 🟢 |
| §43 per-aircraft flight defaults | High | none | 🟢 (Q1 pass owed) |
| §44 long-range carrier ops | Medium | campaign preseeds | 🟡 P2 |
| §45 F10 support-orbit markers | High | none | 🟡 R1 |
| §46 route-aware fuel planning + fuel brief | **Very high** | none | 🟡 S1 |
| §47 continuous clock & weather | High | none | 🟡 T1 |
| §52 C2 decapitation → planner degradation | High | none | 🟡 B6 |
| §60 SAM radar redundancy | Medium — **balance opinion, needs the realism-notes rationale attached** | none | 🔴 pushed as #893, closed 2026-08-02 mid-review — needs the re-open decision above |
| §62 squadron-sequenced modex | High | none (note: parked per-pilot branch is the *upstream* #862/#863 answer) | 🟢 B15 ☑ |
| §64 carrier deck spawn policy | High | none | 🟡 B17/B26 |
| §66 generated-mission archive | Medium | none | 🟢 |
| §67 weather-aware planning | High | none | 🟡 B19 |
| §68 adaptive procurement | High | none | 🟡 B20 |
| §69 SEAD-before-strike coordination | **Very high** | none | 🟡 B21 |
| §70 COMINT (campaign take, C0) | Medium/High | C1/C2 Lua halves → Tier 3 | 🟡 B22 |
| §71 F-4E expanded weapons (XW convention) | Medium | none (mod-gated by design) | 🟡 B24 |
| §73 loadout default-for-task | High | none | 🟡 Q2 |
| Vietnam W5 (GCI-ambush doctrine adaptation) + W6 (red-tempo schedule, rehomed off the removed will economy) | Medium | Vietnam campaign arcs stay per-campaign | 🟡 M-rows (**the W1/W2/W2b political-will economy itself was REMOVED 2026-07-21 — do not carve that part; only W5/W6 survive**) |
| COIN engine family (C1–C4: regen, re-infiltration, IED, HVT, dispersed, concealment) | High (a whole COIN mode) | campaign content + preseeds | 🟡 P-rows — carve as a family once flown |

### Tier 2 — client (React)

Unified map layers panel (§19), fog overview toggle client half, drop-spawn dialog,
minefields overlay (§57 — **shelved 2026-07-30**, still in the tree but hidden from
every settings surface; not preseeded anywhere, so this row is dormant until it's
resumed), downed pilots layer (§21), stroke-signature system (§28) — all must land
in upstream's own map-control surfaces, shipped alongside their Python halves. (The
campaign-status ribbon's §40/§53 halves — phases and supply — were removed with
their Python backends 2026-07-21 and are gone from this list.)

### Tier 3 — vendored-Lua features (high value, hard carve)

The original five (SCAR/TARS/TIC/QRA/C-130J) plus, from §29–§73:

| Feature | Value | Note |
|---|---|---|
| Vietnam Ops suite (§32–§39: Arc Light, flak, NGFS, harassment, gaggle, FAC, snake-nape) | High | One plugin, per-feature toggles already default-OFF |
| §49 mobile missile relocation (SCUD hunt) | High | S2 flown ✓; fire-window + stagger hardened |
| §50 convoy ambush + ambient convoys | High | engine side Tier 1; plugin side here |
| §51 comms jamming / §70 C1–C2 red net | Medium/High | pair them — one comms-war story |
| §57 air-droppable minefields | High | **Shelved 2026-07-30** — dormant (not preseeded, settings hidden); resume before carving, B9 pass still owed |
| §58 briefing popup | High | B10 ☑ VERIFIED |
| §59 ground-AI sleep | **Very high** (MP perf) | B11 pass owed |
| §61 host red scramble | Medium | host/event tool |
| §72 carrier deck decorations | Medium/High | B25 pass owed |
| §21 Combat SAR family (+ §15 Sandy, MIA/POW) | High | the biggest single loop; carve after the G-row queue drains |
| MANTIS IADS engine + bridge | **Very high** | the fork's flagship runtime; needs an upstream Lua champion — propose after a track record of smaller Lua carves lands |

---

## The wave program (refreshed 2026-08-02)

Waves 0–2 of the original program are **done**, with mixed outcomes worth recording
rather than glossing: #841 merged; **#842 (landmap perf) closed unmerged, and its
job is now done anyway** — upstream shipped their own fix as **#876
(`shapely.contains_xy`)**, merged and pulled into the fork in the 2026-08-02 sync,
so #842 is not a re-carve candidate anymore, it's simply superseded; #828 (fog-of-war)
was pushed, then closed 2026-07-20 pending the larger recon-mission-type redesign
Druss99 asked for. The standing crowded-zone rule holds: check `gh pr list` for the
surface first; when someone else owns it, contribute by reviewing their PR.

- **Wave R (standing): reconcile-on-merge.** Runs forever. The 2026-07-19 sync is
  the template (reconciled §23/§24/§56/#805 to upstream's merged shapes same-day);
  the 2026-08-02 sync repeated it for #876/#913/#917/#918/#919/#922/#923.
- **Wave 3 (in progress, needs a gardening pass): finish the open set + the ready
  fixes.** Genuinely open and awaiting review: #872, #874, #880, #881, #884, #886,
  #887, #896, #920, #925. **Needing an explicit decision before being carried
  forward** (all closed 2026-07-20 → 2026-08-02, no successor opened yet): #828,
  #882, #883, #885 (ceded to Druss99, not ours to decide), #873, #891, #892, #893,
  #806 (superseded by #925, no decision needed there). From the inventory: F-14A
  payload `unitType` fix (item 20) **done — merged as #889**; empty-`aircraft:`
  crash (item 12) **closed, verdict accepted** (Druss99 wants a hard error, not a
  defensive guard — respect it, don't re-open as originally scoped); landmap perf
  (item 1) **superseded by upstream's own #876**, drop from future queues; blue-block
  miz markers (item 17) still needs its re-carve with the consistency framing +
  Normandy pruned (see the last-mile queue); helo CFIT trio (item 16, C8) still open.
  **Red Tide campaign publication (item 14)** — the payload is built; push it.
- **Wave 4: the big pure-Python systems.** §46 fuel → §69 SEAD coordination → §67/§68
  → §47 clock → the rest of Tier 1. (§40 phases, §48 ceiling, §53/§54 economy, and
  §55 red intent are **removed from the fork** — struck from this wave entirely,
  see the Tier 1 table note above.) Each its own default-preserving PR, flown first
  where a checklist row exists.
- **Wave 5: the Lua features.** Cheapest, best-evidenced first (§58 briefing ✓,
  §49 SCUD ✓, §59 sleep after B11) → the Vietnam Ops suite → §50 → the CSAR family
  → MANTIS last, with the track record behind it. (§57 minefields dropped from this
  wave's near-term ordering — shelved in the fork since 2026-07-30, dormant until
  resumed.)
- **Wave 6: content + last-mile.** Both last-mile items from Wave 3/4's original
  plan are **already pushed and in flight**: Splash Damage defaults as #880 (draft,
  active review), the Iran pack re-carve as #886 (open, awaiting review). Remaining:
  campaign publications (Red Tide first, item 14), doctrine-defaults proposals.

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
