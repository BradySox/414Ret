from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional, TYPE_CHECKING

from game.settings.settings import FEATURES_PAGE

if TYPE_CHECKING:
    from game.settings.settings import Settings

# The 414th planner-suite gates and their two states. Since the 2026-08-09
# re-convergence decision (see docs/dev/design/
# 414th-autoplanner-upstream-divergence-audit.md, DECIDED block) the Settings
# defaults are the STOCK values -- a new game plans like upstream -- and this
# preset is the one-click opt back into the 414th planner features per campaign.
#
# CSAR is deliberately absent: it is upstream dcs-retribution#929's own design
# and ships with #929's defaults either way. Route-aware fuel tanks (§46) left
# the suite when work order C reverted the feature outright -- there is no gate
# to flip any more.
#
#: The settings page the one-click bar is prepended to. It lives beside the values
#: rather than in the dialog because a page name nothing resolves to renders no bar
#: at all, silently -- which is how this one shipped invisible. Pinned by a test.
PLANNER_SUITE_PAGE = FEATURES_PAGE

# field -> (stock value, suite value)
PLANNER_SUITE_VALUES: dict[str, tuple[Any, Any]] = {
    "barcap_overlap_time": (timedelta(minutes=0), timedelta(minutes=15)),
    "single_sead_escort_flavour": (False, True),
    "auto_add_tarps_recon": (False, True),
    "weather_aware_planning": (False, True),
    "max_escort_jammers": (0, 4),
    "adaptive_procurement": (False, True),
    "continuous_campaign_clock": (False, True),
}


def apply_planner_suite(settings: Settings, suite_on: bool) -> None:
    """Set every suite gate to its 414th (``True``) or stock (``False``) value.

    Only the fields in ``PLANNER_SUITE_VALUES`` are touched; each can still be
    hand-tuned afterward.
    """
    index = 1 if suite_on else 0
    for name, values in PLANNER_SUITE_VALUES.items():
        setattr(settings, name, values[index])


def detect_planner_suite(settings: Settings) -> Optional[bool]:
    """``True`` if every gate is at its suite value, ``False`` if every gate is
    stock, ``None`` for a hand-tuned mix."""
    for suite_on in (True, False):
        index = 1 if suite_on else 0
        if all(
            getattr(settings, name) == values[index]
            for name, values in PLANNER_SUITE_VALUES.items()
        ):
            return suite_on
    return None
