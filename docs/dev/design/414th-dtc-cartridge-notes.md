# Native DCS DTC cartridges (§74) — format reference + design

**Status:** LANDED 2026-07-19. This note is the source of truth for the cartridge
JSON shapes; read it before touching `game/missiongenerator/dtc/`.

## Where the format came from

Two authoritative sources, cross-checked:

1. **A working mission** — `Operation Broken Chain M1 v.2-personalized.miz`
   (hand-built, flown MP 2026-07-18): 12 client FA-18C + 8 client F-16C, every
   unit carrying the `DTC.Cartridges`/`AutoLoad` block, two `DTC/*.dtc` files
   ("Package Data FA-18C/F-16C"). The user's own Hornet pre-loaded everything with
   zero pilot action — the proof the mechanism works end-to-end in multiplayer.
2. **The DCS ME's own DTC editor** — `E:\DCS World\CoreMods\aircraft\FA-18C\DTC\`
   and `...\F-16C\DTC\` (per-jet descriptors: data model, element constructors,
   defaults, limits, import filters) plus
   `MissionEditor\modules\me_managerDTC.lua` (the miz read/write + unit binding).
   **"DTC-capable" is the unit DB flag, not the descriptor folder** (checked
   2026-08-22): `fillTypes()` lists a type when `DB.unit_by_type[t].DTC` is
   true, and `loadDescriptors()` then loads `<module>/DTC/<type>_DTC.lua`. Both
   halves must be present. Install-wide on 2.9.28 the flag is declared six
   times, and only three of them are usable:

   | Declaration | Verdict |
   |---|---|
   | `FA-18C/FA-18C_hornet.lua` = `true` | capable |
   | `F-16C/F-16C.lua` = `true` | capable |
   | `F14/Entry/F-14B.lua` = `rewrite_settings.Name == "F-14BU"` | capable, **F-14B(U) only** — the plain F-14B reads no cartridge |
   | `FA-18C/FA-18C.lua` = `true` (the AI Hornet) | no `FA-18C_DTC.lua` exists |
   | `MiG-29-Fulcrum/MiG-29-Fulcrum.lua` = `true` | AI-only module (`MiG-29 Fulcrum AI`, no `Cockpit/`) — nothing ingests a cartridge |
   | `CH-47F/CH-47F_bl1.lua` = **`false`** | descriptor folder ships, flag does not — **not capable** |

   The CJS Super Hornet mod sets its own flag in
   `Entry/FA-18EFG_AIRCRAFT_DATA.lua` and ships `DTC/{FA-18E,FA-18F,EA-18G}_DTC.lua`.
   **Do not read the capable set off the `CoreMods/aircraft/*/DTC` folders** —
   that is how CH-47F and the Fulcrum got wrongly listed here until 2026-08-22.

The retired §11 export predated all of this: it wrote cartridges to the local
Saved Games library (no MP distribution) against a DCS build whose pre-load didn't
fire. The in-miz + `AutoLoad` shape is what fixed both.

## The contract

- `DTC/<name>.dtc` at the miz **zip root**, pretty-printed JSON:
  `{"data": {…}, "name": <name>, "type": <unit type id>}`. The descriptor's own
  `data` table carries `name`/`type`/`terrain` members again — mirror that.
- Per-unit mission block:

  ```lua
  ["DTC"] = {
      ["Cartridges"] = { [1] = { ["default"] = true, ["name"] = "<name>" } },
      ["AutoLoad"] = true,
  },
  ```

- The cartridge **name is the file name** (manager: `ExportToJSON(tempMissionPath
  .. "DTC/" .. name .. ".dtc")`) — keep it filesystem-safe; units reference it by
  string. Multiple cartridges per unit are legal (one `default`); we emit one.
- No mission-level registry exists — the unit refs + files are the whole contract.
- **Terrain gating:** the ME import drops WYPT/TCN sections whose `terrain` ≠
  `getCurrentTerrainID()`. Emit `game.theater.terrain.name` (the same string
  pydcs writes to the miz `theatre` entry).

## Units & conventions (empirically confirmed)

| Thing | Value |
| --- | --- |
| ETA / TOS | seconds since **Zulu** midnight of the mission day — NOT the local mission clock. See the ETA correction below; the original reading of this row was wrong and shipped wrong for a year. |
| Altitudes | meters (4572.000000018288 = exactly 15,000 ft) |
| Speeds | **km/h** (the ME's unknown-leg default is 463.0 = 250 kt) |
| Coordinates | mission-internal terrain XY (x = north, y = east) |
| Hornet MEZ ring radius | **NM** (`detectionRange / 1852` in the editor) |
| Viper THREAT_PTS radius | **meters** |
| Comm channel names (Hornet) | ≤5 chars, uppercase alphanumeric (the ME import filter `custom_input_filter_*`); Viper channels have **no** name field, and use `freq` not `frequency` |
| Modulation enums | Hornet defaults 0 except CUE/MAR (1); Viper defaults 1 throughout — mirror the per-jet defaults files, don't reason about AM/FM |
| Empty sections | serialize as `[]` (Lua empty table), not `{}` |

## Editor-mined limits

Hornet: 59 waypoints (`MAX_WAYPOINT_NUM`), 3 route sequences, 9 CAP points, 7
corridors × 14 points, 3 FAOR + 3 FLOT lines × 7 points, 40 MEZ threats, COMM
channels 1–20 + `Channel_G/M/C/S` + `Guard` bool. Viper: **25** steerpoints (the
DTC editor's cap, not the jet's 699), 4 GEO line sets (L1–L4 flags on each
point), 15 THREAT_PTS, 20+20 COMM channels.

## Element shapes (constructor-exact)

- **`alt` on a point is the GROUND under it, not the height you fly it at.** Both
  jets, and it is the single easiest field to get wrong. ED's own editors fill it
  from terrain — `alt = getAltitude(mapX, mapY)` in the Viper's
  `CoreMods/aircraft/F-16C/DTC/MPD/NAV_PTS.lua` and the Hornet's
  `FA-18C/DTC/WYPT/WYPT_NAV.lua` — and the Viper's loader defaults a missing one to
  **2000 m** (`F-16C_50_DTC.lua:791`), so it must be written and it must be an
  elevation. The height to fly is a separate field: `routeAltitude` on the Viper's
  point, `NAV_ROUTE[].alt` on the Hornet's. `altitudeType` (1 = MSL, 2 = AGL)
  qualifies **that** one — its combo box lives on NAV_Routes
  (`NAV_Routes.lua:508`), and the Hornet resolves AGL as
  `tmpAlt + getAltitude(x, y)` (`ROUTE_SEQ.lua:50-54`).
- **Hornet NAV_PTS**: `{wypt_num, id "STPT<n>", text_note, note, x, y, alt,
  altitudeType (1 MSL / 2 AGL), velocityType 3, R1/R2/R3, R<n>_order, +
  offset-aimpoint boilerplate (isOA false, idOA "OA<n>"…)}`; route data lives in
  `NAV_ROUTE = [ {"STPT<n>": {route_num, wypt_num, alt, altitudeType, speed, ETA,
  FIX_Time, TGT}}, [], [] ]`.
- **Viper NAV_PTS**: route timing inline on the point (`TOS`, `isTOSEnabled`,
  `speed`, `FIX_Time`, `routeAltitude`); the name rides `note`; OAP_1/OAP_2
  boilerplate.
- **NAV_SETTINGS** (Hornet): `TACAN {Mode (1=T/R, 2=RCV, 3=A/A), Channel,
  ChannelMode (1=X, 2=Y), OnOff}`, `ICLS {Channel 1–20, OnOff}`, `ACLS
  {Frequency 225–399.975, OnOff}`, `AA_Waypoint`, `Home_Waypoint {FPAS_HOME_WP}`,
  `Altitude_Warning {Warn_Alt_Rdr, Warn_Alt_Baro}` (feet).
- **CAP_PTS**: `{id "CAP_PTS_<n>", num, x, y, course (deg, 0=N), length (m,
  default 10 NM), diameter (m, default 5 NM), turn_direction "Left"/"Right",
  note}` — a real racetrack drawn on the SA page. We use it for CAP stations
  *and* tanker/AEW&C orbits (note = short callsign).
- **CORRIDORS**: `{id "CORR_<n>", num, note, points [{id "CORR_<n>_PT_<i>", x,
  y}]}` — 10 NM lane; unused in v1.
- **FAOR_FLOT**: `{FAOR: [...], FLOT: [...]}`, each line `{id "FLOT_<n>", num,
  note, points [{id "FLOT_<n>_PT_<i>", x, y}]}`. **The `Default_*` style indices
  are load-bearing**: the editor inits them to the NONE index (CAP 10, CORR 8,
  FAOR/FLOT 4, MEZ 4) and elements render with that class style — emit **1** for
  every class we populate or the elements may not draw.
- **MEZ_THRTS**: `{id "MEZ_THRTS_<n>", num, x, y, text (≤3 chars), threat_type
  (a name from `MEZ_THRTS_defs` — or **"Custom"**, the only type with a free
  radius), threat_ring_radius (NM), threat_level 1}`.
- **Viper GEO_LINES**: flat point list `{number (global 1..N), id
  "GEO_LINES<30+n>", x, y, alt, L1..L4 bools (set membership), note}` —
  consecutive numbers in one set connect as a polyline.
- **Viper THREAT_PTS**: `{number, id "THREAT_PTS<55+n>", x, y, threatName
  ("Custom"), radius (m), alt, elev, text, ring true, def_num 1}`.
- **Viper DEST**: `{number, id "DEST<80+n>", x, y, alt (m MSL, the field
  elevation), text (<=3 alphanumerics, the HSD label), note}` — editor cap 19,
  so ids run DEST81..DEST99.

## Design decisions

- **Per-flight cartridges** (vs the reference mission's per-type): each flight
  flies its own route; the comm plan + SA picture repeat across a package's
  cartridges. Names: `Retribution <callsign> <type id>` (+ ` 2` on collision).
- **Mirror, never re-plan, the comm channels**: the DTC's channel numbers must
  match the unit `Radio` table the allocator wrote (the kneeboard prints those) —
  the DTC only *names* them. Unassigned channels keep module defaults.
- **STPT n == kneeboard waypoint n** (flown 2026-07-19: the jet read Takeoff as
  WP 1, shifting every briefed number by one): the kneeboard numbers the plan
  from 0, so the cartridge does **not** emit row 0 (takeoff/spawn — the jet's
  native WYPT 0 is where it spawns anyway) and numbers from 1. Both jets.
- **Recon-fog discipline**: threat rings filter through
  `tgo.known_for(flight.friendly)` (the threat-intel kneeboard's own leaf) +
  never `map_hidden`. Verified: Red Tide turn 1 → 0 rings; the flown turn-2 save
  → exactly the 5 TARPS-confirmed sites of 34. Generation runs inside
  `fogofwar.fog_intact()` (flown 2026-07-19 leak: the §18 reveal overview shorts
  `known_for` to truth for ANY viewer, and a DM generating with it ticked baked
  40 exact rings into a cartridge on an unscouted turn — the same latent leak
  existed for the threat-intel kneeboard). Any future generation-time consumer
  of fog-gated intel is covered by that wrapper; never read the fog leaves for
  a shared artifact outside it. That is data discipline, not what the pilot
  sees — the Hornet draws MERAD rings natively; see the manual cross-check.
- **The Hornet SA budget is priority-then-completeness**: support orbits →
  one racetrack per station (`dedupe_stations`) → leftover §6 wave tracks fill
  the remaining slots up to the hard nine. Never leave slots empty while real
  orbits were dropped — and never let wave duplicates squeeze the tankers out.
  (The Viper has no orbit element; its anchors stay one steerpoint per
  station.)
- **The jet DISPLAYS one CAP point — the selected one** (flown 2026-07-19: a
  7-entry cartridge drew exactly the `Default_CAP_Point` orbit). The CAP_PTS
  list is a flip-through library, so the pre-selected default is per flight
  (own station for a CAP flight, first tanker otherwise), and the
  see-everything-at-once picture lives on the §45 F10 drawings, which now
  paint the deduped CAP stations too.
- **Blue client flights only** — AI don't read cartridges; red clients don't
  exist in this squadron's use.
- **Best-effort everywhere**: per-flight failures skip the flight; pass-level
  failures leave the pre-feature miz. The feature must never block Take off.
- **Planner controls are per-flight, not more settings** (the "planners need
  more control" ask): `Flight.dtc_options` (`game/ato/dtcoptions.py`, pickled,
  setstate-defaulted) carries a tri-state enable + six section switches, edited
  on the Edit Flight **DTC tab** and threaded `Flight → FlightData →
  DtcGenerator`. An off section is **omitted** (never emitted empty) so the
  jet's own defaults stand — comms off must leave a pilot's hand-set presets
  alone, which emitting a defaults table would clobber.
- **TCN stations list deferred**: needs TACAN channel→paired-frequency data; the
  boat already auto-tunes via NAV_SETTINGS, which is the payoff.
- **Hornet ALR-67 CMDS/RWR + Viper CMDS/ELINT deferred**: the jets' own defaults
  are sane. A curated program table no longer needs hand-authoring — ED ships
  one (see the manual cross-check).

## Orbits and destinations — the 2026-08-22 rule

**Only the flight's own orbit is drawn, then the tankers and AWACS.** The Hornet SA
page displays one CAP point at a time (the selected one), so the list is a library
to flip through, and other flights' BARCAP stations were clutter the pilot never
asked for. Entry 1 is now the flight's own racetrack when it flies one (BARCAP,
TARCAP, tanker, AEW&C) — or, for a flight with no true orbit, a stand-in at its
**hold point** (the `LOITER` waypoint, else `JOIN`), so every jet gets a track
rather than none. The tanker and AEW&C orbits follow. `own_orbit_track()` in
`common.py` is the one implementation; the Viper's anchor steerpoints and the
Tomcat's reference points take the same list. `Default_CAP_Point` is always 1.

**The Viper's DEST page carries the enemy field the flight is working over.** The
HSD is where the crew wants the field they are attacking or fighting above, and
only the DEST partition draws an airfield. A red, non-naval control point within
10 NM of the target earns the slot right after the briefed divert, so the 19-slot
cap can never squeeze it out. Not a recovery option — it is kept out of the divert
slot on purpose.

## pydcs seams (fork-side until upstream lands)

pydcs (pin `dcs-retribution/pydcs@b0fc06a`) knows neither piece; neither does
root pydcs (checked 2026-07-19). Fork-side seams in
`game/missiongenerator/dtc/cartridge.py`:

1. `install_flying_unit_dtc_serialization()` — one idempotent wrap of
   `FlyingUnit.dict` emitting `d["DTC"]` for units carrying the
   `retribution_dtc` attribute. Byte-identical for every other unit.
2. `append_cartridges_to_miz()` — plain zip append of the `DTC/*.dtc` entries
   after `Mission.save` (runs before the §66 archive copy, so archives carry the
   cartridges).

The clean first-class version (unit attrs + `load_from_dict` round-trip + a
`Mission`-level cartridge dict written/read in save/load) is PR'd to
`dcs-retribution/pydcs`; when merged and the pin moves, delete the seams here.

## Open items

- **B28 in-game pass** — the one genuine unknown is AutoLoad on the §64 spawn
  paths (uncontrolled-at-t=0 carrier clients, late-activated delayed flights);
  the reference mission's jets were plain ramp starts. Also eyeball: SA-page
  FLOT/CAP/MEZ rendering, COMM names on the DDI/UFC, Viper DED steerpoint notes.
- **B91 in-game pass** — the F-14B(U), whose first step is an ME import and needs
  no sortie.
- ~~CH-47F / MiG-29 builders~~ — **dead, 2026-08-22.** The Chinook sets
  `DTC = false` and the Fulcrum is an AI-only module with no cockpit; neither can
  read a cartridge. See the capability table at the top of this note.
- **`ELINT` on the Viper** — the authored F-16C cartridge in the same package
  carries a top-level `ELINT.RWR` table: per-emitter `PRI` (priority), `search`,
  `display` and `unknown` flags, three bands. We emit none of it. A campaign-aware
  version would rank the emitters the mission actually fields, which is real data
  rather than invented values — the first honest v2 candidate. Nothing built.
- v2 candidates: TCN stations, ALR-67/CMDS program tables, corridors for transit
  lanes.

---

## Cross-check against the ED flight manuals (2026-08-18)

Sources: the F-16C and FA-18C Early Access Guides in `references/manuals/`, read
against the live descriptors in `E:\DCS World\CoreMods\aircraft\*\DTC`. Page
numbers are physical PDF pages.

### The Hornet draws enemy SAM rings without the cartridge

FA-18C guide p205: an air defence unit "placed in the mission, and not to be
hidden" appears on the SA page at its true position, ringed at its engagement
range. No detection required; the cartridge is not involved.
`Game._reveal_merad_groups` forces `hide_on_mfd = False` on every MERAD, so
those rings are always on for a Hornet client.

What this means for §74: the `MEZ_THRTS` fog gating is right as data discipline
but does not control what the pilot sees. An unscouted MERAD site is on the SA
page anyway. §74's rings add the SHORAD/LORAD picture the jet omits, plus a
redundant copy of the MERAD ones. Do not cite §74 as what keeps unscouted sites
off the display — §7's `hide_on_mfd` is, and it exempts MERAD on purpose.

### Viper: auto-sequencing stops at STPT 20

F-16C guide p223: with sequencing set to AUTO, "automatic sequencing will only
be performed from steerpoints 1-20". The nav partition itself runs to 25.
`MAX_ROUTE_STEERPOINTS = 20` now caps the flown route; support anchors fill
21-25. A longer route loses its tail rather than shipping steerpoints the jet
will not advance to.

### Viper: the MPD upload can write CMDS

F-16C guide p126, on the MPD partition: "The CMDS MODE knob must be set to the
STBY position on the CMDS control panel prior to uploading the MPD file
partition to prevent erroneous data entry into the CMDS settings." The
descriptor confirms `data.MPD.CMDS` is a real section.

§74 emits steerpoints, which live in MPD, and `AutoLoad = true` fires with no
pilot action — nothing can set STBY first. We emit no CMDS content, so there
may be nothing to write, but that is an assumption. The DTE format's advisory
messages are the observable. Checklist **B28** carries the check.

### Viper: partition boundaries, confirmed exactly

| Partition | Steerpoints | §74 |
| --- | --- | --- |
| Navigation | 1–25 | `STPT<n>`; route capped at 20, anchors 21–25 |
| Ownship markpoints | 26–30 | not emitted |
| Geographic lines | 31–55 | `GEO_LINES{30+n}`, capped at 25 |
| Pre-planned threats | 56–70 | `THREAT_PTS{55+n}`, capped at 15 |
| Destinations | 81–99 | not emitted |
| Datalink markpoints | 500+ | not emitted |

The id arithmetic already matched. The missing piece was a **total** GEO_LINES
cap: 4 sets × 8 points allowed 32, whose ids reach `GEO_LINES62` — inside the
threat partition. `flot_segments` yields 2 points per front, so 8 was the real
maximum and nothing shipped wrong; the guard protects the corridor work in Open
items. The editor's own refusal is `#data.MPD.GEO_LINES > 24`.

### Viper: steerpoints have sub-types

F-16C guide p202: a navigation steerpoint draws as a circle, an IP as a square,
a target as a triangle. `NAV_PTS_Types` accepts `STPT` / `IP` / `TGT` and keeps
the `STPT<n>` id prefix regardless of sub-type. §74 emitted `STPT` for
everything; it now marks target waypoints `TGT` and ingress waypoints `IP`. The
old "the Viper marks targets via the route, not a point flag" comment was wrong.

### ETA / TOS were local; the cartridge clock is Zulu (2026-08-19)

**The bug §74 shipped with, reported from the cockpit and confirmed three ways.**

The ME's own DTC manager states the base outright
(`MissionEditor/modules/me_managerDTC.lua`):

```lua
function getTime()
    return Mission.mission.start_time - (Terrain.GetTerrainConfig('SummerTimeDelta') * 3600)
end
```

Mission time is theater-local; the cartridge's clock is that minus the map's
UTC offset. Both jets agree:

- **Hornet** — "Based on a Time on Target, or TOT, using **Zulu time**" and
  "enter the hour:minute:second for the TOT based on Zulu time" (guide p123).
- **Viper** — the CRUS TOS page shows the desired TOS beside **System Time**
  (p107), and System Time "displays the internal system time in a 24-hour time
  format based on **Zulu time (UTC)**" (p103, p115). The required-ground-speed
  readout is TOS minus System Time, so TOS is Zulu.

`seconds_of_day` emitted raw local seconds-of-day, so **every ETA and TOS in
every cartridge was out by the map's offset** — 4 hours on Caucasus, Syria +3,
Marianas +10, Nevada −8. It now converts through `game.theater.timezone`, whose
per-theater values mirror DCS's `SummerTimeDelta`.

The base stays the mission day's Zulu midnight rather than the wall clock's, so
a sortie crossing 00:00Z hands the jet increasing times. The editor's TOS field
carries a days component for exactly that case.

**Why the original reading looked confirmed.** The evidence was a hand-built
mission where a human typed 07:19:13 into the ME's ETA boxes for an 07:00 local
start. That confirms the *encoding* (seconds since midnight) and says nothing
about the reference — the human typed local into a field the jet reads as Zulu,
which is the same mistake in a different chair.

### The Viper kneeboard now reads Zulu too (2026-08-19)

Fixing the cartridge exposed a second half of the same problem. The Hornet
family's kneeboards already printed Zulu (`utc_kneeboard: true` on the FA-18C/E/F
and EA-18G yamls), so those cards and the corrected cartridge agree. The **Viper
had no flag**, so its card printed local while its avionics ran Zulu — card and
DED an offset apart.

`F-16C_50.yaml` now sets `utc_kneeboard: true`, sourced to the guide's System
Time definition (p103).

### "The flag already drives every kneeboard time" was wrong (fixed 2026-08-20)

That sentence shipped in the 08-19 change and in the features doc. The flag drove
the BLUF's TOT and the friendly-packages page. It did **not** drive the
flight-plan table, the Support Info package TOT, or the AWACS/tanker station
times, so one Viper card carried two clocks four hours apart. Flown 2026-08-20 on
the Persian Gulf (+4): the DED read 10:38:37 under a BLUF of `TOT 11:12:14Z` over
a flight-plan row reading 15:12:14 for that same TOT.

The conversion looked plumbed because it was: `KneeboardGenerator` converted the
mission start time and passed it to `BriefingPage`/`SupportPage` as `start_time`.
Both stored it and neither used it — `FlightPlanBuilder` takes `start_time` and
prints `waypoint.tot` / `waypoint.departure_time` raw, and `SupportPage.start_time`
was read by nothing at all. A dead parameter that looks load-bearing is what made
the claim believable. The parameter is now deleted from all three.

### Both clocks, not one (the shape, and why)

The first fix converted the card to Zulu outright. That is the wrong shape for
this squadron, and upstream said so first: on #949 Starfire13 pointed out that a
squadron flying multiple types coordinates off the **standard kneeboard time**,
not Zulu, so a Zulu-only Viper card stops matching its A-10 and F-15E wingmen.

So a Zulu airframe's card now carries **both**:

- **The flight plan's Time column** carries the pair on one line, both figures
  labelled and local first: `17:28L 14:28Z`. Three constraints produced that shape.
  Stacking was tried first and flown 2026-08-21 — doubling nine waypoint rows
  pushed the Laser Code table off the bottom of the page. **Thirteen characters is
  the budget**, measured against `KneeboardPageWriter._fit_col_widths`: the fitter
  rebalances columns to the page width, so adding characters moves the wrap rather
  than removing it, and `17:28:52L 1428Z` at 15 brings the second line straight
  back. And the local figure carries an **`L`** because marking only the Zulu one
  made it read as the authoritative time, which is backwards — the wing
  coordinates on local, which is why both times are on the card at all.
- **The Departure column carries local only, labelled.** The pair here takes the
  Time column's last character back and wraps both. It holds one row on a typical
  plan and the offset is on every Time cell beside it, so the `L` is all it needs.
- **Seconds live in prose.** The BLUF's TOT and the Support Info line keep
  `17:53:16 (14:53:16Z)`; they are not under width pressure. An airframe that does
  not ask for Zulu keeps its seconds in the table too, and gets no `L`.
- **The friendly-packages timing cell** still stacks: its cell holds a patrol
  window as often as a single TOT, and `a - b (aZ - bZ)` is 31 characters.
- **Prose** — the BLUF's TOT and the Support Info package FREQ/TOT line —
  parenthesises it: `15:12:14 (11:12:14Z)`.
- **The AWACS/tanker `TOT:`/`TOS:` cells** stack it *indented under the time*.
  That column is the narrowest place a time appears; parenthesised, the tanker
  cell wrapped to `TOT: 14:12:09` / `(10:12:09Z) TOS:` / `1:00:00` and lost the
  pairing. The indent is what keeps the Zulu figure reading as the TOT rather
  than as the TOS below it. Caught by rendering the page, not in a sortie.

`format_kneeboard_time` (stacked) and `format_kneeboard_time_inline` share one
`_zulu_text` helper, and every page takes a `zulu_tz` that is the theater
timezone for a Zulu airframe and None for every other. Elapsed time still
subtracts the naive values, so GSPD and on-station dwell are unchanged. Pinned by
`tests/missiongenerator/test_kneeboard_zulu_times.py`.

The **cartridge stays Zulu-only** — it is typed into avionics, not read by a
wingman, so there is nothing for a second figure to serve.

**Still untouched:** the other client airframes were not audited. Each needs its
own manual check before its flag is set.

### `alt` and the leg altitude were the same number (fixed 2026-08-20)

Reported from the cockpit: the DEAD steerpoint does not sit at 0 AGL, it sits at
**0 MSL**.

`client_altitude()` returned one number and both jets wrote it into the point's `alt`
*and* into the route entry. Two consequences, and the second is the wider one:

- A **target** got `alt = 0`, so its ground read as sea level. On high terrain the
  steerpoint ends up under the map, with nothing there to slave a pod to.
- **Every ordinary waypoint** got `alt = ` its cruise altitude, so the jet was told
  the ground under an 18,000 ft nav point is at 18,000 ft. That was on every card
  since §74 shipped.

Split into `steerpoint_elevation()` (the point's ground) and `leg_altitude()` (what
to fly, with `altitudeType`). Only takeoff and landing know their own ground — B79
plans the field's elevation onto them.

**Everything else takes the nearest airfield's elevation (2026-08-22, DM call).**
A generated Viper cartridge showed every steerpoint but the landing at 0, and the
only height data the campaign carries is the per-airfield OSM/DEM elevation the
kneeboard already uses for QFE (`field_elevation_for_airport`). So
`nearest_field_elevation()` picks the closest airfield *with a record* — boats and
FOBs have none and never answer, so a coastal target is not pulled to sea level
by the carrier — and returns 0 only when no field on the map has one. Exact on a
flat map, within the field's valley elsewhere, closer than 0 everywhere. Fork-only:
upstream has no airfield elevation data, so the held carve keeps 0.

**Still an estimate.** The exact route, if a pod slaved to a hilltop target still
aims short, is a DCS-side dump: the GUI-environment `Terrain.GetHeight(x, y)` the
mission editor itself uses, sampled on a grid per terrain the way the pydcs export
is run — not the SRTM-sampled table that was built and reverted on 2026-08-20.
Checklist B90.

### The DED reads `routeAltitude`, and nothing honours the AGL tag (2026-08-22)

The nearest-field fix above landed in `alt`, and the DM's next Viper still read
**ELEV 0 on the DED** for the DEAD steerpoint. The ME's NAV PTS panel shows `alt`
("Elevation ft MSL"; "Terrain ft" is computed live from the map and never stored),
but **the jet's steerpoint ELEV is `routeAltitude`** — the same number the Routes
panel edits. We were writing the ground-marked target as `routeAltitude = 0,
altitudeType = 2`, mirroring the miz route's "0 AGL", and the jet showed exactly
that: 0.

`altitudeType` is decorative. In `MPD/NAV_Routes.lua` the editor's
`transformAltitude()` is `return val_3` — switching AGL/MSL changes the tag and
nothing else — and its own Mach calculation tests `route.alt_type`, a key that
does not exist, so even the editor never adds terrain to an AGL value. So every
altitude is now written **MSL with `altitudeType = 1`**: a ground-marked point's
altitude is the ground estimate itself, and an AGL-planned leg (low-level and
helicopter profiles) is converted with the same estimate. The .miz route keeps its
own 0 AGL, which DCS does resolve.

**The .miz was never wrong.** Read out of a flown mission:
`DEAD on KATYDID` is `alt = 0, alt_type = "RADIO"`, which is DCS's own encoding for
0 AGL. Upstream has no DTC at all, so this whole class of defect is fork-only.

### The Hornet half: the guide has no DTC chapter

Term census over all 424 pages: **FLOT, FAOR, corridor, MEZ, CAP point and DTC
all return zero hits.** Unlike the Viper, whose guide documents the DTE format on
p126-127, the Hornet guide never mentions the cartridge. It cannot validate the
SA half of the Hornet cartridge at all — the descriptor is the only source there.
What it does validate is the cockpit behaviour behind each section.

**One change came out of it.** p158: "The A/A waypoint must coincide with a
waypoint within the waypoint database", and designating it costs the pilot three
presses (HSI -> DATA -> A/A WP) every sortie. §74 hardcoded
`AA_WP_Number: 59, AA_WP_Enabled: False` — the jet's stock bullseye slot, which
our routes never reach, switched off. It now points at the bullseye we already
emit (the kneeboard's `REFERENCE_WAYPOINT_TYPES` puts divert and bullseye after
landing, so both faces agree on its number) and enables it. No bullseye in the
plan leaves the stock 59/off rather than designating empty space. Descriptor
range is 1-59 (`NAV_SETTINGS_defs.lua`), so any emitted number is legal.

**Confirmed against the guide and `NAV_SETTINGS_defs.lua`, no change:** the 59
waypoint cap (`WAYPOINT_MAX`) · three route sequences (p119, "The F/A-18C can
store three sequences") · the TGT flag living on the route entry rather than the
point (p119, WPDSG) · ICLS 1-20, ACLS 225.000-399.975, TACAN 1-126 X/Y · the
500/2000 ft altitude warnings inside the 5000/25000 ft caps · 20 comm presets per
radio plus G/M/C/S (p153-155).

**Two things worth knowing, neither actionable:** comm channel **C (cue) is
marked "(N/I)"** in the guide — we emit it mirroring the module defaults, and it
will never do anything. And **ACLS is documented in the Supercarrier guide, not
the Hornet guide**, which is why a search of the airframe manual comes back
empty.

**Checked, already covered:** the yardstick section (p138) warns off TACAN
channels 68 and 69 for datalink conflict. `UNAVAILABLE[TacanUsage.AirToAir]`
already excludes 64-99 on both bands.

### Confirmed correct — no change

- **STPT numbering.** F-16C guide p224: ME waypoint 0 is the group's initial
  position, and each waypoint after it becomes STPT 1, 2, 3 in Nav Route 1. The
  flown 2026-07-19 off-by-one fix puts the cartridge on the jet's own native
  numbering, so a failed AutoLoad degrades to the same numbers, not different
  ones.
- **Ground-marked steerpoint altitude.** p224 advises ground level for any
  steerpoint used to mark a location or cue sensors. `client_altitude` already
  returns 0 AGL for `GROUND_MARKED_WAYPOINTS`.

### New v2 material

- **`MPD.DEST` (steerpoints 81–99) — BUILT 2026-08-18.** Friendly recovery
  fields as Destination steerpoints: red-held and non-operational fields drop
  out, the briefed divert leads, and the rest sort by distance from the target
  so the nearest alternates take the 19 slots. Labels are three uppercase
  alphanumerics with a collision suffix that stays inside three. Own section
  switch (`destinations`) on the Edit Flight DTC tab, default on. Viper only —
  the Hornet descriptor has no equivalent section.
- **`MPD.CMDS` — INVESTIGATED, NOT BUILT (2026-08-18).** See the decision below.
- **`MPD.VIPVRP`** exists; nothing in the planner produces VIP/VRP offsets.
- The Hornet's `DTC/` folder now carries `DL/` and `IFF/` directories, but
  `MAIN_panels` is still the same eight and `data` has no key for either.
  Dormant, not usable. Re-check after a DCS patch.

---
### Decision: no CMDS section (2026-08-18)

`CMDS_defs.lua` looked like a shipped threat->countermeasure-program table worth
mining. It is not usable as one, on three counts:

1. **It is a defaults file, not intelligence.** The `CMDSPrograms.Air/Ground/
   Naval/Other` tables are what every Viper already has. Emitting them
   reproduces the jet's own state. Making them campaign-aware means inventing
   program and threshold values, which is the unsourced-number failure mode.
2. **Emitting it clobbers the pilot.** `CMDSProgramSettings` carries the burst
   and salvo counts for MAN1-6 / AUTO1-3. An AutoLoaded cartridge would write
   them over anything the pilot hand-set — exactly what the "an off section is
   omitted, never emitted empty" rule above exists to prevent for comms.
3. **The two sources disagree on the shape.** The live descriptor declares
   `data.MPD.CMDS`; ED's own three shipped example cartridges
   (`F-16C/DTC/defaults/test*.json`) are CMDS-only with the section at
   **`data.CMDS`**, carrying `CMDSBingoSettings` + a `MAN1`-only
   `CMDSProgramSettings` and no threat table at all. §74's method is to mine a
   shape from a working artifact and cross-check it against the editor; here the
   two disagree, so there is no confirmed shape to emit.

On top of all three, the guide's STBY warning (above) makes an AutoLoaded CMDS
write the one thing already flagged as risky and unverified in the cockpit.

If CMDS is wanted later, the honest first step is a flown check of what an
AutoLoaded MPD partition already does to the CMDS page — checklist **B28** — not
more mining.

---

## CJS Super Hornets — REMOVED 2026-08-22

FA-18E/F and EA-18G took a cartridge from 2026-08-02 to 2026-08-22. The mod's
descriptors (`<mod>/Core Module/DTC/{FA-18E,FA-18F,EA-18G}_DTC.lua`) are thin
wrappers that `dofile` ED's FA-18C `COMM`, `WYPT`, `ALR67` and `TCN`
implementations and declare **no `SA` table** — no FLOT, no racetracks, no threat
rings. So the cartridge could only carry the comm presets and the route, and the
audit below shows both already reach every jet through the miz. Double work for
no cockpit gain; removed on the DM's call.

The builder and its tests are in git history
(`git show c67783176:game/missiongenerator/dtc/superhornet.py`). **A re-add must
re-mine the mod's descriptor first** — CJS can change it between releases, and
it already carried one stale `dofile` (`TCN/TACAN_defs.lua`, gone from current
DCS). The `FA-18ET`/`FA-18FT` tanker variants never had a descriptor at all.

---

## What the miz already delivers — the double-work audit (2026-08-22)

Asked by the DM: how much of a cartridge duplicates what Retribution already
writes into the miz for every aircraft, and what is lost if the DTC layer is
ever switched off. Checked against the code that writes the miz, not against
the descriptors.

| Data | Reaches the jet without a cartridge? | What the cartridge adds |
|---|---|---|
| Radio presets on channels | **Yes** — upstream's channel allocator writes every client unit's `Radio` table (`FlightData.assign_channel` → `unit.set_radio_channel_preset`, driven by `game/radio/channels.py`) | Hornet: ≤5-char channel **names**. Viper: **nothing** — its schema has no name field, so `COMM` is a pure mirror |
| The route as steerpoints | **Yes** — the miz flight plan | Hornet: names, per-leg ETA/speed, the target flag. Viper: TOS and leg speed inline, TGT/IP sub-types. Tomcat: nothing (plan 1 is the ME route; plan 2 repeats it with TOTs) |
| Recovery TACAN / ICLS / ACLS | No | Hornet `NAV_SETTINGS` |
| A/A waypoint on the bullseye, FPAS home | No | Hornet `NAV_SETTINGS` |
| Own orbit, tanker/AWACS orbits | No (the F10 map has them; the cockpit does not) | Hornet `CAP_PTS`, Viper anchors 21–25, Tomcat references |
| Front line | No | Hornet `FAOR_FLOT`, Viper `GEO_LINES`, Tomcat plot lines |
| Confirmed SAM rings | Partly — the Hornet SA page draws MERAD sites natively (§7) | SHORAD/LORAD rings, and every ring on the Viper and Tomcat |
| Recovery fields + the target's field | No | Viper `DEST` |
| Pre-planned JDAM aimpoints | No | Tomcat `JDAM` |
| TIS send-to list | No | Tomcat `TIS` |

**Consequences.**

- **The cartridge is an overlay, never load-bearing.** With `dtc_data_cartridges`
  off — or the cartridge rejected by the jet — radios and route are exactly
  upstream's. That is the revert path, and it costs nothing to exercise.
- **The mirrors must stay mirrors.** The Hornet `COMM` section overwrites the
  whole channel table, so it has to carry the allocator's frequencies to add its
  names; emitting names alone would blank the presets. The same holds for the
  route sections. A disagreement between the miz and the cartridge is a bug in
  the cartridge.
- **The Viper `COMM` section was the one genuinely redundant piece** — identical
  to the unit's `Radio` table, key for key. **Dropped 2026-08-22 on the DM's call.**
  The Viper's presets come from the miz; `viper.py` emits no `COMM` at all, and the
  tab's comms switch is documented as Hornet-only (on the Tomcat it carries TIS).
  If a future Viper schema ever adds channel names, re-add the section as a mirror
  plus names, the way the Hornet's works.
- This is also why the Super Hornets lost their cartridge: with no `SA`, the
  whole file was the first two rows of this table.

---

## F-14B(U) — the Tomcat schema (2026-08-22)

Mined from `CoreMods/aircraft/F14/DTC/F-14BU_DTC.lua` (138 KB) and its `.dlg`,
cross-read against the ME's DTC panel. Builder: `game/missiongenerator/dtc/tomcat.py`.

**Only the F-14B(U) reads a cartridge.** `F14/Entry/F-14B.lua` sets
`DTC = rewrite_settings.Name == "F-14BU"`, and the descriptor's `setData` refuses
anything whose `type` is not `"F-14BU"`. The plain F-14B and every F-14A have no
DTC at all. (This is also the mistake that reached the pydcs PR thread; see the
capability table at the top of this note.)

The `data` table is **not** the Hornet's shape:

```lua
data = {
    type = "F-14BU", name = "F-14BU DTC", cartridge_name = "DEFAULT",
    CMDS = {}, NAV = {}, JDAM = { stations = { {targets={}} x4 } }, TIS = {},
}
```

Two differences from every other jet §74 writes: there is **no `terrain` member**
(it carries `cartridge_name`, the label the CDNU shows, instead), and `setData`
only imports keys that already exist in that table — an extra key is dropped
silently rather than erroring.

### Plan 1 is the ME route — do not write waypoints into it

`data.NAV` is twelve flight plans, each
`{name, waypoints, lines, additional_points, route_as_line}`. **Plan 1 is the
mission's own route**: the editor prints "Plan 1 waypoints are defined by the ME
route planner" and `updateNAVPlanEditability()` greys out every waypoint field
there. Since Retribution's flight plan *is* that route, the cartridge writes no
waypoints at all — it fills the two things plan 1 accepts and a route cannot
express:

- `lines` — the front line, one line per active front (`flot_segments`).
- `additional_points` — bullseye, divert, the tanker/AEW&C and CAP anchors, and
  the recon-confirmed SAM sites.

Plan 1's `name` is left empty on purpose: the editor labels it "1: ME Route"
while it is, and naming it would hide that.

**Plan 2 is the flown route**, named `ROUTE 1` with `route_as_line = true`. That
is not a guess: the ED-authored cartridge checked against (below) does exactly
this, and its waypoints carry TOTs with `spd = 0` and names ending in the jet's
codes. The reference layer is repeated on plan 2 so selecting it loses nothing.

### Units and exclusivity — the two traps

| Field | Unit | Source |
|---|---|---|
| NAV waypoint / line point / additional point `elev` | **feet** | `wp.elev = metersToFeet(getAltitude(...))` |
| — and it is the point's **only** altitude field | | there is no `routeAltitude` twin here |
| JDAM target `elev` | **metres** | `tgt.elev = getAltitude(...)`, converted only for display |
| NAV waypoint `spd` | knots ground speed, 0 = unset | dlg tooltip, range 0-999 |
| NAV waypoint `tot` | `"HH:MM:SS"` text | dlg tooltip, "e.g. 08:30:00" |
| JDAM `drop_alt` / `drop_spd` | feet / knots | dlg spinboxes, 20000 / 450 default |

`spd` and `tot` are **mutually exclusive**: `updateSpdTOTEnabled()` disables each
when the other is set, so a waypoint carries one or neither.

**The single altitude field is why this jet breaks B90's rule.** The Hornet and
Viper each carry two numbers — the ground under the point and the height to fly
the leg — and §74 keeps them apart. The Tomcat has one, so it cannot. The editor
auto-fills terrain height, but the authored cartridge shows a human overwriting
that with the planned altitude on the two waypoints where it mattered (`20000` on
both IPs) and leaving the auto-filled terrain at the ends (`142`, `167`).
`_waypoint_elevation()` reproduces that: the field's own elevation where we know
it, the planned MSL leg altitude in between, and 0 on a ground-marked point
because that is where the miz puts it for a client. **Which one the CDNU actually
wants is the open question** — read it in the cockpit, checklist B91.

### Name codes — the jet types a point by its name

The NAV tab documents a suffix grammar, and it is the reason our reference points
are named the way they are:

```
X##  special point: FP, IP, HB, DP, HA, ST
XB / X##B  bullseye ref      XD / X##D  destination
XL / X##L  LANTIRN (max 20)
X#1-X#3  priority 1-3        X#4-X#7  generic
Example: OCEANAXHB = 'OCEANA' as Home Base
```

Names cap at **8 characters** (`NAV_WP_NAME_MAXLEN`, enforced on both waypoints
and additional points), so the base name is what gives way, never the code:
`_suffixed()` trims the base. The authored cartridge below uses the grammar in
anger — `IPORCXIP`, `IPBLUXFP`, `BULLSXB` — so it is real, not documentation of
an intention. We emit `XB` (bullseye), `XD` (divert), `XHB` (the recovery field),
`XIP` (every ingress waypoint type) and **`XST` on the first target waypoint in
route order**. A squadron tip (2026-08-22) supplied the two meanings the help text
never states: **`XST` is the surface target, which the HUD highlights with a
pentagon**, and `XB` on the bullseye puts its bearing and range on the HUD in A2A.
The bullseye is an additional point rather than a route waypoint — that is how the
authored cartridge carries it (`BULLSXB`), so the code is assumed to work there.
`XST` goes on one point only, the first target, which is also STA 3's PP1; whether
the jet honours a second is unknown. `DP`, `HA` and `FP` still have no stated
meaning, so nothing is guessed onto them.

### Editor-mined limits

12 plans · 50 waypoints · 4 lines of 9 points (8 if closed, the closing repeat
takes a slot) · plan names 16 chars · point names 8 chars ·
`NAV_MAX_TOTAL_REFS = 20`. That last one is **declared and never enforced** in
the descriptor (the import path allows 50); we honour the smaller number as the
authored intent.

### JDAM — four stations of eight, and the cached LAR

`data.JDAM.stations` is exactly 4 (`STA 3`-`STA 6`), each with 8 pre-planned
targets. An empty slot is `createJDAMTarget()`'s defaults with no coordinate keys
at all; the cartridge omits `x`/`y`/`lat`/`lon`/`launch_x`/`launch_y` rather than
writing zeroes.

The three `lar_*` scalars are the launch-acceptability numbers, **persisted so the
CDNU can read them without the C++ table**. `JDAM_LAR_TABLE` (6 altitudes x 9
Mach x 3 values) and its bilinear lookup are ported into `tomcat.py` as
`lookup_jdam_lar`, including the ISA speed-of-sound the descriptor uses to turn
knots into Mach. The ME's *import* recomputes them and ignores what the file
says; the jet does not, so they are written correctly.

**Each station that carries a JDAM gets its own target as PP1** (2026-08-22, on
a squadron question). The mission generator has already written every pylon into
the miz, so `jdam_stations()` reads the lead client's `unit.pylons` and matches the
CLSIDs against everything pydcs names a JDAM (racks included). The pylon-to-station
mapping is DCS's own: `F-14B.lua` defines the pylons in the order 1A, 1B, 2, 3, 4,
5, 6, 7, 8B, 8A, so **pydcs pylons 4–7 are the tunnel stations the jet labels 3–6**
— the descriptor's STA 3–6. Targets are handed out in route order across the
loaded stations, wrapping when there are more bombs than targets, so releasing
STA 3, 4, 5, 6 at PP1 walks the list with no cockpit selection. Every target stays
on every station behind it (PP2 onward, in order) and a station carrying anything
else gets the plain list, so the crew can always re-pick.

**Every target in a cluster runs in from the IP.** A strike plan gives each
building its own target waypoint a few hundred metres apart; measuring the second
bomb's run-in from the first target gave it a heading set by a 300 m hop, a
two-second leg for its speed and the ground as its release altitude. The reference
is the last non-target route waypoint before the cluster.

`attack_heading` is the run-in: the bearing from the IP to the target. `drop_alt`
is the IP leg's planned altitude (a target waypoint plans on the deck for players,
which is not a release altitude), falling back to the module's 20000 ft when
nothing usable is planned. **`drop_spd` is the slower of the plan's IP-to-target
leg speed and the module's 450 kt default** (DM call, 2026-08-22): the TOT-derived
number came out at 496 and 642 kt on a real save, and the LAR computed from it is
honest only if the crew flies that fast. Capped, the LAR the CDNU draws is the
conservative one — fly the run-in faster and the real envelope is only bigger.

### TIS

`use_mission_callsign` and `add_wingmen_to_list` stay true — the module already
unions the flight's own wingmen. `send_to_callsigns` gets the **package's other
flights**, each sanitized to 6 blank-padded characters exactly like
`sanitizeTISCallsign`. Anything shorter than 6 is padded; the import drops an
all-blank entry.

### CMDS is always written — the descriptor cannot take a partial cartridge

The first cut omitted `CMDS` on the Viper's reasoning. **The ME import of
2026-08-22 proved that wrong for this descriptor**, from `dcs.log`:

```
F-14BU_DTC.lua:455: attempt to index field 'CMDSProgramSettings' (a nil value)
  in function 'init_CMDS'  ←  in function 'setData' (3607)  ←  me_managerDTC.lua:442
```

`setData` resets `data.CMDS` to `{}`, overlays only the sections the file
carries, then ends with `init_CMDS(); init_JDAM(); refreshNAV(); refreshTIS()`.
`init_CMDS` reads `data.CMDS.CMDSProgramSettings.PROG_1` unconditionally, so a
missing `CMDS` kills the whole tail: the NAV grid still drew (the tab's own
`onShow` redraws it), but the JDAM grid stayed blank until a tab switch rebuilt
it and the cartridge-name box never left `DEFAULT`. The *data* had imported —
TARGETAR was on every station once the grid refreshed — only the refresh died.

So the Tomcat writes **all four sections, always**. A section the planner turned
off carries the editor's reset state (twelve empty plans; four stations of eight
default slots; the TIS defaults), and `CMDS` is **ED's stock table verbatim** —
`_CMDS_DEFAULTS` in `tomcat.py`, byte-equal to what the authored reference
cartridge carries, because that is what the editor saves for an untouched one.
Not a place for campaign values: `CMDSAutoOverrides` is a per-DCS-type table and
filling it from known threats would mean inventing program/threshold pairs.
The "omit when off" rule stays right for the Hornet and Viper, whose importers
tolerate a missing section; it is a per-descriptor fact, not a §74 principle.

### x/y is what the ME reads; lat/lon is derived

The DM loaded the Iraq-built test cartridge into a mission on another map and
the ME showed E 066° — Afghanistan — for every point: it recomputed lat/lon from
our `x`/`y` in the open mission's projection and ignored the `lat`/`lon` we
wrote. So the cartridge is **terrain-bound through `x`/`y`**, and unlike the
Hornet and Viper the Tomcat schema has no `terrain` field to say which. Load a
generated cartridge only into a mission on its own map. Whether the *jet* reads
`x`/`y` or `lat`/`lon` is still the B91 question.

### Checked against an authored cartridge (2026-08-22)

The F14 descriptor ships **no `defaults/` example** the way the Viper does
(`F-16C/DTC/defaults/test*.json`), so the shape was first mined from `setData`,
the element constructors and the editor panels. It was then **diffed against a
real hand-authored F-14B(U) cartridge** — the squadron's training-night package,
`DTC/F-14BU/02_29th_Demon-1_29th_Demon-1_OB.dtc`, 42 KB, built in the ME by a
person rather than by us.

Every section's key set matches:

| Compared | Result |
|---|---|
| top level, `data`, plan, route waypoint, line, line point, additional point, `JDAM`, station, target, `TIS` | key sets identical |
| an unused JDAM slot | **byte-identical**, including all three `lar_*` floats |
| `data.CMDS` | present in the reference; absent in ours, deliberately |

Two things that diff told us, and both changed the builder:

1. **The route belongs on plan 2.** The reference leaves plan 1 empty-named with
   zero waypoints — confirming the ME-route rule — and puts a five-waypoint
   `ROUTE 1` on plan 2 with `route_as_line = true`. That turned a deferred idea
   into the shipped behaviour.
2. **The name codes are in live use**, which is what promoted them from "the
   dialog documents a grammar" to "emit them".

The `lar_*` match is the strongest single result: our ported `JDAM_LAR_TABLE`
reproduces ED's cached defaults to the last digit
(`1.5712031862492397 / 7.250980621174471 / 44.98373439541641`), so the
interpolation and the ISA speed-of-sound came across correctly.

**The same package validated the other two builders for free.** It carries
authored cartridges for the F-16C and the FA-18C as well, and against those our
Viper's `NAV_PTS` + `COMM` and our Hornet's `WYPT` + `SA` + `COMM` key sets match
exactly. Each reference carries one section we deliberately skip — `MPD.CMDS` and
`ELINT` on the Viper, `ALR67` on the Hornet — and nothing else differs.

**And it corroborates the capability table.** Eight aircraft have kneeboards in
that package; exactly three have cartridges — `F-14BU`, `F-16C_50`,
`FA-18C_hornet`. The F-14B has kneeboards and no cartridge, which is the same
answer the DB flag gives.

**The reference's `CMDS` is stock defaults, field for field** — bingo 10/10/0/0,
the same five auto-program pairs, `PROG_1` Priority 2 with 2/0.2/8/1.0 chaff.
The author never touched the tab; the editor saved it anyway. That is the case
for omitting it: emitting the section writes ED's own numbers back and clobbers
anything the pilot set.

### What generating one from a real save caught (2026-08-22)

A cartridge built from the turn-2 Iraq autosave — a real route, real package,
real threats — showed two things no unit test would have:

1. **Names reached the file as Retribution writes them**: `Join - Point`,
   `Target area`, `Landing`. Every name in the authored cartridge is bare
   uppercase alphanumerics and the CDNU has no lower case, so `_point_name()`
   now runs them through `sanitize_short_name` — `JOINPUSH`, `TARGETAR`,
   `LANDXHB`.
2. **The ingress waypoint was being pre-planned as a JDAM aimpoint.**
   `is_target_waypoint()` is true for it, because Retribution hangs the target
   list on the ingress point so the task can be built. `_build_jdam` now filters
   on the waypoint *type* (`TARGET_POINT`, `TARGET_GROUP_LOC`, `TARGET_SHIP`)
   instead, which halved the planned points on a SEAD escort.

Generate one the same way when this changes: load the save, man a lead, point
`CARTRIDGE_BUILDERS` at the builder under test, `MissionSimulation.begin_simulation()`
then `MissionGenerator(...).generate_miz()`. The flight states have to be
initialized first or generation raises on an uninitialized flight.

**ME import, 2026-08-22 (B91 step 1):** NAV passed outright — plan 2 `ROUTE 1`
with eight waypoints and their TOTs, the front line as plot line 2 behind the
route, seven references with their `XB` names, elevations in feet. JDAM's data
imported. The only defect was the missing `CMDS`, above, fixed the same day.
**Re-import verified the same day**: cartridge name, JDAM grid on load, Iraq
coordinates on an Iraq mission, a clean `dcs.log` — ED's importer accepts our JSON
end to end. The cockpit is what remains.

In-game pass: checklist **B91**.
