# 414Ret - 414th Joint Fighter Group's DCS Retribution Fork

This repository is the **414th Joint Fighter Group's customized build of
[DCS Retribution](https://github.com/dcs-retribution/dcs-retribution)** - a turn-based
dynamic campaign generator for [DCS World](https://www.digitalcombatsimulator.com/en/products/world/).

It is a squadron-focused build of upstream Retribution (`dev` branch), combining the
414th's campaign, mission, and quality-of-life work with selected newer upstream fixes
and backports. The unmodified upstream project README is preserved as
[`README.upstream.md`](README.upstream.md).

> **For AI assistants / other Claude sessions:** read [`CLAUDE.md`](CLAUDE.md) first.
> It is the engineering handoff doc - architecture, where each feature lives, the
> branch layout, and what is still in flight.

---

## What's different from upstream

414Ret is not a collection of reskins or a single extra aircraft pack. It changes how a
Retribution campaign is planned, understood, and flown by a multiplayer squadron. The
current build starts from upstream `dev` at `dce851ea`, then adds the 414th feature set
and selected later upstream fixes.

### Intelligence is incomplete — and recon has a purpose

- Enemy sites can be known without their exact composition, strength, damage state, or
  threat rings being known. Attacking or scouting a site reveals it; confirmed battle
  damage can require a surviving recon pass.
- **TARPS** is a real player task for F-14s, supported by the **TARS** film-and-debrief
  system. What the aircraft photographs is carried back into the campaign as confirmed
  intelligence.
- When you need the ground truth anyway — debugging a campaign, planning the opposing side,
  or just checking the real laydown — tick **Reveal fog of war (overview)** in the map's layer
  panel (top-right, with the other enemy-intel toggles). It turns the fog off and shows the
  true picture: full enemy composition, threat rings, and otherwise-hidden command posts. It is
  a view toggle only — it never changes the campaign and is never saved.
- The **map layer panel** is a single grouped, collapsible control (dark-themed to match the
  app) with one-click **preset views** — Default, SEAD, Recon, Clean — and it remembers your
  layer choices between sessions.
- An optional **Approximate target area** mode removes perfect player coordinates and
  offsets steerpoints, making visual acquisition, talk-ons, and reconnaissance matter.
  Against mobile SAMs, DEAD and SEAD flights get a single fuzzed target-area waypoint
  instead of a precise steerpoint per launcher/radar; Strike keeps exact per-target
  points since buildings don't move. DEAD kneeboards always trade exact coordinates
  for a rough bullseye cue (bearing and range to ~1 NM) while still listing each
  target's steerpoint number.
- Mobile short-range defenses are kept off player datalinks while larger SAM sites remain
  available for deliberate SEAD/DEAD planning.

### Missions are built for squadron play

- **SCAR** adds a player-led moving-target hunt: identify the real HVT among decoys and
  clutter, then stop it before it reaches safety or, for a SCUD, reaches its launch point.
  Prosecuting the wrong convoy is a mis-identification that costs budget (tunable via the
  `SCAR mis-ID penalty` Campaign Doctrine setting; set 0 to disable), so reading the target
  signature matters — it's printed on your SCAR kneeboard, and the on-scene controller's
  calls go to your flight (and the C-130 King), not the whole coalition. Real armor and missile
  sites can become the moving objective instead of a
  disposable scripted stand-in. An experimental option (on by default for new campaigns while it is
  being playtested) uses finite purchased SOF teams to
  capture a commander alive: a C-130 inserts the team ahead of the fleeing HVT, a clean grab
  reveals enemy command posts (the team escapes with the hostage), and a botched grab strands
  the team as a "downed SOF team" objective you can fly a **helo CSAR recovery** against on a
  later turn before it is overrun. An opt-in `SCAR auto-planning` setting can frag a SCAR hunt
  into your ATO automatically each turn (off by default while the in-mission scripting is being
  playtested).
- **Combat SAR** makes a downed pilot worth flying for. A CH-47 orbits near the front as the
  rescuer while a C-130 holds overhead as the HC-130 "King" — on-scene command with an
  air-tracking TACAN the helo homes on (an AI King lights it automatically; a player King
  sets it from the planned channel in-cockpit) and an F10 survivor-locator readout. When a human pilot
  ejects, they spawn with a beacon; recover them and deliver them to any friendly field and the
  campaign **spares the aviator** (you still lose the jet, but the experienced pilot returns to
  the squadron instead of being lost). Player-flown, with an optional AI standing alert. It is a
  separate task from the SCAR SOF-recovery CSAR above.
- **JAMMING** turns the C-130J into an EC-130H/RC-130H-style EW and ISR platform with
  standoff jamming and ELINT gameplay. This is the only 414th scripted EW model;
  the old generic fighter-pod "EW Jammer Script" is retired.
- Strike and DEAD packages can receive auto-planned **TARPS** follow-up, while BAI remains
  the normal planner task for conventional anti-armor work.
- The fork also carries newer suppression behavior: AI SEAD can loiter near the target,
  react to emitters, and break off on a computed timeline instead of making a single
  inflexible pass.
- The auto-planner no longer sends strikers through a SAM belt it only *intends* to clear:
  if a planned DEAD can't actually reach a SAM shielded behind another live radar threat, the
  strike that depends on it is held back until the belt is genuinely down, instead of bombers
  being tasked into defenses that are still alive.

### The air war behaves like a campaign, not a queue of isolated sorties

- Squadrons can hold aircraft in a **QRA intercept reserve** for runtime base defense.
- BARCAP coverage uses overlapping, jittered, threat-weighted waves and a more useful
  forward defensive line. Quiet sectors retain baseline coverage; contested sectors gain
  more.
- Transit routes treat the active ground battle as a hazard, reducing the tendency for
  unrelated AI flights to loiter over the FLOT.
- AWACS and tanker racetracks are anchored on the front line and stand off into friendly
  airspace, so support orbits sit centered behind the fighting at a sane distance instead of
  being flung far off-axis or pinned onto a home airfield.
- An optional **auto-planner unpredictability** doctrine knob (per side, off by default)
  varies which offensive targets the enemy services first, so red stops striking the same
  targets in the same order every turn. Its reactive air defenses stay just as sharp.
- Doctrine controls expose patrol-altitude floors and scatter, and the aircraft task
  priorities have received a conservative role-based rebalance.
- Soviet/Russian air defenses use improved legacy SAM layouts and radar composition.
  Campaign-map SAM rings, emitters, routes, and IADS links are easier to inspect and read.

### The generated mission feels occupied

- **Troops In Contact (TIC)** produces prolonged, formation-aware frontline firefights
  with ambient suppressive fire instead of letting vanilla ground AI instantly erase the
  battle.
- Frontline formations are distributed along the line rather than piled onto one patch of
  terrain.
- Civilian regional traffic adds light rear-area activity, while the 414th-tuned
  **Splash Damage 3** build improves weapon effects without returning to the plugin's
  harsher stock values.
- **Nation-specific voiceovers per squadron** — each squadron's aircraft fly under their own
  country, so a mixed-nation coalition hears each unit's real national radio voice instead of
  one shared faction voice. Single-nation factions are unaffected.

### Planning and debriefing expose the information crews need

- Ground targets have an intel panel showing known strength, mission suitability, ranges,
  IADS membership, visibility, and capture/purchase state.
- Package and flight dialogs show task, TOT, player slots, departure bases, squadron fit,
  available aircraft, and target distance without making planners hunt across windows.
- The map provides clearer SAM, route, emitter, and IADS interaction; waypoint altitude
  editing supports practical bulk changes.
- Debriefing begins with mission impact — territorial changes, runway damage, and losses —
  before the full event detail.
- Kneeboards are restyled to use the page: clean headings with underline rules and spacing
  (no wasted bottom-half), and the Friendly Packages list flows into two columns when long.
- **Custom kneeboards** can be imported from the *Kneeboards* toolbar button — add an image
  once and it's injected into every flight's kneeboard (or scoped to one airframe), stored in
  the campaign save, instead of hand-editing each mission.
- An optional **Threat Intel Brief** kneeboard page is the enemy air-defense dossier, one card
  per system — guidance, engagement ceiling, MEZ, HARM code, bullseye cues, live/dead counts, and
  a **how-to-defeat** note — like a campaign intelligence briefing. It respects recon fog: sites
  you haven't identified show only their threat tier ("Unidentified MERAD") until you fly a TARPS
  overflight. Off by default.
- Optional **mission code words** (Red Flag style) — the whole side shares one randomised,
  themed table: a **push word per task** (STRIKE / SEAD / OCA / CAS / …) plus SUCCESS / ABORT, so
  one call ("Red Kite") tells everyone SEAD is pushing. Planners see the full table *before*
  generating the mission — a **persistent panel** in the package list, a tooltip, and a
  `PUSH <word>` tag on the join waypoint — to build a briefing. A **Comms & Brevity** kneeboard
  page carries the table (your task marked) plus a brevity crib filtered to your task. Fresh words
  every turn, stable while you plan. Off by default.
- Plugin settings explain what each system does and use squadron-readable labels and units.

### Additional 414th content and integrations

- The **CurrentHill Iran** integration adds Shahed-136 and IRGCN FAC assets plus a dedicated
  `[CH] Iran 2020` faction behind a new-game mod toggle.
- The **settings screen** was audited end-to-end: dead and duplicate options were removed,
  the two AI-radio toggles were merged into a single **AI wingman radio behavior** choice
  (Normal / Suppress contact reports / Radio silence), and many labels were clarified.
  Existing campaigns migrate automatically on load.
- A new **Germany - Red Tide** campaign — a *Red Storm Rising*-flavoured 1988 NATO
  counteroffensive, built for the 414th. The Warsaw Pact opened the war by overrunning the
  Fulda Gap, taking Hamburg, and seizing Copenhagen — but the Soviet thrust has culminated,
  and the 414th now spearheads the push to retake the lost ground. A Soviet Baltic fleet and
  the captured Copenhagen field open a northern over-water front, and the enemy IADS is
  thickened with S-300 and SA-11. Every squadron is now a named historical unit wearing a
  matching livery — real GSFG/VVS regiments on the red side, 414th Joint Fighter Group
  identities (VMF-29, Voodoo, the 414th TFS, JFG Hornets) on the blue — so the air war no
  longer spawns mismatched paint schemes. **Fulda** is now a blue forward helicopter FARP in
  the Gap (Apaches, Kiowas, Hueys) with the front line routed through it, and Frankfurt adds a
  KC-135MPRS drogue tanker. The *Crossing the Rubicon* campaign it forks from
  is left untouched. See
  [`docs/dev/design/414th-red-tide-campaign-notes.md`](docs/dev/design/414th-red-tide-campaign-notes.md).
- A **drop-spawn** sandbox tool lets you right-click blank map space to place a unit group
  (ground force, SAM, EWR, ship, or coastal/missile site) attached to the nearest friendly
  command post, with optional deploy-next-turn timing and respawn; right-click a unit you
  placed to remove it. It is gated behind two cheat settings (unlock placement, and an
  optional free-placement mode that skips the budget cost), and respects terrain and a
  range limit from the nearest CP.
- Numerous mission-generation and debriefing fixes are included, along with selected
  upstream backports newer than the fork's original base.

Most campaign-facing systems have their own setting or plugin toggle. The experimental SCAR
commander-capture/SOF campaign mechanics are on by default for new campaigns while they are
being playtested (toggle `SCAR command-post intel` on the Campaign Doctrine page to turn them
off); existing campaigns keep whatever they were saved with.

For engineering details, implementation paths, defaults, and known limitations, see
[`docs/dev/414th-features.md`](docs/dev/414th-features.md).

---

## Download / Latest build

Pre-built `.exe` releases are published automatically every time `main` is updated.
No GitHub account needed — just grab the zip and run.

**[Download latest build](https://github.com/bradyccox/414Ret/releases/tag/latest)**

1. Download `414th-retribution-latest.zip` from the link above.
2. Extract anywhere.
3. Run `retribution_main.exe`.
4. Point it at your DCS World install on first launch.

> The `latest` release is a rolling pre-release that always reflects the current `main`
> branch. For pinned campaign builds, use versioned releases (tagged `v1.x.x`) if
> available.

---

## Running it (from source)

Same as upstream Retribution. Quick start (Windows, PowerShell):

```powershell
.\scripts\bootstrap-env.ps1
.\scripts\check-env.ps1
.\venv\Scripts\python.exe -m qt_ui.main
```

You need a working DCS World install and the MOOSE-dependent features assume the
bundled mission plugins under `resources/plugins/` are present. See
[`README.upstream.md`](README.upstream.md) for the full upstream setup, dependencies,
and wiki links.

### Windows environment sanity

This repo is sensitive to Python drift on Windows. If `.venv` was created from a Python
install that later moved, was removed, or lost execute permissions, all repo-local
commands will start failing in the same confusing way for humans and assistants.

Use these two scripts from the repo root:

```powershell
.\scripts\bootstrap-env.ps1  # find Python 3.11, recreate .venv, install requirements
.\scripts\check-env.ps1      # verify Python, venv, and Git LFS auth health
```

`check-env.ps1` also warns when Git LFS is unauthenticated, which is a common cause of
GitHub push/upload failures for repos with LFS-tracked content.

### Dev checks (must pass before pushing)

```powershell
.venv\Scripts\python.exe -m black --check .      # formatting
.venv\Scripts\python.exe -m mypy game tests       # type checking (CI only checks game + tests)
.venv\Scripts\python.exe -m pytest tests -q       # unit tests
```

---

## Relationship to the 414th workspace

The 414th also maintains a separate **mission-building workspace** (campaign plans,
`.miz` files, and any Mission-Editor-loaded scripts not yet integrated here, such as
the standalone MANTIS IADS). That workspace is private.

Features that started as standalone ME scripts and are now fully integrated into this
repo (do not use the standalone versions):
- **C-130J EW/ISR** → `resources/plugins/c130j/` (`FlightType.JAMMING`)
  - Supersedes the retired generic `ewrj` / "EW Jammer Script"; do not use that
    standalone script for F-16/A-10 pod jamming.
- **QRA / AI_A2A_DISPATCHER** → `resources/plugins/intercept/` (per-squadron `intercept_reserve`)
- **TARS recon** → `resources/plugins/tars/` (runtime engine for `FlightType.TARPS`)

This repo is the **engine-level** side: capabilities planned and spawned automatically
by the campaign generator rather than hand-placed in the Mission Editor.

---

## License & credit

DCS Retribution is licensed under the LGPL (see [`LICENSE`](LICENSE)). All upstream
authorship and the project's history are preserved. The 414th additions are provided
under the same terms. Upstream project: <https://github.com/dcs-retribution/dcs-retribution>.
