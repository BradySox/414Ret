# MANTIS vs Skynet — IADS Feature-Parity Matrix

**Status:** decision aid — decision taken: migrate to MANTIS at full engine parity
**Date:** 2026-06-24
**Question being answered:** Should 414Ret replace its IADS **engine**, Skynet-IADS (current), with
**MOOSE MANTIS** (`Functional.Mantis`)? A squadron member ("KingDingus69") argued MANTIS is the more
modern, better-maintained option. This doc maps **feature parity** across the engine's *entire* IADS
capability set; the migration plan is `414th-mantis-migration-notes.md`.

> **TL;DR:** MANTIS is genuinely better-maintained and reaches parity-or-better on SEAD/HARM
> defense, emissions control, and AWACS. It is **not a clean drop-in**: it discovers SAMs by *name
> prefix* (Skynet/Retribution wire *explicit named groups*) and has **no per-node comms/power
> connection graph** — a general `advanced_iads` engine capability (Red Tide's "real buildings as
> IADS nodes" is one consumer of it, not the point). This is an **engine-level** replacement scoped
> to the engine's full feature set, so that gap is a **required deliverable**, rebuilt as an
> event-driven layer over MANTIS — not dropped, and not scoped to any campaign subset.

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

## 4. The crux: the advanced-IADS comms/power C2 graph

The one capability MANTIS cannot natively reproduce is the **advanced-IADS connection graph** —
SAMs wired to comms towers, power sources, and command centers whose destruction degrades the
network (Skynet rows 4–6 above: `addCommandCenter` / `addConnectionNode` / `addPowerSource`). MANTIS
has the command-center concept (coarsely) but **no comms or power graph at all**.

This is a **general engine capability** (`advanced_iads`), available to any campaign. Red Tide's
"real buildings as IADS nodes" (command posts, comms towers `RSP-10MA`/`NDB_RADIO`, transformer
power) is just the most visible *consumer* of it — a useful illustration, but the requirement is the
engine capability, not that one campaign. So:

- The *building-anchoring* mechanism (trigger zones → `IadsBuildingGroundObject` → dead unit at
  scenery position) is **plugin-agnostic** and carries over unchanged — confirmed by the codebase
  investigation.
- But the *IADS behavior* those buildings drive (destroy the comms tower → that SAM goes
  autonomous; destroy power → SAM dies) **has no MANTIS equivalent**. Under MANTIS those buildings
  would be cosmetic unless we re-implement the comms/power degradation ourselves.

**This is an engine capability, not a campaign feature.** `advanced_iads` (comms/power/command-center
degradation) is a general engine capability any campaign — bundled, community, or future — can opt
into; it is *triggered* by campaign configuration but is not specific to any campaign. A MANTIS
engine that omits it is therefore **not a valid Skynet replacement**, regardless of how many bundled
campaigns enable it today. (For reference, 16 of 64 bundled campaigns currently set `advanced_iads`
and 9 use explicit `iads_config` — useful for deciding what to validate first, but irrelevant to
whether the capability is in scope. It is.) The migration plan
([`414th-mantis-migration-notes.md`](414th-mantis-migration-notes.md) §0, §5) treats restoring this
C2 layer as a **required deliverable for full parity**, implemented as an event-driven layer over
MANTIS that reuses the existing Python `IadsNetwork` graph.

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

3. **It's an engine adaptation, not a drop-in — but full parity is achievable.** A migration means
   reshaping discovery (prefix vs explicit groups), reusing the Python graph, re-implementing
   comms/power/command-center degradation as an event-driven layer over MANTIS, and generating scoot
   zones. None of this requires *dropping* a capability — the engine can reach **complete parity**.
   Estimated effort ~4–6 wks (codebase review).

### Recommendation / decision

**Decision taken: migrate to MANTIS at full engine parity.** This is treated as an engine-level
replacement, scoped to the engine's entire IADS feature set — not to any campaign subset. The
comms/power/command-center C2 layer is a **required deliverable**, not an optional extra: see the
migration plan ([`414th-mantis-migration-notes.md`](414th-mantis-migration-notes.md)), which keeps
the Python `IadsNetwork` graph as the source of truth and rebuilds the degradation behavior on top
of MANTIS so every campaign — bundled, community, or future — gets identical, complete IADS support.

Skynet stays selectable for one release as a fallback; the default flips to MANTIS only once the
engine is at full parity and has passed its in-game passes (basic **and** advanced IADS).
