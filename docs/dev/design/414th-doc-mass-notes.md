# 414th — documentation mass

`414th-features.md` was 104,332 words across 91 sections, edited 379 times in 60 days — the
most-churned file in the repo. Trimmed to **95,819** on 2026-08-19. All 91 sections and every
`§N` anchor survive.

## What was cut

| Section | Was | Now |
|---|---|---|
| §15 SCAR (removed feature) | 2,292 | 125 |
| Unit-coverage sweep | 2,482 | 339 |
| §46 route-aware fuel (reverted) | 2,302 | 896 |
| §57 minefields (shelved) | 933 | 118 |
| Code audit fixes | 842 | 210 |
| §84 stock attrition (removed) | 658 | 138 |
| §21 Combat SAR (removed) | 588 | 52 |
| §53 / §54 / §55 | 218 | 83 |

Two sections were **restructured, not cut** — the problem there was navigation, not length:

- **§8 robustness** — 30 flat bullets, no headings, 6,988 words. Regrouped under 9 subsystem
  headings. 30 bullets in, 30 out; the only added words are the headings.
- **§4 UI transparency** — 4,480 words, no headings. Three headings *inserted*, nothing moved.
  §4 has narrative order, unlike §8's unrelated bug list.

## The rule that governed it

A removed feature needs four things and no more: what it was, when it went, why, and **the
constraint that must not be re-broken**. Implementation detail for code that no longer exists
is git's job.

Everything extracted rather than deleted:

- `runway_is_operational()` whitelists carrier hulls by type — **a carrier missing from it
  reads as SUNK** the moment a campaign bases on it.
- pydcs saves miz countries **sorted by name**, and the layout loader anchors on the first unit
  of the first matched group. A vehicle group under the statics' country steals the template
  origin and shifts every authored building cluster on every campaign.
- Layout `unit_types` entries name unit **ids**, not pydcs classes. A class name resolves to
  None, the group empties, the site raises `LayoutException`, and nothing else signals it.
- `control_point.captured` is the `Player` enum and is **always truthy** — `"BLUE" if captured
  else "RED"` labels everything BLUE.
- §50 ambient convoys **skim, never commission**. Free seeding is right for the §35 Vietnam
  trail and wrong to generalise — it was adding ~48 free ground units a turn, game-wide.
- §37 Super Gaggle is **losses-only**: "absent from the kill list" is "delivered" *or* "never
  spawned", indistinguishable without a runtime signal the plugin does not emit.
- §55 Red Intent already tried the obvious "make red smarter" shape. Read seam 7 of
  `414th-retribution-long-view.md` before proposing another.

## One mistake worth recording

The first attempt cut §15 by replacing everything between its heading and §20's — and silently
destroyed §16, §17, §18 and "Still in flight / deferred", which sit between them. Caught by a
word count that dropped further than the section was worth.

The fix is mechanical: replace a section by finding **the next `## ` heading, whatever it is**,
and assert the heading list is unchanged afterwards. Do not assume two `§N` are adjacent.

## Still walls (over 1,200 words, no sub-headings)

§72 carrier deck decorations (2,511) · §86 GPS jamming (2,091) · §74 DTC (2,011) · §77 escort
jamming (1,968) · §70 COMINT (1,744) · §58 briefing popup (1,245).

Best done by whoever next edits that feature — they already have the section loaded. A CI check
on section length is worth adding once they are done, and not before: it would block every PR on
day one.

## The separate problem

One feature change touched **16 doc files against 40 code files** (the §3 rework, 2026-08-18).
That comes from 84 design notes plus README plus CLAUDE.md plus AGENTS.md plus the wiki all
restating the same feature. Not addressed here, not scoped.
