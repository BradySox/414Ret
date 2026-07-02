"""Assemble the upstream-ready Red Tide payload (see CARVE-MANIFEST.md).

Builds docs/dev/upstreaming/red-tide/payload/ from the fork's shipped campaign:

- red_tide.yaml     -- fork yaml with the fork-only YAML supply_routes/shipping_lanes
                       removed (baked into the miz instead), the four 414th-identity
                       squadron names swapped for existing upstream squadron defs,
                       the transport re-typed to the vanilla C-130, and the enemy
                       faction re-pointed at the new Russia 1988.
- red_tide.miz      -- fork miz + the 12 land supply routes baked back as blue
                       M-113 front-line path groups and the Baltic shipping lane as
                       a blue HandyWind group (upstream's native route mechanism;
                       the fork reads the same routes from YAML instead). Pure text
                       surgery on the mission Lua -- warehouses/options untouched.
- russia_1988.json  -- upstream russia_1980 verbatim + the stock SA-11 and
                       SA-10/S-300PS preset groups (both in service by 1988), so the
                       campaign's deep LORAD belt matches its premise without
                       touching a stock faction.
- blufor_late_coldwar.json -- upstream copy + one line: KC-135 Stratotanker MPRS
                       (the campaign fragged a drogue tanker for its Navy jets).
- resources/squadrons/**   -- the fork-only squadron defs the campaign references,
                       copied verbatim (all real units; the extra `mission_types`
                       key is unread by upstream and harmless).

Everything is diffed against upstream dev @ dce851ea (this fork's base) via git;
re-validate against CURRENT upstream dev before opening the PR (manifest step 3).

Usage: python docs/dev/upstreaming/red-tide/build_payload.py
"""

import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE / "payload"
UPSTREAM_BASE = "dce851ea"

SQUADRON_SWAPS = {
    "414th Voodoo Squadron": "23rd FS",
    "414th JFG Hornets": "VMFA-251",
    "414th Tactical Fighter Squadron": "336th Fighter Squadron",
    "414th Aviation Detachment": "HMLA-269 (UH-1H)",
}

BLUE_TYPES_USED = [
    "B-1B Lancer",
    "A-10C Thunderbolt II (Suite 3)",
    "Mirage-F1EE",
    "F-4E-45MC Phantom II",
    "A-6E Intruder",
    "F-15C Eagle",
    "F-14B Tomcat",
    "UH-1H Iroquois",
    "AH-1W SuperCobra",
    "B-52H Stratofortress",
    "F-16CM Fighting Falcon (Block 50)",
    "Tornado IDS",
    "F/A-18C Hornet (Lot 20)",
    "F-15E Strike Eagle (Suite 4+)",
    "KC-135 Stratotanker",
    "KC-135 Stratotanker MPRS",
    "C-130",
    "CH-47F Block I",
    "AH-64D Apache Longbow",
    "E-3A",
    "OH-58D(R) Kiowa Warrior",
]


def upstream(path: str) -> str:
    return subprocess.run(
        ["git", "show", f"{UPSTREAM_BASE}:{path}"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def upstream_has(path: str) -> bool:
    return (
        subprocess.run(
            ["git", "cat-file", "-e", f"{UPSTREAM_BASE}:{path}"], cwd=REPO
        ).returncode
        == 0
    )


# --------------------------------------------------------------------------- yaml
def build_yaml(fork_yaml: str) -> str:
    text = fork_yaml
    # Identity: the upstream copy is the public campaign; the fork keeps its own.
    text = text.replace(
        "NATO is going over to the attack, and the 414th Joint Fighter Group leads it --\n"
        "  American Eagles, Tomcats and Phantoms wing-to-wing with the Luftwaffe's own JG 74 'Moelders' --",
        "NATO is going over to the attack -- American Eagles, Tomcats and Phantoms\n"
        "  wing-to-wing with the Luftwaffe's own JG 74 'Moelders' --",
    )
    text = text.replace(
        "recommended_enemy_faction: Russia 1980",
        "recommended_enemy_faction: Russia 1988",
    )
    for old, new in SQUADRON_SWAPS.items():
        assert f"- {old}\n" in text, old
        text = text.replace(f"- {old}\n", f"- {new}\n")
    # The fork consolidated transports onto the (mod) C-130J-30; upstream flies
    # the vanilla C-130.
    text = text.replace("aircraft_type: C-130J-30", "aircraft_type: C-130")
    # Drop the fork-only YAML route definitions -- they are baked into the miz as
    # M-113 / HandyWind groups for upstream (its native mechanism).
    start = text.index("# Supply routes & shipping lanes")
    end = text.index("settings:")
    text = (
        text[:start]
        + "# Supply routes / front geometry and the Baltic shipping lane live in the\n"
        "# .miz as blue M-113 front-line path groups and a HandyWind lane group.\n"
        + text[end:]
    )
    assert "supply_routes" not in text and "shipping_lanes" not in text
    # Only the authors-credit line may still say 414th; no squadron identity remains.
    for leftover in SQUADRON_SWAPS:
        assert leftover not in text, leftover
    assert "Joint Fighter Group" not in text
    return text


# ------------------------------------------------------------------------ factions
def build_russia_1988() -> str:
    import json

    data = json.loads(upstream("resources/factions/russia_1980.json"))
    data["name"] = "Russia 1988"
    data["authors"] = data.get("authors", "") or "dcs-retribution"
    data["description"] = (
        "<p>Soviet armed forces of the late 1980s -- the russia_1980 order of battle "
        "with the long-range SAM belt that entered service across the decade: SA-10 "
        "(S-300PS, 1982) and SA-11 (1980). Built for the Germany - Red Tide campaign; "
        "usable anywhere a late-Cold-War Soviet IADS is wanted.</p>"
    )
    presets = data.get("preset_groups", [])
    for p in ("SA-11", "SA-10/S-300PS"):
        if p not in presets:
            presets.append(p)
    data["preset_groups"] = presets
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def build_blufor() -> str:
    import json

    data = json.loads(upstream("resources/factions/blufor_late_coldwar.json"))
    assert data["name"] == "Blufor Late Cold War (80s)"
    tankers = data.get("tankers", [])
    if "KC-135 Stratotanker MPRS" not in tankers:
        tankers.append("KC-135 Stratotanker MPRS")
    data["tankers"] = tankers
    have = set(
        data.get("aircrafts", [])
        + data.get("awacs", [])
        + data.get("tankers", [])
        + data.get("helicopters", [])
    )
    missing = [t for t in BLUE_TYPES_USED if t not in have]
    assert not missing, f"blufor missing: {missing}"
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


# ------------------------------------------------------------------ squadron defs
def collect_squadron_defs(fork_data: dict) -> list[Path]:
    names = set()
    for configs in fork_data["squadrons"].values():
        for cfg in configs:
            for entry in cfg.get("aircraft") or []:
                names.add(entry)
    names = {SQUADRON_SWAPS.get(n, n) for n in names}
    to_port = []
    for name in sorted(names):
        hits = subprocess.run(
            ["git", "grep", "-l", f"name: {name}", "--", "resources/squadrons"],
            cwd=REPO,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        exact = [
            h
            for h in hits
            if re.search(
                rf"^name: {re.escape(name)}\s*$",
                (REPO / h).read_text(encoding="utf-8"),
                re.M,
            )
        ]
        if not exact:
            # Plain aircraft-type references (e.g. "GAF JG 74" resolves; a bare
            # variant name never will) -- nothing to port for those.
            continue
        path = exact[0]
        if upstream_has(path) or any(
            re.search(rf"^name: {re.escape(name)}\s*$", upstream(p), re.M)
            for p in subprocess.run(
                [
                    "git",
                    "grep",
                    "-l",
                    f"name: {name}",
                    UPSTREAM_BASE,
                    "--",
                    "resources/squadrons",
                ],
                cwd=REPO,
                capture_output=True,
                text=True,
            )
            .stdout.replace(f"{UPSTREAM_BASE}:", "")
            .splitlines()
        ):
            continue  # already upstream
        to_port.append(Path(path))
    return to_port


# ------------------------------------------------------------------------- miz
POINT_TMPL = """\t\t\t\t\t\t\t\t\t\t\t\t[{idx}]=
\t\t\t\t\t\t\t\t\t\t\t\t{{
\t\t\t\t\t\t\t\t\t\t\t\t\t["ETA"]={eta},
\t\t\t\t\t\t\t\t\t\t\t\t\t["ETA_locked"]={eta_locked},
\t\t\t\t\t\t\t\t\t\t\t\t\t["action"]="{action}",
\t\t\t\t\t\t\t\t\t\t\t\t\t["alt"]=0,
\t\t\t\t\t\t\t\t\t\t\t\t\t["alt_type"]="BARO",
\t\t\t\t\t\t\t\t\t\t\t\t\t["formation_template"]="",
\t\t\t\t\t\t\t\t\t\t\t\t\t["name"]="",
\t\t\t\t\t\t\t\t\t\t\t\t\t["speed"]={speed},
\t\t\t\t\t\t\t\t\t\t\t\t\t["speed_locked"]=true,
\t\t\t\t\t\t\t\t\t\t\t\t\t["task"]=
\t\t\t\t\t\t\t\t\t\t\t\t\t{{
\t\t\t\t\t\t\t\t\t\t\t\t\t\t["id"]="ComboTask",
\t\t\t\t\t\t\t\t\t\t\t\t\t\t["params"]=
\t\t\t\t\t\t\t\t\t\t\t\t\t\t{{
\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t["tasks"]=
\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t{{
\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t}}
\t\t\t\t\t\t\t\t\t\t\t\t\t\t}}
\t\t\t\t\t\t\t\t\t\t\t\t\t}},
\t\t\t\t\t\t\t\t\t\t\t\t\t["type"]="Turning Point",
\t\t\t\t\t\t\t\t\t\t\t\t\t["x"]={x},
\t\t\t\t\t\t\t\t\t\t\t\t\t["y"]={y}
\t\t\t\t\t\t\t\t\t\t\t\t}}"""

VEHICLE_GROUP_TMPL = """\t\t\t\t\t\t\t[{idx}]=
\t\t\t\t\t\t\t{{
\t\t\t\t\t\t\t\t["groupId"]={group_id},
\t\t\t\t\t\t\t\t["hidden"]=false,
\t\t\t\t\t\t\t\t["hiddenOnMFD"]=false,
\t\t\t\t\t\t\t\t["hiddenOnPlanner"]=false,
\t\t\t\t\t\t\t\t["manualHeading"]=false,
\t\t\t\t\t\t\t\t["name"]="{name}",
\t\t\t\t\t\t\t\t["route"]=
\t\t\t\t\t\t\t\t{{
\t\t\t\t\t\t\t\t\t["points"]=
\t\t\t\t\t\t\t\t\t{{
{points}
\t\t\t\t\t\t\t\t\t}}
\t\t\t\t\t\t\t\t}},
\t\t\t\t\t\t\t\t["units"]=
\t\t\t\t\t\t\t\t{{
\t\t\t\t\t\t\t\t\t[1]=
\t\t\t\t\t\t\t\t\t{{
\t\t\t\t\t\t\t\t\t\t["coldAtStart"]=false,
\t\t\t\t\t\t\t\t\t\t["heading"]=0,
\t\t\t\t\t\t\t\t\t\t["name"]="{name}-1",
\t\t\t\t\t\t\t\t\t\t["playerCanDrive"]=false,
\t\t\t\t\t\t\t\t\t\t["skill"]="Average",
\t\t\t\t\t\t\t\t\t\t["type"]="{unit_type}",
\t\t\t\t\t\t\t\t\t\t["unitId"]={unit_id},
\t\t\t\t\t\t\t\t\t\t["x"]={x},
\t\t\t\t\t\t\t\t\t\t["y"]={y}
\t\t\t\t\t\t\t\t\t}}
\t\t\t\t\t\t\t\t}},
\t\t\t\t\t\t\t\t["visible"]=false,
\t\t\t\t\t\t\t\t["x"]={x},
\t\t\t\t\t\t\t\t["y"]={y}
\t\t\t\t\t\t\t}}"""

SHIP_GROUP_TMPL = """\t\t\t\t\t\t\t[{idx}]=
\t\t\t\t\t\t\t{{
\t\t\t\t\t\t\t\t["groupId"]={group_id},
\t\t\t\t\t\t\t\t["hidden"]=false,
\t\t\t\t\t\t\t\t["hiddenOnMFD"]=false,
\t\t\t\t\t\t\t\t["hiddenOnPlanner"]=false,
\t\t\t\t\t\t\t\t["name"]="{name}",
\t\t\t\t\t\t\t\t["route"]=
\t\t\t\t\t\t\t\t{{
\t\t\t\t\t\t\t\t\t["points"]=
\t\t\t\t\t\t\t\t\t{{
{points}
\t\t\t\t\t\t\t\t\t}}
\t\t\t\t\t\t\t\t}},
\t\t\t\t\t\t\t\t["start_time"]=0,
\t\t\t\t\t\t\t\t["tasks"]=
\t\t\t\t\t\t\t\t{{
\t\t\t\t\t\t\t\t}},
\t\t\t\t\t\t\t\t["units"]=
\t\t\t\t\t\t\t\t{{
\t\t\t\t\t\t\t\t\t[1]=
\t\t\t\t\t\t\t\t\t{{
\t\t\t\t\t\t\t\t\t\t["frequency"]=127500000,
\t\t\t\t\t\t\t\t\t\t["heading"]=0,
\t\t\t\t\t\t\t\t\t\t["name"]="{name}-1",
\t\t\t\t\t\t\t\t\t\t["skill"]="Average",
\t\t\t\t\t\t\t\t\t\t["type"]="{unit_type}",
\t\t\t\t\t\t\t\t\t\t["unitId"]={unit_id},
\t\t\t\t\t\t\t\t\t\t["x"]={x},
\t\t\t\t\t\t\t\t\t\t["y"]={y}
\t\t\t\t\t\t\t\t\t}}
\t\t\t\t\t\t\t\t}},
\t\t\t\t\t\t\t\t["visible"]=false,
\t\t\t\t\t\t\t\t["x"]={x},
\t\t\t\t\t\t\t\t["y"]={y}
\t\t\t\t\t\t\t}}"""


def render_points(waypoints, action: str) -> str:
    blocks = []
    for i, (x, y) in enumerate(waypoints, start=1):
        blocks.append(
            POINT_TMPL.format(
                idx=i,
                eta=0,
                eta_locked="true" if i == 1 else "false",
                action=action,
                speed=0 if i == 1 else 5.5555555555556,
                x=x,
                y=y,
            )
        )
    return ",\n".join(blocks)


def table_extent(text: str, open_brace: int) -> int:
    """Index just past the matching close brace for the brace at open_brace."""
    depth = 0
    for i in range(open_brace, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("unbalanced")


def splice_groups(text: str, section: str, blocks: list[str], anchor: int) -> str:
    """Append group blocks into the ["<section>"]["group"] table after anchor."""
    si = text.index(f'["{section}"]', anchor)
    gi = text.index('["group"]', si)
    open_brace = text.index("{", gi)
    close = table_extent(text, open_brace)
    body = text[open_brace : close + 1]
    last_idx = max(int(n) for n in re.findall(r"^\t{7}\[(\d+)\]=", body, re.M))
    rendered = []
    for offset, block in enumerate(blocks, start=1):
        rendered.append(block.replace("[{IDX}]=", f"[{last_idx + offset}]="))
    insertion = ",\n" + ",\n".join(rendered) + "\n\t\t\t\t\t\t"
    # insert before the table's closing brace (strip trailing newline+tabs first)
    head = text[:close].rstrip("\n\t ")
    return head + insertion + text[close:]


def build_miz(fork_yaml_data: dict) -> None:
    src = REPO / "resources/campaigns/red_tide.miz"
    with zipfile.ZipFile(src) as z:
        mission = z.read("mission").decode("utf-8")

    next_group = max(int(x) for x in re.findall(r'\["groupId"\]=(\d+)', mission)) + 88
    next_unit = max(int(x) for x in re.findall(r'\["unitId"\]=(\d+)', mission)) + 88

    blue_at = mission.index('"Combined Joint Task Forces Blue"')

    vehicle_blocks = []
    for n, route in enumerate(fork_yaml_data["supply_routes"], start=1):
        wps = route["waypoints"]
        vehicle_blocks.append(
            VEHICLE_GROUP_TMPL.format(
                idx="{IDX}",
                group_id=next_group,
                name=f"SupplyRoute-{n}",
                points=render_points(wps, "On Road"),
                unit_type="M-113",
                unit_id=next_unit,
                x=wps[0][0],
                y=wps[0][1],
            ).replace("[{IDX}]=", "[{IDX}]=")
        )
        next_group += 1
        next_unit += 1

    ship_blocks = []
    for n, lane in enumerate(fork_yaml_data["shipping_lanes"], start=1):
        wps = lane["waypoints"]
        ship_blocks.append(
            SHIP_GROUP_TMPL.format(
                idx="{IDX}",
                group_id=next_group,
                name=f"ShippingLane-{n}",
                points=render_points(wps, "Turning Point"),
                unit_type="HandyWind",
                unit_id=next_unit,
                x=wps[0][0],
                y=wps[0][1],
            )
        )
        next_group += 1
        next_unit += 1

    before_braces = mission.count("{") - mission.count("}")
    mission = splice_groups(mission, "vehicle", vehicle_blocks, blue_at)
    blue_at = mission.index('"Combined Joint Task Forces Blue"')
    mission = splice_groups(mission, "ship", ship_blocks, blue_at)
    assert mission.count("{") - mission.count("}") == before_braces

    # Verify every route/lane landed (group names only; unit names add a -1 suffix).
    assert len(re.findall(r'\["name"\]="SupplyRoute-\d+",', mission)) == len(
        vehicle_blocks
    )
    assert len(re.findall(r'\["name"\]="ShippingLane-\d+",', mission)) == len(
        ship_blocks
    )

    dst = PAYLOAD / "resources/campaigns/red_tide.miz"
    dst.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(
        dst, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            if item.filename == "mission":
                zout.writestr(item, mission.encode("utf-8"))
            else:
                zout.writestr(item, zin.read(item.filename))
    print(f"miz: +{len(vehicle_blocks)} route groups, +{len(ship_blocks)} lane groups")


def main() -> None:
    if PAYLOAD.exists():
        shutil.rmtree(PAYLOAD)
    fork_yaml = (REPO / "resources/campaigns/red_tide.yaml").read_text(encoding="utf-8")
    fork_data = yaml.safe_load(fork_yaml)

    out_yaml = PAYLOAD / "resources/campaigns/red_tide.yaml"
    out_yaml.parent.mkdir(parents=True, exist_ok=True)
    out_yaml.write_text(build_yaml(fork_yaml), encoding="utf-8", newline="")
    yaml.safe_load(out_yaml.read_text(encoding="utf-8"))  # parses

    (PAYLOAD / "resources/factions").mkdir(parents=True, exist_ok=True)
    (PAYLOAD / "resources/factions/russia_1988.json").write_text(
        build_russia_1988(), encoding="utf-8", newline=""
    )
    (PAYLOAD / "resources/factions/blufor_late_coldwar.json").write_text(
        build_blufor(), encoding="utf-8", newline=""
    )

    ported = collect_squadron_defs(fork_data)
    for path in ported:
        # Drop the fork branding from filenames (contents are already historical).
        dst = PAYLOAD / path.parent / path.name.replace("414th ", "")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / path, dst)
        # The fork consolidated transports onto the (mod) C-130J-30; upstream
        # flies the vanilla C-130.
        text = dst.read_text(encoding="utf-8")
        if "aircraft: C-130J-30" in text:
            dst.write_text(
                text.replace("aircraft: C-130J-30", "aircraft: C-130"),
                encoding="utf-8",
                newline="",
            )
    print(f"squadron defs ported: {len(ported)}")
    for p in ported:
        print("  ", p)

    build_miz(fork_data)
    print("payload assembled at", PAYLOAD)


if __name__ == "__main__":
    main()
