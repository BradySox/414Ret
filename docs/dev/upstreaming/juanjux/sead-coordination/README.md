# Strikes push behind their SEAD window

414Ret §69. He queued this by name in his README's 2026-08 review — "packages are
scheduled independently today, so nothing stops a strike entering a ring before the SEAD
servicing it." This is that, ready to apply.

## The defect

`MissionScheduler` times packages independently: a random spread over the mission
window. Nothing connects a strike to the SEAD tasked against the SAM covering its
target, so a strike can arrive at a defended objective **half an hour before** its
suppression.

## What it does

One pass after the spread schedule, before the recovery-tanker ETAs.

- For every movable strike-class package, find the SEAD/DEAD packages whose target's
  threat ring covers the strike's target.
- Open a window `SEAD_WINDOW_LEAD` (2 min) after the **latest** of those TOTs — every
  suppressor on station first — lasting `SEAD_WINDOW_DURATION` (8 min).
- A strike already inside keeps its TOT. One outside moves to the window opening:
  delayed if it was naked, pulled forward if the spread left it long after the window
  closed. Never earlier than the package can physically fly.
- Several strikes behind one SEAD mass into the same window. That is the point — it
  reads as a push.

`STRIKE`, `BAI`, `OCA_RUNWAY`, `OCA_AIRCRAFT`. Armed Recon (a loitering sweep, not a
push) and Air Assault (tied to the ground war's timing) deliberately stay on the spread.

**Only AI, non-ASAP packages move.** A package with a player flight is never
rescheduled — but a player-flown SEAD still opens a window the AI pushes behind, because
providers are read-only.

Off by default (`sead_strike_coordination`, Campaign Doctrine → General).

## Applying

```
git apply sead-coordination.patch
cp test_sead_strike_coordination.py tests/
```

Verified to apply at `ca780fd2`. Touches `game/commander/missionscheduler.py` (+124) and
`game/settings/settings.py` (+19).

The 15 tests are self-contained — pydcs plus `SimpleNamespace` fakes. They split into the
pure window math (`coordinated_strike_tot`, a free function taking four arguments) and
the scheduler wiring (threat-ring matching, latest-provider, player/ASAP immunity, the
setting gate).

> **Ordering note.** His scheduler has no carrier-recovery stagger, so the pass is
> anchored directly before the recovery-tanker ETA filtering. In our tree it runs before
> the stagger as well; the stagger only ever *delays*, so it can nudge a strike deeper
> into its window but never back ahead of its SEAD. If he adds a stagger later, keep that
> order.

## Verification status here

**☑ VERIFIED** (our row B21). Flown. No caveats outstanding.
