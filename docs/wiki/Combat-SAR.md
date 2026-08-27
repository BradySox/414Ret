# Combat SAR

Combat SAR (combat search and rescue) makes a downed pilot worth flying for. In stock
Retribution an ejection is a flat loss: the airframe is gone and the aviator is written off.
With CSAR on, an ejection puts a survivor on the ground with a homing beacon, and a helicopter
can go and get them. Deliver them to a friendly field and the campaign **spares that aviator**:
you still lose the jet, but the experienced pilot goes into recovery and returns to the squadron.

It is a normal, standing task. `FlightType.CSAR` is player-selectable, and the auto-planner
frags rescues on its own — you do not have to build the package by hand.

> **Implementation note.** Since 2026-08-07 the fork runs **upstream
> [dcs-retribution#929](https://github.com/dcs-retribution/dcs-retribution/pull/929)**, driven by
> MOOSE `Ops.CSAR` (the `opscsar` plugin). It replaced the fork's own combat-SAR entirely. The
> old King + Jolly Green + Sandy package, the enemy snatch party, the POW hold clock and the
> `auto_combat_sar` setting are **gone**.

---

## The rescue flight

The pickup is flown by a **helicopter**. There is no escort element built into the task, and a
fixed-wing aircraft cannot make the pickup: the rescue lands at an unprepared site, and the DCS
AI `Land` task is helicopter-only.

Eligible airframes: **CH-47D**, **CH-47Fbl1**, **CH-53E**, **Mi-8MT**, **SH-60B**, **UH-1H**,
**UH-60A**, **UH-60L**.

By default the auto-planner sends a **pair**. Turn on `csar_single_flight` to send one.

### The King

The **C-130J-30** flies CSAR as the on-scene commander. It holds a racetrack near the survivor —
15 nm off on the side away from the nearest threat, and outside any SAM ring the survivor is
sitting in — and never picks anyone up.

Add it by hand: right-click the survivor, add the rescue helicopter, then add a second flight
with the C-130J-30 on the CSAR task. The auto-planner will not frag one, because an AI King
would orbit a survivor it can never collect.

---

## How a rescue works, step by step

1. A pilot goes down in the operating area. Real in-mission ejections always produce a survivor;
   losses where DCS reported no ejection (AI kills, simulated turns) roll against
   `csar_ejection_chance` (**40%**).
2. **Distance to the nearest base decides whether it is a mission at all.** Inside
   `csar_control_point_radius` (**15 nm**) there is no rescue flight: on friendly ground the
   pilot walks back and goes into recovery, on enemy ground they are captured. Only pilots
   outside every control point's radius become downed pilots on the map.
3. The survivor lights an **ADF beacon on a pinned 260 kHz**, the same channel for every
   survivor in the mission, printed on the rescue crew's kneeboard. Tune it before you start and
   home the needle straight in. (MOOSE randomises the channel per survivor out of the box, which
   cannot be briefed — the kneeboard is rendered before the mission runs. The fork pins one.)
4. The helicopter flies to the survivor and either **lands** and boards them, or **holds a low
   hover** and hoists them, depending on `csar_hover_extraction`.
5. Deliver them to any friendly airfield or FARP. The pilot goes into recovery —
   `csar_player_recovery_turns` (**1**) for a human, `csar_ai_recovery_turns` (**2**) for an AI —
   and then returns to the squadron.

**You have to actually bring them home.** A rescue helicopter shot down with survivors aboard
never reaches the delivery, so nobody is credited.

## The clock

A survivor does not wait forever. Left un-rescued they go **missing in action**:

| Where they came down | Turns they last |
|---|---|
| Friendly rear territory | `csar_survival_turns` — **3** |
| Hostile ground or near the front | `csar_survival_turns_hostile` — **2** |

## Prisoners

A pilot captured inside an enemy control point's radius is **held, not killed**. `Pilot.held_at`
persists which control point holds them, and **retaking that base releases them** into recovery.
There is no raid mission against the holding field — win the field back with the ground war.

## Several survivors, one lift

Survivors within `csar_cluster_radius` (**1000 m**) of each other come out on **one flight**
instead of one flight each: they walk to the same landing zone, or are hoisted on the same hover.
This only affects the auto-planner — a package you build by hand still targets one pilot. Set it
to 0 to plan a separate flight for every pilot.

The cluster is rebuilt at runtime rather than trusted from the plan, so a survivor already killed
or already collected is not credited twice.

---

## Settings reference

| Setting | Default | Effect |
|---|---|---|
| `csar_enabled` / `csar_enabled_red` | ON / ON | CSAR for the blue and red coalitions. Unlike the old fork feature, **red gets rescues too** |
| `csar_ejection_chance` | 40% | Survival chance for losses where DCS reported no ejection |
| `csar_control_point_radius` | 15 nm | Inside this, no rescue flight: friendly = walks back, enemy = captured. 0 always requires a rescue |
| `csar_cluster_radius` | 1000 m | Survivors this close come out on one lift. 0 = one flight each |
| `csar_survival_turns` | 3 | Turns a survivor lasts in friendly rear territory |
| `csar_survival_turns_hostile` | 2 | Turns a survivor lasts in hostile territory or near the front |
| `csar_ai_recovery_turns` | 2 | Turns a rescued AI pilot is unavailable |
| `csar_player_recovery_turns` | 1 | Turns a rescued human pilot is unavailable |
| `max_csar_flights` | 2 | Rescue packages the auto-planner commits to per side, per turn |
| `csar_single_flight` | OFF | Plan one helicopter instead of a pair |
| `csar_start_type` | Warm | Start type for rescue flights, overriding the AI/player defaults |
| `csar_hover_extraction` | ON | AI recovery: hover-and-hoist. Off = land and the pilot walks aboard |
| `csar_rescue_ai_pilots` | ON | Register AI ejections as survivors, not only player-flown ones |
| `csar_player_hover_height` | 20 m | How low a **player** hovers to winch a survivor up |
| `csar_player_hover_distance` | 10 m | How close to the survivor that hover has to be |

## Tips

- **Dial 260 kHz before you start.** It is on the kneeboard and it is the same for every
  survivor in the mission. The needle is the whole navigation solution.
- **Bring cover.** The rescue task plans no escort of its own. If the survivor is down inside
  threat rings, frag the escort yourself.
- **Any friendly airfield or FARP scores the save.** You do not need a dedicated field.
- **Raising `csar_player_hover_height`** raises the briefed hover with it, up to a point — the
  briefed figure is clamped to 80% of the setting so it stays inside MOOSE's winch ceiling.

## See also

- [Squadrons and Pilots](Squadrons-and-Pilots)
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
- [Mission planning](Mission-planning)
