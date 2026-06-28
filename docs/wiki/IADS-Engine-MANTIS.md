# IADS Engine: MANTIS

The **IADS engine** is the runtime brain behind enemy air defenses. Without it, each SAM is an
isolated, always-on radar that any HARM can pick off. With it, the enemy's surface-to-air picture
behaves like an **Integrated Air Defense System**: an EWR or AWACS hands tracks to the SAM best
placed to shoot, sites defend against anti-radiation missiles, mobile launchers shoot and scoot,
and losing the right node degrades the whole network. That networked behavior is the single
biggest reason SEAD and DEAD are planned the way they are in this fork — see
[Air Defense and the Air War](Air-Defense-and-the-Air-War) and [Mission planning](Mission-planning).

414Ret runs **one** IADS engine — **MANTIS** — and it is wired up automatically for every new
campaign. There is **no engine to choose**: the old MANTIS-vs-Skynet selector is gone (see
[below](#what-happened-to-skynet)).

---

## What an IADS engine does

- **Networking and track handoff.** EWRs, AWACS, and radar SAMs share contacts; a site can shoot
  on someone else's track. Killing one early-warning radar doesn't blind the whole system if
  another can still see. (Detection rides on the **early-warning layer** — EWRs and AWACS — not on
  each SAM searching alone, so taking down the right EWR genuinely degrades coverage.)
- **Reactive radar shutdown / HARM defense.** When a site detects an inbound anti-radiation
  missile, it shuts its radar down (and, for mobile types, may relocate), so your HARM loses the
  emitter it was homing on, with a per-SAM ARM budget.
- **Shoot-and-scoot.** Mobile SAMs displace after emitting, so the fix you had a minute ago may be
  stale.

The consequence for you as a planner is constant: **a HARM is far less likely to score an emitter
kill than against a dumb, always-on SAM.** Plan SEAD as genuine *suppression* that holds the radar
down, and let **DEAD** close the kill with bombs or ATGMs against the launchers and command
vehicles a HARM can't reach.

---

## MANTIS

MANTIS is the MOOSE-based engine (`Functional.Mantis`), the actively-maintained option — MOOSE
ships every couple of months — which is why the fork standardised on it. It provides:

- **Network-level SEAD / HARM defense** — radar-off plus relocate on an inbound ARM, with a
  per-SAM ARM budget.
- **AWACS as a sensor** with configurable range, plus datalink fusion and acoustic/non-radar
  detection.
- **Reliable detect-and-engage.** By default the fork runs MANTIS with **emissions control off**
  so sites actually detect and shoot — full go-dark emissions control was found to leave the
  network too passive in practice. Reactive shutdown on an inbound HARM still applies.

How it discovers sites is invisible to you as a player: MANTIS finds SAM/EWR groups by **name
prefix** and infers type and behaviour from the unit. 414Ret keeps its **own Python IADS graph**
as the source of truth and drives MANTIS from it, banding each site by its **longest-ranged SAM**
(its Retribution missile-engagement zone) so a mixed site is classified correctly.

---

## Advanced IADS — the comms/power/command graph

The deepest layer is **advanced IADS**: SAMs wired to **command centers, comms towers, and power
sources** whose destruction degrades the network. Take out a SAM's comms tower and it goes
autonomous (loses the shared picture); take out its power and the site dies; take out a command
center and the network's coordination degrades. This is what turns "bomb the buildings" into a
real way to peel an IADS apart without killing a single launcher.

This is a general **engine capability**, not a one-campaign trick — the *Germany — Red Tide*
campaign's "real buildings as IADS nodes" is just the most visible consumer of it. MANTIS has no
native comms/power graph, so the fork **rebuilds the degradation behaviour as an event-driven
layer over MANTIS**, reusing the same Python IADS graph, gated by the campaign's `advanced_iads`
flag.

---

## What happened to Skynet

Earlier builds shipped two engines — MANTIS and Skynet-IADS — and let you pick one per campaign.
**Skynet has been removed.** The `skynetiads` plugin, the `iads_engine` selector, and all the
dual-engine wiring are gone; **MANTIS is the sole engine**. The shared IADS *data model* that both
engines used (the Python `IadsNetwork` / `IadsRole` / `IadsProperties` graph, including the
`Skynet*` back-compat names) stays — MANTIS consumes it — so nothing about how campaigns describe
their air defenses changed.

**Existing saves still load.** A campaign created back when Skynet was an option opens fine; the
old per-save engine pin is migrated out automatically, and the campaign simply runs on MANTIS from
then on. You do not need to do anything.

---

## Settings reference

| Setting | Default | Effect |
|---|---|---|
| (engine selection) | — | **None.** MANTIS is the only engine; there is nothing to choose. |
| `advanced_iads` (campaign) | per campaign | Enables the comms/power/command-center degradation graph layered over MANTIS |

## See also

- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
- [Mission planning](Mission-planning) — the SEAD/DEAD decision guide
- [Electronic Warfare and ISR](Electronic-Warfare-and-ISR)
- [Custom Campaigns](Custom-Campaigns)
