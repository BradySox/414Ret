"""Fix duplicate Lua table keys in red_tide.miz that silently dropped groups.

The Kastrup/Copenhagen hand-edits appended new vehicle and static groups reusing
the integer keys [1]/[2] that the stock groups (and each other) already held. In
Lua a later [k] assignment overwrites the earlier one, so four red vehicle groups
(Ground-2-1, Ground-3-1, the Kastrup SHORAD + AAA) and two static groups (both
Invisible FARPs) were silently dropped on load.

Fix: give the six hand-added Kastrup blocks fresh, unused keys (vehicle 55-58,
static 38/39) so every group survives. groupIds/unitIds are already unique and are
untouched -- only the table keys change. The mission member is re-packed with
zipfile so every other member stays byte-for-byte identical (pydcs Mission.save is
broken for this miz).
"""

import shutil
import zipfile
from pathlib import Path

MIZ = Path("resources/campaigns/red_tide.miz")
BACKUP = MIZ.with_suffix(".miz.bak_dupkeys")

# (line index, expected stripped key, new key) -- line indices verified against the
# current mission member; the script asserts the expected content before editing.
EDITS = [
    (17752, "[1] =", "[55] ="),  # Ground-Kastrup-SHORAD-1 (vehicle)
    (17810, "[2] =", "[56] ="),  # Ground-Kastrup-AAA-1     (vehicle)
    (17869, "[1] =", "[57] ="),  # Ground-Kastrup-LORAD-1   (vehicle)
    (17931, "[2] =", "[58] ="),  # Ground-Kastrup-MRAD-1    (vehicle)
    (19050, "[1] =", "[38] ="),  # Kastrup Command Center   (static)
    (19091, "[2] =", "[39] ="),  # Kastrup Ammo Depot       (static)
]


def main() -> None:
    with zipfile.ZipFile(MIZ, "r") as z:
        members = {n: z.read(n) for n in z.namelist()}
        infos = {i.filename: i for i in z.infolist()}

    text = members["mission"].decode("utf-8")
    assert "\r\n" not in text, "expected bare-LF mission member"
    lines = text.split("\n")

    for idx, expected, new in EDITS:
        stripped = lines[idx].strip()
        assert stripped == expected, f"line {idx}: got {stripped!r}, want {expected!r}"
        indent = lines[idx][: len(lines[idx]) - len(lines[idx].lstrip("\t"))]
        lines[idx] = indent + new

    members["mission"] = "\n".join(lines).encode("utf-8")

    shutil.copy2(MIZ, BACKUP)
    with zipfile.ZipFile(MIZ, "w", zipfile.ZIP_DEFLATED) as z:
        for name, info in infos.items():
            zi = zipfile.ZipInfo(name, date_time=info.date_time)
            zi.compress_type = info.compress_type
            zi.external_attr = info.external_attr
            z.writestr(zi, members[name])

    print(f"Patched {len(EDITS)} keys; backup at {BACKUP}")


if __name__ == "__main__":
    main()
