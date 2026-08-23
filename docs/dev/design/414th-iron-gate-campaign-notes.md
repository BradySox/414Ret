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

## The two traps, both of which bit

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

---

## The laydown

| base | stands | used | squadrons |
|---|---|---|---|
| **Kutaisi** | 58 | 37 | A-10C Suite 7 12, UH-1H 6, OH-58D Kiowa 6, AH-64D 6, CH-47F 5, C-130J-30 2 |
| **Kobuleti** | 42 | 36 | F-15E 12, F-16CM 12, F-15C 12 |
| **Turkey** (off-map air spawn) | ∞ | 6 | KC-135 MPRS 2, KC-135 2, E-3A 2 |
| **Blue CV** | 90 | 66 | F-14B 24 (VMF-29), F/A-18C 24 (VFA-113), A-6E Tanker 4, E-2D 2, F-14B(U) 12 |
| Tbilisi-Lochini | 74 | 70 | MiG-29S 18, MiG-29A 18, Su-25 17, Su-24M 17 |
| Mozdok | 39 | 39 | 5 |
| Mineralnye Vody | 28 | 28 | 6, including red's only AWACS and tanker |
| Beslan | 15 | 15 | Su-27 5, MiG-29S 10 |
| Nalchik | 15 | 15 | 3, one each of MiG-31, MiG-29S, MiG-29A |
| Nigniy Pasanauri FOB | 4 rotary | 4 | Mi-24V 4 |
| Khashuri FOB | 4 rotary | 4 | Mi-24V 4 |

**Blue's land-based fighters total 36 aircraft**, three full squadrons on Kobuleti's 42 stands.
Batumi was the first choice and was dropped: ten stands is not a fighter base. Gudauta was the
other candidate at 31 stands, but it sits 160 NM from the fighting against Kobuleti's 132, and
102 NM from Kutaisi against 32.

**39 squadrons, 320 aircraft.** Squadrons of the same airframe at the same base are merged
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

## Deferred

- **No in-game pass yet.** Checklist **B96**. The parking numbers are arithmetic over pydcs
  stand data, which models DCS rather than being it.
- **The supply-route override moved here** from Northern Russia with `tests/theater/
  test_supply_route_drivability.py`. Plob's campaign keeps the original miz path, so its front
  line still sits on the Likhi ridge — a deliberate call, not an oversight.
- **Red's laydown is Plob's**, re-equipped and re-sized but not re-thought. Objectives, victory
  conditions and the IADS belt are all still his.
