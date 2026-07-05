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
- Enemy **field forces you haven't scouted don't even show an exact position**: a mobile SAM
  site, a deployed vehicle group, or a missile site appears only as a dashed **"suspected
  activity" circle** offset from the truth ("in here somewhere") until recon or an attack
  localizes it — so the Weasel hunt and the SCUD hunt are real hunts. Fixed infrastructure
  stays exact (airfields, buildings, the big strategic SAM sites, EWRs, ships), the circle
  is clickable so you can still plan recon or a strike against the suspected area, and the
  whole behaviour is a Difficulty & Realism toggle (**on** by default for new campaigns).
- **TARPS** is a real player task — flown by F-14s, and by the Vietnam-era photo-recon birds
  (**RF-101B Voodoo**, **RA-5C Vigilante**) in period campaigns — supported by the **TARS**
  film-and-debrief system. What the aircraft photographs is carried back into the campaign as
  confirmed intelligence.
- When you need the ground truth anyway — debugging a campaign, planning the opposing side,
  or just checking the real laydown — tick **Reveal fog of war (overview)** in the map's layer
  panel (top-right, with the other enemy-intel toggles). It turns the fog off and shows the
  true picture: full enemy composition, threat rings, and otherwise-hidden command posts. It is
  a view toggle only — it never changes the campaign and is never saved.
- The **map layer panel** is a single grouped, collapsible control (dark-themed to match the
  app) with one-click **preset views** — Default, SEAD, Recon, Clean — and it remembers your
  layer choices between sessions.
- The campaign map can use a **chart of the DCS terrain itself** as its base map instead of
  real-world satellite imagery (which doesn't match what you'll see in the sim): slice any
  Web-Mercator GeoTIFF — e.g. Flappie's community "accurate DCS Caucasus map" — with
  `tools/tile_geotiff.py` into `Saved Games\Retribution\MapTiles\`, and a button for it appears
  in the layer panel's base-map row. Purely local: nothing is bundled, and machines without
  tiles see no change.
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

- **SCAR** is now the **RESCAP "Sandy"** escort of the combat-SAR package — fly an **A-10 or Apache**
  to bring a downed pilot home: hold near the FLOT with the **King** (C-130) and **Jolly Green** (the
  rescue helo), protect the survivor, suppress the threats around them, and walk the helo in. The enemy
  may send a **snatch party** to grab the downed pilot — kill it in time or the pilot is **captured**
  and held as a **POW at an enemy airfield**: recapture that field to free them, and every turn they
  are held saps your side's political will; leave them held too long and they are lost for good. The
  capture is the consequence for losing the rescue fight — there is no separate raid mission to plan.
  (The old armor-hunt SCAR is retired — SCAR is a rescue role now.)
- **Combat SAR** makes a downed pilot worth flying for. A CH-47 orbits near the front as the
  rescuer while a C-130 holds overhead as the HC-130 "King" — on-scene command with an
  air-tracking TACAN the helo homes on (an AI King lights it automatically; a player King
  sets it from the planned channel in-cockpit) and an F10 survivor-locator readout. When a human pilot
  ejects, they spawn with a beacon; recover them and deliver them to any friendly field and the
  campaign **spares the aviator** (you still lose the jet, but the experienced pilot returns to
  the squadron instead of being lost). Rescue is a **normal, standing task**: the AI plans the
  package (King + rescue helo + a **Sandy** escort) automatically by default — turn `Automatic
  Combat SAR` off to fly rescues manually only — and any human can fly any seat. AI ejections
  count too: an AI-flown helo rescue spares the pilot the same way. If the enemy reaches the downed
  pilot first they are **captured** — held as a POW (see SCAR above).
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

- Squadrons can hold aircraft in a **QRA intercept reserve** for runtime base defense — and
  you can **man part of it yourself**: set how many of the reserve are player-flown and a
  cold-start, home-field alert BARCAP is fragged for you each mission, ready to scramble. You
  get a **"raid inbound — scramble"** radio call when bandits close on the field, and decide
  when to launch. Crew it for co-op (every alert jet a client slot) or fly lead with AI
  wingmen.
- BARCAP coverage uses overlapping, jittered, threat-weighted waves and a more useful
  forward defensive line. Quiet sectors retain baseline coverage; contested sectors gain
  more.
- Transit routes treat the active ground battle as a hazard, reducing the tendency for
  unrelated AI flights to loiter over the FLOT.
- AWACS and tanker racetracks are anchored on the front line and stand off into friendly
  airspace, so support orbits sit centered behind the fighting at a sane distance instead of
  being flung far off-axis or pinned onto a home airfield.
- **Support orbits are drawn on the F10 map.** Every friendly tanker and AWACS gets a cyan
  racetrack + a label (callsign, type, radio freq, TACAN) painted right onto the in-cockpit
  F10 map, so you can find your gas and your controller in flight instead of guessing — no
  DTC, no cartridge, just an object on the map.
- Flight plans **budget real time at the tanker**: a flight with a refuel stop launches and
  pushes early enough to cycle the whole flight through the boom and still make its join and
  TOT, and the package tanker is on station for ingress-side (pre-vul) refuels instead of only
  arriving for the trip home.
- **Flights add fuel tanks when the route is long.** On far-AO campaigns — like the COIN
  carrier parked ~800 km off the beach — a jet whose planned route needs more gas than it can
  carry internally gets extra drop tanks added to its **empty** stations at mission start (so a
  Hornet strike flies out with its third bag). It never swaps out a targeting pod, ECM, or
  ordnance to do it, and it does nothing on short-range routes or to loadouts you've customized.
- An optional **auto-planner unpredictability** doctrine knob (per side, off by default)
  varies which offensive targets the enemy services first, so red stops striking the same
  targets in the same order every turn. Its reactive air defenses stay just as sharp.
- Doctrine controls expose patrol-altitude floors and scatter, and the aircraft task
  priorities have received a conservative role-based rebalance.
- Soviet/Russian air defenses use improved legacy SAM layouts and radar composition.
  Campaign-map SAM rings, emitters, routes, and IADS links are easier to inspect and read.
- **Off-mission engagements are weighted, not coin flips.** The AI-vs-AI fights resolved while you
  fast-forward now account for aircraft capability and numbers (a modern fighter beats an obsolete
  one more often than not, but a pair can still overwhelm a lone jet), and SEAD/SEAD-capable flights
  are credited for surviving SAMs — so the campaign state you inherit between sorties reads
  believably instead of randomly.
- **"Player at IP" fast-forward now actually puts you at your IP.** An AI skirmish elsewhere no longer
  stops the fast-forward short and spawns you back on the ramp; only a fight your own flight is in
  still pauses so you can fly it.
- **The campaign runs on one continuous clock.** Instead of each turn teleporting to a random hour and
  re-rolling the weather from scratch, the mission clock now marches forward a few hours per turn from
  the campaign's start date, the date rolls over at midnight, and the weather **evolves** from the
  turn before — fronts roll in and clear over several turns instead of a thunderstorm one sortie and
  clear skies the next. It's on by default (with day-and-night missions); turn it off in *Campaign
  Management → Campaign clock & weather* for the old per-turn behaviour.

### The generated mission feels occupied

- **Troops In Contact (TIC)** produces prolonged, formation-aware frontline firefights
  with ambient suppressive fire instead of letting vanilla ground AI instantly erase the
  battle.
- Frontline forces deploy as **mixed combat clusters** — an armor wedge with embedded air
  defense, an anti-tank standoff pair, and leading recon — spread evenly along the line
  rather than piled onto one patch of terrain. You can also set a **default front-line
  stance** (HQ Automation) for your sectors when you're managing stances yourself.
- Civilian regional traffic adds light rear-area activity, while the 414th-tuned
  **Splash Damage 3** build improves weapon effects without returning to the plugin's
  harsher stock values.
- **Nation-specific voiceovers per squadron** — each squadron's aircraft fly under their own
  country, so a mixed-nation coalition hears each unit's real national radio voice instead of
  one shared faction voice. Single-nation factions are unaffected. **Pilot rosters match the
  nation, too** — a Greek squadron fills with Greek names, an Iranian one with Persian names,
  and so on, instead of everyone sharing one set of names.

### Planning and debriefing expose the information crews need

- Ground targets have an intel panel showing known strength, mission suitability, ranges,
  IADS membership, visibility, and capture/purchase state.
- Package and flight dialogs show task, TOT, player slots, departure bases, squadron fit,
  available aircraft, and target distance without making planners hunt across windows.
- The map provides clearer SAM, route, emitter, and IADS interaction; waypoint altitude
  editing supports practical bulk changes.
- The **Payload** tab can **save your aircraft settings as a per-airframe default** — set the internal
  fuel, aircraft condition, wear & tear, and spawn type the way you like, click *Save as default*, and
  every new flight of that airframe opens pre-configured instead of resetting to stock each package
  (*Clear default* forgets it). The loadout has always had its own *Save Payload* and the player laser
  code has a campaign setting; this covers the rest of that box. Applies to your side only.
- Debriefing begins with mission impact — territorial changes, runway damage, and losses —
  before the full event detail.
- Every flight's kneeboard leads with a **one-page Brief Sheet** —
  a single scannable, **colour-coded** brief modelled on the squadron's printed brief sheet: header,
  mission, the full route with **steerpoint numbers and times** (`HOLD 1 12:32 → TKR 2 12:38 →
  JOIN 3 12:49 → TGT 5-8 13:01 → LAND 10` — every waypoint listed; multiple strike points collapse
  to one range),
  bingo/joker/divert, air + SAM threats, game plan, comms, code words, bullseye, fields (RWY/ATC/TCN),
  weather (departure-field **QNH/QFE** + surface wind), loadout, laser codes, and Combat SAR — all
  filled in from the mission. Colour does the work: **blue** for
  nav and freqs, **amber** for threats and fuel, **green** for the success word, **red** for abort, so you
  find what you need at a glance. Empty fields keep a `______` fill-in blank, like a real brief sheet, so
  you can write the rest in. The standard pages (Game Plan with the full steerpoint table, Support Info,
  the threat cards) follow it. (The former experimental "compact deck" folding was retired — the deck is
  the classic multi-page layout again, fronted by the pieces that earned their keep.)
- Every flight's kneeboard opens on a **cover page**: the operation name, turn, and date up top; a
  **"last turn" SITREP** (both sides' losses — the enemy's as *claimed* — bases captured or lost, and
  downed pilots recovered); and, when several flights share an airframe (DCS stacks them into one
  kneeboard), a **flight index** — each callsign, task, and start page — so you flip straight to your
  own deck. The
  SITREP appears from your second mission on and hides after a quiet turn (*Campaign SITREP band*,
  Kneeboards page, on by default).
- Kneeboards are restyled to use the page: clean headings with underline rules and spacing
  (no wasted bottom-half), and the Friendly Packages list flows into two columns when long.
- **Custom kneeboards** can be imported from the *Kneeboards* toolbar button — add an image
  once and it's injected into every flight's kneeboard (or scoped to one airframe), stored in
  the campaign save, instead of hand-editing each mission.
- An optional **Threat Intel Brief** kneeboard page is the enemy air-defense dossier, one card
  per system — guidance, engagement ceiling, MEZ, HARM code, bullseye cues, live/dead counts, and
  a **how-to-defeat** note — like a campaign intelligence briefing. It respects recon fog: sites
  you haven't identified show only their threat tier ("Unidentified MERAD") until you fly a TARPS
  overflight. On by default.
- Optional **mission code words** (Red Flag style) — the whole side shares one randomised,
  themed table: a **push word per task** (STRIKE / SEAD / OCA / CAS / …) plus SUCCESS / ABORT, so
  one call ("Red Kite") tells everyone SEAD is pushing. Planners see the full table *before*
  generating the mission — a **persistent panel** in the package list, a tooltip, and a
  `PUSH <word>` tag on the join waypoint — to build a briefing. A **Comms & Brevity** kneeboard
  page carries the table (your task marked) plus a brevity crib filtered to your task. Fresh words
  every turn, stable while you plan. Off by default.
- Optional **Fuel Ladder** kneeboard page — one glanceable column of planned fuel remaining at each
  steerpoint, with the RTB margin (how much you have to spare over what you need to get home — negative
  means tank or divert) called out once and Bingo/Joker. Off by default. Now shows for **every**
  flyable airframe: aircraft without hand-measured fuel data (the C-130J "King", the helicopters,
  warbirds, ...) get a rough estimate derived from their fuel capacity instead of the old "No fuel
  estimate available" placeholder.
- Plugin settings explain what each system does and use squadron-readable labels and units.
- When *Restrict weapons by campaign date* is on, era-defining **cockpit options** are now gated
  alongside the weapons: a pre-2003 campaign no longer offers (or quietly spawns) a **JHMCS**
  helmet-mounted sight, falling back to the period-correct visor. NVG and other era-appropriate
  options stay available.
- The same toggle now also makes the **support trucks** at airbase and FARP ground-starts
  period-correct: a Vietnam-era mission parks GAZ-66 / Ural-375 logistics trucks on the ramp
  instead of modern HEMTTs, falling back to the oldest available vehicle when nothing earlier
  exists in DCS.

### Additional 414th content and integrations

- The **CurrentHill Iran** integration adds Shahed-136 and IRGCN FAC assets plus a dedicated
  `[CH] Iran 2020` faction behind a new-game mod toggle.
- **High Digit SAMs** support now targets the actively-maintained
  [Ultimate Compilation](https://github.com/dcs-sams/HighDigitSAMs-Ultimate-Compilation)
  (v1.4.3+) instead of the abandoned original — same new-game toggle, plus its new content:
  **S-400** and **S-300V4** batteries, the S-300PT, **Pantsir-SM** point defense, the French
  **SAMP/T** Aster battery, **SA-7/SA-7b manpads** for the 70s–80s red factions,
  new early-warning radars (the period **P-37 Bar Lock** gives Cold-War red factions a real EWR
  net for the IADS), and insurgent **ZU-23 Toyota technicals**.
- The **settings screen** was audited end-to-end: dead and duplicate options were removed,
  the two AI-radio toggles were merged into a single **AI wingman radio behavior** choice
  (Normal / Suppress contact reports / Radio silence), the four redundant ground-start truck
  toggles were folded into two (supply trucks / ground-power trucks, each covering both airbases
  and roadbases), and many labels were clarified. Existing campaigns migrate automatically on load.
- The **settings pages were reorganized** so options are easy to find: the two giant catch-all
  lists are gone, replaced by six focused pages (**Difficulty & Realism, Air Doctrine, Campaign
  Management, Mission Generation, Kneeboards, Performance**). New **one-click difficulty presets**
  — **Casual / Normal / Veteran / Ace** — sit atop the Difficulty & Realism page and set AI skill,
  economy, player aids, and realism/restrictions together as a starting point; you can still
  fine-tune any individual setting afterward, and *Normal* restores the stock defaults.
- **Campaign phases**: every campaign now knows what *phase* of the air war it is in — **Air
  Superiority** (roll back the SAM belt, blunt the MiGs), **Interdiction** (choke reinforcement and
  logistics), then the **Offensive** (take ground) — inferred each turn from the live IADS, enemy air,
  and front movement, with no campaign authoring required. A slim **status ribbon over the map** (also
  showing campaign, turn, and date — previously nowhere in the web UI) and a band on the kneeboard
  cover page always show the phase *and why* ("Interdiction — enemy IADS 22% · air threat low · front
  static"), and the campaign announces each transition. The auto-planner leans its offensive tasking to
  match the phase — SEAD/OCA first while rolling back, BAI/Armed Recon in Interdiction, CAS and base
  capture on the push — while your defenses stay untouched. On by default; a single Campaign Management
  toggle turns it off. On the Vietnam campaigns the ribbon also carries the **political-will meters**.
  Click the phase chip and the **arc expander** now reads like a war plan: every phase shows an
  **objectives checklist with live ticks** (measurable goals — "break the SAM belt below 40%" — check
  themselves off as the campaign state moves; guidance lines stay plain bullets) and spells out **when
  and why the next phase arrives** — the schedule *and* the acceleration ("Escalates early if will
  falls below 65 (now 100)"), for inferred arcs just as much as the authored Vietnam ones. Hover the
  **WILL/RESOLVE meters** (or read the SITREP band) for the new **attribution ledger** — exactly which
  feeds moved the number last turn ("heavy bombers ×1 down −6.0 · POWs held ×3 −1.5"), so the will
  economy stops being a mystery meter. And when you plan a package onto an ROE-restricted target, the
  package dialog now warns you **before you fly** — the strike is never blocked, but the political-will
  bill is a knowing choice at planning instead of a surprise at debrief.
- A new **Vietnam Ops** settings page holds opt-in period mechanics for the Vietnam-era
  campaigns (off by default; the Vietnam campaigns turn the relevant ones
  on). The first is **Arc Light**: fly a **Strike with a heavy bomber** (B-52) and instead of a
  single aimpoint it walks a *carpet* of bombs across the target on the run-in, the way Operation
  Niagara saturated the hills around Khe Sanh — tactical strikers are unaffected. The second is an
  **AAA flak gauntlet**: fly within range and below the ceiling of an enemy AAA gun and you draw
  barrage flak that *tightens* when you fly a steady, predictable line and *widens* when you jink —
  the AAA-heavy Vietnam threat the engine never modelled, as pressure to manoeuvre rather than a
  hidden missile. The third is **naval gunfire support** for coastal campaigns: offshore gun ships
  (the New Jersey's 16-inch batteries, cruisers, destroyers) shell shore targets — call a fire mission
  on an F10 map marker from the radio menu, or let the ships bombard enemy coastal positions
  automatically. The fourth is **convoy interdiction (Steel Tiger)**: the enemy runs a **real** supply
  convoy up the road behind the front (the Ho Chi Minh Trail) — carrying actual reinforcements, so hunting it
  down on an Armed Recon genuinely denies the enemy those units, and letting it through means they reach the
  line. It's a live logistics target in the campaign, not a scripted prop. **Right-click an enemy supply route**
  on the map to frag the interdiction package straight onto that corridor — and the Armed Recon **plans a real
  road sweep** (search points at the start, middle, and end of the hunted route, each with its own engagement
  zone) instead of a single waypoint parked on the origin base. The fifth
  is **airbase harassment**: forward enemy airfields draw sporadic rocket/mortar fire near the ramp — the
  near-constant siege of Bien Hoa, Da Nang, and the Khe Sanh strip — so the rear stops feeling like a safe
  area. *Your* active spawn fields are never targeted, and a startup grace period keeps it off while you're
  still starting up. The sixth is the **Super Gaggle**: a formation of transport helos — drawn from a **real** friendly
  helicopter squadron, with a fast-mover suppression flight — runs supplies into a cut-off forward outpost
  (launch field → outpost → back), which you can escort in. Lose a helo and it's a real airframe loss to that
  squadron; get the supplies in and the garrison is bolstered — the Khe Sanh hilltop resupply. The seventh is **FAC(A) marking**: an airborne forward air
  controller (an OV-10 Bronco loitering over the battle area) marks nearby enemy ground with **white-phosphorus
  smoke** so you can visually acquire the target and roll in — the iconic Vietnam Bronco putting willie pete on
  the target. The eighth is **snake and nape**: press a **low, fast Snakeye delivery** onto enemy troops and each
  bomb's **real impact point erupts in napalm fire** — the signature Vietnam CAS run, with the wall of fire
  drawn by your actual ripple (a dry pass lays nothing; a miss burns where it missed). Unlike the flak
  gauntlet (which *punishes* a predictable line), this *rewards* pressing the run in on the deck, and the
  fire genuinely hurts soft targets. Real Mk-77 napalm cans keep their own (Splash Damage) fireballs. And it
  isn't just you: under the Vietnam doctrines, **AI CAS/interdiction flights now fly their attack runs on the
  deck too** (an authored 500 ft low-level profile — Skyraiders pressing in low instead of level-bombing from
  20,000 ft), so an AI Snakeye pass can lay the same fire — and eats the same AAA. See
  [`docs/dev/design/414th-vietnam-ops-notes.md`](docs/dev/design/414th-vietnam-ops-notes.md). The Vietnam
  campaigns (1968 Yankee Station, Velvet Thunder, Red Flag 81-2) turn on the whole battlefield suite by
  default — naval gunfire only on the coastal ones, where offshore guns can actually reach the shore.
- The **Vietnam campaign layer** changes *why* you fly, not just how it feels. **Political will** tracks each
  side's capital for the war: your **Political Will** (Washington's patience — drained by airframe losses, with
  a downed B-52 a national event; by aviators sitting as POWs in Hanoi; by lost ground — and, on 1968 Yankee
  Station, by the **war's sheer duration**: Washington's patience is a one-way **ratchet** that erodes turn
  over turn, and the wins that push it back up (claimed MiGs, rescued crews) are deliberately too small to
  offset the drain — so **body count is a trap** and time is genuinely against you) against the enemy's
  **Regime Resolve** (Hanoi barely registers airframe losses — it drains from **trail-logistics strangulation**
  and the whole air-to-ground campaign: CAS, armed recon, and the **Arc Light B-52 carpets** all bleed it).
  Two things sharpen the squeeze on Yankee Station: **escalating the war costs you at home even when the
  strikes are sanctioned** — resuming the deep bombing at Linebacker, and the Linebacker II "Christmas
  bombing," each dent Washington's patience up front (an early, decisive campaign never pays it) — and a
  **commitment ceiling**: as your will falls, Congress **trims the war budget**, starving a losing war of
  replacements, so the war is quite literally taken out of your hands rather than merely lost at the table.
  The war can now **end at the negotiating table**: break Hanoi's resolve before your
  will runs out and they agree to terms — you never had to take a base; run dry first and Washington orders the
  withdrawal, whatever the map says. And when Hanoi answers your escalation — surging the trail during a bombing
  halt, opening a Tet/Easter ground offensive — you get a **"Hanoi's response"** briefing so the enemy's plan is
  as legible as your own. Territory victory still works. And with the **static front** on, the ground
  war fights like the era's: the front line bends with the battle inside a narrow band around where the campaign
  started — pressure reads on the map — but never sweeps onto a base to capture it; deliberate **Air Assault**
  operations remain the one way to take ground, and attrition pays out through political will instead. Both are
  opt-in (Vietnam Ops → Campaign) and preseeded on in the Vietnam campaigns; watch the will meters move on
  the SITREP band each turn. The Washington/Hanoi framing is just the default: any campaign can carry its own
  **will profile** (a `will:` block in the campaign YAML) that renames the meters, rewrites the exhaustion
  headlines, and re-weights every feed for its era — including a new **warship-loss feed**, so a naval war
  (a Falklands, say) bleeds will from sunk ships the way Vietnam bleeds it from downed B-52s. And the Vietnam campaigns now fly under **Washington's rules of engagement**: an
  authored **Rolling Thunder → Bombing Halt → Linebacker → Linebacker II** arc where a red dashed **sanctuary
  zone** on the map (the "Hanoi" hub) is off-limits, deep target classes (factories, power, airfields) show a
  **RESTRICTED** badge you can see but may not hit — the defining Rolling Thunder frustration — and the AI
  planner obeys. Those no-fly zones aren't just circles: a campaign can define a **box** (a training range, a
  Route Package) or a **corridor** (an ingress lane, the Ho Chi Minh trail) — or **draw the shape directly in
  the Mission Editor** and reference it by name — and they're **painted onto the in-cockpit F10 map**, not
  just the planner, so you see the rules where you fly. *You* can always break the rules; the strike goes through, and Political Will pays the bill.
  Escalation arrives on schedule or **faster the more your will bleeds**, until Linebacker II takes the gloves
  off entirely. And the MiGs fight like it's 1968: Vietnam-era interceptors fly **GCI hit-and-run** — they
  scramble late, slash your strike package close to the target, refuse to chase far from their field, and go
  home after one pass — while their sanctuary bases stay untouchable until the escalation lifts.
- The **three Caucasus Vietnam campaigns are consolidated into one** — **1968 Yankee Station** now carries
  the whole in-country air war in its features and scenario, and the standalone **Khe Sanh: Operation Niagara**
  and **Steel Tiger: Trail Interdiction** campaigns are dropped. Nothing is lost: the **Steel Tiger** trail war
  is folded in as the order-of-battle tilt (Navy Intruders, Skyraiders and Broncos flying BAI/armed recon on
  the Ho Chi Minh Trail alongside the route-package strikers), and the **Niagara** siege is folded in as the
  DMZ front — Da Nang starts depleted so the line begins pressed in near the wire, the forward strips draw
  airbase harassment, and the encircled **FOB Khe Sanh** lives on the Super Gaggle resupply. One map, one
  campaign, the whole war: the coastal route packages, the trail, and the siege. Needs a **NEW** game.
- The **1968 Yankee Station theater is a "coastal ladder."** North
  Vietnam lives where the terrain says it should: **Hanoi (Kutaisi)** inland up the river delta behind
  its SA-2 ring, **Haiphong (Senaki)** on the coast, and the route packages laddering south through **Vinh
  (Sukhumi)** and **Dong Hoi (Gudauta)** to a single **DMZ front at the Psou narrows**, held from **Da Nang
  (Sochi-Adler)** and the **FOB Khe Sanh** hill outpost right under the line. The carriers moved onto a
  proper **Yankee Station off the delta**; the Air Force crosses the mountains from the **"Thailand" fields**
  (Ubon = Maykop, Takhli/Korat = Mineralnye Vody) — the real 1968 Navy/USAF split falls out of the geometry.
  The **Ho Chi Minh Trail is a real, cuttable supply web**: the trail FOBs carry their real names (Mu
  Gia, Ban Karai, Ban Laboy, Tchepone…), every leg crosses a bridge, and the last leg feeds the front. The
  ROE sanctuary sits over **Hanoi itself** — where the MiGs, the SAMs and the industry actually are, so
  Rolling Thunder's restraint finally costs something — plus a **permanent "PRC border" ring at Tbilisi**
  that never releases, even in Linebacker II, exactly like the real war.
- A new **Afghanistan - Operation Enduring Resolve (COIN)** campaign — the first **living
  counterinsurgency** (a fork of Starfire's Operation Shattered Dagger). The insurgency's strongholds
  **regenerate**: cleared cells come back toward their original strength each turn — and your last recon
  picture stands until you re-fly it — throttled by **hidden ammo caches** you recon and strike; kill a
  stronghold's caches and its regeneration collapses to a trickle. The war is decided at the will meters:
  **the Coalition's mandate** (airframes, lost bases, strikes into the Lashkar Gah
  population-center ring — where the insurgency hides its caches and runs its trail, so the restraint
  actually costs something — and plain time) against **the insurgency's momentum** (caches, trail convoys,
  strongholds — almost never its dead fighters). Disrupt the Network → Clear and Hold → Break the
  Momentum, with FOB standoff fire and the supply-trail ratline running throughout. Body count alone
  wins nothing. And the ROE draws the horror of COIN onto the map: the **populated river valleys** — the
  Helmand green zone, the Musa Qala feeder, the Tarin Kowt bowl, the Delaram junction — are drawn as big
  **no-strike "positive-control" areas** where every fixed strike near the people costs you at the mandate
  meter. The open desert and the northern gate are free; trail convoys and troops in contact are always
  fair game, and air assaults are never blocked — so you still retake your objectives, you just pay for
  the collateral when you fight where the insurgency hides. And the map plays the intel game with you:
  a hidden insurgent object you haven't found yet — an IED, a leader's convoy, a cell in the countryside —
  doesn't sit on the map as a marker at its exact position at all; it shows as a dashed **"suspected
  activity" circle** offset from the truth ("in here somewhere"), and only flying recon (or hitting it)
  pins it to a real hostile NATO symbol drawn as what it actually is
  (an infantry cell, a roadside IED, a named leader, a stronghold's militia) instead of anonymous armor.
  And the insurgency **moves** and comes at you as the right kit: the named leader travels as a small
  **convoy** you have to find and run down in his home valley (not a parked jeep waiting to be bombed),
  the cells are technicals and riflemen, and some roadside devices are **suicide VBIEDs** — a lone truck
  that drives for your nearest forward base, so you intercept it en route or it detonates and costs you
  at the mandate. (Only Enduring Resolve is tuned for the moving insurgency for now.)
- A new **Nevada - Red Flag 81-2** campaign — the ultimate war game, played as the war it rehearses. An
  F-4E wing detachment deploys to **Nellis, January 1981** (after the Reflected Simulations campaign the
  squadron flies) against the **integrated Red Force of the real 1981 exercise**: 64th/65th **Aggressor
  F-5Es** flying MiG-21 GCI hit-and-run, the **4477th "Red Eagles" Constant Peg MiGs out of Tonopah Test
  Range** (their actual 1981 field), an **SA-2/SA-3/SA-6/SA-8 emulator array around Tolicha Peak**,
  Fire Can-directed **KS-19 flak belts** on every corridor, four F-86-dressed **mock airfields**, and a
  simulated enemy army on a FEBA north of Camp Mercury — the range laydown **re-pointed at the commercial
  81-2 campaign's own mission files** (a NEW game picks it up). The whole **Vietnam mechanics
  stack rides along** — Red Flag *is* the institutionalized Vietnam feedback loop — political will as the
  TAC assessment, the static front as the exercise FEBA, and a three-phase escalation arc (**Week One →
  Force on Force → Surge Week**) that releases target classes as you prove the force. The **Groom Lake
  box never opens** — enter it and the assessment bleeds, exactly like the real range.
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

Most campaign-facing systems have their own setting or plugin toggle — e.g. the combat-SAR
**enemy-capture race** (the enemy trying to seize a downed pilot) is a `combatsar` plugin option you
can turn off, and the AI rescue package is gated by the `Automatic Combat SAR` setting; existing
campaigns keep whatever they were saved with.

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
