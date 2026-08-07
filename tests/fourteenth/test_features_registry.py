"""The 414th feature registry must stay honest.

These tests turn registry drift into a CI failure: a renamed Settings field, a
removed plugin, a feature added to (or dropped from) the CLAUDE.md feature list
without the registry, an in-game-pass checklist row pointing at an unregistered
feature, or a stale generated catalog all go red here instead of silently rotting
a doc.
"""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path

from game.fourteenth.features import (
    FEATURE_INDEX_DOC,
    FEATURES,
    render_feature_index,
)
from game.settings.settings import Settings

CLAUDE_MD = Path("CLAUDE.md")
CHECKLIST = Path("docs/dev/414th-ingame-pass-checklist.md")
FEATURES_DOC = Path("docs/dev/414th-features.md")


def _settings_field_names() -> set[str]:
    return {field.name for field in dataclasses.fields(Settings)}


def _plugin_ids() -> set[str]:
    return set(json.loads(Path("resources/plugins/plugins.json").read_text()))


def _registry_sections() -> set[int]:
    return {f.doc_section for f in FEATURES if f.doc_section is not None}


def _features_at_a_glance_sections() -> set[int]:
    """Section numbers in the CLAUDE.md 'Features at a Glance' section.

    Live features are a numbered list (``12. **Recon engine** — ...``); retired and
    removed ones are a table (``| 40 | Campaign phases | Removed ... |``) so a dead
    feature does not sit inline between two live ones. Both count as listed — the
    invariant is that the registry and this section cover the same set, not how the
    section renders them.
    """
    text = CLAUDE_MD.read_text(encoding="utf-8")
    start = text.index("## Features at a Glance")
    rest = text[start + len("## Features at a Glance") :]
    end = re.search(r"\n## ", rest)
    section_text = rest[: end.start()] if end else rest
    live = {int(m.group(1)) for m in re.finditer(r"^(\d+)\. \*\*", section_text, re.M)}
    retired = {
        int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", section_text, re.M)
    }
    return live | retired


def _checklist_sections() -> set[int]:
    """Every `· §N ·` feature reference in the in-game-pass checklist rows."""
    text = CHECKLIST.read_text(encoding="utf-8")
    return {int(m.group(1)) for m in re.finditer(r"·\s*§(\d+)", text)}


def _claude_features_doc_pointers() -> set[int]:
    """Every "features doc §N" pointer in CLAUDE.md — the section it tells a reader
    to go read in 414th-features.md."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    return {int(m.group(1)) for m in re.finditer(r"features doc §(\d+)", text)}


def _features_doc_section_headings() -> set[int]:
    """Section numbers with an actual `## §N` or `## N.` heading in 414th-features.md."""
    text = FEATURES_DOC.read_text(encoding="utf-8")
    nums: set[int] = set()
    for m in re.finditer(r"^## (?:§(\d+)|(\d+)\.)", text, re.M):
        nums.add(int(m.group(1) or m.group(2)))
    return nums


def test_keys_are_unique() -> None:
    keys = [feature.key for feature in FEATURES]
    assert len(keys) == len(set(keys)), "duplicate Feature.key"


def test_settings_fields_exist() -> None:
    names = _settings_field_names()
    for feature in FEATURES:
        for field_name in feature.settings_fields:
            assert (
                field_name in names
            ), f"{feature.key}: '{field_name}' is not a Settings field"


def test_plugin_ids_exist() -> None:
    ids = _plugin_ids()
    for feature in FEATURES:
        if feature.plugin_id is not None:
            assert (
                feature.plugin_id in ids
            ), f"{feature.key}: '{feature.plugin_id}' is not a registered plugin"


def test_doc_sections_are_positive() -> None:
    for feature in FEATURES:
        if feature.doc_section is not None:
            assert feature.doc_section > 0, f"{feature.key}: bad doc_section"


def test_registry_covers_features_at_a_glance() -> None:
    # The registry must hold exactly the numbered features in the CLAUDE.md list:
    # adding a feature to the list (or the registry) without the other fails here.
    registry = _registry_sections()
    listed = _features_at_a_glance_sections()
    assert registry == listed, (
        f"registry vs CLAUDE.md 'Features at a Glance' mismatch — "
        f"only in registry: {sorted(registry - listed)}; "
        f"only in the list: {sorted(listed - registry)}"
    )


def test_checklist_sections_are_registered() -> None:
    # Every in-game-pass checklist row references a features-doc §N; each must be a
    # registered feature, so a checklist pointing at an unknown section fails CI.
    unregistered = _checklist_sections() - _registry_sections()
    assert not unregistered, (
        f"in-game-pass checklist references unregistered section(s): "
        f"{sorted(unregistered)}"
    )


def test_features_doc_pointers_resolve() -> None:
    # Every "features doc §N" pointer in CLAUDE.md must resolve to a real section
    # heading in 414th-features.md.
    pointers = _claude_features_doc_pointers()
    headings = _features_doc_section_headings()
    missing = sorted(pointers - headings)
    assert not missing, (
        "CLAUDE.md 'features doc §N' pointer(s) with no matching section heading in "
        f"docs/dev/414th-features.md: {missing}"
    )


# Features whose engineering detail deliberately lives under a differently-numbered
# heading in 414th-features.md, rather than one of their own. Keep this small: a new
# entry here should be a conscious "this shares a section", not a missing write-up.
SHARED_FEATURE_SECTIONS = {
    19: 18,  # unified map layers panel — features.md numbers it 18
    22: 4,  # kneeboard space-utilisation — folded into the kneeboard section
    25: 4,  # compact deck (retired) — same
}


def test_every_listed_feature_has_a_features_doc_section() -> None:
    # This closes the blind spot that let §35 (Convoy interdiction) ship registered +
    # listed + checklist-referenced but with NO engineering section written (found in
    # the 2026-07-01 docs-vs-code audit).
    #
    # It used to check only the "features doc §N" pointers CLAUDE.md happened to carry,
    # which covered a minority of features and went fully vacuous when the 2026-08-07
    # rewrite turned the feature list into a plain index. Checking the listed set
    # directly covers all of them and cannot be silently emptied.
    headings = _features_doc_section_headings()
    listed = _features_at_a_glance_sections()
    missing = sorted(
        n
        for n in listed
        if n not in headings and SHARED_FEATURE_SECTIONS.get(n) not in headings
    )
    assert not missing, (
        "feature(s) in the CLAUDE.md list with no section in "
        f"docs/dev/414th-features.md: {missing} — write the section, or add a "
        "SHARED_FEATURE_SECTIONS entry if it deliberately shares one"
    )


def test_generated_catalog_is_current() -> None:
    actual = Path(FEATURE_INDEX_DOC).read_text(encoding="utf-8")
    assert actual == render_feature_index(), (
        f"{FEATURE_INDEX_DOC} is stale; regenerate with "
        "`python -m game.fourteenth.features`"
    )
