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
  (priority-ordered, with readiness marks), plus the **last-mile items** (need
  packaging/rationale) and the **merge-discipline divergences** to preserve on dev-pulls.
  **Policy 2026-07-19: everything is upstreamable — "clean and correct" is the bar; there
  is no permanent fork-only category.**
- [docs/dev/414th-community-contribution-roadmap.md](docs/dev/414th-community-contribution-roadmap.md) —
  the **long view** (rewritten 2026-07-19 for the everything-upstreamable policy + contributor
  status): the two-axis (community-value × carve-difficulty) classification of *every* feature
  through §73, the **last-mile queue** (Splash Damage defaults, Iran pack, doctrine defaults,
  campaign content — each with its upstream story), the three workstreams
  (**reconcile-on-merge** · drain the queue · package the last mile), and the updated wave
  program.
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
    **🔓 FEATURE LOCK LIFTED 2026-08-03 (DM call: "Red Tide feature lock is not existent").**
    Red Tide takes new features/mechanics/content/laydown again **on the same terms as any
    other campaign** — ordinary design + test + in-game-pass bar, no special permission gate;
    **there is no longer a "Red Tide lock override" process** (the two earlier overrides stay
    in the note as history, not precedent). Still true as engineering judgement, not as a
    rule: it is a **shipped, flown, balanced** build with squadron history, so a
    balance-re-skewing change owes a playtest, and a NEW-game requirement must be said
    loudly. **Two deliberate exclusions survive the lift because they were SEPARATE calls,
    not lock consequences** — the §71 F-4E pack stays un-preseeded (the DM's personal
    option) and §57 minefields stay shelved fork-wide; the lift does not re-open either.
    The banner atop that note is the source of truth (the original lock text is retained
    there, collapsed, as history). **Historical — S-300 regiment restructure 2026-07-12
    (landed pre-lock; recorded at the time as a lock-override go-ahead):** the three rear S-300 hubs
    (Sperenberg/Kastrup/Schönefeld) were restructured into **3-battalion regiments +
    shared EWR** (the reference implementation of the SAM-belt STANDARD) — single-radar battalions
    via the `Russia 1980 (Red Tide)` faction fork (§60 reverted for RT's S-300/SA-5 only; front
    legacy SAMs keep §60 doubling). NEW game required; tests in `test_red_tide_sam_regiments.py`.
    **Historical — lock-override #2 same day (user call off the roster era-audit):** the fork faction gained the
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
    (persistent ISR — the `recon` plugin banks drone overflights as confirmed BDA, so the drones
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
  - `414th-marianas-2027-campaign-notes.md` — **Marianas "Second Island Chain (2027)"** (the
    fork's **modern-day China campaign**, built 2026-08-02). DCS ships no Chinese terrain, so a
    China war can only be fought where China must come to *us* — and exactly one map is that
    place with **zero fiction**: Guam is the Second Island Chain and Andersen AFB is the target
    set the PLA Rocket Force was built to range. **USA 2020 vs the fork faction `China 2027`** on the CurrentHill China pack + High Digit SAMs. Forked from Fuzzle's `pacific_repartee` laydown (rather than edited in place —
    campaign-ownership model; his 2005 scenario stays intact and convergent with upstream) after
    a headless audit found that campaign **cannot** be modernized by a faction swap: red
    airframes are hardcoded, so `China 2020` upgrades the ground/naval kit and leaves **J-7B**
    (a 1960s MiG-21 copy) flying; no red AEW&C is authored though both factions declare the
    KJ-2000; **165 red vs 62 blue** because six carrier blocks omitted `size:` and defaulted to
    12 each; **no `missile`-category TGO anywhere**, so the pack's DF-21D/CJ-10/YJ-12B are never
    placed; and there is no `plugins:` block at all. **Three structural changes**: (1) **the
    premise is inverted** — Guam is US soil and *holds*, the PLA took Rota/Tinian/Saipan, and the
    war is fought northward; that unlocks **Andersen's 194-slot ramp**, the only one on the map
    that can base a heavy wing (B-1B/KC-135/E-3A/C-130J), instead of Repartee's carrier-only
    3-CP cap. (2) **Two dormant airfields are activated** — the Marianas map has 8 fields and
    Repartee used 4, because a `NEUTRAL` airfield **is not a control point**: `control_points`
    gates on `is_blue() or is_red() or is_neutral()` and pydcs's `Airport.is_neutral()` returns
    **False** for NEUTRAL, so such a field silently ceases to exist (neutral CPs are real, but
    only via the explicit `NEUTRAL_FOB_UNIT_TYPE` declaration). Rota (the red strike field 90 km
    off Guam) and Pagan Airstrip go RED, Olf Orote BLUE; **North West Field stays NEUTRAL on
    purpose** — pydcs reports it with **zero runways**. Rota was never owned so it carries no
    authored garrison at all, hence one added SAM marker. (3) **Three PLARF sites** (Rota/Tinian/
    Saipan) make §49 shoot-and-scoot + §3 concealment into the campaign's signature hunt.
    **Landmap gotcha, worth knowing before authoring anything on this map:** only **Guam, Rota,
    Tinian and Saipan** exist in the Marianas landmap — Anatahan, Pagan, Agrihan and Uracus are
    all `is_in_sea` (pre-existing terrain data, inherited from Repartee, whose four FOBs sit on
    them), which is why no missile site is authored north of Saipan. Miz is **GENERATED** by
    `tools/build_marianas_2027_miz.py` (edits the ownership + adds the markers on top of
    `pacific_repartee.miz`, every added position landmap-validated, raises rather than degrading;
    all-vanilla so pydcs round-trips losslessly) — **never hand-edit it**. Preseeds §49+§3, §63
    cruise raids, §78 sea convoys + coastal anti-ship, §50 on Guam's two blue roads, §70 COMINT,
    §59 AI sleep, and every matching plugin (the §36 lesson). **The carrier air wing is the CJS
    Super Hornet package** (`fa_18efg` + `fa18ef_tanker` preseeded — the first campaign to preseed
    them): the Navy retired the EA-6B in 2015/USMC 2019, so a Prowler on a 2027 deck is the same
    anachronism as red's J-7B — VAQ-136 flies **EA-18G** (Escort Jammer 800 vs the Prowler's 790,
    and §77's runtime is airframe-agnostic so the swap is risk-free), the organic tanker is the
    **F/A-18E Tanker** (its `Refueling` priority of 0 is fine — `capable_of` gates on presence,
    not value), and §74's 2026-08-02 DTC cartridges cover all three. **Tanker gotcha, caught by
    the DM after the first cut:** the **KC-135 MPRS is a DROGUE tanker**
    (`tanker_refuel_types: probe` — the multi-point kit *is* the wing drogue pods), not a
    both-methods one; every jet at Andersen/Won Pat is `air_refuel_type: boom` (F-15C/E, F-16CM,
    B-1B, A-10C), so an MPRS-only Andersen left the whole land wing unable to tank. Andersen now
    bases **KC-135 ×4 (boom) + KC-135 MPRS ×2 (drogue)**, and a standing test walks every blue
    airframe asserting some blue tanker's `can_refuel_from` accepts it. **One legacy F/A-18C squadron is kept on the deck
    on purpose** (guard-tested) so an MP pilot without the mod still has a carrier ride. No front lines (the islands aren't connected —
    Air Assault and §76 C-130J paradrops are the capture mechanic); red fields no ambient convoys
    because no two red bases share an island. Headless-verified end-to-end (18 CPs — BLUE 6 /
    RED 13 — 110 TGOs/572 units, all 38 squadrons resolve, **164 blue vs 98 red**); CI-locked in
    `tests/fourteenth/test_marianas_2027.py` (23 tests incl. standing parking-fit,
    tanker-compatibility, pin-band-match, no-sandwich, explicit-`size:` and
    mod-free-carrier-squadron invariants). **Enemy faction `China 2027`** =
    `china_2020.json` with the obsolete **HQ-2 dropped** and **SA-20/S-300PMU-1 +
    SA-20B/S-300PMU-2 added**, so `high_digit_sams` is a hard requirement. Measured
    alternatives, for the record: HDS adds **only the HQ-2** to stock China 2020 and
    **nothing** to USA 2020; `Redfor (China) 2020` can field the S-300PMU family but also
    rolls **SA-2/SA-6** (observed spawning as *base defences*, which `ground_forces`
    cannot reach) and loses the Chinese country identity. **Two `ground_forces` rules
    learned here:** overrides reach **authored markers only** (base defences roll from the
    faction roster), and the preset's task must match the marker's **band** or the override
    is **silently discarded** (`get_unit_group_for_task` gates on `task in fg.tasks`) —
    the HQ-22 declares LORAD, so it needs a long marker, which is why Rota's is one.
    **Laydown re-seated 2026-08-02 off a DM finding** ("the CSG at the very north and
    Andersen blue with all the Red sandwiched in between"): inverting the premise without
    moving Fuzzle's north-anchored fleet left blue holding **both ends**. Blue's CVN/LHA
    now sit SW of Guam, **FOB Uracus reverts to RED** (a blue island 780 km behind red
    lines was the other half of the sandwich), and red's 3 carriers / 2 LHAs / 18-hull
    screen are pulled from 398–854 km into the **60–330 km Guam–Saipan corridor** so they
    can contest it. Blue now occupies −102…+11 km and red 60…781 km, unbroken.
    **F-22A det at Andersen** (`f22_raptor` preseeded — the real Raptor rotation base),
    kept *alongside* a trimmed F-15C squadron so a host without the mod still has an
    air-superiority arm (the carrier's legacy-Hornet pattern). Fixed in passing:
    **`F-22A.yaml` authored no `max_range`**, so it silently fell back to the 150 NM
    default — less than half the F-15C's 400 — which would have range-gated the Raptor
    out of the PLAN carrier groups (108–157 NM) and everything north of Saipan; now an
    honest `max_range: 450` (fleet-wide data fix, upstream-carve candidate). Still
    wrong in that yaml and deliberately untouched: its radios are the **P-51's
    SCR-522**, flagged by an in-tree comment and left for its own change.
    **PLAN fleet rebuilt on the HHQ-9 shooters (DM finding):** carrier groups were being
    screened by **Type 022 missile boats (4 km AD) and Type 056A corvettes (8 km)** while
    the **Type 055 and Type 052D (250 km) never appeared at all** — the stock
    `Chinese-Navy.yaml` preset supplies Type 052C/052B/054A, which satisfy the Naval Group
    layout's Frigate×2/Destroyer×2 slots outright, so `has_unit_for_layout_group` never
    fills from the faction roster. New preset `resources/groups/Chinese-Navy-2027.yaml`
    (Type 055 + 052D + 054B + 054A) and `China 2027` drops the littoral 022/056A + the
    superseded 052B from `naval_units`, so every red hull now carries ≥45 km AD.
    **`squadron_start_full: true`** — note the key is **singular**; the Theater wizard page
    reads `s.get("squadron_start_full", ...)` while its own field is `squadrons_start_full`,
    so a plural typo silently does nothing (pinned by a test).
    **Turn-1 SAM umbrella over Guam fixed (DM screenshot):** measured **13 of 31** red
    sites covering Andersen or the CSG. Governing number: **Guam→Saipan is 205 km, HHQ-9
    reaches 250 km**, so a modern PLAN group anywhere in the corridor covers Guam by
    construction — Rota (**75 km out**) dropped from HQ-22 to **HQ-7 point defence**
    (marker re-banded SHORT), Tinian's S-300PMU-2 → **HQ-22 (170 km, stops 5 km short)**,
    and the scattered ship markers use an **inshore-only preset**. Now **3 of 30**, all
    amphibious-group escorts (mobile/killable, deliberately kept). **Two more
    `ground_forces` rules:** naval groups **cannot be pinned at all** (`generate_ships`
    called `random_group_for_task(GroupTask.NAVY)` and never read the block — **FIXED
    2026-08-03 as a generic engine change**: `generate_navy` now routes through
    `get_unit_group_for_task`, and that method moved up from `AirbaseGroundObjectGenerator`
    to `ControlPointGroundObjectGenerator` so the carrier/LHA generators inherit it; the
    fill pool also now follows the task (`naval_units` for NAVY — it was always
    `ground_units`, so a naval slot could only ever be filled by a ground unit, i.e. never,
    silently shrinking the group). Upstream-carve candidate. Remaining un-pinnable:
    LHA/carrier CP escorts, which `LhaGroundObjectGenerator` builds from `naval_units`
    rather than a marker). **Ring SIZE is its own constraint:** after the coverage fix the
    map still read as a wall of red — **13 of 30 rings were 250 km** (only 2 contained
    Andersen, but Guam→Saipan is 205 km, so one HHQ-9 group covers a third of the theatre).
    Every ship marker is now pinned to the inshore escort preset and the area-defence
    destroyers stay concentrated with the carrier/LHA groups; 250 km rings **13 → 4**. The
    heavy preset was **deleted, not left registered-and-unused** — an unreferenced Navy
    preset is a hazard, since any future unpinned marker coin-flips onto it. `Naval-17/18/27`
    are unpinned deliberately (they bind BLUE and screen the US carrier group). **The
    Type 055 is REMOVED from the roster (flown Tacview 2026-08-03):** the first mission
    produced **374 launches, essentially all in the first five minutes** — both fleets
    emptied their AShM magazines before the player was airborne and the carrier died to
    **ten YJ-21 ASBMs fired between t=11s and t=99s**. Three causes compound: ships spawn
    `OptROE.WeaponFree` + alarm RED (`set_ship_engagement`, long-standing), modern AShM
    out-range the theatre (YJ-18 ~540 km vs a 205 km Guam–Saipan gap), and the compressed
    laydown put both fleets ~300 km apart at t=0. The 055 is the only YJ-21 carrier and the
    YJ-21 cannot realistically be intercepted; the 052D's YJ-18 demonstrably can (99 SM
    intercept shots in the same file). **The weapons-hold-start alternative was BUILT the
    next day as §81 N1** (`naval_weapon_release_stagger`) alongside the N2 magazine — both
    default OFF and deliberately **not preseeded here** until checklist B39 passes, so this
    campaign still relies on the 055 removal + the hull cull for now; the remaining deferred
    option is pushing the PLAN past the 500 km detection range (which undoes the
    compression). Also: **a preset must fill every layout slot it wants to control**
    (a frigates-only preset leaves Destroyer×2 empty, `has_unit_for_layout_group` fills it
    from the roster, and the roster's destroyers are the 250 km hulls — so the "light"
    group silently came back out at 250 km).
    **Turn-1 ATO was 100% defensive — diagnosed + fixed 2026-08-03** (flown `china.retribution`:
    33 packages, 28 BARCAP, **zero** strike/SEAD/DEAD/anti-ship, 71 of 223 airframes tasked,
    every offensive squadron at 0 — while `TheaterState` showed 25 SAM sites / 25 strike
    targets / 13 ships, so the commander was not blind). Established by re-planning the real
    save one lever at a time. **(1) BARCAP ate the fighter force**: rounds are
    `ceil(player_mission_duration / (barcap_duration - overlap))` then threat-scaled to
    `BARCAP_THREAT_CEILING` (2) **and doubled again for a fleet CP** — this laydown has
    **four** fleet CPs (2 CVN + 2 LHA) of 7 defended objectives, so the ceiling case is
    4×4 + 3×2 = **22 flights = 44 of the wing's 66 fighters**; offensive packages then
    proposed escorts into an empty pool and scrubbed (modern doctrine had
    `plan_strikes_without_full_escort=False` **and** `strike_escort_reserve=0`, neither
    campaign-authorable). **(2) the 150 NM gate cannot serve a 421 NM theatre** (Guam→Uracus
    780 km) — raising it **alone changed nothing** (BARCAP still held every fighter); it
    decides how much of red is *reachable* once they are free (400 vs 300 NM moved anti-ship
    6→10 and added the deep Strike packages). **(3)** `strike_through_air_defense_threat` was
    **not** a factor. Fixes, all three needed: **`MODERN_DOCTRINE.strike_escort_reserve` 0 → 8**
    (taken **fork-wide, DM call** — the squeeze is a *ratio* problem, not a fighter-poor-era
    one, so any modern campaign with more exposed objectives than fighters hits it; Cold
    War/WWII untouched, Red Tide is Cold War doctrine and unaffected) + campaign preseeds
    `max_mission_range_planes: 400` and `desired_barcap_mission_duration: 60` (2 rounds → 1).
    Measured on a fresh game, BLUE **26 pkg / 22 BARCAP / 2 offensive / 74 ac → 27 pkg /
    14 BARCAP / 25 offensive / 143 ac**; RED (also modern) 0 → 2. **Found on the way:** the CJS
    Super Hornet payload files index their pylon tables with named constants (`[WTL] = …`),
    which pydcs cannot parse — and the raise truncated the payload scan *before*
    `resources/customized_payloads`, so the fork's own authored fits were never read
    (**FA-18F and EA-18G had ZERO loadouts, FA-18E 2 of 13**). `game/dcs/payloadpatch.py` skips
    the file and keeps walking (called from `persistency.setup`, so headless paths are covered
    too — the app-side copy in `qt_ui/main.py` is now a wrapper); restores 13/13/4. Tests
    `tests/fourteenth/test_super_hornet_payloads.py`. **The CH Arleigh Burke Flight III is
    dropped from every blue faction** (`usa_2020`, `blufor_current`, `nato_baltic_2027`): the
    mod genuinely declares `airWeaponDist = airFindDist = 650000` (**351 NM**, verified against
    the installed `CH Military Asset Pack USA 1.5.0` database — NOT a fork transcription error)
    vs 160 km for the Flight IIA, and one hull blanketing the theatre in a threat ring corrupts
    threat-zone math for both sides; re-tuning the value was rejected (it would diverge the
    registration from the mod and break the export-verification invariant).
    In-game pass = checklist **T5**, the riskiest bit being whether
    a launcher scoots into the sea (the §49 radius is not landmap-checked). NEW game required
  - `414th-iraq-map-2928-notes.md` — **what DCS 2.9.28's Iraq map content unlocks** (design +
    authoring plan, no code/`.miz` edits yet; scoped 2026-07-26 off the 2.9.28.26283 changelog,
    which upstream picked up as `update dcs to 2.9.28.26283` #904 — a pydcs pin bump + refreshed
    `resources/terrain-beacons/` for Caucasus/Iraq/Kola). Headline: the **nine new named dams**
    (Alwand, Dukan, Fallujah, Haditha, Hemrin, Kut, Ramadi, Samarra, Diyala) are consumable as
    `power` scenery strike targets through the **stock** `SceneryGroup.from_trigger_zones` path
    with **zero code** — DS91 already ships 57 hand-authored Iraq scenery targets, so this is ME
    authoring, not engineering. The note carries each dam's computed map XY (via
    `Point.from_latlng(..., Iraq)`, the `supply_route_geo.py:62` call), the campaign split
    (**Fallujah/Ramadi/Dukan → Inherent Resolve** — Al-Taquddum sits between the first two and
    IR's own Highway-10 supply route runs through Fallujah; **Haditha/Kut → Desert Storm**;
    **Samarra/Hemrin/Diyala → both**, they sit in the shared Balad–Baghdad triangle; **Alwand
    parked**, 104 km off both AOs), and the verbatim blue-zone-`PROPERTY_1`-category +
    white-zone-`OBJECT ID` authoring convention, and the **guard for the authoring footgun** —
    `from_trigger_zones` RAISES rather than degrading, so a blue zone with no white zones inside
    (the natural half-finished state) fails **campaign load**; `tools/check_scenery_targets.py`
    mirrors the loader's pairing rules (errors = no/invalid category, no white zones; warnings =
    orphaned object-bound white zone, claimed white zone with no `OBJECT ID`), baseline **71
    campaigns · 712 objectives · 0 errors · 21 pre-existing orphan warnings**, CI-locked in
    `tests/fourteenth/test_scenery_targets.py`. **The new airfields ARE usable** — unfinished
    surroundings constrain *how* a field is used, never whether: undetailed terrain only bites
    where a campaign puts **ground** on it (a front line, `supply_routes:` convoys needing real
    roads, low-level CAS), none of which follow from basing aircraft there, so the safe patterns
    are rear/support basing (the DS91 off-map-Saudi pattern), an isolated air-only CP with no
    front, an island/maritime fight, or a divert field. Per-airfield: **Tromso** (Kola, 72 km from
    Bardufoss, inside `the_anvil_of_war`'s belt — Kola is mature, 2.9.28 only *polished* it) and
    **Zaranj** (Afghanistan, 19 km from the existing Nimroz, in `graveyard_of_empires`' western
    belt) are usable with **no caveat**; **Kharg** is usable **air/naval-only** (an island, so its
    surroundings are water — no front, no supply routes) either as a CP in a purpose-built
    maritime scenario or, needing no CP at all, as an `oil`/`fuel`/`derrick` scenery **target**
    set. Kharg's real blockers are **reach** (565 km from Al-Kut, so no current campaign gets
    near it — it is also an *Iranian* terminal, wrong belligerent for 1991 and irrelevant to 2016)
    and the pydcs pin: pinned pydcs Iraq has **19 airports**, no Kharg — and **no Bahrain**, which
    is roadmap, not 2.9.28 content. It remains the natural home for the Tanker War campaign
    (today on PG over substitute WRL geography) + a §78 coastal-battery showcase. Free wins:
    ED **fixed AI traffic at Mosul + H-3 Northwest** (IR's red anchor and DS91's blue complex),
    and Bashur/Al-Salam lighting opens night ops that §47's continuous clock actually reaches.
    **Gate before authoring = are the dam models destructible** (a white zone needs a destroyable
    object) — checklist **T4**, which also re-checks the taxi fixes + the DS91 parking-fit invariant
  - `414th-desert-storm-campaign-notes.md` — **Iraq "Umm al-Ma'arik (Desert Storm 1991)"**
    (the DM's homemade DS91 campaign fixed + modernized + promoted 2026-07-19: the KARI IADS
    as the Red Tide static-trio pattern (ADOC + 3 SOCs + comms/power relays at every red base
    + a P-37/1L13 EWR chain, MANTIS range-mode, 104 nodes), the Great Scud Hunt (9 authored
    Scud batteries × §49, two in the western baskets), a 12-route real-highway supply graph
    (`tools/supply_route_geo.py` mode `iraq_desert_storm`), the Instant Thunder → Scud Hunt →
    ground-offensive arc with a permanent Baghdad no-strike circle, the Coalition-cohesion
    will profile, and the Dictator-universe scenery names inherited from the Aladeen miz
    renamed to the real 1991 CENTAF target set. Fixed in passing: 6 silent squadron
    substitutions (a missing yaml list marker had dissolved the whole MiG-25 squadron) and the
    escort-starvation blue OOB; the NATO Desert Storm faction gained the A-10C Suite 7 +
    CH-47F Block I the DM authored (era-clamped by the date-gate preseeds). **Laydown v2 same
    day (the DM's call — historical accuracy + the parking audit):** blue holds only the
    seized **H-3 complex** + the **off-map Saudi rear** for the E-3/KC-135 wing — the Iraq map
    has ZERO 60×60 heavy stands west of Baghdad (slot_version-2 dimension resolution; the
    legacy `large` flag is zero map-wide), so big wings genuinely cannot base forward —
    Al-Asad reverts to red as **Qadessiya** (the real Foxbat home), red gains **Balad
    (al-Bakr)** + **Mosul (Firnas)**, the Fulcrum reserve moves off Al-Kut's helipad farm to
    **Al-Sahra (Tikrit)**, and the campaign climbs the M-113-authored pipeline-road **capture
    ladder H-3 → H-2 → Al-Asad** whose legs advance the front and become blue convoy roads as
    each rung falls. A standing **parking-fit test** asserts every based squadron has at least
    as many dimensionally-fitting slots as airframes. **First-fly fix + historical identities
    (same day):** the Bombcat's `air-to-ground` secondary had the planner fragging Tomcats at
    the SA-2 rings (the alias includes DEAD/SEAD; the airframe data carries `DEAD: 390`) →
    `secondary: air-to-air`; and **every squadron is named for its real 1991 unit** (VF-103 /
    58th TFS Gorillas / TF Normandy's 1-101st / the published IrAF squadron numbers — No. 84
    Sqn's Foxbats at Qadessiya), `female_pilot_percentage: 0` era-wide, and Iraqi squadrons
    author an **explicit empty nickname**, which now CLEARS the field (the
    `override_squadron_defaults` `config.nickname or None` one-liner) instead of leaving the
    def generator's random "Apoplectic Porcupine" roll; liveries deliberately un-authored (the
    installed-DCS livery-audit lesson). **Allied AI squadrons at the Saudi rear (same day):**
    RAF **No. 31 Squadron "Goldstars"** (Tornado GR4 standing in for the Granby GR1s; new
    UK-countried preset in `resources/squadrons/Tornado/`; the GR4 yaml gained an honest
    `max_range: 600` — the unset 150 NM default grounds any rear-based Tornado) + Daguet's
    **EC 2/5 "Île-de-France"** Mirage 2000Cs (the existing France preset bound by name) —
    the §23 layer gives all three national comms identity + pilot names (en_GB / fr_FR),
    probe-verified — plus **ER 1/33 "Belfort"**, Daguet's F1CR recon det on primary TARPS
    (the F1CT stands in, camera nose intact; its yaml gained `TARPS: 700` + honest
    `max_range: 450`; the same-silhouette-as-red's-F1EQ grounding story is baked into the
    campaign comment). CI-locked in `tests/fourteenth/test_desert_storm.py` (10 tests);
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
  - `414th-naval-magazines-notes.md` — **cross-turn naval magazines** (§81 N1+N2 LANDED
    2026-08-03 off the flown Marianas 2027 Tacview): the three separate facts behind
    "the whole fleet salvos in the opening minute, every turn" and which tier fixes
    which, why the key is `group_name` (not `original_name`), why §63 double-counting
    is solved by **disjoint weapon sets** rather than by unifying the two magazines,
    why `ReturnFire` beat `WeaponHold`, and **the load-bearing unknown** — DCS ROE is
    per-group, not per-weapon, so whether a held/winchester ship still engages an
    aircraft that hasn't shot at it is fly-only (checklist B39, test it FIRST).
    Deferred: N3 replenishment, N4 the unit-card readout
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
    byte-identical to the pre-#590 baseline. **CONSISTENCY COMPLETED 2026-07-20**
    (Starfire13's upstream #891 review ask — "for some objects you can only use one
    [CJTF block], yet for others both are acceptable"): the loader's last
    single-block classes now chain both blocks too — `factories` was BLUE-only (the
    mirror hole; a sweep found **3 shipped red-block factories silently dropped**:
    TblisiGap, RetakeTheFalklands, operation_allied_sword — now resurrected, binding
    their red bases by proximity, headless-verified), and front-line paths /
    shipping lanes / cp-convoy spawns (blue-only) + the neutral-FOB declaration
    (red-only) chained with **zero** shipped cross-block instances (pure authoring
    tolerance). **This is a deliberate FORK DEVIATION from a documented upstream spec, not a
    bugfix — established 2026-08-05 and worth knowing before touching this code:** the
    Custom-campaigns wiki's **"Unit Type Quick Reference" table prescribes a required CJTF
    block per class**, and upstream's loader implements it **exactly on all 19 classes**
    (Red: EWR / all 3 SAM ranges / ship / missile / coastal / offshore / neutral-FOB ·
    Blue: factory · Either: AAA / armor / ammo / strike / comms / power / command-center /
    FOB). A blue-block SAM marker is therefore dropped upstream **because the author broke
    the documented convention**, so the fork's read-both rule *activates authoring mistakes*
    as well as fixing real drops. **Measured content delta on the upstream campaign set:
    483 objects across 12 campaigns, of which 443 (91 %) is the two Normandy campaigns**
    (`normandy_full` 336 Tunguska + 9 Scud + 7 Silkworm authored under CJTF Blue, whose RED
    block holds only 10 FOB markers — so upstream generates **0** short-range SAM sites
    there and the fork generates **336**; `normandy_small` 75). ⚠️ **That Normandy inflation
    is live in this fork and has never been audited** — see the upstreaming inventory item 17.
    The upstream re-carve was **DROPPED 2026-08-05 (DM call)**: with code and docs already in
    agreement there is no bug to carve, and uniform-"Either" would be a spec change for
    upstream to decide. Fork-side the rule stays total: the block never decides whether an
    authored object exists — it means ownership only for the CP-defining classes and the
    bounded blue-marker preference. Contract-locked in
    `tests/test_miz_marker_binding.py`)
  - **Blank-start campaign maker** — REMOVED (2026-08-02): the New Game "Build your own
    (blank canvas)" wizard entry, the neutral-map paint step, Finalize, Save-as-Campaign, and
    the `blank_canvas`/`blanktheatergen`/`blankcampaign` machinery are fully ripped out. Any
    user-saved `blank_canvas` campaign YAML will no longer load. Do not restore.
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
    `414th-verification-cadence-notes.md` (**the fly-card throttle** — PROPOSED 2026-08-06,
    nothing built. Out of a methods audit: the in-game-pass backlog has no governor (**71
    outstanding vs 82 verified**, untested rows back to 2026-07-01 — counts are
    heading-scoped/first-marker-wins per `.claude/hooks/session-start.sh`; a naive whole-file
    grep reads 127/114 because the checklist quotes markers in prose constantly, a trap the
    hook's own header documents). **Capping the build rate
    is rejected** — the data says this is a *scheduling* problem, not a build-rate one:
    verification is bimodal, **46 rows in the 6 sessions around the scheduled Red Tide M1 vs
    17 across all of July with nothing scheduled, then 20 in the one day the Aug-1 card
    finally ran**, so a card-driven session adjudicates 10–20 rows and an opportunistic one
    adjudicates 1–2. The mechanism already exists — the debt register's §3 pre-flight desk
    pass / §4 fly card / §5 private-session card — but was built as a **one-off inside a
    document framed as disposable**, so nothing owns "what is the next card". **Cadence call
    RESOLVED 2026-08-06 (DM: "once a week for multiplayer events but I fly daily, we could
    really test every 2nd or third day locally") — which substantially revised the design and
    removed its stated kill condition.** The note had assumed cockpit time was the scarce
    resource; it is not, so there are **three cadences, three card types**: a standing
    **watch list** (3–5 opportunistic rows, no setup — the daily fly is the largest untapped
    resource and currently verifies nothing because nothing is assigned to it; the Aug-1 card
    marked A5/G29 "Opportunistic" and had nowhere to put them, and both are still PARTIAL), a
    rolling **local card** every 2–3 days for contrived conditions (the §5 pattern), and a
    dated **event card** weekly (the §4 pattern) — **only the event card needs a date, and it
    inherits one from the event.** Rest of the proposal: the admission rule — **a feature does
    not ship default-ON or preseeded until it is on a card** (default-OFF *and* unpreseeded
    stays unrestricted, so it gates the risk without gating the building) — and a row
    unassigned **3 weeks** (recalibrated from "3 closed cards", which with three cadences can
    elapse in a week) forces **schedule / accept-unverified / delete**, generalizing the
    pass-or-delete move the fork already makes ad hoc, with `SHIPPED UNVERIFIED (accepted)` as
    the new sayable state that stops the backlog being a guilt pile. Enforced on the two
    surfaces the repo already maintains: three lines in the **session-start hook** (watch list
    · event card + local queue · unassigned + aged-out) and a **CI test** on the
    features.py-registry precedent. **The backlog is tractable, not permanent** — ≈15–25
    rows/week at the flown card yields (June 9–12, Aug 5 twenty) ⇒ **3–5 weeks** for the 67
    untested+partial, minus a tail whose conditions never arise. Explicitly does NOT fix: the
    4 REGRESSED rows (bugs, not unverified) or silent no-ops. **2 open calls** (seeding
    grouping; whether `SHIPPED UNVERIFIED (accepted)` should exist at all). Build order starts
    with `WATCH.md` — one short file, no decision needed, pays out on the next flight),
    `414th-wing-growth-notes.md` (**The Wing Grows** — scheduled squadron arrivals, split out
    of the SP-loop note's §S3 reason 5b at the DM's request because it is a real feature, not
    a read-out: a campaign-authored `available_from_turn:` (+ optional `arrival_note:`) on a
    squadron block, so **new airframe types** land mid-campaign on a schedule the player sees
    coming ("F-14 det turn 4, Prowlers turn 6"). Hits two of the three SP-diagnosis factors —
    it converts the DM's own variety motivator into the forward hook, and it **inverts "turn 1
    is the best mission by construction"** by giving the campaign an upward slope. **The build
    is smaller than expected, and the reason is `ControlPoint.squadrons` being a DERIVED
    property** (it filters `air_wing.iter_squadrons()` on `squadron.location`), so there is no
    base→squadron list to maintain: the moment a squadron joins the wing it appears at its
    base, `best_squadrons_for` sees it, and **the planner needs no change at all**. Likewise
    `AirWing.reset()`/`populate_for_turn_0()`/`end_turn()` all walk `iter_squadrons()`, so a
    pending squadron is untouched for free. Shape: build the Squadron at turn 0 exactly as
    today (reusing preset pick / §23 country pin / def claiming — one construction path, and
    a deterministic schedule) but hold it in a pending list instead of `add_squadron`, then
    promote + populate it in `Coalition.initialize_turn` (`Squadron.populate_for_turn_0` is
    already generic despite its name — worth renaming). Announcement is BOTH halves: the
    schedule shown **ahead** (greyed on the SP board's step 1 + the S3 anticipation band —
    the jet you can't fly yet is the advert) and the event on the turn via a new `Sitrep`
    `arrivals` field, which buys kneeboard + web LAST TURN + Qt debrief at once. Edge cases
    owed answers: **parking** (an arrival base full since turn 0 clamps SILENTLY today — a
    regression in spirit vs the standing parking-fit invariant), a lost/enemy-held arrival
    base, def claiming, save compat (new pending state, `__setstate__` empty default, campaign
    edits need a NEW game), the Air Wing Config dialog, and `squadrons_start_full`
    interaction. 6 open calls incl. visible-vs-surprise, red schedules (code symmetric, never
    announced as fact), and `available_until_turn` departures as the use-it-or-lose-it v2.
    **First campaigns picked 2026-08-03: Red Tide + Baltic Fury** — with the note's key
    distinction that **additive** arrivals (new squadrons appear later; total force grows)
    do NOT invert "turn 1 is the best mission", only **deferred** ones do (existing turn-1
    squadrons held back; turn 1 deliberately weaker) — which makes the motivationally
    correct flavour also a real balance change to an already-tuned campaign. **Red Tide's feature
    lock was LIFTED 2026-08-03** (DM: "not existent"), so its schedule needs no override —
    but it remains the weaker candidate on merits (its Frankfurt wing already fields nine
    fixed-wing types on turn 1, so variety isn't what it lacks) and, as a shipped balanced
    build, a deferred schedule there still owes a playtest. **ORDERING PRINCIPLE (DM call 2026-08-03): the schedule IS the air
    campaign — SEAD/DEAD before strike.** Turn 1 = the door-kickers (air superiority,
    SEAD/DEAD, and the enablers — AEW&C/tankers/ISR); later = the exploiters (strike, deep
    interdiction, heavy bombers). Strictly better than the note's first draft on three
    counts: arrivals feel **earned** (the B-1B on turn 7 is the consequence of six turns of
    killing SAMs — the campaign teaches its own doctrine); it **fixes** the balance risk
    instead of creating one (the first draft deferred the Gripen DEAD *against the belt* —
    the scary deferral; deferring **strike** is safe by construction, since the early
    campaign genuinely cannot use deep strike yet); and it settles additive-vs-deferred as
    **deferred, with the right things deferred**. **Corollary: the arc depends on whether the
    campaign opens offensively or defensively** — SEAD-then-strike is the *offensive* shape,
    a back-foot campaign runs **hold → stabilise → counter-attack**; the two picked campaigns
    are one of each. **Baltic Fury (offensive, the clean pilot)**: no lock, and accession
    order and doctrinal order *agree* — T1 F-22A/F/A-18E TARCAP + EA-18G + every enabler +
    the Hamburg CAS/rotary set (the land battle runs from turn 1); T3 **HavLLv 31** Finnish
    F/A-18C BARCAP (first accession; closes blue's real hole — ZERO blue BARCAP squadrons vs
    red's six; full-fidelity module ⇒ a flyable seat); T5 **F 17 Blekinge Wing** Gripen DEAD
    (rollback opens; T1–4 deliberately Growler-thin — that's the pressure, not a gap); T7
    **F-15E + F/A-18F Strike Rhinos**; T9 **34th BS B-1B** (deep strike last). Residual A/G
    during T1–6 is deliberate and sufficient (F/A-18E `secondary: air-to-ground` + the
    A-10C/Apache set) — the player lacks *deep* strike, not bombs. **Red Tide (defensive,
    contingent on the override)**: the Fulda Gap has no door to kick, so the arc is hold →
    stabilise → counter-attack and **CAS cannot be deferred** — T1 the air-superiority trio +
    F-16CM DEAD + F/A-18C SEAD + enablers + A-10C + the whole Fulda rotary hub; T4 Mirage
    F1EE; T6 F-15E BAI (counter-attack opens); T8 B-52H. Sequencing: build the feature
    unauthored, author Baltic Fury and fly it, THEN decide on the override),
    `414th-single-player-loop-notes.md` (**SP Pilot Mode** — why SP campaigns die after turn 1
    while the 414th's MP campaigns finish: in MP you play a *pilot*, in SP you play the DM
    **and** the pilot, and the DM job has no fun in it. The stop point is reproducibly "accept
    results → now plan turn 2", compounded by turn 1 being the best mission by construction, a
    new campaign being cheaper than the next turn, and the §29 SITREP explaining why turn 2
    matters only *after* you commit to turn 2. Scopes an additive express lane in four stages
    — S1 "Accept results & fly next" (chains the existing `process_debriefing` →
    `pass_turn` → generate path), S2 the **aircraft-first two-step board**, S3 the pre-turn
    hook card (§21 MIA capture clocks, §75 victory progress, the COIN fuses/windows — all
    already-tracked state, pulled *ahead* of the commitment), S4 the guardrails.
    **DM spec 2026-08-03 — "I like to fly a lot of different aircraft":** the **airframe is
    the primary axis**, chosen FIRST (the whole wing, not filtered by what the commander
    fragged), and the package options are picked underneath it — a flat sortie list would
    keep offering the same three Hornet sorties. That ordering **settles open call #1**
    (offer-only vs. frag-for-you) as **both, laddered**: seat an existing flight of that type
    → **join an existing package** (the headline rung — it stays inside the commander's plan)
    → a standalone sortie (**explicit opt-in only**, never silently generated; the only
    planner-touching rung; rungs 1–2 are a defensible v1). **DM spec, same day — "I would
    like to be put into existing packages, should still be escort, strike, jamming, whatever
    the planner decides":** two independent variety axes — the player picks the **airframe**,
    the **air war picks the role** — so step 2 leads with role+package (never filtered to one
    task family) and rung 3 is demoted to a surfaced last resort. Rung 2 turns out to be
    cheap — **but not for the reason first written; corrected 2026-08-03 on a DM challenge
    ("these feel like they might need a major rework?") by reading both paths end to end.**
    `ProposedFlight.preferred_type` **holds** (`PackageBuilder.plan_flight` →
    `best_squadron_for(preferred_type=…)`; §44 carrier ops is the shipped exerciser) — but it
    builds a NEW package, so it is **rung 3's** mechanism, not rung 2's.
    `check_needed_escorts` was **overstated twice**: it takes a `PackageBuilder`, and
    `PackageBuilder.__init__` **always constructs a fresh `Package`**, so an existing planned
    package cannot be handed to it (its body reads only `package.flights` /
    `primary_flight`, so re-pointing it at `Package` is 1 real + 3 test call sites — small,
    but a change, not "already exists"); and it answers "what is this route **threatened
    by**" pre-escort, NOT "what is still missing" on a finished package. **The rework isn't
    needed because rung 2 shouldn't go through the commander at all** — adding a flight to an
    existing package is already what the ATO UI does on *Add Flight*
    (`QFlightCreator.create_flight` → `PackageModel.add_flight`), i.e. `Flight(package,
    squadron, …)` + `Package.add_flight` + a TOT update. **Corrected rung costs: all three
    rungs need ZERO engine change** (1 = `set_pilot`, 2 = the UI's own add-flight path,
    3 = `plan_mission` + `preferred_type`); the only optional edit is the role *suggestion*
    (re-point `check_needed_escorts` at `Package`, or just infer absent roles from the
    package's existing flights — free). **Call #2
    SETTLED: one seat, AI wingmen, exactly as in MP** (`client_count` stays 1 — no multi-slot
    bookkeeping, same generation path MP already exercises). **DM steer, same day — "I'm
    looking more for reasons to continue, but this is a great start" — settles the note's
    swinging recommendation: S1+S2 are the VEHICLE, S3 is the PAYLOAD.** S3 is now the
    note's centre of gravity, built on the finding that **the fork already computes almost
    every reason it needs and points them the wrong way in time** — `Sitrep` today carries
    `pilots_mia` / `pows_held` / `red_c2_status` / `victory_lines` (named people on clocks,
    proof your bombing changed enemy behaviour, live victory progress) and renders **all of
    it only after the player has committed to the next turn**. The taxonomy, ranked by
    strength × cheapness: (1) **a named person on a clock you caused** — §21's MIA evader,
    depth-weighted capture roll re-run every turn you don't go, with the §21 surge already
    opening the next turn with the rescue airborne; (2) **proof your sortie changed the
    war** — §52 already measurably degrades red planning and already says so; (3) **open
    loops you opened** — un-killed recon contacts, scooted §49 batteries, unburned §79
    decoys; (4) **a visible finish line** — §75 shipped the mechanism and **no campaign
    authors a `victory:` block**, the largest motivational return for zero engine risk;
    (5) **anticipation** — repairs/replenishment are turn-counted and unsurfaced (**accuracy
    caveat: `pending_deliveries` is a ONE-TURN buffer**, `deliver_all` zeroes it at the next
    boundary, so "4 Vipers arrive turn 12" is not representable and aircraft replenishment
    can only announce "next turn"); **(5b) THE WING GROWS** — DM proposal 2026-08-03,
    endorsed: new airframes/squadrons on an **announced schedule** ("F-14 det turn 4",
    "Prowlers turn 6"), which converts the DM's own variety motivator into the campaign's
    forward hook AND inverts the "turn 1 is the best mission" factor. **Premise checked and
    half-corrected:** aircraft replenishment into existing squadrons exists but only delivers
    more of what you already fly; **mid-campaign arrival of new squadrons/types does not
    exist at all** (the `squadrons:` block applies at turn 0, `Squadron` has no activation
    turn — its `arrival` is an unrelated `ControlPoint` property), so this is NEW machinery,
    not a missing announcement — small and additive (a campaign `available_from_turn:`, held
    out of the air wing until then, unset = today's behaviour), **scoped 2026-08-03 into its
    own note** `414th-wing-growth-notes.md`;
    (6) **dread** — §W6 red tempo + §70 COMINT leaks framed as intel estimates; (7) **a
    record that is yours** — the one gap needing new state (`PilotRecord` tracks only
    `missions_flown`, no kills/rescues). Plus the cheap multiplier: **make the S2 choice
    carry consequence** ("cache — slows regeneration", "HVT window closes in 2 turns"), which
    converts picking tonight's jet into deciding what the war does next. Explicitly NOT
    fixed: the structural "1 of 25 packages" problem, whose real lever is **smaller SP ATOs**
    (planner work, its own note). Records what already exists so it isn't rebuilt
    (`AutoAtoBehavior`, `auto_ato_player_missions_asap`, §43/§73 defaults); 7 open squadron
    calls remain; smaller SP ATOs / victory-arc authoring / a pilot career page deferred),
    `414th-ui-redesign-directions.md` (**UI redesign — DECIDED 2026-07-25: 1 → 2**; D1 step 1
    LANDED. The DM dropped **D3** ("useless" — second-screen planning was its whole
    justification), confirmed **D2** as a *requirement* not a nicety ("we need to keep the map
    visual during planning, once the mission starts it's hidden by the game"), and confirmed
    **D1** as its prerequisite. Three calls: palette = **cold dark + cyan-teal accent** (chosen
    because the map already owns amber/orange semantically — suspected activity, FLOT, MIA
    pilots — so chrome must not compete with map meaning; guarded by a test); order = tokens +
    shell first so the inspector is built once on final styling; D2 scope = the
    **flight-planning spine only** (ATO · package · edit flight · squadron), deliberately NOT
    base menus or target intel, which are consult-once screens. **D1 step 1 landed the same
    day**: `qt_ui/theme/tokens.py` (the palette/scale single source + `to_css_variables()` for
    the web client) + `qt_ui/theme/qss.py` (generates the Qt stylesheet — a faithful superset of
    the 711-line hand-written sheet, plus scrollbar handles/radios/sliders/tooltips/status
    bar/splitters/list rows/focus states it never covered), **all 27 FlightType task chips**
    styled (the old sheet had 10, so 17 drew bare), **one toolbar instead of three** (the
    Discord/Github/Ukraine bar is gone; links stay in Help), **one primary action** (`btn-primary`
    had been on Pass Turn + Air Wing + Transfers + Re-roll RED — "primary" meant "is a button";
    now only Take off carries the accent), and the generated theme took **index 1** so existing
    installs pick it up on launch, with the old sheet preserved at index 2 as "DCS World
    (legacy)". Guards in `tests/test_theme_tokens.py`; verified by rendering the real sheet
    against real Qt offscreen (zero parse warnings; caught two radio-button radius defects).
    Owed: an in-app eyeball (B-series), the D1 step-2 sweep, then D2. Original pitch, for the
    record: the
    complete ~90-screen inventory of both halves of the app (36 Qt dialog classes / 439
    editable controls / 22.5k lines Qt + 7k lines React), the seven evidence-backed findings
    (everything is a modal over the map · four competing navigation systems · no hierarchy ·
    `screenfit.py` exists because only 2 of 34 dialogs were screen-aware · hardcoded hex in
    two unrelated palettes · the web client has no layout, only corners + zero media queries ·
    386 lines of CSS still styling the removed §55/§40 features), and **three directions** for
    the DM to react to — **1 "Sortie"** (restyle: one token file generating the Qt QSS + web
    CSS; small/very-low-risk), **2 "Command Deck"** (restructure: kill modality, a persistent
    selection inspector + a six-mode rail; ~9 of 36 dialogs stay modal; staged, no big-bang),
    **3 "Single Surface"** (replatform: React becomes the whole UI, Qt keeps the window — the
    drift the codebase is already on, since the map/ribbon/layers/SITREP are web-side, the
    server already publishes JSON + a WebSocket, and `client/main.js` is an unused Electron
    wrapper; uniquely buys second-monitor/tablet planning; needs the missing *write* API).
    Direction 1 is a prerequisite for both others, and D3 steps 1–3 == D1 + read-only pages,
    so starting there defers the 2-vs-3 call with the token system already paid for. Rendered
    mockups: `414th-ui-redesign-mockups.html` (self-contained, open in a browser). **No code
    changed; nothing is landed until the DM picks.**),
    `414th-dcs-olympus-notes.md` (DCS Olympus live-GM/RTS layer exploration — the
    "what if?" answer: run-alongside compatibility map, GM doctrine = §20/§61 untracked
    event content, Tier 0 recommended as event tooling + the in-game-pass observation
    deck, all code tiers deferred; **Tier 0 green-lit 2026-07-20** — the GM crib sheet +
    the 11-step compatibility pass card live in `docs/dev/414th-olympus-gm-crib.md`,
    owed a flown pass on the private-session server before event use),
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
    stronghold's C1 cache health; the flip's political-will handoff (a `blue_base_lost`-weight
    move via `consume_reinfiltration_flips`) was removed with the will economy in #710,
    leaving the base-flip a pure map/force event; the 4 §8
    squadron calls resolved to the proposed defaults (HOLD_THRESHOLD=4, 2+2 timers,
    one attempt theater-wide, neutral+lost scope). `advance_reinfiltration(game,
    events)` in `coin.py` runs from `finish_turn` right after regen; gated
    `coin_reinfiltration` default OFF, preseeded ON in the campaign. **Engine-forced
    change vs the sketch**: TGO allegiance follows the parent CP's owner, so the red
    cell/cache attach to the **source red stronghold** (positioned near the target via
    `_infiltration_point`) and **reparent to the target on flip** (`_reparent`) — they
    become the new stronghold's militia + first cache. Tests
    `tests/fourteenth/test_coin_reinfiltration.py`; in-game pass = checklist P3) → C2 will feed (removed) → C3
    campaign fork → C4 dispersed cells (C2 was a `WillWeights.red_cache_lost` cache-loss feed in
    `political_will.py`, removed with the will economy in #710; **C3 LANDED
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
    within `FUSE_TURNS` (3) or they detonate — the device despawns and coalition casualties
    are announced. `advance_roadside_ieds`
    from `finish_turn` after C1/C1.5; `MAX_ACTIVE_IEDS` (2) on distinct roads, placed on
    the road-waypoint nearest the front via the §35 picker pattern, attached to the
    forward red stronghold (allegiance); reuses the shared `coin.spawn_red_ground_at`
    (refactored out of the C1.5 spawn) + `_tgo_by_id`/`_despawn`. (A detonation once drained a
    `WillWeights.blue_ied_detonation` mandate weight via `consume_ied_detonations`; that
    coupling was removed with the will economy in #710.) Gated `coin_ied` default OFF, preseeded
    ON. Tests `tests/fourteenth/test_coin_ied.py`; in-game pass = checklist P4.
    **COIN high-value targets LANDED 2026-07-03** (`game/fourteenth/coin_hvt.py` — the
    fourth COIN direction): a rotating named insurgent leader surfaces near the
    most-contested red stronghold as a recon-fogged 3-unit red TGO, live for
    `HVT_WINDOW_TURNS` (4); killing him inside the window eliminates the leader (announced),
    letting it close is a free miss. `advance_hvt` from `finish_turn` after C1/C1.5/IED; one
    HVT at a time + `HVT_COOLDOWN_TURNS` (3). (A kill once dropped red momentum via
    `WillWeights.red_hvt_killed` / `consume_hvt_kills`, and a lapsed window fed `red_hvt_escaped`;
    both couplings were removed with the will economy in #710.) **The CDE dilemma is gone with the §40 removal (2026-07-21):** it depended on §40 restricted zones + `count_roe_violations`, both removed. Reuses the shared `coin.spawn_red_ground_at`.
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
    `414th-vietnam-political-will-roe-notes.md` + `414th-will-generalization-notes.md`
    **(both SUPERSEDED/REMOVED 2026-07-21)** — the Vietnam campaign layer's political-will
    economy and its campaign-authorable will profiles; kept only as historical record now that
    the will economy is dropped. **W1 (political will) + W2 (negotiation win/loss ending) + W2b
    (static front) were REMOVED 2026-07-21** (the will-economy drop; do not restore) — the BLUE
    Political Will / RED Regime Resolve meters, the `negotiation_verdict`, the `will:` profiles +
    warship feed, the §48 commitment ceiling, and the §75 victory evaluator's will/negotiation
    absorption all went with them; §21 POWs now always run a turn-countdown clock (never the
    indefinite will-coupled hold). **What survives:** **W5** = the GCI-ambush adaptation
    (`Doctrine.gci_ambush` → late-scramble/close-engage dispatcher tuning + the intercept Lua's
    hit-and-run leash; checklist M5), and **W6, rehomed** = red tempo (design note
    `414th-vietnam-red-tempo-notes.md`, `game/fourteenth/red_tempo.py` — Hanoi answers the
    campaign clock): it reads a **top-level campaign `red_tempo:` schedule** of turn-windows
    (each `{from_turn, name?, trail_surge?, ground_offensive?}`; the window in effect is the last
    whose `from_turn` is reached — last-window-wins) — a `trail_surge` logistics window (bigger,
    more-concurrent trail convoys) and a `ground_offensive` stance pulse (raise-only to
    AGGRESSIVE — pressure on the ground battle, never sweep-captures). Authored on 6 campaigns
    (1968 Yankee Station, Velvet Thunder, Desert Storm, Inherent Resolve, Enduring Resolve, Red
    Flag 81-2); campaigns with no block are untouched; hook = `apply_red_tempo` in
    `initialize_turn` after the coalitions plan; checklist M6,
    `414th-campaign-phases-notes.md`, `414th-campaign-phases-pilot.md`,
    `414th-campaign-phases-all66-draft.md` **(all removed 2026-07-21)** — the §40 campaign-phases
    design + the inference pilot + the all-66 classification draft; kept only as historical record now
    that §40 (the phase classifier, ROE zones, and target-release) is dropped,
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
    `Campaign.matches_era`; **re-plumbed 2026-07-26 onto upstream #908's filter framework** — the era is
    now one more criterion (`QCampaignList.current_era_filter`, set via `set_filters(version, map, era)`
    and checked in `_filter_campaign`) instead of a `setup_content(era=...)` argument, `_set_mode` calls
    the shared `on_filter_changed()` so no control clobbers another's criteria, blank-canvas hides the
    filter group, and the `selectedCampaign` wizard field is dropped (a filtered list could leave it
    pointing at a hidden campaign — `accept()` reads `campaignList.selected_campaign` directly);
    needs an in-app pass) + P3 strike-deadlock fix + P3 tasking whitelist + P3 Alpha
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
- [docs/wiki/](docs/wiki/) — the player/contributor wiki, mirrored to the GitHub wiki by
  `wiki-sync.yml` on every push to `main` (edit pages here, never in the wiki UI). Since
  **2026-07-20** it also carries the **adopted upstream dev-process standards** (user call —
  "adopt their way of doing things"): `Contributing-to-DCS-Retribution` ·
  `Campaign-maintenance` · `Developers-Guide` · `New-aircraft-module-checklist` ·
  `New-terrain-module-checklist` · `Creating-shape-files-in-QGIS-for-map-data` ·
  `Release-process` — plus the **Modding Retribution** set (same day, "modding is the
  important one"): `Motorpools` (§56's authoring reference) · `Modded-Unit-Support` (the
  11-step mod-support guide every fork pack follows), with the wiki's Customization
  section renamed to upstream's "Modding Retribution" and `Layouts` linked to
  `docs/modding/layouts.rst` — each a mirror of the upstream wiki page with **414th:** delta notes
  (Python 3.11, the whole-tree Black + out-of-tree pytest + Lua CI gates, the rolling
  `latest` release vs pinned `-414th` tags, MIST-retired Lua discipline, the two-repo
  fork-PR → upstream-carve flow, and the fork's extra unit-data/campaign checklist items).
  See the Conventions bullet below; when upstream revises a page, refresh the mirror and
  re-check the deltas.
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
work-order plugins. TIC and MooseAtis additionally need their main script loaded **after**
every plugin's config table exists (their init reads `dcsRetribution.plugins.<name>` / MOOSE
at file scope) — an ordering the per-plugin work-order pass can't express. They are `LuaPlugin`
subclasses (`game/plugins/{tic,mooseatis}.py`, registered in `manager.py`'s `_PLUGIN_CLASSES`)
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
   `game/server/tgos/models.py`; checklist G24). **Recon BDA capture — ONE mechanism for both crews (`recon` plugin;
   rebuilt 2026-08-05, replacing the `tars` + `airecon` pair)**. Recon previously ran two unrelated
   implementations of one question: MOOSE `Ops.TARS` event callbacks for the player (an F10 "film"
   menu) and a geometric overflight check for the AI. They could not agree by construction and
   failed differently, which is why "is TARS broken" had no answer. **MOOSE `Ops.TARS` is cut**: all
   it contributed to the campaign was a unit NAME scraped off a `Snapshot` whose schema was never
   confirmed — `snap.name or snap.unitName or snap.UnitName` sat under a comment saying the one-time
   `env.info` dump existed so the schema "can be confirmed in-game", so if all three guesses were
   wrong the player path recorded nothing, silently, while the AI path kept working.
   `populate_recon_lua` (`reconluadata.py`) now emits **every** BLUE recon-capable flight — player
   AND AI, which is load-bearing: with the film menu gone, excluding players would leave a human
   recon sortie confirming nothing at all — and the `recon` plugin watches each, banking the enemy
   ground/ship units near the target into the same `tars_recon_captures` ledger the debrief already
   parses (`debriefing.py`→`tars_reconned_tgos`), so nothing downstream changed. **Recon is
   automatic on overfly** (DM call): fly the profile over the target and it confirms; no menu, no
   film limit. The take is shaped by **sensor** (a TARPS tasking reads wider than a drone's ball),
   by **altitude** (a high fast pass resolves less — full radius to 20,000 ft, degrading to 40 % by
   40,000 ft) and by **cloud cover** from the campaign's own weather, which §47/§67 model and recon
   previously ignored entirely. **Timing is deliberately asymmetric:** the CAPTURE fires on overfly,
   but the CUE is held until the flight LANDS (DM call — you get the read-out when the take is home).
   The capture is NOT gated on landing, because missions routinely end before flights land, so
   gating it on touchdown would silently destroy most recon; a cue is cosmetic, a capture is not.
   A shot-down / aborting flight confirms nothing (one-shot); blue-only. Tests
   `game/missiongenerator/tests/test_reconluadata.py` + `tests/lua/test_recon_runtime.py`; runtime
   needs an in-game pass (checklist G19).
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
   recon package (and the `recon` loop banks its overflight as BDA). Armed recon primary is now a
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
   **JTAC is upstream's, unmodified — the packaged-drone model is STRIPPED (2026-08-05, DM call:
   "G26, 27 need stripped from the build, leave G32 as its default behavior"; the upstream
   behaviour is what is wanted — "it fields an AI drone for each faction over the front line
   period thats it").** There is now exactly ONE JTAC model and no setting governs it:
   `FlotGenerator._generate_front_line_jtac` spawns an **invisible, immortal** `jtac_unit` FAC
   orbiting the FLOT at 5,000 ft on the front line's own laser code (1113 under
   `ctld.fc3LaserCode`), gated on nothing but `faction.has_jtac`, blue-side, defaulting to the
   MQ-9 Reaper when a faction declares no `jtac_unit`. **Verified against `upstream/dev`
   line-by-line:** the fork's extracted method is behaviourally identical to upstream's inline
   `# Add JTAC` block — same gate, same blue-only scope, same `str(code)` / `Player.BLUE` /
   `callsign_for_support_unit`, and the `position` it recomputes is the *same*
   `FrontLineConflictDescription.frontline_position` call upstream reads from the enclosing
   scope. **One deliberate divergence, kept:** upstream records `player_frontline_groups`
   *inside* its `has_jtac` block, so a blue side with no JTAC reports no frontline groups at all;
   the fork does it unconditionally. That is an upstream bug, it is not JTAC behaviour, and it
   must NOT be "restored". What was removed: the `coin_packaged_jtac_drone` +
   `auto_jtac_drone` settings, `game/fourteenth/jtac_drone.py`
   (`ensure_jtac_drone_squadron`), `AircraftGenerator._maybe_configure_jtac` +
   `_JTAC_PACKAGE_PRIMARIES`, the `Coalition.configure_default_air_wing` hook, both COIN
   campaign preseeds, and the two test files. Removed settings are save-safe — an old save's
   keys land as dead `__dict__` entries via `deserialize_state_dict`, the §20/§55 precedent.
   Replacement coverage in `tests/missiongenerator/test_front_line_jtac.py` (the FAC had NO
   test of its own before this — the deleted files only ever covered the drone side and the
   exclusion between them); checklist **G32**, with G26/G27 retired.
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
   checklist C9. **Convoy runway spawns (2026-08-02, the flown Baltic Fury "why are units
   generating on the runway"):** a convoy spawns at `Convoy.route_start` = the authored supply
   route's waypoint 0, and an `Airfield` CP's `position` **IS** the DCS airfield reference point
   — the same point pydcs uses for a `StartType.Runway` spawn — so a route anchored on the CP
   coordinate parks the whole convoy on the runway (flown miz: 3 vehicles 0.3 m from Bremen's
   reference, 3 more 0.4 m from Nordholz's). The intended de-stack — miz-authored cp-convoy
   spawn markers (`M1043_HMMWV_Armament` → `_construct_cp_spawnpoints`) — is used by **0 of 72**
   campaigns, so every unit piles onto waypoint 0. `ConvoyGenerator.spawn_position` now walks
   the spawn along the **authored corridor** to the first on-land point ≥ 1500 m from the field
   (`AIRFIELD_SPAWN_CLEARANCE_M`), bounded by `MAX_SPAWN_WALK_M` (5 km); no runway / already
   clear / an authored spawn chain / no clear ground in budget all degrade to today's behaviour.
   Generation-time ⇒ **existing saves fix themselves on the next regeneration, no NEW game**
   (headless-verified on the flown save: 0.3 m → 1503 m). Upstream-shared (upstream's miz-drawn
   `front_line_path_groups` share the pattern); carve candidate. Campaign-data half: Baltic
   Fury's 3 ammo depots authored at 0 m from the Hamburg/Peenemünde/Szczecin references moved
   1.5 km off, CI-locked by `test_no_preset_marker_sits_on_a_runway`; its Peenemünde supply
   routes cross open water and still need a road re-trace (see the campaign note). Tests
   `tests/missiongenerator/test_convoy_spawn_clearance.py`. **Support flights sharing one
   radio channel (2026-08-02, the flown "I can't talk to the A-6 tanker"):** an
   AEWC/REFUELING/RECOVERY flight inherits its **package** frequency, which is correct while
   it is the only support flight in that package (the theater tanker/AEW&C packages) — but
   **§44 long-range carrier ops puts a buddy tanker AND an E-2 in as primary flights of the
   same package**, so both took the one channel (flown miz: `Milestone 8` and `Wizard 7` both
   on 396.0 AM). DCS builds the comms menu per frequency, so only the AEW&C answered and the
   tanker was unreachable; the theater KC-135, on its own package channel, worked fine.
   `setup_radios` now routes the inherited channel through `dedicated_support_frequency`,
   which allocates a fresh UHF when another tanker/AEW&C already holds it (`support_frequencies`
   reads the `MissionData.tankers`/`awacs` registrations — both classes, both coalitions). The
   **first** support flight in a package keeps the package frequency (no channel wasted in the
   common case), and an **explicitly assigned** `Flight.frequency` is honored as-is. Same §74
   DTC symptom: COMM2 channels 3/4/5 all resolved to 396.0 under the AEW&C's name.
   Generation-time ⇒ **existing saves fix themselves on the next regeneration, no NEW game.**
   Upstream-shared (`setup_radios` is upstream code; only the §44 package shape that exposes it
   is fork-side); carve candidate. Tests
   `tests/missiongenerator/aircraft/test_flightgroupconfigurator.py`.
   **"Mission cannot be saved due to errors" — locked speed on the second of two adjacent
   TOTs (2026-08-03, the recurring generated-mission rejection):** DCS refused a generated
   Marianas turn-2 miz with *"All waypoints (2-2) have locked speed and surrounded by
   waypoints 1 and 2 with locked time!"*. The rule is `verifyRouteSeg_` in DCS's own
   `MissionEditor/modules/me_route.lua` — walking the route TOT to TOT, each segment bounded
   by two ETA-locked waypoints needs one **speed-unlocked** waypoint in `(from, to]`,
   **inclusive of the closing waypoint**, so two *adjacent* ETA-locked waypoints are rejected
   when the second is also speed-locked.
   `WaypointGenerator._resolve_locked_speed_time_conflicts` modelled the span as strictly
   interior (unlocking only waypoints with an ETA-locked neighbour on **both** sides), so the
   adjacent case was invisible. The trigger is `set_waypoint_tot` speed-locking a waypoint
   whose ETA clamps to 0: an **air-started** flight whose next TOT has already elapsed gets an
   ETA-0 spawn point (`ensure_in_flight_route_has_locked_time`) immediately followed by an
   ETA-0 TOT waypoint, both speed-locked — which is why it recurs (it needs only a
   regeneration after the sim has advanced past a racetrack/JOIN TOT). The resolver is now a
   faithful port of the DCS rule; times are never touched (they sync the package, and late
   activation requires the first waypoint's TOT). The `_route_is_dcs_legal` test helper
   carried the same wrong model and is now a port of `verifyRoute`. Proven by replaying the
   §66-archived rejected route through the new resolver (rejected → legal). Tests
   `tests/missiongenerator/aircraft/test_waypointgenerator.py`. Generation-time ⇒ **existing
   saves fix themselves on the next regeneration.** Upstream-shared; carve candidate.
9. **TIC — Troops In Contact** — scripted frontline firefights with per-stance movement +
   414th ambient-fire extension (plugin, default ON).
10. **CurrentHill Iran assets pack** — Shahed-136, IRGCN FAC, `[CH] Iran 2020` faction.
11. **Native DCS DTC cartridge export** — RETIRED (2026-06-26): half-baked; never
    pre-loaded reliably and ED is shipping native DTC. Do not restore the OLD
    implementation — **superseded by §74** (ED's native cartridge shipped; the
    rebuilt-from-scratch export shares nothing with this one). (§11)
12. **Recon engine** — the `recon` plugin: one geometric capture rule for player AND AI recon,
    sensor/altitude/weather-shaped, feeding confirmed BDA (default ON). MOOSE `Ops.TARS` was cut
    2026-08-05; see §3.
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
    hold is **always a 4-turn countdown clock** (since the 2026-07-21 will-economy removal there is no
    longer an indefinite will-coupled hold), with a **Homecoming**
    (`resolve_pows_at_game_end` from `process_win_loss`) that repatriates all held blue POWs on a
    win and writes them off on a loss. Every write-off routes through `_write_off`,
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
    flag, then the client re-pulls `/game`. Never persisted; defaults off. **Display-only by
    contract, now enforced at generation** (2026-07-19 flown finding: a §74 DTC cartridge baked
    40 exact SAM rings on an unscouted turn because the DM generated with the reveal ticked —
    the same latent leak existed for the threat-intel kneeboard): `MissionGenerator.generate_miz`
    runs inside `fogofwar.fog_intact()`, so generated artifacts always see the real fog and the
    toggle is restored after; `tests/test_fog_reveal_generation_leak.py`
    (`game/theater/fogofwar.py`, `game/server/fogofwar/`; features doc §3).
19. **Unified map layers panel** — one custom, dark-themed Leaflet control
    (`client/src/components/maplayers/MapLayersControl.tsx`) replacing both stock layer controls:
    collapsible grouped sections (advanced groups start collapsed), preset views (Default / SEAD /
    Recon / Clean), and choices persisted to the campaign save (localStorage-cached), except the
    transient fog overview (`GET`/`PUT /game/map-layers` → `Game.client_map_layers`). The
    old top-left threat-zone/navmesh/terrain control is folded in; side-effect toggles run via
    `useEffect`, not Leaflet add/remove. Client-only; needs the CI client rebuild (features doc §18).
    **Air-defense class rows are FILTERS of the "Air defences" master, not layers (reworked
    2026-07-29)** — off a flown report that read as a §3 fog bug ("with reveal fog of war on, SAM
    sites show nothing at the actual location, just a blank circle you can only find by hovering").
    The five rows were *independent* `TgosLayer`s, so two states were reachable that both look like
    defects: **master off + rows off ⇒ no air-defense marker at all** while *Enemy SAM threat range*
    (a separate layer over the same TGO slice) kept drawing the rings — a ring anchored to nothing,
    which is exactly what was reported (the campaign save carried `airDefenses: false` with all four
    rows false, silently undrawing 54 AD sites **and** 25 §3 concealed "suspected activity" circles;
    recon fog + the reveal overview were both verified CORRECT headlessly — reveal nulls
    `uncertainty_radius_m`, populates threat ranges/units, and surfaces the hidden command posts) —
    and **master on + a row on ⇒ two stacked identical markers**. Now: master off ⇒ no AD icons +
    the four rows grey out (`RowDef.enabledWhen` / `.ml-row-disabled`, the §28 `enabled_when`
    convention in the map panel); master on with no row ticked ⇒ every class; with rows ticked ⇒ only
    those; `normalizeAirDefenseFilters` flips the master on for a stored blob that ticked a class row
    while the master was off (no map goes empty on upgrade). `TgosLayer` took `tasks?: string[]`
    (was `task?: string`) and now checks **category first, task second, both required** — the old
    filter returned on the task check alone, so a task-less TGO fell through to the category check
    (one task-less `aa` site drew a duplicate marker in all four class layers) and a task match never
    had its category enforced; `task` serializes as `[name, role]` (tuple-valued `GroupTask` enum),
    hence `task[0]`. Tests `client/src/components/tgoslayer/TgosLayer.test.tsx`; needs the CI client
    rebuild.
20. **Drop-spawn: map right-click unit placement** — REMOVED (2026-08-02): the map
    right-click unit-placement cheat is fully ripped out — `game/theater/unitplacement.py`,
    the `QPlaceUnitGroupDialog`, the `MapContextMenu.tsx` handler, the
    `POST /qt/place-unit-group` + `DELETE /tgos/{id}` routes, the `enable_unit_placement` /
    `enable_free_unit_placement` cheat settings, and the `user_placed`/`respawn_enabled`/
    `pending_deploy` TGO fields are all gone (the shared SSE `delete_tgo` plumbing stays for
    COIN). Do not restore.
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
    unit-tested (`tests/squadrons/test_pilotnames.py`). **Surfaced 2026-07-20** (the flown Desert
    Storm finding — Israeli/Greek-voiced F-16s wearing the 23rd TFS name, because an airframe-name
    squadron pick is a `random.choice` across every nation's presets under a CJTF faction; also
    the upstream Discord ask): campaign yamls can pin `country:` per squadron block
    (`SquadronConfig.country` — the pick then accepts only same-nation presets, falling through to
    the def generator, and `override_squadron_defaults` stamps the pinned nation; unpinned configs
    byte-identical, an unpinned squadron keeps the picked def's own country; an unknown `country:`
    name **aborts New Game** with a clear error — `resolve_config_country` raises), and the Air Wing
    Configuration dialog gained a **Country selector** under Livery (live-write like the livery
    selector, **full DCS country list**; preset dropdowns show each preset's nation; Save/Load Config
    round-trips the country; fixed in passing — after Replace-with-preset the livery selector wrote to
    the discarded squadron). **Trimmed 2026-07-31 to the upstream #896 maintainer request** (Druss99
    request-changes — the curated per-airframe operator tables were "a massive burden when adding a
    new aircraft module"): `game/dcs/operatorcountries.py` and the operator-derived unpinned-CJTF
    default were **removed** (both fork and carve), the selector shows the full list, and unknown
    countries abort — reducing §896 to "allow country specs in the yaml, don't change default
    behavior." Desert Storm pins all 13 US squadrons `country: USA`.
    (`game/missiongenerator/missiongenerator.py`,
    `game/missiongenerator/aircraft/aircraftgenerator.py`, `game/squadrons/pilotnames.py`,
    `game/campaignloader/campaignairwingconfig.py`, `game/campaignloader/defaultsquadronassigner.py`,
    `qt_ui/windows/AirWingConfigurationDialog.py`; features doc §23, checklist I1/I5 + I6 —
    I6 VERIFIED 2026-07-20 by user pass ("896 is flown and good"); upstream draft #896 is
    deliberately HELD as a draft despite the pass — DM call, un-draft only on a fresh explicit
    call.)
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
    **Campaign filter & sort adopted 2026-07-26** (upstream #908, taken over the fork's bespoke era
    plumbing): the Theater page gains a "Filter && Sort Campaigns" group — Version / Map dropdowns
    (built from the loaded campaigns) + a Name/Version/Performance sort — with the "Show incompatible
    campaigns" checkbox folded into it, all routed through one `on_filter_changed()` repopulate path.
    The Vietnam era shell rides it as another criterion (see the Vietnam-retribution note); the
    blank-canvas terrain picker hides the group; the `selectedCampaign` wizard field is gone.
    Needs an in-app pass.
    (`game/settings/settings.py`, `game/settings/difficultypreset.py`,
    `qt_ui/windows/settings/QSettingsWindow.py`, `qt_ui/windows/newgame/`, `qt_ui/uiconstants.py`;
    features doc §28, checklist K1.) **Dependency greying + detail summarisation (2026-07-10, UI
    audit follow-up):** `OptionDescription` gained a keyword-only `enabled_when=(master, value)` (bare
    `"master"` ⇒ `(master, True)`; normalized by `normalize_enabled_when`, threaded through every
    `*_option` factory) — keyword-only so the frozen subclasses' positional fields are undisturbed.
    `AutoSettingsLayout` stores each field's label + greys a child's **control + label** whenever
    `settings.<master> != value` (live per-section wiring + initial state + post-preset refresh); ~21
    pairs wired (the `coin_*`/qra/motorpool/squadron/etc. dependents, incl. the **inverse**
    `default_front_line_stance` ← `("automate_front_line_stance", False)`). The detail
    *summarisation* half (first sentence inline + full text on hover past 150 chars) was
    **REVERTED 2026-07-20** (user call off the §75 victory-knob descriptions — reading a setting
    must not require hovering it): every `detail` renders in full inline again, the summariser is
    deleted, and an authored `tooltip` still shows on hover; the same-day dead-space follow-up
    also dropped the fixed 55-char textwrap — labels word-wrap to the real column width and the
    label column takes all spare width, so descriptions flow across the row. Guard +
    offscreen-Qt greying tests (+ the full-inline-detail guard) in
    `tests/test_settings_dependencies.py`.
    **Surface rework 2026-08-03 ("do you ever feel like the whole settings interface is
    bloated?").** The audit that started it is worth recording because it *changed the plan*:
    a census of all **213** user-visible fields (the §28 reorg's own doc still said 174 — the
    surface had grown 39 fields in ~4 weeks; §81 landed during the change, making it 215)
    found **zero dead fields**, only **2** that
    qualified as "verified feature + default-ON gate, safe to make unconditional", and **41
    fork-added gates on features that have never had an in-game pass**. The conclusion:
    **the settings surface is a mirror of the in-game-pass backlog** (92 outstanding rows) —
    a kill switch on unverified runtime Lua is doing its job, so deleting fields is not the
    lever, and nothing was retired. The split is **121 inherited from upstream @`e9b2387e` /
    92 fork-added**. What shipped instead is three composing surface changes, all in the
    metadata-driven layer (no per-field edits, no behaviour change, no save migration):
    **(1) a filter bar** — a search box matching label + detail + field name across every
    page (all terms must hit, so "carrier deck" narrows), an **"Only changed"** box built on
    the new `Settings.is_default`, per-page match counts on the category list, and a
    **"● SET BY CAMPAIGN" badge** on every field the selected campaign preseeded
    (`Settings.record_campaign_preseeds` / `campaign_preseeded_fields`, recorded by the New
    Game wizard, stored as a plain `__dict__` key so it is carried in the save but is never
    itself a setting). **(2) the `414th Features` page** — the boolean per-feature gates
    (**41**, after §81 landed mid-change and its two joined them) lifted off the
    topical pages into eleven themed sections, on a deliberate mental
    model: **the Features page answers "what is running", the topical pages answer "how it
    behaves"**, so a feature's switch moves and its tuning knobs stay next to their subject.
    The list (`FEATURE_GATE_FIELDS`) is a **literal** in `settings.py` because `game/__init__`
    already imports settings, so importing `game/fourteenth/features.py` would be circular —
    a test pins it to the registry instead (the same registry-plus-test discipline as the
    feature index), and the **Vietnam Ops page keeps its own eight gates** since it is already
    a scoped features page. **(3) basic/advanced disclosure** — `OptionDescription.advanced`
    (keyword-only, like `enabled_when`) plus a per-section "Show N advanced options" link,
    with the bulk classification by one mechanical rule rather than 213 judgment calls:
    **a numeric tuning knob is advanced**; booleans and choices answer "whether/which" and
    stay basic. Two explicit exception lists — the preset-driven economy dials stay basic
    (the preset bar drives them, so the page must not bury them) and four expert/test
    booleans are forced advanced, which is where the **CSAR test toggles**
    (`combat_sar_test_force_capture` / `combat_sar_test_easy_rescue`) went: they were sitting
    in Campaign Management beside real gameplay settings. Air Doctrine reads **48 → 9**
    options by default; the whole surface is **144 basic / 71 advanced**.
    **One real defect fixed along the way:** `enabled_when` greying was wired *per section*,
    which only ever worked because a master and its dependants happened to be declared
    together — moving the gates broke the live re-enable (`motorpool_enabled` on Features,
    `motorpool_spawn_cap` on Campaign Management). The new `SettingsDependencyHub` broadcasts
    a master's change to every registered layout, so greying is now correct across page and
    section boundaries; `dependency_masters()` keeps it to the controls that are actually
    somebody's master. Tests `tests/test_settings_filter.py` (17, driving the real Qt widgets
    offscreen) + the rewritten cross-page case in `tests/test_settings_dependencies.py`;
    `qt_ui` is not CI type-checked, so it needed an in-app eyeball — checklist B46
    (renumbered from a duplicate B40 2026-08-05; §82 owns B40), **VERIFIED 2026-08-05**
    (user app pass).
    Shipped with the **UI-audit bug fixes**: the defeat-shows-
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
    imagery, and the fills rose (lone 0.18→0.25, cluster member 0.12→0.16). The cluster density cloud
    was **stroke-less** at that point (a flown squadron decision — reversed 2026-07-21 below, when it
    proved invisible on satellite) and the hue stays amber (orange would
    collide with the FLOT token). **Generalized same day to the family-wide stroke-signature system**
    (user call — "unique looks for each … area, zone and exact target"): `StrokeSignature`/`mapStrokes`
    (`mapColors.ts`) give every dashed-overlay category a **unique dash pattern + weight** so hue is
    never the only channel — suspected area "6 6" · minefield ticks "2 8" · pilot MIA solid · POW "3 5" — all drawn cased by the
    shared `CasedCircle`/`CasedPolygon`/`CasedCircleMarker` (`components/map/CasedShapes.tsx`) across
    `Tgo.tsx`/`MinefieldsLayer`/`DownedPilotsLayer`, and the **legend renders the
    real signatures** (`StrokeSwatch` mini-SVG previews + taxonomy labels). Exact targets/buildings keep
    their per-type APP-6/SIDC icons (already unique); threat/detection rings deliberately uncased.
    tsc+jest green; needs the CI client rebuild. **Restyled 2026-07-21** (the §40/§53–§55 ROE/economy
    removals freed the red): the lone suspected-activity ring moved to an **amber dash over a
    dark-red casing** with a centered "?" glyph, via a
    new per-signature `casingColor` channel (`suspectedCasing` token) — the §79 decoy zones inherit
    it, so a feint is indistinguishable from a real hidden contact. **Cluster circles bordered
    2026-07-21** (the flown "I can hardly see these zones" finding — the stroke-less density fill
    vanished on satellite imagery): a clustered member now draws the same red-cased amber dash but
    **lighter** (`mapStrokes.suspectedCluster`, weight 2 / casing 4.5 vs the lone 2.5 / 6) so several
    stacked rings don't ring like klaxons, and its fill still stacks into the density gradient
    (0.16→0.18); the lone ring keeps the bolder signature + the "?" glyph.
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
    losses are framed as **"claimed"** to respect the recon-fog model. The SITREP renders as **its
    own "SITREP — Turn N" kneeboard page** (`SitrepPage`, after Support Info — moved off the Mission
    Info page bottom 2026-07-19 when a flown busy-turn deck clipped the POW/MIA list at the page
    edge; the §30 cover that first hosted it stays retired), gated by `sitrep_for_kneeboard`;
    absent on turn 1 / a quiet turn / when the `generate_sitrep_kneeboard` toggle (Kneeboards page,
    default ON) is off. The Mission Info BLUF's SAR if-down drill was rewritten the same day to
    match the real §21 CSAR model (evade toward friendly lines, capture risk climbs with depth,
    rescue tracks your last known position — "get to high ground" was generic survival copy). v1 covers losses/captures/rescues; front movement + SCAR commander capture are
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
    flight index (§27) is a standalone conditional page again; the phase/ROE surfaces were removed with §40 (2026-07-21). Do not restore the cover — new kneeboard info folds into an
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
40. **Campaign phases (inferred arc + planner emphasis)** — REMOVED (2026-07-21): the turn-by-turn
    phase classifier, its BLUE planner emphasis (the offensive-middle reorder), the ROE
    restricted/free-fire zones + target-release, and the campaign-status ribbon + kneeboard phase/ROE
    surfaces are all gone (the ROE-mechanic drop). The shared `PlanNextAction` offensive-order seam
    the classifier drove stays for §52/§67/§68. Do not restore.
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
    this package first; `_nearest_legal_strike_target` picks the nearest alive enemy TGO
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
    the same date and marches on (no jump, no migration). The calendar now advances in step with the turn count. Gated `continuous_campaign_clock` (Campaign Management →
    Campaign clock & weather, **default ON**). Tests `tests/weather/test_continuous_campaign_clock.py`.
    (`game/weather/conditions.py`, `game/game.py`, `game/settings/settings.py`; features doc §47, checklist T1
    — needs an in-game pass.)
48. **Commitment ceiling (will-coupled war budget)** — REMOVED (2026-07-21): the commitment
    ceiling and the entire political-will economy it capped are gone — the BLUE Political Will /
    RED Regime Resolve meters, the negotiation win/loss ending, the campaign will profiles, the
    per-turn will feeds/ledger, and the Vietnam campaign-layer **W1 (political will) + W2
    (negotiation ending) + W2b (static front)** pieces. The Vietnam **W5 GCI ambush** and **W6
    red tempo** survive (W6 lost only its `resolve_regen` lever); §21 POWs now always run a
    turn-countdown clock, never an indefinite will-coupled hold. Do not restore.
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
    `test_fire_window_stays_inside_the_plugin_scoot_margin`. (The re-fly this owed was flown
    the same night — **S2 is VERIFIED**; this prose lagged the checklist row until the
    2026-08-03 settings audit caught the drift.)
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
    `test_site_loops_are_staggered_across_the_interval`.
    **`CH_CJ10` joined the exclusion 2026-08-05 off the flown Marianas evidence** (two missions,
    Tacviews `-190738` + `-203549`): **all 9 launchers of all 3 PLARF sites moved 0.00 km** while
    the drivable vehicles in the same groups (the §85 bowsers, the PGZ-09/PGL-625/LD-3000 SHORAD)
    jittered only 0.05–0.31 km — a group **pinned by an undrivable member**, with the setting and
    plugin both preseeded and routes being pushed the whole time. It reads as the same post-fire
    pin as the Shahed below, but this hardware fires early every mission so "pinned after firing"
    and "never scoots" coincide. **`CH_Shahed136` is deliberately NOT excluded** (its never-fired
    sites drive). Consequence: **Marianas 2027's authored "hunt the launchers" mechanic does not
    exist** — those sites are stationary targets until the campaign fields a drivable launcher
    (checklist S2 caveat + T5). **The flown 39-site Tacview (same day)
    proved the fire-window fix on vanilla hardware** — 13/13 fired Scud_B batteries scooted after
    their volleys (S2's SCUD half closed) — **and found the residual: all 8 fired `CH_Shahed136`
    sites stay pinned post-salvo** (the never-fired ones drive fine; a mod-side post-fire state
    DCS won't drive out of — `resetTask`/alarm-green don't clear it). Mitigation: the plugin
    **gives up** on a group after 2 consecutive dry route pushes (<100 m progress; movement resets
    the count) — a spent battery is left alone (its magazine is empty; the scoot protects *loaded*
    launchers) instead of drawing futile pushes all mission. Tests
    `test_stuck_group_is_given_up_after_dry_pushes` + `test_moving_group_is_never_given_up`.
    **Mobility is a unit-data contract 2026-08-06:** every exclusion so far was recovered from a
    Tacview after the fact, so the verdicts moved into the units' own definitions as
    **`mobile: false`** (`GroundUnitType.mobile` — the §24 `date_gated_properties` / §86
    `gps_jamming` precedent; `hy_launcher`/`Silkworm_SR`/`CH_CJ10` carry it with their flown
    evidence attached) with `IMMOBILE_UNIT_IDS` kept as the fallback for a DCS type with no
    registered yaml and a test pinning the two in lockstep — so the next finding is a data edit,
    not a code change. The give-up log now also **names the unit types**
    (`giving up on <group> [CH_CJ10, CH_SX2190]`), which is what makes the next flown mission
    conclusive: **`CHAP_9K720_HE`/`CHAP_9K720_Cluster`/`CH_IskanderK`/`CH_DF21D`/`CH_YJ12B` have
    never been established either way** (Baltic Fury's Iskander battery is the cheapest test).
    **`v1_launcher` joined the exclusion 2026-08-06 without a Tacview** — a 1944 launch ramp is a
    poured emplacement of exactly the `hy_launcher` shape, and `class: Missile` puts it in this
    emitter's category with the setting defaulting ON, so it was a latent ANTIFREEZE waiting for
    the first WWII campaign to author a missile marker (none does today). Note the Iskander-M is
    tested as **`CHAP_9K720_*`**: `CH_IskanderM.yaml` is a **tombstone that no longer registers**
    (ED integrated the CurrentHill system into base DCS under the `CHAP_` ids), and three factions
    still carry its dead display name alongside the live pair.
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
    old `plan_convoy_escort` auto-frag is **deleted**. **The spring is authored as NATIVE DCS TRIGGERS at
    generation — there is no plugin** (`game/missiongenerator/convoyambushgenerator.py`
    `ConvoyAmbushGenerator`, run after `ConvoyGenerator` so both the teams and the convoy exist as real
    groups): each team is dug in with `OptAlarmState` green + `OptROE` weapons-hold on waypoint 0 (the
    `set_ship_engagement` idiom), a **hidden** `TriggerZoneCircular` (6 km) sits on the ambush point, and one
    `TriggerOnce` conditioned on `TimeAfter`(120 s grace) **AND** `PartOfGroupInZone(convoy_group, zone)` —
    the convoy's OWN group, never the coalition, so an overflying player can't spring it — raises a
    per-ambush user flag (`ambush-<tgo id>`) and fires the "TROOPS IN CONTACT" `MessageToCoalition` +
    `MarkToCoalition`; two flag-gated `ControlledTask`s on the same waypoint flip the team to
    alarm-red/weapons-free (`start_if_user_flag`, the mirror of the flown escort-split
    `stop_if_user_flag`). A team its convoy never reaches **stays dug in and silent** (the max-hold "spring
    anyway" fallback is removed — it would telegraph a fight nobody drove into). **ROE/cue only** — the
    firefight is reconciled in the turn-boundary force model, so a mover shot down is recorded natively (the
    §35/§37/§49 discipline). **Simplified 2026-08-05** (the plugin audit): this was the `convoyambush` Lua
    plugin polling every 15 s and walking every convoy unit — a re-implementation of the trigger engine DCS
    already runs, which also carried the §36 trap (an unticked plugin silently killed the setting, hence
    preseeds in 7 campaigns). Authoring it removed **572 lines across 5 files**, all 7 plugin preseeds and
    that failure mode; DCS evaluates the zone continuously instead of every 15 s. Design unchanged (same
    radius, grace, cue, ROE-only discipline); the spring had **never fired in a flown test** (S3: "the spring
    never fired because the convoy never drove"), so nothing working was disturbed. Gated `convoy_ambush` (Mission Generation →
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
    `tests/fourteenth/test_ambient_convoys.py` + `tests/missiongenerator/test_convoyambushgenerator.py`
    (the authored zone/trigger/conditions/actions, per-ambush flags, dug-in options, serialization and every
    guard, driven against a real `dcs.Mission`); features doc §50, checklist S3 + S5 — needs an in-game pass.
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
    POW or the compromise window lapsing ends it — time-boxed off the POW's `captured_turn` so a
    held POW doesn't jam forever). Win the SAR race and
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
    → "Enemy C2 degraded (claimed): 1/3 command posts operational", `c2_status_line`, rides along with the
    other real SITREP news). **Pure turn-model** — no `.miz`/Lua/DCS, symmetric in code (each side reads its
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
53. **War economy** — REMOVED (2026-07-21): the per-base materiel supply loop
    (produce → transport → consume), the `supply_effectiveness` bite on recovery / deployable cap /
    ground-combat, the fuel-readiness air grounding, the SITREP front-supply band, and the client
    supply overlay are all gone. Do not restore.
54. **Munitions availability** — REMOVED (2026-07-21): the scarce-munitions stock economy — the
    per-base per-family munitions stock, the loadout stock-degrade gate, the payload-editor
    grey-out, and the base-card readout — is gone with the §53 war economy. Do not restore.
55. **Red Intent — adaptive enemy posture** — REMOVED (2026-07-21): the RED posture classifier
    (`CONSOLIDATE`/`ATTRITION`/`SURGE`), its four planner seams, the per-front postures, and the
    ribbon + SITREP posture surfaces are all gone — the symmetric teardown of the §40 removal. The
    shared unpredictability + offensive-order seams it stacked on stay for §52/§68. Do not restore.
    (Design note `414th-red-intent-notes.md` bannered removed 2026-07-21.)
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
    supported in Pretense. **The HTN strikes depots too** — upstream's `AttackMotorpools` /
    `PlanMotorpoolAttack` (deferred while it collided with §40/§55, both removed 2026-07-21) came in
    with the 2026-07-19 sync: BAI doctrinal primary, STRIKE fallback, package sized off the live
    reserve pool. **Placement + planning reworked 2026-07-26** (upstream #899/#895, adopted over the
    fork's shape): the authored `Garage_A` marker **is** the depot anchor now (the depot renders
    exactly on it; the old opposite-corner `_DEPOT_OFFSET_M` is gone) and the **vehicle grid** moves
    clear instead at `_GRID_OFFSET_M` 45.72 m (150 ft) in the building's local +x/+y corner, still
    heading-rotated — so a garage lands where the author placed it; `PlanMotorpoolAttack` now bails on
    an **empty reserve pool** (`_rendered_unit_count() <= 0`), which matters here because `base.armor`
    is empty at turn 0 by design, so every authored depot was a guaranteed-empty planner target on the
    opening turns; and the capture-zone warning names the radius in nm. Population is ephemeral, so
    **no save migration** — the next generated mission parks in the new spot. Tests
    `tests/**/test_motorpool_*.py` + `tests/ground_forces/test_reserve_armor.py`
    + `tests/fourteenth/test_red_tide_motorpool.py`; features doc §56, checklist B8 — needs an in-game
    pass (Red Tide, a couple of turns in for red to stock reserve; also confirm the garage lands on
    its authored marker).
57. **Air-droppable minefields (convoy interdiction)** — **⛔ SHELVED 2026-07-30** (user call —
    dropping the mechanic from active use, keeping it available to resume later rather than
    deleting it outright). Not preseeded anywhere (Red Tide's preseed was removed); every gate
    (`air_droppable_minefields`, `auto_plan_minefields`, the `minefields` plugin) defaults OFF, so
    the feature is fully inert in every campaign. **The two settings fields are additionally
    hidden from every settings surface** (`Settings.HIDDEN_FIELDS` in `game/settings/settings.py`,
    excluded from `_user_fields()` — so the Qt Settings dialog and the New Game wizard never show
    them) — found 2026-07-30 when a *personal saved default* from before the shelving (captured
    back when Red Tide's now-removed preseed forced it on) stayed visibly checked once nothing
    masked it. The field/default/save-compat stays (`s.__dict__` deserialization doesn't go
    through `_user_fields()`), so an old save with either True still loads correctly; the checkbox
    is just unreachable. Code, tests, Lua plugin, and client overlay are
    **all still in the tree** — nothing below was deleted. **To resume:** drop the two names from
    `HIDDEN_FIELDS` and re-add them to the `FIELD_LAYOUT` "Battlefield life" section (both in
    `game/settings/settings.py`), then re-add `air_droppable_minefields: true` /
    `auto_plan_minefields: true` / `plugins: {minefields: true}` to a campaign yaml (Red Tide's old
    block, restorable from git history) or flip the setting by hand; the write-up below is
    otherwise unchanged and still describes the live implementation.
    DCS has no mine object, so the 414th
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
    **Auto-plan** (`auto_plan_minefields`, default **OFF**, no longer preseeded anywhere — see the
    shelved banner above): `game/fourteenth/convoy_mining.py` `plan_convoy_mining` (hooked in `plan_missions`
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
    §57, checklist B9 — SHELVED, no in-game pass owed while inactive.)
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
    until flown; NOT preseeded in Red Tide — flip it for the next MP event (the RT lock lifted 2026-08-03; this stayed unpreseeded pending a fly, not because of the lock). Tests
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
    never ships/`map_hidden`; the plugin fires
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
    after any other `_offensive_order` emphasis — soft demotion, nothing removed; rain does not demote).
    **Night is deliberately absent** — no per-airframe night-capability data exists, and
    demoting night CAS would ground an A-10C II alongside an A-1. Gated
    `weather_aware_planning` (Air Doctrine, default **ON** — clear skies are byte-identical).
    Tests `tests/fourteenth/test_weather_planning.py` + the storm case in
    `tests/test_armed_recon_planning.py`; features doc §67, checklist B19 — needs an
    in-game pass.
68. **Adaptive procurement (SAM repair + price-weighted choice)** — the AI economy reads
    the war (`game/fourteenth/adaptive_procurement.py`; `ProcurementAi` was a fixed slider +
    doctrine ratios + `random.choice`, coupled to nothing built since). Two couplings:
    **(1) air-defense site repair** (own gate `auto_repair_air_defenses`, default **OFF**) —
    nothing ever rebuilt a dead SAM, so Rollback was a one-way ratchet; each side's AI now
    repairs ≤ `MAX_AIR_DEFENSE_REPAIRS_PER_TURN` (2) dead units/turn at surviving `aa`/`ewr`
    TGOs at full unit price (the player's base-card repair), degraded sites + radars first,
    with the threat-poly invalidation and wreck-marker cleanup the flip needs; **command
    centers/comms are never repaired** (§51/§52 kills stay permanent); BLUE only auto-spends
    when `automate_runway_repair` delegated repairs, RED always; shows as its own Finances
    row; **(2) price-weighted ground-unit choice** (capability proxy — T-72s over gun trucks,
    still a weighted roll). Gated `adaptive_procurement` (Campaign Management → Commander
    economy, default **ON**); NOT preseeded (pending a fly; the Red Tide lock lifted 2026-08-03). Tests
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
    (net silent) ⇒ nothing; **Tier 1** (net up) ⇒ the ambient take (net-up presence only — the §55 posture-detail earn is gone with §55's removal); **Tier 2** (a blue collector — a §2 JAMMING
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
    spot on the dial every mission; GUARD's slot skipped, collisions probed in sorted-name
    order) and the
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
    convention).
    **BAND DISCIPLINE 2026-08-02** (the flown "COMINT is bleeding into mission
    frequencies" report) — two landed assumptions were wrong. **(1) "x.500 cannot collide
    by construction" was false**: only the *inter-flight* `BLUFOR_UHF` allocator steps a
    whole MHz; per-flight aircraft radios (`alloc_for_radio`, e.g. AN/ARC-164 225–400),
    field ATC, and ATIS all allocate on the **25 kHz** grid, where x.500 is an ordinary
    slot — the late-running exact-match probe still let a net key up **one detent** off a
    briefed channel, and let anything allocated after the plan (ATIS) park beside a
    carrier. Now a candidate must clear `NET_GUARD_HZ` (100 kHz) against **every**
    allocated frequency in the band — compared by **hertz, modulation-blind**, since
    `RadioFrequency` equality includes modulation but a pilot's dial does not — and
    `_reserve_guard_band` then reserves the carrier **plus every 25 kHz detent in the
    band**, closing it to every later allocator. **The half-MHz offset is cosmetic; the
    guard band is the guarantee.** **(2) Every comms-active object transmitting does not
    scale**: it is the right *source* set for the take, but as a *transmitter* list a
    KARI-style IADS (DS91 relays at every red base) or a COIN laydown puts dozens of
    carriers across 225–400. New `red_net_max_stations` (Mission Generation → Comms war,
    default **3**, min 1/max 12, `enabled_when=red_comms_net`) caps who is on the air;
    `_stations_on_the_air` picks by **range to the nearest blue CP** (name tie-break; no
    blue position ⇒ name order) with **one slot anchored per kind**, so a crowd of near
    cells can't push the fixed C2 net off the dial or vice versa, and emits name-sorted so
    frequencies don't shift with the anchors. Tests
    `tests/fourteenth/test_comint.py` +
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
    and crew**: tow tractors / P-25 crash truck / Hyster forklift / crane / deck hands in
    the **island street** (the clear staging strip alongside the island) + the 4-figure LSO
    platform team — placements **from the OCN 2 campaign's 13 missions** (Sedlo's deck
    dressing, extracted from the linked statics in the miz files), rotating between 6
    curated street variants per (carrier, turn) crc32 seed. OCN's raw offsets put the cluster
    on the angled-deck foul-line strip (rejected 2026-07-21); that fix shoved it +30 m
    **forward** into the corral, but the forward corral overshot — the flown call
    (2026-07-27) "generating in the **red** instead of the **blue**" pulled it back aft +
    tucked outboard against the island via `CORRAL_SHIFT (+30,−6)→(+9,−1)` (~10 m aft of
    raw / ~5 m outboard; clear of every spot by ≥12 m, min 12.7 m at the six-pack row;
    `ISLAND_STREET_ENVELOPE`→`(−65,−30,10,25)`). **The hard constraint is parking — and
    no static may stand ON a spot, ever**: the SC manual's "blocked spot is skipped" claim
    was FALSIFIED in the first flown mission for late-activated groups (Retribution's
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
    round-down E-2C (M8/M1 positions) standing ONLY during the launch cycle (a **port
    junk row** was tried alongside it and **removed** — flown CVN-71 2026-07-21: it sat
    in the port-quarter *parking* row, not the corridor, and clipped a Hornet on the
    newly-measured spot at (−108,−34); the launch-phase invariant is now "must fall
    inside `LANDING_AREA_KEEP_OUT`", replacing the looser aft-of-x rule) (the arc:
    shipped static → the user's
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
74. **Native DTC data pre-population (F/A-18C + F-16C + CJS Super Hornets)** — the jet starts with the mission
    already in the avionics, via **DCS's native Data Transfer Cartridge** (the mechanism
    reverse-confirmed from a hand-built MP mission flown 2026-07-18 that pre-loaded the DM's
    Hornet with zero pilot action; supersedes the retired §11, whose revisit condition —
    "ED's native cartridge ships" — this is). Each **blue client** Hornet/Viper flight gets
    one JSON cartridge at `DTC/<name>.dtc` in the miz + the per-unit
    `DTC = {Cartridges={{default,name}}, AutoLoad=true}` block, so it loads at spawn and
    distributes to MP clients with the mission download. Contents (per flight): COMM1/COMM2
    presets **mirroring the radio allocator's channel numbers** (kneeboard/Radio-table/DTC
    always agree) with ≤5-char names (callsign, MAGIC/ARCO, DEP/ARR/PKG); the flight's
    steerpoints with ASCII-folded names + the route sequence (per-leg alt/speed, ETA as
    seconds-since-midnight, target flagged); Hornet NAV settings **pre-tuning the §65 boat
    TACAN/ICLS/ACLS** (land arrivals get the field TACAN) + FPAS home waypoint; and the
    SA/HSD picture — FLOT (the F10 drawing's own geometry), **friendly CAP stations + tanker/AEW&C orbits as CAP_PTS racetracks** (Viper:
    named extra steerpoints), and **enemy SAM rings as MEZ/THREAT_PTS** ("Custom" type,
    NATO short labels from DCS unit ids) — **recon-fogged via `known_for(flight.friendly)`**
    (the threat-intel kneeboard's leaf; `map_hidden` never emitted): headless-verified 0
    rings on un-scouted Red Tide turn 1 vs exactly the 5 TARPS-confirmed sites on the flown
    turn-2 save. Schemas + limits mined from the ME's own DTC editor
    (`CoreMods/aircraft/<type>/DTC` + `me_managerDTC.lua`; design note
    `414th-dtc-cartridge-notes.md` is the format reference): 59/25 waypoints, 9 CAP pts,
    3+3 FAOR/FLOT ×7 pts, 40/15 threat rings, and the load-bearing `Default_*` style
    indices (must be 1, the editor inits them to NONE). pydcs knows neither piece (neither
    org nor root repo, checked): two fork-side seams in `dtc/cartridge.py` — an idempotent
    `FlyingUnit.dict` wrap emitting the unit `DTC` key + a post-save zip append (before the
    §66 archive copy, so archives carry cartridges) — with the clean first-class version
    PR'd to `dcs-retribution/pydcs` (delete the seams when the pin moves). Both hooks
    best-effort: any failure logs and leaves the pre-feature miz. CH-47F + MiG-29 also ship
    DTC descriptors — add builders when a campaign fields them blue-client.
    **CJS Super Hornets added 2026-08-02** (`dtc/superhornet.py`, ids `FA-18E`/`FA-18F`/
    `EA-18G`): the mod ships its own DTC descriptors, and they are **thin wrappers that
    `dofile` ED's own `CoreMods/aircraft/FA-18C/DTC` COMM/WYPT/NAV_SETTINGS
    implementations**, so the Hornet builder's emit is reused verbatim
    (`build_hornet_family_cartridge`, factored out of `hornet.py`; a test pins the two
    sections byte-identical). **No SA section** — the CJS `data` table declares only
    `ALR67`/`COMM`/`WYPT`/`TCN` (no `SA`, no `GPS_WYPT`; `SA` occurs **0** times across all
    three descriptors vs **205** in ED's, the panel list is 5 vs ED's 8 — ED adds `pSA` —
    and the `.dlg` keeps only a hollow `"Panel SA"` stub, 1 reference vs ED's 196: CJS
    forked an ED descriptor and stripped SA out. **That stub is the tripwire** — if a CJS
    release fills it in, flipping `with_sa=True` lights up the whole picture with no other
    change), so these jets get comms + route +
    §65 recovery aids but **no FLOT, CAP racetracks or threat rings**; the three SA switches
    go inert (`with_sa=False`) and an SA-only flight builds **no cartridge**
    (`CartridgeBuilder` is now `Optional`-returning; the generator skips `None`). Tanker
    variants `FA-18ET`/`FA-18FT` are NOT registered (no descriptor ships for them).
    ⚠️ Built against a **mod** descriptor, so it can drift with a CJS release — the mod's own
    `initialize_TACAN()` already `dofile`s a `TCN/TACAN_defs.lua` that no longer exists in
    DCS (lazy + harmless here, since §74 emits `"TCN": []`). Gated
    `dtc_data_cartridges` (Mission Generation → Cockpit data, default **ON**; OFF is
    byte-identical). Tests `tests/missiongenerator/test_dtc.py` (shapes, fog, mirroring,
    the seams, a real miz round-trip through pydcs load). **Planner controls (same day,
    user ask "planners need more control"):** the Edit Flight dialog grows a **DTC tab**
    (supported airframes only) writing `Flight.dtc_options` (`game/ato/dtcoptions.py`,
    pickled + `__setstate__`-defaulted) — a tri-state master (follow campaign / always /
    never, the per-flight override beating the global toggle both ways) + six section
    switches (comms, route, recovery aids, FLOT+zones, friendly orbits, threat rings); an
    off section is omitted from the cartridge entirely so the jet's own defaults stand,
    all-off builds no cartridge, and the choices thread `Flight → FlightData →
    DtcGenerator` (per-flight resolve replaces the global gate). Offscreen widget tests
    `tests/test_dtc_tab.py`.
    (`game/missiongenerator/dtc/`, `game/ato/dtcoptions.py`, `game/ato/flight.py`,
    `qt_ui/windows/mission/flight/QFlightDtcTab.py`, `game/missiongenerator/missiongenerator.py`,
    `game/settings/settings.py`; features doc §74, checklist B28 — needs an in-game pass:
    AutoLoad on the §64 spawn paths (uncontrolled carrier clients, late-activated delayed
    flights) is the genuine unknown — the reference mission's jets were plain ramp starts —
    plus an in-app eyeball of the DTC tab.)
75. **Custom victory conditions** — alternate, legible ends to the war (the 2026-07-19
    Discord ask: Ramius007's victory CPs/domination + Starfire's destroy-the-HVTs /
    strength-below-% / air-denial conditions — the community wants the *shallow* layer,
    not another will economy; design note `414th-victory-conditions-notes.md`). Two tiers
    over one engine (`game/fourteenth/victory.py`): an **authored campaign `victory:`
    block** (a top-level campaign YAML block, the S5 rederive-never-pickle rule +
    `_PROFILE_CACHE`; parse fails loudly) with `win_when`/`lose_when` condition lists —
    `capture_cps` (all named CPs blue) / `lose_cps` (any named CP red) /
    `territory_above|below` / `destroy_targets` (all named TGOs dead) /
    `destroy_categories` (no red TGO of the class alive + a turn-0 baseline count > 0, so
    an absent class can't vacuous-win) / `enemy_air_below` / `enemy_ground_below` /
    `friendly_air_below` (strength vs the campaign-start `VictoryBaseline`, latched
    unconditionally in `initialize_turn`; empty baseline never fires) /
    `enemy_air_denied` (no red CP with an operational runway — red off-map spawns make it
    unreachable by construction) / `min_turn` guard / `label` — and two
    **generic opt-in knobs** usable on any campaign (Campaign Management → Victory
    conditions, both default 0=off): `alternate_victory_domination` +
    `alternate_victory_attrition`, synthesized into the same conditions and stacked with
    an authored block. **The will/supply meter conditions
    (`blue_will_below`/`red_resolve_below`/`enemy_supply_below`/`friendly_supply_below`) +
    the negotiation-verdict absorption were REMOVED 2026-07-21** with the will/war economy;
    only the territorial/destroy/strength/air-denial conditions remain.
    **Semantics**: a victory entry is a
    requirement — EVERY set field must hold (AND within the entry), the lists are OR (any
    fully-met entry ends the war) — which is what makes `min_turn` a guard.
    `victory_verdict` is the **single alternate-endings branch** in `Game.check_win_loss`
    ahead of the stock territory defaults (which remain — alternate endings ADD, never
    replace): it evaluates the authored/knob conditions (loss precedence; a met
    condition announced once via a `game.victory_announced` latch). Ground truth,
    turn-boundary only, zero planner coupling (§17 boundary). Surfaced as a green **VICTORY
    ribbon chip** + a live-value expander checklist ("Any one of these ends the war:" /
    "Defeat if:", `CampaignStatusJs.victory` → `client/src/components/campaignstatus/`)
    and a capped SITREP digest
    (`Sitrep.victory_lines` — kneeboard band, web LAST TURN, Qt debrief, §29 parity).
    No preseeds; no shipped campaign changes behavior. **Carved upstream late
    2026-07-19 as draft #885** (the design-note spec: core minus the will/supply meter
    fields, the negotiation absorption, and the SITREP/ribbon surfaces; ceded to Druss99
    2026-07-20 — drift-watch). Tests `tests/fourteenth/test_victory.py`
    (incl. the real `check_win_loss` branch order, driven
    duck-typed); features doc §75, checklist B29 — needs an in-app pass + the CI
    client rebuild.
76. **CTLD paratroopers (fixed-wing air assault)** — fixed-wing troop transports fly
    Air Assault by **paradrop**, for both the human C-130J-30 and AI transports —
    the "proper support for paradrops" the C-130J yaml TODO'd since the Hercules-mod
    purge (#53) made Air Assault helo-only. **Planner:** the Builder gate is now
    "helo OR troop transport" (`cabin_size > 0`); a fixed-wing flight preloads (no
    pickup zone, the carrier/off-map branch) and its CTLD assault-area waypoint
    becomes a real AI run-in at **1,000 ft AGL** (`only_for_player=False` — the old
    Hercules shape) over the 2,500 m target wpZone; `C-130J-30.yaml` gains
    `Air Assault: 40` (below the helos' 50 — a helo in range still wins the tasking,
    the C-130 takes the long-reach/no-helo cases; campaign C-130J squadrons are
    near-universally `secondary: any`, so NEW games auto-plan it). **Runtime**
    (`ctld-config.lua` — the config layer, CTLD.lua untouched): the emitter marks
    paradrop-capable types (fixed-wing + cabin, Python-side); the stock F10
    **"Unload / Extract Troops" IS the jump command** while airborne (the
    `unloadExtractTroops` wrap — grounded unload/extraction/helos fall through to
    stock byte-identically; player jump ceiling 3,000 ft AGL, AI exempt); the stick
    leaves the aircraft immediately and the troop group ground-spawns at the
    velocity-projected drop point after a real **descent delay** (AGL ÷ 6.5 m/s,
    cap 90 s) — a transport killed after the drop still delivers, one killed before
    never does; landing reuses CTLD's own bookkeeping (wpZone march-to-centre = the
    existing assault capture behavior, JTAC stick, dropped ledgers) so **no phantom
    spawns** (the troops are the aircraft's CTLD cargo, losses record natively). An
    AI release loop (5 s) drops one stick per sortie within 1,200 m of the flight's
    own zone centre; `preload_troops` now **retries every 30 s** (~2 h give-up) so
    TOT-delayed late-activated transports stop arriving empty. The C-130J EW
    deny-list (§2) gains TRANSPORT + AIR_ASSAULT so a hauler/paradrop bird never
    grows the EW menu. Deliberately v2: An-26/Il-76 cabins, chute visuals, LAPES.
    Tests `tests/ato/flightplans/test_airassault.py` +
    `tests/lua/test_ctld_paradrop.py` + the extended EW-deconfliction test;
    features doc §76, checklist B30 — needs an in-game pass (the AI run-in profile
    + troops-march-to-capture are DCS-only).
77. **Escort jamming (Growler / Prowler, for all campaigns)** — the "AI can't use it" answer:
    the Timberwolf/Matador EW script family (the C-130 §2 lineage; upstream's `ewrj` gates it
    player-only) gets its missing decision layer. **Escort jamming is flown ONLY by the two
    dedicated ALQ-99 jammers — the EA-18G Growler + EA-6B Prowler** (2026-07-29 user call —
    "only Growlers and Prowlers, no Harriers or anything else with a jammer"; this reverses the
    2026-07-21 graduated-tier experiment). The gate is the `Escort Jammer` task priority in the
    unit yaml, declared ONLY by `EA-18G.yaml` (800) + `EA_6B.yaml` (790), so only they are
    `capable_of(ESCORT_JAMMER)`/auto-assignable. **Removed with the reduction:** the whole
    graduated-tier machinery — `game/data/escort_jamming.py` (`EscortJammerTier`/`TierEffect`),
    the `escort_jammer_tier` field on `AircraftType`, the `escort_jamming_loose` setting, the
    `can_auto_assign` loose gate, and `_has_curated_escort_jammer` — plus the `Escort Jammer`
    task + tier tag on all 14 non-dedicated airframes (Hornet/F-14/F-16/F-4E/AV-8B/A-7E/A-10/
    F-15E/JF-17/M-2000C). No campaign authors the task, so escort jamming appears only where a
    wing fields one of the two mods. **The CJS Super Hornet default stays OFF** (`fa_18efg` +
    `fa18ef_tanker` — the Growler is the DM's opt-in premium jammer, `ModSettings.all_off()`
    keeps mods-off tests honest); the EA-6B Prowler is faction-wired in 9 blue factions
    (`ea6b_prowler`). The `FlightType.ESCORT_JAMMER` role (proposed on the SEAD-escort radar-SAM
    trigger via `EscortType.Jammer`, rides the package join→split, no winchester-RTB — the
    jamming is the payload — SEAD Escort loadout fallback) is blue-only; `can_plan_escort` for
    Jammer is now just `air_wing_can_plan(ESCORT_JAMMER)` + the per-side cap. Runtime:
    `growlerluadata.py` emits `dcsRetribution.growler` (per-jammer group name/side/player flag +
    protected group names; no tier knobs; no jammer → no-op) and the `growler` plugin (default
    ON) drives a **missile-spoof bubble** over the package **+** offensive `WEAPON_HOLD` pulses
    on radar SAMs — **ROE-only** (emissions NEVER toggled; MANTIS alarm/EMCON untouched),
    effectiveness RISES as the jammer closes (deliberately the opposite of the C-130's standoff
    burn-through; never unify them). **The plugin is airframe-agnostic** — it drives whatever
    ESCORT_JAMMER group the emitter names by name + geometry, so **an AI Prowler is driven
    identically to an AI Growler** (there is no EA-18G-specific code path; "make it work with AI
    Prowlers" was already true once a Prowler is emitted). AI jams automatically after a startup
    grace; a player jammer starts OFF with an F10 "Growler jamming" menu. **Balance (a 2-4-ship
    jammer flight × several packages can put many jammers up): effects DON'T stack** — a missile
    faces only the **single strongest bubble** covering it (rolled once, not OR'd per jammer),
    and a suppressed SAM gets a **mandatory `recoverySec` shoot-back window** before ANY jammer
    can re-hold it (jamming is intermittent, never permanently dead). Ship count within a flight
    is already effect-neutral (one bubble per group, from the lead), so the remaining lever is a
    per-side **`max_escort_jammers`** cap (Air Doctrine, default 4, 0=off) enforced in
    `can_plan_escort`. **Dedicated jammers prefer the jammer slot** (2026-07-21): ESCORT_JAMMER
    is **auto-offered to every capable squadron** like TARPS (`SquadronConfig.auto_assignable`),
    so a campaign's dedicated EW jet authored as a SEAD squadron (§717's `primary: SEAD`
    Prowlers) still gains the jammer role with **no per-campaign edit**; and the EA-6B/EA-18G
    **SEAD Escort priority is dropped to 400** (below the strike-fighters' 470/475) so in the
    escort fill (SEAD Escort resolves before Escort Jammer) a Hornet/Viper takes SEAD Escort and
    the dedicated jammer is freed for the Escort Jammer slot (790/800). A lone Prowler with no
    strike-fighter still flies SEAD Escort (400 > the podded jets), and SEAD/DEAD as a **package
    lead** are untouched (620/730), so the Prowler is still a SEAD shooter. Tests
    `tests/fourteenth/test_escort_jammer.py` + `tests/missiongenerator/test_growlerluadata.py` +
    `tests/lua/test_growler_runtime.py` (the harness gained `Weapon:destroy` + ground ROE values;
    the AI-Prowler-pulses-a-SAM case pins airframe-agnosticism; the balance pass keeps the
    non-stacking proof + recovery-window cycle + cap); features doc §77, checklist B31 — needs an
    in-game pass (the hold/restore pulse + non-stacking spoof against a live SAM ring, driven by
    both an AI Growler and an AI Prowler, and that a mass of jammers doesn't flatline the IADS).
78. **Sea-supply convoys + coastal anti-ship engagement** — makes the sea supply
    route (the §-less upstream `CargoShip` lane between two friendly ports with no
    road) a real feature. **Part 1 — convoys with proportional losses**
    (`cargo_ship_convoys`, Mission Generation → Naval strike, default **ON**): a sea
    shipment sails as a **convoy of N cargo ships** instead of one lone hull
    (`game/missiongenerator/cargoshipgenerator.py` `_manifests_for` spreads it ~1 ship
    per `UNITS_PER_SHIP`=2 units, capped by `cargo_ship_convoy_max` default 5 and by
    the unit count — never an empty hull), each hull carrying a **round-robin slice** of
    the cargo. The hull is the loss unit: `unitmap.add_cargo_ship` maps every hull name
    → a `CargoShipUnit(cargo_slice, ship)`, and `commit_cargo_ship_losses` kills **only
    a sunk hull's slice** (`ship.kill_unit` per unit, KeyError-guarded), so sinking k of
    N hulls denies **~k/N** of the reinforcement and the rest still lands — the
    hard-coded single-hull gate (`add_cargo_ship` used to `raise` on >1 unit) is lifted.
    The debrief's `cargo_ships` count now tallies **hulls** sunk; `SideLossCounts` +
    `cargo_ship_losses_by_type` fold across slices. **OFF (or a one-unit shipment) = one
    hull carrying the whole transfer = byte-identical to the legacy all-or-nothing
    loss.** **Part 2 — coastal batteries engage ships** (`coastal_batteries_engage_ships`,
    same section, default **ON**): `CoastalSiteGroundObject` (Silkworm `hy_launcher` et
    al.) is generated **weapons-free + red alarm** (`tgogenerator.set_coastal_engagement`,
    mirroring the ship `set_ship_engagement`) so it fires autonomously on any enemy hull
    in range instead of sitting passive on DCS AUTO (the §63 "AUTO AD ignores it"
    lesson); symmetric, coastal-only, gated so OFF is byte-identical. **The trigger is
    geometry** — a convoy sails a *friendly* lane, so an enemy battery only fires if the
    lane passes within its range of the enemy coast (Tanker War's Praying-Mantis strait
    box is the showcase; author lanes near the opposing shore). No plugin/Lua/save
    change. Tests `tests/fourteenth/test_cargo_ship_convoy.py`; features doc §78,
    checklist B32 — needs an in-game pass (whether a DCS Silkworm on weapons-free
    actually tracks and hits a moving 12-kt cargo ship is the DCS-only unknown; plus
    the convoy visibly running the gauntlet with proportional debrief losses).
79. **Decoy suspected-activity zones** — fake, unitless concealed enemy contacts that render as the
    *exact* §3 "suspected activity" uncertainty circle a real hidden force draws, so the **human**
    mission planner can't tell a feint from a genuine hidden contact without spending recon on it.
    Each decoy is a **unitless concealed `VehicleGroupGroundObject`** carrying a new
    `TheaterGroundObject.is_decoy` flag (`__setstate__`-defaulted for old saves); because it holds
    **zero alive units**, the AI planner — which enumerates targets on ground-truth `is_dead()` —
    skips it automatically, so the deception is **human-only and the AI-immunity is free** (a real
    strike is never wasted on an empty zone). Flying recon onto a decoy (a TARPS overfly or an
    attack) resolves it empty — "no enemy activity … it was a decoy" — and the circle is **burned**
    (removed). "Both" placement model: an **authored budget** (the `decoy_zone_count` setting, or a
    top-level campaign `decoy_zones:` YAML block with `budget:` + optional `near_cps:` placement
    hints) seeds the feints, and a **per-turn refresh** (`advance_decoy_zones` in `game/game.py`
    `finish_turn`, right after the COIN `advance_*` calls) burns the reconned ones and tops the live
    count back to budget — so the player can't memorize which circles are fake. Decoys seed a few km
    off **front-adjacent red control points** (or the authored `near_cps`), on land, under a
    `MAX_DECOY_BUDGET` (12) sanity cap. Pure turn-model — **no plugin, no Lua, no `.miz` change**.
    Gated `decoy_zones` (Difficulty & Realism, default **OFF**,
    `enabled_when=concealed_enemy_forces` — the deception only works when *real* forces are also
    circles, else any circle is obviously a decoy); NOT preseeded in any campaign (opt-in). **Shipped
    with a suspected-circle restyle** (the ROE/economy §40/§53–§55 deletions freed the red): the lone
    "suspected activity" ring now draws an **amber dash over a dark-red casing** with a centered
    **"?" glyph** (a clustered member draws a **lighter** red-cased ring — `mapStrokes.suspectedCluster`,
    no glyph — over the stacking density fill, bordered 2026-07-21 after the flown "I can hardly see
    these zones" finding that the stroke-less fill vanished on satellite), via a new per-signature
    `casingColor` channel in `mapColors.ts` (`suspectedCasing` token) honored by `CasedShapes.tsx` +
    `MapLegend.tsx` and the `Tgo.tsx` glyph — decoys inherit it, so a feint is pixel-identical to a
    real contact. Files: `game/fourteenth/decoy_zones.py`, `game/theater/theatergroundobject.py`
    (the `is_decoy` flag + `__setstate__` default), `game/game.py` (the `finish_turn` hook),
    `game/settings/settings.py` (`decoy_zones` + `decoy_zone_count`), `game/fourteenth/features.py`
    (§79), plus the client restyle (`client/src/theme/mapColors.ts`,
    `client/src/components/map/CasedShapes.tsx`, `client/src/components/legend/MapLegend.tsx`,
    `client/src/components/tgos/Tgo.tsx`). Tests `tests/fourteenth/test_decoy_zones.py` (13);
    features doc §79, checklist B33 — needs an in-game pass.
80. **Mixed-hull ship groups** — a ship group used to put to sea as **N copies of one hull**
    (four identical Arleigh Burkes ringing the carrier), because a layout slot picked ONE unit
    type (`random_dcs_unit_type_for_group`) and `generate_units` stamped it into every position.
    `TgoLayoutUnitGroup.generate_units` now takes **one type per position** and
    `ForceGroup.mixed_dcs_unit_types_for_group` deals that list: the **lead** type is picked
    exactly as before (so the change is a strict refinement, not a reroll), candidates are
    narrowed to the lead's own **unit family** (`layout.UNIT_FAMILIES` — today the single set
    `{Frigate, Destroyer, Cruiser}`; **every other class is its own family**, so a patrol boat
    never turns up in a cruiser's slot, a submarine never surfaces in a surface action group,
    and two carriers never share a slot — `find_carrier_unit` resolves the flagship as
    `groups[0].units[0]`), and the distinct count is capped at `MAX_MIXED_UNIT_TYPES` (3) so a
    deep roster produces a **task group, not a one-of-everything zoo** (each chosen type appears
    once, the rest of the slots are dealt from them, so a 4-ship screen off a 2-hull navy is not
    forced into an even 2/2 split). A pool with no siblings — an explicit `unit_types:` list, or
    a faction fielding one hull of the class — degrades to the old uniform group, so **the change
    can only ever add variety**. Mixing is a **layout-kind property, not a setting**:
    `TgoLayout.mix_unit_types` is False and `NavalLayout` overrides it True, so SAM sites, EWRs,
    armor and missile groups keep generating uniformly (a battery's launchers must stay one type);
    a layout YAML can override a single slot with `mix_unit_types: true|false`; and the parameter
    on `ForceGroup.create_theater_group_for_tgo` defaults **off** so the **buy menu** — where the
    player picked a hull explicitly — still generates exactly what was chosen. **The layouts, in
    passing:** the carrier/LHA screens were declared `unit_classes: [Destroyer]`, which both forced
    one class and locked the layout out of frigate-only navies (hence the duplicate "…with Frigate
    escort", whose `.miz` is byte-identical) — the screens now accept every surface combatant
    (`Destroyer, Cruiser, Frigate`), the Frigate-escort variants are kept as the deliberate **light
    screen** (frigate-led, `Frigate, Destroyer`, no cruiser) rather than a redundant copy that
    would regenerate the uniform look, and `Naval Group` keeps its per-slot class split (a layered
    task group) with new `fallback_classes` so a navy missing a class can still put it to sea.
    Generation-time ⇒ **NEW game required** (existing saves keep their generated groups).
    Headless-verified end to end on Tanker War 1988 / Pacific Repartee / Velvet Thunder. No
    setting, no plugin, no save change; upstream-shared code — carve candidate. Tests
    `tests/armedforces/test_naval_hull_mixing.py` (9); features doc §80, checklist B38 — needs an
    in-game pass (whether DCS sails a multi-class group as one formation).
81. **Cross-turn naval magazines** — the fleet's anti-ship missiles are finite, and it stops
    dumping them all in the opening minute. Off the flown Marianas 2027 Tacview (374 weapon
    launches, essentially all inside the first five minutes): **three separate facts** combined
    into one bad outcome — (1) `TgoGenerator.set_ship_engagement` spawns every ship
    `WeaponFree` + alarm RED because ship weapons are **OPTION-driven** (an `EngageTargets`
    task is air-only and crashed the naval AI when tried), so a hull fires the instant anything
    enters range; (2) a modern AShM **out-ranges the theatre** (YJ-18 ~540 km vs the 205 km
    Guam–Saipan gap), so "in range" is true at t=0 and the whole fleet salvos at once; and
    (3) a DCS mission is a **fresh spawn**, so loadouts reset and red re-dumped a full magazine
    *every turn* — sinking hulls was the only way volume ever fell. Hull culling shrinks each
    salvo and fixes neither (1) nor (3). Two independently-gated tiers, both mirroring §63's
    proven shape (`game/fourteenth/naval_magazines.py`, emitter
    `game/missiongenerator/navalmagazineluadata.py`, runtime `resources/plugins/navalmagazines/`):
    **N1 staggered release** (`naval_weapon_release_stagger`, Mission Generation → Naval strike,
    default **OFF**) — ships generate **`ReturnFire`** and the plugin releases each group to
    weapons-free at its own moment **spread evenly** across `[releaseMinS, releaseMaxS]`
    (120–900 s; evenly rather than rolled independently, so a small fleet can't randomly land
    every release in one frame — the §49 stagger lesson). **`ReturnFire`, never `WeaponHold`**:
    the point is to delay *initiation*, and a holding fleet is a defenceless one — which is
    also why the load-bearing unknown was whether a DCS ship on `ReturnFire` engages an
    *inbound aircraft that hasn't shot at it yet*. **ANSWERED 2026-08-05, BADLY** (the B39
    first fly — two Marianas missions where an emitter bug, fixed same day, kept the fleet
    held all mission): a `ReturnFire` fleet fired **zero** shots in 110 min, including while
    13 Harpoons sank the SUGARGLIDER Type 071 LHA with its HHQ-16 escorts silent alongside —
    **`ReturnFire` = no missile defense at all**, so a held/winchester group is defenseless;
    **reworked same day (DM call): RELEASE-ON-ATTACK** — the first enemy weapon aimed at
    (SHOT target) or landing on (HIT) a managed group releases it to weapons-free
    immediately, held OR winchester (friendly fire never releases; an attacked winchester
    group is never re-dropped and its overshoot stays counted), so the hold decides who
    starts the war, never who may defend. **The re-fly ("CIWS fired but no SAMs") added the
    second half: release the FORMATION, not the group** — a carrier/LHA objective is **two
    DCS groups** and the area-defence SAMs ride the **escorts**, so the targeted Type 071
    fired the AK-630 CIWS that is its whole AAW fit and died while its HHQ-16 escorts
    **1.91 km** away sat holding, never having been shot at. An attack now also frees every
    managed friendly group within `formationReleaseKm` (default **15 km**; the flown geometry
    is unambiguous — screen 1.91 km, next task force 59.02 km), **one hop, never a cascade**,
    same-coalition only. The same fly found + fixed the emitter bug: `LuaData.serialize`
    **drops a node's `add_key_value` entries whenever the node also has child items**, so the
    `stagger`/`metered` switches never reached the miz (`stagger false … metered false` at
    load) — they are now named child items (`add_item().set_value()`, the CombatSAR
    `autoSpawn` pattern), pinned by a serialization-level test; an AST audit cleared every
    other emitter of the mix. Runtime only, no persisted state. **N2 the magazine** (`naval_magazines`, same
    section, default **OFF**) — each naval group carries a persisted anti-ship stock
    (`game.naval_magazines`, keyed by the same stable `TheaterGroup.group_name` §63 uses —
    the TheaterGroup lives in the save, so the key survives regeneration; capacity from the
    curated `ASHM_MAGAZINE_BY_TYPE` summed over alive hulls at first sight, default 8),
    emitted as this mission's hard cap; the plugin hooks **`S_EVENT_SHOT`**, matches the
    weapon type against `ASHM_WEAPON_PATTERNS` (plain **substring**, upper-cased — never a Lua
    pattern, the §70 lesson), decrements, and at zero drops the group back to `ReturnFire` —
    **winchester, not disarmed**. Expenditure mirrors into the new `naval_magazines_state`
    Lua→Python channel (the §57/§63 `f.state` pattern) and is debited at the turn boundary;
    **generation never debits**, so re-generating a mission is free (the §54 lesson). **No
    double-count with §63 by construction**: the two magazines meter **disjoint weapon sets**
    — the land-attack families §63 meters (`BGM_109`, the `3M14` Kalibr) are absent here, and
    nothing as loose as `Kalibr` is used (it would catch the land-attack 3M14 alongside the
    anti-ship 3M54); a Burke legitimately appears in *both* hull tables because it carries
    Tomahawks *and* Harpoons. **Never add a land-attack family to the pattern list.** A group
    that starts a mission dry is still emitted (so the plugin holds it at `ReturnFire` rather
    than letting a spent fleet fight as if freshly loaded) and is never released by the
    stagger. Symmetric — blue's Burkes are bound exactly as red's Type 055s. The plugin owns
    no spawns and no kills: it sets ROE and counts real weapon releases, so hull losses record
    natively as always. Surfaced by `winchester_lines` (blue only — enemy residual stock stays
    hidden, like every magazine readout). **Deferred:** N3 replenishment (refill at a friendly
    port, so sustaining a fleet is a logistics decision) and N4's unit-card readout, both only
    worth doing once N2 is flown. Tests `tests/fourteenth/test_naval_magazines.py` +
    `tests/missiongenerator/test_navalmagazineluadata.py` +
    `tests/lua/test_navalmagazines_runtime.py`; features doc §81, checklist B39 — needs an
    in-game pass (the `ReturnFire` air-defence question above is the gate; then that a
    staggered fleet still fights, and that the winchester drop fires on real AShM releases).
82. **The Wing Grows (scheduled squadron arrivals)** — a campaign can hold a squadron back
    and have it join the air wing on an **announced later turn**
    (`available_from_turn:` + optional `arrival_note:` on a squadron block). Aimed at the
    structural reason SP campaigns die after turn 1: **turn 1 is the best mission by
    construction** (full wing, full ramp, no attrition), so every later turn is a degraded
    copy and nothing ever gets better. A schedule inverts that — the turn-1 wing is no
    longer the whole wing you will ever have — and it converts the DM's own stated
    motivator (variety) into the campaign's forward hook: you play to turn 6 because that
    is when you get to fly the Prowler. **Premise half-corrected when built:** aircraft
    replenishment into an existing squadron exists (`pending_deliveries`) but is a
    ONE-TURN buffer delivering more of what you already fly; **mid-campaign arrival of a
    new squadron/type did not exist at all** (the `squadrons:` block is consumed at turn 0),
    so this is new machinery, not a missing announcement. **It is small for a specific
    reason: `ControlPoint.squadrons` is a DERIVED property** (it filters
    `air_wing.iter_squadrons()` on `squadron.location`), so there is no base→squadron list
    to maintain — a squadron appears at its base and is plannable the moment it joins the
    wing, and **the planner needs no change at all**; likewise `AirWing.reset()` /
    `populate_for_turn_0()` / `end_turn()` all walk `iter_squadrons()`, so a pending
    squadron is untouched by per-turn processing for free. The squadron is **built at turn
    0 exactly as today** (preset pick, §23 country pin, callsign overrides, def claiming)
    and parked in `AirWing.pending_arrivals`; `promote_due_arrivals`
    (`game/fourteenth/wing_growth.py`) runs from `Game.initialize_turn` **before** the
    coalitions initialize, so an arrival is populated + plannable on its own turn, and
    promoted squadrons leave the pending list (naturally idempotent under the base-capture
    / TGO buy-sell re-inits). Announcement = a new `Sitrep.arrivals` field, which buys the
    kneeboard band + web LAST TURN + Qt debrief at once; unlike the §52/§75 lines an
    arrival **counts as news** so it surfaces on a quiet turn. Red schedules work (code is
    symmetric) but are **never announced**. A malformed `available_from_turn` **raises** so
    New Game aborts loudly rather than shipping a wing that never grows; unset =
    byte-identical. **Ordering principle — SEAD/DEAD before strike:** turn 1 is the
    door-kickers (air superiority, SEAD/DEAD, enablers), later arrivals are the exploiters
    (strike, deep interdiction, bombers) — which makes arrivals feel *earned* AND is the
    safe way to defer, since the early campaign cannot use deep strike before the belt is
    down. **The arc differs by how the campaign opens**, so the two shipped schedules are
    different shapes: **Baltic Fury** (offensive — kick the door → rollback → strike) T3
    Finnish F/A-18C BARCAP · T5 Swedish Gripen DEAD · T7 F-15E + F/A-18F Strike · T9 B-1B,
    with the real NATO accession order (Finland Apr 2023, Sweden Mar 2024) agreeing with
    the doctrinal order and turns 1–4 deliberately Growler-thin; **Red Tide** (defensive —
    hold → stabilise → counter-attack) T4 Mirage F1EE Escort · T6 F-15E BAI · T8 B-52H,
    where **CAS is never deferred** because the Gap fight needs it from turn 1 (its feature
    lock was lifted 2026-08-03, so no override was needed). NEW game required (the schedule
    is consumed at turn 0); `__setstate__` defaults keep old saves loading. Deferred:
    announcing under-strength arrivals (parking clamps silently), holding an arrival whose
    base is enemy-held, `available_until_turn` departures, and rendering
    `upcoming_arrivals` ahead of the turn (waiting on the SP Pilot Mode board). Tests
    `tests/fourteenth/test_wing_growth.py` (22) +
    `tests/fourteenth/test_wing_growth_campaigns.py` (20, which pins the *rules* — enablers
    never deferred, air superiority always on the turn-1 ramp, DEAD before strike, Red Tide
    never defers CAS); features doc §82, design note
    `docs/dev/design/414th-wing-growth-notes.md`, checklist B40 — needs an in-game pass.
83. **SP Pilot Mode (pre-turn card + aircraft-first sortie board)** — the express lane for
    the single-player loop, which dies at a reproducible place: create a campaign, fly turn
    1, **accept results**, never play turn 2. The stop point is neither flying nor the
    debrief (the player gets all the way through `process_debriefing`) but the moment the
    map returns and the game says *"now plan turn 2"*. Diagnosis: **in MP you play a pilot;
    in SP you play the DM AND the pilot, and the DM job has no fun in it** — an MP host pays
    the commander cost once for eight sorties, an SP player pays it for one, before any
    reward. **Additive and default OFF** (`sp_pilot_mode`, 414th Features → Single-player
    flow); the map/ATO/hand-planning path is untouched. **S1** = an "Accept results && fly
    next" button on the debrief window running the identical `process_results` → `pass_turn`
    work (extracted to `_process_turn`, shared by both buttons) and then opening the board.
    **S2** = the two-step board (`game/fourteenth/sp_pilot_mode.py`): step 1 the **airframe**
    as the PRIMARY axis — every type the wing can put up, **not** filtered by what the
    commander fragged (a flat sortie list keeps offering the same three Hornet missions) —
    then step 2 the sortie via the ladder, **rung 1** seat an existing planned flight
    (`FlightMembers.set_pilot`, zero planner involvement) → **rung 2** join an existing
    package in the role it still needs. **The role comes from the air war, not the player**
    (escort/strike/jamming — two variety axes, one player-driven), so step 2 leads with
    role+package, never the target. **One seat, AI wingmen, exactly as in MP**
    (`client_count` stays 1 — same generation path MP already exercises). **S3** = the
    pre-turn briefing (`game/fourteenth/pre_turn_briefing.py`), built on the finding that
    **the fork already computes almost every reason to continue and points them the wrong
    way in time** — `Sitrep` carries `pilots_mia`/`pows_held`/`red_c2_status`/`victory_lines`
    and renders all of it only AFTER the player commits. Five urgency-ordered sections
    (a named person on a clock outranks a statistic): **rescue** — §21 evaders, and the one
    genuinely new number, **the capture odds** (`capture_chance` already scales 10%→90% with
    depth and was never shown; "every turn you skip is a roll" only lands when the roll is
    stated) + POWs; **consequence** — §52 C2 damage, attributed ("their planning is worse
    because of you"); **objective** — §75 progress; **anticipation** — §82 upcoming arrivals;
    **open loops** — §3 unidentified contacts (real or a §79 decoy — only a sortie tells you)
    + located §49 launchers that scoot. A **pure view**: computes nothing new, mutates
    nothing, zero planner coupling (§3 viewer discipline), and every section is individually
    guarded so a briefing never breaks a turn. **Deliberately not done:** rung 3 (a
    standalone frag — a private war built to order is what the "put me in existing packages"
    spec rules out); rung 2's *mutation* (the board offers joins, but building the flight is
    the ATO's own add-flight path — the dialog says so plainly rather than failing silently);
    and the structural "1 of 25 packages" problem, whose real lever is **smaller SP ATOs**
    (planner work, its own change). Tests
    `tests/fourteenth/test_sp_pilot_mode.py` (20) +
    `tests/fourteenth/test_pre_turn_briefing.py` (16); features doc §83, design note
    `docs/dev/design/414th-single-player-loop-notes.md`, checklist B41 — **`qt_ui` is not CI
    type-checked and the dialog cannot be driven headlessly, so it needs an in-app pass.**
84. **Old-stock loadout attrition** — squadrons burn the good stock first, so the tail of a
    campaign is flown on what is left in the bunker. Every flight of the same airframe and
    task used to carry a **byte-identical** loadout: `Loadout.default_for` resolves by NAME
    and returns the **first** payload that validates, with zero randomness anywhere in the
    path, so six BARCAP flights put up six identical magazines of the newest missile the
    date allows. `degrade_loadout_for_stock` (`game/fourteenth/stock_attrition.py`) rolls a
    depth **per weapon station** and walks that station down **the fallback ladder the
    weapon data already declares** — so "old stock" needs no new data: AIM-120C → AIM-120B →
    **AIM-7MH** is the ladder, and a deep roll is what breaks out the Sparrows.
    **Per STATION, not per flight, and that is the whole point** (DM call 2026-08-03 —
    "what I'm looking for is mixing and matching on the same flight"): one roll for the
    whole aircraft only ages the magazine *uniformly*, turning 4× AIM-120C into
    4× AIM-120B — four identical rounds either way. Rolling each station means a Hornet
    that wants four long-range missiles comes out with **a couple of AMRAAMs and a couple
    of Sparrows on the same jet**, which is what loading out of a picked-over bunker looks
    like. **It is not an A2A feature** — the hook is task-agnostic and so is the data, so
    BAI/Strike get the generational bomb ladder for free
    (`GBU-31(V)3/B` 2001 → `GBU-24` 1986 → `GBU-10` 1976 → `Mk 84` 1955 — JDAM to LGB to
    dumb bomb; `GBU-38` → `GBU-12` → `Mk 82`; `CBU-97` → `CBU-87`), and **68 % of all
    non-protected weapon groups have usable depth** (a2a-missiles 80 %, bombs 79 %,
    standoff — A2G + anti-ship — 58 %). Hooked at the
    only two planning sites (`FlightMembers.from_roster` / `resize`), where the result is
    stored on the members and pickled, so **the roll is stable across re-generation** with no
    seeding needed; growing a flight clones what it already carries, so the mixture is the
    flight's, not per jet (jet-to-jet variation would need per-member loadouts). **Pressure
    scales with the campaign clock** —
    `stock_attrition_start` at turn 1, `+stock_attrition_per_turn` each turn, capped at
    `stock_attrition_max` (**20** / 4 / 50 %) — and **depth is geometric in that pressure**, so
    one rung is common, three is rare, and both get likelier as the war drags. The 20 %
    baseline is deliberate: a 0 % start (the first cut's default) leaves turn 1 uniformly
    best-equipped, which is exactly the case the feature exists to fix. **Three
    guards, one of them load-bearing:** `WeaponType` **cannot** express a weapon family (a
    Sidewinder and a JDAM are both `UNKNOWN`), and several fallbacks cross families *on
    purpose* — `AN/ASQ-228 ATFLIR → AIM-120C`, `AN/ALQ-131 ECM → 2xAIM-120C`,
    `AGM-84A → GBU-24` — which are a sane last resort for **date gating** but absurd as
    attrition (they would hang a missile on the targeting-pod station). So `WeaponGroup`
    gained a **`category`** (the `resources/weapons` subdirectory it loaded from,
    `object.__setattr__` like `target_overrides`, `getattr`-guarded for old saves) and the
    walk stops at a category boundary; equipment types (`TGP`/`JAMMER`/`OFFENSIVE_JAMMER`/
    `DECOY`) are never touched at all; and a **player-customised loadout is left exactly as
    built**. **The STORE-family guard is the third** (`store_family`, added 2026-08-04 off a
    flown Marianas miz): a mod that models its own pylons namespaces every store it ships
    (`{SUPERHORNET_PYLON_10_AM_1X_AIM-120C}`) **and inherits the stock entries into the same
    pydcs pylon table**, so a stock store passes `can_equip` on the mod jet without being
    mountable on the mod's geometry — DCS drops it and **the pylon spawns EMPTY** (the §71
    `(XW)`-without-injection failure mode). Observed: a CJS F/A-18E's station-8 AMRAAM aged to
    `{LAU-115 - AIM-7H}`, a **stock Hornet rack**, because `AIM-7MH` registers four clsids and
    **none is Super-Hornet-native** — unlike AIM-120C/B/9X, which carry 22/24/62 mod stores and
    substituted mod-natively all along. A substitution that would leave the store family is now
    **refused outright** rather than downgraded further (a flight keeping its modern missile
    beats one carrying an invisible older one); measured **0** family-leaving substitutions
    across every Super Hornet station × store × depth. Note this is a *registration* gap in
    `AIM-7MH.yaml` as much as a walk bug — registering the mod's Sparrows would let that rung
    be used mod-natively. **The same class of defect was ALREADY in the authored fits and was
    fixed the same day** (the reported symptom — "the Super Hornets are generating with empty
    inside pylons where fuel tanks would normally be"): **34 stock stores across the FA-18E/F
    `Retribution …` fits** were re-pointed at the mod's own equivalents — `{AGM_84D}` →
    `{SUPERHORNET_PYLON_03/09_MB_SM_1X_AGM-84D}`, `{AN_ASQ_228}` →
    `{SUPERHORNET_PYLON_05_TP_ASQ228}`, `LAU_117_AGM_65F` →
    `{SUPERHORNET_PYLON_02/10_OB_MV_1X_AGM-65F}`, `{BRU_42A_x3_ADM_141A}` →
    `{SUPERHORNET_PYLON_03/09_IB_TD_3X_BRU_ADM-141A}`, and the stock Litening
    `{A111396E-…}` on the **centre-line** (ME column 6 — the visible one, in the DEAD and
    OCA/Aircraft fits) → `{SUPERHORNET_PYLON_06_CN_TP_AAQ28}`. The mod's **12 TALD stores were
    registered** into `ADM-141A.yaml` so the re-point does not recreate the #771
    ungated-store hole. Verified 0 non-mod-native / 0 non-pylon-legal stores remaining and all
    14 E/F tasks still resolving; guards in
    `tests/fourteenth/test_super_hornet_payloads.py`. **ME column gotcha worth knowing:** the
    CJS row is `INT | 11 | 10 | 9 | 8|7 | 6 | 5|4 | 3 | 2 | 1` — ten columns for eleven
    pylons, so `8|7` and `5|4` are **merged, either/or** slots (the inboard tank *or* the cheek
    AMRAAM, never both). That is why the BARCAP fit (`PYLON_04`/`PYLON_08`) and the SEAD fit
    (`PYLON_05`/`PYLON_07`) look contradictory and are in fact both correct. Separately and
    **not** a bug: the E's `Retribution BARCAP`/`Escort` fits author **no station 5**, so their
    centre-line is deliberately bare (two inboard tanks + internal aux). **The year guard is the second load-bearing one** (added on review before merge,
    after the first cut shipped without it): `fallback` answers "what do I use *instead* when
    this is unavailable", which is a **date-gating** answer and is **not monotonic in year** —
    **18 same-category fallbacks in the shipped data point at a NEWER weapon**, so an
    unguarded walk hands a flight *better* stores the longer the war runs. `2xAIM-120B`
    (1994) → `AIM-120C` (2018) is the trap the first cut mistook for a free win (the yaml's
    own `# If we've run out of doubles, start over with the singles` — right for date gating,
    wrong here **twice**: it halves the magazine *and* upgrades the missile), and
    `AGM-65E` (1985) → `AGM-65G` (1989) → `AGM-65F` (1991) is the proof that **date gating
    cannot save us** — all three are legal in Desert Storm (1991), so nothing downstream
    clamps the upgrade. `_older_group` now takes a rung only when it is **provably older**
    (an undated rung is unprovable, so the walk stops), measured to leave **0 upgrade paths**
    across all 306 groups × depths 0–3 while the headline
    `AIM-120C → AIM-120B → AIM-7MH → AIM-7M` Sparrow break-out is untouched. Date gating
    still runs afterwards, so a substitution can never be newer than the campaign allows —
    but that is a *ceiling*, not the ordering guarantee. A newer rung is also **hopped, not
    treated as the end of the ladder**, which is what recovers the rung actually wanted
    (`2xAIM-120B` → ~~AIM-120C~~ → **AIM-120B**, the single rail of the same generation:
    fewer missiles, not newer ones; `AGM-65E` → **AGM-65B**) — worth +15 groups of usable
    depth, 191 → 206, spread across a2a **and** standoff **and** bombs. Gated
    `stock_attrition` (414th Features → Auto-planner behaviour, default **ON** — DM call
    2026-08-03, "it's the behaviour I asked for"; OFF returns the original loadout object
    untouched and is byte-identical). Tests
    `tests/fourteenth/test_stock_attrition.py` (36 — a repo-wide never-an-upgrade invariant
    over every group, the JDAM→LGB→dumb-bomb ladder, and four that drive the real F/A-18C
    `Retribution BARCAP` fit on real pydcs pylon tables to prove one jet ends up mixed, that
    twelve flights are not identical, and that the shipped fit is never mutated in place);
    features doc §84, checklist B42 — needs
    an in-game pass.
85. **SAM battery support section (refuellers + power)** — a real S-300 site carries a
    **refuelling section** and the **5I57A diesel power stations** that run the battery;
    Retribution generated the radars, the C2 and the launchers and no support at all (DM
    finding 2026-08-04 off a textbook SA-10 built on the training server: "ATZ-10 is a
    refuelling truck, why are we not using it in SAM sites?"). **Three independent causes.**
    (1) **No refueller was a registered unit** — no yaml for `ATZ-10`/`ATZ-5`/`ATZ-60_Maz`/
    `ATMZ-5`/`TZ-22_KrAZ`/`M978 HEMTT Tanker`/`generator_5i57` (the "DPS" in the screenshot =
    *Diesel Power Station 5I57A*, filed by pydcs under `AirDefence`, not `Unarmed`), so none
    was a `GroundUnitType`, none reached `Faction.accessible_units`, and
    `has_access_to_dcs_type` rejected every one. The single place an ATZ-10 *did* appear is
    `tgogenerator.py`'s hardcoded `_SOVIET_TANKERS` FARP/airfield pool, which bypasses the unit
    registry — which is exactly why it was only ever seen on a ramp. (2) **No faction listed
    one** (139 factions author `logistics_units`; all cargo trucks and jeeps). (3) **the
    `S-300 Site Logistics` slot was DEAD CONFIG** — declared in the layout yaml with an explicit
    truck whitelist, but **no group of that name existed in the shared `S-300_Site.miz`**.
    `LayoutLoader._load_from_miz` walks the *MIZ's* groups and looks each up in the mapping, so
    a slot naming a group that does not exist is never instantiated, **with no warning and no
    error** — an S-300/SA-10/SA-20/S-400 site had therefore never generated a support vehicle
    at all, whatever the faction rostered. **Fix is data only** (no setting, no plugin, no Lua,
    no save change): 7 new unit yamls — the refuellers `class: Logistics` (price 3), the 5I57A
    **`class: Power`** (price 6, the class the Patriot EPP and LvS-103 Elverk already use, and
    the load-bearing choice: `LOGISTICS` is in the ground planner's `_DEPLOYABLE_UNIT_CLASSES`
    so bowsers ride to the FLOT with the cargo trucks exactly as the Urals/M818s already do,
    while `POWER` is in neither that nor `FRONTLINE_UNIT_CLASSES`, so a generator never marches
    to a front); **3 new position groups appended to `S-300_Site.miz`** (Logistics/Fuel/Power,
    2 positions each, dispersed ≥50 m clear — appended so the template origin is unmoved and
    every existing offset stays byte-identical; pydcs round-trips this all-vanilla template
    losslessly); **fuel and power are SEPARATE slots and must stay so** (a unit group fields
    exactly ONE type, so a merged slot yields two bowsers *or* two generators, never one of
    each); the 3 S-300-family layouts gain the slots (the SA-2/SA-3 Mixed Site gets Fuel only —
    the 5I57A is S-300 kit); and access comes from the **11 S-300-family preset groups**, the
    **Patriot precedent** (`MIM-104_Patriot_Stationary.yaml` already carries its own EPP + an
    Oshkosh HEMTT this way), so **no faction json changed**. **Fixed in passing — the same bug
    elsewhere:** `Sky_Sabre_Battery.yaml` named its point-defence slot `Point Defense` against a
    MIZ group called `PD`, so **a Sky Sabre battery has never fielded any SHORAD**. Headless-verified on Red Tide (all 7 S-300 sites now field truck +
    refueller + 1–2 power stations; theater 26 refuellers + 12 DPS, previously zero). Balance:
    ~+18 on a ~230-point site (<8 %), all unarmed soft targets — `max_threat_range` unchanged,
    so SEAD/DEAD targeting is unaffected. **The same-day install-wide sweep + wiring pass**
    (DM: "scrub my local install … SO many support vehicles we are not utilizing" → "start by
    editing the stuff we touch most often"): `tools/audit_unit_coverage.py` (the repeatable
    coverage report — run after any DCS/mod update; the complement of `verify_mod_export.py`,
    which checks *values*) measured **130 of 834 placeable units with no yaml** (EW 29 % usable,
    power 67 %, trucks 68 %, C2 80 %); **35 registered** (Gazetchik-E decoy + the 2 "Radio
    jammer" GPS spoofers under a new inert `UnitClass.ELECTRONIC_WARFARE`, 8 C2 vehicles as
    `CommandPost` — safe because every CP slot is `fill: false` — both APA GPU trucks as `Power`,
    the RD-75, 11 support/crash vehicles as `Logistics`, 10 ships incl. **CVN-70 Vinson**, which
    also had to join `runway_is_operational()`'s hull whitelist or a Vinson CP would read as
    SUNK), registration proven inert (no faction reaches any of them un-wired); the remaining 95
    are deliberate (rolling stock, buses, VAP scenery, ramp tugs, payload placeholders). **The
    wiring** (NEW game required): the 12 dedicated legacy layouts (SA-2/SA-3/SA-5/SA-6) carry the
    era-safe 1960s trio (ATZ-5/ATZ-60/TZ-22) in their Logistics whitelists — one slot rolls ONE
    type, trucks OR a bowser; the mixed truck+fuel+power spread stays S-300-only — the C2-less
    SA-2_ZSU + HQ-2 presets carry the **ZIL-131 KUNG** (fills the generic layouts' dormant
    `fill:false` CP slot; generic presets got NO Logistics units on purpose — they would DISPLACE
    faction-fill trucks), and 10 active-campaign factions roster era-correct refuellers
    (`logistics_units` → convoys/FLOT/generic-site fill; the COIN insurgents get the
    **civilian-liveried ATZ-5** on the ratline). Headless: 11/17 RT legacy sites rolled a
    refuelling section. **GPS spoofers deliberately un-wired — another agent owns them.**
    **EWR-site support sections (same day):** the generic EWR template (a lone radar) gained
    appended C2/Power/Logistics groups + three optional layout slots — C2/Power are
    **`unit_types` whitelists, never classes** (a class-based C2 slot would park a Patriot ECS
    or Buk CC at an EWR site), gated by faction access via **`air_defense_units`** (NOT
    `logistics_units` — procurement would buy undeployable dead weight): KUNG + 5I57 for the
    Soviet actives, the **FPS-117 ECS shelter** for RT blue/DS91/USA 2020; the Logistics slot
    is class-based so each nation's own trucks deal in for free; all kit zero-detection, MANTIS
    unchanged; a no-kit faction renders a bare radar as before. Headless: **all 6 RT EWR sites**
    render radar + KUNG + 1–2 DPS + trucks. **Economy building furnishing (same day):** the
    fuel/ammo/factory/warehouse layouts — the fuel farm was 8 static tanks and **not one
    bowser** — each gain one optional class-based Logistics vehicle group (2 appended
    `buildings.miz` positions), dealt from the faction's own roster; reaches
    **layout-generated** objectives only (hand-authored named targets — DS91's CENTAF set —
    never touch layouts and stay as authored, by design). **C2 compound furnishing (same day,
    DM call — the §51/§52 semantics change ACCEPTED):** the comms tower gains a comms van
    (KUNG/PBU) + 5I57s + trucks, the command center a C2 shelter section (**GCI Station (KRU)**
    for 1980s+ Soviets — era-gated, Vietnam 1970 rolls the PBU — + KUNG/PBU) + generators +
    trucks; §51 transmits from **every alive unit** of a node and §52 counts a CC alive while
    **any unit lives**, so killing the building alone no longer silences/decaps a site — the
    surviving van keeps transmitting, and a full §52 kill must take the vehicles too (stated in
    the layout comments + tests). **DS91's KARI is the showcase** (13/13 relays + 4/4 centers
    furnished, GCI shelters at the centers); RT's scenery-authored 9-node network stays as
    authored; power plants stay bare on purpose. **The "do-them-all" closure (same day):**
    the legacy families got the full **truck-AND-fuel spread** — the 3 shared launcher
    templates gained a `Fuel` group, the pass-1 trio moved OUT of the Logistics whitelists
    into fill:false Fuel slots (a bowser in a Logistics whitelist DISPLACES the faction truck
    fill — the load-bearing distinction), and every Soviet family preset + Hawk carries
    era-correct trucks+bowsers (headless: **46/46 DS91 legacy sites** field both); **HQ-22**
    declares the S-300 support slots and China runs the Soviet fuel kit (DM call — preset +
    `china_2027` roster; Marianas' Tinian battery renders SX2190/Urals/TZ-22s/5I57); **western
    C2 kit** closes the no-western-van gap (Trojan Spirit at comms, fire-control bunker +
    Predator GCS at CCs, era-gated — no 1995 van on a 1988 faction, test-pinned); the
    **Gazetchik-E decoy** (confirmed HDS-mod) rides only the HDS-gated modern S-300 presets
    (SA-20/20B/21/23/23B) via the new `S-300 Site Decoy` slot — vanilla can never see it, RT
    stays decoy-free, ARM-seduction is an explicit B44 fly question; and **the textbook
    configuration is THE configuration** (DM call) — S-300-family support slots stopped
    rolling 1–2: every site renders 2 trucks + 2 bowsers + 2 DPS deterministically,
    test-pinned. **Two template landmines,
    now CI-locked:** pydcs saves miz countries **name-sorted** and the loader anchors each
    layout's origin on the first matched unit (vehicles before statics per country), so support
    groups live under **blue/USAF Aggressors** — the only blue country sorting after USA — with
    an origin-pinned-at-(0,0) test; and pydcs seeds unused countries into **NEUTRALS**, which
    the loader never scans (pop into blue first or the groups silently load as nothing). Tests
    `tests/armedforces/test_sam_support_vehicles.py` (161, incl. the dead-slot guard now
    **repo-wide across all five layout families** with the loader's real name-or-statics
    matching, and six both-ways nation-correctness cases for the EWR kit);
    features doc §85 (+ the "Unit-coverage sweep — 2026-08-04" section), checklist B43 + B44 —
    needs an in-game pass.
    **MISSILE batteries got the same treatment 2026-08-06** (DM question, off the 9K720
    Iskander's published system list — TEL · transporter/loader · command-and-staff ·
    information-preparation · maintenance · life-support): a missile site generated **three
    launchers and a UAZ-469 jeep**, from the ONE generic layout
    (`resources/layouts/defenses/missile.yaml`) behind every SCUD/Iskander/CJ-10/V-1/ATACMS site
    in the fork — **33 shipped campaigns author missile markers** (DS91 9 sites, Marianas 3, RT 2,
    Baltic Fury 1). **DCS models 3 of those 7 roles** with distinct hardware (TEL; a
    transporter/loader stand-in — `ZIL-135`, the 8×8 that carries Soviet theatre rockets,
    `S_75_ZIL`, a literal missile transporter, `CH_HEMTT_M977` for NATO; and the §85 C2 kit), so
    the section is transport + transload + fuel + command, **not** a transcription of the TO&E —
    and **zero new unit registrations were needed**, §85 had already registered every candidate.
    Slots (textbook fixed counts): 3 launchers · **2 cargo trucks** · 1 transporter/loader ·
    1 refueller · 1 command-and-staff vehicle · the unchanged optional AAA/SHORAD; four positions
    appended to `missile.miz` with the pre-existing offsets **byte-identical** and the template
    anchor (`ScudGenerator 3`) untouched, so no authored site moves. **The displacement fix:** the
    old class-based `Logistics` slot picks ONE type from a pool that since §85 also holds bowsers,
    so the bowser *replaced* the cargo truck (what the flown Marianas sites showed) — cargo is now
    an explicit multi-national truck whitelist (`fallback_classes: [Logistics]` so nothing
    generates bare) and fuel is its own slot; measured, all **36** missile-fielding factions fill
    cargo + transload, 29 field a refueller, 11 a command vehicle. Same trap re-caught mid-build:
    the transload slot's first cut used the Logistics fallback and resolved **9 of 11 candidates
    to bowsers** for Russia 2020. **§49 shapes the section** — every unit shares ONE DCS group with
    the launchers and `mist.goRoute` routes a group whole, so one undrivable member pins the
    battery: drivable metal only, no statics, no trailers, and deliberately **no 5I57A power
    station** (S-300 kit, and absent from the Iskander's list); enforced by
    `test_no_support_unit_can_pin_the_scoot`. **Launchers are no longer free:** every one was
    `price: 0` (Scud-B, Iskander-M/K, CJ-10, Shahed-136, the V-1 ramp, the whole coastal anti-ship
    family) while missile + coastal sites **are** purchasable and repair cost IS the unit price —
    now V-1 20 · Shahed 25 · Silkworm 30 · Scud-B 40 · RBS-15KA 55 · Bal 60 · Iskander-M 70
    (= both 9K720 registrations) · YJ-12B 70 · Iskander-K/CJ-10/Bastion-P 75 · DF-21D 85, scaled
    against the already-priced `CH_M270A1_ATACMS` (45) and the artillery ladder; a full SCUD
    battery ≈135 vs ≈230 for an S-300 site. Tests
    `tests/armedforces/test_missile_site_support.py` (34); features doc §85, checklist **B47** —
    needs an in-game pass (NEW game required; the composition is generated at campaign start).
86. **GPS jamming (satellite-guided weapons go long)** — enemy GPS-jamming ground sites deny
    satellite guidance over an area, so a JDAM/JSOW/JASSM/SLAM-ER/KAB-*S released into the
    bubble lands off the aimpoint and the pass fails. **The constraint that shapes the whole
    feature: DCS models NO GPS receiver** — no API degrades a jet's navigation, a weapon's
    guidance quality or a JDAM's CEP, which is why every earlier look at GPS jamming
    (`414th-iads-c2-consequences-notes.md`) recorded it as *not feasible*. The way through is
    to stop jamming the aircraft and **jam the weapon**: `S_EVENT_SHOT` starts a track on any
    store matching the curated satellite-guided pattern list; the first sample it is inside a
    live **enemy** jammer's reach, roll `degradeChancePct` **once** (remembered either way, so
    a long glide can't re-roll itself into a certainty); the store then flies its **entire
    normal profile** and only at the terminal gate is `destroy()`ed and detonated at a scored
    offset, **with its own warhead** (`desc.warhead.explosiveMass` × `missPowerScalePct`, so a
    2000 lb JDAM craters like one and a 500 lb JDAM does not; a store reporting no warhead falls
    back to the flat power = the pre-scaling behaviour). The pilot sees the release, the fall and the bang — in the wrong place. Miss
    distance scales with jamming strength (1 at the emitter, 0 at the bubble edge), so a store
    clipping the fringe is nudged and one released overhead is thrown clear. **The predictive
    terminal gate is the non-obvious half:** a plain `agl <= floor` test **fails for fast
    weapons** (a store descending at 400 m/s covers 800 m in a 2 s step, so it can be at 900 m
    AGL one tick and detonated on the aimpoint the next — the jamming silently doing nothing,
    the worst failure mode since it reads as the feature being off), so the gate fires when the
    store would already be *through* the floor by the next sample
    (`floor = max(terminalAgl, descentRate × trackStep × 2)`) — a coarse step makes the destroy
    happen **higher**, never later than impact. **No phantom spawns / no invented losses** (the
    §35/§37/§49 discipline): the store is a real weapon from a real jet, the script spawns
    nothing and owns no kills beyond the miss explosion (ordinary DCS damage, recorded
    natively), and a weapon that vanishes before the gate is simply dropped — a degraded store
    that got that far hit normally and is deliberately **not** re-detonated. The jammer is an
    ordinary strikeable TGO and killing it drops it from the live-site check on the very next
    weapon, so **accuracy returns inside the same mission**. **Identification is a unit-yaml
    contract, not an id list** — the *presence* of a `gps_jamming:` block in a ground unit's own
    data file makes it a jammer (`GpsJammingProperties`, the §24 `date_gated_properties`
    precedent; `radius_nm`/`miss_radius_m` optional, `{}` or `true` = campaign defaults), chosen
    so **adding a jammer is a data edit** and unit work never has to land together with feature
    work; a mixed site takes the **longest** declared reach and the **worst** declared miss.
    **The curated weapon list** (`GPS_GUIDED_WEAPON_PATTERNS`, emitted to Lua so it has exactly
    one home; plain case-insensitive **substrings, never Lua patterns** — weapon names carry `-`
    and `(`, the §70 lesson) is **in:** JDAM (GBU-31/32/38), GBU-54 (Laser JDAM — its *baseline*
    mode is GPS/INS and the runtime can't see whether anyone is lasing), JSOW, JASSM, SLAM-ER,
    WCMD, KAB-500S/1500S (GLONASS, so red eats its own medicine); **out, and load-bearing:**
    every laser/TV/IR/anti-radiation weapon (a Paveway that mysteriously misses is a bug report,
    not a feature) plus the §63/§81 ship-launched cruise missiles (their own flown features).
    **Squadron calls 2026-08-04:** *symmetric* (a site degrades the **opposing** coalition only,
    so a blue jammer works the day one is fielded); *the player is told both ways* — a
    recon-**fogged** kneeboard BLUF line (an un-scouted jammer is **not** briefed, so finding it
    is worth a recon sortie) plus a **one-shot cockpit cue** on a flight's first spoofed weapon,
    so a failed pass reads as jamming rather than a broken sim; *GPS-guided air ordnance only*.
    The counters are **change delivery method** (laser/TV unaffected) or **kill the
    jammer** — NOT standing off: the bubble is a **GPS-denied TARGET area, not a denied
    RELEASE area**, because a weapon aimed at anything inside it flies through it whatever
    range it was launched from, so the radius is simply the size of the target set that loses
    guidance. That fact sizes the feature: reach is **15 nm**, deliberately below the 50 km
    (27 nm) DCS declares for the vehicle, because at 27 nm one site denied a large share of a
    medium map (switching a weapon class off rather than posing a question). **Placement is two
    models, both preset-driven and `optional`+`fill: false` so every shipped site is unchanged**
    (design worked through 2026-08-05): a **standalone `GPS Jamming Site`** (own marker, own
    point defence, own radar) for denial anywhere, and an **attached `S-300 Site GPS Jammer`
    section** (used by `SA-20/S-300PMU-1 (GPS jamming)`) that puts the jammer *inside* an
    existing threat ring — killing it then means entering the S-300's envelope rather than
    strafing a soft truck, and it is where a real EW company sits. **Density: ≤3 per campaign,
    non-overlapping, CI-guarded** — bubbles are large and **invisible on the map**, so a heavy
    hand is easy to author and hard to notice (the Marianas "wall of rings" lesson), and
    overlap specifically buys nothing because **effects do not stack** (a weapon faces only the
    strongest covering bubble, the §77 rule). **It carries NO radar and is a STRIKE target, not a SEAD
    target** (DM call 2026-08-05, reversing the 2026-08-04 pairing): a real GPS jammer is
    **L-band**, which no RWR covers and no ARM homes on, so making it HARM-able was the
    *unrealistic* option — and DCS agrees, the stock unit declares `GT_t.ws = 0` with no
    `GT.WS`/`GT.Sensors`/`searchRadarFrequencies`. You find it by **recon** (§3 surfaces it, the
    kneeboard briefs the area once scouted) and kill it with **bombs**; its optional SHORAD slot
    stops that being free (a faction with no SHORAD — China 2027 — fields an undefended site).
    Dropping the radar also removed the faction-roster leak: **only the jammer is granted**, and
    `ElectronicWarfare` is referenced by no layout, so it can never be faction-filled anywhere. **Task = EarlyWarningRadar**, the one
    air-defence role MANTIS never holds dark. **Granting faction access matters:
    `accessible_units` chains `preset_groups`, so registering the preset there grants access
    BUT also makes the site a `random_group_for_task` candidate — measured 2-to-4 sites
    generating when only 2 were pinned; grant via `air_defense_units` instead.** Fixed in
    passing, a generic engine bug: **`generate_ewrs` called `random_group_for_task` directly
    and never read the `ground_forces` block, so an EWR marker could not be pinned at all** —
    the identical hole naval groups had until `generate_navy` was routed through
    `get_unit_group_for_task` (2026-08-03); upstream-carve candidate. **Fielded in four modern campaigns**
    (2026-08-05), two well-separated RED-owned sites each: **Baltic Fury** (2027), **Marianas
    2027**, **Slava Ukraini** (2026) and **Into the Hornets Nest** (2022) — the era filter is
    the jammer's own 2010 introduction, which excludes the Cold War/Desert Storm laydowns
    outright. **A pin must bind to a CP owned by the side fielding the jammer** (the gate checks
    the *owning* CP's faction, so a red preset on a blue-CP marker is silently discarded —
    caught when three campaigns each generated one of two pinned sites; test-guarded).
    **Preseeded in Operation Baltic Fury** on two dedicated `GPSJAM-*` markers (Copenhagen approach ~5 km from
    the Kastrup victory objective; Rostock on the central axis) added additively by
    `tools/build_baltic_fury_miz.py --gps-jamming` — their own markers, NOT a modifier on the
    EWR net, so red's radar chain and its GPS-denial belt are attacked separately. **Red Tide
    is deliberately NOT a candidate — it is 1988, and GPS-guided weapons postdate it
    entirely** (DM call 2026-08-05). Gated `gps_jamming` (414th Features → Electronic & command warfare, default **OFF**,
    preseeded nowhere) + `gps_jamming_default_reach_nm` (30) / `gps_jamming_miss_radius_m` (200)
    (Mission Generation → Comms war); **the `gpsjamming` plugin is the runtime**, so an unticked
    plugin silently kills the setting (the §36 lesson). Deliberately not done: aircraft
    navigation degradation (impossible, and it would lie to the pilot's own cockpit), a
    dedicated map overlay (the site is an ordinary TGO and already draws), §74 DTC coupling (a
    cartridge carries steerpoints, not guidance quality), and **planner awareness** (the
    auto-planner does not yet avoid jammed areas or re-pick loadouts — a real follow-up kept out
    of v1 so the runtime can be flown alone). Tests
    `tests/fourteenth/test_gps_jamming.py` (34) +
    `tests/missiongenerator/test_gpsjammingluadata.py` (4) +
    `tests/lua/test_gpsjamming_runtime.py` (11); features doc §86, design note
    `docs/dev/design/414th-gps-jamming-notes.md`, checklist B45 — needs an in-game pass (the
    terminal gate beating a real JDAM's terminal profile is the genuine unknown).
87. **Naval station-keeping racetracks** — enemy ships stop being stationary targets. A ship
    TGO only ever got waypoints when the campaign was *repositioning* it
    (`sail_to_destination`, gated on `ShipGroundObject.target_position`); with no destination
    it generated a **zero-waypoint route** and sat motionless on its campaign marker for the
    entire mission, so last turn's recon photo — or a pre-planned coordinate — was always
    still good. (This is also why blue's boats appeared to move and red's never did: the blue
    carrier steams into wind, and only *relocating* ships sailed.)
    `GroundObjectGenerator.hold_station` gives every other ship group a **racetrack centred on
    its anchor** instead. **The centring is the whole design**, not a detail: a circuit drawn
    *around* the marker would have the group steam a full radius clear of it and read as
    transiting off station, whereas an anchor-centred oval keeps the group's **mean position on
    its campaign position** — it holds station under way, and the campaign map, the drawn
    threat rings and the turn-boundary model all stay honest. The envelope is the bound that
    answers "they can't wander off": `STATION_LEG` 3 NM × `STATION_WIDTH` 1 NM at
    `STATION_SPEED` 10 kt puts a hard **~1.6 NM ceiling on displacement from the marker**,
    forever, with a ~48 min lap so the hull is visibly under way all mission.
    **The SIZE is set by the ship's own threat ring, which the map draws at the marker — so
    displacement is straight error in that ring.** The first cut was an **8 × 2 NM** oval
    picked by feel and it is wrong: its 4.1 NM reach is **~4× a Molniya's entire 2 km
    engagement radius** (a hull sitting wholly outside its own drawn ring) and 48 % of an
    Albatros/Rezky's 16 km; at 3 × 1 those become 1.5× and **18 %**, with a Type 054A's 45 km
    at 7 % and a Burke's 100 km at 3 %. Real practice agrees — a naval *station* is quoted in
    **thousands of yards from the guide** (WWII carrier doctrine's "Circle Six"/"Circle Nine"
    are 6,000/9,000 yd for the **whole screen**), so ~3,200 yd is a station and ~7,600 yd was
    an entire screen's radius applied to one hull. **Collision between groups is deliberately
    NOT the constraint** — measured, the closest two naval groups in any shipped campaign are
    **17 NM** apart, so tracks are disjoint by a wide margin either way, which is why the
    threat rings had to set the number. Guard:
    `test_the_station_stays_small_against_a_ship_threat_ring` (fails on the old 8 × 2).
    **No plugin, no Lua, nothing at runtime** — the waypoints are ordinary route points and
    the loop is the Mission Editor's own `SwitchWaypoint` action, so DCS's naval AI sails it
    itself. That is *why* it composes: a §63 cruise-missile `FireAtPoint` is **pushed** onto
    the queue and pops back to this route when the salvo ends, where a scripted `mist.goRoute`
    (a `setTask`) would have wiped it — the §49 fire-then-scoot clobber, avoided by
    construction rather than worked around; §81's ROE/alarm ride `points[0]` and are untouched.
    **Land is handled in Python, where the landmap already lives** — DCS naval AI does no land
    avoidance whatsoever, so each candidate orientation is sampled with `theater.is_in_sea()`
    every 1 NM along **every leg** (two clear endpoints with an island between them would
    beach the group), and 12 bearings are tried in a **crc32-of-group-name order** so a ship in
    open water takes its first choice, one in a strait ends up oriented **along** the water it
    actually has, regeneration re-derives the same station rather than reshuffling the fleet,
    and a whole fleet doesn't steam in parallel like a parade. Every failure degrades to
    **today's stationary behaviour**: no landmap, no clear orientation, or a spawn the landmap
    won't confirm as open water (a marker inside a harbour polygon) simply stays put.
    **Carrier and LHA control points are untouched** — `GenericCarrierGenerator` overrides
    `generate()`, so `steam_into_wind` and the §72 airboss keep the boats. Symmetric, and
    **no setting** (the §80 precedent — same file, same generation-time shape: this is not
    unverified runtime Lua, so a kill switch would only add to the §28 surface). Measured
    across the shipped naval campaigns: **marianas_2027 11/11 · pacific_repartee 21/21 ·
    tanker_war_1988 2/2 · 1968_Yankee_Station 2/3** ship markers put on station, the one miss
    being a hull whose spawn the landmap does not classify as sea (the safe degrade firing).
    NEW mission only — regeneration picks it up, no new game and no save migration. Tests
    `tests/missiongenerator/test_naval_station_keeping.py` (11); features doc §87, checklist
    **B48** (◐ PARTIAL — *the row was created 2026-08-06; §87 shipped without one and this
    pointer read `B46`, which is the §28 settings-surface row, with its only evidence buried
    inside B38's prose*). **Flown 2026-08-05 (Marianas):** groups sail **12–24 km on station**
    vs 0.1 km parked pre-§87, with inter-hull spacing constant to 2 d.p. — so DCS accepts the
    route, ships get under way, and a §80 mixed-hull group holds formation doing it. **Still
    owed, and it is the load-bearing half:** the guarantee is a ~1.6 NM ceiling on
    **displacement from the anchor**, but what was measured is **path length travelled** —
    different quantities, and a group sailing 24 km in a straight line off station reads
    identically. The `SwitchWaypoint` **loop** is also only inferred (48 min at 10 kt ≈ 0.8–1.6
    laps of a 3×1 NM track). Both need a ≥90 min mission measuring position-vs-anchor.

---

## Repo & Branch Layout

- This repo (`bradyccox/414Ret`) `main` = the consolidated, most-up-to-date 414th build.
- Upstream is `dcs-retribution/dcs-retribution`; the 414th's PR fork is
  `bradyccox/dcs-retribution`.
- The 414th's primary "all features" working branch in the dev checkout is
  `414th-all-features`; `main` here = that + the Iran pack + a Black/mypy lint pass.

### Upstream PR ledger (**refreshed 2026-07-20** — 50 PRs: 20 open / 8 merged / 22 closed. **Late 2026-07-20: the squadron-country surfacing carved as draft #896** — the Discord thread (Starfire's yaml `country:` ask + Toad's under-livery dropdown) answered the same day it ran; the fork's I6 pass flew clean that night ("896 is flown and good") but the draft is **HELD through the PR freeze below** (DM call — #896 was opened the same day the freeze was learned, so it stays a quiet draft until the freeze lifts; un-draft on a fresh explicit call then). **The 2026-07-20 QOL carve wave** (the DM's "ship the objective improvements back" call) opened six more drafts in one session: Dog Ear SHORAD #887, F-14A-Early payload #889, squadron-config guard #890, blue-block markers #891 (the upstream sweep found **465** dropped markers across 9 campaigns — Normandy's authored blue defenses dominate, flagged as a maintainer judgment call in the PR), the #791 refresh #892, and §60 radar redundancy #893 (stacked on #892, rationale attached). **#891 self-closed on review the same day**: Starfire13's density reaction ("352 EWRs in Normandy. Good lord…") plus the real ask — **CJTF block-convention consistency** ("for some objects you can only use one, yet for others both are acceptable"); the fork answered the ask same day (the loader's last single-block classes now chain both blocks — 3 shipped red-block factories resurrected, `test_miz_marker_binding.py`) but the **re-carve was DROPPED 2026-08-05** — the Custom-campaigns wiki's block spec table and upstream's loader already agree on all 19 classes, so there is no bug to carve (inventory item 17). Also learned in that session: **#791 closed with zero comments** (never reviewed — hence the refresh) and **#851 closed on a real objection** (juanjux: HDS Ultimate Compilation is NOT backward-compatible with Auranis HighDigitSAMs 2.1.0, which he runs — the S-300 renames collide; a re-carve must first answer which successor mod upstream standardizes on). **Held re-carve draft prepared 2026-07-20** — [docs/dev/414th-hds-recarve-draft.md](docs/dev/414th-hds-recarve-draft.md) (leads with UC-as-successor + migration note, offers the dual-toggle fallback; gated on the PR freeze lifting AND a fresh post-mod-update export). **Three fork PRs merged upstream 2026-07-19** (#805/#843/#854) and geofffranks' #859 (the §56 motorpool source) landed the same day — all four reconciled back into the fork in the `sync/upstream-dev-2026-07-19` merge. Same day, Wave 3 opened: the Splash Damage defaults PR #880 pushed (item 21, the first last-mile carve), the VWV v3.2.0 update #881 pushed (item 22), the §76 paradrop carve #884 opened (un-drafted late that evening + Starfire13 pinged for review), the **infrastructure pair #882 (Lua plugin harness) + #883 (MIST 51-symbol shim, stacked on #882)** opened as drafts, #828 was rebased — briefly un-drafted, then deliberately re-drafted minutes later (21:36→21:40Z per the PR timeline), so it sits as a draft with the un-draft call open — and the night closed with **two more last-mile carves: the §75 victory-conditions core as draft #885 and the Iran-pack re-carve (the #784 redo) as draft #886**. Still re-verify with `gh` before acting; this goes stale fast.

**Sync 2026-07-26 — upstream dev @ `e9b2387e`** (merge base moved `acf02b75` → `e9b2387e`; fork PR
[414Ret#726](https://github.com/BradySox/414Ret/pull/726)). Upstream shipped 12 commits over the
weekend, which reads like the beta release the PR freeze was waiting on — **re-verify whether the
freeze has lifted before pushing anything new** (the held items are listed under the freeze banner
below). Landed: **#904** DCS 2.9.28.26283 (pydcs pin, F-14B(U) module + 10 squadron presets +
payload, beacons, Syria landmap) · **#899 + #895** motorpool placement/planning (§56) · **#910**
EWR + motor-pool campaign pass and the new `operation_desert_trident` · **#911** faction updates for
F-14B(U) · **#908** campaign filter/sort · **#909** F-14A export loadout location · **#905** broken
Kola beacons · **#898** captive AIM-9M clsids · **#903** forum URL. **Our #889 merged** (see Merged
below). Where upstream had solved something the fork also touched, the fork **took upstream's shape**
— the campaign filter/sort framework (our era shell became a criterion inside it), the
velvet_thunder EWR miz (their 3 authored sites over our 1), the faction EWR restructure (borrowed
Flat Face/Tin Shield/Hawk search radars → dedicated `EWR 1L13`/`55G6`/`AN-FPS-117`, applied
semantically so fork-only units like `EWR P-14 Tall King` survive), the F-14A export preset, and the
captive-AIM-9M removal. Fork positions preserved: the `hercules` purge, `f111c` values, the
`[CH] B-21` → `B-1B Lancer` substitution, the §50 supply-route blocks, and our `_target_waypoints`
refactor (which already carried #895's `if targets:` fix, with the empty-list case documented).
**UH-60L un-cut** from `CUT_MOD_AIRCRAFT` (DM call): upstream standardizes on it across a dozen
campaigns + the new faction, and the fork's `uh_60l` ModSetting already ejects it in a mods-off game
— the same mod-with-fallback design the guard's docstring exempts. **New carve candidate:** upstream's
`F-14A-95-GR` + `F-14BU` payload files name a preset `"Retribution Fighter Sweep"`, but the loader
matches `FlightType.value` casing exactly (`Fighter sweep`), so both jets silently fly a fallback
loadout — fixed fork-side, worth carving back once the freeze lifts. **Line-ending gotcha for the
next sync:** base and upstream ship the campaign/faction files CRLF while the fork normalized them to
LF, so ~36 of them conflict as *whole files*; re-running `git merge-file` on `tr -d '\r'`-normalized
stages cuts that to 1–2 real hunks each.)

**⛔ UPSTREAM PR FREEZE — STILL IN FORCE, CONFIRMED BY THE DM 2026-08-05 ("its not lifted yet. Beta branch soon"):** dcs-retribution is accepting **no NEW PRs until their next beta release**; **updating existing PRs is fine** (merging current upstream into an open PR branch, pushing review fixes, and re-requesting review are all allowed and were exercised on all 13 open PRs on 2026-08-05). **Do NOT infer the lift from upstream activity** — that mistake was made twice: the 2026-07-26 sync read 12 weekend commits as "the release the freeze was waiting on", and the 2026-08-05 sync read another 36 commits (incl. their merge of our #889) the same way. Neither was the release. The observable facts as of 2026-08-05: **the newest published release is still v1.5.0 (2026-04-13)**, and the `test/1.6` branch was cut but its tip has not moved since **2026-07-25** while `dev` kept merging through 08-04. **Only the DM lifts this**, on word from upstream — never a `gh`/commit-activity inference. Holds until it lifts: the **HDS re-carve** (held draft prepared — [docs/dev/414th-hds-recarve-draft.md](docs/dev/414th-hds-recarve-draft.md); data re-verified post-mod-update, numbers hold — note that draft carries a SECOND gate of its own, and the real blocker is a *decision* upstream must make: which HDS successor mod they standardize on, since #851 died on a user running Auranis 2.1.0), the pydcs exporter-hardening PR candidate, and the `Retribution Fighter sweep` payload-casing fix from the 07-26 sync. **#896 is NOT on this list** — it is an *existing* open PR (never a draft; the earlier "un-draft #896" note was wrong): Druss99's 07-31 request-changes was answered in full the same day (`6dea2efa`, operator tables dropped), a re-review is **already pending on him**, and the standing `CHANGES_REQUESTED` decision is just the stale flag from that review, which clears only when he submits a new one. Nothing is owed on it. **The post-mod-update queue COMPLETED 2026-07-20 evening** (re-dump run; every export file parsed clean on the hardened exporter): extensions verified 386/386 pre-migration, **HDS unchanged** (the re-carve draft's numbers hold), and the update wave surfaced the real story — **ED has integrated CurrentHill units into base DCS** (`CoreMods/tech/Currenthill Assets Pack`, the `CHAP_*` ids; pydcs pin + 21 fork CHAP yamls already carry them) while the CH 1.5.0 packs renamed their remaining ids to `CH_`/dropped the ED-integrated ones. The fork migrated: Sweden 30 id renames + UK Type45/SkySabre + Ukraine BTR-4/MiG-29MU2/Su-24MU (extension ids + yaml filenames + LvS-103/Sky-Sabre layout refs + eject strings), 6 vanilla-superseded registrations retired (both Ukraine tanks, Scimitar/Scorpion re-pointed in blufor_current to the vanilla CHAP variants), and the **Ukraine pack was discovered double-nested in Saved Games (never loaded — fixed)**; its units export-verify on the next natural dump. The wave's adoption audit lives in [docs/dev/414th-ch-wave-adoption-backlog.md](docs/dev/414th-ch-wave-adoption-backlog.md): ~98 % already adopted (the extensions had tracked newer pack versions all along; every new AD system rides a factioned preset group) — **4 units genuinely open** (TigerUHT yaml, the B-21 faction call, the 2 Project 22160 hulls).

Carved out of this work, against `dcs-retribution/dcs-retribution` (all authored by `BradySox` — the renamed `bradyccox` account):

- **Open (awaiting review):**
  - [#896](https://github.com/dcs-retribution/dcs-retribution/pull/896) surface the squadron country — campaign yaml `country:` pin + Air Wing dialog selector (**draft**, opened 2026-07-20 on dev @ `3760cf2a`) — §23's surfacing follow-on (inventory item 26), answering that day's upstream Discord ask verbatim (Starfire: preset-for-the-nation-if-available-else-generated-set-to-it; Toad: dropdown under Livery): `SquadronConfig.country` → same-nation-only preset pick with def-generator fallthrough + `override_squadron_defaults` stamp, the `SquadronCountrySelector` (live-write, faithful mod-country display), preset dropdowns showing each preset's nation, Save/Load Config country round-trip, and the bind_data livery stale-squadron re-point fix. Upstream carries the 9 game-side tests; the offscreen-Qt selector test + the DS `country: USA` pins stay fork-side. 453 tests / black / mypy green. **I6 VERIFIED 2026-07-20** ("896 is flown and good"). **Druss99 request-changes 2026-07-31** — the operator tables are "a massive burden when adding a new aircraft module"; capitulated fully (DM call): `game/dcs/operatorcountries.py` + the operator-derived unpinned-CJTF default removed (fork + carve), the selector shows the full country list, and an unknown `country:` aborts New Game instead of degrading, reducing the PR to "yaml country pin, no default-behavior change." Fork side = branch `claude/pr-896-review-8kg5xf`; the carve still needs the same trim applied + re-request review.
  - [#893](https://github.com/dcs-retribution/dcs-retribution/pull/893) SAM guidance-radar redundancy (**draft**, opened 2026-07-20, **stacked on #892**) — §60 carried upstream with the realism-notes rationale spelled out in the body (a balance call, not TO&E; the regiment-model tension + "park it if you'd rather keep stock single-radar" offered explicitly): 21 layout yamls `unit_count` 1→2 across 23 slots + the 5 shared templates grafted a second radar position (45–121 m offsets, structurally copied from the fork's templates — the fork-only P-14 "EW Radar" groups deliberately NOT carried) + the 29-pair lockstep test (SAMP/T row dropped — HDS-Ultimate-only). 467 tests green.
  - [#892](https://github.com/dcs-retribution/dcs-retribution/pull/892) SAM site layout variety + EWR radar pool (**draft**, opened 2026-07-20) — the **refresh of #791**, which closed with zero comments (never reviewed): the June branch rebased onto dev @ `acf02b75` with zero conflicts, content unchanged, re-validated same day (68 preset groups load; all 131 factions resolve with 0 bad preset refs; 438 tests).
  - [#890](https://github.com/dcs-retribution/dcs-retribution/pull/890) squadron `aircraft:` empty-key New Game crash guard (**draft**, opened 2026-07-20) — inventory item 12, honestly re-pitched: current upstream campaigns no longer ship the pattern (the item's "two campaigns unplayable" claim was stale — upstream's Northern Guardian Transport squadron has since been filled in; the fork hit the crash when its mod purge emptied the key), so the PR sells it as the defensive guard it is (`data.get("aircraft") or []`; iterating None at defaultsquadronassigner.py:61 kills New Game).
  - [#887](https://github.com/dcs-retribution/dcs-retribution/pull/887) Soviet SHORAD Sborka "Dog Ear" acquisition radar (**draft**, opened 2026-07-20) — the fork's evolved slot-gated + marker-gated implementation (`_add_dog_ear_if_needed` in both `for_layout` + the preset loader, the SHORAD.yaml Search Radar slot, the 3-way test incl. the SAM-site/era exclusions); vanilla unit, no faction edits. Was never in the inventory queue — added as item 23.
  - [#886](https://github.com/dcs-retribution/dcs-retribution/pull/886) CurrentHill Iran Military Assets pack + `[CH] Iran 2020` faction (**draft**, opened late 2026-07-19) — the clean minimal redo of self-withdrawn #784 (that early upload was a monolith dragging in the C-130J plugin/QRA planner/scramble scripts): `pydcs_extensions/iranmilitaryassetspack` (Shahed 136 LM + the 2 IRGCN FACs) + the faction + the `iranmilitaryassetspack` ModSettings toggle/wizard checkbox + the FAC ship-radar registry entries + 3 unit yamls, nothing else — the exact pattern of the six CH packs upstream already carries. Headless probe on upstream dev: 20/20 aircraft / 10/10 preset groups / 6/6 naval / 2/2 missiles / 9/9 AD resolve; mod-off strip verified both ways. 438 tests / mypy / black green. **Export verification CLOSED 2026-07-20** (Druss99's export-provenance ask, same as #881): the wiki's `pydcs_export.lua` process was ACTUALLY RUN on the DM's install (CH Iran 2.0.0 loaded) — it caught `IranFAC_MG_AShM` threat/awd registered 25000 where the live DB says **1800** (the 25000 was `WS.maxTargetDetectionRange` conflated into the AA threat fields; 14× inflated ring), fixed on the branch (`9dffedff`, fork mirrored); `CH_Shahed136` + `IranFAC_MG` verify clean — 3/3 match. Reply posted in-thread with the verdict.
  - [#885](https://github.com/dcs-retribution/dcs-retribution/pull/885) custom victory conditions — **CLOSED-CEDED 2026-07-20, no longer open** (was: draft opened late 2026-07-19 carrying §75's generic core — `game/victory.py` minus the meter fields/negotiation absorption/SITREP surfaces, the `check_win_loss` branch, the two knobs, 28 ported tests). Druss99: "I have a local branch for this already so if you don't mind I'll be taking this one" — the DM closed the PR and handed the feature over the same morning. NOT a rejection, NOT a re-carve candidate: fork §75 is unaffected (B29 app pass still owed fork-side), and when Druss99's implementation lands upstream it becomes a **reconcile-on-merge / drift-watch** item vs the fork's shape.
  - [#884](https://github.com/dcs-retribution/dcs-retribution/pull/884) fixed-wing air assault by CTLD paradrop (opened 2026-07-19, **un-drafted late that evening** + Starfire13 pinged for review) — §76's generic core: the cabin-based planner gate (subsumes `is_hercules`; the Hercules keeps its initial-point ingress + gains a layout-shape pin), the `ctld-config.lua` drop runtime (airborne "Unload / Extract Troops" = jump, descent-delayed ground spawn, AI one-shot zone release, 3,000 ft player ceiling), the preload retry, and `Air Assault: 40` on the C-130J-30 yaml. The fork's lupa-harness runtime test stays fork-side (upstream has no lua harness); the §2 EW deny-list hunk is fork-only. On dev @ `acf02b75`; pytest/Black/mypy green. Fork side = [414Ret#681](https://github.com/BradySox/414Ret/pull/681).
  - [#883](https://github.com/dcs-retribution/dcs-retribution/pull/883) replace MIST with a tested 51-symbol compatibility shim (**draft**, opened 2026-07-19, **stacked on #882** — review the shim commit with/after the harness) — the fork's MIST retirement carried upstream: `mist_moose_shim.lua` extended with the eleven symbols only upstream's extra consumers call (dismounts `getGroupPoints`/`marker.remove`, EW-jammer pitch/roll/`makeVec3GL`, EWRS speed conversions, and the Pretense teleport/respawn family — **new implementations validated by the harness, never fork-flown**, since the fork ran no Pretense: the in-game watch item), `mist_4_5_126.lua` deleted, consumers byte-unchanged, one-line rollback. Bonus: the DB tier rebuilds on debounced BIRTH + a 30 s fallback instead of MIST's whole-mission poll. 462 tests green.
  - [#882](https://github.com/dcs-retribution/dcs-retribution/pull/882) headless Lua plugin test harness (**draft**, opened 2026-07-19) — the fork's `tests/lua/` lupa harness carried upstream (virtual clock with DCS reschedule semantics, recorded `trigger.action`/controller/spawn side effects, populated-world + weapon fakes, a minimal MOOSE facade, file-scope/tick/handler error capture; runs inside plain `pytest tests`, zero workflow changes). First consumer: Splash Damage 3 runtime pins (load + tracking start, the percent-normalization contract, track-to-impact, unknown-weapon ignore; power *values* deliberately unpinned while #880 is discussed). **The enabler for the Wave-5 Lua-feature carves.**
  - [#881](https://github.com/dcs-retribution/dcs-retribution/pull/881) Vietnam War Vessels support → v3.2.0 (inventory item 22, opened 2026-07-19) — upstream's VWV support was frozen at v3.0.0: registers the 3.1.0 Sampans ×5 + Junk civilian craft and the 5 never-registered hulls (Radford / Epperson / Everett F. Larson / Solon Turman / USNS Card; ids from the installed mod's own `Database/Navy/*.lua`), adds all 11 to the `faction.py` eject list, and bumps the wizard label + 4 stale faction `requirements` versions to v3.2.0. Registration-only parity with the fork (no unit yamls/prices — the fork hasn't authored them either). On dev @ `acf02b75`; pytest/Black/mypy green. Fork reconciled same day (same eject entries + its own 4 stale faction strings). **Review response 2026-07-20** (Druss99 asked whether the extension came from a pydcs export — the annotation comments read as AI-generated): comments stripped to exporter style, and the re-verification of all 11 hulls against the mod's public source (`tspindler-cms/tetet-vwv` @ tag `VWV_3.2.0`) caught that the removed **USNS Card** comment was WRONG — `Database/Navy/Card.lua` defines `airFindDist 45000` / `airWeaponDist 18650` (keeps a 5"/38 battery), so Card is now 45000/18650/18650 and Solon Turman carries explicit 15000/0/0 (branch commit `534fbd7`; fork mirrored the same fix). **Export verification CLOSED 2026-07-20**: the wiki's `pydcs_export.lua` process was ACTUALLY RUN on the DM's install (full VWV 3.2.0 fleet loaded; runbook + heavy-mod exporter gotchas in `tools/verify_mod_export.py`'s docstring — the stock exporter crashed twice on 50-mod data and needed nil-guards/pcall hardening, patched copy at `C:\Users\brady\dcs-export\pydcs_export.lua`, pydcs-PR candidate) and it FALSIFIED the tag-source reading: `Solon_Turman.lua` sets `GT.airWeaponDist = 13000` (not unarmed — Turman fixed 0→13000/13000), BHR `plane_num` is 40 (not 8), and 3.2.0 superseded the plain Maddox module with the Tonkin Incident module (id **`USS Maddox T`** — registered additively + eject-listed; The Sullivans left the 3.2.0 distribution entirely, legacy entries kept for old installs). All on the branch (`2ffa9057`, fork mirrored); Card's 45000/18650/18650 export-CONFIRMED; 120/124 registered VWV units match field-for-field (residual: 2 pre-existing cosmetic drifts, aligned fork-side). Reply posted in-thread. **The follow-on fork-wide sweep** (unfiltered `verify_mod_export.py` over every installed mod) then aligned ALL 363 registered units of every extension to the live export — 93 drifted (HDS NATO-name restyle + sensor retunes incl. SA-17 TELAR detection 120→18.5 km, CH UK renames/retunes, IDF SAM ranges, and the `oh6_vietnamassetpack` duplicate VAP registrations whose stale values silently raced `vietnamwarvessels`' at pydcs-injection time — values now agree; module retirement deferred for save-compat) — fork commits `1345a4002` + `2621d695c`; the §63 LACM hull-id audit came back clean (CH Russia Kalibr trio verified; the 4 CH USA ids target a newer pack than installed, no faction fields them).
  - [#874](https://github.com/dcs-retribution/dcs-retribution/pull/874) curated carrier comms (**draft**) — §65 verbatim (per-hull boat cards feeding the DCS-rendered CV Operations Data page: hull-number TACAN + boat ident with `alloc_near` nearest-neighbor degrade, hull-keyed ICLS via a shared `IclsAllocator`, 336-band Link 4, stable persisted ATC, flagship named by hull name). NO fork couplings; the port adds only the Pretense allocator-type adaptation (behavior untouched). On dev @ `ef576acc`; pytest/Black/mypy green — opened 2026-07-16. Fork side = [414Ret#611](https://github.com/bradyccox/414Ret/pull/611). See upstreaming-inventory item 19.
  - [#873](https://github.com/dcs-retribution/dcs-retribution/pull/873) culling: keep scenery-objective kill tracking in culled regions (**draft**) — opened 2026-07-16; `MERGEABLE`. (Added by the 2026-07-16 live refresh; it had never been recorded here. Fork-side context not yet written up.)
  - [#872](https://github.com/dcs-retribution/dcs-retribution/pull/872) ship-launched cruise missile strikes — generic core of fork [414Ret#599](https://github.com/bradyccox/414Ret/pull/599) (Tomahawk/Kalibr shore attack: F10 call-for-fire with marker-text salvo sizing, optional auto raids, persisted no-rearm magazine via the `cruise_missiles_state` debrief channel). **Ready for review 2026-07-19**: the branch carries the review-feedback stagger + un-cull + carrier-escort commits, a current-dev merge, and the flown **defender launch wake** ported from the fork (alarm-RED near the aimpoint for the missile flight window; Skynet-adapted comments) — un-drafted after the DM's local 10/10 fly. See upstreaming-inventory item 18.
  - [#880](https://github.com/dcs-retribution/dcs-retribution/pull/880) Splash Damage coherent field-tuned defaults (inventory item 21, opened 2026-07-19) — fixes upstream's broken percent plumbing (the "(%)" rocket spinner applied raw ×130; overall_scaling 3 = 3% with a second ÷100 in the bomblet path; test mode shipped enabled) and sets the 414th's flown values (60%/80%/static 1/radius 100%/wave ×2, big-iron explTable trims, shaped_charge flags on the 4 HEAT/AP rockets) in upstream's own plugin.json→sd3-config architecture. Plugin stays default-OFF upstream.
  - [#828](https://github.com/dcs-retribution/dcs-retribution/pull/828) recon fog-of-war (§3) — the flagship carve. **Rebased 2026-07-19**: squashed to one commit on dev @ `acf02b75`, re-validated (upstream pytest 451 passed; the new ship-movement test double gained the `game.settings` chain `known_for` reads), `MERGEABLE`. Briefly un-drafted, then **deliberately re-drafted the same evening** (21:36→21:40Z per the PR timeline) — currently a **draft**; un-draft when ready.
  - [#806](https://github.com/dcs-retribution/dcs-retribution/pull/806) configurable cruise/patrol altitude.
  - [#794](https://github.com/dcs-retribution/dcs-retribution/pull/794) hide mobile SAM in combined groups (§7).
  - [#792](https://github.com/dcs-retribution/dcs-retribution/pull/792) wind override UI.
  - [#788](https://github.com/dcs-retribution/dcs-retribution/pull/788) inflight final-waypoint crash (§8).
- **Merged (9):**
  - **2026-07-25:** [#889](https://github.com/dcs-retribution/dcs-retribution/pull/889) F-14A-135-GR-Early payload `unitType` fix (inventory item 20) — the Early Tomcat flew every tasking unarmed because the payload file declared the base `F-14A-135-GR`, and pydcs keys payload files by that field. Upstream merged the one-liner + the changelog note; the **guard test stayed fork-side** (`tests/test_f14_loadouts.py`), and the fork's copy additionally carries the 414th "Retribution TARPS" fit, so the two are convergent on the fix but not byte-identical. Reconciled in the 2026-07-26 sync.
  - **2026-07-19 (the contributor wave — all three reconciled into the fork by the same-day sync merge):**
    [#854](https://github.com/dcs-retribution/dcs-retribution/pull/854) per-squadron DCS country + nation-aware pilot names (§23; resolves upstream issue #627 — upstream's merged copy added `blue_country_ids`/`red_country_ids` helpers, adopted fork-side) ·
    [#843](https://github.com/dcs-retribution/dcs-retribution/pull/843) era-gate payload-editor options / JHMCS helmet cueing (§24 — **upstream merged the fork's final shape**: `date_gated_properties` blocks in the aircraft yamls + `restrict_props_by_date`, NOT the interim helmet-yaml layout from Druss99's first review; the two sides are byte-convergent. ⚠️ upstream's copy of the 4 aircraft yamls froze a **2026-06-29 snapshot of the fork's task priorities** that the rebalance rubric has since re-tuned — flagged for an upstream data-cleanup PR) ·
    [#805](https://github.com/dcs-retribution/dcs-retribution/pull/805) bulk waypoint altitude UI (upstream's merged version carries the full Druss99 skip-list — `DIVERT`/`CARGO_STOP`/target/pickup/dropoff/`REFUEL`/`RECOVERY_TANKER`; the fork's pre-review copy was upgraded to it in the sync).
  - **Earlier:** [#871](https://github.com/dcs-retribution/dcs-retribution/pull/871) targeting-pod era data (merged 2026-07-15) · [#841](https://github.com/dcs-retribution/dcs-retribution/pull/841) plugin `descriptionInUI` field (§14) · [#793](https://github.com/dcs-retribution/dcs-retribution/pull/793) building-card placeholder (§4) · [#826](https://github.com/dcs-retribution/dcs-retribution/pull/826) weapons coverage/repairs · [#789](https://github.com/dcs-retribution/dcs-retribution/pull/789) inverted OPFOR aggressiveness fix.
  - Also relevant: geofffranks' [#859](https://github.com/dcs-retribution/dcs-retribution/pull/859) motorpool depots merged 2026-07-19 — the fork pre-adopted it as §56 (+ the #625 drift port), and the sync brought the final extras (the `AttackMotorpools` HTN task, wired into the fork's offensive-emphasis lists; capture-zone warning already ported).
- **Closed unmerged — NEWLY CLOSED since the 2026-06-27 snapshot (⚠️ the ledger had all four listed as "open, awaiting review"; the *reason* each closed was NOT investigated — check the PR before re-carving):**
  - [#851](https://github.com/dcs-retribution/dcs-retribution/pull/851) High Digit SAMs **Ultimate Compilation** support (§41's generic core) — retargets the HDS toggle to the maintained mod: renamed-radar re-points, retired-unit tombstones, the 42 new units + 7 presets + SAMP/T layout, and the `remove_vehicle` id-vs-name strip fix. NO 414th faction enrichment (P-37/SA-7/S-400 wiring stays fork-side). Opened 2026-07-01. Landed on the fork as [414Ret#382](https://github.com/bradyccox/414Ret/pull/382), so the fork keeps it either way.
  - [#847](https://github.com/dcs-retribution/dcs-retribution/pull/847) F-4E-45MC (Heatblur) loadout rebuild **+** Maverick date-fallback fix (period AIM-7E2/9L baseline; AGM-65 date-fallback rerouted Walleye → Mk-20 Rockeye). Opened 2026-06-28; **consolidated the former #845 + #846** (both also closed). Landed on the fork as [414Ret#322](https://github.com/bradyccox/414Ret/pull/322) + [#325](https://github.com/bradyccox/414Ret/pull/325).
  - [#842](https://github.com/dcs-retribution/dcs-retribution/pull/842) landmap prepared-index perf (carve queue item 1) — opened 2026-06-27.
  - [#791](https://github.com/dcs-retribution/dcs-retribution/pull/791) SAM site layouts + EWR pool.
- **Self-withdrawn (NOT rejected, NOT upstream):** [#784](https://github.com/dcs-retribution/dcs-retribution/pull/784) Iran pack (**re-carved clean as draft #886, late 2026-07-19**) · [#786](https://github.com/dcs-retribution/dcs-retribution/pull/786) AAQ-33 era restriction (folded into the merged #843) · [#790](https://github.com/dcs-retribution/dcs-retribution/pull/790) orbit deconfliction (still fork-only — re-carve if wanted) · [#891](https://github.com/dcs-retribution/dcs-retribution/pull/891) blue-block miz markers (**closed by the DM 2026-07-20, 25 min after Starfire13's review** — "352 EWRs in Normandy. Good lord…" made the 443-marker Normandy resurrection a non-starter, and the comment's real ask was **CJTF block-convention consistency** across object classes ("SAMs have to be defined with CJTF Red, but AAA and static armour groups allow both"). The fork implemented the full consistency rule same day — every loader class reads both blocks; `factories` was the remaining silent-drop hole with 3 shipped red-block factories resurrected. **The re-carve was DROPPED 2026-08-05 (DM call) on a finding that invalidates its premise:** the Custom-campaigns wiki carries a **"Unit Type Quick Reference" spec table assigning a required CJTF block per object class**, and upstream's loader matches it **exactly on all 19 classes** (Red: EWR/all 3 SAM ranges/ship/missile/coastal/offshore/neutral-FOB · Blue: factory · Either: AAA/armor/ammo/strike/comms/power/command-center/FOB). So nothing is "silently dropped" — a blue-block SAM marker is dropped because the author placed it in the block the documentation forbids, and the fork's read-both-blocks rule is a **deliberate deviation from a documented upstream spec**, not a bugfix. Making it a carve would be a *spec change* (uniform "Either" + a wiki edit), which is a maintainer design call and was not worth pursuing. See inventory item 17).
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
`sd3-config.lua` was removed. Don't reintroduce the config layer. (The *values* are an
upstream candidate — inventory item 21, 2026-07-19 policy: upstream's stock defaults damage
buildings ~a mile out, so ship ours back as their new defaults with the rationale. That PR
edits upstream's own config; this pinned file and its locked packaging stay fork-side either
way.)

---

## Conventions

- **ADHD-friendly agent output (STANDARD, 2026-07-20).** The reader has ADHD; every agent
  reply is shaped so an ADHD brain can act on it. The rules live in the vendored
  [`i-have-adhd`](https://github.com/ayghri/i-have-adhd) skill
  (`.claude/skills/i-have-adhd/SKILL.md`, MIT, byte-identical to upstream — update by
  re-copying upstream's `skills/i-have-adhd/SKILL.md`; keep the sibling `LICENSE`). Treat it
  as **always-on**, not invoke-on-request: lead with the next action, number multi-step work,
  end with one concrete next action, defer tangents, restate state each turn ("step 3 of 5"),
  concrete time estimates, visible wins, matter-of-fact errors, lists capped at 5, no
  preamble/recap/closing pleasantries. The skill's own exceptions apply (full explanations
  when asked, confirm destructive actions, stop iterating in a debug spiral, one clarifying
  question on real ambiguity). Composes with the question convention below: a needed decision
  still lands in the ❓ block at the end — that block IS the "one concrete next action."
- **Ask decisions via the AskUserQuestion widget (STANDARD, 2026-07-21 user call).** Whenever
  you need a decision or a choice from the user, use the **`AskUserQuestion` tool** — the
  interactive widget with clickable options — **not** a typed "1, 2, 3" list. Lead with your
  recommended option and mark it "(Recommended)"; give each option a one-line description of what
  it means / its trade-off. Use `multiSelect` when the choices aren't mutually exclusive, and a
  short set of questions (≤4) when several independent decisions are on the table. The user
  considers typed numbered option lists low-effort ("lazy") — the widget is the actual tool for
  this, so default to it.
  - **Fallback — plain highlighted markdown** — only for a quick inline either/or where the widget
    is overkill, or for a **free-text** question with no fixed options. Never bury it mid-paragraph
    or at the tail of a wall of prose: put it in its own block at the **end** of the message, set
    off with a bold marker + blockquote, and lead with your recommended option, e.g.:
    > ❓ **Need your call:** <the question>
  - Do NOT build a custom widget/visualization (`mcp__visualize`, an Artifact) to ask a question —
    `AskUserQuestion` is the one decision surface.
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
- **Upstream dev-process standards (ADOPTED as ours, 2026-07-20 user call).** The upstream wiki's
  Contributing + Core development guides are the fork's own customs and standards, mirrored with
  **414th:** delta notes in `docs/wiki/` (see Project Docs). In practice: follow the
  **Developer's Guide** for dev-env + PR practice (small PRs — one feature/bugfix/change per PR;
  type annotations on all new code; pre-commit runs Black), the **aircraft/terrain module
  checklists** (upstream's P0–P2 items plus the fork's additions on each page) when adding module
  support, the **QGIS shapefile guide** for landmap data, **Modded-Unit-Support** (the 11-step
  guide) for any new mod pack, **Motorpools** when authoring reserve depots into a campaign,
  **Campaign maintenance** for the campaign-ownership model (every fork-authored campaign is
  owned: design note + CI lock), and the **Release process** page for releases (the rolling
  `latest` IS the release; pinned tags are `v<X.Y.Z>-414th`; never `git push --tags`).
  **Upstream carves ship to these same standards** — they are upstream's own, so a carve is held
  to them by construction: target `dcs-retribution/dev` via the PR fork, one focused
  feature/bugfix per PR, upstream's gates validated locally on the upstream tree before push, a
  `changelog.md` note, fork-only couplings stripped (the harness/plugin extras stay here), and
  module/campaign content meeting the relevant checklist page. When an upstream page changes,
  refresh the mirror and re-annotate the deltas rather than letting the two drift.
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
