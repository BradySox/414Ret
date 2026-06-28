"""Regression guard for the cut-mod faction/campaign modernization.

The 414th ships a trimmed mod set; #267 swapped cut-mod aircraft out of the
campaigns and the 2026-06-28 pass did the same for the faction JSONs. The faction
loader **silently drops** an unresolved/cut aircraft (see
``test_unknown_aircraft_name_skipped_not_whole_faction``), so re-introducing one
is invisible at runtime -- this test is the tripwire that keeps it from getting
re-clobbered.

If you intentionally re-add one of these, you must also re-ship its mod and
remove it from ``CUT_MOD_AIRCRAFT`` here (with a note why).
"""

from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_FACTIONS = _REPO / "resources" / "factions"
_CAMPAIGNS = _REPO / "resources" / "campaigns"

# Cut-mod aircraft replaced by in-game / kept-mod equivalents. Intentional
# mod-with-fallback designs (e.g. the Swedish JAS-39 + AJS37 Viggen fallback) are
# deliberately NOT listed -- those mods stay optional.
CUT_MOD_AIRCRAFT = [
    "UH-60L",  # -> UH-60A
    "KC-130J",  # -> KC-135 Stratotanker
    # F-111C Aardvark un-cut 2026-06-28: re-introduced for the Vietnam campaigns
    # (Combat Lancer, 1968). The mod is shipped and the USA Vietnam factions now
    # reference it with f111c:true, so it must NOT be guarded as a cut mod.
    "[CH] B-21",  # -> B-1B Lancer
    "[CH] MiG-29MU2",  # -> MiG-29S Fulcrum-C
    "[CH] Su-24MU",  # -> Su-24M Fencer-D
    "[CH] Su-27P1M",  # -> Su-27 Flanker-B
]


def _content_files() -> list[Path]:
    return sorted(_FACTIONS.glob("*.json")) + sorted(_CAMPAIGNS.glob("*.yaml"))


@pytest.mark.parametrize("aircraft", CUT_MOD_AIRCRAFT)
def test_cut_mod_aircraft_not_referenced(aircraft: str) -> None:
    # Match the name only as a quoted token (how factions/campaigns reference an
    # aircraft) so prose in a briefing can never trip the guard.
    needles = (f'"{aircraft}"', f"'{aircraft}'")
    offenders = [
        fp.relative_to(_REPO).as_posix()
        for fp in _content_files()
        if any(n in fp.read_text(encoding="utf-8") for n in needles)
    ]
    assert not offenders, (
        f"Cut-mod aircraft {aircraft!r} was re-introduced in: {offenders}. "
        "Either swap it for an in-game/kept-mod equivalent, or (if the mod is "
        "being re-shipped) drop it from CUT_MOD_AIRCRAFT with a note."
    )
