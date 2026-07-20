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

## Design decisions

- **Per-flight cartridges** (vs the reference mission's per-type): each flight
  flies its own route; the comm plan + SA picture repeat across a package's
  cartridges. Names: `Retribution <callsign> <type id>` (+ ` 2` on collision).
- **Mirror, never re-plan, the comm channels**: the DTC's channel numbers must
  match the unit `Radio` table the allocator wrote (the kneeboard prints those) —
  the DTC only *names* them. Unassigned channels keep module defaults.
- **Recon-fog discipline**: threat rings filter through
  `tgo.known_for(flight.friendly)` (the threat-intel kneeboard's own leaf) +
  never `map_hidden`. Verified: Red Tide turn 1 → 0 rings; the flown turn-2 save
  → exactly the 5 TARPS-confirmed sites of 34. Generation runs inside
  `fogofwar.fog_intact()` (flown 2026-07-19 leak: the §18 reveal overview shorts
  `known_for` to truth for ANY viewer, and a DM generating with it ticked baked
  40 exact rings into a cartridge on an unscouted turn — the same latent leak
  existed for the threat-intel kneeboard). Any future generation-time consumer
  of fog-gated intel is covered by that wrapper; never read the fog leaves for
  a shared artifact outside it.
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
  are sane; a curated per-era program table is v2 material.

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
