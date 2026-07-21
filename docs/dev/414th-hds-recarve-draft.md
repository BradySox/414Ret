# HDS Ultimate Compilation re-carve — HELD DRAFT (2026-07-20)

**Status: HELD — do not open yet.** Two gates, in order:

1. **Upstream PR freeze** — dcs-retribution accepts no NEW PRs until their next beta
   release (expected the weekend of 2026-07-25/26). Updating existing PRs is allowed.
2. **The DM's mod-update pass** — the installed CH packs + HDS are about to be updated,
   which invalidates the 2026-07-20 export baseline. Before opening: re-run the export
   (runbook in `tools/verify_mod_export.py`), re-align
   `pydcs_extensions/highdigitsams` to the fresh export, and re-confirm 363/363.

## Why #851 closed, and the answer this draft leads with

[#851](https://github.com/dcs-retribution/dcs-retribution/pull/851) closed on a real
objection from juanjux: he runs **Auranis HighDigitSAMs 2.1.0**, and the Ultimate
Compilation's S-300PS radar renames are **not backward-compatible** with it — so "which
successor mod does upstream standardize on?" must be answered before any re-carve.

**Recommended stance (lead of the PR body):** standardize on the **Ultimate Compilation**
(https://github.com/dcs-sams/HighDigitSAMs-Ultimate-Compilation, v1.4.3+):

- The original Auranis line is abandoned; UC is the maintained successor taking fixes.
- The UC data in this PR is **export-verified** — every registered unit diffed
  field-for-field against a live DCS install via the wiki's own `pydcs_export.lua`
  process (the #881/#886 review bar), not transcribed from mod sources.
- Ship a **migration note** in the PR body + changelog: Auranis users must swap mods;
  the renamed S-300PS radars mean existing Auranis-based missions keep working in DCS
  but Retribution's HDS toggle now expects UC ids.

**Fallback offered in the body (maintainer's pick):** a separate `high_digit_sams_uc`
ModSettings toggle alongside the existing Auranis one, so neither user base breaks —
costs a second checkbox + duplicate preset wiring; the fork deliberately did NOT do
this (it switched entirely to UC), so the dual-toggle variant would be new work.

## Draft PR title

> High Digit SAMs: retarget mod support to the maintained Ultimate Compilation (v1.4.3+)

## Draft PR body skeleton

- **What/why**: the Auranis HDS line is abandoned; UC is the maintained successor. This
  retargets the existing `high_digit_sams` toggle to UC and absorbs its breaking
  changes. (Then the successor-mod stance + migration note, per above.)
- **Contents** (all landed + long-flown on the 414th fork — §41):
  - Renamed S-300PS radars (`30N6 MAST tr` / `76N6E sr` / `64H6E MOD sr`) re-pointed in
    the S-300 Site layout + SA-10B preset + `radar_db.py`
  - Dropped HDS KS-19/SON-9/SA-24 replaced by vanilla equivalents (retired pydcs classes
    + unit yamls kept as save-compat tombstones only)
  - The new families: S-400/SA-21 + S-300V4 + S-300PT presets on the extended S-300
    Site, SAMP/T (+NG) on a Patriot-geometry `SAMP/T Battery` layout, Pantsir-SM,
    SA-7/7b manpads, 4 EWRs (P-37 Bar Lock closes the period red EWR gap), ERO ZU-23
    technicals — 42 units, 7 presets
  - `Faction.remove_vehicle` id-vs-name fix (the old name-based strips silently never
    removed anything)
  - **NEW since #851**: the export-verified data alignment (UC's NATO-reporting-name
    display names + sensor retunes — e.g. SA-17 TELAR detection 120 km → 18.5 km, S-400
    92N6E 410 → 450 km, 96L6E mast 300 → 520 km, SA-7/7b threat halved) — re-verify
    against the post-update export before opening
  - **NOT carried**: the 414th faction enrichment (P-37/SA-7/S-400 faction wiring stays
    fork-side)
- **Validation**: upstream pytest/Black/mypy + the export verdict block pasted from
  `tools/verify_mod_export.py --extension highdigitsams --markdown` (upstream has no
  such tool — paste the fork-run verdict).

## Pre-open checklist

- [ ] DM's mod updates done (CH packs + HDS current)
- [ ] Fresh export run + `pydcs_extensions/highdigitsams` re-aligned (fork commit)
- [ ] Upstream freeze lifted (next beta shipped)
- [ ] Successor-mod stance confirmed with the DM (UC-only recommended)
- [ ] Branch built on current upstream `dev`, opened as **draft** (standing rule)
