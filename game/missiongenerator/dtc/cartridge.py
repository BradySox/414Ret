"""Native DCS DTC cartridge model + the two pydcs seams (§74).

DCS's native Data Transfer Cartridge system (FA-18C + F-16C today) is two
pieces inside an ordinary miz, both confirmed against a working MP mission and
the ME's own DTC editor (``CoreMods/aircraft/<type>/DTC/`` +
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

pydcs knows nothing of either piece, so this module owns the two seams:

* :func:`install_flying_unit_dtc_serialization` wraps ``FlyingUnit.dict`` once
  to emit the ``DTC`` key for units carrying :data:`DTC_UNIT_ATTR` (set via
  :func:`attach_cartridge_to_unit`). A no-op for every other unit, so mission
  output is byte-identical when the feature is off.
* :func:`append_cartridges_to_miz` appends the ``DTC/*.dtc`` entries to the
  already-saved miz (plain zip append -- no ``Mission.save`` patch needed).

The clean first-class version of these seams is queued for dcs-retribution/pydcs;
when that lands and the pin moves, this module shrinks to the model + builders.
"""

from __future__ import annotations

import json
import logging
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from dcs.flyingunit import FlyingUnit

#: Attribute stashed on a pydcs FlyingUnit holding its complete ``DTC`` block
#: (the ``{"Cartridges": [...], "AutoLoad": ...}`` dict serialized verbatim).
DTC_UNIT_ATTR = "retribution_dtc"


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


_original_flying_unit_dict: Callable[[FlyingUnit], dict[str, Any]] | None = None


def install_flying_unit_dtc_serialization() -> None:
    """Teach ``FlyingUnit.dict`` to emit the ``DTC`` unit block. Idempotent.

    Only units explicitly given :data:`DTC_UNIT_ATTR` are affected; everything
    else serializes byte-identically, so installing the patch is safe even for
    missions that carry no cartridges.
    """
    global _original_flying_unit_dict
    if _original_flying_unit_dict is not None:
        return

    original = FlyingUnit.dict

    def dict_with_dtc(self: FlyingUnit) -> dict[str, Any]:
        d = original(self)
        dtc = getattr(self, DTC_UNIT_ATTR, None)
        if dtc:
            d["DTC"] = dtc
        return d

    _original_flying_unit_dict = original
    FlyingUnit.dict = dict_with_dtc  # type: ignore[method-assign]


def attach_cartridge_to_unit(unit: FlyingUnit, cartridge_name: str) -> None:
    """Bind a cartridge to a unit (default + AutoLoad), installing the seam."""
    install_flying_unit_dtc_serialization()
    setattr(
        unit,
        DTC_UNIT_ATTR,
        {
            "Cartridges": [{"default": True, "name": cartridge_name}],
            "AutoLoad": True,
        },
    )


def append_cartridges_to_miz(
    miz_path: Path, cartridges: Sequence[DtcCartridge]
) -> None:
    """Append the ``DTC/*.dtc`` JSON entries to an already-saved miz."""
    if not cartridges:
        return
    with zipfile.ZipFile(miz_path, "a", compression=zipfile.ZIP_DEFLATED) as zf:
        existing = set(zf.namelist())
        for cartridge in cartridges:
            if cartridge.archive_path in existing:
                logging.warning(
                    "DTC: %s already present in %s; skipping",
                    cartridge.archive_path,
                    miz_path,
                )
                continue
            zf.writestr(cartridge.archive_path, cartridge.to_json())
