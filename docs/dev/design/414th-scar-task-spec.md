# SCAR Task — Technical Specification

**Target project:** `dcs-retribution/dcs-retribution`
**Source concept:** SCAR-concept-v2 (SME-approved, two review passes)
**Status:** Draft spec for implementation review.

> **Codebase caveat:** symbol names, file paths, and class names below follow the
> Liberation/Retribution lineage but **drift between releases**. Every `code-formatted`
> identifier marked **(verify)** must be checked against `HEAD` before wiring. The spec is
> written so the *design* is authoritative even where the *names* need confirming.

---

## 0. Anchors resolved against HEAD (2026-06-17, 414Ret main)

The `(verify)` items are checked against this fork. Findings:

- **FlightType** → `game/ato/flighttype.py` (`class FlightType(Enum)`). Its docstring is the
  authoritative checklist for adding a type: also touch `flightplan.py`/builder dispatch,
  `aircraftgenerator.py` (a `configure_*` method), each `MissionTarget.mission_types`,
  `resources/units/aircraft/*.yaml` `tasks` weights, optionally `flightwaypointtype.py`,
  `ai_flight_planner.py` `propose_missions`, and `is_air_to_air`/`is_air_to_ground`.
- **Flight-plan builder** → builders live in `game/ato/flightplans/`. Clone
  `armedrecon.py` (`ArmedReconFlightPlan` + `Builder`, both tiny, built on
  `FormationAttack*` and `UiZoneDisplay`). Register the new type in
  `game/ato/flightplans/flightplanbuildertypes.py` `FlightPlanBuilderTypes.for_flight`
  (`builder_dict`). On-station/loiter sizing mirrors the CAP/patrol duration fields.
- **Bundled MOOSE** → `resources/plugins/base/Moose.lua` (4.3 MB, loaded by the `base`
  plugin). The OPS spine the design needs **ships**: `AUFTRAG` (965 refs), `ARMYGROUP`
  (78), `DETECTION_AREAS` (28), `SCORING` (88), plus `FLIGHTCONTROL`/`AUTOLASE`. Only
  `Ops.TARS`/`OPS.PlayerRecce` are absent (TARS is vendored separately in
  `resources/plugins/tars/`). **§8a caution #1 (does AUFTRAG/OPS ship) is resolved: yes.**
- **Results artifact / state-ingest path** → already proven by the TARS BDA bridge; SCAR
  must **extend the same channel, not invent one** (§8a caution #4):
  1. Lua sets a global table + `dirty_state=true`; `resources/plugins/base/dcs_retribution.lua`
     `write_state()` serializes it into `state.json` (see the `tars_recon_captures` entry in
     the state dict).
  2. `game/debriefing.py` `StateData` parses it (mirror `parse_tars_captures`).
  3. `game/sim/missionresultsprocessor.py` consumes it (mirror `tars_reconned_tgos` →
     `update_confirmed_bda`/`reveal_discovered_sites`), resolving unit names to TGOs via the
     `unit_map`.
- **Plugin injection** → not a work order; mirror `_inject_tars_script()` /
  `_inject_tic_script()` in `game/missiongenerator/luagenerator.py` (gated on the plugin
  being enabled, `DoScriptFile` after `inject_plugins()` so `dcsRetribution.plugins.*`
  exists; MOOSE already loaded by `base`).

Still genuinely open (need a maintainer/SME call, not a code lookup): §10 Q1 where the
mis-ID penalty lands, and §10 Q3 the threat value that trips the auto SEAD-escort request.

### 0.1 Implemented so far (2026-06-17)

- **Phase-1 planner foundation + selectability** (CI-validated): `FlightType.SCAR`,
  `ScarFlightPlan` (cloned from Armed Recon), builder dispatch, `configure_scar`,
  fixed-wing-only capability enrichment, `mission_types` exposure, CAS loadout fallback,
  package primary-task order. SCAR is player-selectable; the auto-planner never frags it
  (no commander task class) — auto-fragging stays Phase 3.
- **Integration bridge skeleton** (the §8a recommendation — Python CI-validated, Lua needs
  an in-game pass): `ScarTasking` model + `build_scar_taskings()`/`populate_scar_lua()`
  (`game/missiongenerator/scarluadata.py`), emitted as `dcsRetribution.Scar` and injected
  via `_inject_scar_script()` (gated on the `scar` plugin + a planned SCAR flight). **Targets
  units Retribution already generates** (decision 2026-06-17, replacing the earlier
  placeholder-HVT spawn): a SCAR flight against an enemy **`Convoy`** (`game/transfers.py` —
  moving transfer; killing it already denies the reinforcement via the convoy-loss economy)
  or a **`MissileSiteGroundObject`** (category "missile" → the SCUD variant) emits a tasking
  carrying the target's DCS group name(s). The `scar` plugin (`resources/plugins/scar/`,
  default ON) is **watch-only — no spawning**: success = target group(s) destroyed; for the
  missile variant, fail = it launches (S_EVENT_SHOT by a site unit); a surviving convoy is
  left "active" (the transfer economy already applies the consequence). Outcomes ride the
  proven TARS channel: `dcs_retribution.lua write_state` → `StateData.scar_results` →
  `MissionResultsProcessor.commit_scar_results` (log-only for now). Both target types are
  already SCAR-selectable via the base `mission_types`. Tests: `tests/test_scar_bridge.py`.
- **Deliberately NOT yet built** (next increments): curated decoys/clutter + a glance-readable
  HVT signature for the discrimination puzzle (R2/R4 — convoys give the moving target + real
  consequence, but incidental clutter only); scoring + the mis-ID penalty (§10 Q1) and the
  capture/intel carryover; briefing/marker cueing; Phase-3 auto-planning. **Availability
  caveat:** convoys/missile sites only exist on some turns, so SCAR-from-existing-units can't
  always be offered (fine for player-built v1; gates auto-planning).

---

## 1. Scope

### 1.1 In scope (v1)

A new player-facing **SCAR** flight task: a flight works a defined area to find and prosecute
a single moving high-value target (HVT) hidden among clutter and light-but-real threats,
before the HVT reaches a location where it can no longer be struck.

### 1.2 Out of scope (v1)

- AI flying SCAR with any discrimination logic (AI engages via existing tasking only).
- AI-driven target handoff/coordination between packages.
- An AI GMTI/sensor feed (detection is a live-player capability).

### 1.3 Hard requirements (from SME)

| # | Requirement |
|---|-------------|
| R1 | Exactly **one** HVT per area. |
| R2 | HVT carries a **complete, glance-readable signature** (e.g. SA-9 + command + 2 support trucks). |
| R3 | Clutter is plentiful but **easily distinguishable** — no fine-ID calls (BMP-2 vs -3, etc.). |
| R4 | **≤2 decoy convoys**, each a **partial** signature — never the full element set. |
| R5 | HVT **and** clutter **move** until they reach their destination. |
| R6 | **Fail when** the HVT reaches a no-strike location (city center) — kill lost to collateral. SCUD variant fails on launch. |
| R7 | **Mis-ID is penalized** — prosecuting the wrong convoy costs something. |
| R8 | Area ≈ **10×10 mi**; on-station **15–30 min**, shorter for fast jets, longer for A-10s. |
| R9 | Threat: scattered **ZSU-23-4 / ZU-23-2** + occasional **SA-9/13** — contested, not a SEAD package. |
| R10 | **A-10s** own these areas; squadron tacticians dictate employment; **no dedicated coordinator**. |
| R11 | Cueing via **known ingress lanes** (briefing/markers); fast jets w/ GMT can work with less. |
| R12 | **Day first, night later** — time-of-day is a tuning knob. |

---

## 2. Architecture decision

Two viable implementation philosophies:

| Approach | What it is | Fit |
|----------|-----------|-----|
| **A. First-class generated task** | SCAR becomes a `FlightType` the auto-planner frags procedurally; the generator composes HVT/clutter/decoys/threat. | "Proper" integration, but a large lift and somewhat at odds with how the dynamic campaign picks targets. |
| **B. Lua scenario layer** | A plugin owns convoy composition, movement, fail logic, scoring; triggered when a SCAR flight is present. | Matches the SME's "cheap script" intuition; this is where the gameplay actually lives. |

**Recommendation: hybrid, phased.** Build the player-facing flight plan + capability in the
planner (so SCAR is a selectable task with correct waypoints/loiter), and put the scenario
logic — movement, fail-on-arrival, SCUD fire-and-end, wrong-target penalty — in a **Lua
plugin** modeled on the existing CTLD/Skynet plugin pattern **(verify** `game/missiongenerator/...`
and the Lua plugin loader). Full auto-planner target selection is a later phase.

---

## 3. Data model

A `ScarTasking` object (new) describing one SCAR area. Suggested home: alongside the other
mission/objective tasking models **(verify** package/objective module).

| Field | Type | Notes |
|-------|------|-------|
| `area_center` | LatLon / point | Center of the box. |
| `area_size_nm` | float | ≈ 10×10 mi → ~8.7 NM/side; store as radius or box. |
| `hvt_signature` | list[unit type] | The complete element set (R2). |
| `hvt_route` | list[point] | Ingress lane → destination (R5). |
| `hvt_destination` | point | No-strike location; arrival = fail (R6). |
| `decoys` | list[convoy spec] | ≤2, each partial signature (R4). |
| `clutter` | list[convoy spec] | Plain trucks; count tunable (R3). |
| `threat_laydown` | list[ground unit] | ZSU-23-4/ZU-23-2 + occasional SA-9/13 (R9). |
| `on_station_minutes` | int | 15–30, set by tasked airframe class (R8). |
| `time_of_day` | enum | day/night tuning knob (R12). |
| `variant` | enum | `CONVOY` \| `SCUD`. |

---

## 4. Flight planning

### 4.1 FlightType

Add `SCAR` to the `FlightType` enum **(verify** `game/ato/flighttype.py`). Register it in:

- Task → capability mapping, so only capable airframes can be tasked **(verify** per-airframe
  task lists in aircraft data YAML).
- Any UI task picker / display-name and color maps **(verify** Qt task dropdown + display
  enums).
- The auto-planner priority table — **low priority / opt-in for v1** so the generator doesn't
  spam it before the scenario layer is mature.

### 4.2 Capability

Tasked airframes (R10): primary **A-10C/C-II**; allow **F/A-18C, F-16C, F-15E** as secondary
so squadrons can experiment. Gate via the aircraft data task-capability list.

### 4.3 Flight plan builder

Clone the **Armed Recon** builder **(verify** `game/flightplan/` builder set) and change:

- **Engagement/search geometry:** expand to the ~10×10 mi area (vs Armed Recon's small radius).
- **On-station loiter:** insert a loiter/patrol leg sized by airframe class — ~15 min fast
  jet, ~30 min A-10 (R8). Mirror the BARCAP on-station-duration parameter **(verify** patrol
  duration field).
- **Waypoints:** standard ascent → (hold/join if packaged) → ingress → **SCAR on-station area**
  → egress → split → RTB, using `FlightWaypointType` **(verify** enum members).

### 4.4 TOT semantics

TOT = **start of on-station window** (patrol-start semantics, same family as CAS / Armed
Recon / BARCAP — see the consolidated TOT table in the mission-planning rework). No package
offset by default.

---

## 5. Ground picture generation

Generated either by the planner (Phase 3) or the scenario plugin / mission editor setup
(Phase 1–2). Composition rules:

1. **HVT convoy** — the full signature (R2). Spawns on an ingress lane, routed to
   `hvt_destination`.
2. **Decoys** — ≤2 convoys (R4), each sharing *some but not all* HVT elements. Concretely:
   drop one element and/or change a count so the silhouette reads "close but wrong" the
   instant a pod is slewed onto it.
3. **Clutter** — N plain-truck convoys (R3), where N is tunable; these are obviously-not-it.
4. **Threat** — scatter ZSU-23-4 / ZU-23-2; place 1–2 SA-9/13 (R9). Keep total threat below
   the value that would auto-trigger a SEAD/DEAD requirement on the package planner **(verify**
   threat-zone / escort-request logic so SCAR flights don't auto-pull a SEAD escort).
5. **Movement** — every convoy gets a route to a destination (R5). Clutter destinations are
   arbitrary; only the HVT's destination is the fail zone.

---

## 6. Lua scripting layer

A `scar` plugin **(verify** plugin dir + registration, modeled on CTLD/Skynet). Responsibilities:

| Behavior | Mechanism | Requirement |
|----------|-----------|-------------|
| Convoys track to destinations | Route assignment on spawn; movement is native DCS AI driving. | R5 |
| **Convoy fail** | On HVT group reaching `hvt_destination` zone → flag mission lost, despawn/mark uns trikable. | R6 |
| **SCUD fail** | On launcher reaching launch site → fire event → end scenario. | R6 |
| **Wrong-target penalty** | On a decoy/clutter group destroyed by the SCAR flight → register penalty event. | R7 |
| **Success** | On HVT group destroyed before reaching destination → register success. | R1/R6 |
| Outcome reporting | Push result back to the campaign outcome hook **(verify** debrief/state path). | R6/R7 |

The SME's "spawn → track → fire/arrive → end" model maps directly onto trigger-zone entry
events; this is the cheap-script path he endorsed.

---

## 7. Briefing & intel cueing (R11)

Inject into the generated briefing for any SCAR flight:

- **Target signature** in plain language: the full element set the player must match.
- **Ingress lanes** the HVT may use (the "we know they use these 3 roads" cue) — as text and,
  ideally, drawn map markers **(verify** kneeboard/briefing + map-drawing injection).
- **Decoy warning** (R4 framing): "other convoys may resemble the target but will not carry
  *all* listed elements."
- **Fail condition** stated: find and kill before it reaches \[location].
- For SCUD: the launch-site location and the fire-and-done fail.

---

## 8. Scoring & campaign consequence

| Event | Consequence | Requirement |
|-------|-------------|-------------|
| HVT killed in area | Standard kill credit + intended campaign effect (e.g. deny the SCUD strike / degrade objective). | — |
| HVT reaches no-strike zone | Mission objective failed; no kill credit; optional campaign penalty. | R6 |
| Wrong convoy prosecuted | **Penalty** — define magnitude (score, budget, or reputation hook). | R7 |

Wire via the existing kill/outcome accounting **(verify** mission results / state update). The
mis-ID penalty (R7) likely needs a **new** hook — flag for maintainer input on where
consequence is applied.

---

## 8a. MOOSE building blocks — wired into Retribution

> **Integration discipline (non-negotiable):** MOOSE is a *runtime* Lua framework that lives
> **inside the generated .miz**. It is **orthogonal to the Python planner** (§4). Nothing here
> is freestanding Lua dropped into a mission — every MOOSE object must be **emitted by the
> Retribution generator** from the `ScarTasking` model (§3), and every outcome must **report
> back into campaign state**. The seam is: Python composes the tasking → generator writes the
> SCAR Lua block + a config table built from `ScarTasking` → MOOSE executes in-mission →
> results flow out through the existing state/debrief path. If a piece can't close that loop,
> it doesn't go in.

### The two halves, and the bridge

| Layer | Owns | Tech |
|-------|------|------|
| **Python (Retribution)** | FlightType, flight plan, capability, composing the HVT/decoy/clutter/threat picture, writing the Lua config, ingesting results. | Existing generator (§4–§5, §8). |
| **Lua (MOOSE, in-mission)** | Convoy movement, detection picture, fail/success/penalty detection, player messaging. | Generated SCAR plugin block. |
| **The bridge** | A generated Lua **config table** (from `ScarTasking`) in, a **results artifact** (flags/state) out. | The integration seam — build this first. |

### Requirement → MOOSE class → Retribution wiring

| Req | MOOSE class | What it does | Retribution side (must exist or be built) |
|-----|-------------|--------------|--------------------------------------------|
| R5 (movement) | **`OPS.ArmyGroup`** | Enhanced ground group: route following, waypoint/arrival events. | Generator emits each convoy as an ArmyGroup with a route from `hvt_route` / clutter routes. |
| R6 (fail on arrival) | **`Core.Zone`** + **`AUFTRAG:AddFailureCondition`** | Zone at `hvt_destination`; failure condition fires when HVT enters → mission cancelled. | Generator writes the destination zone + binds the failure condition; **the cancel event must set a flag Retribution reads back** (lost-to-collateral → no kill credit). |
| R6 (SCUD) | **`AUFTRAG`** start/push conditions + **`Core.Timer`** | Launcher tracks to site, fires, mission ends on the same failure-condition mechanic. | Same emit-and-report path as the convoy fail. |
| R1/R2 (find the HVT) | **`Functional.Detection` (`DETECTION_AREAS`)** | Groups detected ground units into areas; **assigns each a threat level 0–10**. | Generator stands up the detection net for the SCAR area; the HVT's SA-9 escort makes its group read **higher-threat** than plain-truck clutter — discrimination becomes data-driven, not just eyeballs. |
| R7 (mis-ID penalty) | **`Functional.Scoring`** + DCS kill event | Logs/administers player scoring events on unit kills. | On a *decoy/clutter* group destroyed by the SCAR flight, register a penalty; **emit it to the same results artifact** so the campaign applies the consequence. This is the §10 open hook — Scoring is the in-mission half, Retribution state is the other half. |
| Coordination (player) | **`Functional.Autolase` / `Ops.PlayerRecce`** | Auto/voluntary lasing + designation menus for talk-ons. | Optional; only if we later support buddy-lase. Player-run, so low priority. |
| Player messaging | **`Core.Message` / `Sound.SRS`** | In-cockpit cues, intel calls (ties to your existing SRS/TTS stack). | Generator can seed the signature brief + ingress-lane cues as SRS calls. |
| Cueing markers (R11) | **`Wrapper.Marker`** | F10 map markers drawn from script. | Generator passes ingress-lane geometry into the Lua config; MOOSE draws them. Resolves the §10 "is briefing text-only" question — markers are scriptable. |

### Honest cautions

1. **AUFTRAG is the spine, but verify the version ships with Retribution's bundled MOOSE.**
   AUFTRAG/OPS classes are develop-branch-era; confirm the MOOSE version Retribution injects
   **(verify** bundled MOOSE in the repo) actually contains them before designing around them.
2. **Detection persistence cuts against the hunt.** `DETECTION_AREAS` *keeps* detected targets
   even after LOS is lost — good for a stable picture, bad for "find it before it hides." The
   refresh interval and persistence need tuning so the HVT can still slip away (R6).
3. **Threat-level discrimination is a gift — don't over-rely on it.** The SA-9 making the HVT
   read hotter is elegant, but if it becomes the *only* tell, players just shoot the highest
   threat and skip the ID skill the SME wanted. Keep the visual signature primary; treat threat
   level as a secondary cue.
4. **The results artifact is the whole ballgame.** Whatever Retribution already reads from a
   completed mission (debrief state, flags, kill log) is what the SCAR Lua must write into —
   **(verify** the state-ingest path). Don't invent a parallel channel.

> Recommendation: build the **bridge first** (emit a trivial `ScarTasking` → Lua config → one
> AUFTRAG that can only pass/fail → read the result back into campaign state). Prove the loop
> closes end-to-end before adding detection, decoys, or scoring. That's what keeps this from
> being a half-integration.

## 9. Build checklist (phased)

### Phase 1 — Player-flyable MVP (manual ground picture)
- [ ] Add `SCAR` to `FlightType` (+ display name, color, capability gating). **(verify names)**
- [ ] Clone Armed Recon flight-plan builder; widen area; add airframe-scaled loiter.
- [ ] TOT = on-station start; correct waypoint chain.
- [ ] Stand up the `scar` Lua plugin skeleton (load + register).
- [ ] HVT signature + ≤2 decoys + clutter placed (editor/manual or plugin spawn).
- [ ] Convoys route to destinations; HVT → fail zone.
- [ ] Fail-on-arrival + success-on-kill events firing in Lua.
- [ ] Briefing injects signature + ingress lanes + decoy warning.
- [ ] Daylight, A-10 first. Playtest the find/ID/kill loop.

### Phase 2 — Penalty, SCUD variant, polish
- [ ] Wrong-target penalty event + consequence hook (R7).
- [ ] SCUD variant (track → launch → end).
- [ ] Light-AAA + SA-9/13 laydown tuned to "contested not SEAD" (R9); confirm no auto SEAD-escort pull.
- [ ] Night iteration; tune clutter density vs satisfaction (R3/R12).
- [ ] **C-130 intel-node framing** (§9b.1): brief the start point / candidate roads / departure time as coming *from* the C-130; optional Herc orbit slot. (Zero code — briefing framing.)

### Phase 3 — Generator integration (optional / later)
- [ ] Auto-planner can frag SCAR against suitable objectives.
- [ ] Procedural HVT/decoy/clutter/threat composition.
- [ ] Tie HVT kill to a real campaign-economy effect.
- [ ] **SOF capture branch** (§9b.2, stretch): C-130 airdrops SOF → capture-vs-destroy. **Capture writes a next-turn intel reward into campaign state** (revealed SAM coords / IADS-critical building); destroy = no carryover. Fragile/time-gated; confirm reward type with SME.
- [ ] **TARPS recon link** (§9c): player-flown F-14 TARPS sortie generates the convoy-hunt cue (start point / roads / timing). Recon quality sizes the next link's cue.
- [ ] **Bidirectional chain consequence** (§9c.2): success eases next link, failure worsens it; convoy reaching destination = enemy advantage next turn.
- [ ] **Botched-capture extract** (§9c.1, stretch): failed/wrong-road capture → SOF egress + helo CSAR mission spawned next turn.
- [ ] **SOF finite-asset model** (§9c.3): 2 teams, consumable, can't reuse until extracted; capture eases the extract, botch = hot pickup. Verify Retribution's warehouse/asset-availability model can carry a custom SOF unit class.

---

## 9a. Player workflow by phase

How a player actually encounters SCAR, tied to the real Retribution loop (new campaign →
Turn 0 setup → Turn 1 map + ATO → claim client slot → Take Off generates .miz → fly in DCS →
Accept Results → next turn). **This changes what "done" means per phase.**

### Phase 1–2: player hand-builds the package
SCAR is **not** auto-fragged, so after passing into Turn 1 the player sees a normal ATO with
**no SCAR package in it**. To fly one they:
1. Select the target area on the map and create a new package (as with any custom mission).
2. Add a **SCAR** flight; assign A-10s; add a client slot; set TOT (= on-station start).
3. **Take Off** → the generated .miz contains the HVT/decoy/clutter convoys, threat laydown,
   movement, and MOOSE logic.
4. In-cockpit: kneeboard shows the target signature + ingress lanes; player hunts, IDs,
   prosecutes; the fail clock runs as the HVT drives toward its no-strike zone.

> **Phase 1 "done" = a human can hand-build and fly a SCAR sortie end-to-end, and the result
> reports back into campaign state.** Not "it appears on its own."

### Phase 3: SCAR appears in the ATO automatically
The auto-planner frags SCAR against a suitable objective, so on Turn 1 it's **already in the
ATO** like any other package — the player just claims a slot and flies it.

> **Phase 3 "done" = SCAR shows up in the turn's ATO without the player building it.**

---

## 9b. C-130 participation

Two roles for the C-130 in SCAR. The first is the committed v1 approach; the second is a
Phase-3+ stretch concept.

### 9b.1 Intel node (committed) — the C-130 owns the cue

Reframes the C-130 from a real-time spotter into the **source of the intel** the SME already
defined. The Herc "owns" the HVT picture: **start location, candidate roads, and departure
time.** This resolves the sensor problem instead of fighting it — a sensorless C-130 providing
*start point + likely routes + timing* is realistic, where a sensorless C-130 producing a live
tracking mark was not (that earlier idea is dropped).

- **Delivery:** narrative briefing source. The intel reaches the players via the kneeboard /
  SRS as coming *from* the C-130 — not a generated map feed, not a tracking mark.
- **Zero code.** This is *who delivers the briefing*, nothing more. The intel content (start
  point, the three roads, departure time) already lives in the `ScarTasking` model and briefing
  injection (§3, §7); this just frames its source.
- **Discrimination intact.** Players still find and ID the HVT among clutter — the C-130
  narrows the search to known roads/timing (the cueing the SME endorsed, R11) without
  identifying the target for them. No AI-feed-line issue.
- **Optional player slot.** A C-130 client seat can fly the intel orbit for immersion, but the
  role works even as a briefing frame with no Herc airborne.

> Net: a **briefing-and-narrative** addition, not engineering. Gives the C-130 a real purpose
> and makes the "known ingress lanes" cue diegetic.

### 9b.2 SOF capture branch (Phase 3+ stretch concept)

A two-outcome alternative to just killing the HVT: the C-130 airdrops a SOF team to **capture**
the target alive — and the reward for capture is **a concrete advantage on the next Retribution
turn**, not an in-mission score bump. (Direction set with the SME.)

**The branch:** A-10s find the HVT *early* → call the correct road → C-130 airdrops the SOF
team **ahead of the HVT on that road** → capture attempt. If they don't find it early enough
(or call the wrong road), fall back to the default **destroy** outcome.

**The incentive (deliberately asymmetric):**

| Outcome | When | Reward |
|---------|------|--------|
| **Capture** | Early find — *harder* to pull off | HVT taken alive → interrogation intel that **benefits the next turn**: e.g. revealed SAM coordinates, or a critical building whose destruction **cuts the enemy IADS**. |
| **Destroy** | Slow / default | Target serviced, threat removed — but the intel dies with him. **No carryover.** A clean result, not a clean *win*. |

The point of the asymmetry: killing him when you're slow is the **cop-out**, not the optimal
play. "Did we win, and *how big*?" expressed as **campaign consequence** rather than a debrief
line — capture changes the *next* mission, not just this one's score.

**Feasibility (honest):**

| Piece | Buildable? | Notes |
|-------|-----------|-------|
| C-130 airdrop + ground SOF team | **Yes** | Core CTLD territory (same plugin family as Air Assault). |
| "Capture" mechanic | **Scriptable, not native** | No native capture in DCS. Script: SOF within X m of stopped HVT for Y s → "captured" → despawn HVT + success event. Same cheap track-to-zone pattern the SME blessed for the SCUD, pointed at a capture outcome. |
| Branch logic (capture vs. destroy) | **Yes, fragile** | Team must be dropped ahead of the HVT on the *correct* road; HVT must reach and stop. Miss the window / wrong road → fall back to kill. |
| **Capture → next-turn reward** | **Yes — and this is the keystone** | Capture writes an intel benefit into campaign state for the following turn (revealed SAM coords / an IADS-critical building flagged for strike). This is exactly the **results artifact** of §8a — the capture outcome *must* report back, unlike the FAC pilot-aid. |

**Why Phase 3+:** the capture path is time-gated with many moving parts (correct road, HVT
arrival, stop, proximity timer), *and* the reward requires writing campaign-state carryover —
which only makes sense once SCAR is generator-integrated (Phase 3) rather than a hand-built
package. Strong concept, but it sits on top of the finished base loop. **SME is in favor of the
carryover framing; confirm the specific reward type before building.**

### Hard constraints (true for both)

1. **No targeting sensor on the C-130** — it cues, and (in the stretch) inserts; it does not
   lase or designate. Any lasing stays with the A-10s.
2. **No FAC(A) task type in Retribution** — the C-130 is an orbit/transport slot; its role is
   the intel framing (and, in the stretch, a CTLD airdrop), not a generated task.

---

## 9c. Mission chain — TARPS → convoy → strike (SME concept)

The capture carryover (§9b.2) is one instance of a larger idea the SME framed: **a recon →
find → exploit loop that runs across turns**, where each mission generates the intel that frags
the next. SCAR is the **middle link**.

### The chain

| Link | Mission | Produces |
|------|---------|----------|
| 1. Recon | **F-14 TARPS** (or similar recon sortie) identifies and stages the target. | The cue the next mission inherits: start point, candidate roads, departure timing — the intel-node content (§9b.1), now *flown* rather than narrated. |
| 2. Find/service | **SCAR convoy hunt** — find and kill or capture the convoy TARPS located. | The outcome: destroy (threat removed) or capture (intel carryover, §9b.2). |
| 3. Exploit | **Next strike** — frags off the link-2 result: the degraded airbase, the cut IADS, the building that drops enemy sortie rate. | The payoff, realized on a later turn. |

### The briefing pattern (reusable — keep this)

The SME's framing is the template for *every* intel handoff in the chain — a concrete recon
finding, an assessed consequence, and a **quantified** payoff:

> *"The F-14 TARPS identified the staging of a fuel convoy preparing to leave for Vaziani; we
> assess they are at a critical fuel state. Eliminating this convoy will result in a 30%
> reduction in sorties from that air base."*

Recon finding → assessment → number. This structure makes "how big did we win" legible and is
worth applying to all mission briefings, not just this chain.

### Build path (both, per decision)

- **Now — hand-authored chain.** Wire the three links manually the way campaign missions are
  built today: the "intel" is narrative + a pre-placed next target, and the carryover is the
  mission designer fragging link 3 based on what happened in link 2. Buildable immediately;
  the right way to prototype the loop and tune the payoff numbers before any code.
- **Goal — auto-generated chain.** Each mission **procedurally frags the next from the prior
  result**: TARPS detection spawns the SCAR convoy tasking; the convoy outcome writes the
  strike tasking (or the capture intel) into campaign state for the following turn. This is
  real Phase 3+ generator work — it sits on top of SCAR generator integration and the §8a
  results-artifact path, and is the natural home for the capture carryover.

### Why it matters

It turns SCAR from a standalone task into a **campaign engine**: recon earns the find, the find
earns the exploit, and player performance at each link sizes the payoff at the next. That's the
"did we win, and how big" debrief expressed as a multi-turn consequence — the strongest version
of everything the SME has been pushing toward.

> **Honest scope flag:** the hand-authored version is a *mission-design pattern* you can use
> now; the auto-generated version is a significant generator feature. Don't let the second
> block the first — prototype the chain by hand, prove it's fun, then decide whether the
> auto-gen lift is worth it.

### 9c.1 Chain design — SME-resolved

Answers from the SME pass on the chain mechanics:

- **Capture reward type — open, by design.** Not locked; worth asking the wider group. Fun
  idea floated: let the **group choose the focus of interrogation**, which determines the
  reward (e.g. "interrogate for SAM laydown" vs. "for the IADS node"). Keeps the payoff
  player-driven. *Carry as an open group decision, not a spec lock.*
- **Payoff magnitude — by-mission feel, ~25–30%.** Set per-mission by the designer rather than
  a fixed table; **25–30%** is the sweet spot — meaningful without nullifying the next
  mission's challenge. The TARPS "30% sortie reduction" line is the reference point.
- **Botched capture → escape-and-evade, not a free retry.** If the SOF drop hits the wrong
  road or misses the window, the team **must egress by another route** — and that **spawns a
  helo extract mission on the next turn** to pull them out. A failed capture isn't a clean
  fallback to "just kill him"; it creates an *obligation* (go get your team), which makes the
  capture attempt a real gamble. This adds a fourth mission type to the chain (CSAR/extract)
  and is strong but clearly Phase 3+ scripting. **Extraction difficulty scales with the
  outcome** (§9c.3): a *successful* capture makes the extract **less contested** — the enemy
  won't act while you hold their leader; a botched capture is a hotter pickup.
- **Chain swings both ways.** Success makes the next link **easier**; failure makes it
  **worse**. The convoy reaching its destination should carry a *negative* consequence (enemy
  advantage next turn), not just a neutral "no carryover." See §9c.2.
- **TARPS is player-flown.** The recon link is a **flyable F-14 TARPS sortie**, not a narrative
  step — the squadron wants to fly it. The TARPS run *generates* the cue (start point, roads,
  timing) that frags the convoy hunt.

### 9c.2 Bidirectional chain consequence

The chain is not win-or-neutral; it's win-or-lose, each link sizing the next:

| Link result | Effect on next link |
|-------------|---------------------|
| TARPS flown well (good recon) | Convoy hunt gets a *tighter* cue — fewer roads, better timing. |
| TARPS poor / skipped | Convoy hunt starts *cold* — wider search, weaker intel. |
| Convoy **captured** (early) | Next strike gets the interrogation intel reward (~25–30% enemy degrade). |
| Convoy **destroyed** (slow) | Threat removed, no intel carryover — neutral. |
| Convoy **reaches destination** (failed) | **Enemy advantage** next turn (e.g. *their* sortie rate up) — the cop-out now costs you. |
| Capture **botched** (wrong road / missed) | Adds a **helo extract mission** next turn to recover the SOF team. |

This is the "did we win, and how big — or how badly" debrief, expressed as multi-turn
consequence in both directions.

### 9c.3 SOF teams as a finite, consumable asset (SME model)

The cleanest way to represent the SOF teams: treat them **like a warehouse weapon** — a
finite, consumable resource the campaign economy already understands, not a free spawn.

- **You have 2 SOF teams.** Deploying one **expends** it.
- **You can't reuse a team until it's been extracted.** A dropped team is committed downrange
  and unavailable until a helo pulls it out.
- **A botched capture therefore has a real economy cost:** it doesn't just add a CSAR mission,
  it **locks up half your SOF capacity** until that team is recovered. Burn both teams on failed
  attempts and you have no SOF capability until you extract them.
- **Capture eases the extract.** Holding the enemy leader means the enemy won't dare act — so a
  *successful* capture's extraction is **less contested** than a botched one's hot pickup.
  Reward and cost are coupled: doing it right buys a safer recovery.

| SOF state | Meaning | Effect |
|-----------|---------|--------|
| Available (×2) | In reserve | Can be tasked to a capture. |
| Deployed | Dropped, on the ground | Unavailable until extracted; capture in progress. |
| Awaiting extract | Capture done **or** botched | Spawns a CSAR mission; *capture* = lower threat, *botch* = hot pickup. |
| Extracted | Recovered | Returns to the available pool. |

**Why this fits:** Retribution already models finite assets with availability states and
warehouse stock, so the "2 teams, use-but-can't-reuse" mechanic likely reuses existing economy
plumbing rather than a parallel system — **(verify** the warehouse/asset-availability model can
carry a custom unit class like this). It also gives the capture branch *campaign-level* stakes,
not just per-mission.

---

## 10. Open implementation questions

1. **Where does the mis-ID penalty land?** Score, budget, squadron reputation, or a new
   field? Needs a maintainer call (R7).
2. **Moving-target prosecution:** confirm there's no assumption in the strike/scoring path
   that SCAR targets are static — they aren't (R5).
3. **Threat threshold:** what total threat value trips the planner's auto SEAD-escort request,
   so we can stay just under it (R9)?
4. **Map-marker injection:** does the current briefing pipeline support drawing ingress lanes,
   or is it text-only? (R11)
5. **Convoy reuse:** can the existing convoy/unit-transfer plumbing be reused for SCAR movement,
   or does the plugin spawn its own groups?

> Recommend a maintainer/SME eyeball on §6 and §10 before code — that's where the cheap-script
> assumption meets the real codebase.
