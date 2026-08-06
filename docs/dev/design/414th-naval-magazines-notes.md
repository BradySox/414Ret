# Cross-turn naval magazines (§81) — design notes

**Status:** N1 + N2 **LANDED 2026-08-03**. N3 (replenishment) and N4 (unit-card
readout) deferred. In-game pass owed — checklist **B39**, and its first item is the
load-bearing unknown below.

Driven by the flown Marianas 2027 Tacview (374 weapon launches, essentially all
inside the first five minutes) and the DM's read: *"in real life they would not dump
the entire Chinese fleet's magazines in the opening shots of the war — if this
campaign goes 20 turns they can't keep dumping 20+ per turn."*

---

## The problem, precisely

Three separate facts combine into one bad outcome, and they need separating because
they have different fixes.

1. **Ships fire autonomously and instantly.** `TgoGenerator.set_ship_engagement`
   spawns every ship `OptROE.WeaponFree` with alarm RED, because that is the only way
   DCS makes a fleet fight (ship weapons are OPTION-driven; an `EngageTargets` task is
   air-only and crashed the naval AI when tried). So a ship shoots the moment anything
   enters weapon range.
2. **Modern anti-ship missiles out-range the theatre.** The YJ-18 reaches ~540 km
   against a 205 km Guam–Saipan gap. "In range" is permanently true from t=0, so the
   whole fleet salvos in the opening minute rather than fighting a developing battle.
3. **A DCS mission is a fresh spawn.** Loadouts reset every turn, so red re-dumps a
   full magazine every single turn. Sinking hulls is the only way volume ever goes
   down — there is no ammunition dimension to the naval war at all.

Hull culling (Marianas 2027, red 93 → 45 hulls) reduces the size of each salvo. It
does nothing about (1) or (3).

---

## What it was built on

**§63 cruise missile raids is the proven pattern for exactly this**, and the new work
mirrors it rather than inventing anything:

| §63 piece | §81 equivalent |
|---|---|
| `Game.cruise_missile_magazines` | `Game.naval_magazines` (same key: `TheaterGroup.group_name`) |
| `cruise_missiles_state` debrief channel | `naval_magazines_state` (parser now shared — both are `{group=, fired=}`) |
| `reconcile_cruise_missiles` | `reconcile_naval_magazines` (via `commit_naval_magazines`) |
| `cruisemissileluadata.py` | `navalmagazineluadata.py` |
| `resources/plugins/cruisemissiles/` | `resources/plugins/navalmagazines/` |

Critically, the property that makes it safe: **generation never debits.** Only the
debrief report does, so re-generating a turn is free (the §54 lesson). Pinned by a
test on both the campaign module and the emitter.

The `S_EVENT_SHOT` hook needed to count autonomous fire was already used by §39
(snake-and-nape tracks weapon-to-impact) and §77, so the runtime shape was known-good
and the harness already had `fire_shot`.

---

## The tiers as shipped

### N1 — staggered release (`naval_weapon_release_stagger`, default OFF)

Ships generate `ReturnFire`; the plugin releases each group to `WeaponFree` at its own
moment, **spread evenly** across `[releaseMinS, releaseMaxS]` (120–900 s).

Evenly rather than rolled independently per group — the §49 stagger precedent exists
precisely because everything firing in the same frame was itself a measured problem,
and independent rolls on a small fleet can land every release in the same few seconds.

**`ReturnFire`, never `WeaponHold`.** The scope draft said weapons-hold; that was
changed during the build. The point is to delay *initiation*, and a holding fleet is a
defenceless one — there is no reason to make a ship unable to answer an attack while
it waits its turn to be released.

### N2 — the magazine (`naval_magazines`, default OFF)

Persisted per-group anti-ship stock, seeded once from `ASHM_MAGAZINE_BY_TYPE` summed
over the group's alive hulls, emitted as this mission's hard cap, decremented by real
`S_EVENT_SHOT` releases, reported back, debited at the turn boundary. No rearm.

A spent group drops to `ReturnFire` — winchester, not disarmed.

---

## Decisions taken during the build

### Group identity: `group_name`, not `original_name`

The scope draft flagged group identity as an unknown and suggested
`TheaterGroundObject.original_name`. Checked and unfounded: `TheaterGroup.group_name`
is `f"{id:04d} | {name}"` off the **persisted** `TheaterGroup`, which lives in the
campaign save. Mission regeneration recreates the DCS group from that same
`TheaterGroup`, so the key is stable — which is exactly why §63 already keys its
magazines on it. Reused verbatim.

### §63 double-count: solved by disjoint weapon sets, not by unifying

The scope draft suggested unifying the two magazines. Rejected: they meter genuinely
different things (VLS land-attack cells vs anti-ship tubes), §63's is
scripted-`FireAtPoint`-only while §81's is autonomous fire, and unifying would couple
two features that otherwise share nothing.

Instead the **weapon sets are made disjoint by construction**:
`ASHM_WEAPON_PATTERNS` deliberately excludes every land-attack family — no `BGM_109`,
no `3M14`, and nothing as loose as `Kalibr` (which would catch the land-attack 3M14
alongside the anti-ship 3M54). A Burke appears in *both* hull tables, and that is fine
precisely because it carries Tomahawks *and* Harpoons.

**Never add a land-attack family to the pattern list.** A guard test asserts the
land-attack names match nothing.

### Substring matching, not exact weapon ids

Weapon `typeName`s vary by mod and by variant (`AGM_84D`, `RGM_84F_Harpoon`,
`weapons.missiles.AGM_84D`, `CH_YJ18`). Family-level substring matching on the
upper-cased name covers a mod's hull variant without a data edit. Plain matching
(`string.find(..., true)`) — never a Lua pattern, since weapon ids carry magic
characters (the §70 lesson). The list is a plugin option, so a campaign that finds an
unmatched hull can fix it without a code change.

### A dry group is still emitted

Otherwise a fleet that spent its magazine last turn would generate weapons-free and
fight as if freshly loaded. Emitting it with `remaining: 0` lets the plugin either
never release it (stagger on) or pull it back to `ReturnFire` at load (stagger off).

---

## The load-bearing unknown — ANSWERED 2026-08-05, BADLY

**Whether a DCS ship on `ReturnFire` engages an inbound aircraft that has not yet
fired at it.**

DCS ROE is per *group*, not per weapon type: there is no way to say "no more anti-ship
missiles, but keep shooting SAMs". `ReturnFire` is chosen over `WeaponHold` precisely
because it should leave the ship able to defend itself — but whether DCS honours it
that way against an aircraft that hasn't shot first is unverified and cannot be
settled without flying it.

**Flown answer (2026-08-05, two Marianas 2027 missions, Tacviews
`Tacview-20260805-184424` + `-190738`):** an emitter serialization bug (the
`stagger`/`metered` switches were dropped from the miz — see the fix note below) meant
the plugin never released anyone, so both missions accidentally ran a pure held-fleet
experiment: every ship sat on generation-side `ReturnFire` for the full 110 minutes.
Result — **zero ship weapon launches of any kind**, including while blue Super Hornets
put 13 AGM-84D into the SUGARGLIDER Type 071 LHA group and sank the LHA with its
HHQ-16 escorts a few km away, and while an F-22 loitered at 24.9 km from an
054A/052B group. The 2026-08-03 WeaponFree fly of the same theatre produced 99 SM
intercept shots, so the contrast is clean: **a DCS naval group on `ReturnFire` mounts
no missile defense and does not return fire even under direct anti-ship attack.**
A held or winchester group is a defenseless one.

**Decision (DM call, same day): RELEASE-ON-ATTACK — built 2026-08-05.** The hold shapes
who *starts* the war, never who may defend:

- The first **enemy** weapon aimed at a managed group (`S_EVENT_SHOT` with
  `weapon:getTarget()` in the group) or landing on it (`S_EVENT_HIT` — the backstop for
  dumb ordnance; a nil initiator still releases, a known friendly one never does — the
  §77 friendly-fire guard) releases that group to weapons-free immediately, **held OR
  winchester**, and marks it `underAttack`.
- An `underAttack` group that runs dry is **not** re-dropped to ReturnFire (that would
  re-defang a ship the enemy is actively shooting at); it may overshoot its magazine
  defending itself, and the overshoot is still counted and debited (the persisted stock
  clamps at zero). An *unattacked* winchester group still drops — spent and unbothered
  means back to holding.
- The scheduled stagger release is idempotent against an earlier attack release
  (`released` latch), and the event handler now registers under either tier (N1-only
  needs it too).
- Harness pins: immediate release on an enemy targeted shot (+ the scheduled release
  no-op), friendly shot never releases, HIT releases, an attacked dry group is released
  despite the dry-refusal path, and the attacked-winchester keep-defending + overshoot
  count. The stub `WeaponFake` gained `getTarget()` (set via `fireShot`'s optional
  `target` group).

### The re-fly: "CIWS fired but no SAMs" — release the FORMATION, not the group

The first re-fly on the fixed build (2026-08-05, `Tacview-20260805-200950`) proved the
plumbing — `stagger true … metered true` at load, and
`0057 | SUGARGLIDER (LHA) under attack -- released weapons-free` in the log — and the
released LHA did fight: **AK-630 CIWS at t=2644.6**, its first and only shots, dying at
t=2668. But still no SAMs, because **releasing the targeted group is not enough**:

A Retribution carrier/LHA objective is **two DCS groups** — the flagship
(`0057 | SUGARGLIDER (LHA)`) and its escort screen (`0058 | SUGARGLIDER (Escort)`) — and
**the area-defence SAMs are on the escorts**. The 16 AGM-84D were aimed at the Type 071,
whose entire AAW fit is the CIWS it fired; the HHQ-16 escorts **1.91 km away** were never
targeted, so nothing released them and they watched their flagship die.

So an attack now frees every managed friendly group within `formationReleaseKm`
(**default 15 km**). The flown geometry makes that radius unambiguous — measured at the
moment of the attack:

| Group | Distance from the attacked LHA |
|---|---|
| `0058 \| SUGARGLIDER (Escort)` | **1.91 km** |
| `0051 \| OWL (Naval Group)` | 59.02 km |
| `0008 \| PUMA (Naval Group)` | 68.50 km |
| `0053 \| BEAVER (Carrier)` | 94.81 km |

A screen rides ~2 km off its flagship; the next task force is 59 km away. 15 km sits in
the middle of a 57 km gap, so the rule cannot leak into an uninvolved task force.

**One hop, never a cascade.** A neighbour freed by the formation rule does not free *its*
neighbours (`freeGroup` never calls back into `releaseFormationAround`), so a single
attack can never ripple across the map — pinned by a three-group A→B→C test where C is
20 km from the attacked A but 10 km from the freed B.

Also pinned: an enemy formation is never freed by our own attack (coalition check), and
`formationReleaseKm: 0` restores targeted-group-only release.

**Re-fly #2 (`Tacview-20260805-203549`) — the release fires; the shooting is another
matter.** The log shows both lines in the same second (`… under attack` / `… in the
attacked formation`). The full chronology, re-verified against the raw ACMI (3,509
frames, zero backward time jumps):

| t | event |
|---|---|
| 872 s | red's own CJ-10s launch — the mission's first weapons, land attack |
| **2146.8 s** | first AGM-84D leaves the rail, 105+ km out |
| **2154.9 s** | escort's first HHQ-16FE — **at a target it cannot reach** |
| 2158–2214 s | 4 more HHQ-16FE, same story |
| **2638.9 s** | the LHA opens up with its AK-630s (1,273 rounds) |
| **2644.2 s** | first Harpoon arrives |
| 2645–2693 s | escort terminal defence: 5 × HHQ-10 + 194 CIWS |
| **2687 s** | the LHA sinks |

**What is proven:** the escort was weapons-free and firing **eight minutes before any
missile reached the fleet** (first shot 2154.9, earliest arrival 2644.2), so it cannot
have been reacting to a hit — the release-on-attack fired on the *launch*, exactly as
designed, and in the previous fly that same escort sat silent through the whole attack.

**What is NOT proven — and the honest read:** those five early HHQ-16FE shots were
wasted. No enemy aircraft came within **106.3 km** of that escort all mission and the
HHQ-16FE tops out well short of that, so the AI reflex-fired at an unreachable target.
The only effective defence was the terminal HHQ-10/CIWS layer, and it did not stop the
strike: all 16 Harpoons reached terminal at 0.2–2.5 km, none intercepted en route.
Sixteen AShM against two escorts is a genuine saturation strike, so a lost amphib is a
fair outcome — but "the escorts defended their flagship" would overstate it. **Open
follow-up, not a §81 defect:** a released ship burning long-range SAMs on targets outside
their envelope and only defending properly at 3 km is DCS naval AI behaviour; if it
matters, it is its own investigation.

**What that fly did NOT exercise: the magazines.** It carried leftover diagnostic options
`releaseMinS/MaxS = 3600`, so no group was ever released on schedule inside a 48-minute
mission and **no ship fired a single anti-ship missile**. N2 is still unflown; re-fly with
the defaults (120/900). A separate smaller mission the same evening (5 naval groups,
120s–900s) did log a scheduled `released weapons-free`, so the stagger timer itself runs.

### The emitter bug (fixed 2026-08-05)

`LuaData.serialize` ignores a node's `add_key_value` entries whenever the node also
has child items — the magazines list serialized, the two switches silently vanished,
and the plugin correctly read absent-as-false (`NAVALMAGAZINES|: armed -- 29 naval
group(s), stagger false (3600s-3600s), metered false`; the plugin *options* ride a
different injection path and were unaffected). The switches are now named child items
(`node.add_item("stagger").set_value(...)` — the flown CombatSAR `autoSpawn` pattern),
pinned by a serialization-level test in
`tests/missiongenerator/test_navalmagazineluadata.py`. An AST audit across every
`*luadata.py` emitter found no other node mixing the two shapes.

If it does not, a spent (or not-yet-released) ship is also a defenceless one. That may
be acceptable — it is out of the fight either way — but it must be a deliberate call,
not a surprise.

**This is the first thing to test.** If it resolves badly the honest options are to
accept it or to abandon N1's hold entirely; per-weapon ROE does not exist to be
reached for.

Secondary unknowns, all in the B39 checklist row:

- Whether the ROE option id (0) and value (3) the plugin writes are what the DCS
  **naval** controller accepts (`AI.Option.Naval.id.ROE` is read when DCS exposes it,
  with the literals as fallback).
- Whether real weapon `typeName`s on the hulls a campaign fields match the pattern
  list — especially the CurrentHill PLAN ships. If they don't, the magazine silently
  never depletes, which looks exactly like the feature being off.
- Whether a staggered fleet still produces a *fight* rather than one that never quite
  engages.

---

## Deferred

- **N3 — replenishment.** Magazines refill slowly, or only at a friendly port, so
  sustaining a fleet becomes a logistics decision rather than a free reset. Only worth
  building once N2 is flown and the numbers are known to be roughly right.
- **N4 — the unit-card readout.** `tgo_magazines` is already written for it (friendly
  side only, like §63's). `winchester_lines` covers the SITREP half today.

---

## Gates & preseeds

`naval_weapon_release_stagger` + `naval_magazines`, both **Mission Generation → Naval
strike, default OFF** until flown. The `navalmagazines` plugin defaults ON so the
setting is the only gate (the §36 saved-defaults-off lesson).

**Not preseeded in any campaign.** Marianas 2027 is the obvious first adopter once
B39 passes — it is the campaign that produced the finding — but preseeding an unflown
feature into a shipped campaign is how §36 got caught.
