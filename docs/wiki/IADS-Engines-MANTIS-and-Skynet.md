# IADS Engines: MANTIS and Skynet

The **IADS engine** is the runtime brain behind enemy air defenses. Without it, each SAM is an
isolated, always-on radar that any HARM can pick off. With it, the enemy's surface-to-air picture
behaves like an **Integrated Air Defense System**: radars stay dark until they're needed, an EWR
or AWACS hands tracks to the SAM best placed to shoot, sites defend against anti-radiation
missiles, mobile launchers shoot and scoot, and losing the right node degrades the whole network.
That networked behavior is the single biggest reason SEAD and DEAD are planned the way they are
in this fork — see [Air Defense and the Air War](Air-Defense-and-the-Air-War) and
[Mission planning](Mission-planning).

414Ret ships **two** engines. You pick one when you create a campaign, on the Mission Generator
settings page.

> **In-game-pass status:** MANTIS is the default but its core networking pass (checklist G6) is
> **partial** — a C2 regression was found and fixed; it still needs a re-fly on a zone-node map.
> Skynet is the long-standing, flight-proven engine. If you want maximum stability today, Skynet
> is the conservative choice.

---

## What an IADS engine does

Both engines provide the same core behaviors; the differences are in how they model them.

- **Emissions control (go-dark).** SAMs keep their radars off by default and only come up when
  there's something to engage, so you can't just troll for emitters at leisure.
- **Networking and track handoff.** EWRs, AWACS, and radar SAMs share contacts; a site can shoot
  on someone else's track. Killing one early-warning radar doesn't blind the whole system if
  another can see.
- **Reactive radar shutdown / HARM defense.** When a site detects an inbound anti-radiation
  missile, it shuts its radar down (and, for mobile types, may relocate), so your HARM loses its
  emitter to home on.
- **Shoot-and-scoot.** Mobile SAMs displace after emitting, so the fix you had a minute ago may
  be stale.

The consequence for you as a planner is constant across both engines: **a HARM is far less
likely to score an emitter kill than against a dumb, always-on SAM.** Plan SEAD as genuine
*suppression* that holds the radar down, and let **DEAD** close the kill with bombs or ATGMs
against the launchers and command vehicles a HARM can't reach.

---

## The two engines

### MANTIS (default for new campaigns)

MANTIS is the MOOSE-based engine (`Functional.Mantis`). It is the more actively-maintained option
— MOOSE ships every couple of months, where Skynet's last release was at the end of 2023 — and
the fork migrated to it for future-proofing. MANTIS reaches parity-or-better with Skynet on the
things that bite in the air:

- **Emissions control** — dark by default, radars up only on contact.
- **SEAD / HARM defense** — a sophisticated network-level model: radar-off plus relocate on an
  inbound ARM, with a per-SAM ARM budget.
- **AWACS as a sensor** with configurable range, plus bonuses Skynet doesn't have (datalink
  fusion and acoustic/non-radar detection).

How it discovers sites differs under the hood: MANTIS finds SAM/EWR groups by **name prefix** and
infers type and behavior from the unit, where Skynet wires each site explicitly. 414Ret keeps its
own Python IADS graph as the source of truth and drives MANTIS from it, so this is invisible to
you as a player.

### Skynet (still selectable)

Skynet-IADS is the previous engine and remains fully supported. Its model is built around an
**explicit, fine-grained graph**: every SAM is registered by its exact generated group name and
individually wired to the comms towers, power sources, command centers, and point-defense sites
near it, with per-unit tuning (go-live range, HARM-detection chance, autonomous behavior when cut
off). That explicit per-unit control is where Skynet is still richer than MANTIS's
inferred-by-type approach.

Skynet stays selectable as the conservative, flight-proven fallback while MANTIS finishes its
in-game passes.

---

## Advanced IADS — the comms/power/command graph

The deepest layer is **advanced IADS**: SAMs wired to **command centers, comms towers, and power
sources** whose destruction degrades the network. Take out a SAM's comms tower and it goes
autonomous (loses the shared picture); take out its power and the site dies; take out a command
center and the network's coordination degrades. This is what turns "bomb the buildings" into a
real way to peel an IADS apart without killing a single launcher.

This is a general **engine capability**, not a one-campaign trick — the *Germany — Red Tide*
campaign's "real buildings as IADS nodes" is just the most visible consumer of it. Skynet models
this graph natively. MANTIS has no native comms/power graph, so the fork **rebuilds the
degradation behavior as an event-driven layer over MANTIS**, reusing the same Python IADS graph,
so that campaigns get the same advanced-IADS behavior on either engine. (This C2 layer is part of
the partial in-game pass noted above.)

---

## Choosing and switching

- You select the engine **when you create a campaign** (Mission Generator → IADS engine). The
  choice is **fixed for that save**.
- **Existing campaigns keep whichever engine they were created with** — there's a save-state pin,
  so loading an older campaign never silently switches engines under you. That's why a campaign
  started before the MANTIS default stays on Skynet.
- New campaigns default to **MANTIS**; switch to **Skynet** in the dropdown if you'd rather fly
  the flight-proven engine while MANTIS finishes validation.

The engine affects only **newly generated missions** for that save; it changes nothing about how
you plan packages day to day beyond the SEAD/DEAD guidance above.

## Settings reference

| Setting | Default | Effect |
|---|---|---|
| `iads_engine` | MANTIS (new campaigns) | Which engine drives enemy air defenses; Skynet selectable; pinned per save |
| `advanced_iads` (campaign) | per campaign | Enables the comms/power/command-center degradation graph |

## See also

- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
- [Mission planning](Mission-planning) — the SEAD/DEAD decision guide
- [Electronic Warfare and ISR](Electronic-Warfare-and-ISR)
- [Custom Campaigns](Custom-Campaigns)
