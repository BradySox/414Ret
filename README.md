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

414Ret isn't a reskin or an aircraft pack. It changes how a Retribution campaign is
planned, understood, and flown by a multiplayer squadron. It starts from upstream `dev`
at `dce851ea`, then adds the 414th feature set and selected later upstream fixes.

Highlights below. **Many of these are opt-in** — the full feature list, with each toggle,
its default, and known limitations, is in
[`docs/dev/414th-features.md`](docs/dev/414th-features.md).

### Intelligence is incomplete — and recon has a purpose

Upstream hands you a map that already knows everything. Here you have to go look.

- **You know a site is there, not what's in it.** Composition, strength, damage and threat
  rings stay unknown until you scout or attack it.
- **Unscouted field forces have no exact position** — a mobile SAM shows as a dashed amber
  *suspected activity* circle offset from the truth, until recon or an attack pins it down.
  Fixed infrastructure stays exact. The Weasel hunt becomes a real hunt.
- **Mobile missiles shoot and scoot**, relocating mid-mission — so the launcher is never
  where the last photo froze it. They stay within a few km of their campaign position, and
  the radar SAM network never moves.
- **TARPS is a real player task**, flown by F-14s and the period photo birds (RF-101B,
  RA-5C). What you photograph becomes confirmed intelligence.
- Plus: **Approximate target area** mode, mobile SAMs kept off player datalinks, a
  *Reveal fog of war* toggle for when you need ground truth, and a DCS-accurate terrain
  chart as the base map.

### Missions are built for squadron play

- **Combat SAR makes a downed pilot worth flying for.** Recover an ejected aviator and the
  campaign **spares the pilot** — you still lose the jet. The AI plans the package (King +
  helo + Sandy) by default, any human can fly any seat, and AI ejections count too. Lose the
  race and the enemy's **snatch party** takes them: a **POW** leaves your roster and drains
  political will every turn held. Retake the field in time and they're back — a few turns on
  a normal campaign, indefinitely on a political-will one, where a negotiated victory brings
  them home. A pilot neither rescued nor captured goes **MIA and keeps evading**, still
  rescuable next mission — but deep behind the lines they're almost certainly caught. Think
  twice before pressing deep with no rescue plan. **Every downed aviator shows on the
  campaign map**: an MIA evader as a rescue-orange marker at their last known position, a
  POW as a gray marker at the holding field — so you plan the rescue from the map, not
  from a kneeboard note.
- **A downed pilot triggers a recovery surge.** The very next turn opens with a coordinated
  "drop everything" rescue package **already airborne at the evader's position** — rescue
  helo, King, Sandys, fighter cover — because a helo spooling up at a rear field never gets
  there in time. One surge per downed pilot; if it fails, the normal rescue paths carry on.
- **SCAR is the RESCAP "Sandy"** of that package — hold near the FLOT with the King and the
  rescue helo, suppress the threats, walk the helo in.
- **JAMMING** turns the C-130J into an EC-130H/RC-130H-style EW and ISR platform.
- **Every generated mission is archived** — a named, dated copy lands in a folder DCS's own
  browser lists, so last week's turn re-opens straight from the game.

### The air war behaves like a campaign, not a queue of isolated sorties

- **QRA intercept reserve** holds fighters for base defense — and you can **man part of it**,
  scrambling from cold alert when the *"raid inbound"* call comes.
- **Support orbits are painted on the F10 map** — a cyan racetrack and label for every tanker
  and AWACS, so you can find your gas in flight. No DTC, no cartridge.
- **Fuel first: tanks are fitted for the sortie, then the tanker passes are decided.** A jet
  short of gas gets drop tanks; the tanker decision counts the fuel in them, so jets stop
  double-tanking sorties their real load covers. The Payload tab shows burn, passes and RTB
  margin live as you edit.
- **One HARM no longer kills a SAM site** — batteries field two guidance radars, spaced so
  one missile can't take both, so real SEAD takes a follow-up shot. Applies to new campaigns.
- **One continuous clock.** Time marches a few hours per turn and weather **evolves** from
  the turn before — fronts roll in and clear over several turns, instead of a thunderstorm
  one sortie and clear skies the next. (With day-and-night missions; a day-only campaign
  keeps the old rotation.)
- **The planner reads that weather.** In rain or storms the automatic photo-recon add-ons
  stay home (cameras photograph cloud deck), and a thunderstorm pushes low-level CAS and
  BAI to the back of the plan so the all-weather strikes claim the jets first.
- **SEAD opens the window, then the strikes push.** Strike packages headed into a defended
  area are timed just behind the SEAD servicing that SAM — several packages massing behind
  one suppressor — instead of wandering in half an hour early. Fly the SEAD yourself and
  the AI push forms up behind *you*.
- Plus: threat-weighted BARCAP waves, front-anchored support orbits, weighted (not
  coin-flip) off-mission combat, and per-side auto-planner unpredictability.

### The generated mission feels occupied

- **Troops In Contact** produces prolonged, formation-aware frontline firefights instead of
  vanilla ground AI erasing the battle in a minute.
- **The roads have traffic — and your convoys can be ambushed.** On any map with roads
  between same-side bases, real supply columns run both networks; sometimes hidden ambush
  teams dig in along a friendly route. Nothing is telegraphed — the first sign is the TROOPS
  IN CONTACT call.
- **Nation-specific voiceovers and pilot names per squadron** — a Greek squadron hears Greek
  and fills with Greek names, instead of one shared faction voice.
- **The carrier reads like a real boat** — TACAN matching the hull with a boat ident
  (Roosevelt 71X TRO, Stennis 74X STN), stable channels, the ship's real name. Learn Mother's
  card once; it holds all campaign (if a map's own beacon owns the hull channel, the boat
  takes the nearest free one). **Navy jets wear real squadron modexes** to match — each
  squadron gets its own block and numbers its jets in sequence. **And the deck is alive** —
  tow tractors, a crash truck, deck hands along the island and the LSO team on the platform
  (deck dressing from the Operation Cerberus North 2 campaign, rotating each turn), placed
  so every parking spot and catapult stays usable. An optional extra dresses the recovery
  corridor during the launch cycle — an alert E-2 on the stern round-down, gear and hands
  by the LSO platform — and the deck crew strikes it all below before recovery, so the
  wires are always clear when you come home.
- Plus: mixed frontline combat clusters, civilian traffic, and the 414th-tuned Splash Damage 3.

### Planning and debriefing expose the information crews need

- **The kneeboard is the classic deck**, with the 414th's additions folded into it rather than
  bolted on. **Mission Info opens on a BLUF**: task, target, TOT, code words, a compact air +
  SAM threat picture, your loadout in one line, and the SAR if-down drill. The **fuel ladder
  rides in the flight plan**, with the RTB margin called out — and it charges the whole
  sortie, including the on-station orbit: a CAP's racetrack row shows the patrol speed to
  fly, and an endurance call-out says how long the gas actually holds the station ("On
  station 45 min planned; fuel supports ~50 min before bingo").
- **A "last turn" SITREP** — both sides' losses (the enemy's as *claimed*), bases taken or
  lost, pilots recovered.
- **A Threat Intel Brief** page is the enemy air-defense dossier: one card per system with
  guidance, ceiling, MEZ, HARM code and a how-to-defeat note. It respects recon fog —
  unidentified sites show only their threat tier until you fly the overflight.
- **Mission code words** (Red Flag style), visible to planners *before* generation and on your
  kneeboard in the cockpit.
- **Set a loadout once and every future flight gets it.** Build the fit you want in the
  payload editor and hit **Set as default for &lt;task&gt;** — from then on every flight of that
  airframe planned for that task is generated carrying it, in this campaign and the next,
  until you clear it. The same box already remembers your fuel and cockpit settings per
  airframe.
- Plus: target intel panels, impact-first debriefs, custom kneeboard import, and era-gated
  cockpit options (no JHMCS in 1968).

### Systems that make the war strategic

- **Bomb fuel, factories and supply lines and the war effort withers.** Each base runs a real
  materiel chain — factories produce, roads carry, the front spends. Starve it and the enemy
  recovers less, fields fewer units, gives ground. Run a field dry of JDAMs and its jets fall
  back to dumb bombs. Symmetric: protect your own.
- **The enemy commander plays with intent, and remembers.** It reads the ground balance, its
  air strength and the *trend* across turns, then holds a posture — **surging** when ahead,
  **consolidating** under pressure. A winning enemy watching its SAM belt come apart digs in
  anyway; one that catches your fighters spent lunges through the gap.
- **Bombing the enemy HQ matters** — knock out its command posts and its planner gets
  measurably sloppier at picking targets **and its offensive tempo thins** (a decapitated
  HQ frags fewer strike packages — never zero). Its reactive defenses never suffer.
- **Listen before you bomb.** With **COMINT collection** on, that same enemy C2 net is also
  your intel source: while it's emitting you read the enemy commander's posture, and a
  collection sortie (the C-130J jamming orbit or any drone) that makes it home buys next
  turn's full take — an intercepted enemy tasking (what's coming, roughly when) and one
  "suspected activity" circle fixed to an exact position. Killing their command posts still
  wrecks their planning — but it also puts out your wiretap. Bomb it or tap it.
- **And the enemy net is really on the air.** Turn on the **enemy radio net** and their
  command posts transmit coded morse traffic in periodic windows on fixed UHF frequencies —
  off your comms plan, so you only hear it by hunting the dial. Phantom, Tomcat, Hornet and
  Tiger needles can home on an open transmission window; kill the node and its net goes
  silent for good. Hidden insurgent cells carry radios too: your kneeboard briefs a
  "suspected clandestine net" with a frequency and an area, the dashed circle on the map is
  the search box, and a needle cut caught during one of its short transmission windows is
  what turns the circle into a fix.
- **The enemy economy follows its intent.** A surging enemy buys the armor its offensive
  spends; one consolidating under pressure husbands ground and rebuilds its air arm — and
  its buys favor its better hardware, not a coin flip over the catalog. Turn on **SAM site
  repair** and the belt regenerates a couple of units a turn unless you keep pressure on
  it — a rolled-back IADS stops being a one-way ratchet (command posts stay dead).
- **Campaign phases** — every campaign knows what phase of the air war it's in (Air
  Superiority → Interdiction → Offensive), inferred from live IADS, enemy air and front
  movement. A map ribbon shows the phase *and why*, and the planner leans its tasking to match.
- **Warships fire real cruise missile raids** — mark a target, call the strike, and the nearest
  ship ripples a salvo. Magazines are finite and never rearm, so a salvo spent on a truck park
  is one you don't have for the command bunker. A launch puts the defender's SAMs around the
  aimpoint on alert, so point defense gets its shot.
- Plus: strikeable **motor pool** depots, **enemy comms jamming** learned off a captured pilot,
  air-droppable **minefields**, and a **host F10 menu** to scramble bandits at a quiet event.

### Campaigns and content

- **Germany — Red Tide** — a *Red Storm Rising* 1988 NATO counteroffensive built for the 414th.
  The Pact overran the Fulda Gap, took Hamburg and seized Copenhagen; the thrust has culminated
  and the 414th spearheads the push back. Every squadron is a named historical unit in matching
  livery. Fulda is a forward helo FARP in the Gap — and lives like one, under artillery fire.
- **1968 Yankee Station** — the whole in-country air war on a **coastal ladder**: Hanoi inland
  behind its SA-2 ring, route packages laddering south to a DMZ front, carriers on a proper
  Yankee Station, the Air Force crossing from the "Thailand" fields. The **Ho Chi Minh Trail is
  a real, cuttable supply web**.
- **Afghanistan — Operation Enduring Resolve** — the first *living* counterinsurgency (a fork
  of Starfire's *Operation Shattered Dagger*). Strongholds **regenerate**, throttled by hidden
  ammo caches you must find and strike; infiltrators creep toward your ungarrisoned bases to
  take them. The populated valleys are no-strike areas where a strike near civilians costs you
  at the mandate meter — the desert is free, and troops in contact and air assaults are never
  restricted. Body count alone wins nothing. Disrupt the Network → Clear and Hold → Break the
  Momentum.
- **Nevada — Red Flag 81-2** — the ultimate war game, played as the war it rehearses: Aggressor
  F-5Es, the Constant Peg MiGs out of Tonopah, an emulator SAM array, KS-19 flak belts. The
  **Groom Lake box never opens**.
- **Iraq — Operation Inherent Resolve** — the second living COIN campaign: the Battle of Mosul,
  2016–17. The insurgency holds Mosul, Erbil and Kirkuk and lives on ten furnished FOBs along
  Highway 1 and the Nineveh ring; you grind north from Balad on one front against IEDs, HVT
  convoys and a 14-route supply web, under a permanent Mosul positive-control box. Predators
  and Reapers fly persistent ISR that banks real BDA.
- **Persian Gulf — The Tanker War (1988)** — the 1987–88 war on Gulf shipping, building to an
  Operation Praying Mantis climax in the Strait of Hormuz. The 1988 carrier air wing (F-14A,
  A-6E, A-7E) against Iranian naval and coastal power; the currency is **ships, not territory**
  — the will economy bleeds from sunk hulls, Silkworm batteries fire from the coast, and AAA
  gun forts stand on the oil platforms. The one DCS matchup where the Tomcat flies both sides.
- **Iraq — Umm al-Ma'arik (Desert Storm 1991)** — the air war against "the most well defended
  city in the world," fought the way it really was fought: **from outside**. Blue holds only
  the three H-3 desert strips seized on the border in the war's opening hours — the tanker
  bridge and AWACS fly from the Saudi rear — and climbs the pipeline-road ladder: **H-2, then
  Qadessiya (Al-Asad), where the Foxbats live**, then the Habbaniyah line toward Baghdad. The
  French-built **KARI** network ties the SA-2/SA-3 rings back through sector operations
  centers to one destroyable ADOC — decapitate it and the net goes autonomous; leave it and
  it repairs. Night-one start (17 Jan 1991, 0300), a Great Scud Hunt in the western baskets
  against launchers that relocate between recon passes, real-highway convoy interdiction from
  Baghdad to Mosul, a GCI-alert Iraqi Air Force on hot-pad QRA, and a no-strike circle over
  Baghdad's river bend that prices collateral into **Coalition cohesion** — one Al-Firdos is
  survivable, a habit is not. Ends where it must: break the regime's resolve at Safwan.
- **The Vietnam campaign layer changes *why* you fly.** **Political will** — Washington's
  patience, drained by losses (a downed **B-52** is a national event), by aviators sitting as
  POWs, and by the war's sheer duration; a one-way ratchet whose restores are too small to
  grind back, so **body count is a trap** — against Hanoi's **Regime Resolve**, which shrugs at
  airframes and bleeds from the trail. The war can **end at the negotiating table**: break
  Hanoi before your will runs out, or run dry and Washington orders the withdrawal, whatever
  the map says. You fly under **Washington's ROE** — a Rolling Thunder → Linebacker II arc
  where sanctuary zones are off-limits and deep targets are RESTRICTED. You can always break
  the rules; will pays the bill. When Hanoi answers — surging the trail during a bombing halt,
  opening a Tet offensive — a **"Hanoi's response"** briefing makes its plan as legible as
  yours. Any campaign can carry its own **will profile**, so a Falklands bleeds from sunk ships
  the way Vietnam bleeds from downed B-52s.
- Plus: **CurrentHill Iran** assets, **High Digit SAMs** (Ultimate Compilation — S-400, SAMP/T,
  Pantsir-SM, period EWRs), the optional **Expanded F-4E Weapons Pack** (check it on the Mods
  page to arm the Heatblur Phantom for real Weasel SEAD — AGM-78 Standard ARMs by default,
  a 4× HARM fit one click away; without the mod the jet falls back to its stock Shrike fits
  automatically), a **rebuilt settings screen** with
  one-click difficulty presets, a **drop-spawn** sandbox, and an eight-mechanic **Vietnam
  Ops** page (Arc Light, flak gauntlet, naval gunfire, trail convoys, airbase harassment, the
  Super Gaggle, FAC(A) marking, snake and nape).

Most campaign-facing systems have their own setting or plugin toggle, and existing campaigns
keep whatever they were saved with.

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
