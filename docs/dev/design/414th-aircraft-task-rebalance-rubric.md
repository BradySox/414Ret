# 414th aircraft task-priority rebalance rubric

Status: **DRAFT for review** (2026-06-15). Nothing is applied to the YAMLs until this
rubric is signed off.

## Why this exists

Each `resources/units/aircraft/*.yaml` has a `tasks:` block mapping a `FlightType` to an
integer weight. The auto-planner uses those weights to pick which airframe fills a given
role. The 256-file set grew organically and the weights, while broadly sensible, were never
derived from a single stated rule — so "rebalancing" them by hand-poking numbers is
unverifiable and tends to regress earlier deliberate tuning (e.g. Tu-22M3 `Anti-ship` 815,
CH_JAS39C `DEAD` 790, M-2000C A2A 460).

This rubric replaces ad-hoc numbers with a **two-axis model** so every weight is traceable:

```
weight(task) = round(tier_base × archetype_shape[task])
```

- **Archetype** sets the *shape* — which tasks an airframe is good at, relative to each
  other (a 0.0–1.0 multiplier per task).
- **Tier** sets the *magnitude* — how good the airframe is overall (its generation /
  capability), as a single base value.

So an F-22 (air-superiority × gen5) sits above an F-5E (air-superiority × gen3) with the
*same* task shape but a higher base.

## Scope / what is NOT touched

- **Combat tasks only** are rebalanced: `BARCAP, TARCAP, Fighter sweep, Escort,
  OCA/Aircraft, OCA/Runway, CAS, BAI, Strike, Anti-ship, Armed Recon, DEAD, SEAD,
  SEAD Escort, SEAD Sweep`.
- **Support / capability-gated tasks are preserved verbatim**: `Refueling, AEW&C, Recovery,
  Transport, Air Assault, TARPS, Jamming`. These are presence-gated by airframe capability,
  not preference-balanced, and several are 414th feature wiring (TARPS, Jamming).
- **Pure-support airframes** (tankers, AWACS, transports, utility helos) have no combat
  tasks and are left entirely untouched.
- **Novelty airframes** (Star Wars `*WING`, `TIE*`, `naboo_*`) are left as-is — not real,
  not worth a rule.
- Deliberate one-off overrides (see *Overrides* below) win over the formula.

## Tiers (base value)

| tier          | base | examples |
|---------------|------|----------|
| `gen5`        | 800  | F-22, F-35 (A/B/C), Su-57, B-2, B-21 |
| `gen45`       | 750  | F-15E/ESE, F-16I, F/A-18E/F, Su-30/34/35 family, JF-17, Rafale |
| `gen4`        | 670  | F-15C/D, F-16A/C, Su-27, J-11, MiG-29 family, F-14, M-2000, Gripen |
| `gen35`       | 560  | MiG-23, MiG-25, Mirage F1, Su-17, Mirage 2000-5(early), Su_15 |
| `gen3`        | 460  | F-4, MiG-21, Mirage III, F-5, A-7, A-4, Su-25-era attack |
| `gen2`        | 360  | F-100/104/105, MiG-19, early century series |
| `gen1`        | 300  | F-86, MiG-15, F-84 |
| `prop_attack` | 220  | A-1 Skyraider, OV-10, Il-2-likes |
| `prop_late`   | 230  | P-51, Spitfire LF, FW-190D, Bf-109K |
| `prop_early`  | 180  | I-16, FW-190A, P-47 early |
| `drone`       | 15   | MQ-9, Predator, WingLoong |

Tiers are coarse on purpose. Small intra-tier nudges (±10) are allowed as overrides to keep
known good orderings (e.g. A-10C above A-10A).

## Archetype shapes (per-task multiplier)

Only non-zero entries listed; everything else is 0 (task omitted from the YAML).

| archetype        | the airframe's job | key shape |
|------------------|--------------------|-----------|
| `air_superiority`| pure fighter | BARCAP 1.00, TARCAP 0.97, Fighter sweep 0.95, Escort 0.85, OCA/Aircraft 0.80 |
| `interceptor`    | fast climb, BVR point defense | BARCAP 1.00, TARCAP 0.92, Fighter sweep 0.85, Escort 0.62, OCA/Aircraft 0.55 |
| `multirole`      | swing fighter | OCA/Aircraft 1.00, CAS 0.95, BAI 0.95, Strike 0.86, OCA/Runway 0.82, BARCAP 0.78, TARCAP 0.76, Fighter sweep 0.74, Escort 0.73, DEAD 0.64, SEAD 0.64, SEAD Escort 0.64 |
| `strike_attack`  | A2G jet, weak A2A | CAS 1.00, BAI 1.00, OCA/Aircraft 0.88, Strike 0.80, OCA/Runway 0.75, Anti-ship 0.40 |
| `cas_specialist` | dedicated CAS | CAS 1.00, BAI 1.00, OCA/Aircraft 0.86, Armed Recon 0.55 |
| `sead_specialist`| Wild Weasel / ECR | SEAD 1.00, DEAD 0.95, SEAD Escort 0.92, SEAD Sweep 0.92, OCA/Aircraft 0.60, Strike 0.58 |
| `bomber`         | heavy strike | Strike 1.00, OCA/Runway 0.95, Anti-ship 0.72, BAI 0.66 |
| `maritime`       | ASuW patrol | Anti-ship 1.00 |
| `recon`          | armed recon | Armed Recon 1.00 |
| `attack_helo`    | rotary CAS | CAS 1.00, BAI 1.00, OCA/Aircraft 0.85 |
| `scout_helo`     | light/armed scout | OCA/Aircraft 0.62, CAS 0.62, BAI 0.62 |

## Overrides (formula loses to these)

Deliberate, in-game-validated tuning that the formula must not stomp. Recorded explicitly so
they survive future re-runs:

- `Tu-22M3` — `Anti-ship: 815` (already landed).
- `M-2000C` — A2A band already landed at 460-class intent; keep current.
- `CH_JAS39C` — `DEAD: 790` (SEAD-leaning Gripen, deliberate).
- Intra-family ordering bumps (A-10A < A-10C < A-10C_2, Ka-50 < Ka-50_3, etc.): allow ±10.

## Application & verification

The deterministic script `tools/rebalance_aircraft_tasks.py` implements this rubric:

1. Builds the exclusion set from `game/factions/faction.py` `remove_aircraft(...)` calls
   plus mod-pack name prefixes (`VSN_`, `vwv_`, `CH_`, `naboo`, `TIE`, `*WING`, ...), so
   **discarded-mod airframes do not factor into the balance**. Pure-support and
   novelty airframes are skipped too.
2. For each remaining candidate it derives `base` = its current top combat weight, looks up
   its archetype, and corrects present tasks toward `base * shape[task]` under the direction
   policy (see below). It **surgically replaces only the changed value lines** in the YAML
   (preserving line endings / trailing-newline) so the diff is minimal.
3. Dry-run is the default; `--write` applies. Verified with `pytest tests -q` (faction /
   campaign / unit data-load tests) and a per-file diff spot-check.

## Direction policy (chosen 2026-06-15: "outliers only")

The existing weights encode deliberate per-airframe role *emphasis* that a formula cannot
distinguish from error (e.g. Su-34 `SEAD: 30`, F-15E A2A `470` are intentional
de-prioritizations, not mistakes). A naive full-shape pass wrongly inflates these into
primary roles. So the applied pass is conservative and **intent-preserving**:

- **Roles are never added or removed** — only weights that already exist are touched.
- **Downward** corrections always apply (rein in over-high secondary roles).
- **Upward** corrections apply only when the weight is already `>= 0.85 * base` (a true
  magnitude fix), never to promote a deliberately low secondary into a primary.

## What landed (2026-06-15)

Conservative outliers pass: **20 files, 31 task changes** — over-high secondary A2A on
Flankers/Mirages and over-high Escort on pure fighters/interceptors tightened to band;
bombers' BAI/Anti-ship reined in below their Strike primary. No mods, support, novelty, or
deliberate suppressions touched. **Full "tighten everywhere" remains deferred** pending
in-game scramble/CAP validation — re-run with relaxed guards only after that.
