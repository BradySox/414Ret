"""Guard the authored scenery strike targets in every shipped campaign.

Scenery objectives are authored by hand in the Mission Editor (a blue circle carrying
the category, containing white zones bound to destructible map objects). The loader,
``SceneryGroup.from_trigger_zones``, is strict: a blue zone with no white zones inside,
or with a missing/misspelled category, raises ``SceneryGroupError`` and the **campaign
fails to load**. Nothing else in CI opens the campaign ``.miz`` files to check that.

That matters right now because the DCS 2.9.28 Iraq map added nine named dams which the
fork intends to author as ``power`` objectives across Desert Storm and Inherent Resolve
(design note ``414th-iraq-map-2928-notes.md``, checklist T4) -- hand-authoring exactly
the shape this test guards.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.check_scenery_targets import (  # noqa: E402
    campaign_mizes,
    check,
    valid_categories,
)


def test_tool_categories_match_the_game_source() -> None:
    # The tool reads NAME_BY_CATEGORY with ast to avoid importing the game package.
    # If that parse ever drifts from the real dict, every category check silently
    # becomes wrong -- so pin the two together.
    from game.theater.theatergroundobject import NAME_BY_CATEGORY

    assert valid_categories() == set(NAME_BY_CATEGORY)


@pytest.mark.parametrize("miz", list(campaign_mizes()), ids=lambda p: p.name)
def test_campaign_scenery_zones_load(miz: Path) -> None:
    # A malformed blue zone is not a cosmetic problem: it raises SceneryGroupError out
    # of the campaign loader, so New Game on that campaign dies.
    report = check(miz, valid_categories())
    assert not report.errors, "\n".join(report.errors)
