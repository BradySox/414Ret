"""Find example static group structures in a .miz."""

import zipfile
import re
import sys

miz = sys.argv[1] if len(sys.argv) > 1 else "resources/campaigns/red_tide.miz"
targets = sys.argv[2:] if len(sys.argv) > 2 else ["Workshop A", ".Ammunition depot"]

with zipfile.ZipFile(miz, "r") as z:
    with z.open("mission") as f:
        lines = f.read().decode("utf-8", errors="replace").split("\n")

for target in targets:
    found = False
    for i, line in enumerate(lines):
        if f'"type"] = "{target}"' in line:
            # Scan back to find the enclosing group start
            start = i
            for j in range(i, max(0, i - 60), -1):
                stripped = lines[j].strip()
                if re.match(r"\[\d+\]\s*=$", stripped):
                    start = j
                    break
            # Scan forward to end of group
            depth = 0
            end = start
            for k in range(start, min(len(lines), start + 80)):
                depth += lines[k].count("{")
                depth -= lines[k].count("}")
                if depth <= 0 and k > start:
                    end = k
                    break
            print(f"=== {target} at line {i} ===")
            for k in range(start, end + 1):
                print(lines[k].rstrip())
            print()
            found = True
            break
    if not found:
        print(f"No '{target}' found in {miz}")
