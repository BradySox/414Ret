"""Native DCS DTC cartridge model (§74).

DCS's native Data Transfer Cartridge system (FA-18C + F-16C today) is two
pieces inside an ordinary miz, both confirmed against a working MP mission and
the ME's own DTC editor (``CoreMods/aircraft/<type>/DTC`` +
``MissionEditor/modules/me_managerDTC.lua``):

* one pretty-printed JSON file per cartridge at ``DTC/<name>.dtc`` in the miz
  zip root, shaped ``{"data": {...sections...}, "name": ..., "type": ...}``, and
* a per-unit mission block::

      ["DTC"] = {
          ["Cartridges"] = { [1] = { ["default"] = true, ["name"] = <name> } },
          ["AutoLoad"] = true,
      }

``AutoLoad`` is the whole point: the jet ingests the cartridge at spawn with no
pilot action, and because the cartridge travels inside the miz it distributes
to multiplayer clients with the mission download.

Both serialization seams are **first-class pydcs** since dcs-retribution/pydcs
gained native DTC support (PR #34, pinned in requirements.txt):
``FlyingUnit.add_dtc_cartridge`` emits the unit block and
``Mission.add_dtc_cartridge`` writes the ``DTC/*.dtc`` file at save (and both
round-trip through ``Mission.load_file``). This module keeps only the fork's
cartridge *model* — the JSON payload the builders fill.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DtcCartridge:
    """One built cartridge: the JSON payload plus its identity.

    ``name`` doubles as the file name inside the miz (``DTC/<name>.dtc``) and
    the string units reference, exactly like the ME's own manager -- keep it
    filesystem-safe (the generator builds names from callsigns, which are).
    """

    name: str
    unit_type: str
    terrain: str
    data: dict[str, Any]

    @property
    def archive_path(self) -> str:
        return f"DTC/{self.name}.dtc"

    def to_json(self) -> str:
        # The ME writes {data, name, type} at the top level; the descriptor's
        # own data table carries name/type/terrain again inside (the builders
        # fill those). 4-space pretty print matches the ME's output.
        payload = {"data": self.data, "name": self.name, "type": self.unit_type}
        return json.dumps(payload, indent=4)
