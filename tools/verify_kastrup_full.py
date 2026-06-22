"""Verify all Kastrup preset groups are present and in the red coalition."""

import zipfile

with zipfile.ZipFile("resources/campaigns/red_tide.miz", "r") as z:
    with z.open("mission") as f:
        lines = f.read().decode("utf-8", errors="replace").split("\n")

expected = [
    "Ground-Kastrup-SHORAD",
    "Ground-Kastrup-AAA",
    "Ground-Kastrup-LORAD",
    "Ground-Kastrup-MRAD",
    "Kastrup Factory",
    "Kastrup Ammo Depot",
]

red_start = next(i for i, l in enumerate(lines) if '"name"] = "red"' in l)

for name in expected:
    line_no = next(
        (
            i
            for i, l in enumerate(lines)
            if f'"name"] = "{name}"' in l and f"{name}-1" not in l
        ),
        -1,
    )
    if line_no < 0:
        print(f"  MISSING: {name}")
        continue
    # Find x/y near the group name
    x_val = next(
        (
            lines[k]
            for k in range(line_no - 5, line_no + 5)
            if '"x"] =' in lines[k] and '"name"]' not in lines[k]
        ),
        "?",
    )
    y_val = next(
        (
            lines[k]
            for k in range(line_no - 5, line_no + 5)
            if '"y"] =' in lines[k] and '"name"]' not in lines[k]
        ),
        "?",
    )
    coalition = "RED" if line_no > red_start else "BLUE"
    print(f"  {coalition}  line {line_no:5d}  {name}")
    print(f"           x:{x_val.strip()}  y:{y_val.strip()}")
