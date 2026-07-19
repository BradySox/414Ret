"""Native DCS DTC cartridge pre-population (§74).

See :mod:`game.missiongenerator.dtc.cartridge` for the format contract and
:mod:`game.missiongenerator.dtc.generator` for the generation pass.
"""

from game.missiongenerator.dtc.cartridge import DtcCartridge
from game.missiongenerator.dtc.generator import CARTRIDGE_BUILDERS, DtcGenerator

__all__ = ["CARTRIDGE_BUILDERS", "DtcCartridge", "DtcGenerator"]
