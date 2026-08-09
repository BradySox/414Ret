"""Every ``unit_types`` string in a layout must resolve to a real unit.

``GroupLayoutMapping.from_dict`` resolves each name with ``unit_type_from_name`` and
**silently skips** anything that returns None (``game/layout/layoutmapping.py``). So a
renamed unit id does not raise, does not log, and does not fail CI -- the slot's type
list just comes back shorter. When that empties a mandatory group,
``TgoLayoutGroup.possible_types_for_faction`` raises ``LayoutException`` and
``ArmedForces._load_forces`` swallows the whole preset group, so the site silently
stops generating for every faction that fields it.

That is not hypothetical. The CurrentHill 1.5.0 id migration renamed the Swedish pack
to ``CH_``-prefixed ids but never re-pointed the four LvS-103 layouts, so every
LvS-103 SAM site was unbuildable -- including the only nation-specific long-range SAM
Sweden 2020 has. The Sky Sabre battery had the same class of bug from a different
cause: its launcher slot named the pydcs *class* (``CH_SkySabreLN``) instead of the
unit *id* (``CH_SkySabre``), and only avoided going dark because that slot also
carries a ``Launcher`` class fallback -- so it generated the wrong launcher instead.
Both were found by the 2026-08-08 whole-repo audit, months after the migration.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# game.dcs.helpers must be imported BEFORE pydcs_extensions: game.persistency imports
# names from pydcs_extensions at module scope, so importing the package first leaves it
# partially initialized and the import fails.
from game.dcs.helpers import unit_type_from_name
import pydcs_extensions  # noqa: E402,F401  registers every mod pack into the pydcs maps

LAYOUT_DIR = Path("resources/layouts")

#: Names that do not resolve and are deliberately left alone, with the reason.
#: Keep this list SHORT and justified -- it is the escape hatch that lets the rest of
#: the sweep stay strict.
KNOWN_UNRESOLVABLE: dict[str, str] = {
    # Upstream-authored and byte-identical to upstream/dev. It is one of a three-way
    # choice (ara_vdm / Essex / cva-31) and the other two resolve, so the slot still
    # fills. Editing it would only manufacture a merge conflict on every sync.
    "cva-31": "upstream's, byte-identical, and the slot has two resolving alternatives",
    # Fork-authored FOB decor naming statics that are registered nowhere. Every group
    # in vietnam_fob.yaml is optional:true, so the decorations are simply absent and
    # nothing breaks. Left as-is rather than deleted: removing a dead entry from a
    # group that also lists unit_classes would let the class fallback fire and START
    # generating something, which is a behaviour change, not a fix.
    "CV_59_H60": "vietnam_fob decor, optional group, no behaviour to restore",
    "CV_59_Large_Forklift": "vietnam_fob decor, optional group",
    "ERO_Container": "vietnam_fob decor, optional group",
    "ERO_ZU23_pos": "vietnam_fob decor, optional group",
    "Invisible FARP": "vietnam_fob decor, optional group",
}


def _unit_type_strings() -> list[tuple[Path, str]]:
    """(layout file, name) for every ``unit_types`` entry under resources/layouts."""
    found: list[tuple[Path, str]] = []

    def walk(node: object, path: Path) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "unit_types" and isinstance(value, list):
                    found.extend(
                        (path, name) for name in value if isinstance(name, str)
                    )
                else:
                    walk(value, path)
        elif isinstance(node, list):
            for item in node:
                walk(item, path)

    for file in sorted(LAYOUT_DIR.rglob("*.yaml")):
        walk(yaml.safe_load(file.read_text(encoding="utf-8")), file)
    return found


def test_the_sweep_actually_finds_layouts() -> None:
    # Guards the guard: a wrong cwd or a moved directory would make every assertion
    # below vacuously pass.
    entries = _unit_type_strings()
    assert len(entries) > 400, f"only {len(entries)} unit_types strings -- wrong cwd?"


def test_every_layout_unit_type_resolves() -> None:
    unresolved = [
        f"{path.as_posix()}: {name!r}"
        for path, name in _unit_type_strings()
        if name not in KNOWN_UNRESOLVABLE and unit_type_from_name(name) is None
    ]
    assert not unresolved, (
        "these layout unit_types resolve to None and are silently dropped, which can "
        "make the whole site unbuildable -- check for a renamed mod id, or that the "
        "string is the unit ID and not the pydcs class name:\n" + "\n".join(unresolved)
    )


@pytest.mark.parametrize("name", sorted(KNOWN_UNRESOLVABLE))
def test_known_unresolvable_entries_are_still_unresolvable(name: str) -> None:
    # If one of these starts resolving (a mod pack registers it, or upstream fixes
    # cva-31), drop it from the allowlist rather than leaving a stale exemption that
    # would hide a real regression on the same name.
    assert unit_type_from_name(name) is None, (
        f"{name!r} now resolves -- remove it from KNOWN_UNRESOLVABLE so the sweep "
        "covers it again"
    )


def test_the_lvs_103_layouts_name_ch_prefixed_ids() -> None:
    """Regression lock for the CurrentHill 1.5.0 id migration.

    Pinned by name rather than left to the general sweep because these four are the
    ones that actually went dark, and the failure mode (a whole preset group vanishing
    from every faction) is invisible without this.
    """
    for file in sorted(LAYOUT_DIR.glob("anti_air/LvS-103*.yaml")):
        names = [name for _, name in _unit_type_strings() if _ == file]
        assert names, f"{file.name} declares no unit_types"
        for name in names:
            assert name.startswith("CH_LvS-103_"), (
                f"{file.name} names {name!r}; the Swedish pack's ids have been "
                "CH_-prefixed since CurrentHill 1.5.0"
            )
