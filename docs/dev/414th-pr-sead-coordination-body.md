# Held PR body — strikes push behind their SEAD window (§69 carve)

Branch: `BradySox:feature/sead-strike-coordination`, cut from upstream `dev` @ `59719b24`.
Target: `dcs-retribution/dcs-retribution` `dev`. **Held under the PR freeze** — §69 answers no
open upstream issue, so the 2026-08-20 issue-ledger exception does not cover it.

Paste the body below with `gh pr create --body-file`, as a draft.

---

## Title

Time strikes into the window behind their SEAD

---

## Body

Packages are scheduled independently. The generic branch in `MissionScheduler` spreads each
package's TOT randomly across the mission window, and nothing connects a strike to the SEAD or
DEAD package tasked against the SAM covering its target. A strike can arrive at a defended
objective half an hour before its suppression.

This adds one pass that sequences them, behind a new option, off by default.

### What it does

`_coordinate_sead_windows` runs after the main scheduling loop, so it sees final TOTs.

- Providers are packages whose `primary_task` is `SEAD` or `DEAD`, read via
  `getattr(package.target, "max_threat_range", None)` so a non-TGO tasking degrades to "no
  window" instead of raising. A zero ring (a dead site) opens no window.
- Consumers are `STRIKE`, `BAI`, `OCA_RUNWAY`, `OCA_AIRCRAFT` and `CAS` packages that are not
  `auto_asap` and have no player flight.
- A consumer matches a provider when the provider's target position is within the ring of the
  consumer's target position.
- The window opens `SEAD_WINDOW_LEAD` (2 min) after the **latest** matching provider's TOT and
  lasts `SEAD_WINDOW_DURATION` (8 min). `max`, not `min`: every suppressor on station before the
  strike pushes.
- A strike already inside the window keeps its TOT. One outside moves to the window opening —
  delayed if it was naked, pulled forward if the spread left it long after the window closed.
- Never earlier than `TotEstimator.earliest_tot`. If even that is past the window, the TOT is
  kept, unless keeping it would still leave the strike ahead of its SEAD.
- Several strikes behind one suppressor mass into the same window.

Armed Recon and Air Assault are deliberately excluded. Armed Recon is a loitering sweep rather
than a push, and Air Assault is timed by the ground war.

CAS is included for the front-line sandwich: it descends to acquire and takes MANPADS low, then
climbs to escape into the area-SAM ring high, so a front under a live umbrella wants that
umbrella down first for the same reason a strike does. CAS already proposes an organic
`SEAD_SWEEP` escort, but that flies the package's own TOT, so it accompanies rather than
pre-suppresses.

### Players are immune, providers are read-only

A package with a player flight is never rescheduled. A player-flown SEAD still opens a window
the AI strikes push behind, because providers are only read.

### One refactor, and why it is behaviour-identical

The recovery-tanker ETA collection moves out of the scheduling loop into its own loop below the
new pass.

It has to move: `flight_plan.landing_time` derives from the package TOT, so a package retimed by
this pass would otherwise have booked its recovery tanker against a landing it no longer flies.

With the option off the two are equivalent. The branches that previously skipped the collection
did so by `continue`ing when `_get_departure_time` returned `None`, and
`Package.mission_departure_time` returns `None` only when the package has no flights — where the
inner `for f in package.flights` loop iterated nothing anyway. The `RECOVERY` skip is carried
over explicitly.

### Option

`sead_strike_coordination`, Campaign Doctrine → General, default off. With it off the pass
returns on the first line and no TOT changes.

### Tests

`tests/test_sead_strike_coordination.py`, 19 tests, self-contained — pydcs plus `SimpleNamespace`
fakes, no campaign fixtures.

The window math is a free function, `coordinated_strike_tot(strike_tot, earliest_tot,
provider_tots, lead, duration)`, which takes no `self` and touches no engine types, so the
interesting half is testable without building a `Coalition`. Eight tests cover it directly:
delay the naked strike, keep an in-window TOT, pull a far-late TOT back, clamp to physics, both
unreachable-window cases, latest-provider, and the no-provider no-op.

Eleven cover the scheduler wiring: ring matching in and out, player and ASAP immunity, provider
read-only, massing, the setting gate, a dead SAM's zero ring, CAS covered and uncovered, CAS and
a strike massing together, and a guard pinning Armed Recon and Air Assault as excluded at the
same front line the CAS test retimes at, so a later edit sweeping them in fails there first.

### Verification

- `black --check` — clean
- `mypy game tests` — no issues in 491 source files
- `pytest tests` — 471 passed, 2 skipped
- Red/green: removing `FlightType.CAS` from the set fails exactly the two CAS behaviour tests
  and leaves the exclusion guard passing.

Flown in the fork this is carved from, with one caveat stated plainly: the mechanism is verified
in-game for the strike case, and the CAS extension has not yet had its own in-game pass. Worth
watching for if it is flown: whether massing CAS behind a DEAD thins the front-line coverage
window relative to today's spread.
