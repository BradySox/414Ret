# WATCH — standing list for the daily fly

**Things to look for in whatever you were flying anyway.** No mission is built for these, no
toggles are flipped, no campaign is required. Five slots, hard cap.

When one closes, note it in the matching checklist row the **same session** with the date
(flown results get clobbered otherwise), move it to [`ARCHIVE.md`](ARCHIVE.md), and pull the
next from the parking lot.

---

## The list

*(Refilled 2026-08-22. Slots 1–2 carried over; 3–4 are new. The previous parking lot was
cleared — both entries named rows that had already closed, `Q3` VERIFIED and the loadout
watch pointing at RETIRED `B42`.)*

### 1 · The ramp time you are given matches the airframe you are starting — `B77`

**Where:** the mission-start briefing card and the kneeboard, any flight. **~1 min.** App-side.

- **Pass:** a Tomcat and a Viper starting cold get different allowances, each the airframe's own.
- **Fail:** every airframe gets the same number.
- **Why it's here:** pulled from the parking lot 2026-09-16 when `B48` closed on the DM's call.

### 2 · The day's flying is reported back, and the numbers are believable — `B70`

**Where:** the next turn's SITREP, after any mission with several AI packages up. **~1 min.**

- **Pass:** the sortie count is close to the number of packages that **flew**, hits never
  exceed shots, and `state.json` is a few hundred KB.
- **Fail:** a sortie count near the theatre's whole aircraft inventory (idle ramp jets counted
  as flights), hits above shots, or a `state.json` over a megabyte.
- **Why it's here:** both defects were fixed on 2026-08-20 against test 12's own save and the
  fix has not been seen on a fresh mission. This is the cheapest row on the board — it closes
  from a mission you already flew.
- **Test 32 (2026-09-15, Persian Gulf, no player):** 92 records, 28 claimed air kills against
  27 in the recording (Shahed drones count), hits never above shots, `state.json` 672 KB. The
  file side passes; the SITREP itself was not opened.

### 3 · The planner behaviour bar actually switches the suite — `B54`

**Where:** the settings UI, Campaign Doctrine. **~1 min.** App-side.

- **Pass:** moving the bar changes the planner options underneath it, and a turn planned after
  the change reads differently from one planned before.
- **Fail:** the bar moves and nothing beneath it changes.
- **Why it's here:** pulled from the parking lot 2026-09-16 when `B78` closed on the DM's call.

### 4 · A ground-level waypoint sits at the field's elevation — `B79`

**Where:** the flight editor, any flight, ~30 s. App-side.

- **Pass:** a waypoint the plan puts on the ground reads the field's elevation, not sea level.
- **Fail:** a takeoff, landing or divert point at 0 ft on a field that is not at sea level.
- **Why it's here:** pulled from the parking lot 2026-09-15 when `B107` closed on test 32.

### 5 · A stuck TIC unit names itself, and the retries are spread — `B108`

**Where:** `dcs.log` after any mission with a front line, one grep for `stuck`. **~1 min.**

- **Pass:** each stuck line names its unit, and the retries are spread across many units
  rather than one unit retrying hundreds of times.
- **Fail:** unnamed stuck lines, or one unit holding most of the count.
- **Why it's here:** pulled from the parking lot 2026-09-16 when `B90` closed on the DM's call.
  Test 33 had a live front and no stuck line at all, so it is still unflown.

---

## Parking lot (pull one when a slot frees)

| Row | Watch for | Note |
|---|---|---|
| `B109` | `_retribution_backups` is gone from `UnitPayloads` and the launch error with it | App-side; set one default loadout first, then restart DCS |
| `B111` | F10 ground speed **and altitude** for a striker and its escort, after the join | First numbers recorded off test 32's recording (three Hornet-escort / Viper-striker legs); see the row. A measurement, not yet a pass/fail — it is what unblocks authoring `cruise_mach:`. Record the loadout with each number |

Closed and dropped items, with the reasoning: [`ARCHIVE.md`](ARCHIVE.md).
Contrived-condition tests live on [`LOCAL.md`](LOCAL.md).
How to write an item, and the three-cadence model:
[`414th-verification-cadence-notes.md`](../design/414th-verification-cadence-notes.md).
