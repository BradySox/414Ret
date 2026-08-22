# Fly-card archive

Items that have left [`WATCH.md`](WATCH.md). Kept because the *reason* is the record — a
dropped item is not a closed one, and re-adding either without reading why it went is how the
same question gets asked twice.

The live card stays short. This is where its history lives.

---

## Closed

| Closed | Item | Row(s) | Verdict |
|---|---|---|---|
| 2026-08-18 | The ATO talks on the AWACS frequency | `B59` | **Feature removed, not verified.** DM call: "the AI already uses the radio" — the synthesized net duplicated chatter DCS produces on its own. It armed 48 scheduled calls on the 2026-08-17 mission and whether any played was never established; that question is now moot. |
| 2026-08-17 | The boat is steaming down the angled deck, not the bow | `B55` | ☑ **VERIFIED, computed from the flown `.miz`.** CVN-72 on BRC 249 at 17.7 kt against a wind from 220 at 8 kt gives 25.0 kt of relative wind 8.9° off the port bow — down a ~9° angled deck, and 25 kt is exactly the §88 target. LHA-1 steams 220, bow-into-wind, correct for a deck with no angle. **Recorded a day late**, which is why the card kept asking. |
| 2026-08-17 | Jets are parked on the ramp that already flew today | `B57` | ☑ **VERIFIED** on the DM's call. |
| 2026-08-17 | The kneeboard fuel ladder is not blank | `H11` | ☑ **VERIFIED** on the DM's call, clearing a REGRESSED mark. |
| 2026-08-17 | Your SA page has other people on it | `B64` | ☑ **VERIFIED** — "B64 is good". Opened and closed the same day. Also closes the manual step #858 shipped owing: the policy is set to Era-correct in the save **and** the settings baseline, so new campaigns no longer inherit the migrated `Never`. |
| 2026-08-17 | Air-defence master off greys out its four class rows | `B35` | ☑ **VERIFIED** — "B35 good". Pulled from the parking lot that morning, closed on the first look. The panel render, the class-row greying and the stored-state migration are the parts CI cannot reach. |
| 2026-08-17 | Civil airliners cross the map high instead of falling out of the sky | `I2` | ☑ **VERIFIED from Tacview** — no flight needed, see below. |
| 2026-08-16 | The JTAC over the front line actually lases | `G32` | ☑ **VERIFIED** — "G32 is good". Closes the only JTAC model in the fork, flown for the first time since the 2026-08-05 strip. Recorded in the checklist on 2026-08-16; the card slot was not cleared until 2026-08-17, which is the failure the "cross it off" rule exists to prevent. |
| 2026-08-06 | Loadouts are mixed, not identical | `B42` (§84) | **Disliked → feature ripped.** "I've seen and disliked, revert or rework" → full rip; the objection was *turn 1 already downgraded*. §84 is removed, not re-tuned — see B42 for why there was no third setting to try. |
| 2026-08-06 | Civil traffic is region-plausible | `I2` | ☑ **VERIFIED** — "looks good". First eyes on the 2026-08-05 rebuild. |
| 2026-08-06 | SAM and missile sites have a support section | `B43` · `B44` · `B47` (§85) | ☑ **VERIFIED** ×3 — "Passing". Three rows on one glance, as intended. |
| 2026-08-06 | Carrier deck gear sits on the deck | `B25` (§72) | ☑ **VERIFIED** — "Passing". The 2026-08-05 float/drift report **did not reproduce**; closes DM work order #2 by non-reproduction. Hull + variant weren't recorded, so 1 of 6 variants was seen. |

### I2 closed from the recordings, 2026-08-17

The DM asked whether this could be settled in Tacview instead of the cockpit. It could, and it
is: **52 fixed-wing civil tracks across all six recordings.**

- **They reach their assigned level.** Peak altitude is FL200, FL259 or FL308 — exactly the
  three authored cruise levels, nothing in between and nothing lower. 31 of 52 spend ≥40 % of
  the track at or above FL180; several are level for 100 % of it.
- **The climb case works.** Tracks starting at FL0–1 reach FL200–259, so the missing
  waypoint-between-takeoff-and-landing fix took.
- **Nothing falls.** 40 of 52 have a descent moment steeper than 6,000 fpm, which looks alarming
  until you check the speed: every one is at **295–406 kt ground speed**, i.e. a powered arrival.
  A below-stall fall — the actual 2026-08-08 defect — is under 100 kt and decaying. Every track
  also survives to the end of its recording; there are **no civil wrecks** in any of the six.

**One number worth a second look, not a defect:** `ARKTIKA 134` (An-30M) shows 78 kt ground
speed in one 10-second window while essentially level at FL200. Every other An-26/An-30 sample
sits at 222–303 kt. One window is not evidence of anything, but if a slow civil contact ever
turns up on the F10 map, this is the thread.

**Not settled, and it does not need a flight:** the density question the 2026-08-05 rebuild
deliberately left open. The count is **16 civil aircraft per mission** (12 fixed-wing + 4
rotary) on Caucasus. That is a taste call, and the DM now has the number to make it without
flying anything.

---

## Dropped (considered and deliberately not watched)

These are **not** closed — every checklist row keeps its existing status and still needs a pass
eventually. They were judged not worth a standing watch slot. Do **not** move them back to the
parking lot without a fresh call.

| Dropped | Item | Row(s) | Why it went |
|---|---|---|---|
| 2026-08-22 | "Apply to all" moves every flown leg's altitude | `Q3` | **Already VERIFIED when the parking lot was briefing it.** Dropped from the parking lot, not watched. |
| 2026-08-22 | Loadouts are identical again across flights of one airframe | `B42` (§84) | **The feature is RETIRED.** There is nothing left to look at; the row was kept only so old notes stay readable. Dropped from the parking lot. |
| 2026-08-06 | SITREP page in the kneeboard | `K2` | Cosmetic doc surface. You either see it or you don't; it does not warrant standing attention. |
| 2026-08-06 | Two AI packages recovering at the boat | `C9` | **Assessed a one-off and accepted** (DM call). Evidence checked: exactly ONE carrier-recovery midair on record, ever — Scenic Route turn 3, 2026-07-16 — and no other collision report anywhere in the checklist. The fix is live (`_deconflict_carrier_recoveries`) and test-covered, and the part that is testable headlessly (≥5 min TOT spacing) is the deterministic part. **Honest caveat: the one-off is the BUG, not the FIX** — the fix shipped the same day it was found and has never been observed working. What makes that acceptable is that a recurrence self-reports: two AI aircraft dying at the boat shows up as unexplained AI losses in the debrief. If that ever appears, widen `CARRIER_RECOVERY_INTERVAL`. |
| 2026-08-06 | Shared-airframe kneeboard index | `H10` | Condition (2+ client flights in one airframe) is MP-only and has not arisen since 2026-06-28. Costs a glance if it ever does. |
| 2026-08-06 | Rear-base QRA · downed pilot goes MIA | `A5` · `G29` | Sat PARTIAL since 2026-07-11 and did not close on the watch list either. **The aged-out call was made 2026-08-07** and split them, because they had nothing in common but a date: **`A5` → ☑ VERIFIED.** The 2026-07-11 fly *did* watch for the fail signature and it did not occur; it was held back only on the marquee 147 NM distance, and distance turns out not to be a threshold — `disengage_nm` is **derived** from the scramble reach (`max(gci, reach) + engage + margin`), so a defender being leashed short is structurally unreachable. Residual is a *fuel* RTB on a long transit: a degradation, self-reporting. **`G29` → SCHEDULED**, on the [`LOCAL.md`](LOCAL.md) card. It was never a watch item — it needs a pilot to eject on purpose, a contrived condition the watch rules explicitly exclude — so it had been parked for four weeks on the one surface that structurally could not close it. |
