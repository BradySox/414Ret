# Carrier Deck Decorations (§72) — OCN 2 deck dressing, parking-safe

**Status: LANDED 2026-07-18.** User request: "Take a look at the deck layouts and
decorations in [the 13 OCN 2 missions]. I wanna apply them to ALL retribution carriers
for flavor. BUT we need all of the parking spots still usable. If you want to block a
catapult that is fine."

This note records where the data came from, what the parking evidence is, and why
specific OCN decorations were dropped — so a future edit argues with the evidence, not
with vibes.

## Source: what OCN 2 actually does

All 13 missions of Sedlo's OCN 2 (`E:\DCS World\Mods\campaigns\FA-18C Operation
Cerberus North 2\OCN 2 Mission N FINAL.miz`) dress the CVN-75 Truman with 12–27
**ship-linked statics**. In the miz format a linked static splits across three levels
(this is the part stock pydcs doesn't model):

```lua
[699] = {                       -- the static GROUP
    ["linkOffset"] = true,      -- group level
    ["route"] = { ["points"] = { [1] = {
        ["linkUnit"] = 6923,    -- route point: the carrier's unitId
        ...
    }}},
    ["units"] = { [1] = {
        ["offsets"] = {         -- unit level: the ship-frame placement
            ["x"] = -47.9, ["y"] = 20.1, ["angle"] = 4.625,  -- rad
        }, ...
    }},
}
```

Ship frame: x along the keel (fwd +), y athwartships (stbd +), angle relative to ship
heading. DCS re-derives world position from the offsets every frame — the statics ride
the steaming boat.

**OCN's vocabulary** (type → what it is → where it lives):

| type | what | where | missions |
|---|---|---|---|
| `Carrier LSO Personell` / ` 1` / ` 3` / ` 4` | LSO team figures | port-aft platform (x≈−130, y≈−21) | 13/13, byte-identical |
| `AS32-31A` / `AS32-32A` | deck tow tractors | island street | all |
| `AS32-p25` | P-25 firefighting vehicle | island street | most |
| `CV_59_H60` | **Hyster 60 forklift** (not a helo!) | island street | 6 missions |
| `us carrier tech` | deck-crew figure | island street clusters | all |
| `AS32-36A` | crane | aft of island (junkyard) | 5 missions — **dropped** |
| `E-2C`, `S-3B Tanker`, `SH-60B` | static aircraft | fantail / bow / finger | varies — **dropped** |

Module ownership: the AS32 gear + carrier personnel are `CoreMods/tech/USS_Nimitz`,
the Hyster is `CoreMods/aircraft/F14` — CoreMods ship with **every** DCS install, which
is exactly why a Hornet-only campaign could use them. No ownership gate needed.

Deck-flavor OCN also gets from **uncontrolled parked AI aircraft** ("Deck Hornets",
"S3 Placeholder" — real aircraft groups, engines off) is *not* reproduced here:
Retribution's own deck population (client flights, the §21 rescue helo, BARCAP
cold-starts) fills that niche with real, tracked airframes.

## The parking evidence

DCS behavior (SC manual + Hoggit): the Nimitz deck has **16 parking spawn locations +
the 4 catapults**; spots 1–4 (six-pack) are mission-start-only and deactivate on MP
unpause; a static ON a spot **blocks it** (the allocator skips it — capacity loss, no
explosion); AI **taxi through** statics, but obstructions in the Patio→El 1 lane can
slow taxi.

Measured spot anchors (Tacview, flown Scenic Route missions 2026-07-16/17, t=0-frame
ship-frame transform — parked aircraft only re-export positions on change, so only
same-frame data is valid; later-frame snapshots skew by ship travel):

| spot | x | y | evidence |
|---|---|---|---|
| six-pack 1 | +1.0 | +34.0 | player took it first, two recordings |
| six-pack 2 | −11.5 | +34.0 | measured, 12 m pitch |
| six-pack 3/4 | −23.5 / −35.5 | +34.0 | extrapolated on the measured pitch (manual shows a 4-row) |
| port quarter | −84.5 / −96.5 | −34.0 | measured — F-14 pairs went here (the manual's "large aircraft may not be able to use some parking spots" explains the six-pack skip) |
| bow-port helo | +58.5 | −31.4 | measured in all four recordings (the §21 rescue helo) |
| Tarawa (for the record) | −61 / −76 | +14.0 | measured; why the LHA is excluded — its spots hug the island side |

The unmeasured remainder (corral 5/6, junkyard 7/8, stern rows, elevator spots) is
handled by **envelope exclusion**, not per-spot clearance: everything shipped lives in
one of two zones where a parking spot cannot be:

- **LSO platform sponson** (x −134..−126, y −25..−18) — off the deck surface.
- **Island street** (x −68..−40, y +12.5..+24.5) — between the LA foul line and the
  island; flanked by the six-pack row (y=+34), the corral (fwd of the island face,
  x>−38) and the junkyard (x<−72). The SC manual's spot diagrams place nothing there,
  no spawn was ever observed there, and OCN parks gear there in 13 flyable missions.

`KNOWN_PARKING_SPOTS` + `MIN_SPOT_CLEARANCE_M` (9 m: folded-Hornet half-span 4.7 m +
placement jitter <2 m + margin) live in `game/data/carrier_deck_decor.py` and the guard
test re-checks every table entry — min actual clearance in the shipped tables is
13.8 m.

**Dropped from OCN, and why:**

- Fantail/bow **static aircraft** (E-2C at x−152/−109, S-3B, SH-60Bs at x−122..−134):
  they sit on real parking real estate. Sedlo could afford to spend spots (blocked
  spots shift spawns, and OCN never needs more than ~10); our constraint is *every*
  spot usable.
- **AS32-36A cranes** (x −69..−92, y +21..+35): the junkyard / El 3 zone — unproven,
  possibly spots 7/8.
- Port-quarter one-offs (M4/M5 items at x −113..−120, y −25..−28): too close to a
  plausible aft continuation of the port row.
- **Catapults untouched** even though the user allowed blocking one: a static on a cat
  is a player-taxi collision hazard, while the AI clips through statics anyway — a cat
  "blocked" by a static still launches AI, so nothing is actually gained.

## What shipped

`game/data/carrier_deck_decor.py`: the LSO 4-figure set (identical in all missions) +
**four street variants** (missions 3 / 10 / 11 / 12 sets, verbatim placements filtered
to the envelope), rotated per (carrier group name, turn) crc32 — deterministic across
regeneration (§70 pattern), varying across turns.
`game/missiongenerator/carrierdeckdecor.py`: `DeckDecorStatic`/`DeckDecorPoint` pydcs
subclasses adding `offsets`/`linkUnit`, one single-static group per decoration (OCN
convention), world position = ship + rotated offset off the §65 BRC. Hooked in
`GenericCarrierGenerator.generate()`'s flagship block; gated
`carrier_deck_decorations` (Mission Generation → Carrier, default ON); hull gate
`NIMITZ_DECK_HULLS` (Stennis + CVN-71/72/73/75). No UnitMap registration (cosmetic),
no plugin/Lua/save change — existing campaigns pick it up on their next generated
mission.

## Follow-up calls (both resolved by user, 2026-07-18)

- **Kuznetsov / Tarawa / Forrestal / Invincible dressing: DECLINED.** Different deck
  plans; the Hoggit spot notes put their parking on the starboard side/aft rows —
  i.e. exactly where a blind Nimitz-street copy would land. If this is ever revisited,
  each hull needs its own curated layout against its own spot evidence (a Tacview
  probe of a flown mission with deck spawns is the proven method; Tarawa already has
  two measured spots, above).
- **Fantail static aircraft: BUILT as the opt-in tier — then trimmed by the user's
  eyes the same day.** `carrier_deck_decorations_aircraft` (default OFF,
  `enabled_when` the main toggle) appends `AIRCRAFT_DRESSING`: two folded SH-60Bs
  starboard-aft (−134.3/−122.6, +27/+28.2 — the junkyard, likely spots 7/8).
  Documented cost ≈2 of the 16 spots. A dedicated guard test keeps the tier ≥9 m from
  every MEASURED spot (six-pack / port quarter / rescue-helo — the spots Retribution's
  own spawns demonstrably use) and out of the default layout.

  **The round-down E-2C lesson (2026-07-18, user screenshot):** the tier's first cut
  also shipped OCN M8's E-2C at (−152.1, +5.4) — it passed the parking guard (clears
  every spot) but the user's first in-game look asked the right question: "how can
  planes land with the E2 there?" It stands 5.6 m tall and 17.6 m long essentially at
  the ramp crossing, where every recovering aircraft passes a few metres above the
  deck. (Correction, same day: the static E-2C renders **folded** — the user's closer
  screenshot disproved my wings-spread read; the ramp argument stands on height +
  length, but the footprint math shrank, which is what re-opened the port-quarter
  E-2 question below.) Sedlo can stage-manage recoveries in a scripted mission; a
  dynamic campaign recovers jets every mission. Cut, and codified as
  `LANDING_AREA_KEEP_OUT` (a stern-threshold + wires box, x −170..−120 / y −15..+12):
  **permanent** placements must clear spots AND the recovery corridor — the parking
  guard alone was demonstrably not enough. Still excluded even after the folded
  correction: the port-quarter E-2s at (−103..−109, −31) — center-to-center 7–13 m
  from the measured patio pair the F-14s park on, inside a folded Hawkeye's
  17.6 m-long footprint envelope.

## The dynamic respot (2026-07-18, the user's next question)

"Why can't we move the planes after we take off? like move the E-2 after the launch
is over." The honest answer: statics can't drive — a DCS static has no AI controller,
no route, no `goRoute`. But they CAN be **struck below**: `StaticObject:destroy()`
removes a static silently (no explosion, no wreck), which reads exactly as the
elevator ride a real deck crew gives the alert Hawkeye between cycles. So the E-2 is
back, as a distinct class:

- `LAUNCH_PHASE_DRESSING` (data): placements allowed INSIDE `LANDING_AREA_KEEP_OUT`
  because they are runtime-cleared. Rules differ from the permanent tiers and are
  guard-tested separately: must still spare every MEASURED spot (the initial spawn
  wave uses those while the statics stand), placed only with the aircraft tier on a
  Nimitz deck, and every launch-phase static MUST reach the plugin's clear list (the
  generator returns the names; `tgogenerator` records them on
  `MissionData.deck_decor`; the emitter refuses nothing).
- The **`deckdecor` plugin** (single-file config script, the §58 pattern) clears each
  boat's list when EITHER fires first, after a 60 s grace:
  - **the astern cone** — any friendly fixed-wing airborne within 4.5 NM / below
    3 000 ft / ±50° of dead astern. Astern = the reciprocal of the **emitted BRC**
    (the boat steams into wind on one course all mission — §65/§8 — so no runtime
    orientation API is needed; the boat's live position comes from
    `Group.getByName`). The CASE I initial runs up the wake at ~800 ft from ~3 NM and
    the CASE III straight-in comes from further out — both enter the cone long
    before the groove. Helos, deck-parked jets, high overhead traffic and departures
    ahead never trip it (harness-pinned).
  - **the fallback timer** (35 min default) — launches are long over; clear the deck
    regardless so a hazard never waits on detection. Clearing early is harmless
    (the E-2's absence hinders nothing); clearing late is the failure mode, so the
    bias is early.
  One-shot per boat, a `DECKDECOR|:` log line + an optional "deck respotted for
  recovery" coalition message. Despawn ONLY — no runtime spawns (a runtime-spawned
  ship-LINKED static is an unverified DCS behavior; the day someone wants the E-2 to
  visibly reappear at a bow spot, MOOSE `SPAWNSTATIC:InitLinkToUnit` is the path to
  evaluate, in-game first).

### The Airboss tie-in (2026-07-18, "should our work tie into MOOSE airboss?")

The fork's `airboss` plugin (default ON — LSO/Marshal comms, grading, the scheduled
recovery window) intersects this feature twice:

- **It steers the boat.** `AddRecoveryWindow(…, turnIntoWind=true, …, uturn=true)` —
  during the window the carrier's real heading drifts off the emitted BRC (≈10°
  angled-deck offset; 180° transients on the U-turn legs). The ±50° cone absorbs the
  offset; the transients are neutralized by clearing BEFORE the window (below).
- **Its window start is known at init** — and with the defaults it opens at +30 min,
  FIVE MINUTES BEFORE the plain 35-min fallback: a gap where Marshal could recover
  onto a still-dressed corridor if nothing had tripped the cone. deckdecor therefore
  reads the sibling options table (`dcsRetribution.plugins.airboss.windowStartOption`
  — same mission, zero coupling) and pulls its clear deadline forward to window start
  − `airbossMarginS` (300 s), floored at grace + one poll. The armed log line says
  which deadline source won ("airboss recovery window" vs "fallback timer").

**Deliberately NOT done:** querying the `AIRBOSS` MOOSE object (the airboss plugin
stores it in a last-boat-wins global — a pre-existing multi-carrier quirk — and MOOSE
internals churn), clearing on Airboss FSM events (the plugin can be unticked; the
cone+timer must stand alone), or letting Airboss own deck objects (it has no deck
model). Bonus attribution fix from this look: the measured bow-port helo spot
(+58.5, −31.4) is **Airboss's rescue helo** spawn (`RescueHeloGroup`,
`enableRescueHelo` default ON), not the §21 CSAR helo as first noted.
- **What DCS must still prove (checklist B25):** destroy() removes the linked static
  cleanly on a moving deck, and whether the freed stern real estate becomes usable
  for recovery parking (bonus observation — nothing depends on it).

## The late-activation falsification (2026-07-18, the flown CVN-73 mission)

The deck-fill round briefly shipped OCN's starboard-aft look as PERMANENT statics
(the Seahawk pair on the junkyard spots + an E-2C/S-3B accent on the El-3 shoulder),
priced as "~3 unmeasured aft spots" under the SC manual's claim that a blocked
parking location is skipped. **The first flown mission falsified the claim**: a
CVN-73 running 30 TOT-delayed deck starts (the §64 late-activation pattern —
Retribution's dominant path) late-activated an A-6E pair **inside the Seahawk
statics** ("some how the A-6s are spawning inside the Helos"). Late activations do
not skip statics-obstructed spots; they interpenetrate.

Consequences, same day:

- **No permanent static-aircraft class exists.** HELO_ARRANGEMENTS +
  FIXED_WING_ACCENTS deleted; a guard test asserts the permanent layout never
  contains a Planes/Helicopters static. The parked-aircraft look comes from
  Retribution's real deck population (the flown decks are already full of real
  jets).
- **Their positions became evidence**: the junkyard pair (−134.3/−122.6, +27/+28.2 ≈
  spots 7/8) and the El-3 shoulder (−98.7, +29.9) joined `KNOWN_PARKING_SPOTS` as
  clip-learned anchors — OCN parks aircraft exactly on them, which is how the lesson
  was bought.
- **"On a spot" is a hard never for every class**, launch-phase included (spawns run
  while corridor dressing stands). The stern round-down + port junk row survived the
  same 30-aircraft mission untouched — evidence they are outside the spawn set —
  which is why the launch-phase corridor set stays.

The same flight caught the **cone false trip**: the E-2 was struck below at ~5 min
("the E-2 gets respoted within the first 5mins") — freshly-launched jets turning
back past the boat are low, astern, and genuinely closing as they overfly. Hardened
same day: ceiling 3 000 → **1 000 ft** (turnbacks are through it within a minute of
the cat; the CASE I initial at 800 ft and CASE III finals stay below it), a
**closing ≥30 kt** gate (crossing/outbound traffic never closes), and a **two-poll
debounce** (a transient closing moment never clears). Harness-pinned in both
directions.

## The second falsification: the deck itself was the "recovery traffic" (2026-07-18 night)

The night re-fly false-tripped the cone **twice more**, bracketing the hardening:
the 21:58 Scenic Route turn-3 flight (generated 32 min before #650 merged, so it
flew the pre-hardening cone) struck GW's corridor set at **t+74 s** — the first
poll after grace — and the 22:42 Dust-to-Dust flight, on the **hardened** build
(armed line confirms 1 000 ft), struck TR's at **t+171 s**. Nothing recovers three
minutes into a fresh mission.

The Tacview forensics on the GW flight found the real qualifier class: **the aft
parking rows themselves**. Parked jets ride the steaming boat 130–170 m astern of
the ship's *pivot point* (inside the cone's ±50° and beyond its old 100 m floor),
DCS reports units on a moving deck as `inAir()`, and with the world-frame
`getVelocity()` the whole row "closes" at exactly boat speed — GW made 22 kt, under
the 30 kt gate by 8 kt of luck; TR evidently didn't get the luck (faster boat
and/or a genuine sub-1 000 ft launch turnback, indistinguishable without its
Tacview — both modes are covered below). The airborne traffic that early (the
air-spawned E-2/A-6 support flights, which materialize 0.3–0.9 NM astern at
500–900 ft) *opens* astern at 200+ kt and never qualifies.

Hardening v2 (same night), three rules that kill the family rather than the
instance:

- **Ship-relative closing** — `closing = -((v_unit - v_boat) · d̂)`: a deck rider
  closes at ~0 however fast the boat steams; a genuine recovery closes 120+ kt
  regardless of boat speed. (The ship unit's `getVelocity()` is the reference.)
- **Deck-footprint stamp radius** — anything within **400 m** of the boat is deck
  traffic, never a trip source (replaces the 100 m floor, which the aft rows
  out-ranged).
- **The outbound roster** — every unit seen inside the stamp radius (parked,
  taxiing, cat stroke, bolter) is stamped per boat, and a stamped unit cannot read
  as recovery traffic for **600 s** after it was last seen there: a jet fresh off
  this deck is its own launch traffic however low and inbound its turnback looks.
  A genuine recovery starts miles out, is never stamped, and still clears through
  the debounce; a returning own-launch jet becomes eligible again once the window
  lapses (by which point the airboss deadline has usually cleared the deck anyway).

Harness-pinned in `tests/lua/test_deckdecor_runtime.py`: deck riders on a 35 kt
boat never clear, sub-boat-speed world-frame closers never clear, the roster
suppresses a fresh launcher's low closing turnback then lapses, and a genuine
run-in on a moving boat still clears. Known residual (accepted): polls only start
at the 60 s grace, so a jet that launched inside the first minute would miss its
stamp — no AI airframe launches that fast from a cold deck.

One stale-options footnote from the same night: plugin option values bake into a
campaign save when the save first runs under a build that has the plugin, so the
Scenic Route save (loaded under the pre-#650 plugin.json) still carries
`coneAltFt: 3000` and will keep feeding it — reset it in the plugin options UI or
accept the wider ceiling (the v2 gates above don't depend on it). Campaigns first
loaded post-#650 pick up 1 000 ft normally.

## Filling the deck (2026-07-18, "go back and look at layouts again")

**⚠️ Partially REVERSED the same day** — the permanent aircraft sub-zones described
below (Seahawk arrangements + fixed-wing accents) were removed by the
late-activation falsification above; the street/launch-phase halves stand.

With the respot mechanism in hand the user asked for a re-mine: "we could fill the
round down within reason if we figure out reliably getting the landing area cleaned
up when needed." Curation v2 reclassified every dropped OCN placement with per-type
**footprint-aware** spot clearances (`required = 9 m + FOOTPRINT_EXTRA_M[type]`; the
folded E-2 carries 8 m extra off its 17.6 m length, the S-3B keeps a spread-margin
10.5 m — its fold state is unverified — the Seahawk 6.5 m). Results, all verbatim
per-mission placements:

- **Street: 6 variants** (M3/M6/M9/M10/M11/M12). The envelope extends aft to −74 and
  up the island wall to +26, bringing in the M6/M9 **AS32-36A crane** accents at the
  island's aft corner (the junkyard's own spots sit x ≤ −80 per the SC diagrams; the
  M3/M10 cranes at −80/−92 stay excluded for exactly that reason). Sets are never
  mixed across missions inside a zone — M11's tractor and M9's crane sit 2 m apart.
- **Aircraft tier: two independently-rotating starboard-aft sub-zones** (25+ m apart,
  so cross-mission combination can't clip): the folded-Seahawk pair (M6/7/9 outer row
  / M2 inner row / M4 forward row) + a fixed-wing accent behind the island (M2 E-2C /
  M11 E-2C / M5 S-3B). Documented cost ≈3 unmeasured aft spots.
- **Launch-phase: two corridor sub-zones**, likewise independent: the round-down
  E-2C (M8 −152.1 / M1 −138.0) + the **port junk row** between the LSO platform and
  the wires (M4's 5-piece set — P-25, three deck hands, the fifth LSO figure — or
  M5's tractor+hand pair). OCN shipped the port row as PERMANENT statics in flyable
  missions, but it sits where a plausible aft continuation of the patio spot row
  would be — launch-phase classification spends that real estate only while the deck
  is a launch deck, and the pre-recovery clear also de-clutters the LSO's line of
  sight. `LAUNCH_PHASE_MAX_X = −100` pins the whole class aft: M4's bow set stays
  excluded forever because forward statics would stand in the bow-cat taxi flow
  exactly during the launch cycle.
- **Still excluded, with reasons:** the port-quarter E-2s (measured-spot fouls, see
  above); M4's bow-shoulder set (taxi flow); the handful of forward strays outside
  every envelope; anything whose only home would mix missions within a zone.
- **Per-hull variety** (different variants on different boats in one theater) falls
  out free of the group-name seed; nothing to do.

## In-game pass

Checklist **B25**: statics ride the steaming deck (no floaters left in the wake), a
max-density cold spawn still fills every spot vs a decorations-off control, AI
recovery taxi behaves around the street gear, variant rotates next turn.
