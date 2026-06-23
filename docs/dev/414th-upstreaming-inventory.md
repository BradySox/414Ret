# 414th Upstreaming Inventory

Every generic fix the 414th carries that **isn't** upstreamed is a guaranteed
merge conflict on every `dcs-retribution/dcs-retribution` `dev` pull, forever.
The cure is to carve the non-fork-specific fixes out into PRs against the 414th's
PR fork (`bradyccox/dcs-retribution`) so they either land upstream or at least
live on a clean branch that rebases cleanly. This file is the **inventory +
queue**: what's genuinely generic, how ready it is, and — just as important —
what is fork-specific and must **never** go upstream.

Working clones live at `..\retribution-pr` (and `..\pydcs-pr` for pydcs); see
the [upstreaming-prs memory] / `docs/` runbook for the carve-out mechanics.
Verify each candidate in-game first (cross-ref
[414th-ingame-pass-checklist.md](414th-ingame-pass-checklist.md)) — an
unvalidated "fix" is not something to ask upstream to take.

## Readiness legend

| Mark | Meaning |
|---|---|
| 🟢 READY | Lua-free, tested, in-game VERIFIED — carve the PR now |
| 🟡 NEAR | Tested but needs an in-game pass (checklist row) before submitting |
| 🟠 CARE | Touches Lua / a vendored script — split the upstreamable Python from the fork glue |
| 🔵 DONE | Already an open/merged upstream PR |
| ⛔ NEVER | Fork-specific — keep on `main`, do not upstream |

---

## Queue (priority order)

| # | Fix | Readiness | Value | Checklist |
|---|---|---|---|---|
| 1 | Landmap terrain-query perf | 🟢 READY | High (broad: ~7 min off ground-gen) | n/a (perf, gen-covered) |
| 2 | DEAD reachability gate on follow-on strikes | 🟡 NEAR | High (planner correctness) | B2 |
| 3 | Support-orbit depth + front-anchor | 🟡 NEAR | High (red AWACS/tanker placement) | C1, C2 |
| 4 | Player-despawn loss accounting | 🟠 CARE | High (false combat losses) | D1 |
| 5 | SOF C-130 runway-start fallback | 🟡 NEAR | Medium (general spawner fix) | E |
| 6 | Negative-start-packages takeoff-time check | 🟢 READY | Low/Medium (UI false-warn) | n/a |
| 7 | AAQ-33 targeting-pod era restriction | 🔵 DONE | — | — |

---

## Details

### 1. Landmap terrain-query perf — 🟢 READY
- **What:** `is_on_land`/`is_in_sea` must test the **prepared** `MultiPolygon`,
  and `pickle` bypasses `__post_init__`, so the spatial index has to be rebuilt
  on load. Fixing both cut a ~7-minute ground-generation stall.
- **Why upstream cares:** pure perf, zero behavior change, benefits every
  theater/campaign — the easiest possible upstream sell.
- **Files:** `game/theater/conflicttheater.py` (landmap query + `__setstate__`/
  index rebuild).
- **In-game pass:** not required — it's a generation-time perf fix already
  exercised by the normal campaign-gen path.
- **Note:** confirm whether the prepared-geometry dependency is satisfied in a
  clean upstream checkout (Shapely version) before submitting.

### 2. DEAD reachability gate on follow-on strikes — 🟡 NEAR
- **What:** a follow-on strike behind a SAM belt is deferred until the belt is
  actually down, instead of trusting an optimistic DEAD clear. The DEAD itself is
  still tasked (with SEAD escort).
- **Why upstream cares:** this is upstream-core HTN behavior, not a 414th
  concept — a correctness fix to the stock planner.
- **Files:** `dead_can_reach` geometry + `apply_effects` routing in
  `game/commander/.../theatercommander.py`.
- **Tests:** `tests/test_dead_planning.py`.
- **Blocker:** in-game pass B2 (confirm blue defers deep strikes until the belt
  is down).

### 3. Support-orbit depth + front-anchor — 🟡 NEAR
- **What:** AWACS/tanker racetracks anchored on the FLOT (#84) and held at a
  depth decoupled from the player's threat strength via
  `AI_SUPPORT_DEPTH_FACTOR` (#86), so red support doesn't loiter on the front.
- **Why upstream cares:** upstream-core flight-plan code; the off-axis red AWACS
  fling is a stock bug.
- **Files:** `game/ato/flightplans/supportorbit.py`.
- **Tests:** `tests/test_support_orbit.py`.
- **Blocker:** in-game pass C1 + C2.

### 4. Player-despawn loss accounting — 🟠 CARE
- **What:** a player dropping to spectator (or a mission ending with players
  airborne) made DCS fire `S_EVENT_CRASH`/`DEAD`, attriting a surviving jet +
  pilot. The fix marks the unit on `S_EVENT_PLAYER_LEAVE_UNIT` and suppresses the
  loss within `PLAYER_LEAVE_GRACE_S`; real shootdowns (loss event fires before
  leaving the seat) and ejections still count.
- **Why upstream cares:** loss-accounting correctness, airframe-agnostic.
- **Files:** `game/debriefing.py` (Python) **+** `dcs_retribution.lua` (the
  plugin-side `PLAYER_LEAVE_UNIT` marking). **Split the PR:** the Python debrief
  logic is clean; the Lua hook lives in the bundled runtime script, so confirm
  the upstream `dcs_retribution.lua` has the same event surface before porting.
- **Tests:** `tests/test_debriefing.py::test_lua_suppresses_player_despawn_loss_events`.
- **Blocker:** checklist D1 (PARTIAL) — verify the engine-teardown edge case.

### 5. SOF C-130 runway-start fallback — 🟡 NEAR
- **What:** on `NoParkingSlotError`, retry a **runway start** before forcing an
  air spawn — previously gated to `FlightType.JAMMING`, now any non-helo
  cold/warm start at an airfield. Stops large aircraft air-spawning when a ground
  start was selected.
- **Why upstream cares:** general spawner robustness, not SOF-specific.
- **Files:** `game/missiongenerator/aircraft/flightgroupspawner.py`
  (`generate_flight_at_departure`).
- **Blocker:** in-game pass E (the SOF half) — but the runway-fallback logic is
  exercisable by any large-aircraft ground start.
- **⚠️ Carve carefully:** ship ONLY the runway fallback. The **EW plugin
  de-conflict** that ships alongside it (§ below) is fork-specific.

### 6. Negative-start-packages takeoff-time check — 🟢 READY
- **What:** `QTopPanel.negative_start_packages` checks **takeoff** time (not
  startup) for DCA patrols, so a normal player-occupied cold-start CAP stops
  tripping the "can't start in time" warning while a genuine misplan still warns.
- **Why upstream cares:** stock UI false-positive fix.
- **Files:** `qt_ui/.../QTopPanel.py`.
- **Tests:** `tests/test_negative_start_packages.py`.
- **Note:** `qt_ui` isn't in the CI mypy path upstream either; Black-clean is the
  bar.

### 7. AAQ-33 targeting-pod era restriction — 🔵 DONE
- Already open as upstream **#786** (`codex/fix-aaq33-era-restriction`). No
  action here; listed so it isn't re-carved.

---

## ⛔ Fork-specific — do NOT upstream

- **C-130J EW (`c130j`) plugin de-conflict on SOF inserts**
  (`game/missiongenerator/luagenerator.py` `_sof_c130_present`): skips the 414th
  EW/ISR plugin when a `FlightType.SOF` flight is a C-130J-30. Depends entirely
  on the fork's `c130j` plugin and `FlightType.SOF` — meaningless upstream.
- **The entire SCAR / commander-capture / SOF / CSAR stack, TIC, TARS, Flight
  Control 414th glue, QRA reserve doctrine, recon fog** — these are the 414th
  *features*, not generic fixes. Keep on `main`.
- **Splash Damage 3.4.2 414th buddy-tuned build** — pinned, intentionally
  divergent from upstream/source. Never push upstream or overwrite from it.

---

## Carve-out checklist (per PR)

1. Branch off a **clean** `dcs-retribution/dev` in `..\retribution-pr` (not off
   `main` — that drags the whole feature stack).
2. Cherry-pick / re-apply only the files listed for that item; drop any
   fork-specific glue (see ⛔).
3. Run the upstream repo's own lint/test gates (not the 414th's).
4. Confirm the matching [in-game pass](414th-ingame-pass-checklist.md) row is
   ☑ VERIFIED before opening the PR.
5. Open against `dcs-retribution/dcs-retribution`; record the PR number back in
   the Queue table here and flip readiness to 🔵 DONE.

[upstreaming-prs memory]: how generic 414Ret fixes become upstream PRs; working
clones in `..\retribution-pr` and `..\pydcs-pr`.
