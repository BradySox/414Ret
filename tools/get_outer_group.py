"""Print the full outer group block containing a given unit type."""

import zipfile
import re
import sys

miz = sys.argv[1]
target_type = sys.argv[2]
target_line_hint = int(sys.argv[3]) if len(sys.argv) > 3 else -1

with zipfile.ZipFile(miz, "r") as z:
    with z.open("mission") as f:
        lines = f.read().decode("utf-8", errors="replace").split("\n")

# Find the target line
target_line = next(
    (i for i, l in enumerate(lines) if f'"type"] = "{target_type}"' in l), -1
)
if target_line < 0:
    print(f"'{target_type}' not found")
    raise SystemExit(1)

# Scan back to find groupId
gid_line = next(
    (
        i
        for i in range(target_line, max(0, target_line - 200), -1)
        if '"groupId"]' in lines[i]
    ),
    -1,
)

# Scan back further to find the array index opening
start = target_line
for i in range(
    gid_line if gid_line > 0 else target_line, max(0, target_line - 200), -1
):
    if re.match(r"\s*\[\d+\]\s*=$", lines[i].rstrip()):
        start = i
        break

# Find end by brace counting
depth = 0
end = start
for k in range(start, min(len(lines), start + 100)):
    depth += lines[k].count("{")
    depth -= lines[k].count("}")
    if depth <= 0 and k > start:
        end = k
        break

print(f"=== Full group block for '{target_type}' (lines {start}-{end}) ===")
for k in range(start, end + 1):
    print(lines[k].rstrip())
