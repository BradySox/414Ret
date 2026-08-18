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
   DTC descriptors exist for **FA-18C_hornet, F-16C_50, CH-47Fbl1, MiG-29
   Fulcrum** — that set defines "DTC-capable" today.

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
| ETA / TOS | **absolute seconds since midnight** of the mission day (mission `start_time` 25200 = 07:00 ↔ first ETA 26353 = 07:19:13) |
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

- **Hornet NAV_PTS**: `{wypt_num, id "STPT<n>", text_note, note, x, y, alt,
  altitudeType (1 baro / 2 radio), velocityType 3, R1/R2/R3, R<n>_order, +
  offset-aimpoint boilerplate (isOA false, idOA "OA<n>"…)}`; route data lives in
  `NAV_ROUTE = [ {"STPT<n>": {route_num, wypt_num, alt, altitudeType, speed, ETA,
  FIX_Time, TGT}}, [], [] ]`.
- **Viper NAV_PTS**: route timing inline on the point (`TOS`, `isTOSEnabled`,
  `speed`, `FIX_Time`, `routeAltitude`); the name rides `note`; OAP_1/OAP_2
  boilerplate.
- **NAV_SETTINGS** (Hornet): `TACAN {Mode (1=T/R, 2=REC, 3=A/A), Channel,
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
- CH-47F / MiG-29 builders when a campaign fields them blue-client.
- v2 candidates: TCN stations, ALR-67/CMDS program tables, corridors for transit
  lanes, MEZ from the §40 restricted circles.

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

## CJS Super Hornets — FA-18E/F + EA-18G (2026-08-02)

The community CJS mod ships **native DTC descriptors of its own** at
`<mod>/Core Module/DTC/{FA-18E,FA-18F,EA-18G}_DTC.lua` (~21.6 KB each, all three
identical bar the `type`/`name`), so these airframes take a cartridge exactly like
the stock jets. Mined the same way as the ED descriptors above.

**They are thin wrappers around ED's Hornet DTC.** The load-time block `dofile`s
ED's *own* implementations:

```
CoreMods/aircraft/FA-18C/DTC/defs.lua
CoreMods/aircraft/FA-18C/DTC/COMM/{COMM_common,COMM1,COMM2}.lua
CoreMods/aircraft/FA-18C/DTC/WYPT/{WYPT_NAV,ROUTE_SEQ,NAV_SETTINGS}.lua
CoreMods/aircraft/FA-18C/DTC/ALR67/{CMDS,RWR}.lua
CoreMods/aircraft/FA-18C/DTC/TCN/TACAN.lua
```

So the **COMM and WYPT schemas are ED's, not CJS's** — which is why
`game/missiongenerator/dtc/superhornet.py` reuses the Hornet builder's emit verbatim
(`build_hornet_family_cartridge`, factored out of `hornet.py`) instead of
reimplementing. A test asserts both sections come out byte-identical to the Hornet's.

**What the descriptor does *not* have — the one real limitation.** The CJS `data`
table is:

```lua
data = { ALR67 = {CMDS, RWR}, COMM = {COMM1, COMM2, mirror_*},
         WYPT = {NAV_PTS, NAV_ROUTE, NAV_SETTINGS, terrain, mirror_NAV_PTS},
         TCN = {}, type = "FA-18F", name = "FA-18F", terrain = "" }
```

There is **no `SA` table and no `GPS_WYPT`**. Four independent confirmations, because
this is the one claim the whole `with_sa=False` decision rests on:

1. **The `data` table above is the complete table** — `ALR67`/`COMM`/`WYPT`/`TCN` plus
   `type`/`name`/`terrain`, nothing else.
2. **Token counts, CJS vs ED** (all three CJS descriptors + their `defs.lua`):
   `SA` **0** vs ED's 205 · `CAP_PTS` 0 vs 43 · `MEZ_THRTS` 0 vs 49 · `FAOR_FLOT` 0 vs 42.
3. **The panel list.** CJS declares five — `pWYPT`, `pRTE_SEQ`, `pTACAN`, `pCOMM`,
   `pALR67`. ED declares eight: the same five **plus `pSA`, `pGPS_WYPT`, `pHARM`**. The
   ME's DTC editor for a Super Hornet therefore has no SA tab at all.
4. **The `.dlg` carries a hollow `pSA` stub** — exactly one `pSA` reference (ED's has
   **196**), whose entire contents are a single static label reading `"Panel SA"`.

Read together: CJS forked an ED Hornet descriptor and **stripped SA out** (along with
GPS_WYPT and HARM), leaving an empty panel shell. Since the `.lua` never lists `pSA` in
`MAIN_panels` and `data` has no `SA` key, nothing populates or reads it.

🔎 **That stub is the tripwire.** If a future CJS release fills `pSA` in and adds the
`SA` table, flipping `with_sa=True` lights up the entire picture — FLOT, CAP racetracks,
threat rings — with **no other code change**. Re-check it after a mod update: grep the
descriptor for `SA` and compare the panel list against ED's.

The Super Hornet therefore gets the comm plan, steerpoints/route and the §65 recovery
aids, but **none of the SA picture** — no FLOT, no CAP/tanker racetracks, no enemy
threat rings. Implemented as
`with_sa=False`: the planner's three SA switches go inert rather than emitting a
table the module cannot parse. A flight with *only* SA sections enabled passes the
generator's `any_content` gate but yields nothing, so the builder returns `None`
(`CartridgeBuilder` is now `Optional`-returning) — an empty AutoLoading cartridge is
worse than no cartridge.

`FA-18ET`/`FA-18FT` (tanker variants) are deliberately unregistered: no descriptor
ships for them, so a cartridge would have nothing to load it.

### Drift risk — read before trusting this

Unlike the rest of §74, this targets a **mod** descriptor. Two consequences:

1. **A CJS release can change the schema.** Adding `SA` would be the welcome case
   (flip `with_sa=True` and the whole picture lights up); renaming or restructuring
   COMM/WYPT would silently produce a cartridge the jet rejects. Re-mine
   `<mod>/DTC/FA-18F_DTC.lua` after a mod update.
2. **The descriptor is already partly stale.** `initialize_TACAN()` `dofile`s
   `CoreMods/aircraft/FA-18C/DTC/TCN/TACAN_defs.lua`, which **no longer exists** in
   current DCS (ED's `TCN/` now holds only `TACAN.lua`). That call is lazy — it fires
   only when the ME DTC editor's TCN panel opens — and harmless to us because §74
   emits `"TCN": []`. But it is the same staleness that broke the mod's *cockpit*
   scripts and crashed the SA page (2026-08-02); treat mod-vs-current-DCS drift as
   the default assumption, not the exception.

In-game pass: checklist **B28**, CJS bullet.
