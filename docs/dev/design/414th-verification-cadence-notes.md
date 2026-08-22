# Verification cadence — the fly-card throttle

> **STATUS: PARTLY BUILT.** Proposed 2026-08-06. Built since: the **watch list**
> (`flycards/WATCH.md`), the **local card** (`flycards/LOCAL.md`) and the session-start
> hook that prints both (build order steps 1–2, and the first line of step 4). Still
> unbuilt: the `· card:` token, the aging/disposition pass (Part 3), the
> `SHIPPED UNVERIFIED (accepted)` state, and the Part 2 admission CI test. The counts
> quoted below are the 2026-08-06 figures and are now stale — as of 2026-08-22 the board
> reads 121 verified / 38 untested / 22 partial / 2 regressed, i.e. **62 outstanding**.
>
> This note came out of a methods audit of
> the fork (methods, not bugs) whose headline finding was that the in-game-pass backlog has
> no governor: **71 outstanding rows** (45 untested / 22 partial / 4 regressed) against
> **82 verified**, with untested rows dating to 2026-07-01 and nothing in the process
> limiting new feature starts as a function of unflown ones.
>
> The obvious throttle — cap the build rate — is **rejected below**, because the data says
> the fork does not have a build-rate problem. It has a **scheduling** problem, and it
> already invented the fix and used it once.
>
> **Open calls for the DM are in the last section.** Part 1 is the only part that cannot be
> automated; if it does not get a date, the rest degrades into a better-labelled backlog and
> should not be built.
>
> **CALL 1 RESOLVED 2026-08-06 (DM): "once a week for multiplayer events but I fly daily, we
> could really test every 2nd or third day locally."** This substantially revised the design.
> The note originally assumed cockpit time was the scarce, non-substitutable resource — it is
> not. There are **three** real cadences, not one, and the design now matches them (Part 1
> below). It also makes the backlog **tractable rather than permanent**: see "How long this
> actually takes".

---

## The finding that reframes it

Verification here is **bimodal**, and the split is not random:

| Period | What existed to fly against | Rows verified |
|---|---|---|
| **2026-06-24 → 06-30** | Red Tide **M1** — a real scheduled event | **42** across 6 sessions (9 / 9 / 10 / 12 / 2) |
| **2026-07-01 → 07-31** | Nothing scheduled. The Aug-1 card was *written* 07-15 and never run | **16** across 7 sessions (1–5 each) |
| **2026-08-05** | The Aug-1 card finally got run, partially, alongside a DM review pass | **20 in one day** |

Five sessions account for **60 of the 82 verified rows**. Of the 13 rows on the Aug-1 card,
four flipped VERIFIED on 08-05 (**B14, B12, B13, A6**) — five days late and roughly a third
executed, and it was still the single largest verification event in the repo's history.

> **Counting note — read before quoting any figure from this checklist.** Every number here is
> **heading-scoped, first-marker-wins**, i.e. `.claude/hooks/session-start.sh`'s method. A naive
> whole-file `grep` inflates badly, because the checklist's own conventions quote status markers
> constantly in prose (*"was ☐ UNTESTED, built …"*, *"was ✗ REGRESSED"*) — it reported
> 127 outstanding / 114 verified / 11 regressed against the true 71 / 82 / 4, and the first draft
> of this note shipped those inflated figures. The hook's header comment documents this trap
> explicitly and predates the mistake. **Use the hook, or scope to `^### ` and take the first
> marker.** The bimodal finding below was re-derived correctly and is unaffected.

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

### Part 1 — three cadences, three card types

The first draft of this note had **one** open card. That was wrong, and the DM's answer to
call 1 is why: there are three distinct rhythms here, they have different setup costs, and
they suit different kinds of row. Forcing them through one artifact would push contrived-
condition rows onto a squadron event (where they do not belong) and leave the daily flying —
by far the largest untapped resource — with nothing assigned to it at all.

| Cadence | Card | Setup cost | What belongs on it |
|---|---|---|---|
| **Daily** (flying anyway) | **Watch list** — 3–5 items, no card, no mission built | Zero | **Opportunistic rows**: things you would notice *if told to look*. Board numbers, a rear field launching to answer a front raid, an MIA appearing on the roster. |
| **Every 2–3 days** (local / solo) | **Local card** — the debt register's §5 pattern | Low; a scratch save is fine | **Contrived conditions** no squadron event should host: test toggles, deliberate setups, single-player arbiters, re-flies with specific plugin options. |
| **Weekly** (MP event) | **Event card** — the §4 pattern | High; needs pilots and a real campaign | Rows that **ride an event organically** plus the few worth assigning a pilot to deliberately. |

**Only the event card needs a date** — it already has one, because the event does. The local
card is a rolling queue that gets drawn from whenever an evening happens; the watch list is
standing. That removes the design's single biggest fragility: it no longer depends on the DM
committing to dates he does not already have.

Cards live as their own artifacts under `docs/dev/flycards/` (`E-2026-08-14.md`,
`L-004.md`, `WATCH.md`) rather than as sections inside a register framed as disposable — that
packaging is precisely why the last one evaporated. A card carries what §4 already carries:
target campaign + turn, the settings/preseeds it needs, the rows assigned, how each is
exercised, what to watch for, and the rows deliberately **not** on it with the reason. Closed
cards stay in the folder as the verification record.

**The watch list is the new idea and the cheapest win.** It is a standing 3–5 items, revised
whenever it empties, and it costs a glance. The Aug-1 card marked A5 and G29 *"Opportunistic"*
and then had nowhere to put them — so they sat, and both are still PARTIAL five weeks later.
A daily flight that already happened is the perfect vehicle for exactly that class of row, and
it currently verifies nothing because nothing has ever been assigned to it. Keep it short on
purpose: a watch list of twenty items is a watch list of zero.

**Row → card is a routing decision, made once, at merge.** The three types are what the
`· card:` token names.

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
### B33 — Decoy suspected-activity zones · §79 · ✅ CLOSED (feature removed 2026-08-18) · card:M3
```

The session-start hook reads the **first** status marker on a heading line, so a trailing
`· card:M3` is parse-safe as written.

### Part 3 — aging forces a disposition

A row that goes **unassigned for 3 weeks** forces a choice. There is no fourth option and no
"later".

*(Originally "3 closed cards". Recalibrated after call 1: with three cadences running, three
cards can close inside a single week, which would force dispositions faster than anyone would
act on them — and a threshold people snooze is worse than none. **3 weeks ≈ 3 event cycles**
is calendar-based, unambiguous across card types, and matches the rhythm the DM actually
described.)*

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

## How long this actually takes

Worth stating, because the whole tone of the backlog changes once call 1 is answered. The
note was written assuming cockpit time was scarce. It is not — the DM flies **daily**, with
~2–3 usable local test slots a week and a weekly MP event. That is capacity the fork has never
pointed at the checklist.

Against the flown evidence for what a card yields (June's scheduled sessions: 10–13 rows;
Aug 5: 20):

| Cadence | Realistic yield |
|---|---|
| Event card, ×1/week | 8–13 rows |
| Local card, ×2–3/week | 4–8 rows each |
| Watch list, continuous | 1–2 rows/week |

**≈15–25 rows/week if the cadence is actually run**, against 67 untested+partial rows. That
is roughly **3–5 weeks**, not a permanent condition.

Two honest deductions. **Not every row is reachable** — many need a specific campaign
(Marianas, DS91, Inherent Resolve, the COIN pair), so campaign-grouping is load-bearing rather
than cosmetic, and a row whose campaign is not in rotation will not close no matter how many
cards run. And **the 4 REGRESSED rows are not in this number at all** — they are bugs with
reproduced fail signatures and belong in the ordinary work queue.

Expect a **tail that does not close**: rows needing conditions that genuinely never arise.
That tail is what `SHIPPED UNVERIFIED (accepted)` and deletion exist for, and it is the real
argument for having those states.

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
verified 82 | untested 45 | partial 22 | regressed 4 | closed 12

WATCH (fly anything): B15 modex · A5 rear-field launch · G29 MIA appears
EVENT CARD 2026-08-14 (Red Tide): 9 rows    LOCAL QUEUE: 14 rows
UNASSIGNED: 78    ⚠ AGED 3wk, need a disposition: B6 · B8 · C8 · G30 · S4
```

Three lines, and the first one is the highest-value: **the watch list is in front of the DM
before every daily flight**, which is the entire mechanism for capturing opportunistic rows.
The aged-out list is the whole enforcement mechanism for Part 3 — it makes the question
unavoidable without anyone having to remember to ask it.

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
- **It does nothing for the 4 REGRESSED rows.** Those are concrete bugs with reproduced fail
  signatures, not unverified features; they belong in the ordinary work queue, not a card.
- **It does not fix silent no-ops.** A feature with four silent early-returns (§21's recovery
  surge, G31) is unfalsifiable on a card too. That is a separate finding from the same audit —
  *prefer a loud failure to a silent one* — now recorded as Rule 5 in the `414ret-reference`
  skill, and worth its own pass over the existing gates.
- **It does not survive a DM who does not date the cards.** See below.

---

## Open calls (DM)

1. ~~**Cadence.**~~ ✅ **RESOLVED 2026-08-06** — weekly MP event · daily solo flying · local
   testing every 2nd–3rd day. Drove the three-cadence rework of Part 1, the recalibrated aging
   threshold, and the "How long this actually takes" section. **The design's stated kill
   condition — "if cards don't get dates, build Part 3 alone" — no longer applies**: only the
   event card needs a date and it inherits one from the event.
2. ~~**Aging threshold.**~~ ✅ **Recalibrated to 3 weeks** (calendar, ≈3 event cycles) as a
   direct consequence of call 1 — with three cadences running, the original "3 closed cards"
   could elapse inside a week. Still wants a sanity check that 3 weeks is a number you would
   act on rather than snooze.
3. ~~**Does the private-session card survive as a separate class?**~~ ✅ **Yes, answered by
   call 1** — the §4/§5 distinction maps exactly onto the event/local split, and a third class
   (the watch list) fell out that neither the debt register nor the first draft had.
4. **Seeding — the live question.** The 71 outstanding rows now need routing to **three**
   destinations before any card is built. Within the event and local piles, group by
   **campaign** (what one Red Tide evening burns down vs. one Marianas evening) or by
   **subsystem** (all the naval rows together)? Campaign-grouping is what the Aug-1 card did
   and what actually flew — but with 2–3 local cards a week, subsystem-grouping becomes
   affordable in a way it was not when there was one card a month.
5. **Is `SHIPPED UNVERIFIED (accepted)` acceptable at all?** Still open, and call 1 cuts both
   ways. Higher capacity means fewer rows genuinely need it — but "How long this actually
   takes" also makes the **tail** explicit: rows whose conditions never arise will not close
   at any cadence. The alternative for those is deletion. The question is whether you want
   "shipped, nobody watched, accepted" sayable in the tracker, or would rather the pressure
   stay on and force delete-or-fly.

---

## Build order, if it goes ahead

1. **`WATCH.md` first — it is the cheapest thing here and the only one that pays out
   tomorrow.** 3–5 opportunistic rows, no mission built, no setup. The DM is flying daily
   regardless; this costs a glance and starts converting flights that currently verify nothing.
   Everything else can wait behind it.
2. `docs/dev/flycards/` + the first **event card** (dated off the next MP event) and the
   **local queue**, seeded by routing the 71 outstanding rows across the three types — which
   answers call 4 by doing it.
3. The `· card:` token + the checklist legend entry for `SHIPPED UNVERIFIED (accepted)`.
4. The session-start hook's three lines (Parts 1 + 3 enforcement).
5. The CI test (Part 2 enforcement).

Steps 3–5 are small and mechanical. Step 1 is deliberately first: it is a single short file,
it needs no decision from anyone, and it tests the whole premise — if a standing watch list
does not convert daily flights into closed rows within a week or two, the rest of this design
is unlikely to be worth building either.

---

## Board defects found and fixed 2026-08-22

The board had been briefing closed work as outstanding. Two independent parsing bugs, both in
`.claude/hooks/session-start.sh`, and the same root shape in each: **crossing something off did
not take it off the board.**

**1. Six closed checklist rows were listed as outstanding.** The hook matched a fixed list of
whole markers (`☑ VERIFIED|☐ UNTESTED|◐ PARTIAL|✗ REGRESSED|⊘ RETIRED|✖ REMOVED`). `✅ CLOSED`
and `☒ CLOSED` were both invented after the hook was written and were in neither the list nor
the Status legend. A row marked `✅ CLOSED` therefore matched nothing on its marker, and
first-marker-wins fell through to the `(was ☐ UNTESTED` that the checklist's own convention
makes every re-marked row quote. B33, G2, S1, S6, B49 and B53 were briefed as pending flights,
and inflated the counts by 4 untested and 2 partial.

**2. Both fly-card items on the LOCAL card were closed items.** The card parser read every
`### ` heading in the file, including the ones under `## Done`. `G29` was taken off the card on
2026-08-20 and `B25`'s follow-on closed the same day; the board asked for both on 2026-08-22.
The card was correct and the board contradicted it. WATCH escaped only because it files closed
items in `ARCHIVE.md` rather than in a section of its own.

**3. A section heading was counted as a verified row.** The scope was `^#{2,3} `, so
`## E. SOF insert generation · #85 · ☑ VERIFIED` counted once as a row.

**4. The at-a-glance table disagreed with four row headings** — B63, S1, S6, B53. Two of them
showed a closed feature as outstanding.

**5. The WATCH parking lot named two rows that had already closed** — `Q3`, VERIFIED, and a
loadout watch pointing at `B42`, RETIRED. This is the failure the card's own "check the row
before you add an item" rule already warned about.

**What changed.** The hook now matches a `<symbol> <WORD>` **pair** rather than fixed strings,
so a newly invented symbol degrades to a legend failure in CI instead of silently unmarking a
row; it scopes rows to `^### `; and the card parser reads only live sections, skipping
`Done`/`Archive`/`Dropped`/`Parking` and any item whose own heading says it is closed. An empty
card now prints as empty rather than vanishing. The Status legend gained the two marks it was
missing (`✖ REMOVED`, `✅ CLOSED`), `C7`'s `☒` and `G12`'s `✗ RETIRED` were normalised onto it,
and the four table cells were corrected to match their headings.

**The guard is `tests/test_flycard_board.py`.** Each of its six checks was verified to fail
against the defect it targets before the fix was kept. It pins: every row heading carries a
legend-listed mark; the table agrees with the headings; the stated outstanding count matches
the headings; no closed item sits in a live card section; every card item names a checklist row
that is still open; and WATCH respects its five-slot cap.

**The lesson, and it is the note's own.** A verification surface that is not itself verified
decays toward telling you to do work you have already done. The board is the only artifact
that routes cockpit time, so its being wrong costs flights — which is the resource this whole
design exists to protect.

## Writing a WATCH item (moved off the card 2026-08-17)

These rules used to sit at the top of `WATCH.md`. They are instructions for whoever *maintains*
the card, not for the person about to fly, and 33 lines of them stood between the DM and the
two-item list underneath. The card now opens on the list.

- **The heading IS the item.** The session-start hook prints *only* the `### ` line and the
  `**Try:**` paragraph — never the rest of the body. So the heading has to state, in plain
  words, the thing you would see out the window or on screen. A row ID, a section number or a
  meta-label is not a description: "The opportunistic pair — `A5` (§1) · `G29` (§21)" told the
  reader nothing and came back marked "?" for exactly that reason (2026-08-06). Nobody looks up
  a feature number to find out what they are supposed to be looking at. Keep the short row tag
  at the end so a result files to the right checklist row; drop the `§N`.
- **A `**Try:**` line is for COCKPIT work only** (DM call, 2026-08-06: *"drop the Try line from
  anything not in the cockpit — stuff we can figure out in the UI shouldn't need it"*). It
  earns that space only when the check needs you **in DCS**: an in-jet procedure, a laser code,
  a thing to watch in the sim, a way to force an otherwise opportunistic event. If the item
  resolves in the Retribution UI — frag a flight, generate a turn, open a panel, read a
  kneeboard — it gets a plain `**Where:**` line instead, which the hook does not print.
  Explaining ordinary app usage to the person who built the app is noise. Wrap a Try across
  source lines freely; the hook joins it and ends it at the first blank line.
- **Five items, hard cap.** A watch list of twenty is a watch list of zero. The cap is a
  ceiling, not a quota — a short list that gets looked at beats five that do not.
- **No setup.** Anything needing a test toggle, a specific campaign or a contrived condition
  belongs on `LOCAL.md`.
- **Seeing it once is enough**, and the result goes in the checklist row the same session with
  the date.
- **Cross it off the moment it closes.** `G32` was recorded VERIFIED in the checklist on
  2026-08-16 and still occupied slot 1 the next day, so the hook kept asking the DM for a
  result that already existed. The archive exists so crossing off costs nothing.
- **A verdict reached in conversation is not recorded until it is in the row.** This is the
  same failure as above wearing a different hat, and it has now happened twice. `B55` was
  *computed* from a flown `.miz` on 2026-08-17, reported to the DM in full, and never written
  down — so it went onto the card as an open item hours after it was settled, and the DM had
  to say "this watch card is wrong". If you work out a verdict, write the row in the same
  reply, before you move on. Analysis that lives only in chat scrollback is analysis nobody
  can find next week.
- **Check the row before you add an item.** Refilling the card from the outstanding list means
  trusting the checklist; if the checklist is stale the card inherits the staleness. Cheap
  guard: `grep "^| <ROW> " docs/dev/414th-ingame-pass-checklist.md` before promoting anything.
- **Not every item needs a flight.** `I2` was closed on 2026-08-17 out of Tacview recordings
  already on disk — 52 civil tracks, cruise levels and descent-rate-versus-groundspeed — after
  sitting on the card as an in-sim question. Before adding an item, ask whether an existing
  recording already answers it.
