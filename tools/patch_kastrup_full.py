"""
Comprehensive Kastrup/Copenhagen patch for red_tide.miz:
  1. Fix existing AAA (Shilka) group — was in water NE of airport, move to land SW
  2. Add S-300 long-range SAM vehicle group (red coalition)
  3. Add SA-75M medium-range SAM vehicle group (red coalition)
  4. Add Workshop A factory static group (red coalition)
  5. Add .Ammunition depot static group (red coalition)

Kastrup (CP 41) center: x=133729, y=-489625
Land is W/SW of the airport; water is NE (Oresund strait).
"""

import zipfile
import re
import shutil
from pathlib import Path

MIZ = Path("resources/campaigns/red_tide.miz")
BACKUP = MIZ.with_suffix(".miz.bak2")

# ---------------------------------------------------------------------------
# New groups to add
# ---------------------------------------------------------------------------

# Vehicle groups — go into red coalition ["vehicle"]["group"]
NEW_VEHICLE_GROUPS = [
    {
        "name": "Ground-Kastrup-LORAD",
        "unit_name": "Ground-Kastrup-LORAD-1",
        "type": "S-300PS 5P85C ln",
        "x": 128500.0,
        "y": -494000.0,  # ~5 km SW of airport, firmly on land
        "heading": 0.0,
        "drive": False,
    },
    {
        "name": "Ground-Kastrup-MRAD",
        "unit_name": "Ground-Kastrup-MRAD-1",
        "type": "S_75M_Volhov",
        "x": 131200.0,
        "y": -491500.0,  # ~2.5 km W/SW of airport, on land
        "heading": 0.0,
        "drive": False,
    },
]

# Static groups — go into red coalition ["static"]["group"]
NEW_STATIC_GROUPS = [
    {
        "name": "Kastrup Factory",
        "unit_name": "Kastrup Factory",
        "type": "Workshop A",
        "category": "Fortifications",
        "shape_name": "tec_a",
        "x": 130000.0,
        "y": -493500.0,  # ~3.5 km SW of airport
        "heading": 0.0,
    },
    {
        "name": "Kastrup Ammo Depot",
        "unit_name": "Kastrup Ammo Depot",
        "type": ".Ammunition depot",
        "category": "Warehouses",
        "shape_name": "SkladC",
        "x": 129500.0,
        "y": -491000.0,  # ~4 km SW of airport
        "heading": 0.0,
    },
]

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

VEHICLE_GROUP_TEMPLATE = """							[{group_idx}] =
							{{
								["visible"] = false,
								["tasks"] = {{}},
								["uncontrollable"] = false,
								["task"] = "Ground Nothing",
								["taskSelected"] = true,
								["route"] =
								{{
									["spans"] = {{}},
									["points"] =
									{{
										[1] =
										{{
											["alt"] = 8,
											["type"] = "Turning Point",
											["ETA"] = 0,
											["alt_type"] = "BARO",
											["formation_template"] = "",
											["y"] = {y},
											["x"] = {x},
											["ETA_locked"] = true,
											["speed"] = 0,
											["action"] = "Off Road",
											["task"] =
											{{
												["id"] = "ComboTask",
												["params"] =
												{{
													["tasks"] = {{}},
												}}, -- end of ["params"]
											}}, -- end of ["task"]
											["speed_locked"] = true,
										}}, -- end of [1]
									}}, -- end of ["points"]
								}}, -- end of ["route"]
								["groupId"] = {group_id},
								["hidden"] = false,
								["units"] =
								{{
									[1] =
									{{
										["transportable"] =
										{{
											["randomTransportable"] = false,
										}}, -- end of ["transportable"]
										["skill"] = "Average",
										["coldAtStart"] = false,
										["type"] = "{unit_type}",
										["unitId"] = {unit_id},
										["y"] = {y},
										["x"] = {x},
										["name"] = "{unit_name}",
										["heading"] = {heading},
										["playerCanDrive"] = {drive},
									}}, -- end of [1]
								}}, -- end of ["units"]
								["y"] = {y},
								["x"] = {x},
								["name"] = "{group_name}",
								["start_time"] = 0,
							}}, -- end of [{group_idx}]
"""

STATIC_GROUP_TEMPLATE = """						[{group_idx}] =
						{{
							["heading"] = {heading},
							["route"] =
							{{
								["points"] =
								{{
									[1] =
									{{
										["alt"] = 0,
										["type"] = "",
										["name"] = "",
										["y"] = {y},
										["speed"] = 0,
										["x"] = {x},
										["formation_template"] = "",
										["action"] = "",
									}}, -- end of [1]
								}}, -- end of ["points"]
							}}, -- end of ["route"]
							["groupId"] = {group_id},
							["units"] =
							{{
								[1] =
								{{
									["category"] = "{category}",
									["shape_name"] = "{shape_name}",
									["type"] = "{unit_type}",
									["unitId"] = {unit_id},
									["rate"] = 100,
									["y"] = {y},
									["x"] = {x},
									["name"] = "{unit_name}",
									["heading"] = {heading},
								}}, -- end of [1]
							}}, -- end of ["units"]
							["y"] = {y},
							["x"] = {x},
							["name"] = "{group_name}",
							["dead"] = false,
						}}, -- end of [{group_idx}]
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def find_max_ids(content: str) -> tuple[int, int]:
    group_ids = [int(m) for m in re.findall(r'"groupId"\]\s*=\s*(\d+)', content)]
    unit_ids = [int(m) for m in re.findall(r'"unitId"\]\s*=\s*(\d+)', content)]
    return max(group_ids, default=0), max(unit_ids, default=0)


def find_red_start(lines: list[str]) -> int:
    for i, line in enumerate(lines):
        if '"name"] = "red"' in line:
            return i
    raise RuntimeError("Could not find red coalition section")


def find_section_end(lines: list[str], start: int, section_key: str) -> int:
    """Find the closing bracket of ["section_key"]["group"] inside the red coalition."""
    in_section = False
    group_block_start = -1
    depth = 0
    for i in range(start, len(lines)):
        line = lines[i]
        if f'["{section_key}"]' in line and not in_section:
            in_section = True
        if in_section and '["group"]' in line and group_block_start < 0:
            group_block_start = i
            depth = 0
        if group_block_start >= 0:
            depth += line.count("{")
            depth -= line.count("}")
            if depth <= 0 and i > group_block_start:
                return i
    raise RuntimeError(f"Could not find red [{section_key}][group] closing bracket")


def highest_index_in_block(lines: list[str], block_end: int) -> int:
    for i in range(block_end, max(0, block_end - 4000), -1):
        if '["group"]' in lines[i]:
            section = "\n".join(lines[i:block_end])
            indices = [
                int(m) for m in re.findall(r"^\s*\[(\d+)\]\s*=\s*$", section, re.M)
            ]
            return max(indices, default=0)
    return 0


# ---------------------------------------------------------------------------
# Fix existing AAA group coordinates (was in water)
# ---------------------------------------------------------------------------


def fix_aaa_position(content: str) -> str:
    """Move Ground-Kastrup-AAA from water (136000, -486800) to land (131000, -494500)."""
    old_x = "136000.0"
    old_y = "-486800.0"
    new_x = "131000.0"
    new_y = "-494500.0"

    # Only replace within the Ground-Kastrup-AAA block
    idx = content.find('"Ground-Kastrup-AAA"')
    if idx < 0:
        print("WARNING: Ground-Kastrup-AAA not found — skipping position fix")
        return content

    # Replace all occurrences of old coords in a window around the group name
    window_start = max(0, idx - 2000)
    window_end = min(len(content), idx + 500)
    block = content[window_start:window_end]
    block = block.replace(old_x, new_x).replace(old_y, new_y)
    return content[:window_start] + block + content[window_end:]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def patch():
    shutil.copy2(MIZ, BACKUP)
    print(f"Backup: {BACKUP}")

    with zipfile.ZipFile(MIZ, "r") as z:
        names = z.namelist()
        files = {n: z.read(n) for n in names}

    content = files["mission"].decode("utf-8", errors="replace")

    # 1. Fix the AAA position
    content = fix_aaa_position(content)
    print("Fixed Ground-Kastrup-AAA position to land (131000, -494500)")

    lines = content.split("\n")
    max_gid, max_uid = find_max_ids(content)
    print(f"Max groupId={max_gid}, max unitId={max_uid}")

    red_start = find_red_start(lines)
    print(f"Red coalition at line {red_start}")

    # 2. Add vehicle groups (S-300 + SA-75M)
    veh_end = find_section_end(lines, red_start, "vehicle")
    next_veh_idx = highest_index_in_block(lines, veh_end) + 1
    print(f"Vehicle group end line {veh_end}, next index {next_veh_idx}")

    veh_insertion = ""
    for g in NEW_VEHICLE_GROUPS:
        max_gid += 1
        max_uid += 1
        veh_insertion += VEHICLE_GROUP_TEMPLATE.format(
            group_idx=next_veh_idx,
            group_id=max_gid,
            unit_id=max_uid,
            unit_type=g["type"],
            unit_name=g["unit_name"],
            group_name=g["name"],
            x=g["x"],
            y=g["y"],
            heading=g["heading"],
            drive=str(g["drive"]).lower(),
        )
        next_veh_idx += 1

    lines = (
        content.split("\n")[:veh_end]
        + veh_insertion.split("\n")
        + content.split("\n")[veh_end:]
    )
    content = "\n".join(lines)

    # Recompute after insertion
    lines = content.split("\n")
    max_gid, max_uid = find_max_ids(content)
    red_start = find_red_start(lines)

    # 3. Add static groups (factory + ammo depot)
    # Static groups may not exist yet in red — handle missing static section
    try:
        static_end = find_section_end(lines, red_start, "static")
    except RuntimeError:
        print(
            "WARNING: No static group section found in red coalition — static groups skipped"
        )
        static_end = -1

    if static_end >= 0:
        next_static_idx = highest_index_in_block(lines, static_end) + 1
        print(f"Static group end line {static_end}, next index {next_static_idx}")

        static_insertion = ""
        for g in NEW_STATIC_GROUPS:
            max_gid += 1
            max_uid += 1
            static_insertion += STATIC_GROUP_TEMPLATE.format(
                group_idx=next_static_idx,
                group_id=max_gid,
                unit_id=max_uid,
                unit_type=g["type"],
                unit_name=g["unit_name"],
                group_name=g["name"],
                category=g["category"],
                shape_name=g["shape_name"],
                x=g["x"],
                y=g["y"],
                heading=g["heading"],
            )
            next_static_idx += 1

        lines = (
            content.split("\n")[:static_end]
            + static_insertion.split("\n")
            + content.split("\n")[static_end:]
        )
        content = "\n".join(lines)

    files["mission"] = content.encode("utf-8")

    with zipfile.ZipFile(MIZ, "w", zipfile.ZIP_DEFLATED) as z:
        for name in names:
            z.writestr(name, files[name])

    print("\nDone:")
    print("  - AAA position fixed (was water, now land SW of airport)")
    for g in NEW_VEHICLE_GROUPS:
        print(f"  - Added vehicle: {g['name']} ({g['type']})")
    if static_end >= 0:
        for g in NEW_STATIC_GROUPS:
            print(f"  - Added static:  {g['name']} ({g['type']})")


if __name__ == "__main__":
    patch()
