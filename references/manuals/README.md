# Aircraft module manuals

English-language manuals copied out of the local DCS install
(`E:\DCS World\Mods\aircraft\<module>\Doc`). Vendor PDFs — local reference only, never
source. The PDFs are gitignored (~820 MB); this README and the per-module `INDEX.md`
page maps are tracked.

Non-English copies (CN/DE/FR/RU/ES/IT) were skipped. They are still in the DCS install.

## Finding something

Each module folder has an **`INDEX.md`** mapping sections to page ranges. Read that first,
then read the PDF with a `pages` range — these run to 1,129 pages and the Read tool caps at
20 pages per call, so opening one blind does not work.

Page numbers in every `INDEX.md` are **1-based physical PDF pages**, ready for the Read
tool's `pages` parameter. They do not match the printed page numbers; no offset needed.

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
| `UH-1H/` | Flight Manual EN, QuickStart Guide EN, KeyCommands EN, Multi-Crew Quick Guide, `manual_en/` in-game manual | 34 MB |

Source folder names differ from the folders here: the C-130J ships as `C130J/docs`,
the F-14 as `F14/Docs`, the F-14B(U) as `F14BU/Docs`, the UH-1H as `Uh-1H/Doc`. Every
other module uses `<module>/Doc`.

## Re-pulling after a DCS update

DCS overwrites these on module patches. To refresh, re-copy from the install — for
example:

```bash
cp "/e/DCS World/Mods/aircraft/F-16C/Doc/DCS F-16C Early Access Guide EN.pdf" references/manuals/F-16C/
```

`F-14B(U)` and `UH-1H/manual_en` are directory copies rather than single files.
