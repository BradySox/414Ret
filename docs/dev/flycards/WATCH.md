# WATCH — standing list for the daily fly

**Five things to look for in whatever you were flying anyway.** No mission is built for these,
no toggles are flipped, no campaign is required. They close from ordinary flying if — and only
if — someone is looking.

Rules that keep this useful:
- **Five items, hard cap.** A watch list of twenty is a watch list of zero.
- An item earns its place by needing **no setup**. Anything needing a test toggle, a specific
  campaign, or a contrived condition belongs on a local card instead.
- Seeing it once is enough. Note it in the matching checklist row **the same session**, with
  the date — flown results get clobbered otherwise.
- When an item closes, cross it off and pull the next one from the parking lot below.

Design rationale + the three-cadence model: `docs/dev/design/414th-verification-cadence-notes.md`.

---

## The five

### 1 · Loadouts are mixed, not identical — `B42` (§84)

**Where:** the ATO / payload screen, before you even take off.

- **Pass:** two flights of the same airframe and task carry **different** loadouts, and at
  least one jet carries a **mixed** magazine — a couple of AMRAAMs and a couple of Sparrows on
  the same aircraft. Bomb-carrying flights should show the generational ladder too (JDAM on one,
  LGB or dumb bombs on another).
- **Fail:** every flight of a type+task is byte-identical, the way it was before §84 — or the
  substitution went the *wrong way* and a later turn is carrying **better** stores than turn 1.
- **Why it's here:** brand new (2026-08-03), and visible without flying at all. The
  never-an-upgrade rule is test-pinned across all 306 weapon groups, so a visible upgrade
  in-game means the data disagrees with the test's assumption.

### 2 · Civil traffic is region-plausible — `I2`

**Where:** out the window, or the F10 map, on any mission.

- **Pass:** traffic fits the region — **no Antonovs over Nevada**, **nothing at all over
  Normandy or The Channel** — reads as civil by operator name (`AEROFLOT 412`, not `CIV_An-26B_3`),
  and crosses the map **high and straight** (FL200–FL310) rather than pottering between rear fields.
- **Fail:** an empty sky on a mapped theatre (check the `Civilian traffic: N flights…` log line
  first — that distinguishes "broken" from "you didn't look up"); traffic at the old flat
  ~16,000 ft; any civil aircraft over a WWII map.
- **Why it's here:** rebuilt 2026-08-05 off your own report and has had no eyes on it since.

### 3 · SAM and missile sites have a support section — `B43` · `B44` · `B47` (§85)

**Where:** any SAM site or missile battery, on the map or over the target.

- **Pass:** an S-300 site fields **2 cargo trucks + 2 fuel bowsers + 2 generators**; legacy
  sites (SA-2/3/5/6) field trucks **and** a bowser; a missile battery (SCUD / Iskander / CJ-10)
  fields 2 cargo trucks + a transporter-loader + a refueller + a command vehicle.
- **Fail:** a bare launcher row with one jeep (the old look); or a bowser standing **instead of**
  a cargo truck rather than alongside it — that is the slot-displacement bug this was built to
  fix, and it would mean a whitelist regressed.
- **⚠ Requires a game started after 2026-08-04** (2026-08-06 for the missile half) — composition
  is generated at campaign start, so an older save will show the old look and prove nothing.
- **Why it's here:** three rows, one glance. Highest rows-per-second on the list.

### 4 · Carrier deck gear sits on the deck — `B25` (§72)

**Where:** any carrier mission, walking the deck or on the F10 map.

- **Pass:** the island-street gear and the LSO platform team sit **on** the deck in the street
  alongside the island, clear of every parking spot and the landing area.
- **Fail — and this is the one worth catching:** a static **floating** off the deck, or the
  cluster sitting visibly out of place. **Note which hull and which static**, because that is
  the exact blocking question on DM work order #2 and nobody has answered it — the decor rotates
  6 street variants per (carrier, turn) seed, so a float may be variant-specific and only a
  specific sighting will pin it.
- **Why it's here:** a reported defect with an open question that a single screenshot resolves.

### 5 · The opportunistic pair — `A5` (§1) · `G29` (§21)

**Where:** nowhere in particular. These need a moment to *occur*, which is exactly why they've
sat PARTIAL since 2026-07-11.

- **`A5` — a rear field answers a raid at the front.** Pass: a QRA flight launches from a base
  well behind the line and **completes the long transit** to the fight. Fail: it launches and
  turns around partway (the disengage-radius signature), or rear fields never launch at all.
- **`G29` — a downed pilot becomes an evader.** Pass: a blue jet is lost and not rescued, and
  next mission that pilot shows as **MIA** on the SITREP band / squadron roster / orange marker
  on the map, then re-spawns as an evader at his last position. Fail: the pilot is simply dead,
  or the MIA entry never appears.
- **Why they're here:** both are already marked *"Opportunistic"* on the old Aug-1 card, which
  had nowhere to put that class of row — so they went nowhere. This is the place.

---

## Parking lot (pull one when a slot frees)

| Row | Watch for | Note |
|---|---|---|
| `C9` (§8) | Two AI packages recovering at the same boat, spaced ≥5 min apart — not converging in the overhead | Needs two AI packages actually recovering |
| `G32` (§3) | The front-line JTAC orbiting the FLOT at 5,000 ft, lasing on 1113 | Any campaign with a blue JTAC faction |
| `K2` (§29) | The SITREP band renders on the Mission Info kneeboard page and reads correctly | Turn 2+ only; needs something to have happened |
| `B35` (§19) | Air-defence master off ⇒ no AD icons **and** the four class rows grey out | App-side, not a flight |
| `H10` (§27) | Two client flights sharing an airframe ⇒ a one-page callsign index at the front of the deck | Needs 2+ client flights of one type |

## Closed

*(Nothing yet — first list, seeded 2026-08-06.)*
