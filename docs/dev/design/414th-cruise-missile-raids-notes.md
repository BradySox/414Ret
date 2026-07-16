# 414th — Ship-Launched Cruise Missile Raids (§63)

**Status:** LANDED 2026-07-15 (Tier 1 player call-for-fire + Tier 2 auto raids, one PR).
Feature §63; checklist B16 (needs an in-game pass). This note records the design calls;
the engineering internals live in `docs/dev/414th-features.md` §63.

## The gap

DCS warships with land-attack cruise missiles — the vanilla Arleigh Burke's Tomahawks,
the CurrentHill packs' explicit Kalibr hulls (`CH_*_LACM`, `CH_Ticonderoga_CMP`) — can
strike shore targets via a `FireAtPoint` task carrying the cruise-missile weapon flag
(`2097152`); mission editors have used that for years. Retribution never tasked them:
ships were ANTISHIP targets, carrier decks (§44 plans the *air wing*, never the hull's
weapons), and the §34 Vietnam gun line (`TaskFireAtPoint` with **no** weaponType — guns
only, 10 NM). So a fleet full of TLAM cells contributed nothing, and red's Kalibr ships
(already in `redfor_current`/`redfor_russia_2020`) were inert props.

## What made this cheap and honest

Every §63 building block already existed:

* **The DCS mechanism is one parameter** on the §34 machinery (MOOSE
  `TaskFireAtPoint(vec2, radius, ammoCount, weaponType)`).
* **The force model is already right**: the launching ship is a real, tracked TGO unit;
  the missiles are real DCS weapons killing real tracked units/statics, so BDA lands at
  debrief through the ordinary death events — zero debrief-schema change for the strikes,
  no phantom spawns (the §35/§37 discipline). ~~and **MANTIS point defense engages the
  missiles** (the same reason Red Tide fielded the SA-15/SA-19 for ARM defense)~~ —
  **WRONG as assumed, disproven by the 2026-07-16 flown test** (see "The intercept gap"
  below): no defender in the stack ever woke for a cruise raid on its own. The plugin's
  **defender launch wake** (built same day) now brings the AD around the aimpoint to
  alarm-RED for the flight window, so the saturation-vs-point-defense game can happen;
  the re-fly is owed.

## Design calls

1. **A campaign magazine, debited only by the debrief report.** DCS silently rearms every
   mission, so unmanaged ships would fire a free full salvo every turn — the exploit that
   sinks the feature. Each launching group carries a persisted stock
   (`game.cruise_missile_magazines`, keyed by the stable `TheaterGroup.group_name`,
   seeded from a per-hull table: Burke 24, the 8-cell UKSK corvettes 8). The **only**
   debit site is the plugin's `cruise_missiles_state` mirror (the §57 minefields channel
   pattern) folded in at the turn boundary — planning/generation never debits, so mission
   re-generation can never double-count (the §54 lesson). **No rearm, deliberately**: the
   magazine is the war stock ("60 TLAMs for the campaign"), and "a salvo spent on a truck
   park is a salvo you won't have for the command bunker" is the whole economy. A slow
   rearm-in-port could be added later; it needs a port/logistics model §53 doesn't have.
2. **Emitter-time planning, not a `Coalition.plan_missions` hook.** §44 hooks the plan
   pass because it consumes squadron airframes; a cruise raid consumes nothing the ATO
   tracks. `plan_cruise_raids` is a pure function of game state called by the emitter —
   idempotent across regenerations, no pickle state for the raid itself, nothing to
   migrate. (Cost: the raid isn't visible in the ATO UI pre-flight. Acceptable for v1;
   a SITREP line is the cheap future surfacing.)
3. **Curated hull set, Python-side authority.** DCS/pydcs expose no per-ship weapon
   taxonomy, so eligibility is the hand-audited `LACM_SHIP_DCS_IDS` (the §41 curated-data
   pattern). The Lua side deliberately does **not** re-derive eligibility from
   `getAmmo()` — a wrong Python entry degrades to a logged no-fire, and the in-game pass
   (B16) is the arbiter for the least-certain hull (the vanilla `TICONDEROG`). AShM-only
   sister hulls (`CH_*_AShM`) are excluded by name: anti-ship is the ANTISHIP task's job.
4. **One raid per side per turn, C2-first.** The raid is punctuation, not a bombardment
   loop: commandcenter/comms first (composes with §52 decapitation), then the §53
   war-economy buildings, then anything strikeable — nearest wins ties; ≤ 250 NM planning
   reach; BLUE raids honor the §40 `roe_blocks_target` gate (red raids don't — the ROE is
   Washington's); never ships (moving targets a point-fire task can't lead), never
   `map_hidden` §50 ambush teams (naming them would reveal them — the carrier-strike
   skip).
5. **The defender hears a launch warning, not targeting intel.** The launching side's cue
   names the target; the defender gets only "LAUNCH WARNING — enemy cruise missile launch
   detected". Real-ish EW fidelity, and it's the gameplay hook: scramble/alert the point
   defense without being told where.
6. **Symmetric by construction.** Both sides' ships emit, both get the F10 menu, red auto
   raids need only the same two toggles. Default OFF (both settings) until flown; the
   plugin's own `defaultValue` is ON so the settings are the single gate (the §36
   saved-default-off lesson).

## Deferred / rejected

* **ATO/package integration** — ships can't be package members; a pseudo-package UI is
  not worth it. The middle ground (right-click an enemy TGO → "Request cruise missile
  strike", the §35 route right-click pattern) is the natural Tier 3 if the F10 flow
  proves too coarse.
* **SITREP raid line** ("Cruise missile raid struck X — N intercepted") — cheap, wants
  the §29 pattern; do it once the runtime is flown and the cue text has settled.
* **Rearm at port / munitions-family integration (§54)** — needs a port-call model; the
  scarce-munitions taxonomy is aircraft-loadout-keyed and doesn't fit ship cells today.
* **Targeting moving ships** — rejected outright; that's ANTISHIP.
* **Runtime `getAmmo` eligibility scan** — rejected for v1 (call 3 above).

## The in-game unknowns (B16) — RESOLVED 2026-07-16 (flown PG "Scenic Route" test)

The core loop passed: the scripted FireAtPoint push fires the exact commanded quantity
(6 commanded → 6 BGM-109C shot events) on both vanilla hulls (the "least certain"
`TICONDEROG` flew the raid; a Burke group flew the F10 call-for-fire + a raid); the
missiles cruised to the C2 target and killed it natively; the magazine debited 16→10
and persisted; next turn re-targeted the next command center. Still unflown (minor):
`#N` marker salvo sizing, the CH Kalibr hulls, red-side raids, magazine exhaustion.
The harness pins everything up to the DCS boundary
(`tests/lua/test_cruisemissiles_runtime.py`).

## The intercept gap (observed 2026-07-16 — fix built same day, re-fly owed)

**No defender engages a cruise raid.** The user watched the target's point defense —
`0011 | SLUG (SHORAD)`, 2× alive SA-15 Tor + Dog Ear SR, ~250 m from the impact point —
sit idle through the whole 6-missile salvo. Root cause, code-confirmed, and it is
structural, not a fluke:

1. **Vanilla groups (SLUG's case)** carry no alarm-state option, so they run DCS's
   default **ALARM STATE AUTO — which never goes weapons-hot for a *weapon* object**.
   Only aircraft trip the auto-wake; the site's radars stay cold as missiles fly past.
2. **MANTIS-managed SAMs** are EMCON-dark and wake off MOOSE `Detection`, which scans
   **units** — a weapon object is invisible to it, so a managed site is equally blind.
3. **The SHORAD link's** wake watch (`SHORAD.Harms`/`SHORAD.Mavs` in MOOSE) lists ARMs
   and Mavericks — **no `BGM_109`, no Kalibr** (MOOSE's `SEAD.HarmData` *does* carry
   BGM_109, but that's the evasion class, not the SHORAD wake list) — and the other
   trigger is MANTIS SEAD suppression. A cruise launch trips neither. (Red also had
   **zero** linked PD groups here: the bridge wraps only `IadsRole.POINT_DEFENSE`
   escorts of SAM nodes, and SLUG is a standalone SHORAD TGO guarding a C2 site.)

**Fix BUILT (2026-07-16, same session — squadron call: option 1, the plugin-side
wake):** `fireCruise` now ends every launch (raid and call-for-fire share it) with
`wakeDefenders`: sweep the opposing side's ground groups, keep those with an alive
`"Air Defence"`-attributed unit within `defenderWakeRadiusNm` (default 8 NM) of the
**aimpoint**, and set each **alarm state RED** via `Controller:setOption` — alarm
state ONLY, `enableEmission` stays untouched (the crash-history constraint). The hold
lasts an estimated flight time (`dist/200 m/s`, a low speed estimate so the window is
generous) + `defenderWakeExtraS` (default 300 s); `standDownDefender` then restores
ALARM AUTO, with per-group `wakeUntil` bookkeeping so overlapping launches extend
rather than clobber the hold. A MANTIS-managed site keeps its own EMCON loop (MANTIS
may re-dark it — that is MANTIS's call to make); it is thematically the LAUNCH WARNING
doing its job. Options: `defenderWake` (default true) / `defenderWakeRadiusNm` /
`defenderWakeExtraS`. Harness-pinned (wake + stand-down + far/friendly/non-AD
selectivity + the kill switch) in `tests/lua/test_cruisemissiles_runtime.py`; the
harness gained `Controller:setOption` recording + the vanilla `AI.Option` enums.
The rejected narrower alternative — adding cruise weapons to the SHORAD link's wake
set in the MANTIS bridge — only covers *linked PD escorts of SAM nodes* (zero groups
on red in the flown test), so it cannot fix the common case alone. **Needs a re-fly
(B16):** pass = the wake log (`CRUISEMISSILES|: defender wake -- N AD group(s) near
the aimpoint held RED`) fires on launch and the SA-15 visibly engages the inbounds
(Tacview: 9M331 launches at BGM-109s); fail signature = the wake log fires but the
Tor still never shoots (then the residual gap is DCS's own Tor-vs-TLAM engagement
logic, not alarm state), or defenders stuck RED long after the raid (stand-down
broke).

**Second flown test, same day (turn 3, pre-wake build — Tacview
`Tacview-20260716-014958`):** the raid onto INSECT sharpened the picture on both
sides of the claim.

* **The gap's linked-PD variant is now flown, not just code-derived**: this laydown
  armed red's SHORAD link (3 PD groups held dark, `0122 | DINGO (PD)` — a Tor pair —
  5 km from INSECT), and DINGO fired nothing as the salvo arrived. Both dark states
  are now observed in the air: vanilla ALARM AUTO (turn 2's SLUG) and link-dark
  (turn 3's DINGO).
* **A defender that CAN shoot, kills**: a red Krivak pair (`0115 | NAUTILUS`) sitting
  in the flight path fired 13 SA-N-4s and **killed 2 of the 6 Tomahawks** (removal
  timestamps match the missile terminals to the second). Ship AD has no alarm-state
  model — it is always hot — which is exactly the "already hot for another reason"
  caveat, and it proves the saturation-vs-point-defense game works the moment a
  defender is awake. The wake fix's job is precisely to give ground PD what ships
  already have.
* **Fix-coverage confirmation**: the bridge builds its SHORAD with `useEmOnOff =
  false`, so linked PD is darkened via **alarm GREEN** (MOOSE `_InitState`'s else
  branch) — the wake's alarm-RED `setOption` overrides that directly. No emission
  toggling is needed to reach any of the three ground management states (vanilla,
  MANTIS-EMCON, link-dark): all of them are alarm-state-based in this fork.
* Incidentals: one Tomahawk flew into the interior mountains at ~1250 m (FireAtPoint
  gives no terrain-following route — a known DCS behavior, acceptable losses); the
  three survivors impacted within 60–257 m of the aimpoint; the same-turn re-fly
  logged the identical `4 left`, flown proof of the turn-boundary-only debit.
