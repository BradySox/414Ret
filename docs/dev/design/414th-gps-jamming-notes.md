# GPS jamming (§86) — design notes

**Status: LANDED 2026-08-04; placement/density/reach redesigned 2026-08-05.**
Gated `gps_jamming`, default **OFF**. Preseeded in Operation Baltic Fury only.
Needs an in-game pass (checklist B45).

---

## The constraint that shapes everything

**DCS models no GPS receiver.** There is no scripting API that degrades a jet's
navigation, a weapon's guidance quality, or a JDAM's CEP. Nothing in
`Weapon`, `Controller`, `Unit` or `trigger.action` touches guidance. So the
honest options were:

1. **Do nothing** — GPS jamming is not implementable. (What every previous look
   at datalink/GPS jamming concluded; see
   `414th-iads-c2-consequences-notes.md`, which records GPS jamming as *not
   feasible*.)
2. **Fake it on the aircraft** — impossible for the same reason, and it would
   have to lie to the pilot's own cockpit.
3. **Fake it on the weapon** — track the released store and make it miss.

(3) is the one that works, and it turns out to be *more* honest than it sounds,
because the thing a GPS jammer actually does to a strike package is exactly
"your satellite-guided weapons do not hit what you aimed at."

## The mechanism

`resources/plugins/gpsjamming/gpsjamming-config.lua`:

1. **`S_EVENT_SHOT`** — the release of any store whose type name matches the
   curated satellite-guided pattern list starts a track.
2. **One roll, once** — the first sample the store is inside a live *enemy*
   jammer's reach, roll `degradeChancePct`. The outcome is remembered either
   way, so a long glide through a bubble cannot re-roll itself into a
   certainty.
3. **The store flies its whole normal profile.** No teleport, no early bang.
4. **Terminal gate** — at 100 ft AGL the weapon is `destroy()`ed and a
   `trigger.action.explosion` is produced at a scored offset from where it was.

The pilot sees the release, the fall and the detonation, just in the wrong
place. Miss distance scales with jamming strength (1 at the emitter, 0 at the
edge of the bubble), so a store clipping the fringe is nudged and one released
overhead is thrown clear.

### The predictive terminal gate (the non-obvious bit)

A plain `agl <= floor` test **fails for fast weapons**. A store descending at
400 m/s covers 800 m in a 2 s sample step, so it can be at 900 m AGL on one
tick and already detonated on the aimpoint by the next — the jamming silently
does nothing, which is the worst possible failure mode (it looks like the
feature is off).

The gate is therefore predictive: fire when the store would already be *through*
the floor by the next sample —

```lua
floor = max(TERMINAL_AGL, descentRate * TRACK_STEP * 2)
```

so a coarse sample step makes the destroy happen *higher*, never later than
impact. `tests/lua/test_gpsjamming_runtime.py::test_a_fast_store_is_caught_before_impact`
pins it.

### What happens if we lose the race anyway

If the weapon vanishes before the gate (it impacted, or a SHORAD killed it), the
track is simply dropped. A degraded store that gets that far **hit normally and
is deliberately NOT re-detonated** — we cannot know it did not already do its
damage, and inventing a second explosion would be a phantom effect (the
§35/§37 discipline).

## No phantom spawns, no invented losses

- The store is a **real weapon from a real jet** — the jet paid for it, the
  sortie flew, and the loadout is the one the planner built.
- This script **spawns nothing** and **owns no kills** beyond producing the miss
  explosion. Any damage that explosion causes is ordinary DCS damage, recorded
  natively at debrief.
- The jammer itself is an ordinary strikeable ground TGO. Killing it removes it
  from the live-site check on the very next weapon, so **accuracy returns inside
  the same mission** — the reward for finding and striking it is immediate.

## Identification: the unit-yaml contract

The *presence* of a `gps_jamming` block in a ground unit's own data file is what
makes that unit a jammer:

```yaml
# resources/units/ground_units/<unit>.yaml
class: Fortification
price: 40
gps_jamming:
  radius_nm: 15        # optional — falls back to the campaign setting (15 nm)
  miss_radius_m: 350   # optional — falls back to the campaign setting (200 m)
variants:
  R-330Zh Zhitel: null
```

`gps_jamming: {}` (or `true`) is a jammer on the campaign defaults.

This is the §24 `date_gated_properties` precedent — era data lives in the unit's
own file — and it is deliberately chosen so that **adding a jammer to the fork
is a data edit**: register the vehicle, write its yaml, add the block. No id
list in Python needs touching, so unit work and feature work never have to land
together.

A site with several jammer types takes the **longest declared reach** and the
**worst declared miss**: the strongest emitter present is what the weapon
actually hears.

## The curated weapon list

`GPS_GUIDED_WEAPON_PATTERNS` in `game/fourteenth/gps_jamming.py`, emitted to Lua
so the list has exactly one home. Matched as **plain case-insensitive
substrings, never Lua patterns** — weapon names carry `-` and `(`, which a
pattern match reads as magic (the §70 lesson).

**In:** JDAM (GBU-31/32/38), GBU-54 (Laser JDAM — its *baseline* mode is
GPS/INS and the runtime cannot see whether anyone is lasing), JSOW, JASSM,
SLAM-ER, WCMD dispensers, KAB-500S/1500S (GLONASS, so red eats its own medicine
wherever blue fields a jammer).

**Out, and load-bearing:** every laser, TV, IR and anti-radiation weapon. A
Paveway that mysteriously misses is a bug report, not a feature. Also out:
**ship-launched land-attack cruise missiles** (§63/§81) — they are their own
flown features and coupling them to an unflown one buys nothing.
`tests/fourteenth/test_gps_jamming.py` pins both directions.

## Squadron calls (2026-08-04/05)

| Call | Decision |
|---|---|
| Whose weapons | **Symmetric.** A site degrades the *opposing* coalition only. Red will own the jammers in practice, but a blue jammer works the day one is fielded. |
| Does the player know | **Both halves.** A recon-**fogged** kneeboard line (an un-scouted jammer is *not* briefed — finding it is worth a recon sortie) **and** a one-shot in-cockpit cue the first time a flight's weapon is spoofed, so a failed pass reads as jamming rather than as a broken sim. |
| Weapon scope | **GPS-guided air ordnance only** (see above). |

## Defaults, and why

- **15 nm reach.** Sized off what the bubble IS — a denied *target* area (see the
  2026-08-05 pass below). At 27-30 nm one site denied a large share of a medium
  map; 15 nm denies a target cluster.
- **85 % degrade chance.** Below 100 so some stores get through: a package can
  still score inside a jammed area, and the player cannot conclude "GPS is
  simply disabled".
- **200 m miss at full strength.** A clean miss that still reads as "the bomb
  went long", not "the bomb vanished".
- **400 kg miss explosion**, deliberately below a real JDAM warhead: a jammed
  bomb is a miss, not a relocated hit.

## Making the jammer huntable (RWR / HARM) — 2026-08-04

The DM asked whether the EW truck could be made to emit something RWR and HARM
can see. Checked against the installed DCS, not from memory.

**The stock unit emits nothing.**
`CoreMods/tech/TechWeaponPack/Database/vehicles/Unarmed/Radio_jammer_Red.lua`:

```lua
GT_t.ws = 0                       -- no weapon system at all
GT.DetectionRange = 50000
GT.attribute = { ... "Trucks", "Jammer" }
-- no GT.WS, no GT.Sensors, no searchRadarFrequencies
```

A unit only lights an RWR / draws an ARM when it declares an emitter. The SON-9
sitting next to it in the same pack has all three:

```lua
GT.WS.radar_type = 103                            -- the RWR lookup ID
GT.WS.searchRadarFrequencies = {{2.7e9, 2.9e9}}   -- the band an ARM homes on
GT.Sensors = { RADAR = "son-9 tr" }
GT.attribute = { ...wsType_Radar... }
```

This is faithful — a real GPS jammer transmits in L-band, which no RWR covers and
no HARM homes on — and **unplayable**: the jammer could only ever be found by
recon, and SEAD could never prosecute it.

**The mod route (offered, declined).** A vehicle mod cloning that DB entry and
adding the four lines would work, and needs no 3D work (mods can reference an
existing ED model). Two caveats made it the wrong first move: every client must
install it (the CH-pack situation), and **each aircraft module ships its own RWR
lookup table**, which a mod cannot extend — so a *new* emitter ID renders as
unknown/blank on most jets, and the practical choice is to borrow an existing
`radar_type`, at which point the contact reads as that SAM radar anyway.

**The vanilla route (chosen).** Pair the jammer with a real emitter instead: an
optional `GPS Jammer 0` slot on the **`Early-Warning Radar` layout** plus the
`GPS Jamming Site (Red)`/`(Blue)` presets. An EWR is the right partner
specifically because **MANTIS never holds an EWR dark** — detection rides on
dedicated EWR sites and AWACS — so the site is *always* emitting. It paints
RWRs, takes HARMs, and SEAD services it like any other radar, with zero mod and
zero integrity-check exposure.

Non-regression is structural: the slot is `optional: true` + `fill: false` and
the presets are opt-in, so every shipped EWR site generates exactly as before.
Country gating keeps each side to its own jammer (test-pinned).

**This pairing is what forced the per-unit liveness contract.** The jammer shares
its DCS group with the radar, so the original group-level `siteAlive` check would
have kept denying GPS on the strength of the surviving radar beside the wreck of
the actual jammer — unkillable jamming. The emitter now sends jammer **unit**
names (`TheaterUnit.unit_name`) and the runtime checks `Unit.getByName`, so:

- kill the **truck** → jamming stops, radar still on your RWR;
- kill the **radar** → site off RWR, jamming continues.

Both are worth a bomb, for different reasons.

## Placement, density and reach — the 2026-08-05 design pass

The first cut bolted the jammer onto the EWR layout. That was a workaround, and
the DM stopped it: *"we gotta think this through and do it right."* The pass
turned up one fact that reframes everything, and three decisions.

### The fact: the bubble is a denied TARGET area, not a denied RELEASE area

The runtime degrades a weapon that *flies through* a live bubble. A weapon aimed
at anything inside the bubble therefore passes through it **whatever range it was
released from**. Standing off does **not** help against a covered target; it only
changes *which* targets are covered. The radius is simply the size of the target
set that loses satellite guidance.

Earlier drafts of this note (and the settings text) listed "stand off" as a
counter. That was wrong and is corrected: the counters are **change delivery
method** (laser/TV are untouched) or **kill the jammer**.

### Decision 1 — placement: both models

| Model | What it is | When to use it |
|---|---|---|
| Standalone `GPS Jamming Site` | Own marker, own point defence, own ARM-able radar | Denial anywhere: an objective, an approach, a bridge |
| Attached `S-300 Site GPS Jammer` section | A slot on the S-300-family layouts, used by `SA-20/S-300PMU-1 (GPS jamming)` | Denial *inside* a threat ring — killing it means entering the S-300's envelope |

A jammer alone in a field is a free kill and nobody has to think; a jammer inside
a SAM ring is the actual dilemma. But denial is often wanted where no SAM is, so
both exist. Both are `optional` + `fill: false` and preset-driven, so every
shipped site generates exactly as before.

### Decision 2 — density: ≤3 per campaign, non-overlapping, CI-guarded

Bubbles are large and **invisible on the campaign map**, so a heavy hand is easy
to author and hard to notice until someone flies it — the Marianas lesson, where
13 of 30 max-radius rings "did not make the campaign harder, it made the map
unreadable".

Overlap is called out separately because **effects do not stack**: a weapon faces
only the single strongest bubble covering it (the §77 non-stacking rule), so a
second overlapping site adds no decision and killing one restores nothing.

Both rules are enforced by tests that walk every campaign's `ground_forces` pins.

### Decision 3 — reach: 15 nm

Deliberately below the 50 km (27 nm) DCS declares for the vehicle. At 27 nm a
single site denied a large share of a medium map, which switches a weapon class
off rather than posing a question. 15 nm denies a target *cluster*, so two or
three can coexist on distinct clusters and most of the theatre stays GPS-usable.

### The access trap, worth knowing before authoring

The override gate is `all(u in faction.accessible_units for u in fg.units)` — one
unreachable unit silently discards the whole pin and the marker falls back to an
ordinary site. `accessible_units` chains `preset_groups`, so registering the
preset there grants access **but also makes the site a `random_group_for_task`
candidate**: unpinned EWR markers then roll jamming sites and the campaign
generates a different shape every time (measured 2-to-4 sites when only 2 were
pinned). **Grant access through `air_defense_units` instead.**

The cost of that route is that a granted unit joins the faction-fill pool: the
ST-68U turned up as a search radar at an unrelated SAM site in roughly one game
in five. Accepted deliberately — an ST-68U is era-plausible wherever it lands for
a 2027 Russian faction, and era-correctness at the jamming site (the thing the
player looks at) matters more. The alternative, reusing the faction's native
ARM-flagged radar, is a 1950s SA-2 Fan Song.

### Engine bug found on the way

`generate_ewrs` called `random_group_for_task` directly and never read the
`ground_forces` block, so **an EWR marker could not be pinned at all** — the
identical hole naval groups had until `generate_navy` was routed through
`get_unit_group_for_task` (2026-08-03). Fixed the same way; upstream-carve
candidate, and independent of this feature.

## What the player does about it

1. **Change delivery method** — laser and TV weapons are unaffected. This is the
   intended counter and the reason the exclusions are load-bearing.
2. **Kill the jammer** — an ordinary strike, with an immediate in-mission reward.

Standing off is **not** a counter for a covered target (see the bubble note
above); it only decides which targets are covered in the first place.

## Deliberately not done

- **Aircraft navigation degradation** — impossible (no API), and it would have
  to lie to the pilot's own cockpit.
- **A map overlay for jamming areas** — the site is an ordinary TGO and already
  draws (fogged, or as a §3 concealment circle if concealed). A dedicated ring
  would double-draw it.
- **Coupling to §74 DTC** — a cartridge carries steerpoints, not guidance
  quality; there is nothing to degrade there.
- **Planner coupling** — the auto-planner does **not** avoid jammed areas or
  re-pick loadouts. That is a real follow-up (route/loadout awareness), kept out
  of v1 so the runtime can be flown on its own first.

## In-game pass (checklist B45)

The DCS-only unknowns, in order of risk:

1. **Does the terminal gate beat a real JDAM's terminal profile?** The harness
   flies a constant-rate descent; a real store's last seconds are steeper. If a
   bomb ever detonates on target *and* produces a miss explosion, the gate lost
   the race — raise `terminalAglFt` or shorten `trackStepS`.
2. **Does `Weapon:destroy()` on a live store look clean in the cockpit/Tacview**,
   or does it read as a disappearing bomb?
3. **Is the miss legible?** 200 m off should look like a miss, not a bug.
4. **Does the cue land once per flight**, and does the kneeboard line appear only
   after recon has found the site?
