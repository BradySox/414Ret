# Caucasus — Iron Gate

The 414th's fork of Plob's **Northern Russia**. June 2018, Russia 2020, blue flying from
Kutaisi and Kobuleti with its tankers and AWACS on an off-map air spawn.

**Plob's campaign still ships, unchanged.** `northern_russia.yaml` is byte-identical to its
pre-fork state — 1995-06-13 against Russia 1975, no `settings:`, no authored squadron sizes.
Anything we wanted lives here instead. `tests/fourteenth/test_iron_gate.py` asserts the two
stay apart, because the tempting mistake is to "fix" Northern Russia into agreement with this
file.

Owner: this note. CI lock: `tests/fourteenth/test_iron_gate.py`.

---

## Why it forked

Northern Russia is a good map layout with a 1995 date bolted to a modern premise: its own
description says Russia invaded Georgia through the eastern mountains, and it fought that out
against **Russia 1975**. Moving it to 2018 is not a bug fix — it is a different campaign — so
it became one.

What changed, and why each was forced rather than chosen:

| | |
|---|---|
| **2018-06-13, Russia 2020** | The premise needs a modern VKS. Russia 2020 is vanilla DCS, so red's SAM belt does not silently collapse for anyone without High Digit SAMs. |
| **17 red squadrons re-equipped** | MiG-21bis, MiG-23MLD, MiG-25PD and Su-17M4 are not a 2018 air force. Successors: MiG-29S, Su-27, MiG-31, Su-24M. **Not cosmetic** — see the assigner trap below. |
| **Every squadron sized** | The campaign asked for 324 red aircraft across 171 stands. See the parking section. |
| **Blue re-based** | Kutaisi held blue's entire land wing on 58 stands. Now Kutaisi is the A-10/helicopter field, the fast jets sit at Kobuleti, and the support spawns airborne. |
| **Blue re-equipped** | The shipped blue wing was a MiG-23MLD, a JF-17, a Mirage 2000C, an AJS-37, a Ka-50 and a pair of Hips and Hinds. It now flies the wing the squadron actually uses. |

---

## The three traps, all of which bit

### 1. A missing airframe does not fail — it substitutes, badly

`DefaultSquadronAssigner.find_squadron_for_task` returns the **first unclaimed compatible
squadron def in dictionary order, with no priority weighting**. A squadron whose airframe is
absent from the faction silently takes whatever comes up.

Russia 2020 has a **BARCAP-capable L-39ZA**. Swapping the faction without re-equipping the
squadrons would have left 15 of red's fighter squadrons able to come up as jet trainers.
Measured: under Russia 1975 all 27 red squadrons resolved to their authored airframe; the
faction swap alone dropped that to 10.

**So: never change a campaign's faction without checking every authored airframe still
resolves in the new one.**

### 2. Stands are nested, so a base's slot count is not the constraint

A stand that takes a Hind also takes a Huey, not the reverse. At Kutaisi only **13** of 58
stands take an Mi-8 or Mi-24, only **25** take any helicopter, and the 13 heavy stands sit
*inside* the 25. Batumi, tried first, had ten stands and **two** of them took a KC-135.

Sizing against a base's grand total therefore overfills the big stands **with no error
anywhere** — the yaml looks fine, the loader is happy, and DCS fails at spawn. It bit four
times during the build, each caught only by checking explicitly:

- 28 helicopters into Kutaisi's 25 helicopter-capable spots;
- Beslan asking a Flanker squadron and a Hind squadron of five each to share its **five**
  large stands;
- Tbilisi-Lochini holding **74 aircraft when its jets fit 70**;
- the Hercules, parked beside two 12-ship helicopter squadrons, pushing the 25-class to 26.

The rule to apply is **Hall's condition over the nested classes**: for every capacity `k`, the
aircraft needing a stand of that class or smaller must total ≤ `k`. `test_iron_gate.py`'s
`test_no_base_oversubscribes_a_stand_class` enforces it over every base.

**`total_aircraft_parking` on a FOB reports 0 for the fixed-wing pool.** A check that compares
against fixed-wing parking will call a FOB helicopter squadron oversubscribed when it is not;
the rotary pool is the one that applies.

### 3. A squadron that names its own airframe has no identity at all

A campaign entry's `aircraft:` list holds **squadron preset names**, not aircraft types. Put
the type there and it matches no preset, so the squadron flies with **no name, no nickname
and no livery** — and nothing warns. Two of Iron Gate's blue squadrons shipped that way:

| squadron | was | now |
|---|---|---|
| A-10C, Kobuleti | `A-10C Thunderbolt II (Suite 7)` — its own type | **81st FS "Termites"**, Spangdahlem |
| OH-58D, Kutaisi | `Taiwanese Army`, CJTF Blue, livery `TWN Army Fictional` | **1-17 Cavalry "Saber"**, livery `US 1-17 A 002` |

The Kiowa case is the nastier one, because it *looks* right — it names a real preset that
really exists. It was a Taiwanese unit with a fictional livery in a US-led coalition, and it
also carried `country: Combined Joint Task Forces Blue`, which costs the §23 US voiceovers and
pilot names every other squadron in the campaign gets.

`Bluefor Modern` is a CJTF faction, so `SquadronDefLoader` does **no country filtering** and
every preset in the repo is reachable. That is why the wrong nation resolved happily.

`test_every_blue_squadron_is_a_real_unit` locks it: no blue squadron may name its own type,
every name must exist as a preset, and that preset must fly that airframe. **The E-2D is the
one documented exception** — no Hawkeye preset exists anywhere in `resources/squadrons`, so
the carrier's Hawkeye has nothing to be named after.

---

## The laydown

| base | stands | used | squadrons |
|---|---|---|---|
| **Kutaisi** | 58 | 25 | UH-1H 6, OH-58D Kiowa 6, AH-64D 6, CH-47F 5, C-130J-30 2 |
| **Kobuleti** | 42 | 36 | F-15E 12, F-16CM 12, A-10C Suite 7 12 |
| **Batumi** | 10 | 10 | F-15C 10 |
| **Turkey** (off-map air spawn) | ∞ | 6 | KC-135 MPRS 2, KC-135 2, E-3A 2 |
| **Blue CV** | 90 | 66 | F-14B 24 (VMF-29), F/A-18C 24 (VFA-113), A-6E Tanker 4, E-2D 2, F-14B(U) 12 |
| Tbilisi-Lochini | 74 | 70 | MiG-29S 18, MiG-29A 18, Su-25 17, Su-24M 17 |
| Mozdok | 39 | 39 | 5 |
| Mineralnye Vody | 28 | 28 | 6, including red's only AWACS and tanker |
| Beslan | 15 | 15 | Su-27 5, MiG-29S 10 |
| Nalchik | 15 | 15 | 3, one each of MiG-31, MiG-29S, MiG-29A |
| Nigniy Pasanauri FOB | 4 rotary | 4 | Mi-24V 4 |
| Khashuri FOB | 4 rotary | 4 | Mi-24V 4 |

**Blue flies from three fields, and each is a different distance from the pass.** Measured to
the turn-1 front line: **Kutaisi 27 NM, Kobuleti 55 NM, Batumi 73 NM.**

| field | holds | why |
|---|---|---|
| Kutaisi | the rotary wing + the Hercules | closest to the front, and its 25 helicopter stands are exactly full |
| Kobuleti | the strike wing — F-15E, F-16CM, A-10C | 42 stands, the only field that fits three fixed-wing squadrons |
| Batumi | the F-15C, and only the F-15C | **ten stands, ten aircraft** — the squadron cannot be sized above 10 |

Batumi was dropped once and brought back (2026-08-23, DM call). Ten stands is not a base for
three squadrons, which is what the first attempt tried; it is a fine base for one. **Gudauta
stays out** — 31 stands, but it sits behind both and a tanker that never lands needs no ramp
at all.

**The Warthogs moved back to Kobuleti and it costs them about six minutes each way** (27 NM to
55 NM, ~5 to ~11 at 300 kt). Kutaisi keeps them within reach of nothing else it could hold:
the 25 helicopter-capable stands were already full, so vacating twelve *fixed-wing* stands
frees nothing for the rotary squadrons. **Kutaisi now runs 25 of 58** — 33 idle stands that
only another fixed-wing squadron could use.

**39 squadrons, 318 aircraft.** Squadrons of the same airframe at the same base are merged
rather than duplicated — two MiG-31 flights at Mineralnye Vody are one squadron of 8, not two
of 4. Where the pair had different primaries the second becomes a `secondary:`, so the merge
never costs a role: Mozdok's Su-24M is SEAD with Strike secondary, Tbilisi's Su-25 is BAI with
Strike. On the carrier the merge takes the **union** of both squadrons' task lists, because
VF-102 carried eleven secondaries against VMF-29's four and keeping only the first would have
quietly halved what the Tomcats could be tasked with.

### The off-map air spawn

Declared by a **blue F-15C plane group** in the miz (`MizCampaignLoader.OFF_MAP_UNIT_TYPE`);
the control point takes the group's name. Placed at `(-450000, 610000)`, south of Batumi and
off the airfield span, so it reads as Turkish airspace. `OffMapSpawn` reports 1000 parking,
accepts any airframe, and forces `StartType.IN_FLIGHT`. Thirteen shipped campaigns already use
the pattern.

Gudauta was tried as a third field first — it is one of only two south-west airfields besides
Kutaisi with enough large stands (10) — and dropped in favour of the spawn: a tanker that never
lands does not need a ramp.

### The LHA was dropped

The Tarawa carried an Apache squadron and a Chinook squadron and nothing else, so it came
out of the miz and they came ashore to Kutaisi. **It cost 20 aircraft** and there was no way
round that: Kutaisi has 58 stands but only **25** take a helicopter, and the Huey, Kiowa and
Hercules already filled them. Five rotary squadrons now share those 25 at 6/6/6/5, so the
Huey and Kiowa halved. Kobuleti was no help — its 26 helicopter stands are a subset of the
42 the fighters occupy 36 of.

The trade was made deliberately (DM call): a simpler laydown, at the price of blue's
rotary strength and of the only sea-based air assault the campaign had.

### Red's helicopters live at the FOBs

Neither Hind squadron is on an airfield. Both red FOBs had four helicopter pads and nothing on
them, and both sit closer to the fighting than the fields the squadrons came from:

| squadron | from | to | NM to the fighting |
|---|---|---|---|
| Mi-24V 4 | Beslan | **Nigniy Pasanauri FOB** | 19 → 59 |
| Mi-24V 4 | Tbilisi-Lochini | **Khashuri FOB** | 104 → 82 |

Beslan's move was forced: it has five large stands and the Flanker regiment wants them, so
the two were sharing at 3 and 2. Tbilisi's was free — better than free. A FOB holds four, so
the squadron drops from 10 to 4, but the ten stands it vacates go to Tbilisi's jets, which
were capped at 70 by their own stand class and sitting at 60. **Red ends up four aircraft
ahead**, and its attack helicopters are 22 NM further forward.

---

## First flown test, 2026-08-23 — it works, and the numbers lie to you

62 minutes of sim, 1,091 units, 238 aircraft. `Tacview-20260823-181233`; the game is on
turn 2 in `autosave.retribution`.

**The parking held.** No field exceeded its stands, every aircraft got a slot, the Turkey
spawn produced air-started tankers, both FOBs parked their Hind squadron on pads, and the
Hercules took one of Kutaisi's large stands. Checklist **B96** is verified.

### Two numbers that read as failures and are not

**"Red flew 5 sorties out of 159 aircraft."** Red's ATO was **8 flights**. The other ~150
aircraft are squadron inventory sitting on the ramp because `squadron_start_full` is on and
every base is filled to its stands — they were never tasked. Seven of the eight activated
inside the flown window and four flew.

**"`CRANE DEAD` never moved: track span 0.0 NM over 30–3750 s."** It activated at **3629 s**
into a mission that ended at **3750 s** — two minutes to start engines and taxi. The 30–3750 s
window is the sortie recorder watching the group object, not time airborne.

**An earlier reading of this same data concluded that ramps filled past ~73 % block AI taxi,
and that conclusion was wrong.** The apparent break between Kobuleti at 62 % and Beslan at
73 % was an artifact of which fields happened to hold the early-activating flights. Nothing
here says a full ramp is safe either — it says this test did not test it. If it is ever
suspected again, the discriminator is the activation time in the miz's `trigrules`, not the
track span.

### The long ATO is one setting, and it is measured

The first flight scheduled activations out to **13,517 s (3 h 45 m)** against a ~62 min
mission, so 8 of blue's 37 never fired. Chased to the end; **nothing to fix in the campaign
or the code.**

`barcap_rounds = ceil(mission_duration / (barcap_duration - overlap))`, and a **fleet control
point doubles it**. The doubling is only half a mechanism:
`max_carrier_simultaneous_barcaps` is what turns the extra rounds into *pairs on station
together* rather than more waves in sequence, and at **1** it never stacks —
`count >= max - 1` is `count >= 0`, true for the first package, so every wave advances the
handover instead of joining the current one.

Measured on `Maybe 414.retribution` (turn 1, 100-min mission, overlap 0, 19 blue packages),
re-planning blue at each value:

| `max_carrier_simultaneous_barcaps` | carrier BARCAPs | last TOT | packages past the mission |
|---|---|---|---|
| **1** (that save) | 4 singles at 4/64/124/184 min | 184 min | **3 of 19** |
| **2** (the default) | 4 in two pairs at 3/4/64/64 min | **95 min** | **0 of 19** |
| 3 | 3/3/4/64 min | 102 min | 1 of 19 |

At the default the whole ATO fits inside the mission and the last package is a DEAD, not a
BARCAP. **This one setting is the entire effect** — every non-carrier package finishes by
95 min at any value.

Overlap pushes the same way when it is non-zero: it does not add cover on top, it *shortens*
each wave's fresh coverage, so more waves get planned. The flown mission had it at 15 min,
which is why that ATO reached 225 min where this save's reaches 184. It is a multiplier on
the problem, not its cause.

So a carrier campaign wants `max_carrier_simultaneous_barcaps` at 2 or more. Iron Gate
preseeds neither setting and should not — they are doctrine, not campaign content.

Separately, `sortie_records` logged **183 flights when 30 aircraft moved**: parked inventory
recorded as sorties. That is §91's problem, not this campaign's — checklist B70.
---
## Deferred

- **No in-game pass yet.** Checklist **B96**. The parking numbers are arithmetic over pydcs
  stand data, which models DCS rather than being it.
- **The supply-route override moved here** from Northern Russia with `tests/theater/
  test_supply_route_drivability.py`. Plob's campaign keeps the original miz path, so its front
  line still sits on the Likhi ridge — a deliberate call, not an oversight.
- **Red's laydown is Plob's**, re-equipped and re-sized but not re-thought. Objectives, victory
  conditions and the IADS belt are all still his.
