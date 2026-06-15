"""Outliers-only aircraft task-priority rebalance (dry-run by default).

See docs/dev/design/414th-aircraft-task-rebalance-rubric.md.

Model: per-airframe base = its current top combat-task weight; target[task] =
round(base * archetype_shape[task]). Only weights that ALREADY EXIST are touched
(roles are never added or removed). Direction policy, to preserve deliberate
tuning:
  - Downward: always allowed when off by > THRESHOLD -- rein in over-high
    secondary roles.
  - Upward: only when the weight is already >= 0.85*base (a true magnitude fix);
    a deliberately low secondary (e.g. Su-34 SEAD=30, F-15E A2A=470) is never
    promoted into a primary role.
Support tasks, discarded-mod airframes, novelty airframes, and explicit
OVERRIDES are untouched.

Run:  python tools/rebalance_aircraft_tasks.py          # dry-run report
      python tools/rebalance_aircraft_tasks.py --write  # apply
"""

from __future__ import annotations

import glob
import os
import re
import sys

import yaml

THRESHOLD = 60

COMBAT = [
    "BARCAP",
    "TARCAP",
    "Fighter sweep",
    "Escort",
    "OCA/Aircraft",
    "OCA/Runway",
    "CAS",
    "BAI",
    "Strike",
    "Anti-ship",
    "Armed Recon",
    "DEAD",
    "SEAD",
    "SEAD Escort",
    "SEAD Sweep",
]

# Archetype shapes: per-task multiplier vs the airframe's own base (its current
# top combat weight). Only tasks already present on an airframe are adjusted.
SHAPES = {
    "air_superiority": {
        "BARCAP": 1.00,
        "TARCAP": 0.97,
        "Fighter sweep": 0.95,
        "Escort": 0.85,
        "OCA/Aircraft": 0.80,
    },
    "interceptor": {
        "BARCAP": 1.00,
        "TARCAP": 0.92,
        "Fighter sweep": 0.85,
        "Escort": 0.62,
        "OCA/Aircraft": 0.55,
    },
    "multirole": {
        "OCA/Aircraft": 1.00,
        "CAS": 0.95,
        "BAI": 0.95,
        "Strike": 0.86,
        "OCA/Runway": 0.82,
        "BARCAP": 0.78,
        "TARCAP": 0.76,
        "Fighter sweep": 0.74,
        "Escort": 0.73,
        "DEAD": 0.64,
        "SEAD": 0.64,
        "SEAD Escort": 0.64,
    },
    "strike_attack": {
        "CAS": 1.00,
        "BAI": 1.00,
        "OCA/Aircraft": 0.88,
        "Strike": 0.80,
        "OCA/Runway": 0.75,
        "Anti-ship": 0.40,
    },
    "cas_specialist": {
        "CAS": 1.00,
        "BAI": 1.00,
        "OCA/Aircraft": 0.86,
        "Armed Recon": 0.55,
    },
    "bomber": {"Strike": 1.00, "OCA/Runway": 0.95, "Anti-ship": 0.72, "BAI": 0.66},
    "maritime": {"Anti-ship": 1.00},
    "recon": {"Armed Recon": 1.00},
    "attack_helo": {"CAS": 1.00, "BAI": 1.00, "OCA/Aircraft": 0.85},
    "scout_helo": {"OCA/Aircraft": 1.00, "CAS": 1.00, "BAI": 1.00},
    "drone": {"OCA/Aircraft": 1.00, "CAS": 1.00, "BAI": 1.00},
}

# Explicit archetype per candidate airframe id (filename stem).
ARCHETYPE = {
    # air superiority / pure fighters
    "F-14A": "air_superiority",
    "F-15C": "air_superiority",
    "Su-27": "air_superiority",
    "J-11A": "air_superiority",
    "M-2000C": "air_superiority",
    "Mirage 2000-5": "air_superiority",
    "F-5E-3": "air_superiority",
    "F-5E-3_FC": "air_superiority",
    "F-86F Sabre": "air_superiority",
    "F-86F_FC": "air_superiority",
    "MiG-15bis": "air_superiority",
    "MiG-15bis_FC": "air_superiority",
    "MiG-19P": "air_superiority",
    "MiG-23MLD": "air_superiority",
    "Mirage-F1B": "air_superiority",
    "Mirage-F1BE": "air_superiority",
    "Mirage-F1C-200": "air_superiority",
    "Mirage-F1CE": "air_superiority",
    "Bf-109K-4": "air_superiority",
    "FW-190A8": "air_superiority",
    "FW-190D9": "air_superiority",
    "P-51D": "air_superiority",
    "P-51D-30-NA": "air_superiority",
    "SpitfireLFMkIX": "air_superiority",
    "SpitfireLFMkIXCW": "air_superiority",
    "I-16": "air_superiority",
    "F4U-1D": "air_superiority",
    # interceptors
    "MiG-25PD": "interceptor",
    "MiG-31": "interceptor",
    # multirole
    "F-16C_50": "multirole",
    "F-16A": "multirole",
    "F-16A MLU": "multirole",
    "FA-18C_hornet": "multirole",
    "F_A-18C": "multirole",
    "F-15E": "multirole",
    "F-15ESE": "multirole",
    "JF-17": "multirole",
    "MiG-29 Fulcrum": "multirole",
    "MiG-29A": "multirole",
    "MiG-29G": "multirole",
    "MiG-29S": "multirole",
    "MiG-21Bis": "multirole",
    "F-4E": "multirole",
    "F-4E-45MC": "multirole",
    "F-14B": "multirole",
    "F-14A-135-GR": "multirole",
    "F-14A-135-GR-Early": "multirole",
    "Su-30": "multirole",
    "Su-30MKA-AG": "multirole",
    "Su-30MKI-AG": "multirole",
    "Su-30MKM-AG": "multirole",
    "Su-30SM-AG": "multirole",
    "Su-34": "multirole",
    "Su-35S-AG": "multirole",
    "Su-33": "multirole",
    "Mirage-F1CT": "multirole",
    "Mirage-F1EE": "multirole",
    "Mirage-F1EQ": "multirole",
    "Mirage-F1M-CE": "multirole",
    "Mirage-F1M-EE": "multirole",
    # strike / attack jets
    "A6E": "strike_attack",
    "AJS37": "strike_attack",
    "AV8BNA": "strike_attack",
    "Su-24M": "strike_attack",
    "MiG-27K": "strike_attack",
    "Su-17M4": "strike_attack",
    # CAS specialists
    "A-10A": "cas_specialist",
    "A-10C": "cas_specialist",
    "A-10C_2": "cas_specialist",
    "Su-25": "cas_specialist",
    "Su-25T": "cas_specialist",
    # attack helos
    "AH-1W": "attack_helo",
    "AH-64A": "attack_helo",
    "AH-64D": "attack_helo",
    "AH-64D_BLK_II": "attack_helo",
    "Ka-50": "attack_helo",
    "Ka-50_3": "attack_helo",
    "Mi-24P": "attack_helo",
    "Mi-24V": "attack_helo",
    "Mi-28N": "attack_helo",
    # scout / light helos
    "OH-58D": "scout_helo",
    "OH58D": "scout_helo",
    "SA342L": "scout_helo",
    "SA342M": "scout_helo",
    "SA342Minigun": "scout_helo",
    "Mi-8MT": "scout_helo",
    "UH-1H": "scout_helo",
    # bombers
    "B-1B": "bomber",
    "B-52H": "bomber",
    "Tu-160": "bomber",
    "Tu-95MS": "bomber",
    "B-17G": "bomber",
    "H-6J": "bomber",
    "F-117A": "bomber",
    "Ju-88A4": "bomber",
    "A-20G": "bomber",
    # maritime
    "Tu-142": "maritime",
    "SH-60B": "maritime",
    "MosquitoFBMkVI": "maritime",
    # drones
    "MQ-9 Reaper": "drone",
    "RQ-1A Predator": "drone",
    "WingLoong-I": "drone",
}

# Deliberate overrides (formula loses): id -> {task: value}
OVERRIDES = {
    "Tu-22M3": {"Anti-ship": 815},
}

# Discarded-mod name prefixes (belt-and-suspenders on top of faction removals)
MOD_PREFIXES = (
    "VSN_",
    "vwv_",
    "CH_",
    "naboo",
    "TIE",
    "XWING",
    "YWING",
    "AWING",
    "CORVETTE",
    "FAUCON",
    "HUNTER",
)


def excluded_ids() -> set[str]:
    fac = open("game/factions/faction.py", encoding="utf-8").read()
    return set(re.findall(r'remove_aircraft\("([^"]+)"\)', fac))


def is_mod(stem: str) -> bool:
    return stem.startswith(MOD_PREFIXES)


def main() -> None:
    write = "--write" in sys.argv
    excl = excluded_ids()
    files = sorted(glob.glob("resources/units/aircraft/*.yaml"))
    changed_files = 0
    total_changes = 0
    skipped_no_archetype = []
    report = []
    for f in files:
        stem = os.path.splitext(os.path.basename(f))[0]
        if stem in excl or is_mod(stem):
            continue
        raw = open(f, encoding="utf-8", newline="").read()  # preserve CRLF/LF
        d = yaml.safe_load(raw) or {}
        tasks = d.get("tasks") or {}
        combat = {k: v for k, v in tasks.items() if k in COMBAT}
        if not combat:
            continue
        arch = ARCHETYPE.get(stem)
        if arch is None:
            skipped_no_archetype.append(stem)
            continue
        base = max(combat.values())
        if base <= 0:
            continue
        shape = SHAPES[arch]
        ov = OVERRIDES.get(stem, {})
        diffs = []
        new_tasks = dict(tasks)
        for task, mult in shape.items():
            cur = combat.get(task)
            if cur is None:
                continue  # never ADD a role the airframe deliberately lacks
            target = ov.get(task, round(base * mult))
            # Direction policy (intent-preserving):
            #  - Downward: always allowed -- rein in over-high secondary roles.
            #  - Upward: only when the weight is already near the airframe's base
            #    (a true magnitude fix), never to promote a deliberate secondary
            #    (e.g. F-15E A2A=470, Su-34 SEAD=30) into a primary role.
            if task not in ov and target > cur and cur < 0.85 * base:
                continue
            if abs(cur - target) > THRESHOLD and cur != target:
                diffs.append((task, cur, target))
                new_tasks[task] = target
        # honor explicit overrides even if task already present and within band
        for task, val in ov.items():
            if new_tasks.get(task) != val:
                diffs.append((task, new_tasks.get(task), val))
                new_tasks[task] = val
        if diffs:
            changed_files += 1
            total_changes += len(diffs)
            report.append((stem, arch, base, diffs))
            if write:
                _apply_value_changes(f, raw, diffs)
    # print report
    for stem, arch, base, diffs in report:
        print(f"\n{stem}  [{arch}, base={base}]")
        for task, cur, tgt in diffs:
            print(f"    {task:14} {str(cur):>5} -> {tgt}")
    print(
        f"\n=== {'APPLIED' if write else 'DRY-RUN'}: {changed_files} files, {total_changes} task changes ==="
    )
    if skipped_no_archetype:
        print(
            f"candidates with NO archetype mapping ({len(skipped_no_archetype)}): "
            + ", ".join(skipped_no_archetype)
        )


def _apply_value_changes(path: str, raw: str, diffs: list) -> None:
    """Surgically replace only the changed `  <task>: <old>` values in the raw
    text, leaving every other byte (line endings, trailing newline) untouched so
    the diff is minimal."""
    text = raw
    for task, cur, tgt in diffs:
        pat = re.compile(
            r'(^[ \t]+(?:"?'
            + re.escape(task)
            + r'"?)[ \t]*:[ \t]*)'
            + re.escape(str(cur))
            + r"(?=\s*$)",
            re.MULTILINE,
        )
        new_text, n = pat.subn(r"\g<1>" + str(tgt), text)
        if n != 1:
            raise RuntimeError(f"{path}: expected 1 match for {task}={cur}, got {n}")
        text = new_text
    with open(path, "wb") as fh:
        fh.write(text.encode("utf-8"))


if __name__ == "__main__":
    main()
