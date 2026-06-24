# Decision: Retire the `ewrs` Plugin (MIST → MOOSE consolidation, phase 2)

**Status:** decision / recommendation (no code change yet)
**Date:** 2026-06-24
**Parent:** [`414th-framework-consolidation-notes.md`](414th-framework-consolidation-notes.md) phase 2.

## Decision

**Delete `resources/plugins/ewrs/` rather than port it.** It is made redundant by the fork's own
**`bigeye`** plugin, which already provides the same player-facing capability on MOOSE with **zero**
MIST dependency. This is the cheapest MIST win after Skynet → MANTIS.

## What `ewrs` does

`resources/plugins/ewrs/ewrs.lua` is the **EWRS** (Early Warning Radar Script, v1.5.3, by Steggles)
— an EWR-driven **BRA threat-callout** system: radar units (EWRs, AWACS) broadcast periodic
Bearing/Range/Altitude contact reports to friendly pilot groups as on-screen text, with an F10 menu
to toggle reports, switch imperial/metric, change reference (self vs bullseye), and request bogey
dope. Scheduled (~30 s) + on-demand.

## Why it's redundant

The fork already ships **`bigeye`** (`resources/plugins/bigeye/bigeye_ewr.lua`) — a fork-authored,
**MOOSE `Ops.INTEL`-based** EWR with strictly broader capability:

| | `ewrs` (legacy) | `bigeye` (modern, fork) |
|---|---|---|
| Framework | **MIST** (2016) | **MOOSE `Ops.INTEL`** (2024+) |
| MIST deps | 3 utility helpers (`makeUnitTable`, `DBs.unitsById`, `utils.*` conversions) | **0** |
| Player feature | EWR→pilot BRA callouts | EWR→pilot **A2A BRAA** + GCI tasking + friendly picture |
| F10 menus | basic | rich |
| Config options | none | many (frequency, cutoff, per-coalition sensor tuning) |
| Default | off | off |
| Authorship | upstream Steggles, unmodified | **414th** (canonical) |

Both are **default-off** standalone plugins — mission designers pick one. MANTIS and Skynet do **not**
substitute here: they use EWRs for SAM *coordination*, not for broadcasting BRA to players. `bigeye`
is the player-callout successor.

## Evidence / provenance

- `resources/plugins/ewrs/plugin.json` — `defaultValue: false`, single script work order, no options.
- `resources/plugins/ewrs/ewrs.lua` — unmodified upstream Steggles code (no 414th patches); ~13 MIST
  *occurrences* across just **3 distinct** MIST functions, all low-level utilities with MOOSE
  equivalents already in `Moose.lua` (`UTILS.*`).
- `resources/plugins/bigeye/bigeye_ewr.lua` — changelog explicitly notes the refactor to `Ops.INTEL`;
  fork-authored; the 414th standard.
- No `game/` Python or `.miz` force-enables the `ewrs` mnemonic. The `game/` references
  (`mizcampaignloader.py: ewrs()`, `start_generator.py: generate_ewrs()`) are **EWR *unit*
  placement** (faction/layout), unrelated to the `ewrs` *plugin* — they are unaffected by deletion.

## Risk

**Effectively zero.** Optional, default-off, nothing forces it on, and a superior fork-owned
replacement already ships. The only consideration is a mission designer who manually enabled `ewrs`;
they switch to `bigeye` (better in every dimension).

## Action when executed (not in this doc)

1. Remove `resources/plugins/ewrs/`.
2. Note the retirement in `changelog.md` (EWRS → BigEye, MOOSE-based).
3. Confirm no bundled `.miz` references the `ewrs` mnemonic.
4. Removes ~13 MIST occurrences toward the phase-7 `mist` drop.
