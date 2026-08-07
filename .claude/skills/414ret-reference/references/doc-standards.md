# Brady's Document Standards

Which format to use, decided by destination:

| Destination | Format | Rules |
|---|---|---|
| Wiki page or PR description | Markdown | Ready to paste directly. GitHub-flavored Markdown tables. No HTML unless the wiki page already uses it. |
| Reference material (specs, lookup docs) | Word (.docx) | Clean and **table-first**: if information can be a table, it is a table. Minimal prose between tables. |
| Mission briefings / handoffs | Word (.docx) | Follow the `TheFinalOption_MissionHandoff.docx` template (see below) |
| Edits to an existing formatting-sensitive file (PowerPoint especially, also polished Word docs) | **Change document** | NEVER edit the file directly. Produce a document listing each change: location (slide/section), current text, replacement text, and any formatting notes. Brady applies the edits himself. |

## Mission briefing template (TheFinalOption_MissionHandoff.docx standard)

- Numbered sections (1, 1.1, 1.2, 2, ...)
- Table-first formatting throughout
- DCS mission editor naming conventions for all units, groups, waypoints, and triggers — names in the doc must match what would be typed into the editor exactly
- Phased build checklists with checkboxes for anything that gets built in the editor
- Military brevity: short declarative sentences, standard brevity terms, no filler

## Change document format

```
CHANGE DOCUMENT — <file name>
Date: <date>    Prepared for: Brady

| # | Location | Current | Change to | Notes |
|---|----------|---------|-----------|-------|
| 1 | Slide 4, title | "..." | "..." | keep existing font/size |
| 2 | Sect 2.1, para 2 | "..." | "..." | |
```

One row per change. Quote the current text exactly so it's findable. Never bundle multiple edits in one row.

## General style

- Bullets and tables over paragraphs in all deliverables
- No decorative formatting — bold only for genuine emphasis or table headers
- DCS terminology is never dumbed down; GitHub terminology always is
