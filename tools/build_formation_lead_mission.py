"""Build the standalone Formation Lead Trainer training mission.

Emits a self-contained Caucasus .miz with four client Hornet slots airborne at
15,000 ft and the trainer script embedded inline, so it needs no Retribution,
no Saved Games script drop and no mod.

    python tools/build_formation_lead_mission.py [output.miz]

The script is embedded as DO SCRIPT text rather than DO SCRIPT FILE: a file
resource lives in the .miz's resource map and breaks the moment the mission is
re-saved from the editor on a machine without the source tree.
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

from dcs.mission import Mission
from dcs.planes import FA_18C_hornet
from dcs.terrain import Caucasus
from dcs.translation import String
from dcs.triggers import TriggerStart
from dcs.unit import Skill
from dcs.action import DoScript

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "resources/plugins/formationlead/formation_lead_trainer.lua"

BRIEFING = """\
FORMATION LEAD TRAINER

You are the lead. A virtual wingman flies your wing -- he is not the DCS AI. He
reacts late, his throttle and G are limited, and he falls out of position exactly
where a human would. Nothing you do can hurt him, and nothing he does affects your
aircraft. He only reports.

RADIO MENU (F10 -> Formation Lead Trainer)
  Set formation   Fingertip / Route / Cruise 0.5nm / Combat spread 1.5nm
  Debrief         Your score and every fault, any time
  Reset run       Start the grading over

WHY YOUR TURNS BREAK A HUMAN AND NOT THE AI
A wingman d metres out on the OUTSIDE of a turn at rate w must fly faster by
w x d, and must acquire that speed at d x w-dot. Both scale with how far out he
is. Fly the same turn wider and you multiply what you are asking of him.

  Fingertip  59 ft   turn up to 95 deg/s   roll in under 33 deg/s
  Route      492 ft  turn up to 11 deg/s   roll in under 30 deg/s
  Cruise     0.5 nm  turn up to 1.9 deg/s  roll in under 25 deg/s
  Spread     1.5 nm  turn up to 0.6 deg/s  roll in under 20 deg/s

SYLLABUS
1. Fingertip. 30 degrees of bank, roll in over a full four seconds. Level, then
   reverse. Target 100 percent.
2. Route. Same turns. Roll in slower. Watch what a snap reversal does.
3. Cruise 0.5nm. Fly a normal 30 degree turn and watch it fail. Then find the
   bank that holds -- it is around 8 degrees.
4. Combat spread. Try to find a bank that works. There is not one. That is the
   whole reason tactical turns exist.
5. Compound. Turn, climb and accelerate together, each one individually legal.
6. F10 -> Debrief.

Nothing is scored below 200 ft AGL or under 120 kt, so the pattern is free.
"""


def build(out_path: Path) -> Path:
    mission = Mission(terrain=Caucasus())
    # Local noon: formation references have to be visible to be flown to.
    mission.start_time = datetime.datetime(2016, 6, 15, 12, 0)

    usa = mission.country("USA")

    # Airborne start well clear of terrain and the Batumi/Kobuleti pattern: the
    # exercise is turns, and a student who has to think about a ridgeline is not
    # thinking about his wingman.
    start = mission.terrain.airports["Kobuleti"].position.point_from_heading(270, 40000)

    flight = mission.flight_group_inflight(
        country=usa,
        name="VIPER",
        aircraft_type=FA_18C_hornet,
        position=start,
        altitude=4572,  # 15,000 ft
        speed=154,  # ~300 kt TAS
        group_size=4,
    )

    # Every slot is a client so the squadron can fly it together and swap the lead.
    # A DCS AI wingman would defeat the point -- it holds position perfectly.
    for unit in flight.units:
        unit.skill = Skill.Client
    flight.units[0].name = "VIPER 1-1 (LEAD)"

    trigger = TriggerStart(comment="Load Formation Lead Trainer")
    trigger.add_action(DoScript(String(SCRIPT.read_text(encoding="utf-8"))))
    mission.triggerrules.triggers.append(trigger)

    mission.set_description_text(BRIEFING)
    mission.set_description_bluetask_text(
        "Fly the syllabus. F10 -> Formation Lead Trainer -> Debrief for your score."
    )

    mission.save(str(out_path))
    return out_path


def main() -> int:
    out = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else (REPO_ROOT / "resources/missions/414th_formation_lead_trainer.miz")
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    build(out)
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
