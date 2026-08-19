# Fog of War and Reconnaissance

Every enemy site is on your map from turn one, at its real position. What is actually parked
there is not. Composition, unit counts, and threat and detection rings stay hidden until you
engage the site — and once you engage it, you know everything about it, permanently.

This page covers that rule, the hidden command posts, the "approximate target area" precision
mode, the hiding of mobile SAMs from the datalink, and the overview toggle that reveals ground
truth.

## What you know, and what stays hidden

Fog is applied only to the human (BLUE) map and dialogs. The AI planner and all threat math
always use ground truth, so the enemy never gets dumber because you are fogged.

| | Shown | Hidden |
|---|---|---|
| An un-engaged enemy site | position, category, allegiance, air-defence band, valid mission types | unit types, unit counts, live/dead state, threat ring, detection ring |
| An engaged enemy site | everything, including current damage | nothing |

The same enemy SAM site, before and after:

![The target intel dialog for an un-engaged enemy SAM site: known live units, detection range, and threat range all read "Unknown (not scouted)", and the units list reads "Not yet scouted — composition unknown"](https://raw.githubusercontent.com/BradySox/414Ret/main/docs/wiki/img/fog-intel-not-scouted.png)

*Before — you know it exists, its type band, and which missions are valid against it. Live
units, detection range, and threat range all read "Unknown."*

![The same site after engagement: known live units 9/9, detection range 54 NM, threat range 27 NM, and the full unit list resolved to SA-11 Buk "Gadfly" launchers, command, search radar, and support vehicles](https://raw.githubusercontent.com/BradySox/414Ret/main/docs/wiki/img/fog-intel-scouted.png)

*After — 9/9 live, 54 NM detection, 27 NM threat, and the actual SA-11 Buk composition you now
have to plan SEAD/DEAD against.*

## What counts as engaging it

Either of these, flown by your side:

- **Ordnance on the site.** Any unit destroyed there reveals it.
- **A ground-attack sortie that reaches it and comes home.** Strike, DEAD, SEAD, SEAD Sweep,
  SEAD Escort, Anti-ship, BAI, CAS, or Armed Recon — the crews saw what was down there. Kills
  are not required.

A flight that is shot down before it gets there reveals nothing.

**Recon does not reveal an ordinary site.** Flying TARPS over one tells you nothing you did
not already know. The fog is meant to be lifted by attacking, not by scouting. Recon has
exactly one job, below.

Discovery is permanent and total. Once a site is engaged there is no second confirmation step —
you see its damage the moment the strike lands, and it stays known for the rest of the campaign,
across save and load.

The master switch is **`recon_intel_fog`** (Campaign Doctrine page, **default ON**). Turn it off
and nothing is ever hidden. Saves made before the feature existed load fully revealed, so the
fog is felt on new campaigns.

## Hidden command posts — and the one thing recon is for

A separate gate, the **"Hidden enemy command posts"** setting (**default ON** for new campaigns),
hides enemy **command posts** entirely — no marker, not plannable, not strikable.

That makes them the one target engagement cannot reach: you cannot put ordnance on something you
cannot see. So **flying TARPS recon is how you find them**. A recon flight that comes home
reveals any hidden command post within about 3 NM of the area it was sent to photograph, and you
get a "RECON: enemy command post located" message. Once found, a command post shows fully, with
exact coordinates, and can be planned against like anything else.

Mapping the enemy command network is therefore its own campaign task, and recon is the tool for
it. Toggle the setting off under Difficulty & Realism → Realism & restrictions to make command
posts plainly visible instead.

## Uncertainty circles

One class of contact does not get an exact marker: the insurgent spawns on the
[COIN campaign](Enduring-Resolve-Campaign-Briefing) — roadside IEDs and VBIEDs, HVT convoys, and
dispersed cells. Those draw a dashed amber "somewhere in here" circle offset from the true
position, because localizing them is the point of that campaign. A roadside IED's circle slides
along its highway rather than off into the fields: you know what road it is on, not which
stretch. The circle clicks and right-clicks like a marker, so you can plan against the suspected
area; engaging it snaps the contact to its real symbol.

Ordinary enemy sites are never circled.

## Approximate target area — making you find it

The **target location precision** setting (`EXACT` vs `APPROXIMATE`) changes how much help your
steerpoints and kneeboards give you. In **Approximate** mode:

- Player target steerpoints are offset to a randomized area **1–3 NM** from the real target, and
  the waypoint is renamed `TARGET AREA`. You fly to the area and visually acquire. AI attack
  logic is unaffected.
- **DEAD and SEAD** flights drop their per-emitter target points and fly a single fuzzed
  target-area waypoint instead.
- Objective F10 map marks are suppressed even if marks are otherwise on.
- Strike/SEAD/DEAD kneeboard pages omit exact coordinates. The SEAD/DEAD page shows one
  consolidated cue: a rough **bullseye for the centre of the site** (about 1 NM accurate) plus
  the single target-area steerpoint, then a description/ALIC table of the site's emitters.

**Strike is deliberately exempt** — its targets are fixed installations with reliable
coordinates, so Strike always gets exact per-unit points regardless of the setting.

## Mobile SAMs hidden from the datalink

Short-range and mobile air-defense units (SHORAD, AAA, MANPADS) are hidden from the MFD datalink
picture, including escort SAMs riding inside armor or missile groups. Standalone medium- and
long-range SAMs stay visible so SEAD can plan against them. You do not get a free, perfect
datalink fix on every pop-up MANPAD.

## Reveal fog of war (overview)

To plan against the real laydown — sketching a campaign, checking what is actually out there, or
running a debrief — tick **Reveal fog of war** in the map's layer panel (top-right, in the "Enemy
intel" group; see [Map Layers and Interface](Map-Layers-and-Interface)). It forces every
player-facing fog rule to ground truth: composition, threat and detection rings, and hidden
command posts all appear at once. Unticking re-hides everything.

This toggle is **transient by design**: it is never saved. A campaign file can never carry a
god-view, and a shared campaign can never leak one. It always defaults off and is the only map
layer choice the panel deliberately does **not** remember between sessions.

## Settings reference

| Setting | Default | Effect |
|---|---|---|
| `recon_intel_fog` | ON | Master switch. Hides an un-engaged site's composition and rings |
| Hidden enemy command posts | ON | Hides enemy command posts from the map entirely until a recon pass finds them |
| Target location precision | EXACT / APPROXIMATE | Offsets steerpoints, hides marks/coords, consolidates DEAD bullseye kneeboards |
| Reveal fog of war (map toggle) | OFF, never saved | Short-circuits all fog to ground truth |

## Caveats

- Fog is BLUE-only on purpose; red always plays against the truth.
- TARPS finds command posts and nothing else. It does not lift an ordinary site's composition
  fog — see [TARPS Reconnaissance](TARPS-Reconnaissance).
- The satellite-imagery recon **kneeboard** pages ship default-off. The marker/tile misalignment
  that kept them gated was fixed 2026-07-18; the toggle stays off until the fix gets an in-game
  pass. Turn on `Generate target recon kneeboard pages` to try them.

## See also

- [TARPS Reconnaissance](TARPS-Reconnaissance)
- [Map Layers and Interface](Map-Layers-and-Interface)
- [Mission planning](Mission-planning)
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
