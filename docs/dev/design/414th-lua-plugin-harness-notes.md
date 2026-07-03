# Headless Lua plugin test harness (lupa)

**Status: landed (first slice) — vietnamops covered; extend per-plugin as needed.**

## The gap

The Lua plugins are the runtime half of every 414th feature, but CI could only prove they
*parse* (`lua-lint.yml`, `luac5.1 -p`). Whether a script actually *runs* — arms its timers,
survives its config table, fires its effects — was only ever proven by an in-game pass, which
is why the checklist (`414th-ingame-pass-checklist.md`) accumulates UNTESTED rows and why
several past regressions (the Sandy divert no-op, the combat SAR dispatch crash) shipped
parse-clean and failed at runtime.

Meanwhile `lupa` (a real Lua interpreter embeddable in Python) has been in
`requirements.txt` the whole time, used only by `resources/tools/import_beacons.py`.

## What this is

`tests/lua/` runs the *real, unmodified* plugin scripts inside pytest on **Lua 5.1 — the
dialect DCS runs** (`lupa.lua51`; this matters: e.g. `math.atan2` exists in 5.1 but not 5.4,
so testing on the wrong dialect would pass code DCS rejects, and vice versa):

- **`dcs_stubs.lua`** — a fake of the vanilla-DCS mission sandbox: a virtual clock backing
  `timer.scheduleFunction` (with DCS's reschedule-by-return semantics), recording
  `trigger.action.*` stubs, a tiny unit/group world the tests populate
  (`coalition.getGroups`, `Group.getByName`, attributes, life, velocity), event dispatch
  (`world.addEventHandler` + `DcsHarness.fireEvent`), and a **minimal MOOSE facade**
  (`GROUP:FindByName` / `IsAlive` / `GetCoordinate` / `TaskFireAtPoint` / `PushTask`) that
  wraps the fake world — NOT the real `Moose.lua`.
- **`harness.py`** — `DcsPluginHarness`: builds the `dcsRetribution` config table from plain
  Python dicts (exactly what the mission generator would have emitted), loads a plugin file,
  advances the virtual clock, and returns the recorded activity for assertions.
- **`test_vietnamops_runtime.py`** — the first consumer: the data-presence gates, Arc Light
  (release range, one-shot, dead-bomber-never-fires, malformed-record degradation), the flak
  envelope (in-range bursts near-but-never-on the aircraft, ceiling safety, no-guns no-op),
  and airbase harassment (grace period, ramp dispersion, and the **`excludedFields`
  player-field double-guard** — the anti-grief guarantee, now CI-locked).

Sabotage-verified at build time: deleting the excluded-field guard and typo-ing
`trigger.action.explosion` inside a timer tick both turn the suite red.

## What it is NOT

It models **no DCS AI, LoS, physics, weapons flight, or pathfinding** — a green harness run
says "the script executes and its logic branches behave", never "the feature feels right in
the cockpit". The in-game pass checklist stays authoritative for behavior; this kills the
*"script errored and the feature silently never started"* class before anyone flies, and
pins the safety-critical invariants (grace periods, exclusion lists, one-shot latches) that
an in-game pass exercises only incidentally.

Loading the real `Moose.lua` is explicitly out of scope for this slice (its `DATABASE` init
scans a live mission world); plugins that lean on deep MOOSE state (tars, mantisiads) need
either a fatter facade or targeted extraction before they can ride the harness.

## Extending it

1. Enumerate the plugin's API surface: `grep -oE "(env|timer|trigger|world|coalition|land|missionCommands)\.[A-Za-z_.]+" <plugin>.lua | sort -u` and the `:Method(` calls.
2. Add any missing stubs to `dcs_stubs.lua` (record, don't simulate).
3. Feed `set_retribution_config` the same table shape the plugin's `*luadata.py` emitter
   produces (read the emitter, not the docs).
4. Drive `advance_to` past the plugin's poll/grace constants; assert on
   `records("explosions"|"texts"|"marks"|"firedTasks"|...)` and always end with
   `assert_no_lua_errors()`.

Good next targets: `combatsar`'s divert/release routing (G23's regression shape), the
`airecon` capture trigger (G19), TIC stance cadences.

## CI

No workflow change: `test.yml` installs `requirements.txt` (lupa is pinned there) and runs
`pytest tests`, which picks the suite up. The whole vietnamops suite runs in ~0.1 s.
`lua-lint.yml` still owns syntax; `.luacheckrc` scope is untouched (tests/lua is not a
mission script).
