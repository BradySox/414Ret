# The Tanker War (1988) — campaign design notes

**Status: Phases 1 + 2 + 3 BUILT & headless-VERIFIED (2026-07-07).** `resources/campaigns/tanker_war_1988.yaml`
+ `.miz` generate a full turn-0 game with the period air OOB, the will economy + authored phase
arc + shipping-lane ROE zone, the coastal Silkworm shoot-and-scoot, and AAA gun forts on the oil
rigs; parsers + generation clean, Black/mypy/tests green. **Registered 2026-07-18** (the
maintenance sweep found the campaign shipped silent — laydown guard
`tests/fourteenth/test_tanker_war.py`, README + CLAUDE.md design-notes entries, checklist row
T2 all in). Remaining: the in-game pass (esp. the platform-AAA on-deck render) +
will-weight/ROE-corridor tuning. NOTE (§49 interaction, 2026-07-17): vanilla Silkworm hardware
(`hy_launcher`/`Silkworm_SR`) is a fixed emplacement and is never routed (`IMMOBILE_UNIT_IDS`)
— the batteries fire their fire-window missions but do not scoot; only genuinely mobile
coastal launchers move. See the Build log (§8–§10).
Decisions locked:

- **Framing:** the broader **Tanker War (1987–88)** as a multi-turn attrition arc that
  *builds to* an **Operation Praying Mantis** climax (not the single-day battle). *(user: 1.1)*
- **Enemy scope:** **Iran + an Iraqi Exocet flavor** — historically not clean (Iran and Iraq
  were enemies), accepted as a gameplay abstraction of the two-belligerent threat to Gulf
  shipping. *(user: 2.2)*
- **Process:** **design all three phases on paper first, then build.** *(user: 3.2)*
- **Base laydown:** fork **`WRL_Operation_Noisy_Cricket_Redux`** for its Strait-of-Hormuz
  geography (see "Base laydown" below). *(user proposed; agreed)*
- **Carrier:** keep **Stennis** (accept the anachronism; Forrestal dropped). *(user: 1.2)*
- **IADS:** **keep `advanced_iads`, re-dress to period** — which is *nearly free*: the placed
  SAMs are band markers filled from the faction, so re-factioning auto-periodizes them; only the
  ~4 long-range (S-300) markers need attention (`iran_1988` has no long SAM). *(user: 2.2)*
- **Oil-platform gun forts:** **in scope for the first build** (the 15 platforms are already
  placed in the miz). *(user: 3.2)*
- **Name:** ***"Persian Gulf — The Tanker War (1988)"***. *(user: 4.1)*
- **Factions:** use the **existing** `usn_1985` / `iran_1988` / `iraq_1991`; only *add* a unit
  to a faction if something is genuinely missing (don't author new factions). *(user)*

**Open decisions still owed** — flagged inline with ❓ and collected at the end.

---

## 1. Concept

The 1987–88 "Tanker War" phase of the Iran–Iraq War, when attacks on Gulf shipping drew the
US Navy into direct combat with Iran, culminating in **Operation Praying Mantis (18 Apr 1988)**
— the largest US surface engagement since WWII, fought right in the central Gulf / Strait of
Hormuz among the Iranian islands and oil platforms.

The player flies the **US Navy carrier air wing of 1988** (F-14A, A-6, A-7, EA-6B, E-2C, S-3)
protecting Gulf shipping and grinding down Iranian naval + coastal power. The decisive currency
is **ships, not territory** — this is the campaign that finally headlines the fork's dormant
**warship will-feed** (`blue_ship_lost` / `red_ship_lost`).

Why this map/era is special: the Persian Gulf is the **only DCS theater where the F-14 Tomcat
can be flown historically on both sides** — US Navy VF squadrons *and* the IRIAF's "Persian
Cats." The period factions already exist and are historically on-point (see §3).

---

## 2. Base laydown — why Redux

Three PG naval candidates were compared (`scenic_route`, `operation_noisy_cricket`,
`WRL_Operation_Noisy_Cricket_Redux`). **Redux wins on geography**, which is the one thing that
is expensive to change after the fact:

| | scenic_route | Noisy Cricket | **Redux** |
|---|---|---|---|
| Lines / richness | 146, light | 218 | **445, richest** |
| Blue basing | CVN + LHA only | CV + land | **CV + LHA + real GCC land (Khasab, Al Dhafra, Al Minhad)** |
| Strait geography | vague coastal + generic FOBs | Abu Musa/Qeshm/Bandar Abbas | **Abu Musa / Qeshm / Gt. Tunb / Bandar Abbas / Kish — the exact Praying Mantis box** |
| IADS | simple modern | modern | advanced_iads placed network + C2 graph |
| §50 supply corridors | none | authored | authored |

Khasab (Musandam) is the literal mouth of the Strait where US forces staged; Abu Musa & the
Tunbs are the IRGC islands; Bandar Abbas is Iran's real naval HQ. The Sassan/Sirri/Nasr oil
platforms (the Praying Mantis targets) sit among those islands. This is irreplaceable and is
why Redux beats the lighter, vaguer bases despite more re-dress work.

**How the `.miz` actually works — band markers, not literal systems** (verified in
`game/campaignloader/mizcampaignloader.py`, constants at L44–115 + classifiers at L200–260, NOT
the wiki summary I first misread). A campaign `.miz`'s placed groups are a **fixed vocabulary of
markers**: the loader classifies each group by `units[0].type` into a band/category, records its
**position** as a `PresetLocation`, and the ground generator **fills the actual system from the
faction roster** at turn zero. **The placed unit type sets the band + position, NOT the weapon
that spawns.** The canonical markers (loader constants):

| Marker `type` in the miz | Band / category | Fills from |
|---|---|---|
| `S-300PS 5P85C/D ln`, `Patriot ln` | **long-range SAM** | faction long-range roster |
| `Hawk ln`, `S-75` (SA-2), `S-125` (SA-3), NASAMS | **medium-range SAM** | faction medium roster |
| `rapier_fsa_launcher`, `2S6 Tunguska`, Avenger, Strela | **short-range SAM** | faction short roster |
| `flak18`, `Vulcan`, `ZSU-23-4 Shilka` | **AAA** | faction AAA |
| `1L13 EWR` | **EWR** | faction EWR |
| `Scud_B` | **missile site** (the §49 category) | faction missiles |
| `hy_launcher` (Silkworm) | **coastal defense** | faction coastal |
| `USS_Arleigh_Burke_IIa` | **ship** (red naval site) | faction naval roster |
| `Oil platform` | **offshore strike target** | static objective |
| `Stennis` / `LHA_Tarawa` | **carrier / LHA** (a control point) | faction carrier names |

**Consequence: re-factioning to `usn_1985` / `iran_1988` auto-periodizes almost the whole laydown
for free.** What Redux places — `Hawk ln` ×15, `rapier_fsa_launcher` ×15, `2S6 Tunguska`,
`1L13 EWR` ×13, `hy_launcher` (Silkworm) ×7, `Scud_B` ×2, `USS_Arleigh_Burke_IIa` ×2,
`Oil platform` ×15, plus the C2 statics (`Comms tower M` ×9 / `.Command Center` ×2 /
`GeneratorF` ×2) — are **all just markers**. Under the period factions the ship markers become
Iranian frigates/boats (`iran_1988.naval_units`), the SAM markers fill with period Iranian kit,
the Tunguska marker becomes ZSU-23-4, etc. **Nothing to swap.** My earlier "swap 7 anachronistic
groups" was wrong — none of these are literal systems. Bonus: the 15 oil platforms are already
offshore-strike-target markers (the Sassan/Sirri gun-fort foundation), and the 7 Silkworm markers
are ready-made §49 shoot-and-scoot coastal sites.

**The one genuine issue (decision 2.2): the long-range SAM markers.** `long_range_sams` reads the
red `S-300PS 5P85C ln` ×4 markers, but **`iran_1988` has no long-range SAM** in its roster (top
band = HAWK medium + SA-2/3). So those 4 sites can't fill period-correctly. Options:
- **downgrade the 4 long-range markers → medium (`Hawk ln`) markers** — a naval war needs no deep
  long-SAM anyway; or
- **add a period long-range SAM to `iran_1988`** ("add if needed") — but Iran '88 fielded no
  S-200/S-300, so this is the historically wrong lever; or
- **delete the 4 markers.**
→ recommend downgrade-to-HAWK or delete. **Must verify:** what the generator does with an
unfillable long-range `PresetLocation` (graceful fallback to best-available vs. an empty site) —
that decides whether this is must-fix or merely cosmetic.

So decision 2.2 ("re-dress to period, keep `advanced_iads`") is **nearly free**: re-faction +
address ~4 long-range markers. The C2 net and everything else stays, so §51/§52 remain wired.

**Who makes that one edit.** The long-range-marker fix (and any oil-platform gun-fort AAA in
Phase 3) is a *tiny* `.miz` edit — either the **user's ME pass**, or **Claude via pydcs / zip
text-edit** if the Redux miz round-trips vanilla-safely (verify-load-save first; pydcs re-emits a
duplicate `theatre` zip member that must be stripped — see [[pydcs-miz-save-vanilla-safe]] /
[[sam-layout-editing-and-p14]]). ❓

---

## 3. Factions — all period-correct, already in the repo

| Role | Faction file | Key period assets |
|---|---|---|
| **Player** | `usn_1985` (US Navy 1985) | F-14A/B, **A-6A Intruder**, **A-7E Corsair II**, **EA-6B Prowler** (jammer), S-3B Viking (anti-ship + tanker), E-2C Hawkeye, SH-60B; ships **FFG O.H. Perry, CG Ticonderoga, LHA Tarawa**, carrier |
| **Enemy (Iran)** | `iran_1988` (Iran 1988) | F-14A, F-4C/E, F-5E, MiG-21bis, AH-1J; ships **FAC La Combattante IIa** (= Kaman/*Joshan* missile boat), corvette, frigate; AD: **HAWK, SA-2/3, P-37 EWR**, ZU-23/Shilka, Scud-B |
| **Enemy (Iraqi flavor)** | `iraq_1991` (Iraq 1991) | **Mirage F1EQ** (the real Exocet anti-ship platform — hit USS *Stark* 1987), Su-24, Tu-22M3 |

Historical resonance is high: the O.H. Perry is the class of USS *Samuel B. Roberts* (mined
14 Apr 1988 → the trigger for Praying Mantis); the La Combattante IIa is the class of the
*Joshan*, sunk by Harpoon in the real battle; the frigate stands in for *Sahand*/*Sabalan*.

**Carrier choice.** `usn_1985` lists CVN-74 Stennis (commissioned 1995 — anachronistic). The
period-correct DCS supercarrier is the **Forrestal (CV-59)** — the actual Praying Mantis-era
carrier, and a MOOSE AIRBOSS-supported type. Plan: add `Forrestal` to the faction's carrier
names and use it. **Risk:** the carrier's ship-type must be in the engine's
`runway_is_operational()` whitelist or the air group is treated as sunk/invisible (known
gotcha). **Must verify Forrestal is whitelisted before committing** — else fall back to Stennis
and accept the anachronism.

**Iraqi Exocet abstraction (decision 2.2).** Retribution is strictly 2-coalition, and Iran+Iraq
were enemies, so we can't model them as separate belligerents. Implementation: fold the Iraqi
threat into the **RED coalition as a single "anti-ship raider" squadron** — Mirage F1EQ flying
`Anti-ship`/`Strike` from a **northern red field** (Shiraz/Kerman edge), briefed as "belligerent
anti-ship strikes on Gulf shipping." Lampshaded in the campaign text as a deliberate gameplay
abstraction of the two-front tanker threat. Kept small (a detachment), so it reads as flavor,
not a second air force.

---

## 4. The three phases

### Phase 1 — playable period re-faction (fast, low-risk core)

Goal: a period-correct naval campaign that *runs* and is fun, before any 414th identity layer.

1. **Fork** `WRL_Operation_Noisy_Cricket_Redux.{yaml,miz}` → `tanker_war_1988.{yaml,miz}`
   (name e.g. *"Persian Gulf — The Tanker War (1988)"*).
2. **Re-faction** the YAML: player `US Navy 1985`, enemy `Iran 1988`. Replace the WRL custom
   Task Force factions.
3. **Re-map every squadron** to period airframes:
   - Blue CV: F-14A BARCAP/TARCAP, **A-6A** strike/anti-ship, **A-7E** BAI/CAS, **EA-6B** SEAD
     escort/jam, **E-2C** AEW&C, **S-3B** tanker + anti-ship, SH-60B transport/CSAR.
   - Blue LHA: A-4E/AV-8 → **A-7E / A-4E**, AH-1W → **AH-1** period, UH-1.
   - Red (Iran): drop anachronistic **A-50 / Su-24MK** → **F-14A / F-4E / F-5E / MiG-21bis**
     BARCAP + strike; AH-1J.
   - Red (Iraqi flavor): one **Mirage F1EQ** anti-ship detachment at the northern edge.
4. **IADS (decision 2.2):** keep `advanced_iads: true`. Re-factioning auto-periodizes the placed
   SAM/ship/EWR/coastal markers from `iran_1988`; only the ~4 long-range (S-300) markers need
   handling (downgrade to HAWK or delete — see §2). The C2 net stays, so §51/§52 remain wired.
5. **Dates / economy:** `recommended_start_date: 1988-04-18`; tune money/income so the carrier
   wing can sustain the tempo (naval campaigns are airframe-hungry).
6. **Carrier (decision 1.2):** keep **Stennis** (accept the anachronism — Forrestal dropped).

Deliverable: flyable, period-correct, no 414th layer yet.

### Phase 2 — the 414th naval-war identity

The layer that makes this *our* campaign and exercises features nothing else does.

- **Will profile (`will:` block).** Re-label the meters **US Resolve** vs **Iranian Regime
  Resolve**; weight **ship losses as the dominant currency** so the war is won/lost at sea, not
  by counting jets or taking dirt. Representative (schema to confirm against `parse_will_profile`
  at build time):
  ```yaml
  will:
    blue_label: "US Resolve"
    red_label: "Iranian Regime Resolve"
    weights:
      blue_ship_lost: 8      # a sunk US frigate/escort is a strategic event (USS Stark echo)
      red_ship_lost: 6       # sinking Iranian combatants/boats breaks Tehran's nerve
      blue_aircraft_lost: ...
      red_aircraft_lost: ...
    # exhaustion banners re-framed to the 1988 negotiation ending
  ```
  Negotiation ending (via the existing `check_win_loss` will branch): grind Iranian resolve to
  zero → Iran halts attacks on shipping (WIN); US resolve breaks first → Washington pulls the
  escort mission (LOSS). Territory victory stays as a fallback.
- **ROE restricted zone (§40): the neutral shipping lane.** A **corridor** `RestrictedZone`
  down the deep-water Strait of Hormuz shipping channel — the signature Tanker War dilemma.
  Weapons released against shipping inside it price the mandate (neutral tankers, third-party
  flags). Painted on the F10/ME + web map. This is the ROE-zone showcase.
- **Campaign-phases arc (§40).** Authored `phases:`:
  1. **Tanker War** (attrition; escort + armed recon over the shipping lanes; ROE tight).
  2. **The *Samuel B. Roberts* mining** (trigger event → target release; the gloves come off).
  3. **Praying Mantis** (retaliation; the oil-platform + naval strike is authorized).
  4. *(optional)* **Escalation / Iranian collapse.**
  `advance_when` coupled to will + turn, per the Vietnam arc precedent.

### Phase 3 — Praying Mantis signature content (needs ME work)

- **Oil-platform "gun forts"** — the Sassan (Salman) & Sirri (Nasr) platforms as offshore
  objectives: static rigs + AAA/ZU-23 + a HAWK/short-SAM, placed among Abu Musa/Sirri in the ME.
  The literal Praying Mantis targets. ❓ feasibility of static-rig placement + making them a
  strike/capture objective to confirm at build (may need a bespoke TGO layout).
- **Iranian missile-boat swarm** — the La Combattante IIa / IRGC boats as naval targets and a
  Silkworm/anti-ship threat to the escort force.
- **Coastal Silkworm shoot-and-scoot (§49).** Model the Iranian coastal anti-ship missile sites
  as `category: missile` TGOs so the **mobile-missile-relocation** feature makes them relocate
  between recon looks — the "hunt the Silkworm battery" mini-game. (This is the *one* piece of
  the shelved Earnest Will idea that drops in cleanly here.)
- **Optional (B) IADS re-dress** — a small period coastal HAWK/SA-2 net + red C2 node to light
  up §51 comms-jam / §52 C2-decap near Bandar Abbas.

---

## 5. Feature fit summary (why this campaign is worth building)

| Fork feature | How the Tanker War uses it | Novelty |
|---|---|---|
| **Warship will-feed** (`blue/red_ship_lost`) | the decisive win currency | **first campaign to headline it** |
| Political will + negotiation ending (§48/W2) | US Resolve vs Iranian Regime | naval reframing |
| ROE restricted zones (§40) | neutral shipping-lane corridor | signature dilemma |
| Campaign phases (§40) | Tanker War → S.B. Roberts → Praying Mantis | authored arc |
| Mobile-missile relocation (§49) | hunt the coastal Silkworm batteries | first sea-facing use |
| Comms-jam / C2-decap (§51/§52) | *optional* coastal Iranian IADS | only if IADS option (B) |
| F-14 on both sides | historical, this map only | identity hook |

---

## 6. Open decisions

Decisions 1–4 are now **resolved** (see the status block at top: Stennis / re-dress IADS /
oil forts in scope / "The Tanker War (1988)"). The one **still open**:

1. **Who makes the miz edits** — the ~7-group period touch-up (§2 table), the oil-platform
   AAA/SAM, and the naval laydown. Either:
   1. **User's ME pass** following the touch-up list (fork-standard "decorate the base miz").
   2. **Claude via a pydcs build script / text-edit** — viable **only if** the Redux miz
      round-trips vanilla-safely (verify-load-save check owed first; type list looks all-stock).
   *(recommend: verify vanilla-safe first; if it is, Claude scripts the edits so the whole
   build stays in-repo and reproducible — else it's a user ME pass.)*

---

## 7. Build order (when the design is approved)

1. Fork + re-faction + re-map squadrons + dates (Phase 1) → headless-load verify (CP/faction
   bind, squadrons resolve, carrier operational).
2. Add `will:` + `phases:` + the shipping-lane ROE zone (Phase 2).
3. Register the campaign (feature index / any preseeds), add a `tests/fourteenth/`-style guard
   locking the laydown, add the checklist row (needs an in-game pass).
4. Phase 3 signature content as a follow-on.

*NEW game required to play (new campaign). No save-migration concerns (additive).*

---

## 8. Build log — Phase 1 (BUILT & headless-VERIFIED 2026-07-07)

**Files:**
- `resources/campaigns/tanker_war_1988.yaml` (new) — forked from Redux; re-factioned + squadron
  re-map + period `ground_forces` + date 1988-04-18 + mod preseeds.
- `resources/campaigns/tanker_war_1988.miz` (new) — **byte copy of the Redux miz, unedited.**
  No miz edit was needed for Phase 1 (see below).
- `resources/factions/iran_1988.json` — added `Mirage-F1EQ` (aircraft, the Iraqi raider),
  `Rapier` (SHORAD) + `EWR 1L13` (early-warning) to `air_defense_units`.
- `resources/factions/usn_1985.json` — added `A-6E Intruder` (free Heatblur AI, the strike arm)
  and `KC-130` (land tanker).

**Key discovery — the IADS periodized in pure YAML, NO miz edit.** The `.miz` markers are
band/position only; the actual SAM system comes from the campaign's `ground_forces:` map (which
overrides even the band→faction auto-fill). So periodizing = rewriting `ground_forces:` red
values to `Hawk` (long+med markers → an I-HAWK belt) + `Rapier` (short markers). `advanced_iads`
+ the whole `iads_config` C2 graph are unchanged, so §51/§52 stay wired. This **resolves the §6
"who makes the miz edits" question for Phase 1: nobody — it was YAML.** (A miz edit is still
wanted in Phase 3 only, to add AAA/SAM to the oil platforms as "gun forts".)

**Three build-time findings (all fixed):**
1. **Mod-gated aircraft → the campaign went mod-free (user call 2026-07-07).** `A-6A Intruder` /
   `EA-6B Prowler` / `A-7E Corsair II` are AI **mod** airframes (`ModSettings.a6a_intruder` /
   `ea6b_prowler` / `a7e_corsair2`, default OFF) — without the toggles they silently substitute to
   stock jets. Rather than depend on mods, the strike arm is now the **free Heatblur `A-6E Intruder`**
   (no `ModSettings` toggle exists for it; added to `usn_1985`; does Strike/SEAD/ANTISHIP/OCA and is
   carrier-capable), the **A-7 mod is dropped**, and the Prowler's SEAD role goes to the **A-6E** on
   the carrier (iron-hand) + **F-4E** ashore. **No mod preseeds — the campaign needs no community
   mods.** (A-6E carries no `max_range` in its data → defaults to 150 NM; fine with the carrier near
   the AO, revisit if the strike reach proves short.)
2. **`iran_1988` EWR gap.** The faction's `'EWR P-37 Bar Lock'` (the §41 game-wide add across 16
   factions) does **not** resolve to an `EARLY_WARNING_RADAR` ForceGroup — `generate_ewrs` logged
   `Iran 1988 has no ForceGroup for EWR` and red got no ground EW. Since `tanker_war_1988` is the
   **only** campaign using `iran_1988`, this latent gap was never exercised before. Fixed by adding
   the known-good `'EWR 1L13'` (proven in `russia_1980`). **⚠ Follow-up worth filing:** if P-37
   Bar Lock genuinely forms no EWR group, the §41 "closes the EWR blind-net across 16 factions"
   claim may be false for all of them — verify the P-37 is in the EWR layout's `unit_types`.
   (Blue `US Navy 1985 has no ForceGroup for EWR` is expected & left as-is — a carrier group uses
   the E-2C, not ground radar.)
3. **Mirage-F1EQ has no ANTISHIP task** in-engine → the "anti-ship raider" flies `Strike` instead
   (flavor is briefing-level; red's real anti-ship threat is the Silkworm sites + boats). No
   `iran_1988` airframe has ANTISHIP; that's fine.

**Verified (headless `GameGenerator` → `begin_turn_0`):** generates clean; CP ownership RED 7 /
BLUE 5; blue CVW = A-6E/F-14A/S-3B Viking/E-2C/S-3B Tanker (A-6E flies Strike + carrier SEAD) +
F-14A/F-4E-45MC ashore + AH-1W/UH-1H off the LHA/Khasab — **all stock/free, `mods enabled: []`**; red =
F-14A/F-4E/F-5E/AH-1J/A-50 + Mirage F1; IADS = HAWK belt +
Rapier + AAA, oil platforms ×60 + Silkworm ×35, **0 empty AA sites**. `pytest tests/fourteenth
tests/armedforces tests/test_newgame_settings.py tests/test_campaignairwingconfig_empty.py` → 398
passed.

**Notes / open nits (non-blocking):** the carrier name rotates among `usn_1985.carrier_names`
each generation (Stennis/Lincoln/…) — all anachronistic Nimitz-class, acceptable per decision 1.2;
pin one later if wanted. The 4 `BLUE L-LONG` markers are still `Patriot` (usn_1985 can't field it)
but produce **0 empty sites**, so left as-is.

**Not yet done (after Phase 1):** the will/phases/ROE identity layer (→ Phase 2, now done, §9);
docs registration (README / features doc / feature index) + a `tests/` laydown guard + checklist
row; in-game pass; Phase 3 content.

---

## 9. Build log — Phase 2 (BUILT & headless-VERIFIED 2026-07-07)

The 414th naval-war identity layer, all in `tanker_war_1988.yaml` (no code, no miz edit):

**`will:` profile** (gated by `vietnam_political_will: true`, preseeded) — relabels the meters
**Washington's resolve** vs **Tehran's regime resolve** with naval exhaustion banners, and weights
**ships as the decisive currency**: `blue_ship_lost: 10` (a US frigate lost is front-page — the
Stark echo), `red_ship_lost: 6` (sinking Iran's navy is the load-bearing pressure), plus
`blue_roe_violation: 4` (neutral-tanker hits), `red_ground_unit_lost: 0.4` (the oil-platform gun
forts + coastal sites bleed Tehran), `blue_airframe_loss: 1.5` / `red_airframe_loss: 0.5`, mild
passive regen both sides. Drives the existing negotiation ending — grind red resolve to 0 → Iran
halts the attacks (WIN); Washington's resolve breaks first → escort mission withdrawn (LOSS).

**`phases:` arc** (gated by `campaign_phases: true`, preseeded) — 3 authored phases:
1. **Tanker War** (`emphasis: interdiction`, turn 0) — locked classes `[oil, power, commandcenter,
   comms]` so early on you may only *defend shipping* (engage boats/coastal/SAM), not wage war
   ashore; `advance_when: blue_will_below: 80` accelerates the escalation if the US bleeds.
2. **USS Samuel B. Roberts** (`emphasis: rollback`, `min_turn: 3`) — the mining; C2/power/comms
   released, oil platforms still locked (`[oil]`); `advance_when: red_resolve_below: 70`.
3. **Operation Praying Mantis** (`emphasis: offensive`, `min_turn: 6`) — everything released; the
   oil-platform gun forts and the navy are targets.

**ROE — the neutral shipping lane** — a no-strike zone present in **all three** phases via a YAML
anchor (`&shipping_lane` / `*shipping_lane`): releasing a weapon against shipping there prices the
mandate (`count_roe_violations` → `blue_roe_violation`), the signature Tanker War dilemma. **The
zone is a hand-drawn `.miz` polygon** (Path B): the user traced a named free-form polygon
(`Strait of Hormuz shipping lane`, 218 pts) on the campaign miz's F10 map, and the phases read it
via `from_drawing: "Strait of Hormuz shipping lane"` (resolved through `theater.zone_drawings` →
`active_restricted_zones`, verified: 1 polygon zone with usable geometry). The earlier typed
4-point corridor is retired. **Edit the shape in the Mission Editor, not the YAML.**

**Category basis** (from the generated game): red TGO categories are `aa/ewr/oil/coastal/armor/
commandcenter/comms/power/missile/ship/fob` — so `oil` (11) = the platforms, `coastal` (7) = the
Silkworm sites, `ship` (2) = the naval sites; the locked-class escalation keys off these.

**Verified:** `parse_will_profile` + `parse_phases` parse clean (they raise on malformed input);
full `GameGenerator → begin_turn_0` still generates with the layer active (RED 7 / BLUE 5, 0 empty
AA sites); `pytest tests/fourteenth tests/armedforces tests/test_newgame_settings.py` → 396 passed.

**Weight balance is a first cut** (checklist M1-style pacing) — tune once flown.

---

## 10. Build log — Phase 3 (BUILT & headless-VERIFIED 2026-07-07)

The signature Praying Mantis content, in two parts:

**Part 1 — coastal Silkworm shoot-and-scoot (§49 extension).** §49 (`mobile_missile_relocation`)
deliberately excludes `coastal` sites, so the Silkworm batteries didn't move. Added an **opt-in
`coastal_missile_relocation`** setting (Mission Generation → Battlefield life, default OFF): the
emitter (`mobilemissileluadata.py`) now emits `coastal` TGOs too when it's on, feeding the same
category-agnostic `mobilemissiles` plugin (no plugin change). Campaign preseeds both toggles.
Verified: the emitter emits **9 shoot-and-scoot sites** (7 Silkworm + 2 SCUD). Tests extended
(`test_mobilemissileluadata.py`, +2 cases: coastal only-when-opted-in, and it composes with the
missile setting); Black + mypy clean.

**Part 2 — oil-platform AAA gun forts.** `tools/build_tanker_war_miz.py` (the RF81/ER "SRC→DST"
generated-miz pattern — reads the pristine Redux miz, writes `tanker_war_1988.miz`, idempotent;
**edit + re-run, never hand-edit the miz**) places a red **`ZSU-23-4 Shilka` AAA marker** on each
oil platform (the band-marker model — the generator fills it from `iran_1988`'s AAA roster
ZU-23/Shilka). Verified: **every oil rig gets a red AAA gun fort** — the 15 platform statics are
11 rig complexes, and red `aa` rose exactly `34 → 45` (+11, one per rig); campaign generates clean,
0 empty AA sites, blue AAA untouched.

**Two engine constraints found (why the gun fort is AAA-only, per the user's option 1):** the
campaign miz is marker-based, so **infantry can't be placed** (no infantry marker), and a Silkworm
*on* a platform would fight Part 1's scoot (it's a `coastal` TGO). AAA is the clean, historically
accurate gun-fort kit (Sassan/Sirri had ZU-23); the 7 shore Silkworms carry the anti-ship hunt.
**On-deck render is the one in-game unknown** (blind to headless): if a battery lands in the water,
nudge `DECK_OFFSET` in the tool or place them by eye in the ME. (Technique confirmed against paid
campaigns — Cerberus North mounts a Silkworm+infantry on a gas platform; see
[[units-on-oil-platforms]].)

**Remaining for the campaign:** the in-game pass (checklist row T2) and will-weight/ROE-corridor
tuning. Docs registration + the `tests/fourteenth/test_tanker_war.py` laydown guard landed
2026-07-18. Phase 3 content is in; the naval war is feature-complete headless.
