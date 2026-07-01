# 414th Vietnam Ops suite — design note

**Status:** **Phases 1–3 landed** — the `Vietnam Ops` settings page (Phase 0 scaffold) + §32 **Arc
Light** (checklist L1) + §33 **AAA flak gauntlet** (L2) + §34 **Naval gunfire support** (L3), all
registered + emitter-tested; the runtime Lua of each needs an in-game pass. **Phase 4 (§D convoy
interdiction §35) landed** — corridor pick emitter-tested, the spawn Lua pending an in-game pass
(checklist L6). **Phase 5 (§E Super Gaggle §37) landed 2026-07-01 — runtime, not the planner.** The
planner-template v1 stayed blocked (no auto-plannable CTLD cargo run; AIR_ASSAULT assaults a contested LZ,
it doesn't resupply a friendly besieged base — `best_squadron` returns None), so §E shipped the **runtime**
path instead, exactly like §35 convoy: Python picks the besieged outpost + launch field, the plugin spawns
and flies a helo gaggle, re-rolling on a cadence. The fast-mover suppression choreography stays deferred (its
originally-planned "optional later increment"). Emitter-tested; the spawn Lua needs an in-game pass (checklist
L9).
**Date:** 2026-06-28 (designed) · 2026-07-01 (§E landed runtime)
**Related:** [`414th-moose-ops-opportunity-map.md`](414th-moose-ops-opportunity-map.md)
(why this is Tier-A only, never `Ops.Chief`), [`414th-tic-dynamic-fronts-notes.md`](414th-tic-dynamic-fronts-notes.md)
(TIC firefights — the flak/convoy effects reuse its `TaskFireAtPoint` pattern),
[`414th-scar-king-fac-notes.md`](414th-scar-king-fac-notes.md) (the King on-scene-commander
pattern NGFS spotting reuses), [`414th-combat-sar-spec.md`](414th-combat-sar-spec.md),
CLAUDE.md §20 (drop-spawn), §28 (settings IA). Campaign target: `khe_sanh_niagara.yaml`
(inland siege) + `1968_Yankee_Station.yaml` (coastal).

---

## Why this exists

Retribution is a **modern** air-war engine. Its mission taxonomy (BARCAP/SEAD/DEAD/Strike) and
threat model (SAM rings, MEZ geometry) assume a SAM-and-MiG war. Vietnam's air war was the
opposite: **AAA-saturated, FAC-directed, B-52-and-helicopter-heavy**, with naval gunfire and
night trail interdiction. Several of its defining missions simply have no model in the engine.

The 414th already carries the Vietnam *content* (Khe Sanh "Operation Niagara" + Yankee Station
campaigns, VWV factions, period airframes, Sandy/King CSAR). This suite adds the missing
**period mechanics** on top, as opt-in features grouped under one settings page.

## Architecture posture (locked)

Every feature here is a **Tier-A runtime build** in the sense of the MOOSE Ops opportunity map:
*Python plans the geometry and force composition; Lua/MOOSE executes the runtime behavior inside
the single generated `.miz`.* None of them touch the Python campaign brain (economy, HTN
planner, procurement, save format). **`Ops.Chief`/`Commander` (Tier C) stays out** — the fork has
declined a runtime MOOSE theater commander twice (§17 + `turnless.md`).

This means each feature is independently opt-in, independently in-game-validated, and removing
its toggle removes its behavior with no campaign-model change — the same shape as MANTIS,
Combat SAR, and TIC.

## The container — `Vietnam Ops` settings page

A dedicated settings page (alongside Difficulty & Realism, Air Doctrine, …) holds every toggle.
The §28 settings IA is fully metadata-driven: the page is one entry in
`_LAYOUT_SPEC` (`game/settings/settings.py`) plus a page→icon mapping in
`qt_ui/uiconstants.py`, and the dialog + New Game wizard build themselves from it. New boolean
fields are save-safe by construction (`Settings.__setstate__` backfills missing fields from a
fresh `Settings()`).

**Gating model:** every toggle defaults **OFF globally**, and the Vietnam campaign YAMLs flip
the relevant ones **ON** via their `settings:` block (`campaign.py` already applies
`data.get("settings", {})`). So a modern campaign never sees flak puffs or carpet bombing, but a
Khe Sanh game lights up out of the box. The underlying capabilities are era-flexible (flak,
Arc Light, NGFS, convoy interdiction all apply to other eras); the page name follows the user's
framing ("the Vietnam stuff") and is cheap to rename if we generalize later.

**Scaffold-merge note:** Phase 0 ships toggles with no consumers yet. To avoid dead toggles on
`main`, either keep Phase 0 on the branch until Arc Light (Phase 1) fills the first one, or
bundle Phase 0 + Arc Light into the first PR. Decide at PR time (never auto-merge).

### Page layout

| Section | Toggle (field) | Default | Backing feature |
|---|---|---|---|
| Fire support | `vietnam_arc_light` | off | §A Arc Light |
| Fire support | `vietnam_naval_gunfire` | off | §C NGFS |
| Battlefield & interdiction | `vietnam_flak_gauntlet` | off | §B Flak gauntlet |
| Battlefield & interdiction | `vietnam_convoy_interdiction` | off | §D Convoy interdiction |
| Battlefield & interdiction | `vietnam_super_gaggle` | off | §E Super Gaggle |

---

## §A — Arc Light (reframed as a Strike *effect*, not a new flight type)

**Decision (user):** *not* a new `FlightType`; make it what a heavy-bomber **Strike** already
*does*. Keeps planning, ATO, ROE, and save-compat untouched — the carpet is a runtime effect
layered on a normal Strike.

**Mechanism.** A small Lua effect (its own plugin, or an extension of `dcs_retribution.lua`)
keyed to: (a) the `vietnam_arc_light` toggle, (b) a striker whose airframe is a heavy bomber
(B-52, etc.), against (c) an area-type target. At time-on-target it **walks a box of impacts**
across the target zone (a grid of `trigger.action.explosion` / a `ZONE`-bounded BOMBING
`AUFTRAG`), plus the rolling-thunder rumble and an F10 mark. The Python side emits the eligible
heavy-bomber Strike package's target zone + bomber group names (the MANTIS/CSAR config-bridge
pattern); Lua runs the carpet.

**Why this shape:** B-52 AI bombing of a point target is unsatisfying and inaccurate; a scripted
walking carpet over an *area* is both more historical (Niagara Arc Light boxes) and more
reliable. Real damage still flows through the normal ground-loss path if the box overlaps real
TGOs (troop concentrations / supply dumps), so it attrits natively.

**Units:** B-52H + the real Arc Light squadrons (Guam 43rd SW, U-Tapao 307th SW) are already in
the repo.

**DoD / in-game pass:** a B-52 Strike against an area target produces a walking carpet at TOT
(not a single aimpoint); a tactical striker (F-4/A-4) Strike is unaffected; toggle off restores
vanilla Strike; `dcs.log` clean.

## §B — AAA "flak gauntlet" (fresh Lua plugin)

**The point:** the standing fork note is that the *real* Vietnam threat was **AAA, not
SAMs/MiGs** — and Retribution's SAM/MEZ-centric threat model barely represents it. This is the
single biggest **atmosphere** upgrade, and it applies campaign-wide, not to one mission.

**Mechanism.** A fresh plugin (TIC/splash-damage-shaped) keyed to enemy AAA TGOs: barrage flak
bursts (`trigger.action.explosion` airbursts) seeded over the target box at the player's
altitude band, tracer streams from the airstrip AAA belts, and a **predictable-run-in penalty**
(repeating the same heading/altitude into a defended box raises the burst density). Gated by
`vietnam_flak_gauntlet`. Tunable: burst density, altitude band, the predictability window.
Reuses TIC's `TaskFireAtPoint`/effect plumbing as the template.

**Caveat:** this is presentation + soft suppression, not a new lethality model — keep it from
becoming an unfair invisible-SAM. The suppression should *encourage jinking*, not delete the
player. Tune conservatively; in-game pass watches for "feels like Vietnam" vs "feels like a
hidden SA-?".

**DoD / in-game pass:** flying a predictable line into a AAA-defended target draws visible
barrage flak + tracers that thicken with repetition; jinking/varying run-in reduces it; no
phantom kills; `dcs.log` clean.

## §C — Naval Gunfire Support (standalone)

**Verification:** there is **no** existing NGFS feature. CTLD has JTAC *autolase* (likely what
prompted "I think it's in a plugin option"), and TIC already calls MOOSE `TaskFireAtPoint` for
**land** artillery. NGFS = pointing that same primitive at **naval gun ships**.

**Mechanism.** Python identifies friendly gun ships near the coast (battleship/cruiser main
batteries — New Jersey 16″, Oklahoma City, already in the VWV factions) + emits them to a small
`navalgunfire` plugin. A call-for-fire is spotted by the **on-scene commander** (reuse the King
"MAGIC" spotting pattern / an F10 fire-mission menu / a JTAC): the ship `TaskFireAtPoint`s the
called grid, splash + adjust. Minimal-F10, voice-first like SCAR.

**Historicity gate:** **coastal only.** Khe Sanh is inland — naval gunfire never reached it.
This belongs to Yankee Station / I-Corps coastal campaigns, and the `vietnam_naval_gunfire`
toggle is left **off** for Khe Sanh. Document the coastal restriction in the toggle detail.

**DoD / in-game pass:** an on-scene call drops naval gunfire on the called grid (coastal
campaign); inland campaigns see nothing; `dcs.log` clean.

## §D — Truck-convoy interdiction (via Armed Recon corridors)

**Decision (user):** surface it through the existing **`ARMED_RECON`** task — frag Armed Recon
on an enemy road corridor; MOOSE seeds a moving convoy in the corridor; find-and-kill.

**Mechanism.** Extend `ARMED_RECON` so an enemy **road corridor** in red territory is a valid
target (Python picks the corridor + emits it). At runtime a `convoy` plugin spawns a moving
truck column on the road that **scatters/hides** when hunted (stops under tree cover, kills
lights at night). Tie the kill to **red logistics**: destroying the convoy dents the supply the
corridor feeds (lean on the existing supply-route economy so the loss is real, not cosmetic).
Models Steel Tiger / Ho Chi Minh Trail interdiction. Gated by `vietnam_convoy_interdiction`.

**UI (DONE — right-click to frag, per playtest):** the player **right-clicks an enemy supply route**
on the map to frag the interdiction package. `SupplyRoute.tsx` gains a `contextmenu` handler →
`POST /qt/create-package/supply-route/{route_id}` (`game/server/qt/routes.py`) →
`interdiction_target_for_route_id` resolves the route to its enemy end (the contested one first) → the
Qt package dialog opens there, where the player picks **Armed Recon**. The route id now encodes the
two CP ids (`"<cp_a_id>:<cp_b_id>"`) so the endpoint can resolve it; a fully-friendly route 404s (no
dialog). This **supersedes** the earlier "no right-click" stance — it's still an Armed Recon frag (not
a new task or a runtime spawn), just made discoverable on the route itself. Client API hook is
hand-added to the generated `_liberationApi.ts` (codegen unavailable here; matches what
`regenerate-api` would emit). Test: `tests/server/test_supply_route_interdiction.py`; in-app pass L7.
**Pre-select Armed Recon — DONE:** an interdiction frag opens the package dialog with the add-flight
dialog auto-opened and **Armed Recon pre-selected** — a parallel `create_new_interdiction_package`
callback/signal carries the target, and its handler threads `default_task=ARMED_RECON` into
`QNewPackageDialog` → `QFlightCreator` (which selects it if the target offers it; an enemy CP does, via
`MissionTarget.mission_types`). **Deferred:** an Armed Recon flight plan that patrols the exact road
(today it frags against the enemy CP, not the road geometry).

**DoD / in-game pass:** an Armed Recon corridor frag yields a moving convoy that reacts to being
hunted; killing it registers a logistics hit at debrief; `dcs.log` clean.

## §E — "Super Gaggle" hilltop resupply — LANDED 2026-07-01 (runtime, CLAUDE.md §37)

**Original decision (user):** the resupply drop is expressible with existing parts (a CTLD helo cargo run +
a CAS/escort package); the *only* thing a script buys is the **choreography** (the fast-mover AAA-suppression
window + the tight "gaggle" timing) that made it distinctive at Khe Sanh.

**What shipped (runtime, not the planner).** The planner-template v1 below stayed blocked (no auto-plannable
CTLD cargo run — see the top-of-file status), so §E shipped as a **runtime Vietnam Ops feature**, the same
shape as §35 convoy: `_populate_super_gaggle` (`vietnamopsluadata.py`) picks the friendly (BLUE) FOB/FARP
nearest a front as the besieged outpost + the nearest other friendly helo-capable field as the launch point;
the `vietnamops` plugin spawns a helo gaggle (default 3 × UH-1H) that flies launch → outpost → back, announces
delivery, and re-rolls on a cadence. The player can escort it. Runtime-cosmetic (no supply-economy effect),
blue-only (symmetry deferred). The **fast-mover AAA-suppression choreography landed 2026-07-01**: each run
also launches a short attack flight (default 2 × A-4E-C, the historical suppressor) that flies launch → over
the outpost (CAS task) → back, tied to the gaggle lifecycle and its own `pcall`. Emitter-tested; runtime Lua
pending an in-game pass (checklist L9) — the suppressor's default loadout / effectiveness is the open tuning
item (it spawns with DCS's default payload; give it an explicit one or a scripted effect if it needs teeth).

**Original planner-template design (NOT built — kept for the future increment).** A planner package template:
when `vietnam_super_gaggle` is on and a friendly outpost is cut off, auto-plan the package (suppress + cargo +
escort) the way `auto_combat_sar` self-plans. Blocked on the missing auto-plannable CTLD cargo run; revisit if
that capability lands.

---

## §G — "Snake and nape" napalm CAS effect — LANDED 2026-07-01 (runtime, CLAUDE.md §39)

The signature Vietnam CAS delivery: an attacker rolls in low and fast and lays a **wall of fire** across the
enemy ("snake" = Snakeye retarded bombs, "nape" = napalm). DCS doesn't model napalm as an effective AI/soft-
target weapon, so this is the flavor layer that makes the on-the-deck run *do* something — and it's the
**reward** counterpart to the flak gauntlet's *punishment*: flak thickens against a predictable straight run;
snake-and-nape pays off pressing in low over the target.

**What shipped (runtime, on-marker + discovery — the §B flak / §38 FAC shape).** `_populate_snake_nape`
(`vietnamopsluadata.py`) emits only `snakeNape = { enabled = true }` when `vietnam_snake_and_nape` is on. The
`vietnamops` plugin discovers **attack aircraft** at runtime (DCS `Attack airplanes` attribute) making a
**low** (≤ ceiling AGL), **fast** (≥ min speed), **near-an-enemy-ground-unit** pass and lays a **napalm swath**
— a line of `effectSmokeBig` fires along the run-in heading (auto-`stopEffect` after a burn time) + a modest
per-node `explosion` bite — once per pass (a per-aircraft cooldown). Symmetric (both sides' attack jets).
Emitter-tested; runtime Lua pending an in-game pass (checklist L11) — the open item is confirming the
`Attack airplanes` attribute matches the intended CAS jets in-mission (widen the gate if not).

**Deferred.** A weapon-release-tied version (matching an actual napalm/Snakeye `S_EVENT_SHOT` rather than a
proximity/low-pass gate) is the possible later increment; `S_EVENT_SHOT` weapon-id matching is brittle across
modules, so v1 uses the pass gate as the low-risk flavor core.

---

## Phasing (each its own branch + in-game pass; never merge unflown)

| Phase | Scope | Registry/doc work when it lands |
|---|---|---|
| 0 | This note + the `Vietnam Ops` settings page (5 inert toggles) | none (no numbered feature yet; toggles gate nothing) |
| 1 | §A Arc Light effect | register §N, feature-index, checklist row, CLAUDE.md/README, AGENTS sync |
| 2 | §B Flak gauntlet | same |
| 3 | §C NGFS | same |
| 4 | §D Convoy interdiction | same |
| 5 | §E Super Gaggle (runtime; planner-template deferred) | same |
| — | §G Snake and nape (runtime napalm CAS effect; CLAUDE.md §39) | same |

Each numbered feature is added to `game/fourteenth/features.py` (with its `plugin_id` +
`settings_fields`), the generated `414th-feature-index.md` is regenerated, an in-game-pass
checklist row is added, and CLAUDE.md "Features at a Glance" + README + AGENTS.md are synced —
**only when that feature actually lands and is flyable**, so the registry/checklist never claim
a non-working feature. Phase 0 deliberately registers nothing.

## Open questions / risks

- **Scaffold on main:** dead toggles (see the merge note above) — bundle Phase 0 with Phase 1 or
  hold the branch.
- **Flak balance (§B):** the line between "atmospheric" and "unfair invisible threat." Tune
  conservatively; this is the riskiest feature to get *feel* right.
- **Convoy corridor selection (§D):** the geometry/UI detail is deferred to §D's branch.
- **Heavy-bomber detection (§A):** how the effect identifies an eligible heavy bomber + an
  "area" target cleanly (airframe list + target type) without misfiring on tactical strikes.
- **NGFS coastal gate (§C):** ensure inland campaigns truly no-op (no orphaned gun ships
  spotting nothing).
