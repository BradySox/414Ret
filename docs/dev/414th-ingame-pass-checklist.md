# 414th In-Game Pass Checklist

Most 414th features are validated by careful reading + Python tests, but their
**runtime behavior cannot be exercised in CI** — the Lua plugins, the planner's
spatial placement, and the MOOSE dispatcher only show their true colors in a
live DCS mission. The engineering doc
([414th-features.md](414th-features.md)) tags these as *"needs an in-game
pass."* This file is the **tracker** that turns those scattered tags into a
verdict-producing protocol: one row per outstanding check, each with an
observable pass criterion and the failure signature to watch for.

Update a row's **Status** when you fly it. Don't mark `VERIFIED` on a hunch —
it means *"I watched for the fail signature and it did not occur,"* ideally with
a Tacview/log reference and a date. When a row reaches `VERIFIED`, also drop the
*"needs an in-game pass"* tag from the matching section of `414th-features.md`
so the two docs don't drift.

## Status legend

| Mark | Meaning |
|---|---|
| ☐ UNTESTED | Built; no in-game observation yet |
| ◐ PARTIAL | Flown, but not under the conditions that stress the fix |
| ☑ VERIFIED | Watched for the fail signature in-game; did not occur (note date/Tacview) |
| ✗ REGRESSED | Fail signature reproduced in-game — reopen the fix |

---

## A. Air-to-air / QRA

### A1 — QRA air-spawn profile · §1 · ☐ UNTESTED
- **Setup:** Campaign with alert reserves; trigger an enemy raid so a QRA pair
  scrambles. Include at least one **high-elevation** alert base (e.g. Vaziani).
- **Pass:** Scrambled jets spawn at a sane speed and a terrain-relative LOW
  altitude, then climb/turn to intercept under control.
- **Fail signature:** Jets air-spawn stalled (~0 kt) and dive clawing for
  airspeed (the Su-27-nearly-hit-the-ground-at-Vaziani case, Tacview
  2026-06-20). Check `SCRAMBLE_SPEED_KT` / `SCRAMBLE_AGL_M` in
  `intercept-config.lua` if seen.

### A2 — QRA base-defense doctrine · §1 · ☐ UNTESTED
- **Setup:** Default doctrine (`qra_gci_max_radius_nm` 60, `qra_engagement_range_nm` 38).
- **Pass:** QRA scrambles only when a raid closes within ~60 NM and interceptors
  don't chase far past the FLOT — they screen their own base, not the front line.
- **Fail signature:** QRA pushing forward over the FLOT (the pre-tuning
  behavior that prompted lowering the radii).

---

## B. Planner placement / target logic (Lua-free Python)

### B1 — Forward-CAP / FLOT depth on coastal fronts · §6 · ☐ UNTESTED
- **Setup:** A campaign on a **coastline / river / narrow-land** front.
- **Pass:** Deep ground roles (artillery, logistics) spawn at depth and spread,
  not in direct contact.
- **Fail signature:** Deep groups stacked in contact at depth 0 because the
  perpendicular walk hit water/off-map (the bug the lateral fallback fixes).

### B2 — DEAD reachability gate on follow-on strikes · § DEAD · ☐ UNTESTED
- **Setup:** A target behind an intact SAM belt that blue wants to strike.
- **Pass:** Blue still tasks the DEAD (with SEAD escort) but **defers the deep
  strike** until the belt is actually down.
- **Fail signature:** Blue sends the follow-on strike into a live belt because
  it trusted an optimistic DEAD clear.

---

## C. Support flights

### C1 — AWACS/tanker orbit front-anchor · #84 · ☐ UNTESTED
- **Setup:** Any campaign with AWACS + tanker support.
- **Pass:** Support racetracks anchor on the FLOT, behind the front.
- **Fail signature:** Red AWACS flung far off-axis (the ~175 NM case #84 fixed).

### C2 — Support orbit depth behind FLOT · #86 · ☐ UNTESTED
- **Setup:** As C1; watch where the orbit actually sits relative to threats.
- **Pass:** Orbits hold **deep** behind the FLOT, clear of forward SAM/CAP reach.
- **Fail signature:** Support orbit placed within enemy engagement depth.

---

## D. Loss accounting (upstream-core)

### D1 — Player-despawn loss suppression · §8 · ◐ PARTIAL
- **Setup:** Player despawns/jumps seat mid-mission (not an ejection, not a
  shootdown), then the mission ends.
- **Pass:** Airframe + pilot are NOT logged lost; a real shootdown and a real
  ejection still DO count.
- **Fail signature:** Surviving player jet logged lost (the GERBIL F-14 case).
- **Residual to watch:** if the engine tears the mission down without
  per-player `PLAYER_LEAVE_UNIT` events, despawn-crashes aren't caught —
  land/despawn before ending remains the belt-and-suspenders.

---

## E. SOF insert generation · #85 · ☐ UNTESTED
- **Setup:** A SCAR commander-capture campaign that plans a SOF C-130 insert.
- **Pass:** The SOF C-130 **ground-starts** (incl. the runway fallback when no
  parking is free) and the **EW (`c130j`) plugin is skipped** on that airframe.
- **Fail signature:** SOF C-130 air-spawns, or the EW menu/behavior bolts onto
  the SOF insert because the airframe matched `eligibleTypeNames`.

---

## F. SCAR

### F1 — HVT movement + SOF capture loop · §15 · ☐ UNTESTED
- **Setup:** SCAR tasking (spawn/armor variant) with `scar_command_post_intel`
  ON and a purchased SOF team allocated.
- **Pass:** HVT (incl. towed/SCUD groups) actually **drives** toward the city on
  activation (alarm-GREEN route); the SOF capture resolves `captured` when the
  un-killed command vehicle enters `SCAR_SOF_CAPTURE_RADIUS_M` (600 m) with the
  SOF group still alive. Priority killed > captured > escaped/timeout.
- **Fail signature:** HVT sits still (the alarm-RED pinning bug — do NOT revert
  the `mist.goRoute` alarm-GREEN route; a hand-rolled `setTask` did not move
  them); or `captured` never fires / fires after the vehicle is dead.

### F2 — Command-post intel fog · §15 · ☐ UNTESTED
- **Setup:** New campaign (default `scar_command_post_intel` ON).
- **Pass:** Enemy command posts are **entirely hidden** from the player map
  (no marker, not in target list) until a commander is captured or normally
  discovered; then they reveal with exact coords, permanently. AI/planner are
  unaffected (ground truth).
- **Fail signature:** Command posts visible on the player map before reveal, or
  a reveal that doesn't persist across turns.

### F3 — Player-flown SOF insert + C-130 EW exclusion · #56 / §15 · ☐ UNTESTED
- **Setup:** Plan a `FlightType.SOF` insert flown by a C-130J-30.
- **Pass:** The player can fly the air-assault-shaped delivery; the `c130j` EW
  plugin is skipped for that mission (logged).
- **Fail signature:** EW menu appears on the SOF insert; or the insert can't be
  planned/flown by the fixed-wing transport.

### F4 — Results bridge round-trip · §15 · ☑ VERIFIED (2026-06-17/18)
- Verified in-game: `SCAR area scar-N: launched/failed` round-tripped through
  the TARS channel into the debrief. No action; listed for completeness.

---

## G. Plugin runtime (Lua, not CI-runnable)

### G1 — Flight Control: AI flow unaffected + no spot spam · §13 · ☐ UNTESTED
- **Setup:** Default ON; a base where Retribution parks STATIC objects on ramp
  spots (e.g. Kutaisi/Kutaisi-like).
- **Pass:** AI QRA/CAP **launch normally** from FLIGHTCONTROL bases (players-only
  is pragmatic, not a hard gate); no "Number of parking spots does not match!"
  spam (orphan spots marked `RetributionStatic`).
- **Fail signature:** AI scrambles queued/strangled, or the parking-mismatch
  warning every cycle (138× in one playtest before the orphan-reconcile fix).

### G2 — TARS BDA bridge · §12 · ☐ UNTESTED
- **Setup:** Fly an F-14 TARPS recon pass over enemy targets.
- **Pass:** Captured-target snapshots feed back into Retribution's BDA
  fog-of-war (confirmed composition/damage after the pass).
- **Fail signature:** Film menu never unlocks, or captures don't reach the
  debrief / don't update BDA.

### G3 — TIC ambient fire / dynamic fronts · §9 · ☐ UNTESTED
- **Setup:** Fly over an active front, including where terrain (towns/ridges)
  blocks line-of-sight between combatants.
- **Pass:** The front looks **alive from the air** — tracers/impacts around real
  enemy positions even where LOS is blocked (ambient area-fire), without aimed
  lethality spikes.
- **Fail signature:** Front goes silent/dead-looking where LOS is blocked.
  Note: with StormTrooper AI on (default), TIC cloaks managed groups — known
  limitation, not a bug.

### G4 — C-130J EW/ISR mission systems · §2 · ☐ UNTESTED
- **Setup:** Fly the C-130J-30 JAMMING slot (static slot, player-only).
- **Pass:** EW (area/directional/spot jamming, missile spoof, pod loadout) and
  ISR (passive detection, ELINT map marks, SIGINT reports, crew handoff) work
  per `C-130J-30 Mission Systems Overview.txt`.
- **Fail signature:** Menu missing/erroring (would now be caught earlier by the
  Lua syntax gate), or any of the documented EW/ISR actions not firing.

---

## How this feeds the other threads

- A row that reaches **✗ REGRESSED** is a concrete bug to fix.
- A cluster of **☑ VERIFIED** Lua-free Python rows (B, C, D, E) are the
  upstream-PR candidates — verify in-game, then carve them out (see the
  upstreaming inventory).
