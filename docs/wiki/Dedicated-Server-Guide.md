# Dedicated Server Guide

Retribution generates a fresh `.miz` for each turn, and that mission runs like any other
DCS mission — including on a **DCS dedicated server**. This is how a squadron flies a
Retribution campaign co-op: one person runs Retribution and generates the turn, the
mission goes on the server, everyone flies it, and the results come back into the campaign.
This page covers the workflow and the multiplayer settings that matter.

## The big picture

Retribution stays a desktop app. You do **not** run Retribution on the server. The loop is:

1. On a normal client install, plan the turn in Retribution and press **Take off** to
   generate the next-turn mission (`retribution_nextturn.miz`).
2. Put that `.miz` on the dedicated server and run it.
3. The squadron joins the server and flies it. As the mission runs, in-mission events
   (kills, captures, runway damage) are written to a results file.
4. Pull the results back to the Retribution machine and submit them, advancing the
   campaign. Generate the next turn and repeat.

## Server setup

Run DCS headless with a batch file launching `DCS.exe --server --norender`. The DCS
WebGUI server manager (its `index.html`) handles administration — uploading the mission,
starting/stopping, and managing slots.

A dedicated server is worth using even for a small group or solo play: it offloads the
simulation and improves frame rates. One quirk to expect is that AI wingmen can behave
oddly during taxi when the mission runs server-side.

## Server configuration (scripting access)

Retribution missions rely on injected Lua plugins (see [Lua Plugins](Lua-Plugins)), and
some need access DCS sandboxes by default. On the server you must edit
`MissionScripting.lua` to comment out the sanitization lines that remove the `os`, `io`,
and `lfs` packages.

- This has to be redone after every DCS update — patches restore the defaults.
- If you run slmod, apply the same change to its parallel MissionScripting file.

## Mission preparation

Generate the mission on a regular Retribution client, not the server. Pressing **Take off**
produces `retribution_nextturn.miz`, which is ready to fly — it does **not** need to be
opened or re-saved in the Mission Editor first. Copy that file straight to the server.

## Results management

While the mission runs, events update a state/results file (Retribution writes campaign
state to `state.json`). After the flight:

- Confirm the results file's timestamp updated (proof the mission wrote its outcome).
- Submit the results in Retribution to advance the campaign. If automatic pickup misses,
  submit them manually through Retribution's interface.

Keep the campaign save and the results file together, and back up saves between turns — a
save migrated by a newer build is not readable by an older one.

## Multiplayer and co-op notes for squadrons

- **SRS for Flight Control ATC voice.** The fork's **Flight Control** plugin gives
  players-only tower sequencing at friendly land bases and speaks over SRS, with an
  optional text fallback. Have your SRS server running and players connected so the tower
  comms are audible (see [Lua Plugins](Lua-Plugins) and the in-game features overview).
- **"Never delay player flights."** For squadron play, enable the *never delay player
  flights* option so human flights aren't held on the ramp waiting for an AI scheduling
  slot — players spawn ready to go.
- **Player tasks are built for groups.** SCAR, Combat SAR, JAMMING, and TARPS are designed
  to be flown by humans; plan packages so the slots your pilots want are present in the
  generated mission.
- **DTC export is per-machine.** The native F/A-18C DTC cartridge is mirrored into the
  generating machine's Saved Games library, so it does not distribute to other players over
  multiplayer — it is off by default anyway.

## See also

- [Lua Plugins](Lua-Plugins) — what runs inside the generated mission
- [Custom Campaigns](Custom-Campaigns) — generating the missions you fly
- [Getting Started](Getting-Started) — installing and running Retribution
- [Mission planning](Mission-planning) — building the packages your squadron flies
