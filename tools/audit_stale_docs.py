"""Find published docs that still describe a removed feature.

``CLAUDE.md`` step 7: when a feature's RULE changes, the feature's own doc faces are
not enough -- every *other* note that merely mentions it is now wrong too, and those
are what get missed. The 2026-08-18 §3 rework updated 16 files and left 8 stale
claims, two of them on the published wiki. The 2026-08-07 CSAR replacement updated
the design note and left **five** published pages briefing a package that no longer
existed, including a sidebar-linked wiki page written in the present tense.

That step is a manual grep nobody runs. This makes it a command.

Scope is the **published** surface only -- ``README.md``, ``docs/wiki/`` and
``docs/campaigns/``. Design notes under ``docs/dev/`` are deliberately excluded:
they are a historical record and are *expected* to describe dead features.

A file whose opening carries a removal banner is exempt, so the established
"banner it and keep it so old saves stay readable" pattern does not trip the
audit. See ``docs/wiki/Campaign-Phases-and-ROE.md`` for the shape.

    python tools/audit_stale_docs.py            # report; exit 1 if anything is found
    python tools/audit_stale_docs.py --quiet    # exit status only, for a CI gate

**Adding a feature when you remove one.** Append a :class:`Removed` row carrying the
terms that only make sense if the feature is *live*. Prefer a distinctive setting
name, class name or role name over a generic English word -- a broad pattern buries
the real hit in false positives, which is how the rule stopped being run by hand.
The first draft matched a bare "suspected activity" for §79 and flagged the COMINT
and COIN circles, which are both still real. Anything the audit should tolerate goes
in ``allow``: a substring that, when present on the matched line, means the mention
is a correct statement that the feature is gone.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO = Path(__file__).resolve().parent.parent

#: The published surface. Design notes are excluded on purpose -- see the module docstring.
ROOTS = ("README.md", "docs/wiki", "docs/campaigns")

#: A file opening with one of these is a deliberate historical record, not a defect.
BANNERS = ("⛔ REMOVED", "historical record only", "SUPERSEDED")

#: How much of a file to scan for a banner.
BANNER_WINDOW = 1200

#: Words that mean the surrounding prose is *reporting* a removal rather than
#: describing a live feature. Applied to every entry on top of its own ``allow``.
#:
#: Matched against the whole paragraph, never the single line: markdown wraps at
#: about 95 characters, so "the old X package no longer exists" routinely puts the
#: name and the disclaimer on different lines. Line-scoped matching flagged eleven
#: correctly-written pages on the first run.
REMOVAL_WORDS = (
    "removed",
    "Removed",
    "retired",
    "Retired",
    "reverted",
    "deleted",
    "no longer",
    "is gone",
    "are gone",
    "went with",
    "replaced",
    "supersede",
    "Supersede",
    "historical",
    "was an option",
    "does not exist",
    "never restore",
    "removal",
    "not shipped",
    "unsupported",
    "moot in this fork",
)


@dataclass(frozen=True)
class Removed:
    """One removed feature and the words that imply it is still live."""

    what: str
    when: str
    pattern: str
    #: Substrings that make a match a correct "it was removed" statement.
    allow: tuple[str, ...] = ()


REMOVED: tuple[Removed, ...] = (
    Removed(
        "SCAR / the Sandy rescue escort (S15)",
        "2026-08-07",
        r"\bSandy\b|FlightType\.SCAR|Jolly Green|auto_combat_sar|snatch party"
        r"|combat_sar_surge|combat_sar_persistent",
        allow=("removed", "no longer exists", "historical"),
    ),
    Removed(
        "the fork's own Combat SAR (S21), replaced by upstream #929",
        "2026-08-07",
        r"FlightType\.COMBAT_SAR|\bcombatsar\b|HC-130|survivor ledger"
        r"|pow_recovery|\bLARS\b",
        allow=("removed", "no longer exists", "historical", "replaced"),
    ),
    Removed(
        "campaign phases, ROE zones and target release (S40)",
        "2026-07-21",
        r"restricted_zones:|free_fire_zones:|campaign_phase|free-fire zone|ROE zone",
        allow=("removed", "Removed:", "no longer"),
    ),
    Removed(
        "the political-will economy and the war economy (S48, S53, S54)",
        "2026-07-21",
        r"[Pp]olitical [Ww]ill|Regime Resolve|war economy|munitions availability"
        r"|commitment ceiling",
        allow=("removed", "Removed:", "no longer"),
    ),
    Removed(
        "Red Intent adaptive posture (S55)",
        "2026-07-21",
        r"[Rr]ed [Ii]ntent|red_intent",
        allow=("removed", "no longer"),
    ),
    Removed(
        # NOT a bare "suspected activity": COMINT and COIN both still draw real ones.
        "decoy suspected-activity zones (S79)",
        "2026-08-18",
        r"decoy[- ]?(suspected|activity)|fake (activity|suspected)",
        allow=("removed", "no longer"),
    ),
    Removed(
        "the living-battlespace voice net (S89's second layer)",
        "2026-08-18",
        r"voice net|voicenet",
        allow=("removed", "no longer"),
    ),
    Removed(
        "The Wing Grows (S82)",
        "2026-08-16",
        r"[Ww]ing [Gg]rows|wing_growth|scheduled squadron arrival",
        allow=("removed", "no longer"),
    ),
    Removed(
        "old-stock loadout attrition (S84)",
        "2026-08-06",
        r"old-stock|loadout attrition|weapon_attrition",
        allow=("removed", "no longer"),
    ),
    Removed(
        "route-aware fuel-tank planning (S46, fuel-first)",
        "2026-08-09",
        r"fuel-first|route-aware fuel|fuel_first",
        allow=("reverted", "removed", "no longer"),
    ),
    Removed(
        "the reverted air-defence planner geometry (S6)",
        "2026-08-09",
        r"forward CAP line|threat-weighted volume|forward-middle layer|FLOT navmesh",
        allow=("reverted", "removed", "are all gone", "no longer"),
    ),
    Removed(
        "the recon-to-BDA bridge and scout-to-reveal (S3)",
        "2026-08-18",
        r"alive_at_last_recon|sync_confirmed_status|until scouted|BDA lag"
        r"|confirmed BDA|banks what",
        allow=("removed", "no longer", "does not"),
    ),
    Removed(
        "the per-base backstop EWR (S1) and the generic ewrj jammer (S2)",
        "n/a -- never restore",
        r"backstop EWR|\bewrj\b",
        allow=("retired", "removed", "is gone", "no longer", "upersede"),
    ),
    Removed(
        "MIST",
        "2026-07-10",
        r"mist_4_5_126|\bMIST\b",
        allow=("retired", "removed", "shim", "MIST→MOOSE", "MIST-to-MOOSE"),
    ),
    Removed(
        "the Skynet IADS engine",
        "2026-06",
        r"[Ss]kynet",
        allow=("removed", "retired", "sole IADS engine", "What happened to"),
    ),
    Removed(
        "Pretense",
        "n/a -- ripped out",
        r"[Pp]retense",
        allow=("removed", "no longer"),
    ),
    Removed(
        "the blank-start campaign maker and drop-spawn placement (S20)",
        "2026-08-02",
        r"blank-start|blank canvas|campaign maker|drop-spawn",
        allow=("removed", "no longer"),
    ),
    Removed(
        "the SOF capture economy",
        "2026-07-01",
        r"SOF Insert|SOF capture|capture economy",
        allow=("removed", "retired", "no longer"),
    ),
    Removed(
        "Flight Control ATC (S13)",
        "2026-06-26",
        r"Flight Control ATC|`flightcontrol`",
        allow=("retired", "removed", "no longer"),
    ),
)


def published_files() -> list[Path]:
    out: list[Path] = []
    for root in ROOTS:
        path = REPO / root
        if path.is_file():
            out.append(path)
        else:
            out.extend(sorted(path.rglob("*.md")))
    return out


def is_historical(path: Path) -> bool:
    """True for a page that opens by declaring itself a record of something removed."""
    head = path.read_text(encoding="utf-8", errors="replace")[:BANNER_WINDOW]
    return any(banner in head for banner in BANNERS)


def paragraphs(text: str) -> list[tuple[int, str]]:
    """Split into blank-line-separated blocks, each with its first line number."""
    blocks: list[tuple[int, str]] = []
    start = 1
    buffer: list[str] = []
    for number, line in enumerate(text.splitlines(), 1):
        if line.strip():
            if not buffer:
                start = number
            buffer.append(line)
        elif buffer:
            blocks.append((start, "\n".join(buffer)))
            buffer = []
    if buffer:
        blocks.append((start, "\n".join(buffer)))
    return blocks


def scan(paths: Iterable[Path]) -> list[tuple[Removed, Path, int, str]]:
    findings: list[tuple[Removed, Path, int, str]] = []
    for entry in REMOVED:
        matcher = re.compile(entry.pattern)
        allowed = REMOVAL_WORDS + entry.allow
        for path in paths:
            text = path.read_text(encoding="utf-8", errors="replace")
            for start, block in paragraphs(text):
                match = matcher.search(block)
                if not match:
                    continue
                # Emphasis splits a phrase mid-way ("is **not** shipped"), and a
                # wrapped line splits it across a newline. Flatten both before
                # looking for the words that say this is a removal notice.
                prose = re.sub(r"[*_`]+", "", block).replace("\n", " ")
                if any(token in prose for token in allowed):
                    continue
                offset = block[: match.start()].count("\n")
                line = block.splitlines()[offset].strip()
                findings.append((entry, path, start + offset, line))
    return findings


def main(argv: list[str]) -> int:
    quiet = "--quiet" in argv
    # The docs carry emoji and en dashes; a cp1252 console dies on them mid-report.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    every = published_files()
    paths = [p for p in every if not is_historical(p)]
    findings = scan(paths)

    if not quiet:
        print(
            f"Scanned {len(paths)} published files "
            f"({len(every) - len(paths)} exempt, bannered)."
        )
        if not findings:
            print("No published doc claims a removed feature is live.")
        current = None
        for entry, path, number, line in findings:
            if entry is not current:
                current = entry
                print(f"\n== {entry.what}  (removed {entry.when})")
            print(f"   {path.relative_to(REPO).as_posix()}:{number}")
            print(f"       {line[:110]}")
        if findings:
            print(
                f"\n{len(findings)} line(s) to check. Each is either a doc to fix "
                "or an `allow` token to add in this file."
            )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
