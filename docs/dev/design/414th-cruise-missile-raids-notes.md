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
  no phantom spawns (the §35/§37 discipline), and **MANTIS point defense engages the
  missiles** (the same reason Red Tide fielded the SA-15/SA-19 for ARM defense). A raid
  against a Tor-defended C2 node is a genuine saturation-vs-point-defense game, both
  directions.

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

## The in-game unknowns (B16)

Whether the ship AI ripples the commanded `expendQty` on a *scripted* FireAtPoint push
(the ME-authored task is community-proven; the pushed table is identical but unflown),
which curated hulls honor the cruise flag, Tomahawk/Kalibr terrain behavior at range,
and whether SHORAD actually engages the inbounds in anger. The harness pins everything
up to the DCS boundary (`tests/lua/test_cruisemissiles_runtime.py`).
