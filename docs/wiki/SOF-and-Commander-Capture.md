# SOF and Commander Capture

> **Status (2026-06-27): the capture economy is dormant.** The SOF-team / commander-capture loop
> described on most of this page was driven by the in-mission SCAR **armor-hunt** scenario, which
> was **retired** when SCAR became the ["Sandy" rescue escort](SCAR). With the armor-hunt Lua
> plugin gone, nothing in a generated mission triggers a commander grab or strands a SOF team, so
> the buy → insert → capture → recover chain **does not fire in the shipped build**. The campaign
> scaffolding (the `scar_command_post_intel` setting, the SOF team unit, the recovery objective) is
> still present but inert pending a decision on its future. **The one part that is still live is the
> command-post fog**, described first below.
>
> The spiritual successor for "captured personnel" is the **[Combat SAR](Combat-SAR)** POW path: a
> downed pilot seized by an enemy snatch party becomes a POW you can recover.

---

## What's still live: enemy command-post fog

This part works today and is independent of the (dormant) capture loop. With
**`scar_command_post_intel`** on (Campaign Doctrine, **default ON for new campaigns**), enemy
**command posts are hidden entirely** from your map — no marker, not plannable or strikable —
until you **discover them the normal way**: strike near them, scout them, or photograph them on a
[TARPS](TARPS-Reconnaissance) pass. Once discovered, a command post shows fully, with exact
coordinates.

So with the feature on, mapping the enemy's command network is a reconnaissance task: you don't
get the command laydown for free, you have to find it. Turn `scar_command_post_intel` off to
restore plain enemy command-post visibility.

| Setting | Default | Effect |
|---|---|---|
| `scar_command_post_intel` | ON (new campaigns) | Hides enemy command posts until you discover them by strike / scout / TARPS |

---

## The capture economy (dormant — how it used to work)

For reference, this is the loop that is currently inert. It hung off the old SCAR armor hunt: on a
SCAR sortie you found the enemy commander's vehicle and, rather than killing it, let a purchased
special-operations team grab it alive.

- **SOF teams were a finite, bought asset** — a buyable, player-only infantry unit (`SOF Team`),
  kept out of the front-line ground war, drawn down by flying an insert.
- **The insert was a C-130 airdrop** (`FlightType.SOF`) that dropped the team at the SCAR area.
- **A clean capture** permanently revealed the enemy command posts (the "commander captured"
  reveal) and refunded the team; **a botched grab** stranded the team behind enemy lines as a
  next-turn **"downed SOF team"** objective.
- **A stranded team** was recovered by a `FlightType.CSAR` helo air-assault or a
  [Combat SAR](Combat-SAR) CASEVAC pickup (refunding the team), or lost if abandoned past a turn
  cap or overrun by the front.

`FlightType.SOF` and `FlightType.CSAR` still exist as flight types, and the recovery/refund Python
code is still in the tree, but without the armor-hunt trigger none of it is reachable in a normal
campaign. If the commander-capture mechanic returns, it will be re-wired to a new in-mission
trigger; this page will be updated when it does.

## See also

- [SCAR](SCAR) — now the "Sandy" rescue escort (the armor hunt this loop hung off is retired)
- [Combat SAR](Combat-SAR) — the live capture/POW path for downed pilots
- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)
- [Mission planning](Mission-planning)
