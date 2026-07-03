<!-- 414Ret wiki: how the fork plans the air war. Modeled on the upstream
     wiki tone; documents the 414th's air-defense planning rework, QRA reserve,
     SEAD/DEAD behavior, and the IADS engine note. Cross-links Mission-planning. -->

# Air defense and the air war

414Ret reworks how a Retribution campaign plans its air war so it behaves like a campaign
rather than a queue of isolated sorties. The auto-planner holds interceptors in reserve, lays
overlapping and threat-weighted fighter coverage, anchors its support orbits on the front,
refuses to send bombers through a live SAM belt, and keeps mobile short-range defences off
your datalink so you plan SEAD against the sites that matter. This page explains each piece and
how it changes what you see when you build packages.

For the per-task fragging detail (SEAD vs DEAD, BARCAP timing, escorts), see
[Mission-planning](Mission-planning). Two campaign-level layers also steer the planner's
*offensive* priorities: the **[campaign phase](Campaign-Phases-and-ROE)** (which objectives get
first claim on offensive jets this month) and, on ROE campaigns, the restricted-zone gate (the
AI never strikes into an active sanctuary). Reactive defense — everything on this page — is
never touched by either.

## QRA intercept reserve

Squadrons can hold aircraft back in a **QRA (quick-reaction alert) intercept reserve** for
runtime base defence, instead of having every airframe fragged into the ATO.

- The reserve is **per squadron** (`intercept_reserve`), clamped by owned aircraft and
  available untasked pilots. Aircraft in the reserve are not auto-fragged — they wait on alert.
- At runtime, raids that close on a defended base scramble interceptors via a Moose
  `AI_A2A_DISPATCHER`. Many alert bases each put up a **small** response (a 1-ship / 2-ship mix),
  so a raid draws interceptors from several directions rather than one base launching a big
  formation.
- Defaults are a **base-defence posture**: QRA scrambles only when a raid closes within a set
  radius and interceptors chase a limited distance, so QRA does not screen forward over the
  FLOT. Both are live Campaign Doctrine settings (`qra_gci_max_radius_nm`,
  `qra_engagement_range_nm`), so you can re-tune them per campaign.

The reserve is edited in the air-wing / squadron dialogs; see
[Air-Wing-Configuration](Air-Wing-Configuration). The old ramp-scramble system is retired — QRA
is the only live reactive-A2A path.

## Reworked BARCAP coverage

Defensive fighter coverage was reworked so contested sectors get more and the whole line gets
useful forward coverage, while quiet flanks keep baseline behaviour:

- **Overlapping, jittered waves.** Land-CP BARCAP is scheduled as overlapping waves with a
  jittered first wave, instead of front-loaded back-to-back waves that all arrive at mission
  start (which let attackers simply wait the CAP out). The `barcap_overlap_time` doctrine
  setting controls the overlap; `0` reproduces the legacy schedule.
- **Forward CAP line.** Coverage now also defends any friendly CP that anchors an **active front
  line**, so raids inbound to rear income points are screened — not just bases close to an enemy
  airfield.
- **Threat-weighted volume and placement.** How many BARCAP waves a defended CP receives, and
  how far forward the orbit sits, both scale with the **air** threat to that CP (proximity and
  number of A2A-capable enemy aircraft within range, plus a floor for active fronts). This is
  **additive only** — a contested sector earns up to roughly double the waves and a forward
  orbit; a zero-threat CP gets exactly the legacy coverage. Coverage never regresses below the
  baseline.
- **Red forward-middle BARCAP layer (large maps).** On a big map, a red front CP whose nearest
  blue field is off-axis would otherwise fling its screen far from the FLOT. 414Ret adds **one
  extra** BARCAP, placed roughly halfway from the rear CP to the FLOT and parallel to the front,
  **in addition to** the unchanged rear/base BARCAP. It is map-scaled (only fires when the rear
  orbit can't already cover the front), front-relative (no hardcoded distances), and red-side
  only.

The result: when you fly into a hot sector, expect layered, overlapping red CAP that commits
on you sooner; quiet flanks stay thin.

## Front-anchored support orbits

AWACS and tanker racetracks are anchored on the **active front line** and stand off into
friendly airspace, rather than being computed from a single control point's bearing (which
swung off-axis as the front moved, and could pin a tanker onto its own home runway).

- Support orbits centre on the FLOT nearest the supported area, then push back into friendly
  airspace along the stable enemy→friendly axis until they clear the enemy threat zone by the
  configured buffer.
- The **player** coalition holds forward (closer behind the FLOT, for coverage); the **AI**
  coalition holds deeper, so red tankers and AWACS don't loiter near the front.
- **You can find them from the cockpit.** Every blue tanker and AEW&C orbit is painted onto the
  generated mission's **F10 map** as a cyan dashed racetrack with a label — callsign, type,
  radio frequency, TACAN — so "where's my gas?" is answered by the F10 map, no DTC and no
  briefing screenshot needed. See
  [Map Layers and Interface](Map-Layers-and-Interface#what-the-dcs-f10-map-shows).

### Theater tanker placed on receiver demand

A shared theatre tanker is repositioned **after** the ATO is built, onto the count-weighted
centre of the flights that actually need fuel (honouring boom vs probe compatibility), instead
of orbiting wherever the planning anchor happened to land. Same-package buddy tankers are not
moved; if there is no compatible demand the tanker keeps its front anchor. So the tanker tends
to sit where your thirsty flights converge.

<a name="long-range-carrier-ops"></a>
## Long-range carrier ops

*Toggle: **Carrier operations** (`long_range_carrier_ops`, Campaign Management) — default off;
pre-seeded by campaigns that park the boat far out (Operation Enduring Resolve).*

Some campaigns stand the carrier hundreds of miles offshore — the real OEF Arabian-Sea cycle put
the boat ~400+ NM from the fight, which is past the stock planner's range gate, so every carrier
squadron just sat on deck. With this on, the boat joins the war deterministically:

- **One carrier package a turn**, fragged from the boat's own squadrons before the main planner
  runs: a 2-ship **strike** section (aimed at the nearest legal target, preferring ammo caches),
  an **A-6E buddy tanker** holding a real orbit off the boat for launch/recovery gas, and an
  **E-2** on AEW&C station — proper flight plans, shared TOT, forced through the range gate.
- **Everything from the boat tanks from the boat.** Any other carrier flight the commander frags
  in a tanker-less package (SEAD Hornets, escorts) has its refuel point pinned onto the buddy
  A-6's orbit, so the ingress top-off and recovery gas actually exist instead of a phantom
  refuel waypoint 500 NM from any tanker.
- Campaigns pair the toggle with a wider `max_mission_range_planes` so the carrier squadrons are
  assignable to normal tasking at that range at all.

No carrier, no capable jets, or no legal target ⇒ silent no-op. Blue-side only. See the
**[Enduring Resolve briefing](Enduring-Resolve-Campaign-Briefing#the-carriers-war)** for the
shipped example. *(Engine-verified; awaiting its first flown campaign — checklist P2.)*

## DEAD reachability gate

The planner no longer sends strikers through a SAM belt it only *intends* to clear. When a
strike is shielded behind a radar SAM, the planner schedules a DEAD against that SAM — but it
only treats the SAM as removed (and releases the dependent strike) if the DEAD's **actual
routed flight plan** can reach the site without crossing **another** live radar-SAM ring.

- If the DEAD can't range past the belt, the SAM stays modelled as alive, and the strike that
  depends on it stays **deferred until real battle-damage confirms the kill on a later turn** —
  rather than bombers being tasked into defences that are still up and then turned around by
  threat-reaction ROE without dropping anything.
- A close SAM whose DEAD route is clear is still cleared the same turn, so legitimate
  same-turn SEAD-escort-then-strike sequences are unaffected.

Practically: deep strikes wait for the belt to be genuinely peeled, layer by layer, instead of
flying optimistically into live rings.

## Mobile SAMs hidden from the MFD

Mobile short-range defences are kept **off player datalinks** so the SEAD/DEAD picture shows the
sites worth a deliberate package:

- SHORAD, AAA, and MANPAD units are hidden from the datalink — **including** short-range escorts
  generated *inside* an armour or missile-site group, which would otherwise leak onto the link.
- Standalone radar SAM sites (mobile MERAD/LORAD — SA-6/11, SA-2/3/5/10 and similar) **stay
  visible and targetable**, so you can still plan SEAD/DEAD against them.

When you frag suppression, you're aiming at the radar threats that warrant it, not chasing every
ZSU on the link. Pair this with the **Approximate target area** mode and DEAD/SEAD flights get a
single fuzzed target-area waypoint per mobile SAM rather than a precise steerpoint per
launcher — visual acquisition matters. See [Mission-planning](Mission-planning) for the SEAD/DEAD
task detail.

## Reactive, loitering SEAD

The fork's AI SEAD can **loiter near the target, react to emitters, and break off on a computed
timeline**, instead of making a single inflexible pass and leaving. Combined with reactive radar
shutdown from the IADS engine (below), this means SEAD is best planned as genuine *suppression*
that holds the radar down while DEAD closes the kill — not as a reliable emitter-killer on its
own.

## Auto-planner unpredictability (doctrine knob)

A campaign reads as "scripted" when the enemy hits the same targets in the same order every
turn. An opt-in, per-side doctrine knob varies which **opportunistic** offensive targets the
enemy services first:

- `ownfor_planner_unpredictability` and `opfor_planner_unpredictability` (0–100, **default 0**).
  At 0 the planner is exactly the deterministic strict-priority planner; as the value rises,
  lower-priority opportunistic targets become progressively more likely to be picked first,
  while the top target stays the most likely pick.
- It applies **only** to opportunistic offensive tasking (strike, anti-ship, OCA, BAI, and the
  non-threatening DEAD tiers). **Reactive threat response stays strictly deterministic** — BARCAP
  scheduling, escort sizing, the QRA dispatcher, and SAMs actually threatening a planned target
  are never randomised. Variety never delays a real defensive reaction.

Raise the opfor value if red's offensive target choice feels too repetitive; its air defences
stay just as sharp.

## IADS engine

The runtime integrated air-defence system is what makes enemy SAMs network, hand off tracks, and
shut their radars down reactively — and it's why a HARM is less likely to score an emitter kill
than against a dumb SAM, and why DEAD's bomb/ATGM kill is often the only reliable way to remove a
networked site.

**MANTIS is the IADS engine for every campaign** — it is the sole engine (Skynet was removed), and
older saves migrate to it automatically. The engine and the advanced comms/power/command-center
degradation graph have their own page:

> **→ [IADS Engine: MANTIS](IADS-Engine-MANTIS)** for what the engine does, advanced IADS, and
> the Skynet removal.

## See also

- [Mission-planning](Mission-planning) — packages, TOT timing, and the full per-task detail
  (SEAD/DEAD decision guide, BARCAP, escorts).
- [Air-Wing-Configuration](Air-Wing-Configuration) — squadron setup and the QRA reserve.
- [IADS Engine: MANTIS](IADS-Engine-MANTIS) — the runtime engine behind enemy air defenses.
- [Electronic Warfare and ISR](Electronic-Warfare-and-ISR) — the C-130J jammer/ELINT platform.
- [Fog-of-War-and-Reconnaissance](Fog-of-War-and-Reconnaissance) — recon fog and the overview
  reveal toggle that shows true threat rings.
- [Getting-Started](Getting-Started) — first-campaign walkthrough.
