# 414th — Community Contribution Roadmap (the long view)

The [upstreaming inventory](414th-upstreaming-inventory.md) carves out the generic
**bug-fixes** so they stop conflicting on every `dev` pull. This doc takes the longer
view the squadron asked for: **almost every 414th *feature* is a generic capability
the whole Retribution community would want.** "Fork-specific" in the inventory was
mostly a verdict on *carve difficulty*, dressed up as "the community doesn't want
this." Those are not the same thing, and conflating them undersells what we built.

The cure is to score every feature on **two independent axes** and stop letting a high
carve cost masquerade as low community value.

## The two axes

- **Community value** — would a stock-Retribution player, on any theater, want this?
  For nearly everything here the answer is *yes*. A new mission type, a living
  frontline, photo-recon that feeds BDA, ATC, a blank-canvas campaign builder — none of
  that is squadron-specific.
- **Carve difficulty** — how hard is it to extract cleanly and get an upstream
  maintainer to take it:
  - **Pure-Python / data** — easy. Lua-free, CI-checkable, often already tested.
  - **Client (React)** — easy-ish, but needs the CI client rebuild and lands in
    upstream's own map control, not our custom panel.
  - **Vendored Lua** — hard. Upstream gates Lua with a syntax lint only; a vendored
    MOOSE-adjacent plugin means *they now own and maintain that script*. Needs a Lua
    champion on their side, a default-OFF gate, and an in-game pass first.
  - **Content** — N/A. Campaigns, factions, and the buddy-tuned ballistics are
    identity, not capability.

Recon fog already made the journey this doc is arguing for: it sat under "⛔ fork
feature" until it was split from the SCAR command-post gate, and is now a carved,
verified upstream PR (inventory item 8). **Most of the stack can make the same trip.**

---

## What is *genuinely* 414th — the thin layer

This is the part that should never leave `main`. It is small, and it is **content +
identity + the multi-turn economy**, not the feature mechanisms:

| Thing | Why it stays | Files |
|---|---|---|
| **Red Tide campaign** | A hand-authored story campaign (blue-offensive reframe of Crossing the Rubicon), not generic content | `resources/campaigns/red_tide.{yaml,miz}` |
| **Operation Shattered Dagger campaign** | Iran + Caucasus scenario; depends on the Iran faction | `resources/campaigns/operation_shattered_dagger.{yaml,miz}` |
| **[CH] Iran 2020 faction** | Requires the CurrentHill Iran assets mod (Shahed-136, IRGCN FAC) — a hard external dependency | `resources/factions/CH_iran_2020.json`, `pydcs_extensions/` (carved separately as upstream PR #784) |
| **Splash Damage 3.4.2 (414th build)** | Intentionally divergent buddy-tuned ballistics; settings LOCKED by design | `resources/plugins/splashdamage3/Splash_Damage_3.4.2_414th.lua` (PINNED) |
| **Doctrine *default values*** | The *mechanisms* are generic; the tuned numbers are ours. Upstream ships its own defaults | `qra_gci_max_radius_nm=60`, `qra_engagement_range_nm=38` (`settings.py:294,306`), `QRA_SINGLE_SHIP_PROBABILITY=0.75` (`intercept_reserve.py:10`) |
| **SCAR commander-capture / SOF / CSAR economy loop** | The multi-turn "capture a commander → reveal the command net → SOF insert → CSAR a downed team" chain is the campaign-engine differentiator | `game/scar_rescue.py`, `game/scar_objectives.py`, `coalition.captured_commander`, the `scar_command_post_intel` gate |
| **C-130J EW *physics constants*** | The missile-spoof probability curve and burn-through model are design choices, not generic rules | `resources/plugins/c130j/c130j_mission_systems.lua` (the baked constants, not the `FlightType.JAMMING` framework) |
| **TIC stance → waypoint tuning** | The specific stance profiles (standoff distances, press depths, cadence) are our doctrine read; the movement engine underneath is generic | `_tic_stance_profile()` in `game/missiongenerator/flotgenerator.py` |

Everything below this line is **community capability** that could go back.

---

## The feature ledger

Readiness marks reuse the inventory legend (🟢 READY · 🟡 NEAR · 🟠 CARE · 🔵 DONE).
"414th slice to strip" is the *only* part that has to come out for a clean PR — the
rest is the community capability.

### Tier 1 — pure-Python / data (easy carve)

| Feature | Community value | 414th slice to strip | Tests | Readiness |
|---|---|---|---|---|
| Landmap terrain-query perf | High (≈7 min off ground-gen) | none | gen-covered | 🟢 (inv #1) |
| DEAD reachability gate on follow-on strikes | High (planner correctness) | none | `test_dead_planning.py` | 🟢 (inv #2, B2 ☑) |
| Support-orbit depth + front-anchor | High (red AWACS/tanker placement) | none | `test_support_orbit.py` | 🟢 (inv #3, C1/C2 ☑) |
| Negative-start-packages takeoff check | Low/Med (UI false-warn) | none | `test_negative_start_packages.py` | 🟢 (inv #6) |
| SOF C-130 runway-start fallback | Medium (general spawner) | the `c130j` EW de-conflict that ships beside it | — | 🟢 (inv #5, E ☑) — ship *only* the fallback |
| Player-despawn loss accounting | High (false losses) | the Lua hook lives in the bundled runtime — split Python from `dcs_retribution.lua` | `test_debriefing.py`, `test_player_spawn_halt.py` | 🟠 (inv #4, D1 ☑) |
| Air-defense planning rework (BARCAP waves, forward CAP, threat-weighted orbits, FLOT hazard) | High (every campaign) | none | `test_barcap_threat_weighting.py`, `test_front_line_threat_zone.py`, `test_objectivefinder_barcap.py` | 🟡 — B4 ☑, B3 ◐, B1 ☐ (needs the multi-sector + coastal passes) |
| Auto-planner target unpredictability | Med/High (red stops scripting) | none | `test_planner_unpredictability.py` | 🟢 — default OFF, opt-in |
| Auto-hide mobile SAMs on MFD | Medium | none | `test_mobile_air_defense_hiding.py` | 🟢 |
| Player target location precision (Approximate) | High | none | — (confirm before carve) | 🟢 — EXACT stays default |
| Kneeboard overflow pagination | Medium | none | `test_airfield_directory_page.py`, `test_kneeboard_task_pages.py` | 🟡 — H1 ☐ (busy-theater pass) |
| Weapon date-gating | High (era consistency) | none (data is map-agnostic) | data-only (YAML) | 🟢 — see weapon-dates note for the 5 known stale CLSIDs |
| Settings QOL audit (dead-field cleanup, AiRadioBehavior enum + migration) | Medium | none | — (settings-migration tests exist; confirm the AiRadioBehavior case before carve) | 🟢 |
| Drop-spawn unit placement (Python core: `place_unit_group`, TGO + SSE) | High | none | **no dedicated unit test — readiness gap; only server-route tests exist** | 🟡 — §20 in-game pass + add coverage first |
| Campaign maker / blank canvas (Python core) | High (the "major release") | none | `test_blanktheater.py`, `test_campaignairwingconfig_empty.py` | 🟡 — Increment C (support buildings) deferred; in-game BC-rows pending |
| Recon fog-of-war core (viewer-aware visibility) | Medium (player-facing) | `hidden_on_player_map` / SCAR command-post gate → drop; TARPS damage-lag → PR #2 | `test_recon_intel_fog.py`, `test_recon_intel_api_fog.py`, `test_merad_reveal.py` | 🟢 (inv #8) — already carved + verified on upstream `dev` |

### Tier 2 — client (React, needs the CI rebuild)

| Feature | Community value | Note |
|---|---|---|
| Unified map layers panel | High (UI polish) | Client-only; must land in upstream's own layer control, not our custom dark panel |
| Recon fog overview toggle (client half) | Medium | `PUT /fog-of-war/reveal` + re-pull; server side `test_fogofwar_route.py` |
| Drop-spawn map dialog (React `MapContextMenu` + Qt `QPlaceUnitGroupDialog`) | High | Ships with the drop-spawn Python core |

### Tier 3 — vendored-Lua features (high value, hard carve)

These are the ones the inventory wrongly stamped "⛔ NEVER." They are **high community
value**; the cost is a vendored script + a default-OFF gate + an in-game pass + an
upstream Lua maintainer willing to own it. That is *work*, not *exclusion*.

| Feature | Community value | Realistic upstream shape | Tests |
|---|---|---|---|
| **SCAR base task** | High — a discrimination hunt that fills the gap between AI BAI and human CAS; zero content deps (vanilla units, any theater) | Phase-1 carve: `FlightType.SCAR` + builder + the scenario Lua, **stripping** the commander-capture/SOF/CSAR loop and the command-post fog gate | `test_scar.py`, `test_scar_bridge.py`, `test_scar_autoplan.py` |
| **TARS recon + BDA bridge** | High — TARPS film menu + confirmed-BDA feedback fixes a real upstream blind spot | Vendor `TARS.lua` (MOOSE Ops.TARS) + the small Python BDA bridge; the `allowedAmmo`/name-filter overrides are targeted fixes, not doctrine | `test_tarps_recon.py`, `test_tars_bda_bridge.py`, `test_bda_tarps_reveal.py` |
| **TIC dynamic fronts** | High — a living FLOT instead of two static walls | Vendor `TIC_v1.1.lua`; the stance→waypoint compiler is our doctrine read (upstream takes it or writes their own) | `test_tic_dynamic_fronts.py`, `test_tic_clone_mapping.py` |
| **QRA intercept reserve** | High — distributed base-defense beats ramp-scramble everywhere | Python reserve model is generic and largely upstream already (feeds PR #782 `AI_A2A_DISPATCHER`); **the tuned radii/probability are doctrine defaults, not the mechanism** | `test_qra_reserve_settings.py`, `test_game_qra_propagation.py`, `test_interceptattrition.py` |
| **C-130J EW/ISR framework** | Medium — generic EC-130H/RC-130H role | Upstream the `FlightType.JAMMING` enum + behavior (AWACS-track + WEAPON_HOLD ROE); **leave the ~2,200-line EW physics script fork-vendored** — it's a whole subsystem upstream would have to own | — (Lua runtime; not CI-testable) |
| **Plugin Options UI (`descriptionInUI`)** | High — per-plugin description line, pure discoverability | Trivial: one optional JSON field + ~10 lines of Qt. Backward-compatible. **Carve this first — it's the cheapest community win in the repo.** | — |

---

## Recommended contribution program

Each wave is gated by its [in-game-pass](414th-ingame-pass-checklist.md) rows — the
project's own freeze policy ("no new feature work until the queue drains") *is* the
upstreaming gate, because a cluster of ☑ VERIFIED Lua-free rows is exactly an
upstream-PR batch.

1. **Wave 0 — trivia (now).** `descriptionInUI` plugin-description UI. One field, ten
   lines, no behavior change. Warm-up PR that also lands a UX win.
2. **Wave 1 — the verified pure-Python fixes (now).** Inventory items 1–6: landmap
   perf, DEAD gate, support orbit, negative-start, runway fallback, despawn accounting
   (Python half). All ☑ VERIFIED. Carve against a clean `dev`, one PR each. This is the
   concrete "given back to the hub" deliverable.
3. **Wave 2 — recon fog (already carved).** Push the prepared `fog-of-war-complete`
   patch stack (PR #1 fog core, PR #2 TARPS damage-lag) from a checkout with creds.
4. **Wave 3 — the bigger pure-Python features.** Air-defense planning, planner
   unpredictability, MFD SAM hiding, target precision, kneeboard pagination, weapon
   dates, settings QOL, drop-spawn (after adding a unit test), campaign
   maker (after Increment C + the BC in-game pass). Each its own default-preserving PR.
5. **Wave 4 — the vendored-Lua features.** SCAR base task, TARS, TIC,
   QRA, C-130J framework. Each needs: split from the 414th doctrine/economy layer,
   default-OFF gate, an in-game pass, and ideally a sympathetic upstream Lua maintainer.
   Highest value, highest effort — pursue once Waves 1–3 establish a track record.

**The honest read:** "ship it back to the hub" makes sense for *most of the fork* — just
not as one monolithic push, and not the content/identity layer. The seam between
generic capability and 414th identity is sharp and already mostly factored in the code;
the work is carving along it patiently, lowest-difficulty first.

---

## Cross-references

- [414th-upstreaming-inventory.md](414th-upstreaming-inventory.md) — the tactical carve
  queue + per-PR mechanics for the Wave-1 bug-fixes.
- [414th-ingame-pass-checklist.md](414th-ingame-pass-checklist.md) — the gate; a row
  reaching ☑ VERIFIED is what clears a feature for its wave.
- [414th-features.md](414th-features.md) — per-feature engineering internals.
- `docs/dev/upstreaming/fog-of-war/` — the worked example: a carve manifest + PR kit +
  portable patch. The template every Wave-3/4 carve should follow.
