# 414th — Flight Control (ATC) integration (design notes)

Goal: bring MOOSE **FLIGHTCONTROL** (v0.7.7, already in the vendored Moose.lua) online as
**players-only** ATC at friendly land airbases — immersive taxi/takeoff/landing
sequencing with SRS voice (text-subtitle fallback) — without letting it queue or strand
AI scrambles (QRA/CAP).

Plugin default: **ON** (414th choice). The Lua is not runnable in CI, so it still
warrants an in-game pass — chiefly confirming AI launches are unaffected.

---

## What's available and the hard constraints

`FLIGHTCONTROL` is in `resources/plugins/base/Moose.lua` (line ~92795), so no MOOSE
upgrade is needed. From its `New(AirbaseName, Frequency, Modulation, PathToSRS, Port)`:

- **AIRDROME only** — `New()` returns `nil` for FARPs and ships (it logs and bails). We
  still pre-filter to blue land airdromes on the Python side.
- It **builds MSRS in the constructor**: `path = PathToSRS or MSRS.path`. We pass `nil`
  so MOOSE auto-detects the server-side SRS install; with no SRS it degrades to text
  subtitles. Port is configurable (default 5002).
- It auto-adds a backup holding pattern (`_AddHoldingPatternBackup()`), so no per-base
  zone setup is required.
- It sets `SetTransmitOnlyWithPlayers(true)` by default.

## Players-only is pragmatic, not a hard switch

MOOSE FLIGHTCONTROL inherently *observes* AI flights at its airbase; there is no clean
"ignore AI entirely" flag. We approximate players-only by setting **generous** AI limits
so AI flow is effectively pass-through:

```
fc:SetLimitLanding(maxLanding, maxLanding)   -- default 99/99
fc:SetLimitTaxi(maxTaxi, false, maxLanding)  -- default 99
fc:SetTransmitOnlyWithPlayers(true)
fc:SetRadioOnlyIfPlayers(true)
```

**This is the primary in-game risk to validate:** confirm AI QRA/CAP launches from
FlightControl bases are unaffected. If AI ever gets queued/stranded, lower nothing —
raise the limits further or scope FlightControl to player-only bases.

## Wiring

- `flightcontrol_414_init.lua` reads the airbase list from
  `dcsRetribution.FlightControl.airbases` and its options from
  `dcsRetribution.plugins.flightcontrol.*` (plugin.json mnemonics: `subtitles`,
  `srsPort`, `maxLanding`, `maxTaxi`). It spins up one `FLIGHTCONTROL:New(...)` per
  airbase, each wrapped in `pcall` so one bad base can't abort the rest, then `:Start()`.
- `_inject_flightcontrol_script()` in `game/missiongenerator/luagenerator.py` (appended
  after `inject_plugins()`, gated on the plugin being enabled) emits the airbase list and
  loads the init script. The list is built by `_flightcontrol_airbase_entries()`:
  blue-held control points with `dcs_airport is not None`, each carrying its ATC
  frequency + modulation when `mission_data.runways` has it (the Lua falls back to a
  default frequency otherwise). Reuses the friendly-airbase pattern from
  `_inject_civilian_traffic_script()`.

## Known limitations / refinements
- Default ON; still warrants an in-game pass (chiefly the AI-launch check above).
- SRS voice requires a server-side SRS install (auto-detected); otherwise text-only.
- Per-base ATC frequency comes from `RunwayData.atc` where present; bases without runway
  data fall back to the Lua default. Mapping every airbase to its real DCS tower
  frequency is a possible refinement.
- "Lose control once AI taxi/land" is a documented MOOSE caveat; our generous limits keep
  it from acting on AI in the first place.
- Tests: `tests/test_flightcontrol_emit.py` (airbase-list selection + ATC freq). Lua is
  not runnable in CI.
