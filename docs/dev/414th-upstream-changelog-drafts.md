# Upstream changelog entries — drafts for the open carve PRs

**Working handoff file — delete once applied.** Produced by the 2026-07-20 standards
audit (the upstream dev-process adoption): upstream's Developer's Guide + PR template ask
that features and bug fixes carry a `changelog.md` note in the upcoming-release section,
and the open carves were cut before that standard was adopted as ours. DM call
2026-07-20: **draft them all** and apply from the dev machine (the carve branches live on
`bradyccox/dcs-retribution`, outside the authoring session's GitHub scope).

## How to apply (per PR, in the `..\retribution-pr` clone)

1. `git checkout <the PR's head branch>` (branch name is on the PR page; #881's is
   `vwv-3-2-0-support`).
2. **Verify the branch doesn't already carry an entry**:
   `git diff $(git merge-base upstream/dev HEAD)..HEAD -- changelog.md` — empty output
   means no entry yet. (#872 is expected to already have one — its dev rebase hit a
   changelog conflict.)
3. Add the entry to `changelog.md` under the **top in-development version heading**, in
   the subsection labeled below (`## Features/Improvements` or `## Fixes`; create the
   subsection if that version block lacks it). Match the neighboring entries' style for
   whether a trailing PR number is used — keep or drop the `(#NNN)` accordingly.
4. Commit additively (`changelog: <short description>`) and push. **No force-push** —
   review-safe additive commits only, #828 especially (it is in active re-review).

Two caveats from the audit session: the upstream diffs could not be read from there (the
session's GitHub scope), so step 2 is mandatory per PR; and the four pre-wave drafts
(#788/#792/#794/#806) plus #892 are written from ledger summaries — **sanity-check their
wording against the actual diff before pasting**.

**Deliberately no draft for #882** (headless Lua test harness): dev-only infrastructure
with no user-observable behavior — exempt under upstream's own changelog rule.

---

## Fixes

**#788 — inflight final-waypoint crash** *(verify wording vs diff)*
```
* **[Engine]** Fixed a crash (IndexError) when an aircraft spawned in flight ran off the end of its flight plan mid-mission. (#788)
```

**#873 — culled scenery-objective kill tracking**
```
* **[Mission Generation]** Scenery strike objectives no longer lose their kill tracking when their region is performance-culled — destroying them counts either way. (#873)
```

**#889 — F-14A-135-GR Early payload unitType**
```
* **[Data]** The F-14A-135-GR Early's payload file declared the wrong unitType, so the Early Tomcat flew every tasking unarmed; its loadouts now resolve (with a guard test pinning the payload to the airframe). (#889)
```

**#890 — empty squadron `aircraft:` key**
```
* **[Engine]** A campaign squadron entry with an empty `aircraft:` key no longer crashes New Game generation — it is treated as an empty list. (#890)
```

**#891 — blue-block campaign markers**
```
* **[Campaign]** Campaign `.miz` markers authored under the blue country block (ships, SAM/EWR sites, missile and coastal sites) were silently dropped by the loader — they now load and bind to the nearest blue control point, bounded so a marker far from any blue base still binds by plain proximity. 465 authored markers across 9 shipped campaigns were affected, most of them the Normandy campaigns' blue defenses. Economy objects keep their original binding. (#891)
```

## Features/Improvements

**#792 — wind override UI** *(verify wording vs diff)*
```
* **[UI]** The weather dialog can override the generated wind — set direction and speed yourself instead of taking the roll. (#792)
```

**#794 — hide mobile SAM in combined groups**
```
* **[Mission Generation]** Short-range air defenses (SHORAD/AAA/MANPADS) embedded inside armor and missile-site groups are now hidden from the MFD/datalink like standalone short-range systems already were; standalone medium/long-range SAM radars stay visible for SEAD targeting. (#794)
```

**#806 — configurable cruise/patrol altitude** *(verify wording vs diff)*
```
* **[Options]** Default cruise and patrol altitudes are configurable instead of hardcoded. (#806)
```

**#828 — recon fog of war**
```
* **[Campaign]** Recon fog of war: the enemy ground picture is earned, not given. Without fresh reconnaissance the map shows a site's last-known state — unconfirmed kills still render alive (battle-damage lag) and unscouted sites hide their composition; recon flights confirm BDA and reveal what's really there. AI planning always uses ground truth, so only the human's picture is fogged. (#828)
```

**#872 — ship-launched cruise missile strikes** *(expected already present — apply only if step 2 shows none)*
```
* **[Mission Generation]** Warships fire real cruise missile raids: put an F10 map marker on a shore target and call for fire from the nearest capable ship (marker text like `6` sets the salvo size), or enable auto raids for one planned salvo per side per turn. The missiles are real weapons from real, sinkable ships — kills count at debrief, defenses can intercept, and every hull carries a finite campaign magazine with no rearm. (#872)
```

**#874 — curated carrier comms**
```
* **[Mission Generation]** Carrier comms are curated instead of randomly allocated: TACAN follows the hull number with the boat's real ident (CVN-71 → 71X `TRO`), ICLS is hull-keyed, Link 4 sits in the real 336 MHz ACLS band, ATC stays stable across turns, and the flagship is named for its hull — so the DCS "CV Operations Data" kneeboard page reads like a proper Mother card. Values persist to the save, and a map-owned TACAN channel degrades to the nearest free neighbor. (#874)
```

**#880 — Splash Damage defaults**
```
* **[Plugins]** Splash Damage: the percent options now actually behave as percents (the rocket "(%)" spinner applied its raw value ×130, and overall scaling was divided by 100 twice in the bomblet path), test/debug mode no longer ships enabled, and the defaults are replaced with field-tuned values so big iron stops damaging buildings a mile away. The plugin remains off by default. (#880)
```

**#881 — Vietnam War Vessels v3.2.0**
```
* **[Modding]** Vietnam War Vessels support updated to v3.2.0: adds the sampans and Junk civilian craft plus five previously unregistered hulls (Radford, Epperson, Everett F. Larson, Solon Turman, USNS Card), with mod filtering for all of them and the version labels brought current. (#881)
```

**#883 — MIST replaced by a tested shim**
```
* **[Plugins]** MIST is retired in favor of a small, tested compatibility shim implementing the symbols the bundled scripts actually call; `mist_4_5_126.lua` is no longer shipped or loaded. Third-party plugin scripts calling MIST symbols outside the shim's set must bundle those functions themselves. The shim's unit database refreshes on spawn events instead of a whole-mission poll. (#883)
```

**#884 — fixed-wing air assault by paradrop**
```
* **[Flight Planner]** Fixed-wing troop transports fly Air Assault by paradrop. The airborne "Unload / Extract Troops" menu drops the stick (players below 3,000 ft AGL); AI transports run in at 1,000 ft and release over the objective automatically, and dropped troops use the normal CTLD bookkeeping so captures and losses count. The C-130J-30 gains the Air Assault task, letting the planner use it where helicopters lack the reach. (#884)
```

**#885 — custom victory conditions**
```
* **[Campaign]** Custom victory conditions: a campaign can author its own win/lose conditions (capture or hold named bases, destroy named targets or whole target classes, force-strength and territory thresholds, air denial, minimum-turn guards), and two generic opt-in settings (domination / attrition victory) work on any campaign. Alternate endings add to the stock territory victory — they never replace it. (#885)
```

**#886 — CurrentHill Iran Military Assets pack**
```
* **[Modding]** Added support for the CurrentHill Iran Military Assets pack: the Shahed-136 launcher, two IRGCN fast-attack craft, and a new `[CH] Iran 2020` faction, behind a New Game mods checkbox. (#886)
```

**#887 — Sborka "Dog Ear" SHORAD acquisition radar**
```
* **[Units/Factions]** Soviet-doctrine SHORAD groups field their Sborka "Dog Ear" acquisition radar (a vanilla DCS unit) when the site's layout has a search-radar slot free — era-gated and excluded from SAM sites, so period groups get their real acquisition picture with no mod required. (#887)
```

**#892 — SAM site layout variety + EWR pool** *(refresh of #791 — verify wording vs diff)*
```
* **[Mission Generation]** More variety in generated air defenses: additional SAM site layout variants and a wider era-appropriate EWR radar pool, so generated sites stop repeating one template. (#892)
```

**#893 — SAM guidance-radar redundancy**
```
* **[Mission Generation]** SAM sites field two engagement radars (the shared site templates gain a second, dispersed radar position), so a single anti-radiation missile no longer functionally kills the whole site. Buy-menu counts and site prices follow. A deliberate survivability/balance call — rationale and trade-offs in the PR body. (#893)
```
