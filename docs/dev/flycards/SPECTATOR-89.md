# SPECTATOR-89 — closing the living-battlespace rows without flying

**One session, no cockpit.** Five §89 rows (`B56`–`B60`) are all written as "fly a sortie and
look around", but every observable in them belongs to the **AI**, not to you. This card
re-shapes them for a spectator: take a slot, never move the throttle, and watch the war on
F2 / F10 / Tacview.

Not a third cadence. This is a one-off session plan for §89, sitting beside
[`WATCH.md`](WATCH.md) (zero setup, closes from ordinary flying) and
[`LOCAL.md`](LOCAL.md) (the rolling contrived-condition card). Delete it when the five rows
close.

Rows live in [`414th-ingame-pass-checklist.md`](../414th-ingame-pass-checklist.md); design
rationale in [`414th-living-battlespace-notes.md`](../design/414th-living-battlespace-notes.md).

---

## Before you start — five things that decide whether the session proves anything

1. **Keep a client flight in the ATO.** `auto_preroll_stop_needed` ends in
   `game.ato_has_clients()`: with no player flight there is **nothing to pin the pre-roll to
   and no pre-roll runs at all**. Frag your normal package, take the slot, then sit there.
   A "pure spectator" mission with zero client slots silently tests nothing.
2. **Generate the turn twice — gate off, then gate on.** Same save, same turn. The gate-off
   miz is the control, and without it half the checks are unfalsifiable: a stock generation
   already carries air starts (measured 4 of 118), uncontrolled jets (27 — QRA templates and
   idle aircraft) and ~111 embedded sound clips. Only the delta is §89.
3. **Time acceleration is single-player only.** `LCtrl+Z` accelerates sim time, and the
   plugins schedule on `timer.getTime()`, so the 7-minute reaction delay and the two-hour wave
   window ride along with it. In multiplayer you wait in real time.
4. **Allow external views.** If `external_views_allowed` is unticked, Retribution forces F2
   off in the miz and there is nothing to spectate.
5. **Run the adjudicator afterwards.** It reads both mizzes plus `dcs.log` and prints a
   verdict per row:

```bash
python tools/spectator_89_report.py --control off.miz --test on.miz
```

---

## The cards

### 1 · The war is already up when you open your eyes — `B56`

**Try:** gates on, **turn 3+**, cap at the default 40. Spawn, do nothing, go straight to F10
and then F2 through the AI. **~10 min.**

- **Pass:** several AI flights are mid-route rather than on ramps, at least one recovers at a
  friendly field within ~20 min, and the DCS clock reads mission start plus the pre-roll.
- **Fail:** the whole ATO is on the ramp with you (the launch flow never marched the sim), or
  you spawn already airborne (the PLAYER_STARTUP halt fired late).
- **Also check:** repeated *"No room on runway or parking slots"* in `logs/retribution.log`.
  Once is the known fallback; a cluster is parking overflow.
- **Turn 0 is a separate check, and it is a UI one:** generate turn 0 with the gate on and
  off and run the adjudicator on the pair. The curve's zero means the two should not differ.

### 2 · Jets parked that no one flew in — `B57`

**Try:** same generation as card 1. F10 map, then F2 around a rear friendly field, especially
one that is **not** a squadron's home base. **~10 min.**

- **Pass:** parked, engines-cold jets sit at a field the control generation left empty, and an
  egressing AI strike flight shows bare pylons (pods may remain).
- **Fail:** a returner still carrying bombs; the same flight appearing both airborne **and**
  parked (a flight must take exactly one path); residue on a carrier deck (the naval guard
  leaked).
- **Free extra:** strafe one of the parked jets. It is a real registered airframe, so the loss
  must show in the debrief. Nothing else on this card needs a weapon.

### 3 · The sky does not die behind you — `B58`

**Try:** same generation. Read the DCS briefing screen first, then sit through the back half
of the mission — time-accelerate. **~20 min at 4×.** **~90 min real time.**

- **Pass:** the briefing carries "The air war so far today" with plausible per-side counts, and
  AI packages are still starting up and launching well after the point your own sortie would
  have ended.
- **Fail:** nothing launches late. Discriminate before blaming the feature — the adjudicator
  reads the activation triggers straight out of the miz. Triggers present at late times but no
  launches means the trigger *conditions* are the suspect (the hostile-airbase guard); no late
  triggers at all means the spread window never widened.
- **Also check:** counts higher than the ATO has flights (the census double-counting).

### 4 · The ATO talks, and you can read it — `B59`

**Try:** before generating, set the **battlespacenet** plugin option *"Show each call as a
subtitle too"* to **1**. Both gates on, turn 3+. Watch the screen, not the radio. **~20 min.**

- **Pass:** call text appears at plausible moments matching visible events — a wave launches
  and its check-in follows; a package nears its TOT and it pushes — with no two calls stacking
  and no calls from a flight you just watched die.
- **Fail:** `BSNET|: no calls emitted` in `dcs.log` (emitter gate or no blue AWACS); a wall of
  calls (rate limit not holding); your own package voiced over.
- **What this card cannot close:** audibility and voice quality. Those need a radio tuned to
  the AWACS channel, which is cockpit work. **`B59` stays ◐ PARTIAL after this session** — the
  schedule, liveness and rate limit are proven, the sound is not.

### 5 · Red scrambles over a target it just lost — `B60`

**Try:** both gates on, and **drop the pre-roll cap to 5** (or use turn 1). Then simply watch
a blue AI strike package work — the watch list is the red objectives blue's own ATO is tasked
against, so you do not need to drop anything yourself. Stay on the objective ~10 min after the
hits, or time-accelerate. **~15 min.**

- **Pass:** `dcs.log` reads `REACTRED|: armed`, then `<objective> struck; alert launch in
  420 s`, then `scrambling over`, then `on station over` — and F2/Tacview shows a red pair
  starting up cold and settling into an orbit over the struck objective.
- **Fail:** `armed` present but no launch after a confirmed kill (the death-event name match);
  a reaction from a group or over a point that was never emitted (**positive-list leak — this
  is a stop-ship, not a bug report**); the alert flight airborne at mission start; a takeoff
  wedged by the orbit push.
- **Why the short cap matters:** with a 40-minute pre-roll the strike that would trigger the
  reaction can resolve *during* the pre-roll, off-screen. No death event fires in the mission
  and the row reads as a silent failure that never happened.

---

## Filing the results

Write each row the **same session**, with the date and the session id — flown results get
clobbered otherwise. `NOT OBSERVED` is not a pass: for features whose failure mode is silence,
it is the thing to chase next.
