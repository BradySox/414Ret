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

---

## On the card

### 1 · A downed pilot turns up MIA, then evades — `G29`

**Try:** in an ordinary ATO jet — **never a dynamic slot**, those can never go MIA by design —
eject deep over enemy ground, end the mission with no rescue, then pass the turn. **~10 min.**

- **Pass:** next mission that pilot reads **MIA** in three places — the SITREP band, the
  squadron roster, and an **orange marker** on the map at his last known position — and he
  re-spawns as an evader there, with a fresh snatch race against him.
- **Fail:** the pilot is simply **dead** and no MIA entry ever appears anywhere. That is the
  signature worth catching, because it is silent: the whole §21 rescue economy would be doing
  nothing and nothing would say so.
- **Why it's here:** the Lua half is already proven live (2026-07-11 — the no-asset path armed
  instead of bailing, and `combat_sar_survivors` was written). What has **never** been seen is
  the Python turn-boundary arc: MIA flip → SITREP / roster / map → next-mission respawn. That
  half is unit-tested and unflown, and every consequence of it is player-facing.
- **One trap, already paid for once:** the 2026-07-11 run *did* leave a survivor entry, but it
  belonged to a **DCS dynamic-slot** jet, which `record_downed_pilots` correctly discards. If
  you eject from a dynamic slot this test proves nothing and looks like a failure.

### 2 · A full deck still parks 16 jets with the decorations on — `B25` follow-on

**Try:** load a Nimitz-hull campaign (Stennis / CVN-71 / 72 / 73 / 75), frag a **cold** carrier
mission with at least 16 deck starts, and count the jets that actually make it onto the deck.
Then flip `carrier_deck_decorations` **off**, regenerate the same turn, and count again.
**~15 min**, most of it generation.

- **Pass:** both runs park the same number. The Supercarrier guide documents **16 parking
  spots + 4 catapults**, so a healthy deck fills 16.

> **Test 9 (2026-08-18) — strong partial, the control run is still owed.** A Syria turn parked
> **24 jets on CVN-72** (8 BARCAP + 16 BAI, all `TakeOffParkingHot`) plus 8 on LHA-1, with
> `carrier_deck_decorations` **on**, and every one launched — the six-pack last-resort path was
> never used. That is well past the 16 spots this card worries about, so "the decorations-on run
> parks fewer" is hard to sustain. What is still missing is the **decorations-off control run on
> the same turn**, which is the actual comparison. Row stays open for that.
- **Fail:** the decorations-on run parks fewer, or a jet reports *"your flight is delayed to
  start"* while the control run does not. Either means a street static is standing on a spawn
  spot.
- **Why it's here:** `KNOWN_PARKING_SPOTS` holds **11** spots. ED documents **16**. On the
  starboard side our table runs out at `x = −35.5` (aft end of the six-pack row) and does not
  resume until `x = −98.7` (El-3 shoulder) — a **63.2 m stretch with no entry** — and **52 of
  the 67** street-gear placements sit inside it. Every variant's guard-tested clearance
  (12.7–14.7 m) is measured to `(−35.5, 34.0)`, the *edge* of that gap; nothing inside it is
  tested, because nothing inside it is in the table. The manual's parking diagram puts
  **spots 5 and 6** in that region — forward of the island on the starboard deck edge, with
  spot 5 drawn E-2-sized.
- **Why B25 does not already cover it:** B25 closed 2026-08-06 on the DM's "Passing" verdict,
  which answered the *appearance* symptoms — gear on the deck, nothing floating, nothing out of
  place. The parking-capacity half of its criterion was never run. This card is that half and
  only that half; it does not reopen B25.
- **One trap:** a blocked spot is **silent**. §72's own history is that late-activated groups
  spawn *into* statics rather than skipping them, so the failure can look like a normal deck
  rather than an error. Count, do not eyeball.

---

## Done

*(Nothing yet — first card, seeded 2026-08-07.)*
