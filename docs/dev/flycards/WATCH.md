# WATCH — standing list for the daily fly

**Things to look for in whatever you were flying anyway.** No mission is built for these, no
toggles are flipped, no campaign is required. Five slots, hard cap.

When one closes, note it in the matching checklist row the **same session** with the date
(flown results get clobbered otherwise), move it to [`ARCHIVE.md`](ARCHIVE.md), and pull the
next from the parking lot.

---

## The list

*(All four previous items closed 2026-08-17 — `G32`, `I2`, `B64`, `B35`. Refilled from the
outstanding rows, choosing the ones that resolve on a glance at something you were looking at
anyway. Swap any of them out; nothing here is precious.)*

### 1 · Jets are parked on the ramp that already flew today — `B57`

**Where:** the ramp at mission start, before you go anywhere. **~1 min.**

- **Pass:** aircraft whose sorties finished before your start time are sitting on their home
  ramp, and they are **clean** — pylons empty, no stores hung on a jet that already dropped.
- **Fail:** an empty ramp when the briefing says packages already flew; or parked jets still
  carrying a full load.
- **Why it's here:** §89's residue tier decides what the field looks like when you walk out, and
  a wrong answer is visible in one glance and invisible to every test.

### 2 · The boat is steaming down the angled deck, not the bow — `B55`

**Where:** F10 map or the deck itself, any carrier mission. **~1 min.**

- **Pass:** the carrier's course is offset ~9–10° from the wind line, so the wind comes straight
  down the **angled** deck rather than over the bow.
- **Fail:** the boat steams directly into wind (bow-aligned), which puts the relative wind across
  the landing area.
- **Why it's here:** §88 changed the recovery heading and nothing has looked at the boat since.

### 3 · The kneeboard fuel ladder is not blank — `H11`

**Where:** the kneeboard flight-plan page, any airframe without measured fuel data. **~30 s.**

- **Pass:** every waypoint row shows a minimum-fuel and planned-fuel figure, including on
  airframes with no hand-measured consumption block.
- **Fail:** blank or zero fuel columns — the capacity-derived estimate is not filling in.
- **Why it's here:** this row is marked **REGRESSED**, so it is known broken rather than unknown.
  Confirming it either way costs one page turn.

---

## Parking lot (pull one when a slot frees)

| Row | Watch for | Note |
|---|---|---|
| — | Loadouts are **identical** again across flights of one airframe + task | Confirms the §84 rip landed in the build you actually run. Low priority: the removal is test-covered |
| `B23` | The red C2 net is audible on the radio and can be DF'd | PARTIAL — you would hear it on an ordinary sortie |
| `B48` | Ships hold station instead of drifting off it | PARTIAL — an F10 glance at any naval group |

Closed and dropped items, with the reasoning: [`ARCHIVE.md`](ARCHIVE.md).
Contrived-condition tests live on [`LOCAL.md`](LOCAL.md).
How to write an item, and the three-cadence model:
[`414th-verification-cadence-notes.md`](../design/414th-verification-cadence-notes.md).
