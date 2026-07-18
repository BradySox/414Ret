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
  planes land with the E2 there?" It stands 5.6 m tall essentially at the ramp
  crossing, where every recovering aircraft passes a few metres above the deck — and
  the DCS static E-2C renders **wings-spread**, not folded, so it looms over the
  threshold. Sedlo can stage-manage recoveries in a scripted mission; a dynamic
  campaign recovers jets every mission. Dropped, and codified as
  `LANDING_AREA_KEEP_OUT` (a stern-threshold + wires box, x −170..−120 / y −15..+12)
  guard-tested against BOTH tiers — the parking guard alone was demonstrably not
  enough; anything new must clear spots AND the recovery corridor. Also still
  excluded: the S-3B at (−98.7, +29.9) (would foul the El-3 elevator spot) and the
  port-quarter E-2s at (−103..−109, −31) (their span fouls the measured port pair the
  F-14s park on).
- **Per-hull variety** (different variants on different boats in one theater) falls
  out free of the group-name seed; nothing to do.

## In-game pass

Checklist **B25**: statics ride the steaming deck (no floaters left in the wake), a
max-density cold spawn still fills every spot vs a decorations-off control, AI
recovery taxi behaves around the street gear, variant rotates next turn.
