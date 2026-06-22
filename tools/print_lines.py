"""Print lines N-M from a .miz mission file."""

import zipfile
import sys

miz = sys.argv[1]
start = int(sys.argv[2])
end = int(sys.argv[3])

with zipfile.ZipFile(miz, "r") as z:
    with z.open("mission") as f:
        lines = f.read().decode("utf-8", errors="replace").split("\n")

for k in range(start, min(end + 1, len(lines))):
    print(f"{k}: {lines[k].rstrip()}")
