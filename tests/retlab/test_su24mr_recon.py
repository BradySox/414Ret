"""The Su-24MR must resolve a real recon fit for TARPS, not a clean airframe.

Sibling of test_su24mu_loadouts.py. The recon Fencer shipped with no payload
file at all, so a TARPS-tasked flight fell through every candidate loadout name
-- including the BARCAP fallback -- and ``default_for_task_and_aircraft``
returned ``empty_loadout()``: no Shpil-2, no ETHER, no self-defence missiles.
The failure is silent, which is what this guards.
"""

import re
from pathlib import Path

import pytest
from dcs.payloads import PayloadDirectories
from dcs.planes import Su_24MR
from dcs.unittype import FlyingType

from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout

PAYLOADS_DIR = Path(__file__).parents[2] / "resources" / "customized_payloads"

# The fit is a verbatim splice of the DCS-shipped "SHPIL,ETHER,R-60M*2,Fuel*2".
SHPIL_RECON_POD = "{0519A263-0AB6-11d6-9193-00A0249B6F00}"
ETHER_ELINT_POD = "{0519A261-0AB6-11d6-9193-00A0249B6F00}"


@pytest.fixture(autouse=True)
def payload_dirs() -> None:
    PayloadDirectories.set_fallback(PAYLOADS_DIR)
    FlyingType._payload_cache = None  # type: ignore[assignment]


def test_payload_file_binds_to_the_pydcs_id() -> None:
    # pydcs keys payload files by the unitType FIELD, not the filename.
    text = (PAYLOADS_DIR / "Su-24MR.lua").read_text()
    match = re.search(r'\["unitType"\]\s*=\s*"([^"]*)"', text)
    assert match is not None
    assert match.group(1) == Su_24MR.id == "Su-24MR"


def test_tarps_resolves_the_recon_fit() -> None:
    loadout = Loadout.default_for_task_and_aircraft(FlightType.TARPS, Su_24MR)
    assert loadout.name == "Retribution TARPS"
    clsids = {weapon.clsid for weapon in loadout.pylons.values() if weapon}
    # Both sensor pods, or the jet is flying a recon sortie blind.
    assert SHPIL_RECON_POD in clsids
    assert ETHER_ELINT_POD in clsids


def test_we_add_one_preset_and_redefine_none() -> None:
    # pydcs merges payload files by name and the first directory wins, so a file
    # reusing a stock name would replace that fit in the payload editor. Assert
    # on our own file rather than on the merged result: the shipped fits come
    # from the DCS install, which CI does not have.
    text = (PAYLOADS_DIR / "Su-24MR.lua").read_text()
    names = set(re.findall(r'\["name"\]\s*=\s*"([^"]*)"', text))
    # ["name"] also appears once at file scope, holding the unit id.
    assert names == {"Su-24MR", "Retribution TARPS"}
