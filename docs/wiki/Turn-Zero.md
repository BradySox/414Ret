# Turn Zero

Turn Zero is the special setup turn at the very start of a campaign. You do not fly anything during
Turn Zero — instead you spend your opening budget, position your forces, and let the campaign
initialize the front line and the air-defense picture. When you are satisfied, you commit and roll
into Turn 1, which is the first turn you actually generate and fly.

Keep one rule in mind throughout Retribution: **only events that happen inside a running mission
change the campaign.** Turn Zero is your chance to set the board before any of that starts.

## What happens during Turn Zero

When the campaign loads for the first time it:

- Reads your chosen faction and the campaign's preset squadrons to build your starting
  [air wing](Air-Wing-Configuration).
- Establishes the **front line (FLOT)** between the opposing control points and seeds frontline
  ground forces along it.
- Initializes the enemy **IADS** — SAM sites, EWRs, and the links between them — that the
  air-defense planner and threat math will reason about.
- Grants your opening budget so you can purchase reinforcements before the war begins.

## Initial purchases and positioning

**Aircraft.** Open each base, go to the **Airfield Command** tab, and use the **+** button to buy
airframes. Purchases arrive next turn, are capped by budget and parking, and can be cancelled
before you commit (sales are final). Buy to cover the missions you plan to run — CAP/BARCAP,
SEAD/DEAD, Strike, CAS, and support.

**Ground units.** Recruit from **Ground Forces HQ**. Turn Zero is unusually permissive: you can
reinforce *any* friendly control point. After Turn Zero, ground recruitment requires control points
with **factories**, and a convoy advances one supply-route segment per turn — so use this turn to
position your ground forces sensibly. Set offensive vs. defensive stance here too, depending on
whether you intend to push or hold.

**Auto Purchase.** If you would rather not micromanage, enable Auto Purchase to let the campaign
reinforce routine needs for you while you hand-buy only the squadrons and units you care about.

## Front and IADS initialization (fork notes)

Because 414Ret runs **recon intel-fog**, the enemy picture you see at Turn Zero is deliberately
incomplete. Newly seeded enemy sites can be *known to exist* without their composition, strength,
damage state, or threat rings being revealed — you have to scout or attack a site to confirm what
is actually there. This means you should plan your opening turns expecting to *discover* the
defenses, not assuming the map shows ground truth. See
[Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance) for how TARPS and the recon system
turn unknowns into confirmed intel.

When you need the real laydown anyway — sanity-checking a fresh campaign, planning the opposing
side, or just debugging — tick **Reveal fog of war (overview)** in the map's layer panel
(top-right, with the other enemy-intel toggles). It un-fogs the whole map and intel dialogs to show
true enemy composition, threat rings, and otherwise-hidden command posts. It is a *view toggle
only*: it never alters the campaign and is never saved, so you can flip it on to plan and off again
to play honestly.

## Ending Turn Zero

When you have spent what you want to spend and positioned your forces, commit the turn (the
**Begin Campaign** / proceed control) to advance into Turn 1. From there, every turn follows the
normal loop of planning, generating, and flying a mission — walked through in
[Your First Operation](Your-First-Operation).

## See also

- [Air Wing Configuration](Air-Wing-Configuration)
- [Your First Operation](Your-First-Operation)
- [Mission Planning](Mission-planning)
- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)
- [Squadrons and Pilots](Squadrons-and-Pilots)
