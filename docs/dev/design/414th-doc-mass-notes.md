# 414th — documentation mass (scoping, not built)

Status: **scoping only.** Nothing here is cut yet. Written 2026-08-19.

## The problem, measured

| | |
|---|---|
| All tracked docs | **~447,000 words** |
| `docs/dev/design/` notes | **84 files** |
| `414th-features.md` | **104,231 words**, 92 sections |
| Commits touching `414th-features.md` in 60 days | **379** (~6/day — the most-edited file in the repo) |
| Doc files one feature change had to touch (§3 rework, 2026-08-18) | **16**, against 40 code files |

That last ratio is the cost. A 0.4 doc-file-per-code-file tax on every change, paid by
someone who has to find all 16, is why docs drift — and drift is worse than length, because
a doc describing removed behaviour actively misleads.

## Where the mass is

`414th-features.md`, broken down:

| | Words | Sections |
|---|---|---|
| Live feature sections | 88,285 | 70 |
| **Tombstones** (REMOVED / RETIRED / REVERTED / SHELVED) | **12,389** | 18 |
| **Not a feature at all** (work logs) | **3,557** | 4 |

The top 12 sections are **40% of the file**. The largest:

- **§8 "Robustness / crash fixes" — 6,988 words, 30 flat bullets, zero sub-headings.** Some
  bullets run past 150 words. This is not a feature; it is a changelog with no index.
- §28 Settings IA — 4,608
- §4 UI transparency — 4,480
- §6 Air-defense planning — 3,853, and the feature is **reverted**
- "Unit-coverage sweep — 2026-08-04" — 2,482, a session work log
- §15 SCAR — 2,292, and it was **removed 2026-08-07**

## The three cuts, cheapest first

**1. Delete the work logs — 3,557 words, zero risk.**

"Unit-coverage sweep — 2026-08-04", "Code audit fixes — 2026-07-07" and two siblings are
session records. Git already has them, with better fidelity. They are not features and no
`§N` refers to them.

**2. Compress the tombstones — 12,389 → ~2,000.**

A removed feature needs four things: what it was, when it went, why, and **the constraint
that must not be re-broken**. It does not need its implementation history. §15 does not need
2,292 words to say "removed 2026-08-07, replaced by upstream #929, and the blue-only rule is
dead."

⚠️ **The constraint line is the whole point of keeping a tombstone.** CLAUDE.md's own rule —
*"Compress a constraint comment, never delete it"* — governs here. The hard-constraints list
exists because those cost missions to learn. Every tombstone gets read for a "never restore
this, because…" before a word is cut, and that sentence survives verbatim.

**3. Split §8 — 6,988 words that are not one feature.**

30 unrelated bug fixes under one heading. Triage each into one of three buckets:

- carries a hard constraint (the helo CFIT cluster, the carrier-recovery stagger) → its own
  numbered entry, or a line in the hard-constraints list
- has a checklist row → one line pointing at the row
- neither → delete; git has it

## What must not be lost

- Every **hard constraint**. They are the reason this file is worth its size.
- Every **flown-test finding**. "The squadron's read of the flown result" is knowledge no
  test carries and no rerun recovers.
- Every **`§N` anchor**. Old notes, saves and commit messages reference them; numbering stays
  stable and removed features keep their number as a tombstone.

## What must not happen

- **Do not "tidy" a section you have not read end to end.** The compressible-looking prose is
  where the flown findings hide.
- **Do not move history into the design notes wholesale.** There are already 84 of them; the
  goal is less total surface, not the same surface relocated. History that no longer changes a
  decision goes to git.
- **Do not touch in-fiction campaign material.** Briefing packs and role cards are exempt from
  the plain-writing standard by convention, and from this.

## Making it stick

Cutting once is worth ~16k words; the file grows 6 commits a day, so without a guard it comes
back. Two candidates, both mechanical:

1. **A CI check on the fork's own stated conventions** — fail on a bullet over ~60 words, or a
   section over ~1,200 words with no sub-headings. CLAUDE.md already says *"One fact per line…
   Long paragraphs are the failure mode — nobody reads a 120-word bullet."* Nothing enforces it.
2. **A stated split rule**: `414th-features.md` describes what is true **now**; the design note
   carries how it got there. Also already the convention, also unenforced.

The check is the cheaper of the two and would have caught §8 at bullet three.

## Expected result

~104k → ~85k words on the first pass, without losing a constraint or a flown finding, and a
guard that keeps the shape. The 16-files-per-change tax is a separate problem — it comes from
84 design notes plus README plus CLAUDE.md plus AGENTS.md plus the wiki all restating the same
feature, and it is worth its own pass once this one lands.

## See also

- [CLAUDE.md](../../../CLAUDE.md) — Conventions: the plain-writing standard this enforces
- [414th-features.md](../414th-features.md) — the subject
