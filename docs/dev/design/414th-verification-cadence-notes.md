# Verification cadence — the fly-card throttle

> **STATUS: PROPOSED 2026-08-06. Nothing built.** This note came out of a methods audit of
> the fork (methods, not bugs) whose headline finding was that the in-game-pass backlog has
> no governor: **127 outstanding rows** (87 untested / 29 partial / 11 regressed) against
> **114 verified**, with untested rows dating to 2026-07-01 and nothing in the process
> limiting new feature starts as a function of unflown ones.
>
> The obvious throttle — cap the build rate — is **rejected below**, because the data says
> the fork does not have a build-rate problem. It has a **scheduling** problem, and it
> already invented the fix and used it once.
>
> **Open calls for the DM are in the last section.** Part 1 is the only part that cannot be
> automated; if it does not get a date, the rest degrades into a better-labelled backlog and
> should not be built.

---

## The finding that reframes it

Verification here is **bimodal**, and the split is not random:

| Period | What existed to fly against | Rows verified |
|---|---|---|
| **2026-06-24 → 06-30** | Red Tide **M1** — a real scheduled event | **46** across 6 sessions (10 / 10 / 10 / 13 / 2 / 1) |
| **2026-07-01 → 07-31** | Nothing scheduled. The Aug-1 card was *written* 07-15 and never run | **17** across 7 sessions (1–5 each) |
| **2026-08-05** | The Aug-1 card finally got run, partially, alongside a DM review pass | **20 in one day** |

Five sessions account for **63 of the 114 verified rows**. Of the 13 rows on the Aug-1 card,
four flipped VERIFIED on 08-05 (**B14, B12, B13, A6**) — five days late and roughly a third
executed, and it was still the single largest verification event in the repo's history.

**Batch verification happens when, and only when, a scheduled fly exists to batch against.**
July's trickle is not fatigue or lack of discipline; it is the no-open-card state. A session
that flies opportunistically adjudicates 1–2 rows. A session that flies *a card* adjudicates
10–20. That is an order of magnitude, and it sits entirely on the verification side of the
ledger — which is why throttling the build is the wrong tool.

## The mechanism is already designed

`414th-feature-debt-register.md` (2026-07-15) contains the whole thing:

- **§3 — the pre-flight desk pass.** Load the miz, read the arming lines in `dcs.log`, read
  the ATO, read the map/SITREP. *"Anything that fails here fails before the squadron ever
  slots in — that is the point."*
- **§4 — the fly card.** A table of `row → how it gets exercised → what to watch for`, split
  into rows that ride the event **organically** and rows that need a pilot deliberately
  assigned. It also records what *cannot* ride that event and why (B16 needs modern LACM
  hulls; 1988 Red Tide has none).
- **§5 — the private-session card.** The rows needing contrived conditions no squadron event
  should host: the `[TEST] force capture` jam loop, the minefield persistence leg, the G23
  single-player pass-or-delete arbiter.

This is a good design. It was built as a **one-off for one event**, inside a document
explicitly framed as disposable (*"Archive once the Aug-1 wave is processed"*), so when the
event passed there was nothing left holding a cadence. Nothing owns the question *"what is
the next card and what is on it."*

**The proposal is not a new mechanism. It is making this one recurring, and giving it teeth.**

---

## The design

### Part 1 — the card is always open

There is **always exactly one open fly card**, and it has a **date**. It lives as its own
artifact under `docs/dev/flycards/` (`M3.md`, `M4.md`, …) rather than as a section inside a
register that ages out — that packaging is precisely why the last one evaporated.

A card carries what §4 already carries: the target campaign + turn, the settings/preseeds it
needs, the rows assigned, how each is exercised, what to watch for, and — importantly — the
rows deliberately **not** on it with the reason. Closed cards stay in the folder as the
verification record.

When a card is flown it closes and the next opens. New features queue into the open one.

This is the lever. Everything below exists to keep it from lapsing again.

### Part 2 — the admission rule (the actual throttle)

> **A feature does not ship default-ON, and is not preseeded into any campaign, until it is
> assigned to a fly card.**

The line is drawn there deliberately:

- **Default-OFF *and* unpreseeded** = genuinely dark. Nobody's game runs it, so it is harmless
  debt — and it is the fun half of building, which stays completely unrestricted. Build
  whatever you want, whenever.
- **Default-ON, or preseeded** = live in a real game, unverified. That is the half worth
  gating, and it is the half that has quietly accumulated: **18 of 44 feature gates default
  OFF pending a fly**, while others went ON or into a campaign without one.

The back-pressure is *felt* rather than prohibitive. Want the feature on? Put it on the card.
Card full? Schedule the next one, or accept it stays dark a while longer. That is a real cost
paid at the right moment, by the person who can pay it, without ever telling the DM they may
not build something.

Compliance cost is one token in the checklist row heading:

```
### B33 — Decoy suspected-activity zones · §79 · ☐ UNTESTED · card:M3
```

The session-start hook reads the **first** status marker on a heading line, so a trailing
`· card:M3` is parse-safe as written.

### Part 3 — aging forces a disposition

A row that goes **unassigned across 3 closed cards** forces a choice. There is no fourth
option and no "later":

| Disposition | Meaning |
|---|---|
| **Schedule** | Onto the open card. |
| **Accept** | `☑ SHIPPED UNVERIFIED (accepted YYYY-MM-DD)` — an explicit, dated risk decision. Not a failure state; some features are not worth an evening. |
| **Delete** | Remove the feature. |

The third is not a new move here — it is the fork's existing and genuinely good instinct,
generalised. G23 is already *"FROZEN, pass-or-delete"*. §57 minefields are shelved. Eleven
features have been removed outright with `do not restore` banners and save-compat tombstones.
What is missing is only the **trigger** that forces the question on a schedule instead of
when someone happens to notice.

The **Accept** state is the important addition, because it is what stops the backlog being a
guilt pile. A row sitting untested for five weeks is currently indistinguishable from one
nobody ever intends to fly. Making the second case *sayable* is most of the cleanup.

---

## Enforcement

Discipline alone will not hold this. The evidence is in the tree: *"one PR = one
feature/bugfix/change"* was formally adopted from upstream on 2026-07-20 and is already being
violated by multi-feature single-day landings. A rule that depends on remembering it will
lapse exactly the way the Aug-1 card lapsed.

**1. The session-start hook** (`.claude/hooks/session-start.sh`) already prints the status
board and is read at the top of every single session — it is the ideal surface, and it costs
nothing to extend:

```
=== 414th in-game-pass checklist ===
verified 114 | untested 87 | partial 29 | regressed 11 | closed 12

OPEN CARD: M3 — Red Tide, target 2026-08-14 — 9 rows assigned
UNASSIGNED: 78 rows
⚠ AGED OUT (3+ cards, need a disposition): B6 · B8 · C8 · G30 · S4
```

Three lines. The aged-out list is the whole enforcement mechanism for Part 3 — it makes the
question unavoidable without anyone having to remember to ask it.

**2. A CI test**, following the existing feature-registry precedent (a test already fails CI
when the registry, feature list, catalog and checklist drift apart):

> Every feature whose setting defaults **ON**, or that is **preseeded in a campaign yaml**,
> must have a checklist row that is `VERIFIED`, `SHIPPED UNVERIFIED (accepted)`, or
> card-assigned.

All four inputs are parseable and already parsed elsewhere: `game/fourteenth/features.py`
(feature → setting), `game/settings/settings.py` (defaults), the campaign yamls
(`tests/fourteenth/test_campaign_plugin_preseed.py` already walks these), and the checklist.
This is the mechanical half of Part 2, and it means the rule cannot silently lapse.

**3. Nothing else.** No new status board, no dashboard, no ceremony. The two surfaces above
are ones the repo already maintains.

---

## Rejected alternatives

**A WIP limit on new features** — *"no new §N while more than N rows are unflown."* This was
the obvious first answer and it is wrong three ways. (1) The data says build rate is not the
constraint — a scheduled card moves 10–20 rows regardless of how much was built between
cards. (2) It would block the **highest-value** work specifically: a large share of features
here are built *in response to* a flown finding (§81 off the Marianas Tacview, §49's fire-then-
scoot off the Scenic Route fly, §64 off the deck-jam report), and a WIP limit stops exactly
that. (3) It is a prohibition on a hobby project where the builder, the flyer and the
beneficiary are the same person — it would be ignored, and rules that get ignored corrode the
ones that shouldn't be.

**More default-OFF gating** — this is what produced the problem, not a fix for it. A
default-OFF gate on an unflown feature is a promissory note; 18 of them is a portfolio. The
2026-08-03 settings audit diagnosed this precisely (*"the settings surface is a mirror of the
in-game-pass backlog"*) and then treated the symptom by making the surface navigable rather
than shrinking what it mirrors.

**Headless/self-play verification to substitute for cockpit time** — already exhausted, and
the checklist header says so: *"the desk-adjudicable work is exhausted… don't re-run the test
sweep expecting a status flip."* There is also a standing caution against adjudicating
anything off fast-forwarded turns, since the §26 abstract resolver inverted M1's flown 34:0
air war. Headless probes de-risk a card; they cannot close a row.

**Archiving the backlog and starting clean** — loses the fail signatures, which are the most
valuable content in the checklist and the reason its findings are trustworthy.

---

## What this does not fix

Stated plainly, because a process change that oversells itself is worse than none:

- **It does not create cockpit time.** It multiplies the yield of the time that exists.
- **It does nothing for the 11 REGRESSED rows.** Those are concrete bugs with reproduced fail
  signatures, not unverified features; they belong in the ordinary work queue, not a card.
- **It does not fix silent no-ops.** A feature with four silent early-returns (§21's recovery
  surge, G31) is unfalsifiable on a card too. That is a separate finding from the same audit —
  *prefer a loud failure to a silent one* — now recorded as Rule 5 in the `414ret-reference`
  skill, and worth its own pass over the existing gates.
- **It does not survive a DM who does not date the cards.** See below.

---

## Open calls (DM)

1. **Cadence.** What is a realistic interval for an open card — every squadron event, monthly,
   or "whenever the next event is scheduled, whatever that turns out to be"? The design does
   not need a fixed period, only that the open card always carries **a date**. If the honest
   answer is "I can't commit to dates," say so — the right build then is Part 3 alone
   (aging + accept/delete), and Parts 1–2 should not be built.
2. **Aging threshold.** 3 closed cards is a guess. Could be 2, could be calendar-based
   (6 weeks). Wants a number you would actually act on rather than snooze.
3. **Seeding.** Card M3 has to be built from the current 78 unassigned rows. Group it by
   **campaign** (what one Red Tide evening burns down vs. one Marianas evening), or by
   **subsystem** (all the naval rows together)? Campaign-grouping is what the Aug-1 card did
   and what actually flew.
4. **Does the private-session card survive as a separate class?** §5 of the debt register
   distinguishes rows needing contrived conditions from rows that ride an event organically.
   That distinction earned its keep — worth keeping as a card *type*, or fold both into one
   card with a column?
5. **Is `SHIPPED UNVERIFIED (accepted)` acceptable at all?** It is a new status marker, and it
   means deliberately shipping something nobody watched. The alternative for a row nobody will
   ever fly is deletion. Some features are genuinely worth having unverified; the question is
   whether you want that sayable in the tracker or would rather the pressure stay on.

---

## Build order, if it goes ahead

1. `docs/dev/flycards/` + card M3 seeded from the unassigned rows (answers call 3 by doing it).
2. The `· card:MN` token + the checklist legend entry for `SHIPPED UNVERIFIED (accepted)`.
3. The session-start hook's three lines (Part 1 + Part 3 enforcement).
4. The CI test (Part 2 enforcement).

Steps 2–4 are small and mechanical. Step 1 is the one that carries the actual design decision,
and it is worth doing first precisely because seeing what one evening would really burn down
is the cheapest way to find out whether any of this is worth having.
