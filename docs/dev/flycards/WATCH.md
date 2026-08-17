# WATCH — standing list for the daily fly

**Things to look for in whatever you were flying anyway.** No mission is built for these, no
toggles are flipped, no campaign is required. Five slots, hard cap.

When one closes, note it in the matching checklist row the **same session** with the date
(flown results get clobbered otherwise), move it to [`ARCHIVE.md`](ARCHIVE.md), and pull the
next from the parking lot.

---

## The list

### 1 · Your SA page has other people on it — `B64`

**Try:** set Settings → Mission Generator → Gameplay → **Datalink** to **Era-correct**, in the
current save **and** again with no campaign loaded so the settings baseline takes it. Then fly a
modern campaign and look at the SA page. **~5 min.**

- **Pass:** on a 2000s-or-later campaign you see friendly PPLI and surveillance tracks — the
  flight, the AWACS, the tanker. On a 1991-or-earlier campaign the page is empty and that is
  correct.
- **Fail:** the SA page is empty on a modern campaign. Check `dcs.log` for the group's `EPLRS`
  task, and check the policy actually saved — the old `false` migrates to **Never**, so this
  reads identical to the bug it replaced.
- **Why it's here:** the boolean became a per-airframe era gate on 2026-08-17 (#858) and 14
  airframes carry dates. The mechanism is tested; whether the terminal comes up is DCS-only.
  **Your saved baseline carried the old off value**, so this is the first thing that will bite.

### 2 · Air-defence master off greys out its four class rows — `B35`

**Where:** the custom map layers panel, no flight involved. **~10 s.**

- **Pass:** unticking the air-defences master clears every AD icon from the map **and** the four
  class rows below it grey out, because they are filters of the master rather than peers of it.
- **Fail:** icons stay; or the class rows stay live and can be ticked while the master is off.
- **Why it's here:** pulled from the parking lot 2026-08-17 when slots 1 and 2 closed.

---

## Parking lot (pull one when a slot frees)

| Row | Watch for | Note |
|---|---|---|
| — | Loadouts are **identical** again across flights of one airframe + task | Confirms the §84 rip landed in the build you actually run. Low priority: the removal is test-covered |

Closed and dropped items, with the reasoning: [`ARCHIVE.md`](ARCHIVE.md).
Contrived-condition tests live on [`LOCAL.md`](LOCAL.md).
How to write an item, and the three-cadence model:
[`414th-verification-cadence-notes.md`](../design/414th-verification-cadence-notes.md).
