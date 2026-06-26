# 414Ret for Retribution Veterans

You've flown stock DCS Retribution. This is what's different in the 414th's build —
nothing here changes the core loop you already know (frag → fly → debrief → advance),
it just fixes the parts that always felt off and adds the missions that were missing.

Everything below is on top of upstream; we still pull upstream fixes, so you lose nothing.

---

## The fixes you'll notice on turn one

| You're used to (stock) | In 414Ret |
|---|---|
| Red AWACS/tankers wandering far off-axis, sometimes near the front | Support orbits **anchor on the FLOT** and hold at a sane depth behind it |
| One BARCAP box per sector, predictable | **Overlapping, jittered BARCAP waves**, threat-weighted, with a forward CAP line |
| CAS packages spawning with no TARCAP; forward DEAD/BAI flying unescorted | Escort/TARCAP reach fixed — front-line packages get their **A2A + SEAD escort** |
| QRA ramp-scrambling (and occasionally clawing off the runway) | **Distributed alert interceptors** with a base-defense posture — they screen their field instead of charging the FLOT |
| Mobile SHORAD/AAA/MANPADs showing up on the datalink/MFD | Mobile SAMs **hidden from the datalink**; standalone MERAD/LORAD stay visible for SEAD |
| Red hitting the same targets every turn | Optional **auto-planner unpredictability** — red's opportunistic targets shuffle, threat response stays deterministic |
| Kneeboard package/airfield lists running off the page | **Pagination** — long lists spill onto continuation pages instead of clipping |
| A surviving jet logged as lost when you despawn/jump seat | Player-despawn **loss accounting fixed** — real shootdowns and ejections still count |
| Deep strikes sent through a SAM belt on an optimistic "it'll be clear" | **DEAD reachability gate** — the deep strike waits until the belt is actually down |

---

## The big additions

**A living front line (TIC).** The FLOT is no longer two static walls of armor. Ground
units hold formation and fight scripted, maneuvering firefights with per-stance behavior,
so flying CAS over the front finally looks and feels alive — and your strafing passes are
the real source of attrition.

**Recon fog + TARPS BDA.** Enemy sites show as targets you can plan against, but their
*composition, damage state, and threat rings stay hidden* until you scout, strike, or kill
a unit there. Fly the F-14 on a TARPS pass and your film feeds **confirmed BDA** back into
the campaign. The AI planner always uses ground truth, so auto-planning is unaffected —
the fog is yours alone. A one-click overview toggle lifts it when you want the full map.

**SCAR — a moving-target hunt.** A player-flown Strike Coordination & Reconnaissance task:
a high-value target crawls toward safety hidden among decoy and clutter convoys, and you
have to *pick it out* and prosecute it before it escapes — with a mis-ID budget penalty if
you hit the wrong convoy. (Optional commander-capture + SOF/CSAR loop on top.)

**C-130J electronic warfare / ISR.** A player-flyable EC-130H/RC-130H — area/spot jamming,
missile spoofing, ELINT/SIGINT, passive detection. A whole mission role stock doesn't have.

**Approximate target locations.** Optionally offset player steerpoints and hide exact
coords so you have to *visually acquire* the target instead of flying to a perfect mark.

---

## And a campaign builder

Stock gives you a fixed list of campaigns. 414Ret adds a **blank-canvas maker**: start
from an empty map, left-click airfields to paint ownership (blue / red / neutral),
finalize, and the front is derived from where you meet. Then drop SAMs, armor, and ships
straight onto the map with a **right-click**, with terrain and range checks (and a free-
placement cheat if you want it). Build the fight you want instead of picking from a menu.

---

## How to try it

It's the same Retribution workflow you already know — just our build. Grab the current
release and your existing instincts carry straight over; the differences above are what
you'll feel in the first campaign.

- Full feature internals: [`docs/dev/414th-features.md`](dev/414th-features.md)
- What's headed back upstream (most of it): [`docs/dev/414th-community-contribution-roadmap.md`](dev/414th-community-contribution-roadmap.md)

*414Ret is maintained by the 414th Joint Fighter Group, built on the open-source
[DCS Retribution](https://github.com/dcs-retribution/dcs-retribution) project.*
