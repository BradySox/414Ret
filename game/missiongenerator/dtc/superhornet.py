"""CJS Super Hornet DTC cartridge builder -- FA-18E/F + EA-18G (§74).

The community CJS Super Hornet mod ships **native DTC descriptors** of its own
(``<mod>/DTC/{FA-18E,FA-18F,EA-18G}_DTC.lua``), so these airframes take a
cartridge exactly like the stock Hornet does. Those descriptors are thin
wrappers: they ``dofile`` ED's *own* FA-18C implementations for every section
they expose --

    CoreMods/aircraft/FA-18C/DTC/COMM/{COMM_common,COMM1,COMM2}.lua
    CoreMods/aircraft/FA-18C/DTC/WYPT/{WYPT_NAV,ROUTE_SEQ,NAV_SETTINGS}.lua
    CoreMods/aircraft/FA-18C/DTC/ALR67/{CMDS,RWR}.lua
    CoreMods/aircraft/FA-18C/DTC/TCN/TACAN.lua

-- which is why the Hornet builder's COMM/WYPT emit is reused verbatim here
instead of being reimplemented: the schema is ED's, not CJS's.

**No ``SA`` section.** Unlike ED's FA-18C descriptor, the CJS ``data`` table
declares only ``ALR67``/``COMM``/``WYPT``/``TCN`` -- no ``SA`` table, no
``GPS_WYPT``. Confirmed four ways: the ``data`` table is complete as written;
``SA`` occurs **0** times across all three CJS descriptors + their ``defs.lua``
against **205** in ED's (``CAP_PTS`` 0/43, ``MEZ_THRTS`` 0/49, ``FAOR_FLOT``
0/42); the CJS panel list is five (``pWYPT``/``pRTE_SEQ``/``pTACAN``/``pCOMM``/
``pALR67``) against ED's eight, which adds ``pSA``/``pGPS_WYPT``/``pHARM``; and
the ``.dlg`` retains a hollow ``pSA`` stub -- one reference (ED: 196) holding a
lone static label ``"Panel SA"``. CJS forked an ED descriptor and stripped SA
out, leaving the shell.

So these jets get the comm plan, steerpoints/route and recovery aids, but
**not** the SA picture: no FLOT, no CAP/tanker racetracks, and no enemy threat
rings. The planner's SA-section switches are simply inert for them rather than
emitting a table the module cannot read.

If a CJS release ever fills that ``pSA`` shell in and adds the ``SA`` table,
flipping ``with_sa=True`` below lights up the whole picture with no other
change -- re-check the descriptor after a mod update.

Drift warning: this builds against a *mod* descriptor, not ED's. A CJS release
can change or extend the schema (adding ``SA`` would be the welcome case) --
``tests/missiongenerator/test_dtc.py`` pins what we rely on, but the installed
mod is the source of truth. The same staleness that broke the mod's cockpit
scripts applies here.

The tanker variants (``FA-18ET``/``FA-18FT``) are deliberately absent: the mod
ships no DTC descriptor for them, so a cartridge would have nothing to load it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from game.missiongenerator.dtc.cartridge import DtcCartridge
from game.missiongenerator.dtc.hornet import (
    CARTRIDGE_SECTIONS,
    build_hornet_family_cartridge,
)

if TYPE_CHECKING:
    from game import Game
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.missiondata import MissionData

#: DCS unit type ids of the CJS airframes carrying a DTC descriptor.
SUPER_HORNET_UNIT_TYPES = ("FA-18E", "FA-18F", "EA-18G")


def build_super_hornet_cartridge(
    flight: FlightData, mission_data: MissionData, game: Game, name: str
) -> Optional[DtcCartridge]:
    """Build the cartridge, or ``None`` if nothing this jet supports is on.

    The generator's ``any_content`` gate passes a flight with *only* the SA
    sections enabled -- for a Super Hornet that yields no sections at all, and
    an empty cartridge is worse than none (it would AutoLoad and carry
    nothing), so signal the generator to skip it.
    """
    cartridge = build_hornet_family_cartridge(
        flight,
        mission_data,
        game,
        name,
        flight.aircraft_type.dcs_unit_type.id,
        with_sa=False,
    )
    if not any(section in cartridge.data for section in CARTRIDGE_SECTIONS):
        return None
    return cartridge
