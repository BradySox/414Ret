# Fog of War and Reconnaissance

In 414Ret your intelligence picture is deliberately incomplete. The enemy laydown is not
handed to you fully revealed at the start of a turn, and post-strike battle-damage
assessment (BDA) lags until something actually goes and looks. This page explains the recon
model, the tools that fill in the picture (TARPS photo recon and the TARS film-and-debrief
engine), the "approximate target area" precision mode, the hiding of mobile SAMs from the
datalink, and the overview toggle that reveals ground truth when you want to plan or just
check the real picture.

The whole point: reconnaissance is a thing you fly, not a free fact you read off the map.

## What you know, and what stays hidden

Intel fog is applied only to the human (BLUE) map and dialogs. The AI planner and all threat
math always use ground truth, so the enemy never gets dumber because you are fogged.

Two rules drive the player-facing picture:

| Rule | What it does |
|---|---|
| **Recon intel-fog** | A newly appeared enemy site shows on the map as a targetable marker — you see its position, category, and allegiance — but its **composition and threat/detection rings stay hidden** until you attack, scout, or destroy it. Until then the intel panel reads "Not yet scouted — composition unknown." |
| **BDA damage lag** | When you strike an enemy site, its units keep showing as alive until a recon pass **confirms** the kill. You do not get an instant, accurate kill count just for dropping bombs. |

Discovery is sticky: once a site is scouted or attacked, it stays revealed. Both rules are
governed by the **`recon_intel_fog`** setting (Campaign Doctrine page, **default ON**). Older
saves are migrated to fully revealed, so the fog is felt mainly on new campaigns.

A third, related gate hides enemy **command posts** entirely from your map for the SCAR
commander-capture feature — see [SCAR](SCAR) and the `scar_command_post_intel` setting.

## TARPS — flying the photos

`TARPS` is a real, player-flyable flight type for the F-14. Every F-14 variant carries the
TARPS reconnaissance pod, and the recon bird flies a clean overflight of the target (no
bombing tasks — it is there to take pictures, not fight). The flight plan puts a single
overflight waypoint roughly five minutes behind the strikers so you photograph the target
just after the strike goes in.

The auto-planner can append one TARPS sortie to Strike and DEAD packages automatically when
**`auto_add_tarps_recon`** is enabled and a TARPS-capable squadron is available. You can also
plan TARPS by hand like any other task.

## TARS — turning photos into confirmed intel

TARPS would just be a sightseeing flight without something to turn the overflight into actual
campaign intelligence. That is the **TARS recon engine** (`tars` plugin, **default ON**), a
MOOSE runtime that handles the in-mission side:

- An F10 "film" menu and automatic overfly detection.
- Coalition F10 map markers where you photographed.
- A landing debrief that feeds the BDA system the exact enemy units your surviving recon pass
  saw.

When a TARPS bird overflies a struck site and lands safely, the units it photographed are
**confirmed** — their true alive/dead state snaps into your picture, clearing the BDA lag for
that site. No surviving recon pass, no confirmation. Several plugin options are exposed
(scoring, film limit, SRS voice); the playtested defaults ship turned on. The TARPS→BDA
bridge has passed an in-game validation pass.

## Approximate target area — making you find it

The **target location precision** setting (`EXACT` vs `APPROXIMATE`) changes how much help
your steerpoints and kneeboards give you. In **Approximate** mode:

- Player target steerpoints are offset to a randomized area **1–3 NM** from the real target,
  and the waypoint is renamed `TARGET AREA`. You fly to the area and visually acquire — AI
  attack logic is unaffected.
- **DEAD and SEAD** flights drop their per-emitter target points and fly a single fuzzed
  target-area waypoint instead (mobile SAMs relocate between intel updates, so an exact
  per-launcher fix would defeat the "go find it" intent).
- Objective F10 map marks are suppressed even if marks are otherwise on.
- Strike/SEAD/DEAD kneeboard pages omit exact coordinates. The SEAD/DEAD page shows one
  consolidated cue: a rough **bullseye for the center of the site** (about 1 NM accurate) plus
  the single target-area steerpoint, then a description/ALIC table of the site's emitters.

**Strike is deliberately exempt** — its targets are fixed installations (buildings, bunkers,
bridges) with reliable coordinates, so Strike always gets exact per-unit points regardless of
the setting.

## Mobile SAMs hidden from the datalink

Short-range and mobile air-defense units (SHORAD, AAA, MANPADS) are hidden from the MFD
datalink picture, including escort SAMs riding inside armor or missile groups. Standalone
medium- and long-range SAMs stay visible so SEAD can plan against them. The intent: you do not
get a free, perfect datalink fix on every pop-up MANPAD.

## Reveal fog of war (overview)

When you want to plan against the real laydown — sketching a campaign, double-checking what is
actually out there, or running a debrief — tick **Reveal fog of war** in the map's layer panel
(top-right, in the "Enemy intel" group; see [Map Layers and Interface](Map-Layers-and-Interface)).
It forces every player-facing fog rule to resolve to ground truth for whoever is looking:
enemy composition, threat and detection rings, post-strike kills, and even hidden command
posts all appear at once. Unticking re-hides everything.

This toggle is **transient by design**: it is never saved. A campaign file can never carry a
god-view, and a shared campaign can never leak one. It always defaults off and is the only map
layer choice the panel deliberately does **not** remember between sessions.

## Settings reference

| Setting | Default | Effect |
|---|---|---|
| `recon_intel_fog` | ON | Master switch for recon intel-fog + BDA damage lag |
| `auto_add_tarps_recon` | — | Auto-append a TARPS sortie to Strike/DEAD packages when a TARPS squadron is available |
| Target location precision | EXACT / APPROXIMATE | Offsets steerpoints, hides marks/coords, consolidates DEAD bullseye kneeboards |
| TARS plugin | ON | In-mission film/overfly/debrief engine that confirms BDA |
| Reveal fog of war (map toggle) | OFF, never saved | Short-circuits all fog to ground truth |

## Limitations and caveats

- The TARPS→BDA bridge has been verified in-game; the satellite-imagery recon **kneeboard**
  pages remain gated off because marker overlays do not reliably line up with the tiles (a
  known, separate geometry bug).
- Fog is BLUE-only on purpose; red always plays against the truth.

## See also

- [Map Layers and Interface](Map-Layers-and-Interface)
- [Mission planning](Mission-planning)
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
- [SCAR](SCAR)
