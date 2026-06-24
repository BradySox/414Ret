# MANTIS Migration — Design Notes

**Status:** design / not started (no code changes landed)
**Date:** 2026-06-24
**Prereq reading:** [`414th-mantis-vs-skynet-iads-parity.md`](414th-mantis-vs-skynet-iads-parity.md)
(the feature-parity matrix and verdict this plan builds on).

This is the implementation plan for replacing **Skynet-IADS** with **MOOSE MANTIS**
(`Functional.Mantis`) as 414Ret's IADS engine. The parity matrix established that this is an
**adaptation, not a drop-in**: MANTIS is better-maintained and at-or-above parity on SEAD/HARM,
emissions control, and AWACS, but (a) discovers SAMs by **name prefix** where we wire **explicit
named groups**, and (b) has **no per-node comms/power connection graph**.

### Scope reality check — the C2 gap affects a minority of campaigns

Of the **64 bundled campaigns, only 16 set `advanced_iads: true`** and just **9 use explicit
`iads_config`**. The other **48 (75%) run basic mode — SAM + EWR only**, with no comms/power/
command-center graph at all. So the comms/power C2 gap (§5) — including the Red Tide
"real buildings as IADS nodes" feature — is a **phase-2 concern touching ~25% of campaigns, not a
blocker for the migration as a whole**. Basic mode is a near-clean MANTIS swap for the 48-campaign
majority, and that is what ships first. The C2 layer is built afterward for the advanced subset; it
is explicitly **not** allowed to gate the basic-mode rollout.

This doc still specifies how to keep the C2 feature alive on top of MANTIS (§5), but treats it as a
follow-on phase rather than the critical path.

---

## 0. Guiding principles

1. **Keep the Python data model as the source of truth.** `IadsNetwork` already computes the full
   node-and-edge graph (which SAM is fed by which comms/power/command-center). We do **not** throw
   that away — MANTIS just becomes a different *consumer* of it. This is what makes the C2 gap
   solvable.
2. **The building-anchoring mechanism is plugin-agnostic and stays untouched.** Trigger zones →
   `IadsBuildingGroundObject` → dead unit at scenery position is confirmed independent of Skynet.
   No changes there.
3. **Phase it.** Land a behind-a-setting MANTIS path that runs *alongside* Skynet first; flip the
   default only after an in-game pass. Never a big-bang replacement.
4. **One in-game pass is mandatory.** The Lua can't be compiled/run in CI; every runtime claim
   here needs a flight test (add rows to `414th-ingame-pass-checklist.md`).

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

## 2. MOOSE dependency

MANTIS has a hard dependency on the full MOOSE framework (GROUP/UNIT/SET_GROUP/DETECTION_AREAS/
INTEL/SEAD/SHORAD). 414Ret **already bundles `Moose.lua`** (used by TIC, TARS, Flight Control,
SCAR — see CLAUDE.md "scramble pattern"). Two options:

- **Option A (preferred):** rely on the bundled MOOSE already injected by `inject_plugins()`, and
  ship MANTIS as a thin plugin that just constructs the network. Confirm the bundled `Moose.lua`
  version includes `Functional.Mantis` at the feature level we need (SEAD class, `AddScootZones`,
  `SetAdvancedMode`). If the bundled build is older, bump it.
- **Option B:** vendor `Mantis.lua` + its dependencies verbatim (mirrors how SCAR/TIC vendor
  classes). More control, more maintenance.

**Action item:** grep the bundled `Moose.lua` for `MANTIS` and verify the method set in §4–§5
exists before committing to Option A.

---

## 3. Python data-model generalization

### 3.1 `IadsRole` (game/theater/iadsnetwork/iadsrole.py)
The enum *values* are currently literal Skynet strings (`"Sam"`, `"Ewr"`, `"CommandCenter"`…) that
get emitted into Lua. Decouple:
- Keep the enum *members* (`SAM`, `EWR`, `COMMAND_CENTER`, `CONNECTION_NODE`, `POWER_SOURCE`,
  `POINT_DEFENSE`, `SAM_AS_EWR`, `NO_BEHAVIOR`) — they're plugin-neutral concepts.
- Replace the string values with neutral tokens (or add a `.skynet_value` / `.mantis_value`
  mapping) so the same role can serialize for either backend during the phased rollout.
- `connection_range` (15 nm comms / 35 nm power) stays — it's *our* wiring policy, not Skynet's.

### 3.2 `SkynetProperties` → `IadsProperties` (game/dcs/groundunittype.py)
Rename the dataclass to `IadsProperties` (keep `skynet_properties` as a deprecated alias property to
avoid touching 100+ unit YAMLs immediately). Map each field to its MANTIS expression:

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

### 3.3 Node export (game/theater/iadsnetwork/iadsnetwork.py)
`IadsNetwork.skynet_nodes()` already produces the full graph. Add `iads_nodes()` returning the same
data in a plugin-neutral shape; `luagenerator` picks the emitter based on the active plugin. The
**edge data (ConnectionNode/PowerSource/PD/CommandCenter per SAM) is retained verbatim** — it's the
input to the C2 layer in §5.

---

## 4. Lua bridge — network construction

`mantis-config.lua` reads `dcsRetribution.IADS.<COALITION>` (same table we already emit) and builds
MANTIS per coalition. Because MANTIS discovers by prefix, we bridge the explicit→prefix gap by
**injecting a shared prefix into generated group names** OR by constructing MANTIS from explicit
`SET_GROUP`s we populate by name. Preferred: build `SET_GROUP` objects from our exact group-name
lists and hand them to MANTIS, avoiding any rename of generated groups:

```lua
-- pseudo-code
local samSet = SET_GROUP:New():FilterActive(true)
for _, u in pairs(coalition_iads.Sam) do samSet:AddGroupsByName({u.dcsGroupName}) end
samSet:FilterStart()
-- MANTIS still wants prefixes; if SET injection is unsupported in the bundled build,
-- fall back to stamping a "<COALITION> SAM " prefix on generated names in luagenerator.
local mantis = MANTIS:New("RED-IADS", "RED SAM", "RED EWR", hqGroup, coalition.side.RED,
                          true  --[[dynamic]], "RED AWACS", true --[[EmOnOff]], nil, zones)
mantis:SetAdvancedMode(true)
mantis:SetUsingEmOnOff(true)
mantis:Start()
```

**Action item:** confirm whether the bundled MANTIS accepts a pre-built `SET_GROUP` (some versions
do via the constructor's group args). If not, we take the prefix-rename path in `luagenerator`
(low-risk: it's just a naming convention on generated groups).

EWR, SAM-as-EWR, AWACS, emissions control, SEAD/HARM, and shoot-and-scoot map onto MANTIS methods
per the parity matrix §3. Shoot-and-scoot specifically: Skynet's radius-based `setActMobile`
becomes MANTIS `AddScootZones` — we **generate small scoot zones** around each mobile SAM in
`luagenerator` from the existing `actMobile*` distances (min/max scoot distance → zone radius).

---

## 5. The C2 layer — re-implementing comms/power/command-center degradation (phase 2, advanced campaigns only)

> **Applies to ~16 of 64 campaigns** (`advanced_iads: true`). The 48 basic-mode campaigns never
> reach this code path and ship in phase 1 without it. Do not gate the migration on this section.

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
- **Cutover is a setting**, not a deletion: add `iads_engine: skynet | mantis` (campaign/settings).
  Keep both plugins shippable until the MANTIS path passes an in-game pass on Red Tide
  specifically (it exercises the C2 layer).

---

## 8. Phased rollout

1. **Spike (1–2 days):** confirm bundled MOOSE has the needed MANTIS API (§2 action item) and
   whether `SET_GROUP` injection works (§4 action item). These two answers de-risk everything else.
2. **Python generalization:** `IadsRole`/`IadsProperties` rename + `iads_nodes()` exporter, behind
   the existing data (Skynet still default). Fully unit-testable (pytest).
3. **Lua bridge (basic mode — covers 48/64 campaigns):** `mantisiads/` plugin + `mantis-config.lua`
   network construction (no C2 yet). In-game pass #1: do SAMs detect/engage/go-dark correctly?
   **This is the main deliverable** — at this point MANTIS is a viable engine for 75% of campaigns.
4. **Shoot-and-scoot + per-type tuning.** In-game pass #2. Still basic-mode campaigns.
5. **Flip default** `iads_engine: mantis` for basic-mode/new campaigns; keep Skynet selectable and
   keep advanced campaigns on Skynet until §6 lands.
6. **C2 layer (§5) — phase 2, advanced campaigns only:** comms/power/CC degradation handlers.
   In-game pass #3 on an advanced campaign (e.g. Red Tide): kill a comms tower, confirm the
   dependent SAM goes autonomous; kill power, confirm offline. Only after this do advanced campaigns
   move to MANTIS.
7. **Docs:** update `414th-features.md` §IADS, `README.md` if player-visible, this file → landed,
   and add the in-game-pass rows.

---

## 9. Risks / open questions

| Risk | Mitigation |
|---|---|
| Bundled MOOSE lacks needed MANTIS methods | §2 spike first; bump `Moose.lua` or vendor `Mantis.lua` |
| `SET_GROUP` explicit injection unsupported → forced prefix rename | Low-risk fallback; just a naming convention in `luagenerator` |
| Statics don't fire `Dead` reliably for C2 layer | Use a `SCHEDULER` poll of `:isExist()` instead of events |
| Per-instance go-live tuning lost | Accept per-type; document in changelog |
| Red Tide C2 feel changes | In-game pass #2 is the gate; tune `c2DegradationPolicy` |
| Two IADS engines increase surface area | Time-boxed: remove Skynet one release after MANTIS default |

---

## 10. Effort estimate

Split by phase, since the C2 layer is no longer on the critical path:

- **Phase 1 (basic mode, 48/64 campaigns): ~2–3 weeks.** Python generalization + Lua network
  construction + shoot-and-scoot + 2 in-game passes. This delivers a usable MANTIS engine for the
  majority and is the realistic "is the swap worth it?" milestone.
- **Phase 2 (C2 layer, 16 advanced campaigns): ~1.5–2 weeks.** Comms/power/CC degradation handlers
  + in-game validation on an advanced campaign.

Total ~4–6 weeks if both phases are done, but phase 1 stands alone and can ship first. If the §2/§4
spikes come back unfavorable (old bundled MOOSE, no SET injection), add ~1 week for vendoring + the
prefix-rename path.
