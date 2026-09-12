# IADS Engine: Skynet

The **IADS engine** is the runtime brain behind enemy air defenses. Without it, each SAM is an
isolated, always-on radar that any HARM can pick off. With it, the enemy's surface-to-air picture
behaves like an **Integrated Air Defense System**: an EWR or AWACS hands tracks to the SAM best
placed to shoot, sites defend against anti-radiation missiles, mobile launchers shoot and scoot,
and losing the right node degrades the whole network. That networked behavior is the single
biggest reason SEAD and DEAD are planned the way they are in this fork — see
[Air Defense and the Air War](Air-Defense-and-the-Air-War) and [Mission planning](Mission-planning).

414Ret runs the same engine upstream does, **Skynet-IADS**, wired up automatically for every
campaign. There is no engine to choose.

---

![The campaign map with the enemy IADS network layer on: red SAM threat rings overlapping across the theater, with cyan command/early-warning links and green power/comms links tying the sites, EWRs, and command nodes together into one connected network](https://raw.githubusercontent.com/BradySox/414Ret/main/docs/wiki/img/map-iads-network.jpg)

*The enemy IADS as the map draws it: overlapping red threat rings, with the cyan links (track handoff / early warning) and green links (power & comms in advanced IADS) showing which nodes hold the network together — and therefore what's worth striking.*

## What the engine does

- **Networking and track handoff.** EWRs, AWACS, and radar SAMs share contacts; a site can shoot
  on someone else's track. Killing one early-warning radar doesn't blind the whole system if
  another can still see.
- **Reactive radar shutdown / HARM defense.** When a site detects an inbound anti-radiation
  missile it shuts its radar down, so your HARM loses the emitter it was homing on. Each SAM type
  has its own HARM detection chance.
- **Shoot-and-scoot.** With the mobile-SAM options on, SA-8/9/13/15/19 (and optionally
  SA-6/11/17) displace after emitting, so the fix you had a minute ago may be stale.
- **Point defense.** A site's co-located SHORAD is paired to it and covers it against the
  missiles it cannot dodge.
- **Autonomy when cut off.** A SAM that loses its early-warning coverage or its command network
  fights on alone with its own radar, as vanilla DCS AI would.

The consequence for you as a planner is constant: **a HARM is far less likely to score an emitter
kill than against a dumb, always-on SAM.** Plan SEAD as genuine *suppression* that holds the radar
down, and let **DEAD** close the kill with bombs or ATGMs against the launchers and command
vehicles a HARM can't reach.

---

## Advanced IADS — the comms/power/command graph

The deepest layer is **advanced IADS**: SAMs wired to **command centers, comms towers, and power
sources** whose destruction degrades the network. Take out a SAM's comms tower and it goes
autonomous (loses the shared picture); take out its power and the site dies; take out every
command center and the whole network goes autonomous. This is what turns "bomb the buildings"
into a real way to peel an IADS apart without killing a single launcher.

This is a general **engine capability**, not a one-campaign trick — the *Germany — Red Tide*
campaign's "real buildings as IADS nodes" is just the most visible consumer of it. Skynet carries
the graph natively, and the fork adds one thing on top: a node you destroyed on an earlier turn
stays destroyed. The campaign tells the mission which comms, power and command nodes are already
gone, so the SAMs behind a bombed power station do not come back next mission.

---

## Modded SAMs

The fork's compiled Skynet carries profiles for the **High Digit SAMs Ultimate Compilation**
(S-400, S-300V4, SAMP/T, Pantsir-SM and the renamed SA-10B radars) and for the **CurrentHill**
Russia, US, UK, Germany and China packs (Buk-M3, S-350, Pantsir-S1/S2, Tor-M2, NASAMS 3, THAAD,
Patriot, HQ-22, Sky Sabre and more). A modded site with a profile joins the network like any
vanilla one; a site with none fights alone as vanilla DCS AI.

---

## Settings reference

The plugin's options are upstream's, under **Plugins → Skynet IADS**.

| Setting | Default | Effect |
|---|---|---|
| Create IADS for RED / BLUE | on | Build each coalition's network |
| Include RED / BLUE IADS in radio menu | on | An F10 status menu per network |
| Enable Mobile SAMs SHORAD | off | SA-8/9/13/15/19 shoot-and-scoot, with emission time and scoot distances |
| Enable Mobile SAMs MERAD | off | The same for SA-6/11/17 |
| Adjust default SAMs GoLiveRange | off | Per-type go-live range for the SA-5/10/17/20/23 |
| `advanced_iads` (campaign) | per campaign | Enables the comms/power/command-center graph |

## See also

- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
- [Mission planning](Mission-planning) — the SEAD/DEAD decision guide
- [Electronic Warfare and ISR](Electronic-Warfare-and-ISR)
- [Custom Campaigns](Custom-Campaigns)
