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

## 🔴 CRITICAL FIX 2026-06-26 — MANTIS was controlling ZERO SAMs (EMCON never worked)

The "minor remaining" note above (human-flown "dark until in range" not eyeballed) turned out to hide
the core bug. A 2026-06-26 playtest eyeballed it: SA-2/SA-6 **track radars emitted in search mode on
ingress** — no EMCON at all. Root cause: MOOSE `SET_GROUP:FilterPrefixes` matches each prefix with
`string.find(name, prefix)` **as a Lua pattern** (Moose.lua ~13321), escaping only `-`. Every
Retribution SAM group is named `NNNN | CALLSIGN (SAM)`; the `(...)` is read as a pattern capture, so a
name never matches its own group. `mantis.SAM_Group` was therefore **empty** — MANTIS controlled **0
SAMs**, which then ran vanilla DCS AI (radars always on). True for **every MANTIS campaign since it
became the default**.

Why G6 still "passed": the C2 layer (`setup_c2`) uses `GROUP:FindByName` (exact, not patterns), so
comms/power/decapitation worked and masked the dead core. The "SAMs stayed offline after a power kill"
observation was the C2 `SetAIOff`, **not** MANTIS EMCON.

**Fix (PR `claude/mantis-emcon-prefix-fix`):** `mantis-config.lua` now Lua-pattern-escapes every name
before handing it to `MANTIS:New` (`escape_prefix`), and logs `resolved N/M SAM + K EWR live group(s)`
right after `Start()` as the EMCON ground truth (**0 SAM = still broken**). **Re-run G6** watching that
log line (should equal the SAM count) and confirm in-cockpit that SA-2/3/6 track radars stay dark until
you're in range.

## ⭐ THE next step — MANTIS is the default; CTLD is now the gate

With G6 passed, **MANTIS is now the default IADS engine for new campaigns** (flipped 2026-06-24;
existing campaigns stay on their original engine via the `__setstate__` Skynet pin). Skynet remains
selectable. The only remaining MANTIS follow-up is a minor human-flown emissions-control eyeball
("SAM radars dark until a target is in range") — lower-risk, does not block anything. The remaining
MIST→MOOSE work below is now unblocked.

## After G6 — the remaining MIST → MOOSE work (NEW strategy: a MOOSE-backed `mist` shim)

**The plan changed (2026-06-24).** Rather than rewrite each consumer to be MOOSE-native (the old
"CTLD → `Ops.CTLD` is the gate" approach), we retire MIST by **replacing `mist_4_5_126.lua` with a thin
`mist` compatibility shim that delegates to MOOSE** (which already provides MIST's two roles: utility
library + object DB). One artifact, consumers untouched, **SCAR can't break**, no `Ops.CTLD` template
mismatch. **Active plan:** [`414th-mist-moose-shim-notes.md`](414th-mist-moose-shim-notes.md). The
`Ops.CTLD` port is **shelved** (`414th-ctld-mantis-style-port-scope.md`).

1. **Build the shim** — `resources/plugins/base/mist_moose_shim.lua` implementing the 42 called
   symbols. Tier-1a (vector/math utils) is in; remaining tiers (geo/coord, object DB, spawn/route/
   sched, msg/log) per the design doc.
2. **Validation swap** — in `base/plugin.json`, replace `mist_4_5_126.lua` with the shim (load AFTER
   `Moose.lua`, BEFORE consumers). In-game pass: CTLD cycle, SCAR capture + CSAR, intercept/QRA,
   Skynet (if selected), core glue.
3. **Drop MIST** — delete `mist_4_5_126.lua` + its `base/plugin.json` entry. **Definition of done.**

**⚠️ Do not swap `base/plugin.json` to the shim until every one of the 42 symbols is implemented** —
a missing symbol crashes a consumer at runtime. Until the swap, `mist_4_5_126.lua` stays loaded and
`main` is unaffected. (CLAUDE.md's Tech Stack row still gates deletion on the consumers being off MIST.)

## Deferred MANTIS enhancements (gated, safe to build after G6 validates the base)

Proactive SHORAD scoot-zones (needs Python zone-gen) and `SetAdvancedMode` (needs HQ/command-center
group wiring). Both noted in the migration doc; neither blocks G6.

## State of play in one line

**MANTIS is now the default IADS engine** for new campaigns (G6 passed 2026-06-24; existing campaigns
pinned to their engine); Skynet still selectable, pending only a minor emissions-control eyeball. MIST
retirement is now a **MOOSE-backed `mist` shim** (not per-consumer ports): `mist_moose_shim.lua` Tier-1
(utils + geo/coord) is in, inert; Tiers 2–4 (object DB, spawn/route/sched, msg/log) remain, then the
`plugin.json` swap + in-game pass drops `mist_4_5_126.lua`.
