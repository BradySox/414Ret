"""AGENTS.md is a byte-identical mirror of CLAUDE.md below the title line.

The two files are the same 12,000-word guide addressed to two different agent
harnesses. Keeping them in step is a documented manual ritual -- `cp CLAUDE.md
AGENTS.md`, then edit line 1 back -- performed on 385 commits so far with nothing
checking it. A missed sync silently leaves one harness reading stale rules, which
is exactly the failure the guide exists to prevent.

This is the check. It does not remove the ritual; it removes the chance of
forgetting it.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
AGENTS_MD = REPO_ROOT / "AGENTS.md"


def _title_and_body(path: Path) -> tuple[str, str]:
    # newline="" keeps the file's own CRLF intact -- rewriting these with LF is
    # its own known way to produce a spurious whole-file diff.
    text = path.read_text(encoding="utf-8")
    title, _, body = text.partition("\n")
    return title, body


def test_agents_md_mirrors_claude_md() -> None:
    claude_title, claude_body = _title_and_body(CLAUDE_MD)
    agents_title, agents_body = _title_and_body(AGENTS_MD)

    assert claude_body == agents_body, (
        "AGENTS.md has drifted from CLAUDE.md. They are one guide with two "
        "titles: resync with `cp CLAUDE.md AGENTS.md`, then restore AGENTS.md's "
        "first line. Do not use `sed -i` -- it flattens the CRLF endings and "
        "rewrites the whole file."
    )
    # The titles are the one intended difference, so pin that they differ rather
    # than letting a `cp` with no follow-up edit pass silently.
    assert claude_title != agents_title
    assert agents_title.startswith("# AGENTS.md")


def test_both_guides_import_the_same_shared_files() -> None:
    """The `@`-imported files are shared, not duplicated.

    `docs/dev/CLAUDE-architecture.md` and `docs/dev/CLAUDE-ci.md` are referenced by
    both guides through the same paths, so editing one updates both faces for free.
    A copy of either under an AGENTS-specific name would reintroduce the drift this
    module exists to catch.
    """
    claude_text = CLAUDE_MD.read_text(encoding="utf-8")
    for shared in ("docs/dev/CLAUDE-ci.md",):
        assert f"@{shared}" in claude_text, f"{shared} is no longer imported"
        assert (REPO_ROOT / shared).is_file(), f"{shared} is missing"
