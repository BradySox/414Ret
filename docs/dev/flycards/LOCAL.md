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

---

## Done

*(Nothing yet — first card, seeded 2026-08-07.)*
