# ATMOS-X live weather

Adopted from upstream [dcs-retribution#927](https://github.com/dcs-retribution/dcs-retribution/pull/927),
second commit (`49e619203`, 2026-08-19). The first commit of that PR — the selectable
cloud preset pack — was adopted separately on 2026-08-03 as fork #773.

Status: **built 2026-08-19, never flown.** In-game pass row **B83**.

**Probed against the real CLI 2026-08-19**, outside DCS, on the installed ATMOS-X
(`C:\Program Files\ATMOS-X`). Everything below the mission itself is confirmed working:
`detect_cli()` found the install through the registry; `atmosx-cli metar LCLK --save` returned
`METAR LCLK 192130Z 31003KT CAVOK 26/23 Q1011`; the parser read the real file (not the trimmed
fixture); QNH converted 758 mmHg -> 29.84 inHg against the METAR's Q1011 (29.85); the station
picker resolved 60 Syria stations and 17 Caucasus, matched `Adana Sakirpasa` to ATMOS-X's
`Adana Şakirpaşa Airport` through the fold, and fell back from Beirut (no station) to Rayak.
What the probe does **not** cover is everything B83 exists for: whether the sky the mission
actually renders matches, and whether the kneeboard agrees with the turn display.

---

## What it does

With the **ATMOS-X** cloud preset pack selected, `Use ATMOS-X live weather` replaces the
turn's generated weather with a real METAR observation.

- The observation is fetched when the turn's `Conditions` are built, so it *is* the turn's
  weather. The turn display, the kneeboard QNH and winds, the active-runway choice and the
  carrier's course into wind all read the same thing the `.miz` gets.
- The mission always keeps its own date and time. Only the sky is taken.
- Any failure keeps the generated weather and logs why.

Settings live on **Mission Generation → Weather**, gated on the pack via `enabled_when`.

## Why the CLI's read-only command

ATMOS-X ships `atmosx-cli.exe`. Its `inject` command stamps the mission's date and time as
well as its weather, which would drag a 1991 or 2030 campaign to today. `metar <ICAO> --save`
writes a preset file that keeps the two apart — `vdata` is the weather, `dtime` is the clock —
and only `vdata` is read.

The CLI serves at most 30 days of history, so a campaign's own date almost never has a METAR
to fetch. The observation is therefore always the current one.

## Station selection

`dcs_icao.csv` ships beside the CLI and lists the airfields ATMOS-X knows per terrain. The
station is the field the player flies from if it reports, otherwise the nearest one on that
map that does. An ICAO can be set by hand instead.

Names are folded (accents, `Air Base`/`Airport`/`International` suffixes, punctuation) before
matching: ED and ATMOS-X spell the same airfield differently often enough that a verbatim
match finds two of sixty on Syria.

## Setup gotcha

The CLI runs, fetches and writes a preset **whether or not the ATMOS-X mod is activated in
DCS** — it warns (`ATMOS-X is not active in this DCS installation. Run 'atmosx-cli activate'
first.`) and carries on. That warning goes to the CLI's stdout, which is only logged on
failure, so a player who never activated the mod gets real METAR numbers and no ATMOS-X
clouds, with nothing in Retribution's log to say why. Auto-selection reads
`<DCS>\Config\Effects\clouds.lua` and returns `none` when it cannot resolve a preset, which
the code then treats as a clear sky.

## Constraints

- **A cloud base outside its preset's range is clamped, never passed through.** DCS refuses
  to save a mission whose base falls outside the preset's own `min_base`/`max_base`, and a
  METAR ceiling a few metres under the minimum is ordinary.
- **`clouds_preset` must be the pydcs object, not the preset key.** The mission writer reads
  `.name` off it and validates the base against it; a bare string takes mission generation
  down.
- **A preset key this DCS install does not have is dropped, not fatal.** The player may not
  have the pack the observation names.
- **`apply_weather` copies field by field rather than replacing wholesale.** A METAR describes
  only some of a DCS weather block; halo, cyclones and the rest stay as the campaign set them.

## The three fork couplings

Upstream hooks one call site, because upstream re-rolls the weather independently every turn.
The fork does not, and a straight port was wrong in three places. All three are pinned by
tests in `tests/weather/test_atmosx_live_weather.py`.

| # | Where | Straight port did | Now |
|---|---|---|---|
| 1 | `Conditions._evolve_weather_type` (§47) | Raised `StopIteration` on the turn after a live-weather turn — the ladder is the four generated classes and `LiveWeather` is on none of them | `Conditions._ladder_type` maps it by the archetype it observed, so the next turn evolves from the sky that was flown |
| 2 | `Conditions.advance` (§47) | Live weather landed on turn 1 only — every later turn comes through `advance`, which upstream never touches | `advance` takes `settings` and fetches too |
| 3 | `weather_planning.storm` / `poor_visibility_weather` (§67) | Read a live thunderstorm as clear — the isinstance test is against `Raining`/`Thunderstorm` | Falls back to the archetype id, so auto-recon stays home and low-level attack still demotes |

`enabled_when` also grew the ability to carry a non-bool expected value, so an option can be
gated on one choice of a dropdown rather than only on a checkbox. The fork greys such options
out; upstream's own version of this hides them (`visible_when`). Greying keeps them
discoverable, which is why the fork's existing mechanism was extended instead of a second one
being imported.

## Not adopted from upstream's commit

- `visible_when` and its `apply_visibility` pass — §28 already rebuilt the settings dialog
  with `_set_row_visible` + `apply_filter`, and a second visibility mechanism alongside the
  filter would fight it.

## Deferred

- **`fog2` is not read.** Only the legacy `fog` block maps onto the game's `Fog`; the modern
  fog animation rides along in `vdata` and reaches the `.miz` unread.
- **No caching.** Every turn that asks runs the CLI. Acceptable at one call per turn; it would
  not be if anything started asking per flight.
- **Windows only.** `detect_cli` reads the uninstall registry. `winreg` is imported at module
  scope and `conditions.py` imports this module, so the app does not import on Linux. Upstream
  has the same property and Retribution is a Windows app; noted rather than fixed.
