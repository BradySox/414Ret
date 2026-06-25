# Troops In Contact

**Troops In Contact (TIC)** replaces vanilla DCS ground AI at the front line with prolonged,
formation-aware firefights. Instead of letting stock ground AI instantly erase a frontline
engagement, TIC keeps maneuver units in formation, has them trade theatrical suppressive
fire, and moves them according to each side's combat stance — so the ground battle is
something you can actually fly close air support over for the length of a sortie.

TIC is a **plugin, default ON**. You can toggle it per campaign on the LUA Plugins Options
page ("Troops In Contact").

## What TIC changes at the front

- **Prolonged firefights.** Frontline tank/IFV/APC/ATGM groups become formation-keeping TIC
  combatants that hold a fighting line and exchange fire over a battle arc sized to roughly
  1.5–2 hours, rather than annihilating each other in seconds.
- **Ambient suppressive fire.** The 414th extension adds area "suppression" fire: a combatant
  with no line-of-sight target has a chance each firing cycle to lob a salvo near the closest
  enemy formation within about 6 km — tracers arc over line-of-sight blockers, but the fire
  is **not aimed for lethality**. It makes the line look and sound alive without turning into
  a mass-casualty event.
- **Per-stance movement.** Each formation moves according to its **combat stance**, so the two
  sides don't run the same script and collide as a symmetric wall:

  | Stance | Behavior |
  |---|---|
  | Aggressive | Standoff fighting distance, light slide-and-press assault |
  | Breakthrough | Straight thrust, deeper penetration, faster cadence |
  | Elimination | Repeated slide/press cycles to hunt line-of-sight |
  | Defensive | Dig in at standoff range, occasional low-chance counterattack |
  | Ambush | Most rearward hold, never counterattacks |
  | Retreat | A single fallback leg |

- **Distributed FLOT formations.** Frontline groups are spread along the line rather than
  piled onto one patch of terrain, so the front reads as a line of contact instead of a
  single blob.
- **Staggered cadence.** Movement is staggered per group so the line ripples forward instead
  of lurching all at once.

## How it changes CAS / BAI gameplay

Because TIC keeps the battle alive, the front becomes a **persistent CAS and BAI
environment**. The scripted fire produces only sparse near-miss kills by design — the real
attrition source is **you**. The campaign front moves on **player kills**, not on TIC's own
fire, so flying CAS over a contested sector genuinely matters to how the ground war develops.

### Known limitation: StormTrooper AI

With TIC's StormTrooper AI on (the default), TIC **cloaks its managed units from DCS AI
sensors**. That means **AI CAS flights and the AI JTAC cannot detect the enemy frontline** —
only human CAS works against it. If you want AI ground combat visible to AI air, turn
StormTrooper off in the plugin options; you trade some of the scripted-battle polish for
real-AI detectability.

## See also

- [Frontline-Stances-and-Movement](Frontline-Stances-and-Movement)
