# MANTIS vs Skynet — IADS Feature-Parity Matrix

**Status:** investigation / decision aid (not a commitment to migrate)
**Date:** 2026-06-24
**Question being answered:** Should 414Ret move its IADS from **Skynet-IADS** (current) to
**MOOSE MANTIS** (`Functional.Mantis`)? A squadron member ("KingDingus69") argued MANTIS is the
more modern, better-maintained option. This doc settles **feature parity** before any migration
design work (`414th-mantis-migration-notes.md`) is undertaken.

> **TL;DR:** MANTIS is genuinely better-maintained, and reaches parity-or-better on
> SEAD/HARM defense, emissions control, and AWACS. But it is **not a clean drop-in**: it
> discovers SAMs by *name prefix* (Skynet/Retribution wire *explicit named groups*), and it
> has **no per-node comms/power connection graph** — the exact capability the Red Tide
> "real buildings as IADS nodes" feature is built on. A swap is viable but is an *adaptation*,
> not a *substitution*, and it partially regresses the advanced-IADS / Red-Tide C2 feature
> unless that gap is engineered around.

---

## 1. What 414Ret actually uses from Skynet

This is the *complete* dependency surface — every Skynet API the generated config bridge
(`resources/plugins/skynetiads/skynetiads-config.lua`) calls, plus the Python model that feeds it
(`game/theater/iadsnetwork/`, `game/dcs/groundunittype.py:SkynetProperties`). Parity must be
measured against *this list*, not against Skynet's full manual.

| # | Skynet API called | Purpose | Fed by (Python) |
|---|---|---|---|
| 1 | `iads:addSAMSite(groupName)` | Register a SAM by **exact DCS group name** | `SkynetNode.dcs_name`, role `SAM` |
| 2 | `iads:addEarlyWarningRadar(name)` | Register EWR (and AWACS units) | role `EWR`; `dcsRetribution.AWACs` |
| 3 | `samUnit:setActAsEW(true)` | LORAD SAM doubles as EWR | role `SAM_AS_EWR` (`GroupTask.LORAD`) |
| 4 | `iads:addCommandCenter(static)` | C2 node; loss degrades network | role `COMMAND_CENTER` (`GroupTask.COMMAND_CENTER`) |
| 5 | `samUnit:addConnectionNode(static)` | **Comms tower**; per-SAM graph edge | role `CONNECTION_NODE`, 15 nm auto-wire |
| 6 | `samUnit:addPowerSource(static)` | **Power source**; per-SAM graph edge | role `POWER_SOURCE`, 35 nm auto-wire |
| 7 | `samUnit:addPointDefence(samSite)` | Explicit PD pairing to a parent SAM | role `POINT_DEFENSE` |
| 8 | `samUnit:setCanEngageHARM(bool)` | HARM/ARM defense toggle | `SkynetProperties.can_engage_harm` |
| 9 | `samUnit:setHARMDetectionChance(n)` | HARM detection probability | `SkynetProperties.harm_detection_chance` |
| 10 | `samUnit:setCanEngageAirWeapons(bool)` | Engage air weapons (e.g. cruise missiles) | `SkynetProperties.can_engage_air_weapon` |
| 11 | `samUnit:setGoLiveRangeInPercent(n)` | **Per-unit** go-live range | `SkynetProperties.go_live_range_in_percent` |
| 12 | `samUnit:setAutonomousBehaviour(x)` | Behavior when cut off from IADS | `SkynetProperties.autonomous_behaviour` |
| 13 | `samUnit:setEngagementZone(x)` | Engagement-zone mode | `SkynetProperties.engagement_zone` |
| 14 | `iads:getSAMSitesByNatoName(n):setActMobile(emit,minD,maxD)` | **Shoot-and-scoot** per NATO type (SA-8/9/13/15/19, SA-6/11/17) | plugin options `actMobile*` |
| 15 | `iads:getSAMSitesByNatoName(n):setGoLiveRangeInPercent(%)` | Go-live tuning per NATO type (SA-5/10/17/20/23) | plugin options `adjustGoLiveRange_*` |
| 16 | `iads:addRadioMenu()` | In-mission IADS status radio menu | plugin options `include*InRadio` |
| 17 | `iads:getDebugSettings()` + flags | ~17 debug toggles | plugin options `debug*` |
| 18 | `iads:activate()` | Bring the network online | always |

**The architectural shape that matters:** Retribution generates a **per-named-group explicit
graph** — each SAM is added by its exact generated DCS group name, then individually wired to the
specific comms towers, power sources, command centers, and point-defense sites near it
(`IadsNetwork.skynet_nodes()` → `dcsRetribution.IADS.<COALITION>.{Sam,Ewr,SamAsEwr,CommandCenter}[]`
with `ConnectionNode[]`/`PowerSource[]`/`PD[]` arrays per node). This is a fine-grained,
node-and-edge model.

---

## 2. What MANTIS offers (from `Functional.Mantis` source)

MANTIS (`MANTIS:New(name, samprefix, ewrprefix, hq, Coalition, dynamic, awacs, EmOnOff, Padding, Zones)`)
discovers groups by **name prefix** via `SET_GROUP:FilterPrefixes()` — there is **no explicit
"add this one named group" API**. Type/behavior is *inferred* from the unit type. Relevant methods:
`SetAdvancedMode`, `SetCommandCenter`, `AddShorad`, `SetUsingEmOnOff`, `SetDetectInterval`,
`SetAutoRelocate`, `AddScootZones`, `SetSAMRange`, `SetMaxActiveSAMs`, `SetAwacs`, `AddZones`,
`SetCorridorZones`, integrated `SEAD` class with `SeadAllowSuppression`. **Hard dependency on the
full MOOSE framework** (GROUP/UNIT/SET_GROUP/DETECTION_AREAS/INTEL/SEAD/SHORAD) — standalone use is
not viable.

---

## 3. The parity matrix

Legend: ✅ parity-or-better · 🟡 partial / different model / needs glue · ❌ no equivalent

| Capability 414Ret relies on | Skynet | MANTIS | Verdict | Notes |
|---|---|---|---|---|
| Register SAM site | `addSAMSite(group)` explicit | prefix discovery (`samprefix`) | 🟡 | **Core mismatch.** Retribution wires exact group names; MANTIS wants a prefix and auto-finds. Needs either renaming all generated groups to a prefix scheme or a per-group wrapper. |
| EWR | `addEarlyWarningRadar` | `ewrprefix` | ✅ | Prefix-based, but functionally equivalent. |
| SAM acts as EWR (LORAD) | `setActAsEW(true)` | auto by type/role | 🟡 | MANTIS infers; loses explicit per-group control. |
| Command center degradation | `addCommandCenter(static)` + graph | `SetCommandCenter(group)` + `SetAdvancedMode` | 🟡 | MANTIS models HQ loss as *slower detection interval*, not a hard C2 cut. Coarser. Takes a **group**, not a static object. |
| **Comms / connection nodes** | `addConnectionNode(static)` per-SAM | — | ❌ | **No per-node comms graph in MANTIS.** This is the biggest gap. |
| **Power sources** | `addPowerSource(static)` per-SAM | — | ❌ | **No per-node power graph in MANTIS.** |
| Point defense pairing | `addPointDefence(parent)` explicit | `AddShorad` / auto POINT-type | 🟡 | MANTIS auto-registers short-range/POINT SAMs network-wide; not explicit parent→PD pairing. |
| HARM / ARM defense | `setCanEngageHARM` + `setHARMDetectionChance` per unit | integrated `SEAD` + `SeadAllowSuppression` | ✅ | MANTIS's SEAD model (radar-off + relocate on inbound ARM, per-SAM ARM budget) is arguably *more* sophisticated, but is network-level not per-unit-tunable from our properties. |
| Engage air weapons | `setCanEngageAirWeapons` | (DCS AI default / zones) | 🟡 | No direct equivalent toggle. |
| Per-unit go-live range | `setGoLiveRangeInPercent` per unit | `SetSAMRange` (global %) + per-type `radiusscale` | 🟡 | MANTIS tunes **globally / per type**, not per individual unit. Our `SkynetProperties.go_live_range_in_percent` per unit type maps OK; per-*instance* does not. |
| Autonomous behavior when cut off | `setAutonomousBehaviour` | — | 🟡 | No direct knob; MANTIS SAMs are network-driven. |
| Engagement zone | `setEngagementZone` | `AddZones` / `SetCorridorZones` | 🟡 | Different (network spatial filter vs per-unit zone). |
| Shoot-and-scoot | `setActMobile(emit,minD,maxD)` per NATO type, radius-based | `AddScootZones` (zone-based) + `SetAutoRelocate` | 🟡 | **Different mechanism.** Skynet scoots a radius after N seconds emitting; MANTIS moves units between predefined **zones**. We'd have to generate scoot zones per mobile SAM. |
| Emissions control / go-dark | minimize-emissions by default | `SetUsingEmOnOff` (default dark, radar up only on contact) | ✅ | Parity. |
| AWACS as sensor | `addEarlyWarningRadar(awacs)` | `SetAwacs(prefix)` / `SetAwacsRange` | ✅ | Parity-or-better (configurable range). |
| In-mission radio menu | `addRadioMenu()` | — | 🟡 | No built-in equivalent; would need a custom MOOSE menu. Minor. |
| Debug output | `getDebugSettings()` ~17 flags | `Debug(onoff)` | 🟡 | Coarser (single toggle + BASE tracing). Cosmetic. |
| Datalink fusion | — (not used) | `SetUsingDLink(INTEL_DLINK)` | ✅+ | MANTIS-only bonus we don't currently exploit. |
| Acoustic / non-radar detection | — | `SetAccousticDetectionOn` | ✅+ | MANTIS-only bonus. |

---

## 4. The crux: Red Tide "real buildings as IADS nodes"

The feature KingDingus69 specifically praised — Red Tide mapping IADS onto **real map buildings**
(command posts, comms towers `RSP-10MA`/`NDB_RADIO`, transformer power) — is built **on top of**
Skynet rows 4–6 above (`addCommandCenter` / `addConnectionNode` / `addPowerSource`). MANTIS has
the command-center concept (coarsely) but **no comms or power graph at all**. So:

- The *building-anchoring* mechanism (trigger zones → `IadsBuildingGroundObject` → dead unit at
  scenery position) is **plugin-agnostic** and carries over unchanged — confirmed by the codebase
  investigation.
- But the *IADS behavior* those buildings drive (destroy the comms tower → that SAM goes
  autonomous; destroy power → SAM dies) **has no MANTIS equivalent**. Under MANTIS those buildings
  would be cosmetic unless we re-implement the comms/power degradation ourselves.

**This is the single most important finding in the matrix:** the headline Red Tide capability is
the one MANTIS is weakest at.

---

## 5. Verdict

1. **Maintenance (KingDingus69's main point): he's right.** Skynet's last release is v3.3.0
   (2023-12-29); the bundled build is stamped 2023-05-16; its `master` shows no recent commits.
   MOOSE (which hosts MANTIS) ships every ~2–3 months (~976 commits in 2025). As a
   *future-proofing* bet, MANTIS wins. *(Caveat: "Skynet is actively broken right now" is **not**
   established — it appears dormant, not confirmed-broken.)*

2. **Feature parity: mixed, not clean.** MANTIS is ✅ on SEAD/HARM, emissions control, AWACS
   (and adds datalink/acoustic bonuses), but 🟡/❌ on the things Retribution's model is actually
   built around: explicit per-group wiring, the comms/power connection graph, per-unit tuning,
   and radius-based shoot-and-scoot.

3. **It does not cleanly "look good" as a drop-in.** A migration is an *adaptation* (rename to
   prefix discovery, reshape the Python graph, re-implement or drop comms/power degradation,
   generate scoot zones), not a *substitution*. Estimated effort is unchanged from the codebase
   review (~4–6 wks) and carries a **partial regression of the advanced-IADS / Red-Tide C2
   feature** unless the comms/power gap is explicitly engineered around.

### Recommendation

**Do not treat this as a like-for-like swap.** Three honest paths:

1. **Stay on Skynet, vendor-maintain it.** It's dormant but feature-complete for our model, and
   Claude can patch breakages as they appear. Lowest risk; keeps Red Tide C2 intact.
2. **Migrate to MANTIS and accept/redesign the C2 gap.** Future-proof, but budget the comms/power
   re-implementation explicitly (see proposed `414th-mantis-migration-notes.md`).
3. **Hybrid:** keep Skynet's node/graph model as the source of truth, evaluate MANTIS only for the
   pieces it does better (SEAD/HARM, datalink) — high complexity, probably not worth it.

> ❓ **Decision needed before the migration design doc:** the matrix shows MANTIS regresses the
> comms/power/Red-Tide-C2 feature you just praised. Given that, do you still want the full
> migration design doc (path 2), or pivot to a "keep + vendor-maintain Skynet" plan (path 1)?
