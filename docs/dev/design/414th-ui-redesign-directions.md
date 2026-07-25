# 414th UI redesign — three directions (DECISION PENDING)

**Status:** design only, nothing landed. Three directions are offered for the DM to react to;
no code has been changed. The rendered version of this note — with live HTML mockups of all
three directions — is `414th-ui-redesign-mockups.html` alongside this file (open it in a
browser; it is self-contained).

**Why now:** every UI change the fork has made so far has been a *repair* — the §28 settings
IA reorg, the §19 map-layers panel, the §18 fog toggle, the web-map colour tracks, the
`screenfit.py` dialog clamp. Each was correct in isolation and none of them changed how the
application reads, because there is no design system underneath them to change. This note asks
for a direction instead of another patch.

---

## The surface being redesigned

Measured from the working tree, not remembered.

| | Qt desktop | Web client |
|---|---|---|
| Distinct screens & panels | ~90 | 7 chrome + ~30 map layers |
| Dialog classes (`QDialog` subclasses) | 36 | 0 — it defers to Qt |
| Tab sets | 8 | 0 |
| Editable controls | **439** | 40 layer toggles |
| Lines of UI code | 22,507 | 6,987 |

The 439 = 214 metadata-driven settings fields (7 pages / 41 sections) + 217 plugin options
(25 flat group boxes on one scrolling page) + 8 cheat toggles.

Full per-screen inventory is in the HTML note. The short version by area: startup 4 · main
window 9 · top panel 9 · ATO sidebar 3 · package planning 4 · edit flight 11 · base menus 9 ·
ground objects 3 · air wing 10 · New Game wizard 7 · settings 10 · reference windows 11 ·
small dialogs 8 · modal prompts 20+.

---

## What is actually wrong

Seven findings, each verifiable in the tree:

1. **Everything is a modal over the map.** 36 dialog classes. A right-click on the *web* map
   POSTs `/qt/create-package/…` so the *Qt* app can throw a modal over the top — so editing a
   flight hides the map you were reading it against.
2. **Four competing navigation systems.** A menubar, three toolbars, a button row in the top
   panel, and the ATO tree. Settings is in a toolbar; Air Wing is in the top panel; base
   details are map-click-only.
3. **No hierarchy.** Discord / Github / Ukraine are a peer toolbar to campaign actions, and
   "Take off" — the one control that generates and launches the mission — is one grey gradient
   button among sixteen identical ones.
4. **Dialogs never fit real screens.** `qt_ui/screenfit.py` is an app-wide event filter that
   shrinks and repositions *every* dialog on show, because only 2 of 34 ever consulted
   `availableGeometry`. That is a workaround for an unsized layout system.
5. **Hardcoded styling in two unrelated palettes.** Qt: 711 lines of literal hex and gradients,
   no variables, 139 fixed `px` rules that fight DPI scaling. Web: no custom properties outside
   `mapColors.ts` — seven near-identical greys, two different border colours for the same role,
   four base font sizes.
6. **The web client has no layout, only corners.** Its root element has zero CSS rules; ribbon,
   events feed, legend and layers panel are absolutely positioned into four corners and kept
   apart by magic numbers plus one hand-bumped z-index. Zero media queries in the whole client.
7. **Deleted features are still styled.** `CampaignStatusBar.css` is 386 lines, ~2/3 of it
   styling the removed §55 posture chip and §40 campaign-phase panel. The browser tab still
   reads "React Redux App".

Plus: three files under `qt_ui/` are empty stubs, and `QLiberationWindow` still carries the
map-display-toggle machinery that moved to the web client years ago.

---

## Direction 1 — "Sortie" (restyle)

Keep the architecture exactly. Replace the 711-line stylesheet and the web client's scattered
hexes with **one token file** (colour, spacing, type scale, radius, elevation) from which the
Qt QSS is generated and the web CSS is written.

- Effort: small · Risk: very low · Ceiling: modern, still 2016-shaped.
- Fixes: one visual language across both halves; gradients/greys/type scales gone; DPI scaling
  stops fighting `px`; a real primary action; **settings search over all 439 controls**; all 36
  dialogs improve without being touched individually.
- Does not fix: modality, the four navigation systems, the 217-option plugin page, the wizard
  embedding the whole settings dialog (cheats included), desktop-only.

Coverage: shell → one toolbar + hierarchical status strip (social links to Help); all 36
dialogs inherit the generated QSS with a shared header/footer applied to the ten most-used;
settings keep their tree and gain search; web map re-themed from the same tokens with the dead
CSS deleted.

## Direction 2 — "Command Deck" (restructure)

Kill modality. The map stays on screen; selection drives a **persistent right-hand inspector**,
and a **left mode rail** (Map / ATO / Wing / Intel / Logistics / Setup) replaces the
toolbar-menubar-statusbutton scramble.

- Effort: large but staged · Risk: moderate · Ceiling: feels like a 2026 planning tool.
- Fixes: never lose the map to edit something on it; one inspector replaces the dialog zoo;
  dialogs stop needing the global clamp because they stop being dialogs; the log and events feed
  get real space.
- Costs: re-parenting each dialog into a panel widget; a selection/context system; the payload
  editor is too wide for an inspector and likely stays a window; muscle-memory change.

Delivery is **incremental** — the inspector can host one converted dialog at a time and
everything unconverted keeps opening as a modal. No big-bang cutover.

| Surface today | Becomes |
|---|---|
| Base menu (Airfield Command, Ground Forces HQ, Intel, Departing Convoys) | Inspector, four sections |
| Edit flight (General, Payload, Waypoints, DTC) | Inspector, four sections (payload may stay a window) |
| TGO info, unit info, buy/replace | Inspector |
| Package dialog | Inspector, opened by map right-click |
| Air Wing, squadron, wing config | **Wing** mode |
| Stats, finances, intel, info log, events | **Intel** mode |
| Transfers, pending transfers, convoys | **Logistics** mode |
| Settings, plugins, plugin options, preferences, kneeboards, notes | **Setup** mode |
| ATO panel | **ATO** mode + the persistent left list |
| New Game wizard, debrief, callsign/TACAN/ICLS/radio pickers, confirms | **stay modal** |

Roughly 9 of 36 stay dialogs; everything else becomes a panel or a page.

## Direction 3 — "Single Surface" (replatform)

The React client becomes the whole interface; Qt keeps the window and the file dialogs.

The codebase has been drifting this way for two years without a decision: the map, layers
panel, campaign ribbon, SITREP, victory checklist, events feed, minefield and downed-pilot
overlays are all already web-side; the server publishes the game as JSON over HTTP and pushes
deltas over a WebSocket; an unused Electron wrapper (`client/main.js`) already exists. What is
missing is only the **write** half.

- Effort: largest · Risk: high · Ceiling: highest, and where the code already points.
- Uniquely buys: planning on a **second monitor, laptop or tablet** while DCS holds the main
  display, and the squadron being able to open the campaign map during a brief.
- Also: retires ~22,500 lines of Qt UI over time; every future feature is built once, not twice.
- Costs: the write API (packages, flights, purchases, transfers, settings) does not exist; the
  payload editor is genuinely hard (real pylon data, per airframe); the New Game wizard and
  faction editor are large rebuilds; longest road to first visible improvement; two UIs coexist
  during the transition.

Migration order that keeps the app usable throughout:

1. Design system + the four existing web panels — no API work, ships immediately
2. Intel: stats, finances, info log, events, debrief — read-only, data already exposed
3. Setup: settings, plugins, preferences — one generic write endpoint covers all 439 controls
4. ATO + package/flight editing — the first real write API, biggest daily payoff
5. Air wing, logistics, base menus — purchases and transfers
6. Payload editor, New Game wizard — hardest last; Qt keeps them until ready

---

## They are not exclusive

Direction 1 is a prerequisite for both others — the token system is the same work either way.
2 and 3 are the real fork, and they differ mostly in *where* the inspector gets built: Qt or
React. **Steps 1–3 of Direction 3 are the same work as Direction 1 plus read-only pages**, so
starting there defers the 2-vs-3 choice with the design system already paid for.

| If you want… | Do this |
|---|---|
| A visibly better app soon, near-zero risk | Direction 1, then reassess |
| The biggest change to how planning *feels*, staying on Qt | 1 → 2 |
| To end the two-application problem for good | 1 → 3 steps 2–6 |

---

## Open questions for the DM

1. Which mockup did you want to keep looking at? First reaction, ignoring cost.
2. Is losing the map behind a dialog actually annoying, or have you stopped noticing? If it
   doesn't bother you, Direction 2's premise is wrong and should be dropped now.
3. Does planning on a second screen or tablet matter? That is the only thing Direction 3
   uniquely buys, and it is expensive.
4. The three palettes are deliberately different (warm dark / cold dark / light). Any wrong on
   sight? Cheap to change now, expensive later.
5. Anything here worth actively defending — the ATO sidebar, the toolbar, the current colours?
   Better to know before redesigning around it.
