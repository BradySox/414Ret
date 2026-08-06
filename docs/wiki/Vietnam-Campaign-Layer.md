# The Vietnam Campaign Layer

The **campaign layer** is the war *over* the war. The [Vietnam Ops](Vietnam-Ops) suite makes the
*missions* feel like 1968 — flak, Arc Light, the trail. This layer makes the **campaign** play
like it: era-authentic taskings and engagement ranges, Alpha Strikes massed on one target,
MiGs that ambush from GCI rather than fly Western BARCAP, and a red side whose tempo answers
the campaign clock.

It ships in the **three Vietnam campaigns** (1968 Yankee Station · Operation Velvet Thunder ·
Red Flag 81-2), which pre-seed the toggles on. Everything is default-off globally: a modern or
Cold-War campaign sees none of it.

> **New game required.** The doctrine-side behaviour — Alpha Strikes, ambush MiGs, the fighter
> economy, red's air-defense posture, the period planner ranges — is baked into a campaign when
> it is created. Start a fresh Vietnam campaign to get it.

> **Removed on 2026-07-21.** This layer originally carried a **political-will economy** (win at
> the negotiating table by breaking Hanoi's resolve before Washington's patience ran out), a
> **static front**, and an escalating **Rolling Thunder → Linebacker II ROE arc** that decided
> what you were allowed to hit each month. All three are gone, along with the `will:`,
> `phases:` and zone blocks that authored them; the old machinery is described for historical
> reference only on [Campaign Phases and ROE](Campaign-Phases-and-ROE). What survives from that
> work is **red tempo** (below) and the **GCI ambush** posture.

---

## Red answers the campaign clock

The enemy isn't a mirror of you, and it isn't static either.

- **Hanoi's air force flies air defense, not your playbook.** Red Vietnam factions run a
  dedicated **air-defense doctrine**: full MiGCAP stacks over their bases, no massed strikes, no
  fighters wasted banking escorts for raids the NVAF never flew.
- **Ambush MiGs (GCI doctrine).** Red interceptors scramble **late** (raid ~40 NM out, not at
  the border), run a **close, slashing intercept** (knife-fight ranges, not BVR duels), then
  **break off and run home** — a leash at ~50 NM from base plus an early fuel bingo. You get hit
  once, hard, near your target, by MiGs that live to ambush again — the actual NVAF playbook.
- **The Bombing Halt is a logistics window.** While the Halt holds, the trail runs **two
  concurrent, bigger convoys** (see [Convoy interdiction](Vietnam-Ops#4--convoy-interdiction-steel-tiger))
  and **Hanoi's resolve regenerates** (~1.5/turn). Waiting out the halt is not free — every quiet
  turn hands the regime leverage back. Fly the trail war or pay for the pause.
- **The Easter Offensive.** When the arc enters **Linebacker**, red's ground forces surge: for
  about three turns every active front goes **aggressive**, with the trail surging alongside.
  The static-front band still holds — the offensive **bleeds your will** through frontline
  attrition rather than sweeping bases — and it lands exactly when your ROE finally opens up,
  which is the same bitter irony 1972 served.

## Your air war fights like 1968 too

The Vietnam campaigns run a period **air doctrine** that changes how the auto-planner fights,
not just what things are called:

- **Era taskings.** MiGCAP, GCI Intercept, Iron Hand, Interdiction, Sandy, College Eye — the
  display layer renames the taskings to the period vocabulary (the underlying mission types are
  unchanged).
- **No SEAD, and strikes go anyway.** Vietnam air wings have no reliable defense suppression, so
  the modern "suppress before you strike" rule is off: strikes press into defended areas and fly
  without a full escort rather than deadlocking the whole offensive fleet.
- **Knife-fight ranges.** Early Sparrows and short-range Sidewinders mean CAP and escorts engage
  at visual-merge distances (≈22/10 NM), not modern BVR standoff.
- <a name="the-real-alpha-strike"></a>**The real Alpha Strike.** The planner masses a
  **deck-load on one target**: up to **four coordinated, shared-time-on-target strike sections**
  plus a **forced fighter escort**. Only the first section is guaranteed — the rest surge on as
  squadron inventory allows, so the top-priority target absorbs the strike fleet and later
  targets get the leftovers. The **"Alpha Strike" name is earned**: only a package massing ≥2
  sections and ≥4 bombers wears it; a lone section reads plain "Strike." And **nobody strikes
  alone** — strike sections are floored at 2 ships.
- **The fighter economy serves the bombers.** Rear support orbits (AWACS/tanker) fly unescorted
  — they hold stations the leashed MiGs can't reach anyway — and a **fighter reserve is fenced
  for strike escorts**: BARCAP thins (coldest bases first, never the hottest) and non-strike
  packages can't spend the last fighters, so the MiGCAP goes where the MiGs will actually be:
  on the bombers' wing.

## Practical notes

- **Turning it off.** Each piece has its own toggle on the Vietnam Ops page; all default off
  globally and are pre-seeded by the Vietnam campaigns. Toggling mid-campaign is safe — the
  layer arms/disarms cleanly.
- **New Game.** The New Game wizard's **Vietnam** card filters the campaign list to the era, and
  selecting a Vietnam campaign pre-seeds the Ops + campaign-layer toggles in one step.
- **Watch your losses, not just your kills.** A "successful" strike that costs two Phantoms and
  leaves a crew in Hanoi is a poor trade — squadrons are finite and a captured pilot stops
  flying. Combat SAR sorties and trail interdiction are strategic acts here, not flavour.
- **Status.** The layer's model logic is unit-tested. The flown-combat rows — ambush-MiG feel
  and the red tempo's multi-turn feel — are on the in-game pass checklist (M5–M6).

## See also

- **[Vietnam Ops](Vietnam-Ops)** — the mission-level suite this layer sits on: Arc Light, flak,
  the trail, the gaggle, napalm.
- **[Air Defense & the Air War](Air-Defense-and-the-Air-War)** — the generic CAP/escort planning
  this doctrine tunes.
- **[Combat SAR](Combat-SAR)** — rescue the pilot before he becomes a POW.
- **[Map Layers & Interface](Map-Layers-and-Interface)** — the campaign ribbon and events feed.
