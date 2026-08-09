# 414Ret — 414th Joint Fighter Group's DCS Retribution Fork

A squadron-focused build of [DCS Retribution](https://github.com/dcs-retribution/dcs-retribution),
the turn-based dynamic campaign generator for
[DCS World](https://www.digitalcombatsimulator.com/en/products/world/).

Based on upstream `dev` at `dce851ea`, plus the 414th's feature set and selected later
upstream fixes. The unmodified upstream README is kept as
[`README.upstream.md`](README.upstream.md).

> **AI assistants:** read [`CLAUDE.md`](CLAUDE.md) first — architecture, feature locations,
> branch layout.

---

## Download

Pre-built `.exe` releases are published automatically on every push to `main`. No GitHub
account needed.

**[Download latest build](https://github.com/BradySox/414Ret/releases/tag/latest)**

1. Download `414th-retribution-latest.zip`.
2. Extract anywhere.
3. Run `retribution_main.exe`.
4. Point it at your DCS World install on first launch.

`latest` is a rolling pre-release tracking current `main`. Versioned releases (`v1.x.x`) are
pinned campaign builds.

---

## What's different from upstream

Most of this is opt-in. Full list with toggles, defaults and known limitations:
[`docs/dev/414th-features.md`](docs/dev/414th-features.md).

### Recon and intelligence

- Enemy site composition, strength, damage and threat rings stay hidden until you scout or
  attack the site.
- Unscouted mobile forces draw a dashed circle offset from their true position instead of an
  exact marker. Fixed infrastructure stays exact.
- Optional decoy zones plant fake contacts indistinguishable from real ones. Scouting one
  burns it away; new ones appear each turn.
- Mobile missile launchers relocate mid-mission, within a few km of their campaign position.
  The radar SAM network does not move.
- TARPS is a player task (F-14, RF-101B, RA-5C). Photographs become confirmed intelligence.
- Also: approximate target-area mode, mobile SAMs hidden from player datalink, a fog reveal
  toggle, DCS-accurate terrain charts as base map.

### Combat SAR and squadron missions

- An ejected pilot becomes a survivor on the campaign map and stays there across turns. Rescue
  them and they recover for a few turns, then return to duty. Nobody reaches them in time and
  they go missing in action. AI ejections count.
- CSAR is a normal auto-planned mission type for both sides. Any helicopter with a cabin
  qualifies, and a human can fly the rescue in any CSAR-capable helo.
- The survivor keys an **ADF homing beacon on 260 kHz**, briefed on your kneeboard. Tune it
  before you launch — the C-130J, UH-1H and Mi-8 all home it directly.
- The C-130J flies the "King" on-scene commander role. It is player-flown: DCS only lets
  helicopters land at an unprepared pickup site, so an AI King will not complete a pickup.
- Two pickup styles: land and let the survivor walk aboard, or hoist them on a hover. A pilot
  down in the water is always hoisted.
- Survivors pop smoke for AI rescue flights. Human crews get the F10 menu — list active
  survivors, request smoke, flare or IR strobe — and choose when to expose the position.
- JAMMING turns the C-130J into an EC-130H/RC-130H-style EW and ISR platform.
- Escort jamming is flown by the EA-18G Growler and EA-6B Prowler only (both require their
  mods). The jammer spoofs radar missiles fired at anything under its bubble and pulses
  tracking SAMs to weapons-hold; effect strengthens with proximity. AI flies it automatically;
  players get an F10 menu. A per-side cap limits how many fly per turn.
- The auto-planner puts jammers on the packages that fly into a SAM ring — DEAD and strike.
  Helicopter packages (air assault, CSAR) do not get one; neither do their fast-jet formation
  escorts, which now follow the same helo/LHA rule the A2A and SEAD escorts already used.
- A threatened package is escorted by one SEAD flavour, not two. It draws a SEAD Escort that
  rides with it; front-line CAS still gets a SEAD Sweep running ahead.
- Fixed-wing transports fly Air Assault as a paradrop. Players run in below 3,000 ft AGL and
  use the CTLD *Unload / Extract Troops* call; AI releases automatically over the drop zone.
  Helicopter assaults are unchanged.
- Every generated mission is archived to a dated copy in a folder DCS's mission browser lists.

### Air war planning

- QRA intercept reserve holds fighters for base defence. Part of it can be player-manned as
  cold alert.
- Native DCS data cartridges auto-load in Hornets, Vipers and CJS Super Hornets: comm presets
  matching the kneeboard, route with push times, boat TACAN/ICLS/ACLS, and the SA/HSD picture
  (FLOT, no-strike zones, friendly orbits, recon-confirmed SAM rings). A per-flight DTC tab
  controls the cartridge or any single section of it. Super Hornets carry no SA picture — the
  mod's cartridge format has no field for one.
- Tanker and AWACS orbits are drawn on the F10 map with callsign, frequency and TACAN.
- Drop tanks are fitted for the sortie before tanker passes are decided, so jets stop
  double-tanking sorties their real load covers. The Payload tab shows burn, passes and RTB
  margin live.
- SAM batteries field two guidance radars, spaced so one missile cannot take both. New
  campaigns only.
- One continuous clock: time advances a few hours per turn and weather evolves from the
  previous turn instead of re-rolling. Requires day-and-night missions.
- The planner reads that weather — rain and storms ground automatic photo-recon and push
  low-level CAS and BAI behind all-weather strikes.
- Strike packages headed into a defended area are timed just behind the SEAD servicing that
  SAM. Fly the SEAD yourself and the AI push forms behind you.
- Also: overlapping jittered BARCAP waves, weighted off-mission combat resolution, per-side
  planner unpredictability.

### Battlefield and world

- Troops In Contact produces prolonged, formation-aware frontline firefights.
- Supply columns run both sides' road networks. Friendly routes sometimes hide ambush teams;
  nothing is telegraphed before the TROOPS IN CONTACT call.
- Sea shipments sail as convoys of cargo ships, each carrying a share, so sinking some denies
  only their share. Coastal anti-ship batteries fire on enemy shipping in range.
- Ship groups generate as mixed task groups rather than copies of one hull. Patrol boats never
  join a cruiser screen; a navy with one hull of a class still gets a coherent group. New games
  only.
- Missile batteries generate with a support park — cargo trucks, transporter/loader, fuel
  bowser, and a command vehicle where the faction has one — in that nation's kit. Launchers
  now have a purchase and repair cost. New games only.
- Squadrons spawn under their own DCS country, giving nation-specific voiceovers and pilot
  names. A country selector sits in the Air Wing Configuration dialog; campaigns can pin
  `country:` per squadron.
- Carrier comms match the hull: TACAN and ident (Roosevelt 71X TRO, Stennis 74X STN), stable
  channels, the ship's real name. If a map beacon owns the hull channel the boat takes the
  nearest free one. Navy jets wear sequential per-squadron modexes.
- Carrier decks carry dressing — tractors, crash truck, deck crew, LSO team — placed clear of
  every parking spot and catapult. An optional launch-corridor set is struck below before
  recovery.
- Also: mixed frontline combat clusters, civilian traffic, 414th-tuned Splash Damage 3.

### Kneeboards and debrief

- The kneeboard is the stock deck with 414th content folded into it. Mission Info opens on a
  BLUF: task, target, TOT, code words, compact air and SAM threat picture, loadout summary,
  SAR drill.
- The fuel ladder rides in the flight plan with RTB margin called out. It charges the whole
  sortie including on-station orbit, so a CAP row shows patrol speed and an endurance line
  ("On station 45 min planned; fuel supports ~50 min before bingo").
- A SITREP page reports last turn: both sides' losses (the enemy's as claimed), base changes,
  pilots recovered.
- A Threat Intel Brief gives one card per enemy air-defence system — guidance, ceiling, MEZ,
  HARM code, defeat note. It respects recon fog: unidentified sites show only a threat tier.
- Mission code words are visible to planners before generation and on the kneeboard in the
  cockpit.
- **Set as default for &lt;task&gt;** in the payload editor pins a loadout for that airframe and
  task across campaigns until cleared. Fuel and cockpit settings are already remembered per
  airframe.
- Also: target intel panels, impact-first debriefs, custom kneeboard import, era-gated cockpit
  options.

### Campaign systems

- **SP Pilot Mode.** The debrief gains an *Accept results & fly next* button that processes the
  turn and opens a sortie board instead of the map. Pick an aircraft from anything the wing can
  put up, then a sortie in it — one seat, AI wingmen. The role comes from what the package
  needs. A pre-turn brief covers evading pilots and their capture odds, enemy C2 damage,
  victory progress and the next squadron arrival. The map and mission planner are untouched.
- **Scheduled squadron arrivals.** Campaigns can add *new airframes* on announced turns, so the
  wing you start with is not the wing you end with. Schedules follow air-campaign order:
  air superiority, SEAD/DEAD and enablers first, deep strike once the SAM belt is coming down.
  Operation Baltic Fury and Red Tide ship with schedules.
- **Command-post strikes matter.** Destroying enemy command posts degrades its target selection
  and thins its offensive tempo. Reactive defence is unaffected.
- **COMINT collection.** A collection sortie that makes it home (C-130J jamming orbit or any
  drone) buys next turn's take: an intercepted enemy tasking and one suspected-activity circle
  fixed to an exact position. The same nodes are the ones you'd bomb to wreck their planning.
- **Enemy radio net.** Command posts transmit coded morse in periodic windows on fixed UHF
  frequencies, held clear of every briefed channel. How many stations are up at once is a
  setting. Phantom, Tomcat, Hornet and Tiger needles can home on an open window. Killing the
  node silences it permanently. Insurgent cells transmit too — the kneeboard briefs a frequency
  and an area, and the dashed map circle is the search box.
- **Enemy procurement** favours its better hardware rather than rolling the catalogue. Optional
  SAM site repair regenerates a couple of units per turn unless pressured; command posts stay
  dead.
- **Victory conditions.** Campaigns can author them: hold objective bases, destroy named
  high-value targets, kill every command post, grind enemy air below a threshold, or deny all
  operating airfields. Any campaign can enable a domination or attrition ending from settings.
  The map ribbon shows a live checklist. The capture-everything ending always remains.
- **Cruise missile raids.** Mark a target and call the strike; the nearest warship ripples a
  salvo. Magazines are finite and never rearm. A launch alerts defending SAMs around the
  aimpoint.
- **Naval magazines.** Warships can be released to weapons-free a group at a time instead of
  all at once, and anti-ship missiles fired are gone for the rest of the war. A dry ship still
  defends itself.
- **GPS jamming.** A JDAM, JSOW, JASSM or SLAM-ER released inside an enemy jamming bubble flies
  its normal profile and lands off the aimpoint — further off the deeper inside you released.
  Laser and TV weapons are unaffected; killing the jammer restores accuracy immediately. A
  scouted jamming area is briefed on the kneeboard, an unscouted one is not.
- Also: strikeable motor pool depots, enemy comms jamming learned from a captured pilot,
  air-droppable minefields, a host F10 menu to scramble bandits.

---

## Campaigns

| Campaign | Map | Setting |
|---|---|---|
| Red Tide | Germany | 1988 NATO counteroffensive through the Fulda Gap |
| 1968 Yankee Station | Caucasus | Vietnam air war, coastal ladder from Hanoi to the DMZ |
| Operation Enduring Resolve | Afghanistan | Living counterinsurgency |
| Red Flag 81-2 | Nevada | The exercise, played as the war it rehearses |
| Operation Inherent Resolve | Iraq | Battle of Mosul, 2016–17 |
| The Tanker War | Persian Gulf | 1987–88 Gulf shipping war to Praying Mantis |
| Umm al-Ma'arik | Iraq | Desert Storm 1991, fought from the H-3 strips inward |
| Second Island Chain | Marianas | 2027 China fight up the chain from Guam |

- **Red Tide** — the Pact overran the Fulda Gap, took Hamburg and seized Copenhagen; the thrust
  has culminated. Every squadron is a named historical unit in matching livery. Fulda is a
  forward helo FARP under artillery fire.
- **1968 Yankee Station** — Hanoi inland behind its SA-2 ring, route packages laddering south to
  a DMZ front, carriers on Yankee Station, the Air Force crossing from the Thailand fields. The
  Ho Chi Minh Trail is a real, cuttable supply web.
- **Operation Enduring Resolve** — a fork of Starfire's *Operation Shattered Dagger*. Strongholds
  regenerate, throttled by hidden ammo caches you have to find and strike. Infiltrators creep
  toward ungarrisoned bases to take them. Body count alone wins nothing.
- **Red Flag 81-2** — Aggressor F-5Es, the Constant Peg MiGs out of Tonopah, an emulator SAM
  array, KS-19 flak belts. The Groom Lake box never opens.
- **Operation Inherent Resolve** — the insurgency holds Mosul, Erbil and Kirkuk plus ten
  furnished FOBs along Highway 1 and the Nineveh ring. Grind north from Balad against IEDs, HVT
  convoys and a 14-route supply web, under a permanent Mosul positive-control box. Predators
  and Reapers fly persistent ISR that banks real BDA.
- **The Tanker War** — the 1988 carrier air wing (F-14A, A-6E, A-7E) against Iranian naval and
  coastal power. The currency is ships, not territory: Silkworm batteries fire from the coast
  and AAA gun forts stand on the oil platforms. The one DCS matchup where the Tomcat flies both
  sides.
- **Umm al-Ma'arik** — blue holds only the three H-3 desert strips seized on the border, with
  the tanker bridge and AWACS flying from the Saudi rear, and climbs the pipeline-road ladder:
  H-2, then Qadessiya (Al-Asad) where the Foxbats live, then the Habbaniyah line toward
  Baghdad. The French-built KARI network ties the SA-2/SA-3 rings back through sector operations
  centres to one destroyable ADOC — decapitate it and the net goes autonomous, leave it and it
  repairs. Night-one start (17 Jan 1991, 0300), a Scud hunt in the western baskets, real-highway
  convoy interdiction, and a GCI-alert Iraqi Air Force on hot-pad QRA. Every squadron is its
  real 1991 unit.
- **Second Island Chain** — a Taiwan crisis went kinetic; the opening salvo cratered Guam's ramps
  while amphibious groups took Rota, Tinian and Saipan. Hold the remaining ramp and fight north.
  A modern PLA air-defence belt (S-300PMU-2 on Tinian, HQ-22 on Rota, HQ-7 and HQ-17A point
  defence), road-mobile PLARF launchers that shoot and scoot, three PLAN carrier groups and a
  Badger regiment. Both fleets trade cruise missiles from finite magazines. The islands aren't
  connected, so no ground front forms — islands change hands by air assault, helicopter off the
  LHA or C-130J paradrop.

The Vietnam campaign layer also changes how the enemy fights: Hanoi answers the campaign clock
by surging the Trail or opening a Tet-style ground push on a scheduled window, and its MiGs fly
a period GCI ambush — scramble late, one slashing pass, run for home.

**Mod content:** CurrentHill Iran assets, High Digit SAMs (Ultimate Compilation — S-400, SAMP/T,
Pantsir-SM, period EWRs), and the optional Expanded F-4E Weapons Pack (check it on the Mods page
to arm the Heatblur Phantom for Weasel SEAD; without the mod the jet falls back to stock Shrike
fits). Plus a rebuilt settings screen with difficulty presets and an eight-mechanic Vietnam Ops
page (Arc Light, flak gauntlet, naval gunfire, trail convoys, airbase harassment, Super Gaggle,
FAC(A) marking, snake and nape).

Existing campaigns keep whatever settings they were saved with.

---

## Running from source

Same as upstream. Windows, PowerShell:

```powershell
.\scripts\bootstrap-env.ps1
.\scripts\check-env.ps1
.\venv\Scripts\python.exe -m qt_ui.main
```

You need a working DCS World install. MOOSE-dependent features assume the bundled plugins under
`resources/plugins/` are present. Full upstream setup and dependencies:
[`README.upstream.md`](README.upstream.md).

### Environment health

This repo is sensitive to Python drift on Windows. If `.venv` was created from a Python install
that later moved or was removed, every repo-local command fails the same confusing way.

```powershell
.\scripts\bootstrap-env.ps1  # find Python 3.11, recreate .venv, install requirements
.\scripts\check-env.ps1      # verify Python, venv, and Git LFS auth
```

`check-env.ps1` also warns on unauthenticated Git LFS, a common cause of push failures.

### Checks before pushing

```powershell
.venv\Scripts\python.exe -m black --check .      # formatting
.venv\Scripts\python.exe -m mypy game tests      # type checking
.venv\Scripts\python.exe -m pytest tests -q      # unit tests
```

---

## Relationship to the 414th workspace

The 414th maintains a separate, private mission-building workspace (campaign plans, `.miz`
files, and Mission-Editor scripts not yet integrated here).

These started as standalone ME scripts and are now integrated — do not use the standalone
versions:

- **C-130J EW/ISR** → `resources/plugins/c130j/` (`FlightType.JAMMING`). Supersedes the retired
  generic `ewrj` / "EW Jammer Script".
- **QRA / AI_A2A_DISPATCHER** → `resources/plugins/intercept/` (per-squadron `intercept_reserve`)
- **Recon** → `resources/plugins/recon/` (runtime engine for `FlightType.TARPS`)

This repo is the engine-level side: capabilities planned and spawned by the campaign generator
rather than hand-placed in the Mission Editor.

---

## License

DCS Retribution is LGPL (see [`LICENSE`](LICENSE)). Upstream authorship and history are
preserved; 414th additions are under the same terms.
Upstream: <https://github.com/dcs-retribution/dcs-retribution>.
