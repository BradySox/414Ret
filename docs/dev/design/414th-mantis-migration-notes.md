# MANTIS Migration — Design Notes

**Status:** in progress — spikes + Python seams + **phase-3 core-networking Lua bridge landed
(gated, inert)** (2026-06-24); awaiting in-game pass (checklist G6); shoot-and-scoot + C2 layer not
started
**Date:** 2026-06-24
**Broader context:** this migration is **phase 1** of retiring MIST and standardizing the mission
scripting on MOOSE — Skynet is the biggest MIST consumer with a first-class MOOSE replacement. See
[`414th-framework-consolidation-notes.md`](414th-framework-consolidation-notes.md).
**Prereq reading:** [`414th-mantis-vs-skynet-iads-parity.md`](414th-mantis-vs-skynet-iads-parity.md)
(the feature-parity matrix and verdict this plan builds on).

This is the implementation plan for replacing **Skynet-IADS** with **MOOSE MANTIS**
(`Functional.Mantis`) as 414Ret's IADS engine. The parity matrix established that this is an
**adaptation, not a drop-in**: MANTIS is better-maintained and at-or-above parity on SEAD/HARM,
emissions control, and AWACS, but (a) discovers SAMs by **name prefix** where we wire **explicit
named groups**, and (b) has **no per-node comms/power connection graph**.

### This is an engine-level change — scope it to the engine, not to campaigns

This replaces the IADS **engine**. The bar is **full feature parity for any campaign — present or
future — that the engine supports**, not "good enough for the campaigns that happen to ship today."
`advanced_iads` (comms/power/command-center degradation) is a **general, first-class engine
capability** any campaign can opt into; it is **not** a Red Tide feature, and the fact that a given
count of bundled campaigns currently use it is **irrelevant to scope**. The new engine must support
the *entire* IADS feature set — including the comms/power C2 layer (§5) — or it is not a valid
replacement. Dropping a capability because few campaigns use it today would silently break any
campaign (including community-made ones) that relies on it.

Campaign usage statistics are recorded here **only** as build-sequencing guidance (what to validate
first), never as a reason to narrow what gets built. Every capability Skynet provides today is a
required deliverable of the MANTIS engine.

---

## 0. Guiding principles

1. **Full engine parity is the bar.** The replacement must support every IADS capability the engine
   exposes today — basic networking *and* the advanced comms/power/command-center C2 layer — for any
   campaign that uses it. No capability is dropped or deferred-indefinitely on the grounds that few
   campaigns currently exercise it.
2. **Campaign-agnostic.** The engine knows nothing about specific campaigns. Behavior is driven by
   the campaign's IADS configuration (`advanced_iads`, `iads_config`, unit properties), so any
   campaign — bundled, community, or future — gets identical treatment.
3. **Keep the Python data model as the source of truth.** `IadsNetwork` already computes the full
   node-and-edge graph (which SAM is fed by which comms/power/command-center). We do **not** throw
   that away — MANTIS just becomes a different *consumer* of it. This is what makes the C2 layer
   implementable on top of MANTIS.
4. **The building-anchoring mechanism is plugin-agnostic and stays untouched.** Trigger zones →
   `IadsBuildingGroundObject` → dead unit at scenery position is confirmed independent of Skynet.
   No changes there.
5. **Sequence the build, don't narrow the scope.** Land a behind-a-setting MANTIS path alongside
   Skynet; bring capabilities online in a sensible order; flip the default only once the engine is at
   **full parity** and has passed its in-game passes. Never a big-bang replacement, and never a
   permanent feature subset.
6. **In-game passes are mandatory.** The Lua can't be compiled/run in CI; every runtime claim here
   needs a flight test (add rows to `414th-ingame-pass-checklist.md`), covering both basic and
   advanced IADS behavior.

---

## 1. Scope — what changes, what stays

| Area | File(s) | Change |
|---|---|---|
| Compiled IADS Lua | `resources/plugins/skynetiads/skynet-iads-compiled.lua` | **Replace** with vendored MOOSE (or rely on the already-bundled `Moose.lua` — see §2) |
| Config bridge | `resources/plugins/skynetiads/skynetiads-config.lua` | **Rewrite** as `mantis-config.lua` (new plugin dir `mantisiads/`) |
| Plugin manifest | `resources/plugins/skynetiads/plugin.json` | **New** `mantisiads/plugin.json`; remap options (§6) |
| Lua data emission | `game/missiongenerator/luagenerator.py` (~467–486) | Emit MANTIS-shaped tables (§4); keep Skynet emission until cutover |
| IADS role enum | `game/theater/iadsnetwork/iadsrole.py` | Decouple enum *values* from Skynet role strings (§3) |
| Per-unit properties | `game/dcs/groundunittype.py` (`SkynetProperties`) | Generalize → `IadsProperties` (§3); keep field names, add mapping |
| Network model | `game/theater/iadsnetwork/iadsnetwork.py` (`SkynetNode`) | Add a plugin-agnostic node export; keep graph computation as-is |
| **C2 degradation** | **new** `mantis-config.lua` event handlers | **Re-implement comms/power/CC degradation** (§5 — the hard part) |
| Building anchoring | `start_generator.py`, `tgogenerator.py` | **No change** |
| Save format | `persistency.py` | Migration only if a persisted enum value changes (§7) |

---

## Spike results (2026-06-24) — both de-risking spikes resolved

- **§2 spike — does the bundled MOOSE ship MANTIS at the level we need? ✅ YES.**
  `resources/plugins/base/Moose.lua` contains the full `MANTIS` class (113 refs) including every
  method the plan relies on: `New`, `SetAdvancedMode`, `AddScootZones`, `AddShorad`,
  `SetUsingEmOnOff`, `SetCommandCenter`, `SetAutoRelocate`, `SetSAMRange`, `SetMaxActiveSAMs`,
  `SetAwacs`, `AddZones`, plus the SEAD/relocation state handlers (`onafterSeadSuppression*`,
  `onafterRelocating`, `onafterGreenState`/`onafterRedState`). **Option A is viable — no vendoring
  required**, which removes the biggest feasibility risk and trims the worst-case estimate by ~1 wk.
  *(One name from the MOOSE docs, `SeadAllowSuppression`, is not a top-level `MANTIS:` method in the
  bundled build — SEAD suppression is driven by the integrated SEAD class + the `onafterSead*`
  handlers instead. Cosmetic; does not affect feasibility.)*

- **§4 spike — can we hand MANTIS explicit groups, or must we use a prefix? → PREFIX path.**
  `MANTIS:New(name, samprefix, ewrprefix, …)` builds its SAM/EWR sets *internally* via
  `SET_GROUP:New():FilterPrefixes(...)` (Moose.lua ~L55381–55388). The constructor takes **no
  pre-built `SET_GROUP`**, so explicit per-group injection is not supported. The supported path is
  the plan's documented fallback: **stamp a per-coalition prefix on the generated IADS group names**
  (e.g. `"RED SAM <name>"`) in the Python group naming / `luagenerator`, and pass that prefix to
  `MANTIS:New`. Low-risk (a naming convention on generated groups). **Consequence to carry into
  §3/§5:** MANTIS *infers* SAM type/role from unit type, so explicit role nuances we set today —
  `SAM_AS_EWR` (LORAD-as-EWR) and explicit point-defense pairing — are not directly controllable via
  the prefix and must be handled in the role-mapping / C2 work, not assumed automatic.

**Net:** both spikes favorable. Engine feasibility is confirmed; the open design work is the
prefix-naming seam (§4) and the role/C2 mapping (§3, §5), not whether MANTIS can run.

---

## 2. MOOSE dependency

MANTIS has a hard dependency on the full MOOSE framework (GROUP/UNIT/SET_GROUP/DETECTION_AREAS/
INTEL/SEAD/SHORAD). 414Ret **already bundles `Moose.lua`** (used by TIC, TARS, Flight Control,
SCAR — see CLAUDE.md "scramble pattern"). Decision from the §2 spike above:

- **Option A (chosen):** rely on the bundled MOOSE already injected by `inject_plugins()`, and ship
  MANTIS as a thin plugin that just constructs the network. Confirmed present at the needed feature
  level — no version bump required at this time.
- **Option B (not needed):** vendor `Mantis.lua` + its dependencies verbatim (mirrors how SCAR/TIC
  vendor classes). Kept as a fallback only if a future `Moose.lua` refresh regresses MANTIS.

---

## 3. Python data-model generalization

### 3.1 `IadsRole` (game/theater/iadsnetwork/iadsrole.py) — ✅ seam landed
The enum *values* are literal Skynet strings (`"Sam"`, `"Ewr"`, `"CommandCenter"`…) emitted into Lua.
- Enum *members* (`SAM`, `EWR`, `COMMAND_CENTER`, `CONNECTION_NODE`, `POWER_SOURCE`,
  `POINT_DEFENSE`, `SAM_AS_EWR`, `NO_BEHAVIOR`) are plugin-neutral concepts and stay.
- **Done:** added a `skynet_value` property (returns the Skynet token) as the single named
  serialization seam; the emitters (`IadsNetwork.iads_nodes`, `luagenerator`) now call
  `role.skynet_value` instead of `role.value`. A future `mantis_value` slots in beside it without
  touching the Skynet path. The enum `value` is intentionally left as the Skynet string for now
  (changing it would alter the emitted Lua keys); the seam decouples *consumers*, not the raw value.
- `connection_range` (15 nm comms / 35 nm power) stays — it's *our* wiring policy, not Skynet's.

### 3.2 `SkynetProperties` → `IadsProperties` (game/dcs/groundunittype.py) — ✅ landed
**Done:** renamed the dataclass to `IadsProperties`; `SkynetProperties` remains as a module-level
alias. The persisted **field** stays `skynet_properties` (pickle + YAML-key compatibility —
`GroundUnitType` has a `__setstate__`), with a new engine-neutral `GroundUnitType.iads_properties`
accessor for new code. No unit YAMLs touched. MANTIS field mapping:

| `IadsProperties` field | Skynet | MANTIS expression |
|---|---|---|
| `can_engage_harm` / `harm_detection_chance` | `setCanEngageHARM` / `setHARMDetectionChance` | MANTIS `SEAD` is automatic; expose via `SeadAllowSuppression` callback gating per SAM type |
| `go_live_range_in_percent` | per-unit `setGoLiveRangeInPercent` | per-type `SetSAMRange` + `radiusscale` (per-*instance* not supported — accept per-type) |
| `can_engage_air_weapon` | `setCanEngageAirWeapons` | DCS AI ROE default; no direct knob (document as dropped) |
| `autonomous_behaviour` | `setAutonomousBehaviour` | emulated by our C2 layer (§5) when cut off |
| `engagement_zone` | `setEngagementZone` | `AddZones` / `SetCorridorZones` (network-level) |

> **Decision baked in:** per-*instance* tuning degrades to per-*type* tuning under MANTIS. This is
> acceptable for our campaigns (we tune by SAM type already in plugin options) but must be called
> out in the changelog.

### 3.3 Node export (game/theater/iadsnetwork/iadsnetwork.py) — ✅ landed
**Done:** the exporter is now `IadsNetwork.iads_nodes()` (engine-neutral name) with `skynet_nodes()`
kept as a thin backwards-compatible alias; the `SkynetNode` dataclass is renamed `IadsNode`
(`SkynetNode` alias retained). `luagenerator` calls `iads_nodes()`. Output is byte-identical to
before (covered by `tests/theater/test_iads_engine_abstraction.py`). The **edge data
(ConnectionNode/PowerSource/PD/CommandCenter per SAM) is retained verbatim** — it's the input to the
C2 layer in §5. A future MANTIS emitter consumes the same `IadsNode` list.

---

## 4. Lua bridge — network construction

`mantis-config.lua` reads `dcsRetribution.IADS.<COALITION>` (same table we already emit) and builds
MANTIS per coalition. **§4 spike resolved: MANTIS discovers by prefix only** — `MANTIS:New` builds
its SAM/EWR sets internally via `SET_GROUP:New():FilterPrefixes(...)` and exposes no hook for a
pre-built `SET_GROUP`. So the path is the **prefix approach**: stamp a per-coalition prefix on the
generated IADS group names (in the Python group naming / `luagenerator`) and pass it to `MANTIS:New`:

```lua
-- Python stamps generated IADS group names as "RED SAM <name>" / "RED EWR <name>" etc.
local mantis = MANTIS:New("RED-IADS", "RED SAM", "RED EWR", hqGroup, coalition.side.RED,
                          true  --[[dynamic]], "RED AWACS", true --[[EmOnOff]], nil, zones)
mantis:SetAdvancedMode(true)
mantis:SetUsingEmOnOff(true)
mantis:Start()
```

**Consequence (carry into §3/§5):** MANTIS *infers* SAM type/role from unit type, so the explicit
role distinctions we set today — `SAM_AS_EWR` (LORAD-as-EWR) and explicit point-defense pairing —
are **not** controllable through the prefix. They must be handled in the role-mapping / C2 work
(e.g. a distinct EWR prefix for LORAD-as-EWR groups, and PD pairing emulated in the C2 layer), not
assumed automatic. The prefix stamping itself is low-risk — a naming convention on generated groups.

EWR, SAM-as-EWR, AWACS, emissions control, SEAD/HARM, and shoot-and-scoot map onto MANTIS methods
per the parity matrix §3. Shoot-and-scoot specifically: Skynet's radius-based `setActMobile`
becomes MANTIS `AddScootZones` — we **generate small scoot zones** around each mobile SAM in
`luagenerator` from the existing `actMobile*` distances (min/max scoot distance → zone radius).

---

## 5. The C2 layer — re-implementing comms/power/command-center degradation (required for full parity)

> This is the capability MANTIS lacks natively and the engine must restore. It is **required for the
> engine to reach parity**, not optional — `advanced_iads` is a general engine feature, and any
> campaign that enables it (today or in future) depends on this behavior. It is triggered by campaign
> configuration, so basic-mode campaigns simply never activate it; that is data-driven, not a
> dropped feature.

MANTIS models only HQ loss (→ slower detection via `SetAdvancedMode`). It has **no comms/power
graph**. Since our Python model still computes the full per-SAM edge list, we re-implement the
degradation **in the Lua bridge** as event-driven handlers — small, self-contained, and exactly the
behavior Skynet gave us:

**Inputs (already emitted):** for each SAM node, its `ConnectionNode[]` (comms statics),
`PowerSource[]` (power statics), and the coalition `CommandCenter[]` statics.

**Mechanism:**
1. Build a Lua map `static name → list of dependent SAM group names` from the emitted edges.
2. Register a MOOSE `EVENTS.Dead` / `EVENTS.UnitLost` handler (or a periodic `SCHEDULER` poll of
   `StaticObject.getByName(x):isExist()` — statics don't always fire Dead reliably; poll is safer).
3. On a comms static dying → for each dependent SAM, set it **autonomous** (emulating
   `autonomous_behaviour`): either remove it from MANTIS network control so DCS AI runs it locally,
   or force radar dark if our policy is "no comms → no engagement."
4. On a power static dying → take the dependent SAM **fully offline** (radar off, removed from
   MANTIS active set) — matches Skynet's "no power = dead site."
5. On all command-center statics for a coalition dying → trigger MANTIS degraded mode network-wide
   (we already have `SetAdvancedMode`; additionally widen `SetDetectInterval`).

**Why this works:** the *intelligence* (which SAM depends on which building) lives in Python where
it already is; the Lua layer is a dumb executor of edges — same division of labor as the rest of
414Ret (planner/Lua split, CLAUDE.md). This restores the Red Tide C2 feature to **functional
parity**, with the degradation policy explicit and tunable.

**Open policy question for the squadron:** on comms loss, do we want "SAM goes autonomous"
(engages what it sees locally, Skynet's default) or "SAM goes dark" (harsher)? Default to
autonomous to match current behavior.

---

## 6. Plugin options redesign (`mantisiads/plugin.json`)

Most Skynet options map directly. Changes:
- `createRed/BlueIADS`, `includeRed/BlueInRadio`, `debugRED/BLUE` → keep (radio menu becomes a
  small custom MOOSE menu, §parity matrix; or drop with a note).
- `actMobile*` (SHORAD/MERAD shoot-and-scoot distances/times) → keep; feed scoot-zone generation
  (§4).
- `adjustGoLiveRange_*` per NATO type → keep; feed `SetSAMRange`/per-type scaling.
- **New:** `c2DegradationPolicy` (autonomous | dark) for §5; `advancedModeRatio` for
  `SetAdvancedMode`.

---

## 7. Save-compat & cutover

- If any **persisted** enum value changes (e.g. `IadsRole` values), add migration in
  `FlightType._missing_`-style spots and `persistency.py` per CLAUDE.md "Save migration." `IadsRole`
  is computed at load from `GroupTask`, so it's likely **not** persisted directly — verify before
  assuming a migration is needed.
- **Cutover is a setting**, not a deletion. ✅ **Landed (2026-06-24):** `Settings.iads_engine`
  (`IadsEngine` enum, `SKYNET`/`MANTIS`, default `SKYNET`) in `game/settings/settings.py`. Persisted
  now so cutover is a flip, not a schema change; old saves auto-backfill to `SKYNET` via
  `Settings.__setstate__` (the `Settings().__dict__` default-overlay), so **no explicit migration
  entry was needed**. Deliberately **internal (no UI choices_option)** until the MANTIS emitter
  exists — exposing a non-functional MANTIS choice would be a trap; flip it to a `choices_option`
  when the bridge lands. Covered by `tests/settings/test_iads_engine_setting.py`.
- Keep both plugins shippable until the MANTIS path passes its in-game passes (basic + advanced).

> **Dropped from the original phase-1 plan — `IadsRole.mantis_value`.** The §4 spike showed MANTIS
> discovers SAMs by **name prefix and infers role from unit type**; it does *not* consume Skynet-style
> per-role string table keys. A `mantis_value` analogue of `skynet_value` would therefore be the
> **wrong abstraction** — the role→MANTIS decision lives in the prefix/naming + C2 layers, not a
> per-role token. Not added; revisit only if the emitter design actually needs a role token.

---

## 8. Phased rollout

1. **Spike — ✅ DONE (2026-06-24):** bundled MOOSE has the full MANTIS API (Option A, no vendoring),
   and discovery is **prefix-only** (no `SET_GROUP` injection) → prefix-stamp path. See "Spike
   results" above.
2. **Python generalization — ✅ DONE (2026-06-24):** `IadsProperties` (alias `SkynetProperties`),
   `IadsRole.skynet_value` seam, `IadsNode`/`iads_nodes()` exporter (alias `SkynetNode`/
   `skynet_nodes()`), `luagenerator` switched to the neutral names. Skynet output byte-identical;
   covered by `tests/theater/test_iads_engine_abstraction.py`. Skynet remains the only engine.
3. **Lua bridge — core networking — ✅ CODE LANDED (2026-06-24), ☐ in-game pass pending:**
   `mantisiads/` plugin (`plugin.json` + `mantis-config.lua`), registered in `plugins.json`.
   `luagenerator` emits an `engine` marker into `dcsRetribution.IADS`; `mantis-config.lua` builds a
   MANTIS network per coalition from the existing IADS data (SAM/EWR group-name tables fed to
   `MANTIS:New` as prefixes — no group renaming, per the §4 spike correction), with emissions
   control; `skynetiads-config.lua` now stands down when the engine is MANTIS. **Gated behind
   `iads_engine` (default SKYNET, not UI-exposed), so it lands inert** — Skynet output is unchanged.
   *Not yet implemented in this phase:* shoot-and-scoot, point-defense pairing, SamAsEwr nuance,
   per-unit tuning (phase 4) and the C2 layer (phase 5). In-game pass #1 tracked as checklist **G6**:
   do SAMs detect/engage/go-dark correctly across coalitions?
4. **Shoot-and-scoot + per-type tuning.** In-game pass #2.
5. **C2 layer (§5) — comms/power/command-center degradation:** the capability that brings the engine
   to **full parity**. In-game pass #3 on an advanced-IADS campaign: kill a comms tower, confirm the
   dependent SAM goes autonomous; kill power, confirm offline; kill all command centers, confirm
   network degrades.
6. **Flip default** `iads_engine: mantis` for new campaigns **only once steps 3–5 are all at parity
   and passed**. Keep Skynet selectable for one release as a fallback. No campaign class is left
   behind — basic and advanced both run on MANTIS at cutover.

7. **Docs:** update `414th-features.md` §IADS, `README.md` if player-visible, this file → landed,
   and add the in-game-pass rows.

The order above is *build sequencing* (core networking is a prerequisite for the C2 layer), not a
scope boundary: the default is not flipped until the engine is feature-complete.

---

## 9. Risks / open questions

| Risk | Mitigation |
|---|---|
| ~~Bundled MOOSE lacks needed MANTIS methods~~ | ✅ Resolved: full MANTIS API present (Option A, no vendoring) |
| ~~`SET_GROUP` explicit injection unsupported → forced prefix rename~~ | ✅ Resolved: prefix-stamp is the path; low-risk naming convention. Side effect: role inference (SAM_AS_EWR / PD) handled in §3/§5, not via prefix |
| Statics don't fire `Dead` reliably for C2 layer | Use a `SCHEDULER` poll of `:isExist()` instead of events |
| Per-instance go-live tuning lost | Accept per-type; document in changelog |
| Red Tide C2 feel changes | In-game pass #2 is the gate; tune `c2DegradationPolicy` |
| Two IADS engines increase surface area | Time-boxed: remove Skynet one release after MANTIS default |

---

## 10. Effort estimate

~4–6 weeks for a competent Lua/Python dev to reach **full engine parity** (the only acceptable
end state). Broken down by build step, not by scope:

- **Core networking** (Python generalization + Lua construction + shoot-and-scoot + 2 in-game
  passes): ~2–3 weeks. This is a prerequisite, not a shippable subset — the default is not flipped
  here.
- **C2 layer** (comms/power/command-center degradation + in-game validation): ~1.5–2 weeks. Required
  to reach parity before cutover.

The C2 layer is the long pole, but it is **in scope by definition** — an engine that omits it is not
a Skynet replacement. If the §2/§4 spikes come back unfavorable (old bundled MOOSE, no SET
injection), add ~1 week for vendoring + the prefix-rename path.
