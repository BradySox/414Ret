"""The 414th feature registry — one self-describing entry per wired feature.

The fork carries ~30 features layered on upstream Retribution. Most of the
"how is this wired" knowledge (which Lua plugin runs it, which ``Settings``
toggle gates it, which features-doc section documents it) lives only in prose
that drifts as code changes. This module makes that wiring a *data structure*:

* Each feature with concrete wiring is a :class:`Feature` in :data:`FEATURES`.
* ``tests/fourteenth/test_features_registry.py`` asserts every reference resolves
  — a renamed ``Settings`` field or a removed plugin fails CI instead of quietly
  rotting a doc.
* :func:`render_feature_index` renders the registry to a committed Markdown table
  (``docs/dev/414th-feature-index.md``); a freshness test keeps it in lockstep.

Scope (v1): only features that have a plugin and/or a persisted ``Settings``
field are registered — those are the ones where wiring drift actually breaks
something. Pure-behavior features (UI polish, planner reworks with no toggle)
stay in the prose docs for now. Generating the full feature list from a richer
registry is the next increment.

Regenerate the doc after editing this file::

    python -m game.fourteenth.features
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Feature:
    """One 414th feature and its concrete wiring.

    ``key`` is a stable slug (never user-facing); ``title`` is the human name.
    ``doc_section`` is the §N in ``docs/dev/414th-features.md`` (None for
    features documented only in design notes, e.g. the engine plugins).
    ``plugin_id`` is a ``resources/plugins/<id>`` directory; ``settings_fields``
    are ``Settings`` dataclass field names that gate the feature.
    """

    key: str
    title: str
    doc_section: int | None = None
    plugin_id: str | None = None
    settings_fields: tuple[str, ...] = ()


# THE registry. Ordered by features-doc section, with the always-on engine
# plugins (no numbered section) last. Add an entry when a feature gains a plugin
# or a Settings toggle; the consistency test keeps the references honest.
FEATURES: tuple[Feature, ...] = (
    Feature(
        key="qra_intercept_reserve",
        title="QRA intercept reserve",
        doc_section=1,
        plugin_id="intercept",
    ),
    Feature(
        key="c130j_ew_isr",
        title="C-130J EW/ISR (JAMMING)",
        doc_section=2,
        plugin_id="c130j",
    ),
    Feature(
        key="tic",
        title="Troops In Contact",
        doc_section=9,
        plugin_id="tic",
    ),
    Feature(
        key="tars_recon",
        title="TARS recon engine",
        doc_section=12,
        plugin_id="tars",
    ),
    Feature(
        key="scar_rescue",
        title="SCAR — Sandy rescue escort",
        doc_section=15,
        plugin_id="scar",
        settings_fields=("scar_command_post_intel",),
    ),
    Feature(
        key="planner_unpredictability",
        title="Auto-planner target unpredictability",
        doc_section=17,
        settings_fields=(
            "ownfor_planner_unpredictability",
            "opfor_planner_unpredictability",
        ),
    ),
    Feature(
        key="drop_spawn_placement",
        title="Drop-spawn unit placement",
        doc_section=20,
        settings_fields=("enable_unit_placement", "enable_free_unit_placement"),
    ),
    Feature(
        key="combat_sar",
        title="Combat SAR",
        doc_section=21,
        plugin_id="combatsar",
        settings_fields=("auto_combat_sar",),
    ),
    Feature(
        key="date_gated_aircraft_properties",
        title="Date-gated aircraft properties",
        doc_section=24,
        settings_fields=("restrict_weapons_by_date",),
    ),
    Feature(
        key="compact_kneeboard",
        title="Compact kneeboard deck",
        doc_section=25,
        settings_fields=("compact_kneeboard",),
    ),
    Feature(
        key="sitrep_kneeboard",
        title="Campaign SITREP kneeboard",
        doc_section=29,
        settings_fields=("generate_sitrep_kneeboard",),
    ),
    Feature(
        key="mantis_iads",
        title="MANTIS IADS engine",
        plugin_id="mantisiads",
    ),
    Feature(
        key="splash_damage",
        title="Splash Damage (414th tuned)",
        plugin_id="splashdamage3",
    ),
)

# Path (relative to repo root) of the generated wiring-map doc.
FEATURE_INDEX_DOC = "docs/dev/414th-feature-index.md"


def render_feature_index() -> str:
    """Render :data:`FEATURES` to the Markdown wiring-map (a stable string)."""
    lines = [
        "# 414th Feature Wiring Map",
        "",
        "> **Generated** from `game/fourteenth/features.py` — do not edit by hand.",
        "> Regenerate with `python -m game.fourteenth.features`; CI fails if stale.",
        "",
        "Every 414th feature with concrete wiring (a Lua plugin and/or a `Settings`",
        "field) is registered in `FEATURES`. A test asserts each reference below",
        "resolves, so a renamed setting or removed plugin fails CI instead of",
        "silently rotting this map.",
        "",
        "| Feature | Features doc | Plugin | Settings |",
        "| --- | --- | --- | --- |",
    ]
    for feature in FEATURES:
        section = f"§{feature.doc_section}" if feature.doc_section is not None else "—"
        plugin = f"`{feature.plugin_id}`" if feature.plugin_id else "—"
        if feature.settings_fields:
            settings = ", ".join(f"`{name}`" for name in feature.settings_fields)
        else:
            settings = "—"
        lines.append(f"| {feature.title} | {section} | {plugin} | {settings} |")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    from pathlib import Path

    out = Path(FEATURE_INDEX_DOC)
    out.write_text(render_feature_index(), encoding="utf-8", newline="\n")
    print(f"wrote {out}")
