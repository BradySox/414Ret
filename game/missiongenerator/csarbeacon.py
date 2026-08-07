"""The briefed survivor ADF beacon channel for Combat SAR.

MOOSE ``Ops.CSAR`` gives every downed pilot a homing beacon. It is a looped
``trigger.action.radioTransmission`` from the survivor's position
(``Moose.lua`` ``CSAR:_AddBeaconToGroup``), in the NDB band, which is the band the
rescue fleet's ADF sets actually receive:

===============  =========================  ====================
Airframe         ADF set                    Band
===============  =========================  ====================
C-130J-30        2x ADF-462                 NDB (manual p150)
UH-1H            ARN-83                     190-1750 kHz
Mi-8MT           ARK-9                      150-1290 kHz
===============  =========================  ====================

Out of the box MOOSE picks a **random** channel per survivor from a large pool,
which cannot be briefed: the kneeboard is rendered before the mission runs, and the
crew would have to wait for the MAYDAY call to learn where to tune. So the fork pins
one channel for the whole mission and briefs it. Everybody dials it in before start
and homes the survivor directly.

There is no relay. An earlier design had the King re-transmit as TACAN, which does not
work in either direction: the C-130J's AN/ARN-153 is receive-only against ground
stations (manual p150, and the CNI-MU ``TR-REC`` control is the DME interrogation, not
a beacon), and neither flyable rescue helo carries TACAN at all. Since all three
airframes hear the NDB band, the relay was never needed.
"""

from __future__ import annotations

#: The pinned SAR beacon channel, in kHz.
#:
#: Chosen to sit inside MOOSE's own beacon band (200-999 kHz, 10 kHz grid, see
#: ``UTILS.GenerateVHFrequencies``) while avoiding every entry on that function's
#: navaid skip list, so it can never sit on top of a real theater NDB or VOR. 310
#: and 320 kHz are the obvious round numbers and BOTH are skip-listed; 260 is clear.
#:
#: To change it, keep it on the 10 kHz grid, inside 200-999, and off the skip list.
#: ``tests/missiongenerator/test_csarbeacon.py`` enforces all three.
SAR_BEACON_KHZ = 260

#: The band MOOSE allocates beacons from, for validation and for the doc line.
BEACON_BAND_KHZ = (200, 999)

#: The tuning grid inside that band.
BEACON_GRID_KHZ = 10


def sar_beacon_hz() -> int:
    """The pinned beacon channel in Hz, the unit DCS's radio API takes."""
    return SAR_BEACON_KHZ * 1000


def sar_beacon_brief() -> str:
    """The one-line kneeboard/briefing form of the channel."""
    return f"{SAR_BEACON_KHZ} kHz ADF"
