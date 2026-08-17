# Datalink era gating — why the EPLRS boolean became a policy

**Status:** built 2026-08-16, session `c86c58dd`. Replaces the `eplrs_enabled` boolean with
`DatalinkPolicy` and adds `datalink_introduced:` to the aircraft data files.

---

## 1. What EPLRS actually is here

DCS reused the name. **Enhanced Position Location Reporting System** is a real US Army networked
radio — the A-10C's SADL runs on it — but the `EPLRS` task on a DCS group is the generic
*datalink-enable* switch. It is what makes a group take part in datalink at all:

| Aircraft | What the task actually enables |
|---|---|
| F/A-18C, F-16C, F-15C | **Link 16** — the SA page, donors, PPLI/SURV tracks |
| A-10C | SADL (genuinely EPLRS) |
| Ground units | their own datalink net |

Without the task the terminal never comes up. In the cockpit that reads as an empty SA page, not as
an error — which is what made this expensive to find.

## 2. The flown evidence

A generated Caucasus mission versus a hand-built modern campaign mission, same install, same mods:

| | blue plane groups carrying the EPLRS task |
|---|---|
| ours | **1** of 23 — and that one was the JTAC drone |
| hand-built reference | **16** of 18, including the player |

Both flown saves carried `eplrs_enabled = False`, inherited from
`Saved Games/DCS/Retribution/Settings/Default.zip`. The code default was `True`; the older
`Default.audit-backup.zip` still is. It had been flipped at some point, and the label —
"Enable EPLRS" — gives no hint that it costs every jet its datalink.

**Ruled out on the way, do not re-chase:** the DTC cartridge (DCS's own
`FA-18C_hornet_DTC.lua` declares `ALR67, COMM, WYPT, GPS_WYPT, SA, TCN, HARM` — there is **no**
datalink field in the Hornet cartridge schema, so it cannot enable or disable Link 16), the Link-16
STNs (valid octal, no duplicates, E-2C on the net), and the user's OVGME mods.

## 2a. The gate restores; it does not add

Worth knowing before you read the code, because it inverts the obvious reading. **pydcs already
gives every capable airframe the task**: `dcs/mission.py:736` — `if _type.eplrs:
wp.tasks.append(task.EPLRS(...))` at group creation. Retribution then throws it away —
`AircraftBehavior.configure_behavior` opens with `group.points[0].tasks.clear()` (line 130) — and
`configure_eplrs`, which runs at the end of `apply_to`, is the only thing that puts it back.

So the policy is not "should this aircraft be given a datalink". It is "should we restore the one
DCS already gave it". `NEVER` actively strips a capability the sim would otherwise have provided,
which is exactly why hand-built Mission Editor missions have it and ours did not: the ME never
clears the task in the first place.

## 3. Why a boolean could never be right

The fork ships campaigns from 1981 to 2027. One switch has two settings and both are wrong
somewhere:

| | Red Tide 1988, Desert Storm 1991 | Inherent Resolve 2016, Marianas 2027 |
|---|---|---|
| **on** | Hornets with Link 16 a decade early | correct |
| **off** | correct | no datalink at all |

This is the same shape as the §24 payload-property gate (JHMCS on the Hornet from 2003) and the
weapon-date gating: a capability that arrives on a date, per airframe.

## 4. Why pydcs's own flag cannot answer it

`AircraftType.eplrs_capable` is `getattr(dcs_unit_type, "eplrs", False)`. That flag means only
"DCS lets you tick the box", and it is **true for 87 airframes** — including the **B-47 Stratojet,
the Tu-16 Badger, the OV-10A Bronco and the SA-342 Gazelle**. It answers "can this ever have a
datalink", never "by when". Hence a separate per-airframe year.

## 5. The design

- `datalink_introduced: <year>` in the aircraft data file — the year that airframe's tactical
  datalink was in squadron service, **not** the year the airframe was.
- `DatalinkPolicy` in Settings: `ERA_CORRECT` (default for new games), `ALWAYS` (the old "on"),
  `NEVER` (the old "off").
- `game/datalinkera.py::datalink_available(policy, introduced, campaign_year)` is the whole rule.
- **Absent date reads as permissive.** An un-authored airframe behaves exactly as it did before the
  gate existed. That makes the data set extensible one airframe at a time and means a missing entry
  never silently strips a capability from something nobody has researched.
- **Ground units** are unaffected by `ERA_CORRECT` — whether a vehicle exists at all in a given year
  is already settled by its own introduction date, so there is nothing further to decide. Only the
  explicit `NEVER` turns them off.

### Save migration

The boolean maps to the explicit choice, **not** to `ERA_CORRECT`: a campaign that deliberately had
datalink off stays off, and one that had it on does not lose it mid-campaign because an airframe's
date postdates the campaign. `ERA_CORRECT` is the default for new games only. Mirrors how the §64
six-pack boolean became `CarrierDeckPolicy`.

## 6. The authored dates, and how good they are

14 airframes, chosen as the ones the fork's own era-split campaigns actually field. Each is the
airframe's datalink in squadron service, accurate to about a year — good enough to separate a 1991
campaign from a 2016 one, which is the entire job. **They are not a citation-grade dataset**, and
should be corrected in place by anyone who has better sourcing.

| Airframe | Year | System |
|---|---|---|
| F/A-18C, F/A-18E/F | 2002 | MIDS-LVT / Link 16 |
| F-16C Block 50 | 2003 | Link 16 with the CCIP tape |
| F-15C | 2000 | MSIP II JTIDS / Link 16 |
| F-15E Suite 4+ | 2004 | Link 16 |
| EA-18G | 2009 | IOC, born with Link 16 |
| A-10C, A-10C II | 2007 | SADL |
| E-2C | 1994 | JTIDS / Link 16 |
| E-3A | 1988 | JTIDS Class 1 |
| F-22A | 2005 | IOC, Link 16 receive-only |
| MQ-9 | 2007 | |
| AH-64D Block II | 2003 | |

Everything else in the fleet is un-authored and therefore unrestricted. Adding a row is a one-line
data change with no code.

## 7. What is NOT modelled

- **Per-variant dates.** The gate is per `AircraftType`, so a Lot 20 Hornet and an early Hornet share
  one year. The variant machinery could carry it if that ever matters.
- **Datalink *quality*.** Receive-only versus full participation (the F-22A's Link 16 is
  receive-only) is one boolean either way in DCS.
- **Red-side networks.** Su-30SM/Su-35S carry their own datalink; no dates authored, so they are
  unrestricted. Worth doing if a Cold War campaign ever fields a modern Flanker.
