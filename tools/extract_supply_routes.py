import zipfile
import re
import sys

miz_path = sys.argv[1] if len(sys.argv) > 1 else "resources/campaigns/red_tide.miz"

with zipfile.ZipFile(miz_path, "r") as z:
    with z.open("mission") as f:
        content = f.read().decode("utf-8", errors="replace")

lines = content.split("\n")

m113_lines = [i for i, l in enumerate(lines) if '"type"] = "M-113"' in l]
print(f"Found {len(m113_lines)} M-113 units")

seen_groups = set()
for unit_line in m113_lines:
    # Find nearest group name above
    gname = None
    for j in range(unit_line, max(0, unit_line - 80), -1):
        m = re.search(r'"name"\] = "(.+?)"', lines[j])
        if m:
            name = m.group(1)
            if not name.endswith("-1") and not name.endswith("-2"):
                gname = name
                break

    if gname in seen_groups:
        continue
    seen_groups.add(gname)

    # Find waypoints in the points block
    wpts = []
    for j in range(unit_line, max(0, unit_line - 200), -1):
        if '"points"]' in lines[j]:
            k = j + 1
            while k < min(len(lines), j + 200):
                ym = re.search(r'"y"\] = ([-\d.]+)', lines[k])
                if ym:
                    if k + 1 < len(lines):
                        xm = re.search(r'"x"\] = ([-\d.]+)', lines[k + 1])
                        if xm:
                            wpts.append((float(xm.group(1)), float(ym.group(1))))
                if "end of" in lines[k] and "points" in lines[k]:
                    break
                k += 1
            break

    print(f"\n  Group: {gname}")
    for idx, (x, y) in enumerate(wpts):
        print(f"    wpt {idx+1}: x={x:.0f}, y={y:.0f}")
