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

### 1 · The enemy C2 net is audible on the radio — `B23`

**Try:** tune the red UHF net while you are anywhere near a live enemy command post and listen
for CW/voice traffic; it is DF-able, so a bearing swing as you fly past is the confirmation.
**~5 min.**

- **Pass:** you hear the net, and the signal strength tracks your distance to the C2 site.
- **Fail:** silence with a live command post in range; or audio that does not change with range.
- **Why it's here:** §70's audible half has sat PARTIAL, and it needs ears rather than a test.

### 2 · Ships hold station instead of sliding off it — `B48`

**Where:** the F10 map, any naval group, twice ten minutes apart. **~1 min.**

- **Pass:** each group is still on its assigned station, walking a racetrack rather than
  drifting downrange.
- **Fail:** a group well off station, or stopped dead.
- **Why it's here:** §87 anchors the ovals; whether they hold over a long mission is a look.

### 3 · The day's flying is reported back, and the numbers are believable — `B70`

**Where:** the next turn's SITREP, after any mission with several AI packages up. **~1 min.**

- **Pass:** the sortie count is close to the number of packages that **flew**, hits never
  exceed shots, and `state.json` is a few hundred KB.
- **Fail:** a sortie count near the theatre's whole aircraft inventory (idle ramp jets counted
  as flights), hits above shots, or a `state.json` over a megabyte.
- **Why it's here:** both defects were fixed on 2026-08-20 against test 12's own save and the
  fix has not been seen on a fresh mission. This is the cheapest row on the board — it closes
  from a mission you already flew.

### 4 · The escorts leave you at the split instead of following you home — `B78`

**Try:** lead a package that has an escort or escort jammer on it and fly the whole profile.
At your split point, look behind you. **Free — it is the flight you were flying.**

- **Pass:** the escorts break off at the split and route to their own recovery field.
- **Fail:** they formate on you all the way home (the release never fired), **or** they break
  off at the *join* on the way in and call their own split index on the radio.
- **Why it's here:** the release fix landed 2026-08-18 and its first version reproduced the
  opposite failure, fixed again 2026-08-21. Neither shape has been flown since. Both failures
  are visible from the cockpit without looking anything up.

### 5 · The log is no longer 60 % one MOOSE error — `B107`

**Where:** `Saved Games/DCS/Logs/dcs.log` after any flight, one grep. **~1 min.**

- **Pass:** `grep -c "EVENTMETA data for event ID" dcs.log` returns 0, and every plugin still
  prints its startup banner (CTLD, CSAR, MANTIS, TIC).
- **Fail:** thousands of them still — the `414Ret patch` in the vendored `Moose.lua` was lost,
  most likely to a bundle bump. A *different* unknown event id means DCS added another event.
- **Why it's here:** it fired 6,807 times in one 7-minute mission and 11,861 in an archived
  Germany Cold War log, and it cannot be exercised headlessly — the harness never raises it.

---

## Parking lot (pull one when a slot frees)

| Row | Watch for | Note |
|---|---|---|
| `B79` | A ground-level waypoint sits at the field's elevation, not at sea level | App-side, ~30 s in the flight editor |
| `B77` | The ramp time you are given matches the airframe you are starting | App-side; a Tomcat and a Viper should not get the same allowance |
| `B54` | The planner behaviour bar actually switches the suite | Settings UI, ~1 min |
| `B108` | A stuck TIC unit names itself in the log, and the retries spread across many units | Same log, same read as slot 5; the distribution is the actual question |
| `B109` | `_retribution_backups` is gone from `UnitPayloads` and the launch error with it | App-side; set one default loadout first, then restart DCS |

Closed and dropped items, with the reasoning: [`ARCHIVE.md`](ARCHIVE.md).
Contrived-condition tests live on [`LOCAL.md`](LOCAL.md).
How to write an item, and the three-cadence model:
[`414th-verification-cadence-notes.md`](../design/414th-verification-cadence-notes.md).
