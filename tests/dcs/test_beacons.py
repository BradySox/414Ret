"""Guard: a beacon with no frequency must not masquerade as one.

Every shipped terrain has beacons with ``hertz: null`` -- channel-addressed
TACANs and the Russian RSBN/PRMG systems, which carry no radio frequency at all
(1 on Marianas, 80 on Germany Cold War). ``Beacon.frequency`` used to wrap that
null in a ``RadioFrequency`` regardless, and the mission generator reserved the
result, so the radio registry held channels whose ``hertz`` was None. That sat
harmless for as long as nothing *read* it -- then the §70 red-net band guard
compared every allocated channel's hertz and generation died with

    TypeError: '<=' not supported between instances of 'int' and 'NoneType'

so the contract is now explicit: no frequency rather than a broken one.
"""

import json
from pathlib import Path

import pytest

from game.dcs.beacons import BEACONS_RESOURCE_PATH, Beacon, BeaconType

TERRAIN_BEACON_FILES = sorted(Path(BEACONS_RESOURCE_PATH).glob("*.json"))


def test_beacon_data_ships_with_the_repo() -> None:
    # If this ever finds nothing, the parametrized tests below silently pass.
    assert TERRAIN_BEACON_FILES


def test_frequency_is_none_when_the_beacon_has_no_hertz() -> None:
    beacon = Beacon(
        name="x",
        callsign="X",
        beacon_type=BeaconType.BEACON_TYPE_TACAN,
        hertz=None,
        channel=42,
    )
    assert beacon.frequency is None


def test_frequency_is_populated_when_the_beacon_has_hertz() -> None:
    beacon = Beacon(
        name="x",
        callsign="X",
        beacon_type=BeaconType.BEACON_TYPE_VOR,
        hertz=114_000_000,
        channel=None,
    )
    frequency = beacon.frequency
    assert frequency is not None
    assert frequency.hertz == 114_000_000


@pytest.mark.parametrize("path", TERRAIN_BEACON_FILES, ids=lambda p: Path(p).stem)
def test_no_shipped_beacon_yields_a_hertzless_frequency(path: Path) -> None:
    for beacon_id, data in json.loads(path.read_text(encoding="utf-8")).items():
        beacon = Beacon(
            name=data["name"],
            callsign=data["callsign"],
            beacon_type=BeaconType(data["beacon_type"]),
            hertz=data["hertz"],
            channel=data["channel"],
        )
        frequency = beacon.frequency
        assert frequency is None or frequency.hertz is not None, (
            f"{path.stem}:{beacon_id} ({beacon.callsign}) produced a "
            "RadioFrequency with no hertz"
        )
