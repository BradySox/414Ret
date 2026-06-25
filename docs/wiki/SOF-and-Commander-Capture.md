# SOF and Commander Capture

This is the campaign-layer half of [SCAR](SCAR): instead of just killing the high-value target,
you can try to **capture the enemy commander alive** using a finite, purchased special-operations
team. A clean grab maps the enemy command network for the rest of the campaign; a botched grab
strands your team behind enemy lines and starts a rescue subplot. It is the fork's most
involved, multi-turn gameplay loop — a small economy of consumable assets wrapped around the
SCAR hunt.

It is **experimental** and gated by one setting:

> **`scar_command_post_intel`** (Campaign Doctrine) — **default ON for new campaigns** while it
> is being playtested. Existing saves keep whatever they were saved with. Turn it off to restore
> plain enemy command-post visibility and remove the SOF economy.
>
> **In-game-pass status:** the planner, capture loop, and command-post fog are verified in-game;
> the **mis-ID penalty** Lua (checklist F5) and the full capture → permanent-reveal carryover
> across turns (F2) still owe a pass. Treat the path as experimental.

---

## Why capture anyone?

With the feature on, enemy **command posts are hidden entirely** from your map — you cannot see
where the enemy is run from. Capturing an enemy commander on a SCAR sortie is **how you map that
command network**: a clean capture permanently reveals the enemy command posts, with exact
coordinates. So the SOF loop is an intelligence campaign, not just a body count — you are trading
a scarce team and a risky insert for a lasting picture of the enemy's command structure.

---

## SOF teams are a finite, bought asset

The capture team is a real, procurable, naturally-finite campaign unit — not an abstract counter:

- It is a **dedicated, buyable infantry unit** (`SOF Team (BLUFOR)` / `(OPFOR)`), priced at **8**
  — roughly the cost of the default mis-ID penalty, so wasting a team and prosecuting the wrong
  convoy hurt about the same.
- You buy it like any ground unit, but it is **player-only**: the AI never buys, deploys, or uses
  SOF teams. By design the team is kept **out of front-line deployment ratios, combat-strength
  scoring, and redeployment math**, so it sits in inventory as a special asset rather than
  feeding the ground war.
- Your **pool** is simply how many SOF units your coalition holds across its bases. The generator
  will only offer a SOF insert while you have teams, capped per turn at the number available.

---

## The loop, turn by turn

### 1. Buy a team and plan the insert

Stock a SOF team at a rear base, then plan a **SOF insert** — a dedicated `FlightType.SOF` flight.
Key points:

- The insert is a **C-130 airdrop**: it is flown by **fixed-wing transports** (C-130/An-26), not
  helicopters. Helos are reserved for the **recovery** leg. It reuses the air-assault delivery
  spine to drop the team at the SCAR area's **ambush point** along the HVT's route.
- Fragging the insert **debits one team** from the origin base — once per target per turn,
  regardless of what happens next. (Buy-and-fly is the spend; the outcome decides whether you get
  it back.)
- The EW (C-130J) plugin is correctly **skipped on the SOF insert C-130**, so you can't fly the
  electronic-warfare jet and run a SOF insert on the same airframe in one mission.
- If you don't fly the insert, a scripted fallback team is spawned so the loop never silently
  dies — but flying it for real is the intended play. The F10 mark reads "airdrop your SOF team
  here," and the capture binds to a player-delivered team found near the ambush point (within
  ~2500 m), falling back to the scripted spawn otherwise.

### 2. The grab, in-mission

Your job on the SCAR sortie is to find the real HVT and **not** kill the command vehicle — you
want it alive. Outcomes are ranked **killed > captured > escaped/timeout**:

- **Clean capture** — the un-killed command vehicle drives into the capture radius **while your
  SOF team is still alive**. The team grabs the commander and **escapes with the prisoner** ("no
  one dares attack while the commander is a hostage"). The enemy command posts are **revealed
  permanently, with exact coordinates**, and the capture **refunds** the team — it got out, so it
  nets out the debit-on-frag.
- **Botched / late** — the team is on the ground but the grab fails or comes too late. The team
  is **stranded** behind enemy lines and becomes a rescue objective next turn (below). No refund
  yet — recovery is the only way to get the team back.

### 3. If stranded: the recovery subplot

A stranded team is surfaced **next turn as a first-class "downed SOF team" map objective** — a
real TGO at the strand point, attached to the nearest friendly control point, that **persists
across turns** until it is recovered or overrun.

- **Loss conditions:** it ages out after a **3-turn cap**, or is lost if the enemy front
  **overruns** its position.
- **Recovery (helo only):** you get the team back two ways, and either one **refunds** the bought
  team (it only refunds once):
  1. A dedicated **`FlightType.CSAR`** helo air-assault flown at the objective that survives the
     sortie, **or**
  2. A **[Combat SAR](Combat-SAR)** flight extracting it in-mission as a MOOSE CASEVAC pickup.

This SCAR SOF-recovery `CSAR` is **distinct** from the Combat SAR pilot-rescue flight type,
though a Combat SAR helo can service both. A team recovered by both paths still refunds only
once.

---

## The economy at a glance

| Event | Team cost | Intel / objective effect |
|---|---|---|
| Buy a SOF team | pay 8 (price) | Adds one team to your pool |
| Frag a SOF insert | debit 1 team (per target/turn) | Team airdropped at the ambush point |
| **Clean capture** | **refund 1 team** | Enemy command posts revealed permanently |
| **Botched grab** | no refund (yet) | Team stranded → "downed SOF team" objective next turn |
| Recover a stranded team (CSAR or Combat SAR) | **refund 1 team** | Objective cleared |
| Stranded team ages out (3 turns) or is overrun | team lost | Objective removed |

The net effect: a successful capture costs you a risky sortie and an insert but returns the team
and a lasting intel win; a failure costs you the team unless you mount a rescue.

## Settings reference

| Setting | Default | Effect |
|---|---|---|
| `scar_command_post_intel` | ON (new campaigns) | Hides enemy command posts; enables the SOF buy/insert/capture/recovery loop |
| `scar_misid_penalty` | 8 | Budget cost of prosecuting the wrong convoy on the SCAR hunt (0 disables) — see [SCAR](SCAR) |
| SOF team price | 8 | Cost of one purchased SOF team |
| Stranded-team turn cap | 3 | Turns a downed SOF team objective survives before it is written off |

## See also

- [SCAR](SCAR)
- [Combat SAR](Combat-SAR)
- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)
- [Mission planning](Mission-planning)
