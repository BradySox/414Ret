# DCS module manuals

English-language manuals copied out of the local DCS install. Vendor PDFs — local reference
only, never source. The PDFs are gitignored (~843 MB); this README and the per-folder
`INDEX.md` page maps are tracked.

Non-English copies (CN/DE/FR/RU/ES/IT) were skipped. They are still in the DCS install.

## Finding something

Each folder has an **`INDEX.md`** mapping sections to page ranges. Read that first, then
extract only that range — these run to 1,129 pages, so opening one blind does not work.

Extract with `pdftotext`:

```bash
pdftotext -f 63 -l 73 "references/manuals/Supercarrier/DCS Supercarrier Operations Guide EN.pdf" -
```

`-f` is the first page, `-l` the last, trailing `-` writes to stdout.

**The Read tool cannot open these PDFs on this machine.** It renders pages as images via
`pdftoppm`, which is not installed — it fails with "pdftoppm is not installed". `pdftotext`
is present. Use Read only if you need to see a diagram and poppler has since been installed.

Page numbers in every `INDEX.md` are **1-based physical PDF pages**. They may not match the
printed page numbers; no offset is needed either way.

The `dcs-aircraft-manuals` skill (`.claude/skills/`) wraps this and covers when the manuals
are and are not the right source.

## Inventory

| Folder | Files | Size |
|---|---|---|
| `AH-64D/` | DCS AH-64D Flight Manual EN.pdf | 52 MB |
| `C-130J/` | DCS C-130J User Manual.pdf | 14 MB |
| `CH-47F/` | DCS CH-47F Early Access Guide EN.pdf | 11 MB |
| `F-4E/` | F-4E Manual.pdf, Chucks Guide.pdf | 214 MB |
| `F-14/` | F-14 Manual.pdf, Chucks Guide.pdf | 181 MB |
| `F-14B(U)/` | Gulf Guardian briefing pack, CVW-17 Marianas + NTTR briefing packs | 15 MB |
| `F-15C/` | F-15C DCS Flaming Cliffs Flight Manual EN.pdf | 12 MB |
| `F-15E/` | F-15E Manual EN ver 1.7.pdf, Be Afraid of the Dark Part 1.pdf | 217 MB |
| `F-16C/` | DCS F-16C Early Access Guide EN.pdf | 53 MB |
| `FA-18C/` | DCS FA-18C Early Access Guide EN.pdf | 22 MB |
| `Supercarrier/` | DCS Supercarrier Operations Guide EN.pdf | 24 MB |
| `UH-1H/` | Flight Manual EN, QuickStart Guide EN, KeyCommands EN, Multi-Crew Quick Guide, `manual_en/` in-game manual | 34 MB |

12 folders, 17 PDFs, 7,349 pages.

## Source paths

Most modules ship as `Mods/aircraft/<module>/Doc`. The exceptions:

| Folder here | Source |
|---|---|
| `C-130J/` | `Mods/aircraft/C130J/docs` |
| `F-14/` | `Mods/aircraft/F14/Docs` |
| `F-14B(U)/` | `Mods/aircraft/F14BU/Docs` |
| `UH-1H/` | `Mods/aircraft/Uh-1H/Doc` |
| `Supercarrier/` | `Mods/tech/Supercarrier/Doc` — **not** under `aircraft/` |

## Re-pulling after a DCS update

DCS overwrites these on module patches. To refresh, re-copy from the install:

```bash
cp "/e/DCS World/Mods/aircraft/F-16C/Doc/DCS F-16C Early Access Guide EN.pdf" references/manuals/F-16C/
```

`F-14B(U)` and `UH-1H/manual_en` are directory copies rather than single files.

If a page range looks wrong after an update the manual was revised — regenerate the index
rather than trusting stale ranges. The generator is not vendored; it needs `pypdf`, which is
deliberately not a project dependency. Install it to a scratchpad target, walk each PDF's
outline, and emit top-level sections plus one level of subsections with 1-based page ranges.
