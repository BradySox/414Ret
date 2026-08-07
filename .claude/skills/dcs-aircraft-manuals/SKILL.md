---
name: dcs-aircraft-manuals
description: Locate and read the official DCS manuals held locally for 11 aircraft modules (AH-64D, C-130J, CH-47F, F-4E, F-14, F-14B(U), F-15C, F-15E, F-16C, FA-18C, UH-1H) plus the Supercarrier Operations Guide, including both Chuck's Guides. Use when a question needs the manual's own words about an aircraft's systems, cockpit controls, avionics pages, HOTAS, radar or sensor modes, weapon employment, startup or emergency procedure, or performance limits — or about carrier operations: Case I/II/III departure and recovery, the marshal stack, the groove, LSO and IFLOLS, catapult and launch-bar procedure, deck handling and deck crew. Also use when authoring briefing packs, kneeboard pages, role cards or campaign documents that describe how a jet is actually flown or how the boat is actually worked. Read the INDEX.md, then extract only that page range.
---

# DCS manuals

Vendor PDFs for 11 aircraft modules plus the Supercarrier, copied from the local DCS
install. 7,349 pages. Each folder carries an `INDEX.md` mapping sections to physical page
ranges so a lookup is a targeted extract, not a sweep.

Root: `references/manuals/`

## The one rule

**Read `INDEX.md` first. Then extract only the pages it points at.**

These files run to 1,129 pages. Opening one without the index burns the context window and
usually misses the section anyway.

```
1. Read references/manuals/<MODULE>/INDEX.md
2. Find the section; note its page range
3. Extract that range as text
```

**Extract with `pdftotext`, not the Read tool.** The Read tool renders PDF pages as images
via `pdftoppm`, which is not installed on the 414th's machine — it fails with
"pdftoppm is not installed". `pdftotext` is present and text is cheaper anyway:

```bash
pdftotext -f 63 -l 73 "references/manuals/Supercarrier/DCS Supercarrier Operations Guide EN.pdf" -
```

`-f` is the first page, `-l` the last, and the trailing `-` writes to stdout. Reach for the
Read tool only when you actually need to *see* a diagram or cockpit illustration, and expect
it to fail unless poppler has since been installed.

Page numbers in every `INDEX.md` are **1-based physical PDF pages**. They may not match the
manual's printed page numbers — do not add or subtract an offset. (In the Supercarrier guide
the two happen to align exactly; in most of the others they do not.)

## What is where

| Module | Folder | Manual(s) | Pages |
|---|---|---|---|
| AH-64D Apache | `AH-64D/` | Flight Manual EN | 687 |
| C-130J Hercules | `C-130J/` | User Manual | 357 |
| CH-47F Chinook | `CH-47F/` | Early Access Guide EN | 156 |
| F-4E Phantom II | `F-4E/` | Manual · Chuck's Guide | 1129 · 936 |
| F-14A/B Tomcat | `F-14/` | Manual · Chuck's Guide | 1156 · 572 |
| F-14B(U) | `F-14B(U)/` | briefing packs only — no manual | — |
| F-15C Eagle | `F-15C/` | Flaming Cliffs Flight Manual EN | 149 |
| F-15E Strike Eagle | `F-15E/` | Manual EN 1.7 · Be Afraid of the Dark Pt 1 | 595 · 97 |
| F-16C Viper | `F-16C/` | Early Access Guide EN | 704 |
| F/A-18C Hornet | `FA-18C/` | Early Access Guide EN | 424 |
| UH-1H Huey | `UH-1H/` | Flight Manual EN · QuickStart · KeyCommands · Multi-Crew | 204 · 52 · 11 · 10 |
| Supercarrier | `Supercarrier/` | Operations Guide EN | 110 |

The **F-14B(U)** has no manual of its own — its folder holds the Gulf Guardian and CVW-17
briefing packs. For B(U) systems questions use the `F-14/` manual.

The **Supercarrier** guide is not an airframe manual — it is the boat. It covers Case I/II/III
departure and recovery, the marshal stack, catapult and launch-bar procedure, deck crew
signals, the LSO station and IFLOLS, and the Mission Editor's carrier features. It is the
right source for carrier-ops procedure in briefings and kneeboards, and useful background for
the fork's carrier work (deck spawn policy, carrier comms curation, deck decorations).
Its source folder is `Mods/tech/Supercarrier/Doc`, not `Mods/aircraft/`.

## What these are NOT the source of truth for

This matters more than it sounds. For campaign-generator work the manuals are the wrong
source, and reaching for them produces plausible wrong answers:

- **Loadouts and pylon legality** — the module's own payload Lua and the built-in fits are
  authoritative. Manuals describe intent, not what the sim accepts.
- **Weapon availability and dates** — CLSIDs and the weapon-date tables.
- **Unit stats, ranges, detection** — the pydcs export from the live install.
- **Anything the sim models differently from the real aircraft** — early-access guides in
  particular document planned behavior that may not be implemented.

Use the manuals for **procedure, systems behavior and cockpit description**: what a page
does, what a switch is for, how a mode is entered, how a weapon is employed. That is what
briefing and kneeboard material needs.

## Gotchas

- **The PDFs are gitignored.** Only `INDEX.md` and `README.md` are tracked. On a checkout
  without a local DCS install the indexes are still readable but the PDFs are absent — say
  so rather than reporting a read failure as a missing section. `references/manuals/README.md`
  carries the re-pull instructions.
- **DCS overwrites these on module patches.** If a page range looks wrong after an update,
  the manual was revised — regenerate the index rather than trusting stale ranges.
- **Chuck's Guides are slide decks.** Their bookmark titles carry chapter prefixes (`2 - AWG-9
  Radar`) that do not appear on the slide itself, and headings are set as graphics. The page
  ranges are correct; do not expect the index title to match the page text verbatim.
- **Subsections are listed only for sections of 12+ pages**, capped at 40 per parent. For a
  fine-grained target inside a long chapter, read the chapter's first page — it usually
  carries the chapter's own contents list.
- **Two manuals have no bookmarks** (UH-1H Flight Manual, Be Afraid of the Dark). Their
  indexes were built by matching the printed table of contents against body text, verified
  page-by-page.
- **The Supercarrier PDF has a malformed xref and an incremental update.** Some readers
  report it as 243 pages. It is **110** — its own `/Count`, the raw page-object count, its
  printed pagination, and `pdftotext` all agree, and the last page is numbered 110. Ignore a
  243 anywhere.
- **`MISSION EDITOR FEATURS`** on Supercarrier p94 is ED's typo, not a bad page reference.

## Regenerating an index

The generator is not vendored — it needs `pypdf`, which is deliberately not a project
dependency. Install it to a scratchpad target rather than the project venv, walk each PDF's
outline, and emit top-level sections plus one level of subsections with 1-based page ranges.
For bookmark-less PDFs, parse the front-matter table of contents and locate each heading in
the body text to recover its true physical page.
