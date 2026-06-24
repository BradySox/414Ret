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

## ✅ G6 in-game pass — PASSED 2026-06-24 (engine routing + networking + C2)

The MANTIS engine has now **been run in-game** and passed the high-risk parts. Confirmed from
`dcs.log` + the `.miz` engine marker + a Tacview + direct AI-vs-AI observation:

- Engine routing correct (`Skynet … skipping`, MANTIS builds both coalitions, watchers armed),
  MANTIS v0.9.34 + INTEL/DLINK start clean, no Lua errors.
- C2 events fire on both comms and power kills (`MANTIS C2 - comms/power … lost`).
- **The #1 risk did NOT materialize:** degraded *networked radar* SAMs (SA-3/5/6) stayed offline
  against live targets — MANTIS did **not** re-enable them. The only late launches were autonomous
  SHORAD (SA-8/2S6), which are out of C2 scope by design (`IadsRole.participate` excludes
  `POINT_DEFENSE`/`NO_BEHAVIOR`). So the watcher does **not** need the "drop from MANTIS' managed
  set" fix.

Full results + caveats in `414th-ingame-pass-checklist.md` **G6**.

**Minor remaining:** the human-flown emissions-control "dark until in range" path is not yet
eyeballed (lower risk). Separately noted: 13-of-14 red SAMs hung off one power node — a
connection-graph concentration worth a later look (Python IADS-gen, not MANTIS).

## ⭐ THE next step — MANTIS is validated; CTLD is now the gate

With G6 passed, MANTIS is a **real, flight-validated option** (still gated behind `iads_engine`,
default SKYNET). The decision to flip the default to MANTIS can be made after the minor
emissions-control eyeball. The remaining MIST→MOOSE work below is now unblocked.

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

Skynet is still the default IADS engine; MANTIS is **fully built and now flight-validated (G6 passed
2026-06-24)** — a real selectable option, pending only a minor human-flown emissions-control eyeball
before the default could flip; 2 of 5 MIST consumers retired; CTLD is the gate for finishing the MIST drop.
