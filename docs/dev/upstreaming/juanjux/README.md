# Carve payloads for juanjux/dcs-retribution

Built 2026-08-24. Three apply-ready patches and two comparison briefs, prepared for
the second fork we watch — see
[414th-juanjux-fork-watch-notes.md](../../design/414th-juanjux-fork-watch-notes.md).

**These target his tree, not upstream `dev`.** Every patch was generated against
`juanjux/dcs-retribution@ca780fd2` and verified to apply there. That is the whole point:
a patch built against our own fork point (`dce851ea`) would not have applied — upstream
has moved, and so has he.

## What is here

| Payload | Kind | Applies to his tree | Tests |
|---|---|---|---|
| [naval-station-keeping](naval-station-keeping/) | patch | ✅ verified | 11, self-contained |
| [sead-coordination](sead-coordination/) | patch | ✅ verified | 15, self-contained |
| [region-priorities](region-priorities/) | patch (core only) | ✅ verified | 18 of 23 |
| [sortie-records](sortie-records/) | comparison brief | — | — |
| [dtc-cartridges](dtc-cartridges/) | comparison brief | — | — |

All three patches also apply **together**, in any order, and the seven touched files
compile as a set. Verified 2026-08-24:

```
git apply naval-station-keeping/station-keeping.patch \
          sead-coordination/sead-coordination.patch \
          region-priorities/region-priorities-core.patch
```

> The §69 and §93 settings hunks originally collided — both inserted at
> `desired_barcap_mission_duration`. §93 is re-anchored on
> `desired_awacs_mission_duration` so the two stack. If you regenerate either patch,
> re-check that.

## Why these five

His own inventory of our fork (`inventario_fork_414ret.txt`, his repo root) sets the
bar: pure Python, self-contained, no MOOSE, "clearly worth the maintenance". His
README's 2026-08 review covered our commits to 2026-08-22 and queued §90, §69 and the
§78 convoy half.

- **§87 naval station-keeping** — not in any of his ledgers. He is mid-naval build
  (anti-ship magazines, mixed hulls, three PLAN carrier groups in Marianas 2027) and
  without this every authored naval group generates with a zero-waypoint route and sits
  on its marker all mission. Single file.
- **§69 SEAD coordination** — he queued it by name and has not started. Ready here.
- **§93 region priorities** — landed 2026-08-20, two days after his review window
  closed, so he has not assessed it. It is the *weighting* answer to red-one1's
  upstream #686.
- **§91 sortie records** and **§74 DTC** — not patches. Each is a place where his tree
  and ours answer the same question differently, and the brief is the useful artifact.

## Fork identity stripped

The patches carry no `§N` markers, no `game/fourteenth/` package, and no pointers into
`docs/dev/`. `region_priorities.py` is renamed `game/regionpriorities.py`. Comments that
cited a fork design note were cut rather than re-pointed at a file he does not have.

## What is NOT here

- No in-game verification on his hardware. Our own rows: B48 is ◐ PARTIAL, B21 and B89
  are ☑ VERIFIED. See each payload's README.
- No Qt or React surfaces for §93 (core engine only).
- No upstream PR. The freeze binds us, and routing a carve through him to get around it
  would be using him as a proxy for a policy we have been told applies to us. These are
  offered for his fork and his testing; what he sends upstream is his call, on his
  timeline, as it already is.
