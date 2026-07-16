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
  site, a deployed vehicle group, or a missile site appears only as a dashed **amber "suspected
  activity" circle** offset from the truth ("in here somewhere") until recon or an attack
  localizes it — amber, so it can't be mistaken for the dashed red ROE off-limits circle — so the Weasel hunt and the SCUD hunt are real hunts. Fixed infrastructure
  stays exact (airfields, buildings, the big strategic SAM sites, EWRs, ships), the circle
  is clickable so you can still plan recon or a strike against the suspected area, and the
  whole behaviour is a Difficulty & Realism toggle (**on** by default for new campaigns).
- And once you get there, **mobile missile sites shoot and scoot**: SCUD/SSM launchers drive
  to a new position every few minutes during the mission (holding fire while they move), so
  the launcher is never quite where the last recon photo froze it. The site stays within a
  few km of its campaign position, kills count normally, and the radar SAM network never
  moves. On by default (Mission Generation → "Mobile missile sites relocate"); a naval
  campaign can also opt its coastal anti-ship batteries (Silkworms) into the scoot
  (**"Coastal anti-ship sites relocate too"**, off by default), so the coastal-missile
  hunt is a hunt too.
- **The roads have traffic now — and your convoys might get ambushed.** Every turn, a few
  real supply columns run each side's road network (a randomized number, sometimes sharing
  a road, sometimes spread out): the enemy's are ordinary Armed Recon/BAI prey, and yours
  are yours to worry about. Because sometimes — it's a chance, never a certainty — hidden
  enemy ambush teams dig in along a friendly convoy's route: one contact, or a gauntlet of
  five or six down the same road. Nothing is telegraphed: the convoy looks like any other
  friendly convoy, no objective or escort package shows in the UI, and the first sign of
  trouble is the TROOPS IN CONTACT call when an ambush springs mid-mission. Fly to the
  column's aid and clear the ambushers, or let it fight through alone — your call. Both the
  convoys and the ambushers are real, tracked units — losing a column costs you real
  reinforcements, and the debrief counts both sides' losses. Both behaviours are **on by
  default** for new campaigns (Mission Generation → "Ambient supply convoys" / "Friendly
  convoy ambushes") on any campaign whose map has roads between friendly bases.
- **You can mine the roads yourself.** DCS has no mines, so we fake them: load the **"Aerial
  Minefield"** loadout (a CBU-99 dispenser — on the A-7E, Hornet, or Harrier) and drop it on a
  road, and the impact area becomes a live minefield. An enemy supply convoy that drives across it
  takes real losses **the same mission** you laid it — mine the road just ahead of an inbound
  column to stop it cold. The mines kill real, tracked vehicles (the debrief counts them; they
  never arrive), only your side sees the field on the F10 map, and — with cross-turn persistence
  on — a field left undisturbed is still there next mission, wearing down over turns until it's
  spent. Opt-in (enable the "Air-droppable minefields" plugin in Plugin Options; the matching
  "Air-droppable minefields" setting adds the persistence across turns). You can also let the
  **auto-planner frag mining sorties for you** ("Auto-plan mining sorties ahead of enemy convoys"):
  it puts a mining strike against an enemy convoy in the ATO each turn — fly it yourself or let the
  AI take it. Blue-only.
- **Warships fire real cruise missile raids.** A Burke's Tomahawks (or the enemy's Kalibr
  ships, with the CurrentHill packs) finally do their job: put an F10 map marker on a shore
  target and call **F10 → Cruise Missile Strike** to ripple a salvo from the nearest capable
  ship (want a specific weight of fire? type just a number in the marker's text — `6` or
  `#6` — and exactly that many fly) — or turn on auto raids and each side commits one salvo a turn at its best reachable
  target (command bunkers and comms first, then war industry), announced to the defender only
  as a bare **"LAUNCH WARNING — enemy cruise missile launch detected"**. The missiles are real
  weapons from real, sinkable ships: kills count at debrief, and every ship carries a
  **finite campaign magazine with no rearm** ("Magazine status" on the same F10 menu shows
  what's left) — so a salvo
  spent on a truck park is a salvo you won't have for the command bunker. Opt-in (Mission
  Generation → "Ship-launched cruise missile strikes" + "Auto-plan cruise missile raids").
- **The enemy's IADS jams your radios — once it knows your channels.** By default the enemy
  learns your comms plan the hard way: **off a captured pilot**. Lose the Combat SAR race and
  within minutes your briefed channels take sporadic bursts of barrage static — transmitted
  from a real enemy comms mast or command bunker with real power falloff (worst deep over the
  C2 belt), and SRS hears it too (SRS tunes off your cockpit radios). While a POW is held, the
  next missions launch already compromised — until you free them (retake the holding field) or
  the comms plan is rotated. GUARD, ATC and a briefed **JAM BACKUP** channel (printed on the
  kneeboard Mission Info page, next to the code words) always stay clean, and the noise comes in duty-cycled bursts, never a
  wall — hop channels, push to the backup, or kill the node: one strike on the C2 site silences
  the jamming *and* degrades the IADS. So SAR matters twice over, and the squadron learns to
  rotate compromised channels. Opt-in (Mission Generation → "Enemy comms jamming"; the
  captured-pilot intel gate is on by default, or disable it for ambient jamming) and preseeded
  on in Red Tide, where the radio isn't clean either.
- **A briefing card greets you when you slot in.** Just like the professional DCS campaigns, a few
  seconds after you take a seat a short card appears on screen: the **campaign name**,
  **mission number**, **date and time**, then your own **callsign, aircraft, task, and departure
  field** — so you always know what you're flying before opening a kneeboard. A **second card**
  follows it with the startup call — *"Get started up, Contact ground @ 249.50 when ready to
  taxi"* (that ground frequency is a plugin option), and a **short beep** plays as each card flashes.
  Both fire at mission start in single-player and whenever anyone slots in or rejoins on a server,
  showing each pilot their own flight's details. Purely informational (nothing changes in the
  mission). On by default (Mission Generation → "Mission-start briefing popup"); the card duration,
  the ground frequency, and the beep are plugin options.
- **Big missions run smoother — without deleting the battlefield.** The old culling option was all
  or nothing: a distant unit either fully existed or was never spawned at all. The new **"Distant
  ground AI sleeps until aircraft approach"** (Mission Generation → Performance) is the middle
  ground: rear-area garrisons keep existing — visible, strikeable, kills count exactly as before —
  but their AI is switched off while nobody is near, cutting the sim cost of hundreds of thinking
  ground units on a dense multiplayer mission. Any aircraft (yours, a wingman's, or an AI strike's)
  closing within ~15 NM wakes them seamlessly, and getting shot wakes them instantly. SAM sites,
  the front-line battle, convoys and every scripted mover are never touched, so nothing about the
  war changes — only the frame rate. Off by default; works alongside (or instead of) culling.
- **The host can summon bandits.** For multiplayer events: with **"Host tool: F10 red-interceptor
  scramble menu"** on (Mission Generation), the host gets an F10 **HOST: Red Scramble** menu that
  launches a fresh 2- or 4-ship of the enemy's own fighters from any red airfield — or, with one
  **EMERGENCY** press, from the base nearest your airborne flights — and vectors it straight onto
  the nearest friendly fighters. The "give the boys something to shoot" button for a session that
  goes quiet after the first wave. Set your DCS player name — or just its static part
  ("Flash" matches "Viper 1-1 | Flash" whatever the flight prefix) — in the plugin's *Host
  player names* option so only you see the menu (empty shows it to every BLUE client). The
  bandits are free event content: killing them changes nothing in the campaign. Off by
  default; preseeded on in Red Tide, already gated to the host's name tag.
- **Bombing the enemy HQ actually matters now.** Destroy a side's IADS command posts and its
  auto-planner gets *sloppier* — the more of its command network you knock out, the more
  unpredictable and less effective its offensive target selection becomes turn to turn, so
  decapitating the enemy's command-and-control is a real strategic play instead of a strike
  checkbox. Its reactive defenses are never affected (a headless enemy still defends itself), and
  your kneeboard SITREP reports the enemy's command status so you can see the strike land. Opt-in
  (Air Doctrine → "Command-center kills degrade enemy planning"); a campaign with no command posts
  is unaffected.
- **Bomb the enemy's fuel, factories, and supply lines and watch their war effort wither.** With the
  **War economy** on (Campaign Management), each base runs a real materiel supply chain — factories
  produce it, it flows over the roads to the front, and it's spent holding the line. Interdict it —
  strike the factories, cut the routes — and a starved enemy front stops recovering, fields fewer units,
  and gives ground, with the kneeboard SITREP showing you why. Bomb an airfield's **fuel depots** and it
  flies fewer sorties next turn. And with **Munitions availability** on (Mission Generation → Loadouts),
  airfields hold a stock of the scarce precision munitions — run a field dry of JDAMs (or knock out its
  ammo dumps) and its jets fall back to dumb bombs, greyed out in the loadout screen. A **Supply status**
  map layer colours each of your fronts by how well-supplied it is (with the producers feeding it), and
  each base card reads out its front supply and munitions on hand. All symmetric — protect your own
  supply too — and off by default.
- **The enemy commander plays with intent — and remembers the war.** With **Red Intent** on (Air
  Doctrine), the AI reads the war each turn — the ground balance, its air strength, how the last turn
  went — and, crucially, the **trend across turns**: it notices when you've been dismantling its SAM
  belt, when its resolve is cracking, when it's bleeding bases. It adopts a *posture* that carries
  across turns instead of planning the same way every time: it **surges** when it holds the advantage
  (pressing to take ground, committing its reserves, striking with focus), **consolidates** when it's
  under pressure (defending, husbanding), or grinds it out in between — and it reacts to the *shape* of
  your campaign, so a winning enemy that watches its air defenses come apart will **dig in even while
  it still outnumbers you**, and one that catches your fighters spent will **lunge through the gap**. It
  even presses *harder* the further ahead it is and turtles *harder* the deeper the trouble. A
  colour-coded **"ENEMY" chip on the map ribbon** (and your kneeboard SITREP) names the enemy's posture
  and *why* ("Surging (all-in)", "Consolidating — IADS falling") so you can read its mood — and with the
  war economy on, **bomb its supply and a winning enemy digs in**. On a **multi-front** war it now holds a
  *separate* posture per front — pressing on the front it's winning while it digs in on the one it's
  losing — and a single **boldness** dial lets you tune its whole temperament from cautious to reckless
  (plus how sticky its posture is and how far back it reads the war's trend). Opt-in and enemy-only (your
  side's "intent" is the campaign phase), and it never touches the enemy's reactive defenses. **Germany —
  Red Tide** ships with it on.
- **Bomb the enemy's motor pool before its armor reaches the front.** A base's not-yet-deployed
  armor reserve now shows up as a **strikeable depot** on the map — hit the parked vehicles at the
  motor pool and the owner has to repurchase them next turn, so you can attrit the reserve directly
  instead of only meeting it at the front line. Depot strikes don't move the front (they're tracked
  separately from front-line casualties), and the parked reserves hold fire. On by default; **Germany —
  Red Tide** stages one at Haina by the Fulda Gap (its parked tanks fill in as the Soviets buy armor),
  and any campaign can place its own. *(Adopted from upstream Retribution PR #859.)*
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
- The map **explains itself**: a collapsible **Legend** button (bottom-right) decodes the
  overlay colours — friendly/enemy/front line, the amber "suspected activity" vs red "ROE
  off-limits" dashed circles, weapons-free pockets, supply health — and the things you can
  right-click to plan a mission (front lines, enemy supply routes, target markers,
  suspected-activity circles) show a pointer cursor plus a hover hint naming the action, so
  fragging a package straight off the map is discoverable instead of a hidden gesture.
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
  and held as a **POW at an enemy airfield**. A captured pilot is pulled from the flying roster (they
  show as **POW** in the squadron and can't be fragged while captive), named on your kneeboard SITREP
  each turn with where they're held, and **recapturing that field brings them back**. Every turn they're
  held saps your side's political will. On a **political-will (Vietnam) campaign** the hold is
  indefinite — the drain is a real running sore Hanoi holds over Washington — and a **negotiated victory
  brings your POWs home** (a defeat writes them off); on other campaigns they're lost for good after a
  few turns. If you fly with **invulnerable player pilots** on, your own captured pilots are returned
  rather than killed. The capture is the consequence for losing the rescue fight — there is no separate
  raid mission to plan. (The old armor-hunt SCAR is retired — SCAR is a rescue role now.)
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
  pilot first they are **captured** — held as a POW (see SCAR above). **The snatch race runs even
  when nobody can come for them** — turning auto-CSAR off or flying without a rescue helo doesn't
  make your pilots un-capturable; it makes them *more* exposed. And a pilot who is neither rescued
  nor captured by mission end is **not lost — they go MIA and keep evading**: they show on the
  SITREP and roster, re-appear at their last known position next mission (red smoke, a fresh enemy
  snatch race), and can still be rescued. Each turn they're out, a pilot near the front usually
  keeps evading while one **deep behind the lines almost certainly gets found** and becomes a POW —
  so think twice before pressing deep with no rescue plan. There's no timer: they evade until
  rescued, recovered, or caught (`Downed pilots persist` setting, on by default).
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
- **Fuel-first planning: tanks are fitted for the sortie, then the tanker passes are
  decided.** Once a package is built and the route is known, a jet short of gas gets drop
  tanks on its **empty** tank-capable stations (on far-AO campaigns — like the COIN carrier
  parked ~800 km off the beach — a Hornet strike flies out with its third bag), and — when
  filling empties still isn't enough — a self-protection **jammer pod gives up its seat to a
  bag, but only when that saves a whole tanker pass** (a SEAD Viper that used to plan pre-
  AND post-vul refueling now flies three bags and one pass). The tanker decision **counts
  the fuel in the bags** instead of internal fuel alone, so jets stop double-tanking on
  sorties their real load covers, and the kneeboard fuel ladder agrees. Nothing else is ever
  swapped (never a targeting pod, decoy, or ordnance), it does nothing on short routes, and
  loadouts you've customized are always left alone (both toggles live in Mission Generation →
  Loadouts). **The fuel plan shows in the flight editor**: the Payload tab has a live line under
  the fuel slider — burn vs. carried (internal + bags), tanker passes planned, and the RTB
  margin — that recomputes as you drag the fuel slider or edit pylons, and turns amber with a
  "short of getting home" warning if your edits leave the jet dry.
- **The planner frags a pre- or post-strike tanker when a sortie can't make it home.** If the
  route burns more than the jet can carry, it's sent to a tanker on the way in (or out) instead
  of launching short — and this now works for mod jets that ship no measured fuel data (e.g. the
  F-4E), which used to fly the whole leg untanked while the kneeboard warned "short of getting
  home." No tanker in the campaign? Then the RTB-margin warning stands and you plan a divert.
- An optional **auto-planner unpredictability** doctrine knob (per side, off by default)
  varies which offensive targets the enemy services first, so red stops striking the same
  targets in the same order every turn. Its reactive air defenses stay just as sharp.
- Doctrine controls expose patrol-altitude floors and scatter, and the aircraft task
  priorities have received a conservative role-based rebalance.
- Soviet/Russian air defenses use improved legacy SAM layouts and radar composition.
  Campaign-map SAM rings, emitters, routes, and IADS links are easier to inspect and read.
- **One HARM no longer kills a whole SAM site.** Every SAM battery now fields **two**
  guidance radars (track radars, or the combined search/track unit on systems like the SA-6),
  spaced far enough apart that a single missile can't take both — a site keeps shooting after
  the first radar dies, and real SEAD takes a follow-up shot or a strike. Applies to new
  campaigns; purchased sites default to the pair but can be trimmed in the buy menu.
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
- **Navy jets wear real squadron modexes.** Hornet and F-14 board numbers used to be random
  three-digit noise; now each Hornet/Tomcat squadron gets its own modex block (100, 200,
  300, … — Tomcats take the traditional 100/200 fighter blocks) and its jets are numbered in
  sequence within it: the first jet 100, the second 101, and so on across the whole mission.
  Two squadrons never share a block, and every other airframe keeps its normal number.
  Always on — nothing to configure.

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
- The kneeboard is the **classic Retribution deck** (Mission Info → Support Info → task pages),
  with the 414th's additions folded into those pages instead of extra ones. The **Mission Info
  page opens on a BLUF block**: your task, target and TOT; the push/success/abort code words; the
  JAM BACKUP channel when the enemy is jamming; a compact **air + SAM threat picture**
  (`SA-5 S-200 138nm · SA-11 Buk 27nm`); your **loadout** in one line; and the **SAR** assets +
  if-down drill. Below it, the standard airfield table, the flight plan, bullseye, weather,
  bingo/joker and laser codes.
- A **"last turn" SITREP** (both sides' losses — the enemy's as *claimed* — bases captured or
  lost, and downed pilots recovered) closes the Mission Info page from your second mission on,
  hiding after a quiet turn (*Campaign SITREP band*, Kneeboards page, on by default).
- When several flights share an airframe (DCS stacks them into one kneeboard), a **flight
  index** page — each callsign, task, and start page — fronts the deck so you flip straight to
  your own block.
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
  `PUSH <word>` tag on the join waypoint — to build a briefing. In the cockpit, your own words
  ride the Mission Info BLUF and the full colour-keyed table (your task marked) sits on the
  Support Info page. Fresh words every turn, stable while you plan. Off by default.
- The **fuel ladder rides in the flight plan**: the Mission Info steerpoint table has a `Fuel`
  column — planned fuel remaining at each steerpoint — with the RTB margin (how much you have to
  spare over what you need to get home — negative means tank or divert) called out once under the
  table. No separate page, no toggle. Works for **every** flyable airframe: aircraft without
  hand-measured fuel data (the C-130J "King", the helicopters, warbirds, ...) get a rough estimate
  derived from their fuel capacity.
- Plugin settings explain what each system does and use squadron-readable labels and units.
- A new *Restrict aircraft options by campaign date* setting (sibling of the weapons toggle —
  enforce either or both) gates era-defining **cockpit options**: a pre-2003 campaign no longer
  offers (or quietly spawns) a **JHMCS** helmet-mounted sight, falling back to the period-correct
  visor — likewise the A-10C II's Scorpion HMCS (2012) and the MiG-29's HMS. NVG and other
  era-appropriate options stay available.
- The weapons toggle also makes the **support trucks** at airbase and FARP ground-starts
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
  doesn't sit on the map as a marker at its exact position at all; it shows as a dashed **amber
  "suspected activity" circle** offset from the truth ("in here somewhere"), and only flying recon (or hitting it)
  pins it to a real hostile NATO symbol drawn as what it actually is
  (an infantry cell, a roadside IED, a named leader, a stronghold's militia) instead of anonymous armor.
  And the insurgency **moves** and comes at you as the right kit: the named leader travels as a small
  **convoy** you have to find and run down in his home valley (not a parked jeep waiting to be bombed),
  the cells are technicals and riflemen that **wander their patch of countryside** (and the infiltrators
  taking your ungarrisoned base creep toward it during the mission), a roadside IED is an **emplaced
  device with a security team dug in around it** — kill the bomb and it's cleared even if the team runs;
  strafing the guys alone doesn't defuse anything — and some devices are **suicide VBIEDs**, a lone truck
  that drives for your nearest forward base, so you intercept it en route or it detonates and costs you
  at the mandate. The war also comes to *you*: friendly airfields and FOBs within mortar reach of a
  living stronghold draw **sporadic insurgent rocket/mortar fire** during the mission (never the field
  you spawn at) — pushing the strongholds back is what silences it.
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
  the Gap (Apaches, Kiowas, Hueys) with the front line routed through it — and it lives like a
  frontline FARP: fields within artillery reach of the front (Fulda, and red's Haina spearhead)
  draw **sporadic enemy artillery harassment** during the mission (never the field you spawn at;
  the "Frontline artillery harassment" setting, preseeded here). Frankfurt adds a
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
