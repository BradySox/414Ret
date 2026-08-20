# CH-47F — manual page index

Page numbers are **1-based physical PDF pages**. They may not match the
printed page numbers.

Extract a section as text:

```bash
pdftotext -f 63 -l 73 "references/manuals/CH-47F/<file>.pdf" -
```

The Read tool renders PDF pages as images via `pdftoppm`, which is often not
installed; `pdftotext` is, and text is cheaper. If Read does work, the same
numbers go in its `pages` parameter.

PDFs live in this folder and are gitignored. See [README.md](../README.md).

## DCS CH-47F Early Access Guide EN.pdf

156 pages · index source: 197 PDF bookmarks

| Section | Pages | Len |
|---|---|---|
| Introduction | 2–2 | 1 |
| Table of Contents | 3–5 | 3 |
| Latest Changes | 6–6 | 1 |
| DCS FUNDAMENTALS | 7–19 | 13 |
| &nbsp;&nbsp;· Health Warning! | 8–8 | 1 |
| &nbsp;&nbsp;· Installation and Launch | 9–18 | 10 |
| &nbsp;&nbsp;· Flight Control | 19–19 | 1 |
| THE CH-47F | 20–74 | 55 |
| &nbsp;&nbsp;· Aircraft History | 21–28 | 8 |
| &nbsp;&nbsp;· Cockpit Overview | 29–55 | 27 |
| &nbsp;&nbsp;· Cyclic, Thrust Control Lever, & MFCU Hand Controls | 56–61 | 6 |
| &nbsp;&nbsp;· Multi-Function Displays (MFD) | 62–67 | 6 |
| &nbsp;&nbsp;· Control Display Unit (CDU) | 68–73 | 6 |
| &nbsp;&nbsp;· Digital Advanced Flight Control System (DAFCS) | 74–74 | 1 |
| PROCEDURES | 75–95 | 21 |
| &nbsp;&nbsp;· Aircraft Start | 77–84 | 8 |
| &nbsp;&nbsp;· Taxi | 85–86 | 2 |
| &nbsp;&nbsp;· Takeoff | 87–89 | 3 |
| &nbsp;&nbsp;· Landing | 90–92 | 3 |
| &nbsp;&nbsp;· Aircraft Shutdown | 93–95 | 3 |
| NAVIGATION | 96–114 | 19 |
| &nbsp;&nbsp;· Mission Database | 97–101 | 5 |
| &nbsp;&nbsp;· Flight Plans | 102–114 | 13 |
| TRANSPORT OPERATIONS | 115–123 | 9 |
| AIRCRAFT SURVIVABILITY EQUIPMENT (ASE) | 124–133 | 10 |
| “BOB" AI | 134–136 | 3 |
| APPENDICES | 137–156 | 20 |
| &nbsp;&nbsp;· Appendix A – Abbreviated Checklists | 138–147 | 10 |
| &nbsp;&nbsp;· Appendix B – RWR Threat Symbols | 148–149 | 2 |
| &nbsp;&nbsp;· Appendix E – Glossary of Terms | 150–154 | 5 |
| &nbsp;&nbsp;· Appendix F – Formulas | 155–156 | 2 |
