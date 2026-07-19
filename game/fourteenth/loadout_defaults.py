"""Per-(airframe, task) default loadout override for the payload editor (414th, §73).

Retribution resolves a planned flight's loadout **by name**: ``Loadout.default_for``
walks ``default_loadout_names_for(task)`` and takes the first preset that exists for
the airframe (``Retribution CAS``, ``Liberation CAS``, the legacy names, ...). Those
presets ship in the repo's ``resources/customized_payloads``, which ``qt_ui.main``
registers as the *fallback* payload directory behind the user's own
``Saved Games/DCS/MissionEditor/UnitPayloads`` -- and pydcs takes the first directory
that supplies a given name. A user payload saved under the name a task resolves to
therefore silently *overrides* the shipped fit for every future flight.

That capability already existed; it was undiscoverable, because the Save Payload
dialog pre-fills ``Custom <task>`` -- a name nothing ever resolves -- so the obvious
action produced a preset the planner would never pick. This module makes it a
first-class operation: resolve the name the task actually lands on, write the loadout
there, and be able to take it back out again.

Design notes:

* The override is **global**, exactly like the ``UnitPayloads`` files it lives in: it
  is not part of a save game, it applies to both coalitions (an enemy flight of the
  same airframe and task resolves the same name), and it persists across campaigns
  until cleared. The Qt confirm dialog spells that out.
* :func:`override_name_for` returns the name that *currently wins* for the task rather
  than a hardcoded ``Retribution <task>``. That keeps it correct when a
  higher-priority candidate exists -- the §71 expanded-weapons ``(XW)`` fits sort
  ahead of the plain name -- so the override always lands in the slot the planner
  actually reads, and stays idempotent once written.
* Every write backs the file up first (into ``_retribution_backups``) and only ever
  touches the single named entry, so a hand-authored Mission Editor payload sitting in
  the same file survives.
* A file that exists but cannot be parsed is left completely alone. Rewriting it from
  scratch would silently destroy every other payload saved for that airframe.
"""

from __future__ import annotations

import logging
from pathlib import Path
from shutil import copyfile
from typing import Any, Optional, Type

from dcs import lua
from dcs.unittype import FlyingType

from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from game.persistency import payloads_dir


def override_name_for(task: FlightType, dcs_unit_type: Type[FlyingType]) -> str:
    """The payload name a flight of ``task`` in this airframe currently resolves to.

    This is the slot an override has to occupy to take effect. Normally it is the
    airframe's existing preset for the task; when the airframe has no preset at all
    the first non-expanded-weapons candidate is claimed instead, so saving still
    produces a loadout the planner will pick up.
    """
    dcs_unit_type.load_payloads()
    resolved = Loadout.default_for_task_and_aircraft(task, dcs_unit_type)
    if resolved.name and resolved.name != Loadout.empty_loadout().name:
        return resolved.name
    for name in Loadout.default_loadout_names_for(task):
        if not Loadout.is_expanded_weapons_name(name):
            return name
    # Unreachable in practice -- default_loadout_names_for always yields the plain
    # name -- but the caller needs a string, not an exception, from a UI handler.
    return f"Retribution {task.value}"


def user_payload_file(aircraft_id: str) -> Path:
    """The airframe's payload file in the user's (preferred) payload directory."""
    return payloads_dir() / f"{aircraft_id}.lua"


def _load_unit_payloads(path: Path) -> Optional[dict[str, Any]]:
    """The ``unitPayloads`` table from ``path``, or None if it cannot be read."""
    try:
        with path.open("r", encoding="utf-8") as payload_file:
            parsed = lua.loads(payload_file.read())
    except (OSError, SyntaxError, ValueError):
        logging.warning("Could not parse payload file %s", path, exc_info=True)
        return None
    if not parsed:
        return None
    payloads = parsed.get("unitPayloads")
    if not isinstance(payloads, dict) or not isinstance(payloads.get("payloads"), dict):
        return None
    return payloads


def _write_unit_payloads(path: Path, payloads: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as payload_file:
        payload_file.write("local unitPayloads = ")
        payload_file.write(lua.dumps(payloads, indent=1))
        payload_file.write("\nreturn unitPayloads")


def ensure_backup(aircraft_id: str) -> None:
    """Back the airframe's user payload file up once, before we first modify it."""
    payload_file = user_payload_file(aircraft_id)
    backup_file = payloads_dir(backup=True) / f"{aircraft_id}.lua"
    if backup_file.exists() or not payload_file.exists():
        return
    try:
        copyfile(payload_file, backup_file)
    except OSError:
        # A read-only/synced Saved Games tree must not abort the save; the write
        # below only ever replaces one named entry.
        logging.warning("Could not back up %s", payload_file, exc_info=True)


def _reload_payloads(dcs_unit_type: Type[FlyingType]) -> None:
    """Drop the airframe's parsed payloads so the next read comes off disk again."""
    dcs_unit_type.payloads = None
    dcs_unit_type.load_payloads()


def write_payload_entry(
    dcs_unit_type: Type[FlyingType], name: str, payload: dict[str, Any]
) -> bool:
    """Save ``payload`` under ``name`` in the airframe's user payload file.

    Replaces an existing same-named entry in place; otherwise appends. Returns False
    if the file exists but could not be parsed (in which case nothing was written --
    the other payloads in it are worth more than this one save).
    """
    aircraft_id = dcs_unit_type.id
    path = user_payload_file(aircraft_id)

    if dcs_unit_type.payloads is None:
        dcs_unit_type.load_payloads()
    if dcs_unit_type.payloads is not None:
        dcs_unit_type.payloads[name] = payload

    if not path.exists():
        _write_unit_payloads(
            path,
            {"name": aircraft_id, "payloads": {1: payload}, "unitType": aircraft_id},
        )
        dcs_unit_type.add_to_payload_cache(path)
        return True

    ensure_backup(aircraft_id)
    payloads = _load_unit_payloads(path)
    if payloads is None:
        return False
    entries = payloads["payloads"]
    key: Any = next(
        (k for k, entry in entries.items() if entry.get("name") == name),
        # Not len() + 1: a file whose keys start above 1 (or have had an entry
        # removed) would collide with a live entry and silently overwrite it.
        max((k for k in entries if isinstance(k, int)), default=len(entries)) + 1,
    )
    entries[key] = payload
    _write_unit_payloads(path, payloads)
    return True


def remove_payload_entry(dcs_unit_type: Type[FlyingType], name: str) -> bool:
    """Delete the ``name`` entry from the airframe's user payload file.

    Returns True if something was removed. The airframe's parsed payloads are then
    reloaded, so the repo's shipped preset of the same name takes over again.
    """
    aircraft_id = dcs_unit_type.id
    path = user_payload_file(aircraft_id)
    if not path.exists():
        return False
    payloads = _load_unit_payloads(path)
    if payloads is None:
        return False
    entries = payloads["payloads"]
    doomed = [k for k, entry in entries.items() if entry.get("name") == name]
    if not doomed:
        return False
    ensure_backup(aircraft_id)
    for key in doomed:
        del entries[key]
    _write_unit_payloads(path, payloads)
    _reload_payloads(dcs_unit_type)
    return True


def has_override_for(dcs_unit_type: Type[FlyingType], name: str) -> bool:
    """Whether the *user's* payload file supplies ``name`` (i.e. an override exists).

    Deliberately reads the file rather than the merged in-memory payloads, which
    cannot distinguish the user's entry from the repo's shipped one.

    Only ever reports state, so it degrades to "no override" on any failure -- it is
    read on every payload-tab build, including headless tests where the Saved Games
    tree was never set up.
    """
    try:
        path = user_payload_file(dcs_unit_type.id)
        if not path.exists():
            return False
        payloads = _load_unit_payloads(path)
        if payloads is None:
            return False
        return any(entry.get("name") == name for entry in payloads["payloads"].values())
    except Exception:
        logging.debug("Could not check for a loadout override", exc_info=True)
        return False
