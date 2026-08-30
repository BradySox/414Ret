# LOCAL — the rolling card for contrived conditions

**Things that will never close by themselves.** The sibling of
[`WATCH.md`](WATCH.md), and the distinction between them is the whole point:

- **WATCH** = zero setup. It closes from ordinary flying if someone is looking.
- **LOCAL** = a *contrived condition*. Something has to be deliberately arranged — a toggle
  flipped, a specific campaign loaded, or, most often, a thing made to happen on purpose.

Run it against the local fly, every 2–3 days. It needs no date of its own; unlike the event
card it is not tied to a scheduled session.

**Why this file exists** (created 2026-08-07): `G29` sat ◐ PARTIAL for four weeks and then
failed to close on the WATCH list *as well* — because it was never a watch item. It needs a
pilot to eject on purpose, which is precisely the contrived condition the WATCH rules exclude.
It had been parked on the one surface that structurally could not close it. The
three-cadence model in
[`414th-verification-cadence-notes.md`](../design/414th-verification-cadence-notes.md)
predicted exactly this gap and named this card as the fix; it just had not been built.

Conventions follow WATCH.md, and the session-start hook parses both files identically:
the `### ` heading states the observable in plain words, and a `**Try:**` line under it says
how to arrange the condition. Keep it short — a card nobody finishes is a card nobody reads.

**Only items under `## On the card` are printed.** Anything filed under `## Done` is history.
Until 2026-08-22 the hook read every `### ` in the file, so both closed rows below were
briefed as live work after they were crossed off — the card was right and the board was
wrong. `tests/test_flycard_board.py` now fails if a closed item is left in the live section.

---

## On the card

*(Refilled 2026-08-22. The card had been empty since 2026-08-20, and the session-start hook
was printing the two rows under **Done** as if they were still live work — so the board asked
for a test that had been crossed off two days earlier. The hook now reads only this section;
see the note at the bottom.)*

### 0 · Measure what the KA-99 actually covers — sizes the reveal radius `G40` uses

**Why this is a card and not a code change.** `TARPS_POD_RADIUS_NM = 3.0`
(`game/sim/missionresultsprocessor.py:36`) decides how close a TARPS pass must come to
find a hidden command post (§3 candidate A, row `G40`). Its own comment records it as
the *deleted* recon plugin's pod radius — it was never sized against a camera. The
2026-08-26 patch added the KA-99 panoramic camera, which is a real reason to widen it,
and **the F-14 manual documents no KA-99 at all** (checked: no "KA-99", no "panoramic"
anywhere in its 1,156 pages — the camera is newer than the manual). There is no number
to look up, so the only honest source is a measurement.

**Try:** any campaign with a client F-14 carrying the TARPS pod — Red Tide or a Vietnam
turn. Fly a straight, level pass at a **known altitude** past a line of enemy ground
units whose map positions you can read afterwards. Land (photos only develop after the
flight). On the TARPS page, note the **outermost unit that got circled** by the intel
analysis department on either side of track. **~20 min.**

- **Record:** pass altitude (AGL), and the lateral distance from your ground track to
  the furthest circled unit, left and right. Two or three passes at different altitudes
  is much better than one — the swath almost certainly scales with height.
- **Pass criterion:** none. This card produces a *number*, not a verdict. Write it into
  [`414th-recon-role-scoping-notes.md`](../design/414th-recon-role-scoping-notes.md)
  and the radius can then be set from evidence.
- **Watch for:** the KS-87 frame camera and the KA-99 panoramic have different coverage
  — note which was recording. The pilot can now run either (`hold Store Release`), so
  this no longer needs a human RIO.

### 1 · Red alert fighters answer a strike you just made — `B60`

**Try:** turn on the living-battlespace master **and** `living_battlespace_reactive_red` (it
defaults off), take a turn 3 or later, strike a red objective your own ATO is tasked against,
and stay within ~10 NM for ten minutes. **~25 min.**

- **Pass:** `dcs.log` carries `REACTRED|: armed`, then `<objective> struck; alert launch in
  420 s`, then `<group> scrambling over <objective>` — and a red pair sets up an orbit over
  what you hit.
- **Fail:** `could not wake <group>` (neither start path took), nothing after `armed` (the
  death event's unit name does not match the emitted list), or a red flight airborne at
  mission start (its parked TOT broke).
- **Why it's here:** the launch could never fire — the generated group is uncontrolled, not
  late-activated, so `activate()` was a no-op on it. Fixed plugin-side 2026-08-20 and not
  flown since. It is REGRESSED, so this is a bug re-test, not a first look.

### 2 · A target you destroyed stays destroyed next turn — `B63`

**Try:** frag a strike on a **map-scenery** target (a port, factory or terminal drawn as white
zones — not a spawned static). **Pick one sitting in clutter** — a dockside or built-up
objective, not an isolated building. Launch the mission, **quit to the menu after about a
minute, then relaunch and fly it properly.** Destroy the target, land, accept the results.
**~30 min.**

- **Pass (the snapshot fix):** the target reads destroyed on the next turn's map, and
  `retribution.log` carries `state.json on disk carries N recorded events but the last polled
  debriefing had only M — committing the fresh read`.
- **Pass (the matcher, new 2026-08-30):** `dcs.log` carries `Scenery objectives: N known, M
  already destroyed, match radius 30 m` at mission start, then one `Objective destroyed:
  '<zone>' (D m from the hit)` per building you flatten.
- **Fail:** the target is still standing next turn, a kill is charged twice, or `Objective
  destroyed` fires for a building you never hit (report the logged distance before anyone
  changes the 30 m radius).
- **Why it's here:** this row now covers **two independent causes**, both real. The
  quit-and-relaunch is the exact condition that broke the first and is the one thing an ordinary
  sortie never does by accident. The second — an objective sharing its zone with indestructible
  scenery, so it could never be credited at all — was fixed 2026-08-30 from upstream #957 and
  is why the target must sit in clutter: an isolated zone would have passed before the fix too.

## Done

### 1 · A downed pilot turns up MIA, then evades — `G29` — **OFF THE CARD 2026-08-20**

Closed twice over, and it should have come off the card the first time:

- **Verified 2026-07-17** at scale on a fresh Scenic Route turn 1 — 10 survivor groups, 12
  snatch parties, `combat_sar_survivors: 8` flushed clean, the player’s own pilot banked as an
  evader. MIA banking and ledger hygiene both confirmed. That is the arc this card was
  written to see, and it was already seen three weeks before the card was created.
- **Retired 2026-08-07** when §21/§15 were removed and replaced by upstream #929. Nothing this
  row describes still exists — no snatch race, no POW hold, no `combat_sar_survivors`. There
  is nothing left to fly. Upstream’s CSAR needs its own rows (B71–B75, G33–G38).

The card was created on 2026-08-07 — the same day the feature was deleted — citing a four-week
stall as the reason it existed. The stall was real; the row was simply already answered and
about to be moot. **The lesson is the card’s own:** check the checklist row before seeding a
fly card from it, or the card briefs a test nobody can run.

### 2 · A full deck still parks 16 jets with the decorations on — `B25` follow-on — **CLOSED 2026-08-20**

DM verdict: B25 is verified. The capacity half is answered by its own strongest evidence —
the 2026-08-18 Syria turn parked **24 jets on CVN-72** (8 BARCAP + 16 BAI, all
`TakeOffParkingHot`) plus 8 on LHA-1 with `carrier_deck_decorations` **on**, and every one
launched, with the six-pack last-resort path never used. 24 is well past the 16 spots this
row worried about, so "the decorations-on run parks fewer" cannot be sustained.

The decorations-off control run was never run and now will not be. **What survives, as a note
and not a test:** `KNOWN_PARKING_SPOTS` holds 11 of the Supercarrier guide’s 16 spots, with a
63.2 m starboard stretch carrying 52 of the 67 street placements and no table entry. That did
not cost anything measurable across 24 spawns. If a "your flight is delayed to start" ever
turns up on a dressed deck, re-measure that gap first — do not re-seat the gear on the raw
campaign A offsets, which is a separate accepted drift.
