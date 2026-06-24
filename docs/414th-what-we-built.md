# 414Ret — What the 414th Built on Top of DCS Retribution

*A short tour of the work behind the squadron's fork of [DCS Retribution](https://github.com/dcs-retribution/dcs-retribution).*

DCS Retribution is the open-source dynamic-campaign generator we fly. **414Ret** is the
414th Joint Fighter Group's fork of it — the same proven campaign engine, with a thick
layer of squadron-built features bolted on top: smarter air defense, a living frontline,
photo-recon, electronic warfare, a moving-target hunt, a from-scratch campaign builder,
and a lot of quality-of-life polish. This page is the short version of *how much* went
into that.

---

## By the numbers

| | |
|---|---|
| **20** | major features added on top of upstream |
| **6** | custom in-mission plugin systems (~**11,400 lines** of Lua mission scripting) |
| **260+** | squadron commits, with **100,000+ lines** added (new code, mission scripting, vendored frameworks, campaign data) |
| **100+** | automated tests (21 dedicated to our own features) |
| **4** | continuous-integration gates every change must pass (formatting, type-checking, tests, Lua syntax) |
| **~6,000** | lines of engineering & design documentation |
| **2** | custom campaigns + **1** custom faction |

*Built in a focused development push from June 2026, on top of — not instead of — the
upstream engine, so we still inherit every upstream fix.*

---

## What we added (in plain terms)

**Smarter air war.** The enemy now defends like it means it: quick-reaction interceptors
that scramble to protect their bases, overlapping CAP waves that actually screen the
front, AWACS and tankers that hold sensible orbits instead of wandering into the fight,
and an auto-planner that stops hitting the same targets every turn. Strike packages get
the escorts and TARCAP they should.

**A living battlefield.** The front line isn't two static walls of armor anymore —
**TIC (Troops In Contact)** drives scripted firefights with real maneuver, so the FLOT
looks alive from the air, tracers and all. Mobile SAMs hide from the datalink the way
they should, and target locations can be made deliberately approximate so you have to
*find* the enemy, not just fly to a waypoint.

**Recon and intel that matter.** Fly the F-14 on a **TARPS** photo pass and what you
photograph feeds real battle-damage assessment back into the campaign. Enemy sites stay
*fogged* — you see a threat exists but not exactly what's there — until you scout or
strike it, so recon sorties are worth flying. A one-click "reveal" toggle lets you lift
the fog when you want the full picture.

**New ways to fly.** A player-flown **C-130J** electronic-warfare / ISR platform
(jamming, ELINT, SIGINT). **SCAR** — Strike Coordination and Reconnaissance — a
moving-target hunt where you pick the real high-value target out of decoys, with an
optional commander-capture and special-forces recovery loop on top. Players-only ATC
tower comms at every airbase.

**Build your own war.** A **blank-canvas campaign maker**: start from an empty map, paint
which airfields are yours, and drop SAMs, armor, and ships straight onto the map with a
right-click. Native DCS data-cartridge export pre-loads your jet's situational-awareness
page. Plus a unified, dark-themed map-layers panel to keep all of it readable.

*(Full per-feature engineering detail lives in [`docs/dev/414th-features.md`](dev/414th-features.md).)*

---

## Built to a real standard

This isn't a pile of hacks. Every change runs a four-gate CI pipeline — code formatting,
type-checking, the full test suite, and a Lua syntax gate — before it can ship, and a
rolling build is published automatically so the squadron always flies current `main`.
Features that CI can't exercise (anything that only shows its true colors in a live DCS
mission) go through a written **in-game pass checklist** with a pass/fail criterion for
each one, flown and signed off before it's called done.

---

## Good enough to give back

The clearest measure of the work's quality: **most of it isn't actually
414th-specific.** We recently went feature-by-feature and found that the large majority
are *generic capabilities* the whole Retribution community would benefit from — only a
thin layer (our campaigns, our faction, our ballistics tuning, our doctrine settings) is
truly squadron-only. We've already started contributing fixes back upstream, and have a
[roadmap](dev/414th-community-contribution-roadmap.md) for handing the rest back.

In other words: we didn't just build a lot — we built a lot that's good enough that the
project we forked from would want it too.

---

*414Ret is maintained by the 414th Joint Fighter Group. Source:
<https://github.com/bradyccox/414Ret>. Built on the open-source
[DCS Retribution](https://github.com/dcs-retribution/dcs-retribution) project.*
