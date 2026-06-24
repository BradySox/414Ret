# HANDOFF — MANTIS IADS engine + MIST → MOOSE consolidation

**Date:** 2026-06-24
**Branch:** `claude/mantis-modern-iads-tsetkx`
**Read first:** [`414th-framework-consolidation-notes.md`](414th-framework-consolidation-notes.md),
[`414th-mantis-migration-notes.md`](414th-mantis-migration-notes.md),
and the in-game-pass checklist row **G6**.

This is the next-session pickup point for the work that started as "is MANTIS a more modern IADS than
Skynet?" and grew into a MIST → MOOSE consolidation program.

## ✅ Merged to `main` this session (PRs #141–#144)

- **#141** — MANTIS vs Skynet parity matrix + migration plan (engine-level scope).
- **#142** — IADS engine-agnostic abstraction seams: `IadsProperties` (alias `SkynetProperties`),
  `IadsRole.skynet_value`, `IadsNode`/`iads_nodes()` (aliases kept). Skynet output byte-identical.
- **#143** — `iads_engine` setting (`IadsEngine` enum, registered for JSON round-trip) + emitter
  wiring; **`ewrs` retired**; consolidation strategy + EWRS/dismounts/CTLD decision docs + MOOSE Ops
  opportunity map.
- **#144** — **MANTIS engine, phases 3–5, gated/inert** (core networking + tuning/shoot-and-scoot +
  comms/power/command-center C2 layer); `iads_engine` exposed as an experimental UI choice;
  CLAUDE.md/AGENTS.md updated with the MIST→MOOSE status + MOOSE docs link.
- Also retired earlier: **`dismounts`** (dead/dormant plugin).

## 🟡 Open: PR #145 (draft, docs-only)

CTLD↔SCAR intersection finding + corrected consolidation sequencing. Safe to merge anytime; it's the
only thing not yet in `main`. (This handoff doc rides on it too.)

## ⭐ THE next step — fly the MANTIS G6 in-game pass

The entire MANTIS engine is **built but never run.** Nothing else should be built on it until it's
flown. It is gated behind `iads_engine` (default **SKYNET**, so `main` is unaffected).

**To test:** Settings → **Mission Generator → Gameplay → IADS engine → "MANTIS (experimental)"**,
generate a mission with red SAMs + EWRs, fly in. Watch `dcs.log` for `mantis-config.lua` /
`MANTIS C2 -` lines and `skynetiads-config.lua ... skipping`.

**#1 risk to confirm:** MANTIS owns SAM emissions and may **re-enable a SAM the phase-5 C2 watcher
disabled** on its next detection cycle (so comms/power-loss degradation may not "stick"). If so, the
watcher must remove the SAM from MANTIS' managed set, not just toggle the group. Full pass criteria +
fail signatures are in `414th-ingame-pass-checklist.md` **G6**.

## After G6 — the remaining MIST → MOOSE work (do NOT blind-port)

**Key sequencing rule (see consolidation notes):** `mist_4_5_126.lua` cannot be unloaded until **all**
consumers are off it, and **CTLD (84 refs) is the long pole.** So:

1. **CTLD → `Ops.CTLD`** is the gate. Port it as a gated, **SCAR-validated** bridge — SCAR's
   capture + CSAR reuse the air-assault CTLD machinery, so a wrong port breaks the flagship. Scope:
   `414th-ctld-mantis-style-port-scope.md`.
2. **SCAR/intercept glue + core `dcs_retribution.lua`** — these are *live* spawning/routing/scheduling
   (`mist.dynAdd`, `mist.goRoute`, `mist.scheduleFunction`), not helpers. Porting them *before* CTLD
   buys nothing (MIST stays loaded for CTLD) while risking live regressions. **Batch them with the
   final MIST drop**, in one in-game-validated pass.
3. **Drop MIST** from `base/plugin.json` — definition of done.

**⚠️ Do not delete `mist`/`mist_4_5_126.lua` until CTLD + SCAR/intercept + core glue are all off it.**
This is also called out in CLAUDE.md's Tech Stack row.

## Deferred MANTIS enhancements (gated, safe to build after G6 validates the base)

Proactive SHORAD scoot-zones (needs Python zone-gen) and `SetAdvancedMode` (needs HQ/command-center
group wiring). Both noted in the migration doc; neither blocks G6.

## State of play in one line

Skynet is still the live IADS engine; MANTIS is fully built and one flight test away from being a real
option; 2 of 5 MIST consumers retired; CTLD is the gate for finishing the MIST drop.
