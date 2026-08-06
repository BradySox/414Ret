"""Guards for every campaign that authors a `victory:` block.

A victory condition names control points, ground objects and object categories
as *strings*. Nothing else validates them: `victory.py` deliberately treats a
name that matches nothing as "never met" rather than raising, so that a removed
campaign or a broken edit still plays with the stock endings instead of
crashing. That safety property means a typo -- or a laydown edit that renames a
FOB -- turns a campaign's win condition into a silent dud that no test, no log
line and no UI would ever surface.

These tests close that hole: for every shipped campaign with a `victory:` block,
the block must parse, and every name it references must resolve against the
campaign's own theater.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from game.campaignloader.campaign import Campaign
from game.fourteenth.victory import VictoryProfile, parse_victory

CAMPAIGN_DIR = Path("resources/campaigns")


def _campaigns_with_victory() -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(CAMPAIGN_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("victory") is not None:
            found.append((path.stem, data))
    return found


CAMPAIGNS = _campaigns_with_victory()
STEMS = [stem for stem, _ in CAMPAIGNS]


def test_some_campaign_authors_a_victory_block() -> None:
    """The suite below is vacuous if nothing authors one -- fail loudly instead.

    §75 shipped the mechanism and for a long time exactly zero campaigns used
    it, so "no campaign authors victory conditions" is a real regression shape,
    not a hypothetical.
    """
    assert STEMS, "no shipped campaign authors a victory: block"


@pytest.mark.parametrize("stem,data", CAMPAIGNS, ids=STEMS)
def test_victory_block_parses(stem: str, data: dict[str, Any]) -> None:
    profile = parse_victory(data["victory"])
    assert isinstance(profile, VictoryProfile)
    assert profile.win_when or profile.lose_when


@pytest.mark.parametrize("stem,data", CAMPAIGNS, ids=STEMS)
def test_every_named_control_point_exists(stem: str, data: dict[str, Any]) -> None:
    """capture_cps / lose_cps must name control points the theater actually has.

    A name that matches nothing is not an error at runtime -- it is simply never
    satisfied -- so an unreachable win condition would ship silently.
    """
    profile = parse_victory(data["victory"])
    assert profile is not None
    theater = Campaign.from_file(CAMPAIGN_DIR / f"{stem}.yaml").load_theater(
        advanced_iads=False
    )
    known = {cp.name for cp in theater.controlpoints}

    missing: list[str] = []
    for bucket in (profile.win_when, profile.lose_when):
        for condition in bucket:
            for name in (*condition.capture_cps, *condition.lose_cps):
                if name not in known:
                    missing.append(name)

    assert not missing, (
        f"{stem}: victory block names control points that do not exist: "
        f"{sorted(set(missing))}. Known: {sorted(known)}"
    )


@pytest.mark.parametrize("stem,data", CAMPAIGNS, ids=STEMS)
def test_capture_conditions_never_name_a_blue_control_point(
    stem: str, data: dict[str, Any]
) -> None:
    """`capture_cps` on a CP that starts blue is met on turn 0 -- a free win."""
    profile = parse_victory(data["victory"])
    assert profile is not None
    theater = Campaign.from_file(CAMPAIGN_DIR / f"{stem}.yaml").load_theater(
        advanced_iads=False
    )
    blue_at_start = {
        cp.name for cp in theater.controlpoints if cp.starting_coalition.name == "BLUE"
    }

    offenders = [
        name
        for condition in profile.win_when
        for name in condition.capture_cps
        if name in blue_at_start
    ]
    assert not offenders, (
        f"{stem}: capture_cps names control points that already start BLUE "
        f"{sorted(set(offenders))} -- the condition would be met immediately"
    )


@pytest.mark.parametrize("stem,data", CAMPAIGNS, ids=STEMS)
def test_lose_conditions_never_name_a_red_control_point(
    stem: str, data: dict[str, Any]
) -> None:
    """`lose_cps` on a CP that starts red is met on turn 0 -- an instant loss."""
    profile = parse_victory(data["victory"])
    assert profile is not None
    theater = Campaign.from_file(CAMPAIGN_DIR / f"{stem}.yaml").load_theater(
        advanced_iads=False
    )
    red_at_start = {
        cp.name for cp in theater.controlpoints if cp.starting_coalition.name == "RED"
    }

    offenders = [
        name
        for condition in profile.lose_when
        for name in condition.lose_cps
        if name in red_at_start
    ]
    assert not offenders, (
        f"{stem}: lose_cps names control points that already start RED "
        f"{sorted(set(offenders))} -- the campaign would be lost on turn 0"
    )


@pytest.mark.parametrize("stem,data", CAMPAIGNS, ids=STEMS)
def test_destroy_categories_have_something_to_destroy(
    stem: str, data: dict[str, Any]
) -> None:
    """A category with no authored markers can never be satisfied.

    `victory.py` guards against a *vacuous win* (an absent category would
    otherwise read as "all destroyed" on turn 0) by requiring a non-zero
    campaign-start baseline. The flip side is that authoring a category the
    campaign does not place makes the condition permanently unreachable -- so
    check the markers exist in the miz.
    """
    from dcs.mission import Mission

    from game.campaignloader.mizcampaignloader import MizCampaignLoader as Loader

    profile = parse_victory(data["victory"])
    assert profile is not None
    categories = {
        category
        for bucket in (profile.win_when, profile.lose_when)
        for condition in bucket
        for category in condition.destroy_categories
    }
    if not categories:
        pytest.skip("campaign authors no destroy_categories condition")

    marker_for = {"ammo": Loader.AMMUNITION_DEPOT_UNIT_TYPE}
    mission = Mission()
    mission.load_file(str(CAMPAIGN_DIR / data["miz"]))

    for category in categories:
        unit_type = marker_for.get(category)
        if unit_type is None:
            pytest.skip(f"no marker mapping known for category {category!r}")
        count = 0
        for block in (Loader.BLUE_COUNTRY.name, Loader.RED_COUNTRY.name):
            country = mission.country(block)
            if country is None:
                continue
            count += sum(
                1
                for group in country.static_group
                if group.units and group.units[0].type == unit_type
            )
        assert count > 0, (
            f"{stem}: destroy_categories names {category!r} but the miz places "
            f"no such marker -- the condition can never be met"
        )
