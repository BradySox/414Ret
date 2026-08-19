# 414th — documentation mass

Written 2026-08-19 as a scoping note proposing a ~19,000-word cut. **The cut does not
exist.** Reading the sections disproved the scope. This note is kept as the record of what
was actually found, because the wrong conclusion is easy to reach again from the same
numbers.

## What the measurements said

| | |
|---|---|
| All tracked docs | ~447,000 words |
| `414th-features.md` | 104,231 words, 92 sections |
| Commits touching it in 60 days | 379 (~6/day — the most-edited file in the repo) |
| Doc files one feature change touched (§3 rework, 2026-08-18) | 16, against 40 code files |
| Tombstone sections (REMOVED / RETIRED / REVERTED / SHELVED) | 12,389 words, 18 sections |
| Sections that are not a numbered feature | 3,557 words, 4 sections |

The inference was: ~16,000 of those words describe things that no longer exist, so they can
go. That inference was **structural** — it read heading patterns and word counts, never the
prose.

## What reading them found

Every candidate held something recorded nowhere else.

- **"Unit-coverage sweep — 2026-08-04"** (2,482 words) is not a work log. It is the runbook
  for `tools/audit_unit_coverage.py`, plus three landmines closed on the way (the
  `runway_is_operational()` carrier-hull whitelist among them), plus a deliberate,
  documented semantics change to §51 — comms-jam now transmits from every C2 building.
- **"Code audit fixes — 2026-07-07"** (842 words) says in its own preamble that each entry
  "brings the code to what its feature section already documents". True of the first half.
  The **second half is three design decisions** — §50 ambient convoys skim rather than
  commission free units, §37 Super Gaggle is losses-only because "delivered" is
  indistinguishable from "never spawned", §15's Sandy divert stays frozen pending a re-fly.
  Those exist here and nowhere else.
- **§15 SCAR** (2,292 words) is already correctly shaped: a REMOVED banner, an explicit
  "kept because" line, and the history folded into a `<details>` block. Somebody already did
  this compression.
- **§6 and §46** (3,853 + 2,302) are **partial** reverts, not tombstones. Live behaviour is
  documented inside them — §6's overlap waves and orbit-band fix, §46's external-fuel
  accounting helpers. Cutting them by their banner would have deleted current behaviour.
- The remaining 15 tombstones share ~3,900 words — about 260 each. Already terse.

**The file is long because it is dense, not because it is padded.** 93 features, each with
its flown findings and the constraints those cost. That is what it is for.

## The real problem, and it is not length

Navigation. Ten sections ran past 1,200 words with **zero** sub-headings — about 24,000
words with no way in but reading top to bottom. The fork's own convention already forbids
the shape: *"One fact per line… Long paragraphs are the failure mode — nobody reads a
120-word bullet."* Nothing enforced it.

**Done 2026-08-19:**

- **§8 "Robustness / crash fixes"** — 30 flat bullets, no headings, 6,988 words. Regrouped
  under 9 subsystem headings (flight plans, refuelling, support orbits, carrier deck,
  helicopters, loadouts, ground movement, campaign robustness, debrief). Verified 30 bullets
  in, 30 out; the only words added are the headings.
- **§4 "UI transparency"** — 4,480 words, no headings. Three headings **inserted** (map and
  dialog panels / flight altitude editing / kneeboards). Nothing moved: unlike §8's unrelated
  bug list, §4 has narrative order and reordering it would have been destructive.

**Still walls, worst first:** §72 carrier deck decorations (2,511) · unit-coverage sweep
(2,482) · §86 GPS jamming (2,091) · §74 DTC (2,011) · §77 escort jamming (1,968) · §70
COMINT (1,744) · §58 briefing popup (1,245).

These are mechanical and safe, and each is best done by whoever next edits that feature —
they already have the section loaded. A big-bang pass buys nothing a gradual one does not.

## The guard, if the shape is to hold

A CI check on the fork's own stated conventions — fail on a section past ~1,200 words with
no sub-headings. It cannot land until the seven above are fixed, or it blocks every PR on
day one. Worth doing at that point, because 6 commits a day will otherwise rebuild the walls.

## What must never be cut

Restated because the numbers make the opposite look attractive:

- Every **hard constraint**. They are why the file is worth its size.
- Every **flown-test finding**. No test carries them and no rerun recovers them.
- Every **`§N` anchor**. Old notes, saves and commits reference them; removed features keep
  their number as a tombstone.
- **Do not tidy a section you have not read end to end.** That is the mistake this note
  records.

## The separate problem

The 16-doc-files-per-change tax is real and is *not* addressed by any of the above. It comes
from 84 design notes plus README plus CLAUDE.md plus AGENTS.md plus the wiki restating the
same feature. That is its own pass and has not been scoped.

## See also

- [CLAUDE.md](../../../CLAUDE.md) — Conventions: the plain-writing standard
- [414th-features.md](../414th-features.md) — the subject
