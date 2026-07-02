# 414th — Will-system generalization (any-era profiles) — design notes

**Status: LANDED 2026-07-02** (labels + tunable weights + the warship feed). This note is
the spec for the *generic* half of the political-will economy; the Vietnam campaign layer
that built the mechanic stays specced in `414th-vietnam-political-will-roe-notes.md` — read
that first for the model itself (feeds, negotiation verdict, invariants).

---

## 1. Why

The Vietnam campaign-layer arc (W0–W6) built, in practice, a **generic limited-war
engine**: a symmetric will economy on `Coalition.political_will`, a negotiation win/loss
ahead of the territory checks, authored phase arcs with ROE zones/target release, and red
tempo. Almost none of it is mechanically Vietnam — everything is gated by settings any
campaign YAML can preseed and by the `phases:` authoring block. What *was* Vietnam-locked
was thin and cosmetic-plus-tuning:

1. **The strings** — "Washington's patience", "Hanoi's resolve", the exhaustion banners —
   hard-coded in `political_will.py` and echoed by the client ribbon, the Qt intel box,
   and the Stats chart legend.
2. **The feed weights** — module constants (a B-52 = 6.0, a trail truck = 1.5), correct
   for Vietnam, wrong for a naval war or COIN.
3. **A feed gap** — warship losses fed *nothing* (they hid inside RED's generic
   ground-object attrition and BLUE's losses fed nothing at all), which forecloses the
   single best non-Vietnam fit (Falklands: the war ends when the task force bleeds).

This change removes all three, so the will system is honest about being generic: the
Vietnam framing is just the **default profile**.

## 2. The `will:` campaign block

A campaign YAML may carry a `will:` block (sibling of `phases:`/`settings:`). Every key is
optional; anything absent keeps the Vietnam default. Parsed by
`parse_will_profile` (`game/fourteenth/political_will.py`) into a frozen `WillProfile`
(`WillSideCopy` ×2 + `WillWeights`):

```yaml
will:
  blue:
    label: Downing Street's patience          # meter framing, possessive, mid-sentence
    exhaustion_title: London recalls the task force
    exhaustion_body: The war cabinet has folded — the fleet sails home.
  red:
    label: the Junta's resolve
    exhaustion_title: The Junta capitulates
    exhaustion_body: Buenos Aires sues for peace.
  weights:                                    # any WillWeights field, by name
    blue_ship_lost: 8       # a Type 42 on the evening news
    red_ship_lost: 6        # the Belgrano moment
    blue_airframe_loss: 0.5 # Harriers are precious but not B-52s
```

Rules (all following the phases-S5 precedent):

- **Re-derived at load, never pickled** — `will_profile_for(game)` scans the campaign
  YAMLs by `campaign_name`, caches per process (`_PROFILE_CACHE`), and returns the
  defaults for a blank name (campaign maker) or a removed campaign.
- **Degrade, never crash** — a malformed block (wrong shape, unknown weight key) is a
  `ValueError` at parse, caught by the lookup and degraded to the defaults with a log.
  Unknown weight keys are *rejected*, not ignored, so a typo can't silently no-op a
  rebalance.
- **Default-equivalence** — no `will:` block ⇒ exactly the pre-profile constants and copy.
  The 4 Vietnam campaigns carry no block and are byte-identical
  (`test_default_profile_is_the_vietnam_framing`).

## 3. The warship feed

New weights `blue_ship_lost` (default **4.0** — a warship sunk is front-page news; a
Sheffield, not a truck) and `red_ship_lost` (default **0.5**). Counted from the
debriefing's ground-object loss lists by `TheaterUnit.is_ship` (naval TGO units); RED's
ships are **subtracted from the generic ground-attrition pool** so a sunk vessel is never
double-counted. Rare in Vietnam (the defaults barely move); the load-bearing feed for
naval wars. Carriers/LHAs are control points, so a lost carrier already lands in the
`bases_lost` feed — no special case.

## 4. Surfaces that follow the profile

- The per-turn "Political will" message + both **exhaustion banners** (`political_will.py`).
- The client ribbon meter tooltips (`CampaignStatusJs.blue/red_will_label` →
  `CampaignStatusBar.tsx`; fallbacks keep the Vietnam strings for a stale client).
- The Qt **intel box** tooltip and the **Stats window** will-chart legend.
- The settings detail copy now says the framing/weights are campaign-authorable.

The SITREP band's "Political will X% — enemy resolve Y%" line stays generically worded
(the `Sitrep` is pickled; labels stay out of the save schema).

## 5. The any-era survey (what this unlocks)

Ranked by fit, from the 2026-07-02 review of the 66-campaign / 134-faction inventory.
(A Korea scenario was surveyed and **dropped** — squadron call 2026-07-02.)

1. **COIN / insurgency** (Graveyard of Empires, Aleppo Insurgency, the insurgent factions +
   the §41 ZU-23 technicals) — **the squadron's pick, and genuinely missing.** No territory
   win is even coherent; will *is* the game (blue drains on casualties + duration, red
   "resolve" = insurgent capacity fed by the existing convoy/ground feeds; ROE zones around
   civilian areas price hearts-and-minds; §36 harassment is already generic FOB rocket
   fire). **Blocked on real work beyond this layer:** COIN-shaped *laydowns* (dispersed
   cells, no classic IADS/FLOT) and an insurgent **unit-replenishment model** (cheap,
   steady regeneration rather than convoy-fed reinforcement) don't exist yet — that's its
   own design pass before a campaign is authored.
2. **Yom Kippur 1973** (`operation_gazelle` ships today) — survival panic → counterattack →
   canal crossing as an authored arc (`advance_when: capture_cp` on the crossing),
   superpower-escalation restricted zones, the SA-6/SA-7 era threat the §41 HDS wiring
   already provides. Wants the ATGM-heavy ground OOB the Vietnam doctrine deliberately
   excluded.
3. **Falklands** (4 campaigns shipped) — the purest will economy after Vietnam; the ship
   feed above is its prerequisite and §34 naval gunfire is literally its mechanic. Author
   `will:` labels + ship-heavy weights + a two-phase arc (air battle → landings).
4. **Cold-War-gone-hot** (Red Tide, Crossing the Rubicon, Able Archer 83, Northern
   Guardian) — restricted zones as *escalation thresholds* (deep strikes priced in will),
   `blue_will_below` running the escalation ladder, red tempo as echelon commitment.
5. **Modern peer** (Slava Ukraini, Kola) — Tier-0 already infers a decent arc; authored
   will framing is polish, not a prerequisite.

## 6. Deferred / out of scope here

- **Start values / regen asymmetry per campaign** — will always starts at 100; a
  `start:` key was considered and deferred (no scenario needed it yet; weights cover
  pacing).
- **A duration drain** ("every turn costs will", the COIN clock) — belongs to the COIN
  design pass; trivially added as a weight later (`blue_turn_drain`) once a scenario
  wants it.
- **Cargo-ship losses as a red logistics feed** (sea trail) — the debriefing already
  tracks them separately; fold into a naval-war profile when one is authored.
- **The COIN laydown + insurgent replenishment model** — the real blocker for #1 above;
  now designed (not built) in `414th-coin-insurgent-replenishment-notes.md` (2026-07-02:
  base = a fork of Operation Shattered Dagger; free anchored-cap cell regeneration
  throttled by destroyable cache TGOs; the C1–C4 delivery plan).
