"""Red Tide forward-basing guards.

The red laydown pushes a modern MiG-29 regiment onto the Fulda front at Haina and
moves Haina's Mi-24/Mi-8 helo detachments back to **H FRG 20**, which is flipped
RED in ``red_tide.miz`` (its airport ``dynamicSpawn`` turned off + coalition set to
RED). Two fragile edits a future upstream sync or ``.miz`` re-save could silently
revert -- stranding the helos at a neutral field, or leaving the front without its
modern fighter -- so pin both the miz-side ownership and the yaml-side placement.
"""

from pathlib import Path

import yaml

from game import persistency
from game.campaignloader.campaign import Campaign

YAML = Path("resources/campaigns/red_tide.yaml")


def test_h_frg_20_loads_red(tmp_path: Path) -> None:
    persistency.setup(str(tmp_path), False, 0)
    campaign = Campaign.from_file(YAML)
    theater = campaign.load_theater(campaign.advanced_iads)
    hfrg = next(c for c in theater.controlpoints if c.name == "H FRG 20")
    assert hfrg.starting_coalition.is_red, (
        "H FRG 20 must load RED -- its airport dynamicSpawn/coalition in red_tide.miz "
        "was reverted (a dynamicSpawn field loads NEUTRAL). Re-flip it (dynamicSpawn "
        "off + set_red) or the forward helo detachments have no red field to base at."
    )


def _squadrons_by_cp() -> dict[int, list[str]]:
    data = yaml.safe_load(YAML.read_text())
    out: dict[int, list[str]] = {}
    for cp_id, sqns in data["squadrons"].items():
        out[int(cp_id)] = [s.get("aircraft_type", "") for s in sqns]
    return out


def test_forward_basing_squadron_placement() -> None:
    by_cp = _squadrons_by_cp()
    # H FRG 20 (143): the forward helo FOB.
    assert 143 in by_cp, "H FRG 20 (143) squadron block missing -- helos have no home."
    assert any("Mi-24" in a for a in by_cp[143])
    assert any("Mi-8" in a for a in by_cp[143])
    # Haina (161): a modern MiG-29 on the front, no helos.
    assert any("MiG-29" in a for a in by_cp[161])
    assert not any(a.startswith("Mi-") and "MiG" not in a for a in by_cp[161])
    # Kastrup (41): its MiG-29 moved up to Haina.
    assert not any("MiG-29" in a for a in by_cp.get(41, []))
