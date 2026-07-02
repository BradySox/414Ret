# The Vietnam Campaign Layer

The **campaign layer** is the war *over* the war. The [Vietnam Ops](Vietnam-Ops) suite makes the
*missions* feel like 1968 — flak, Arc Light, the trail. This layer makes the **campaign** play
like it: you don't win by rolling the front to Hanoi (you can't — the front barely moves), you
win at the **negotiating table**, by breaking Hanoi's resolve before Washington's patience runs
out, inside an escalating **Rules-of-Engagement arc** that decides what you're even *allowed* to
hit this month — against an enemy that fights, and escalates, the way the NVAF and NVA actually
did.

It ships in the **four Vietnam campaigns** (Khe Sanh: Operation Niagara · 1968 Yankee Station ·
Operation Velvet Thunder · Steel Tiger), which pre-seed the toggles on. Everything is default-off
globally: a modern or Cold-War campaign sees none of it.

> **New game required for the doctrine half.** The political will, front, phases, and ROE arc
> all pick up on any save — but the *doctrine*-side behaviour (Alpha Strikes, ambush MiGs, the
> fighter economy, red's air-defense posture) is baked into a campaign when it's created. Start
> a fresh Vietnam campaign to get all of it.

---

## Political will

*Toggle: **Political will tracking** (Vietnam Ops page, "Campaign" section) — pre-seeded on.*

Two meters decide the war:

- **Your Political Will** — Washington's patience. Drained by **airframe losses** (weighted by
  type: **losing a B-52 is a national event**), **POWs** sitting in Hanoi (a per-turn drain for
  every turn they're held — another reason Combat SAR matters), **ROE violations** (kills inside
  an active restricted zone — see the arc below), and lost ground.
- **The enemy's Regime Resolve** — Hanoi's capacity to absorb the war. Drained by **attrition**
  and by **strangling the trail** (logistics losses hurt the regime more than body counts).

Hit zero on either side and the war ends at the table, whatever the map says:

- **Regime Resolve exhausted → you WIN**: *"Hanoi agrees to terms."* No base capture required —
  the pressure campaign did what the front line never had to.
- **Political Will exhausted → you LOSE**: *"Washington orders withdrawal."*
- Territory victory still applies — a conventional map win stays a win.

**Where you see it:** the two meters live on the **campaign status ribbon** over the map (with a
trend sparkline), a **Political will tab** in the Stats window graphs both sides across the whole
campaign, the turn SITREP calls out big swings, and the Intel box in the Qt UI carries the
current numbers.

## The static front

*Toggle: **Static front (bounded siege line)** — pre-seeded on.*

Vietnam's ground war was **attrition in place, not maneuver** — Khe Sanh was besieged for
77 days without the line meaningfully moving. With this on, each front **bends with the strength
battle inside a narrow band (±10 %) around where the campaign started** but never sweeps onto a
base to capture it. The strength battle still matters — it feeds the will economy, where the war
is actually decided — and **deliberate Air Assault operations remain the one territorial lever**
if you want to take ground the hard way.

## The ROE arc — Rolling Thunder to Linebacker II

All four Vietnam campaigns run an authored **campaign-phase arc** (a Vietnam-flavoured layer on
the generic [campaign phases](Vietnam-Campaign-Layer#campaign-phases-generic) feature):

**Rolling Thunder → The Bombing Halt → Linebacker → Linebacker II**

Each phase carries the era's **political restrictions**, and the map shows them:

- **Restricted zones** — red dashed circles (sanctuaries: Hanoi's ring, the PRC border buffer).
  The **AI planner will not task strikes inside them**. *You* are never hard-blocked — the
  LBJ-era pilot could always break the rules — but kills inside an active zone are **ROE
  violations** that drain your Political Will at the debrief. The zone layer lives in the map
  layers panel ("Enemy intel" group), and hovering a zone explains what it is and when it eases.
- **Target release** — early phases keep whole target classes **locked** (factories, power, oil,
  airfields…). Locked targets show a **RESTRICTED — ROE** badge on their tooltip instead of
  vanishing — you can see the target you're not allowed to hit yet, which is the defining
  Rolling Thunder frustration, on purpose.
- **The schedule** — the arc advances on historical-feeling turn pins (Halt ≈ turn 8,
  Linebacker ≈ 11, Linebacker II ≈ 16), **accelerated by your bleeding will**: as Washington's
  patience drops, restraint gets voted out and escalation comes early. Historically backwards-
  sounding; historically true.
- **The phase ribbon** over the map names the current phase, explains it, and (click the chip)
  expands the whole arc with what each phase locked and released.

## Red answers the arc

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

<a name="campaign-phases-generic"></a>
> **Campaign phases in general.** The phase machinery isn't Vietnam-only: *every* campaign
> tracks an inferred phase (Air Superiority → Interdiction → Offensive) from its live IADS, air
> threat, and front movement, shows it on the ribbon/kneeboard, and leans the auto-planner's
> offensive tasking to match (`Campaign phases` toggle, Campaign Management page, default on).
> The Vietnam campaigns simply *author* their arc instead of inferring it — which is what carries
> the ROE payload and the red tempo.

## Practical notes

- **Turning it off.** Each piece has its own toggle (Vietnam Ops page "Campaign" section +
  Campaign Management for phases); all default off globally and are pre-seeded by the four
  Vietnam campaigns. Toggling mid-campaign is safe — the layer arms/disarms cleanly.
- **New Game.** The New Game wizard's **Vietnam** card filters the campaign list to the era, and
  selecting a Vietnam campaign pre-seeds the Ops + campaign-layer toggles in one step.
- **Watch your losses, not just your kills.** Under the will economy a "successful" strike that
  costs two Phantoms and leaves a POW in Hanoi can be a net loss. Combat SAR sorties, ROE
  discipline, and trail interdiction are all *strategic* acts here, not flavour.
- **Status.** The layer's model logic is fully unit-tested and the ROE arc has been verified
  across a live fast-forwarded campaign (turns 1 → 8 → 11 → 16 ran exactly as authored, zero AI
  violations). The flown-combat rows — will pacing, the front band under fire, ambush-MiG feel,
  the red tempo's multi-turn feel — are on the in-game pass checklist (M1–M6).

## See also

- **[Vietnam Ops](Vietnam-Ops)** — the mission-level suite this layer sits on: Arc Light, flak,
  the trail, the gaggle, napalm.
- **[Air Defense & the Air War](Air-Defense-and-the-Air-War)** — the generic CAP/escort planning
  this doctrine tunes.
- **[Combat SAR](Combat-SAR)** — rescue the pilot before he becomes a will-draining POW.
- **[Map Layers & Interface](Map-Layers-and-Interface)** — the restricted-zones layer, campaign
  ribbon, and events feed.
