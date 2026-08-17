# Carrier Deck Decorations (§72) — campaign A deck dressing, parking-safe

**Status: LANDED 2026-07-18.** User request: "Take a look at the deck layouts and
decorations in [the 13 campaign A missions]. I wanna apply them to ALL retribution carriers
for flavor. BUT we need all of the parking spots still usable. If you want to block a
catapult that is fine."

This note records where the data came from, what the parking evidence is, and why
specific campaign A decorations were dropped — so a future edit argues with the evidence, not
with vibes.

## Source: what campaign A actually does

All 13 missions of campaign A (a paid FA-18C campaign in the DM's
`<DCS>\Mods\campaigns\` folder) dress the CVN-75 Truman with 12–27
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

**campaign A's vocabulary** (type → what it is → where it lives):

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

Deck-flavor campaign A also gets from **uncontrolled parked AI aircraft** ("Deck Hornets",
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
- **Island street** (x −63.9..−31.4, y +11.9..+24.7 — the current placements after the
  2026-07-27 re-reposition below; this bullet read x −68..−40 until 2026-08-07 and was
  stale by the `CORRAL_SHIFT` retune) — between the LA foul line and the island; flanked
  by the six-pack row (y=+34), the corral (fwd of the island face, x>−38) and the
  junkyard (x<−72). No spawn was ever observed there, and campaign A parks gear there in 13
  flyable missions. ⚠️ **The third leg of that argument — "the SC manual's spot diagrams
  place nothing there" — does not survive reading the diagrams.** See *The 11-vs-16 spot
  gap* below.

`KNOWN_PARKING_SPOTS` + `MIN_SPOT_CLEARANCE_M` (9 m: folded-Hornet half-span 4.7 m +
placement jitter <2 m + margin) live in `game/data/carrier_deck_decor.py` and the guard
test re-checks every table entry — min actual clearance in the shipped tables is
13.8 m.

**Dropped from campaign A, and why:**

- Fantail/bow **static aircraft** (E-2C at x−152/−109, S-3B, SH-60Bs at x−122..−134):
  they sit on real parking real estate. the campaign author could afford to spend spots (blocked
  spots shift spawns, and campaign A never needs more than ~10); our constraint is *every*
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
subclasses adding `offsets`/`linkUnit`, one single-static group per decoration (campaign A
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
  also shipped campaign A M8's E-2C at (−152.1, +5.4) — it passed the parking guard (clears
  every spot) but the user's first in-game look asked the right question: "how can
  planes land with the E2 there?" It stands 5.6 m tall and 17.6 m long essentially at
  the ramp crossing, where every recovering aircraft passes a few metres above the
  deck. (Correction, same day: the static E-2C renders **folded** — the user's closer
  screenshot disproved my wings-spread read; the ramp argument stands on height +
  length, but the footprint math shrank, which is what re-opened the port-quarter
  E-2 question below.) the campaign author can stage-manage recoveries in a scripted mission; a
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
  recovery" coalition message. Despawn only **until 2026-08-07** — the recovery-phase tier below added
  the one sanctioned spawn, by exactly the route this paragraph predicted (MOOSE
  `SPAWNSTATIC:InitLinkToUnit`). Its caveat still stands and is now the open item: a
  runtime-spawned ship-LINKED static is **unverified DCS behavior**, so it needs the
  in-game look first (B49).

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

The deck-fill round briefly shipped campaign A's starboard-aft look as PERMANENT statics
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
  clip-learned anchors — campaign A parks aircraft exactly on them, which is how the lesson
  was bought.
- **"On a spot" is a hard never for every class**, launch-phase included (spawns run
  while corridor dressing stands). The stern round-down E-2 survived the same
  30-aircraft mission untouched — evidence it is outside the spawn set — which is why
  it stays. (The port junk row also appeared to survive here, but was later
  falsified — see the 2026-07-21 section below.)

## The corral reposition (2026-07-21, flown CVN-71 SKINK, second finding)

Same flown mission, a separate issue the user flagged with an annotated
screenshot: the **street gear was in the wrong place**. The screenshot circled
the corral (the clear lane forward of the island) and X'd the gear cluster,
which had spawned on the **angled-deck foul-line strip** alongside/aft of the
island — "they should have been in the circle not the X".

Root cause: the street gear used campaign A's verbatim offsets (x −40..−74, y +12..+26),
which place the cluster alongside the island. Cross-referenced against the real
deck geometry (island base x −40..−80 y +20..+55 from `USS_CVN_71.lua`; landing
touchdown x −104 y −33 port; six-pack spots y +34): those offsets sit in the
narrow starboard strip between the island and the foul line — reading as "on the
landing markings." campaign A's own **corral** gear (forward of the island) was sparse
crew only, so rather than lose the rich tractor/crash-truck/forklift/crane
cluster, the whole campaign A arrangement is **translated forward** into the corral by
`CORRAL_SHIFT = (+30, −6)` (preserves the relative layout). Result: gear at
x −11..−43, y +7..+20 — forward of the island, starboard of the angled deck,
inboard of the six-pack, **≥7 m clear of every known spot** (guard-tested across
all six variants). `ISLAND_STREET_ENVELOPE` moved to the corral box
(−46, −8, 4, 22); the envelope-bounds guard updated to match.

Method note: the position was confirmed against a **top-down deck map** built
from the measured spots + the lua geometry before shipping (the perspective
screenshot alone was ambiguous — repeated deck-geography guesses had failed, so
the map is the source of truth).

## The port junk row clip (2026-07-21, the flown CVN-71 SKINK)

Third flown mission, third static-placement lesson. The user reported "weird
spawning" and attached the miz. Tacview forensics on the flown recording measured
where aircraft actually spawned on deck (their miz positions are meaningless — carrier
parking starts sit on the carrier reference and DCS assigns real spots at runtime),
and found a **port-quarter parking spot at (−108, −34)** that was not in
`KNOWN_PARKING_SPOTS` (the row was only known back to −96.5). A Hornet spawned there
stood **8.7 m** from the launch-phase port junk-row tractor at (−113.7, −27.6) — a
wingtip clip.

Root cause: the **port junk row was launch-phase in name only**. The deck-fill round
placed it at x −105..−114 / y −24..−28 and called it "corridor dressing by the LSO
platform", but that is **forward and port of the `LANDING_AREA_KEEP_OUT` box**
(x −170..−120, y −15..+12) — i.e. in the port-quarter *parking* row, not the recovery
corridor. The weak "aft of x ≤ −100" launch-phase rule let it pass. Fixes:

- **Port junk row removed.** Launch-phase is now the round-down E-2 only (which sits
  genuinely inside the corridor box and has never clipped across three flown missions).
- **Invariant tightened**: launch-phase dressing must fall **inside**
  `LANDING_AREA_KEEP_OUT` — the one zone the plugin actually clears and by definition
  not a parking area. This replaces `LAUNCH_PHASE_MAX_X`; the guard test enforces
  containment, so a parking-row position can never be mislabeled launch-phase again.
- **(−108, −34) added to `KNOWN_PARKING_SPOTS`** (measured), which independently makes
  the footprint-clearance guard flag the removed junk row too.

The **street gear (starboard) and LSO crew are unaffected**: across two flown
recordings, deck spawns only ever landed on the six-pack (y +34, forward), the
port quarter (y −34, aft), and the rescue-helo spot — never the starboard street zone
(the island's footprint, x −40..−74, y +12..+26). Residual risk remains (I cannot
enumerate every DCS spot from files — they are model attach-points), so the honest
posture is: the provably-safe core is the off-deck LSO crew + the runtime-cleared
round-down E-2; the street gear rests on "no observed spawn there across the flown
missions," not proof.

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
up when needed." Curation v2 reclassified every dropped campaign A placement with per-type
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
  M5's tractor+hand pair). campaign A shipped the port row as PERMANENT statics in flyable
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

## The island-street re-reposition (2026-07-27, flown, red-vs-blue finding)

The 2026-07-21 corral move (above) **overshot forward**. On a later flown mission
the user annotated a deck screenshot with a **red** circle (where the gear now
generates — the forward corral) and a **blue** blob (where it should go —
alongside the island, a bit aft and tucked outboard). "It was good with another
client until something changed and now they're generating in the red instead of
the blue." The `+30 m` forward shift had pushed the cluster too far toward the bow.

Fix: pull the cluster back into the **island street** — aft toward the island and
outboard against it, off the foul-line strip (outboard = away from the port angled
deck). `CORRAL_SHIFT` retuned `(+30, −6) → (+9, −1)`: ~10 m aft of the raw campaign A
offsets / ~5 m outboard of the old forward corral, preserving the relative layout.
Result: shifted cluster at x −63.9..−31.4, y +12..+24.7. `ISLAND_STREET_ENVELOPE`
widened to `(−65, −30, 10, 25)` and the envelope-bounds guard relaxed to match
(`sx0 ≥ −70`, `sy1 ≤ 25`). Verified clear of every `KNOWN_PARKING_SPOT` — **min
12.7 m** at the six-pack row (was ≥7 m) — so the outboard tuck stays well off the
y = +34 six-pack spots and the aft junkyard/El-3 spots (x < −98). Guard tests
(`test_carrier_deck_decor.py`, 12) green. Needs an in-game eyeball to confirm the
blue-spot placement (B25).

## The 11-vs-16 spot gap (2026-08-07, from the Supercarrier guide's own diagrams)

The `references/manuals/` pass put the **DCS Supercarrier Operations Guide** on disk and
indexed it. Reading the two things in it that bear on this feature changes what the
parking-safety argument above actually proves.

**What the guide says in prose** (p100–101) — most of it already matches this note: 16
parking spots + 1 per catapult; spots 1–4 deactivate on MP unpause; the F-14 blocks
adjacent spots; parking is assigned in the order aircraft are added to the carrier. Two
things here were **not** recorded before:

- Deck control routes a landing aircraft only to a spot it can reach, and treats **static
  objects as taxi-route obstructions**. If a mission leaves no reachable spot, the landed
  aircraft is **removed from the simulation** — a harsher failure than this note's "a
  static ON a spot blocks it (the allocator skips it — capacity loss, no explosion)".
- ED's own advice is to keep an unobstructed lane to **elevators 1 and 2**, forward of the
  island: aircraft routed there are struck below and keep the deck clear.

**What the diagrams say** is the part that matters, and it was invisible until now because
pages 104–106 are **images** — `pdftotext` returns only "Slide 1 / Slide 2 / Slide 3", so
every earlier reading of this manual missed them. They are titled **Static Object Safe
Zones**, drawn on CVN-71, in two columns (Launch Ops / Recovery Ops) at **4, 8 and 16
aircraft**. Two consequences:

- **The launch-vs-recovery split this feature already ships is ED's own model.** The
  LAUNCH-PHASE tier standing in the recovery corridor and being struck below before
  recovery is exactly the difference between ED's two columns. Nothing to change.
- **The safe zone shrinks as the deck fills, and §72 does not model that.** The placements
  are fixed; there is no aircraft-count input. A set that is safe on a light deck is not
  automatically safe on a full one.

**The gap, quantified.** `KNOWN_PARKING_SPOTS` holds **11** entries; ED documents **16**.
On the starboard side the table runs out at `x = −35.5` (aft end of the six-pack row) and
does not resume until `x = −98.7` (El-3 shoulder) — **63.2 m of deck with no entry** — and
**52 of the 67** street-gear placements sit inside it. The guard-tested clearance is real
but proves less than it reads: all six variants' minimum (12.7–14.7 m) is measured to the
same spot, `(−35.5, 34.0)`, the *edge* of the gap. Nothing inside the gap is tested,
because nothing inside it is in the table. The guide's parking diagram (p100) places
**spots 5 and 6** in that region — forward of the island on the starboard deck edge, aft of
the 1–4 row, with spot 5 drawn E-2-sized.

**What was deliberately not done.** Registering the safe-zone slides to ship-frame metres
was attempted and **the result was discarded**: the deck aspect derived from the image came
out 22 % wider than a Nimitz, and the two drawings of the same hull disagreed by 23 px,
because aircraft icons are drawn overlapping the deck edge. So this note does **not** claim
the street is inside or outside the green. Repeated deck-geography guesses have failed on
this feature before (see the corral reposition's method note); the honest answer is that
spots 5 and 6 need **measuring**, by the same Tacview t=0 method that produced the 11
entries we have.

**Consequence:** LOCAL card 2 — count the jets a full cold deck actually parks, decorations
on vs off. That is the parking-capacity half of B25's criterion, which B25's 2026-08-06
closure did not exercise (it closed on the appearance symptoms). Until it runs, treat the
island street as **flown-clean but not capacity-proven**.

## Completing the campaign A mining (2026-08-07)

The original extraction mined **7** of the 13 campaign A missions for street sets (3, 6, 9, 10,
11, 12/13). All 13 were re-extracted with a lupa parser over each `.miz`'s `mission` table,
validated against the shipped literals first: **12/12 offsets and 12/12 angles reproduce
mission 3's `_CAMPAIGN_A_STREET_VARIANTS[0]` exactly**, so the extractor is reading what the
original pass read.

238 ship-linked statics across the 13 missions. What the six unmined missions hold, after
`CORRAL_SHIFT` and the envelope filter:

| mission | items in envelope | min spot clearance | shipped |
|---|---|---|---|
| 1 | 8 | 14.7 m | yes |
| 2 | 8 | 16.2 m | yes |
| 4 | 5 | 12.2 m | yes |
| 5 | 7 | 17.8 m | yes |
| 7 | 4 | 15.1 m | **no** |
| 8 | 2 | 15.6 m | **no** |

Missions 7 and 8 clear the guard but are too thin: a 2-item "street" reads as a bare deck.
The **five-item curation floor** is now a test
(`test_every_street_variant_carries_enough_gear`). `STREET_VARIANTS` goes **6 -> 10**, and
the rotation test already asserts every variant is reachable, so the four new sets rotate
with the rest.

**No new launch-phase data exists, and that is a finding rather than an omission.** Only
**two** campaign A static aircraft stand inside `LANDING_AREA_KEEP_OUT` and both already ship as
`ROUND_DOWN_VARIANTS` (the mission 8 and mission 1 E-2Cs, 28.0 m and 22.2 m clear). Every
other campaign A static aircraft -- 10 SH-60Bs, 2 more E-2Cs, the S-3B -- sits **0.0-8.2 m from a
known parking spot**:

| | |
|---|---|
| m6 SH-60B (-134.29, 27.02) | **0.0 m** |
| m6 SH-60B (-122.57, 28.24) | **0.1 m** |
| m5 S-3B (-98.65, 29.93) | **0.1 m** |
| m2 E-2C (-97.78, 28.80) | 1.4 m |

Those are not near-misses. The first three are the junkyard and El-3 shoulder spots
*themselves* -- the entries `KNOWN_PARKING_SPOTS` learned from the 2026-07-18 flown
falsification, derived from where campaign A parks its Seahawks. Mining them back in would
re-create the exact defect that pass removed. The round-down pool is therefore **closed at
two** unless positions are authored rather than extracted.

## The recovery-phase tier (2026-08-07, built default-OFF)

The mirror of the launch-phase tier, and the first §72 dressing that is **spawned rather
than placed**. A real deck is re-spotted for recovery -- landing area cleared, gear ranged
forward onto the bow -- which is exactly what the Supercarrier guide's safe-zone slides
encode: its Recovery column marks the bow and catapult tracks safe while the angled deck
must stay clear, and its Launch column marks the opposite. §72 already shipped that split
without knowing ED had drawn it.

**Mechanism.** The placements are deliberately absent from the `.miz` -- the bow has to be
a launch deck until launches are over. The `deckdecor` plugin spawns them on the SAME
trigger that strikes the launch set below (astern cone or fallback timer, whichever fires
first), via **MOOSE `SPAWNSTATIC:InitLinkToUnit`**, which is the only runtime path that
writes the three-level linked static (`linkUnit` + `linkOffset` + `offsets{x,y,angle}`).
A plain `coalition.addStaticObject` would drop the gear at a world point and the boat would
steam out from under it.

**The despawn-only invariant was broken deliberately, on an explicit call (2026-08-07).**
The plugin's header promised "Despawn ONLY -- no spawns" from the day it was written; the
carrier case is the one place that rule cannot hold, because gear ranged forward for
recovery must NOT be on the bow during the launch cycle -- so it cannot be generated into
the miz -- and a static that rides a steaming hull cannot be faked any other way. The
exception is deliberately **scoped, not widened**: one one-shot spawn per boat, on the same
trigger as the strike-below, `pcall`-wrapped, skipped entirely when MOOSE is absent, and the
despawn half runs regardless. A second spawn caller would make this a spawner, which is a
different kind of script with a different failure surface; do not add one without a fresh
call. The plugin's own header predicted this exact route before it was taken.

**Data: four variants, rotating on the same (carrier, turn) seed as the street.** It shipped
on 2026-08-07 with a single set, which meant every recovery on every carrier looked identical
-- corrected the same day. The four come from a wider re-read of the campaign A extract: the original
pass only looked at x > 0 (the bow proper) and found one usable set, but the tier's real zone
is the bow **plus the forward mid-deck strip**, and campaign A dresses that in most missions.

| variant | source | items | min known-spot clearance |
|---|---|---|---|
| bow set -- the full forward respot | mission 4 | 9 | 9.8 m |
| forward mid-deck cluster | mission 8 | 4 | 9.6 m |
| forward mid-deck cluster | mission 3 | 3 | 19.9 m |
| forward mid-deck cluster | mission 5 | 3 | 17.4 m |

Three otherwise-good sets were **excluded, and the reason is now a guard**: campaign A missions 7, 12
and 13 put their forward cluster inside `ISLAND_STREET_ENVELOPE`, where the permanent street
gear stands all mission. Spawning recovery gear on top of it would interpenetrate -- statics
have no collision resolution -- so `test_recovery_and_street_zones_never_overlap` asserts the
two boxes are disjoint and that no recovery item lands in the street box. Mission 2's forward
pair (2 items) was also dropped, too thin to read as a set.

`FORWARD_DECK_ENVELOPE` is sized to the shipped campaign A extent plus slack, **not** to a deck edge
read off the safe-zone slides: the slides could not be registered to ship-frame metres, so no
bound in this feature is taken from them.

**⚠️ This is the least-evidenced tier in §72 and it is default-OFF for that reason.** It
clears every entry in `KNOWN_PARKING_SPOTS` -- but that table holds 11 of the guide's 16
spots, and the five it lacks are the bow-edge spots (11/12/13) nearest this zone. "Clears
every known spot" is not "clears every spot" here, and this tier is the one place in §72
where that distinction could bite. Promoting it to default-ON requires MEASURING the bow
spots by the Tacview t=0 method that produced the 11 entries we have. Until then the honest
description is: authored from real campaign A offsets, guarded against everything we know, and
unflown.

Guards: `test_recovery_tier_stays_inside_the_forward_deck_box`,
`_clears_every_known_spot`, `_never_touches_the_landing_area`, `_has_static_meta`,
`_is_gated_and_rotates`, and `_is_never_written_into_the_mission` -- the last one being the
invariant that matters most, since a recovery placement that reached the `.miz` would stand
on the bow from mission start and re-create the spawn-clip this feature has already paid
for twice.

## Campaign B, and static aircraft in the recovery tier (2026-08-07)

A second installed campaign (18 missions, all dressing a CVN-73) was extracted with the same
validated parser. 191 ship-linked statics.

**The headline: campaign B dresses its deck almost entirely with static AIRCRAFT** -- 56
Hornets, 12 Tomcats, plus an A-6E, S-3Bs, a UH-60A and E-2Cs. Strip those under §72's
no-permanent-static-aircraft rule and the campaign yields almost nothing: 7 usable recovery
items and 5 street items, none of the street sets above 2 items.

**That rule was relaxed for the recovery tier only, on an explicit call.** The reasoning: the
clipping that produced the ban was a *placement* problem, not an aircraft problem, and the
recovery tier only stands once launches are over. The split is now:

- **PERMANENT layout: still no static aircraft, unchanged.** It is up for the whole mission
  while every spawn path runs, which is the condition that produced the 2026-07-18 clip.
- **RECOVERY tier: aircraft allowed**, because it appears after the launch cycle and because a
  deck respotted for recovery with jets ranged forward is the point of the tier.

Both halves are pinned by `test_recovery_tier_may_carry_aircraft_but_permanent_gear_may_not`.

**What the relaxation cost, and what pays for it.** Aircraft are far bigger than deck gear, so
`FOOTPRINT_EXTRA_M` gained six entries at roughly half each type's published fuselage length
(Hornet 8.5, Tomcat 9.5, A-6E 8.5, S-3B 8.0, UH-60A 8.0 -- the E-2C's 8.0 stays the only one
confirmed against the in-game render, so the rest are rounded up and only ever make the guard
stricter). Footprint-aware clearance then **rejected 15 of campaign B's forward placements**
outright -- the filter is doing real work, not rubber-stamping.

A second guard came out of this: box disjointness checks item *centres*, and a parked Tomcat
reaches ~9.5 m aft of its centre. `test_recovery_aircraft_footprints_clear_the_street_gear`
checks the footprint *edge* against the street box instead; the worst case currently clears by
11.8 m.

Five variants shipped (6/5/3/3/3 items), taking the recovery pool to **nine**.

## Naming

Source campaigns are referred to as **campaign A** and **campaign B** rather than by name
(2026-08-07 call). They are paid third-party DCS campaigns; the placements here are extracted
coordinate data, and the fork does not name the products in its own docs or code. Sets are
still traceable to a specific source mission (`campaign A mission 3`), so the "never mix sets
across missions within a zone" rule stays checkable.

## In-game pass

Checklist **B49** covers the recovery tier (spawned dressing appears forward when the
launch set is struck below, rides the steaming deck, and a full cold deck still parks
16 with the tier on). LOCAL card 2 covers the capacity question for the permanent
street.

Checklist **B25**: statics ride the steaming deck (no floaters left in the wake), a
max-density cold spawn still fills every spot vs a decorations-off control, AI
recovery taxi behaves around the street gear, variant rotates next turn, and the
street gear now sits in the island street (the 2026-07-27 blue spot), not the
forward corral.

## The 11-vs-16 spot gap: measured (2026-08-17)

The two holes the 2026-08-07 audit named are closed with data, not with a guess.

**Method.** Same as the original eleven: every aircraft within 200 m of a CVN-71 at the
frame it first appears, transformed into the ship frame (`forward = dN·cos h + dE·sin h`,
`starboard = −dN·sin h + dE·cos h`), clustered at 8 m. Five recordings, 2026-08-16.

| new entry | sightings | missions | what it is |
|---|---|---|---|
| (+35.6, +36.7) | 6 | 5 | six-pack row, forward pair |
| (+23.4, +35.5) | 6 | 4 | six-pack row, forward pair |
| (−89.8, +26.4) | 9 | 5 | starboard mid-deck, aft end of the blind band |
| (−76.3, +26.4) | 1 | 1 | same row, forward |
| (−74.6, −38.4) | 2 | 1 | port quarter, forward of −84.5 on the row's 12 m pitch |

F-14B, F-14B(U), FA-18C and EA-18G all park to the same cluster centres, so these are
spots rather than airframe artefacts. The known (−35.5, +34.0) row entry drew **no**
sightings across the five missions — it stays as the extrapolation it always was.

**The two thin rows are deliberately kept.** This table is a keep-out set: an extra entry
can only reject a decoration, never place one, so a single real sighting is worth more
than the certainty it lacks.

**What it caught immediately.** The recovery tier put an `AS32-31A` **5.8 m** from
(+35.6, +36.7), against the feature's own 9.0 m floor — the hazard the old table was blind
to, and exactly the failure class the 2026-07-18 fly taught. Five sets were affected.

**The fix is a filter, not an edit.** `RECOVERY_DECK_VARIANTS` is now
`_AUTHORED_RECOVERY_VARIANTS` passed through `clears_known_spots`, with sets falling below
`MIN_RECOVERY_SET_ITEMS` (3) dropped whole — 9 authored sets become 7 shipped. Nudging
coordinates by eye is the method that has failed this feature before (see the corral
reposition's method note); a filter means the next measured spot prunes what it invalidates
with no authoring at all. The launch-phase street sets were already clear of all sixteen.

**Still not claimed:** that these ARE the guide's spots 5/6/11/12/13. The safe-zone slides
could not be registered to ship-frame metres (§"What was deliberately not done"), so this
note says what was measured and nothing more. The count reaching 16 is a corroboration, not
the evidence.

## The astern cone fired with nothing in it (2026-08-16, unresolved)

A faithful replay of `approachDetected` over the whole 4th-test recording **never trips**,
at any poll from t+60 to t+390. The only objects ever inside the 4.5 nm cone were:

- the boat's own four parked Hornets, 35–112 m out — inside `DECK_STAMP_M` (400 m), so
  roster-stamped and never trip sources;
- the rescue helo — a rotorcraft, which `coalition.getGroups(side, Group.Category.AIRPLANE)`
  cannot return, and 155–180° off the stern in any case (ahead of the beam);
- `0913 | CG Ticonderoga` at 3.7 km, 129° off the stern.

Ruled out alongside: the emitted BRC (138.0) matches the recorded ship heading exactly, and
every emitted plugin option was at its default (`coneHalfDeg 50`, `coneClosingKts 30`,
`coneDistNm 4.5`, `coneAltFt 1000`, `pollS 10`, `graceS 60`).

So the plugin cleared the deck for "recovery traffic astern" with no traffic astern, and the
recording cannot say why. The plugin now logs the tripping unit's name, range, off-stern
angle, altitude and closing rate on **every** trip poll — not only the pair that clears —
plus the pcall error if the check itself throws. The next occurrence identifies itself in one
line. Until then the launch-cycle floor (below) bounds what a spurious trip can do.

## The launch-cycle floor held the deck for three hours (2026-08-17)

The 2026-08-16 floor read the **latest** departure off the deck. `departure_delay` is the
whole wait until a flight's scheduled start, so one late package off CVN-71 produced
`still launching, respot held until 11388s` in a 19-minute mission — the deck never
respotted at all. `launch_cycle_ends_at` now returns the *current* cycle: the run of
departures from the first, broken by an idle gap longer than `LAUNCH_CYCLE_MARGIN_S`. That
constant serves as both the post-launch margin and the cycle-ending gap; a second constant
would only let the two drift.
