# WATCH — standing list for the daily fly

**A short list of things to look for in whatever you were flying anyway.** No mission is built for these,
no toggles are flipped, no campaign is required. They close from ordinary flying if — and only
if — someone is looking.

Rules that keep this useful:
- **The heading IS the item.** The session-start hook prints *only* the `### ` line — never
  the body under it. So the heading has to state, in plain words, the thing you would see out
  the window or on screen. A row ID, a section number, or a meta-label is not a description:
  "The opportunistic pair — `A5` (§1) · `G29` (§21)" told the reader nothing and came back
  marked "?" for exactly that reason (2026-08-06). **Nobody is going to look up a feature
  number to find out what they are supposed to be looking at.** Keep the short row tag at the
  end so a result can be filed to the right checklist row; drop the `§N` — it is noise to the
  person flying and the row tag already leads there.
- **A `**Try:**` line is for COCKPIT work only** (DM call, 2026-08-06: *"drop the Try line
  from anything not in the cockpit — stuff we can figure out in the UI shouldn't need it"*).
  The hook prints it directly under the heading, so it is the second half of what reaches the
  reader — but it only earns that space when the check needs you **in DCS**: an in-jet
  procedure, a laser code, a thing to watch in the sim, a way to *force* an otherwise
  opportunistic event. **If the item resolves in the Retribution UI — frag a flight, generate
  a turn, open a panel, read a kneeboard — it gets NO Try line.** Explaining ordinary app
  usage to the person who built the app is noise. Those items use a plain `**Where:**` line
  instead, which the hook does not print, and the heading carries them on its own. Wrap a Try
  across source lines freely — the hook joins it back up and ends it at the first blank line.
- **Five items, hard cap.** A watch list of twenty is a watch list of zero.
- An item earns its place by needing **no setup**. Anything needing a test toggle, a specific
  campaign, or a contrived condition belongs on a local card instead.
- Seeing it once is enough. Note it in the matching checklist row **the same session**, with
  the date — flown results get clobbered otherwise.
- When an item closes, cross it off and pull the next one from the parking lot below.

Design rationale + the three-cadence model: `docs/dev/design/414th-verification-cadence-notes.md`.

---

## The list

*(2026-08-06, second pass same day: the DM dropped four of the five replacements on
review — see **Dropped** below for why each went. Deliberately **not** refilled to five; the
cap is a ceiling, not a quota, and a short list that gets looked at beats five that do not.
Pull from the parking lot when there is appetite. **Item 2 added 2026-08-08** — not pulled from
the parking lot, but a fresh defect fixed that day whose only remaining question is in-sim.)*

### 1 · The JTAC over the front line actually lases — `G32`

**Try:** carry an LGB on a CAS run along the FLOT. The FAC is **invisible**, so look for
the spot, not the aircraft — it orbits ~5,000 ft and lases on **code 1113**. **~15 min.**

- **Pass:** a single FAC orbits the front line at ~5,000 ft, is **invisible and immortal**,
  and **lases on code 1113** — put a laser-guided weapon on its designation and the weapon
  guides.
- **Fail:** no FAC over the FLOT at all; it is visible/killable; or it orbits but never
  designates, so an LGB has nothing to track.
- **Why it's here, and why it leads the list:** JTAC was **stripped back to upstream's model
  on 2026-08-05** (the packaged-drone JTAC and both its settings were ripped out). This is
  now the *only* JTAC model in the fork and **it has never been flown in that state** —
  freshest change on the board with zero eyes on it.

### 2 · Civil airliners cross the map high instead of falling out of the sky — `I2`

**Try:** pick any civil contact on the F10 map (`AEROFLOT 412`, `INTERFLUG 208` — the operator
name is the label) and watch its altitude for a minute or two. **~2 min.**

- **Pass:** it holds its flight level (FL200–FL310) and tracks straight across the map.
- **Fail:** it descends steeply from the moment it appears; it never climbs above low level at
  all; or civil wrecks turn up on the map with nobody having shot at anything.
- **Why it's here:** two defects fixed 2026-08-08, both invisible to the app. Air-start speeds
  were written at **a third** of the planned figure (pydcs takes km/h, the planner passed m/s),
  so ~70% of fixed-wing traffic spawned below stall at cruise altitude and fell. And a transit
  departing from a field had **no waypoint between takeoff and landing**, so it never climbed
  to its assigned level. Both are pinned by tests, but **only DCS can show whether it flies**.
  Second question on the same look: **is there enough of it?** The old "judge density on this
  build" call was made against traffic that was falling down, so that judgement is owed again
  before anyone builds a concurrency scheduler.

---

## Dropped (considered and deliberately not watched)

These are **not** closed — every checklist row below keeps its existing status and still needs
a pass eventually. They were judged not worth a standing watch slot. Do **not** move them back
to the parking lot without a fresh call; the reason is the record.

| Dropped | Item | Row(s) | Why it went |
|---|---|---|---|
| 2026-08-06 | SITREP page in the kneeboard | `K2` | Cosmetic doc surface. You either see it or you don't; it does not warrant standing attention. |
| 2026-08-06 | Two AI packages recovering at the boat | `C9` | **Assessed a one-off and accepted** (DM call). Evidence checked: exactly ONE carrier-recovery midair on record, ever — Scenic Route turn 3, 2026-07-16 — and no other collision report anywhere in the checklist. The fix is live (`_deconflict_carrier_recoveries`) and test-covered, and the part that is testable headlessly (≥5 min TOT spacing) is the deterministic part. **Honest caveat: the one-off is the BUG, not the FIX** — the fix shipped the same day it was found and has never been observed working. What makes that acceptable is that a recurrence self-reports: two AI aircraft dying at the boat shows up as unexplained AI losses in the debrief. If that ever appears, widen `CARRIER_RECOVERY_INTERVAL`. |
| 2026-08-06 | Shared-airframe kneeboard index | `H10` | Condition (2+ client flights in one airframe) is MP-only and has not arisen since 2026-06-28. Costs a glance if it ever does. |
| 2026-08-06 | Rear-base QRA · downed pilot goes MIA | `A5` · `G29` | Sat PARTIAL since 2026-07-11 and did not close on the watch list either. **The aged-out call was made 2026-08-07** and split them, because they had nothing in common but a date: **`A5` → ☑ VERIFIED.** The 2026-07-11 fly *did* watch for the fail signature and it did not occur; it was held back only on the marquee 147 NM distance, and distance turns out not to be a threshold — `disengage_nm` is **derived** from the scramble reach (`max(gci, reach) + engage + margin`), so a defender being leashed short is structurally unreachable. Residual is a *fuel* RTB on a long transit: a degradation, self-reporting. **`G29` → SCHEDULED**, on the new [`LOCAL.md`](LOCAL.md) card. It was never a watch item — it needs a pilot to eject on purpose, a contrived condition these rules explicitly exclude — so it had been parked for four weeks on the one surface that structurally could not close it. |

## Parking lot (pull one when a slot frees)

| Row | Watch for | Note |
|---|---|---|
| `B35` (§19) | Air-defence master off ⇒ no AD icons **and** the four class rows grey out | App-side, not a flight — costs ~10 seconds in the map panel |
| — | Loadouts are **identical** again across flights of one airframe + task | Confirms the §84 rip landed in the build you actually run. Low priority: the removal is test-covered |

## Closed

| Closed | Item | Row(s) | Verdict |
|---|---|---|---|
| 2026-08-06 | Loadouts are mixed, not identical | `B42` (§84) | **Disliked → feature ripped.** "I've seen and disliked, revert or rework" → full rip; the objection was *turn 1 already downgraded*. §84 is removed, not re-tuned — see B42 for why there was no third setting to try. |
| 2026-08-06 | Civil traffic is region-plausible | `I2` | ☑ **VERIFIED** — "looks good". First eyes on the 2026-08-05 rebuild. |
| 2026-08-06 | SAM and missile sites have a support section | `B43` · `B44` · `B47` (§85) | ☑ **VERIFIED** ×3 — "Passing". Three rows on one glance, as intended. |
| 2026-08-06 | Carrier deck gear sits on the deck | `B25` (§72) | ☑ **VERIFIED** — "Passing". The 2026-08-05 float/drift report **did not reproduce**; closes DM work order #2 by non-reproduction. Hull + variant weren't recorded, so 1 of 6 variants was seen. |
