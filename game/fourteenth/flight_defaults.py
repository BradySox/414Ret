"""Per-aircraft "save as default" for the flight payload editor (414th, §43).

Retribution re-seeds a new flight's cockpit knobs -- internal fuel, aircraft
condition, wear & tear, spawn variant, and any other unit *properties* -- from the
pydcs engine defaults every time a flight is created. A player who always wants
(say) their F/A-18C to spawn hot with 80% fuel therefore has to redo it on every
package. This module gives those knobs the same persistence the payload dropdown
already has: a small JSON store keyed by DCS aircraft id, written from a button in
the payload tab and applied to each freshly-created BLUE flight.

The loadout has its own "Save Payload" mechanism (writes DCS ``UnitPayloads``) and
the player laser code has a campaign-wide setting; this covers the *rest* of that
box -- fuel and the property editor knobs.

Design notes:

* Storage is one JSON file under the Saved Games tree (never the save game, never
  the repo) -- :func:`game.persistency.flight_defaults_path`. It survives across
  campaigns, exactly like the ``UnitPayloads`` files the loadout button writes.
* Each entry is ``{"fuel": <kg>, "properties": {<prop id>: <scalar>}}`` -- plain
  JSON. ``properties`` carries whatever the user set in the property editor
  (condition/wear/spawn/HMD/ripple/...); an untouched knob simply isn't stored and
  falls back to the engine default.
* :func:`apply_flight_defaults` is called from ``Flight.__init__`` for genuinely
  fresh flights (``roster is None``, so it never clobbers a cloned roster's edits)
  on the player (BLUE) coalition only (so it never touches enemy AI). It is fully
  defensive: any failure -- persistency not set up (a headless test), a missing or
  malformed file, an airframe with no saved entry -- is a silent no-op.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Optional

from game.persistency import flight_defaults_path

if TYPE_CHECKING:
    from game.ato.flight import Flight

# A ``{aircraft_id: {"fuel": float, "properties": dict}}`` mapping, loaded once and
# then held in memory. ``None`` means "not yet loaded"; an empty dict is a valid
# loaded state (nothing saved, or persistency wasn't available). Kept in lockstep
# with the file by the writers below.
_cache: Optional[dict[str, Any]] = None


def _load() -> dict[str, Any]:
    """The store, loaded from disk on first use and cached thereafter."""
    global _cache
    if _cache is not None:
        return _cache
    data: dict[str, Any] = {}
    try:
        path = flight_defaults_path()
        if path.exists():
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
    except Exception:
        # No Saved Games folder (headless tests), unreadable/corrupt file, etc.
        # Defaults are a QOL convenience, never load-bearing -- degrade to "none".
        logging.debug("Could not load flight defaults store", exc_info=True)
    _cache = data
    return _cache


def _write(data: dict[str, Any]) -> None:
    global _cache
    try:
        path = flight_defaults_path()
        path.write_text(
            json.dumps(data, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
        )
    except OSError:
        # A locked/read-only store (OneDrive-synced Saved Games is a real case)
        # must not blow up the Qt click handler -- the default just isn't
        # persisted this session. Keep the in-memory cache so the button still
        # "works" until restart.
        logging.warning("Could not write flight defaults store", exc_info=True)
    _cache = data


def invalidate_cache() -> None:
    """Drop the in-memory cache so the next read re-loads from disk (tests)."""
    global _cache
    _cache = None


def has_defaults_for(aircraft_id: str) -> bool:
    """Whether a saved default exists for ``aircraft_id`` (drives the Clear button)."""
    return bool(_load().get(aircraft_id))


def save_defaults_for(
    aircraft_id: str, fuel: float, properties: dict[str, Any]
) -> None:
    """Persist ``fuel`` (kg) + ``properties`` as the default for ``aircraft_id``."""
    data = dict(_load())
    data[aircraft_id] = {"fuel": float(fuel), "properties": dict(properties)}
    _write(data)


def clear_defaults_for(aircraft_id: str) -> None:
    """Remove any saved default for ``aircraft_id`` (no-op if none exists)."""
    data = dict(_load())
    if aircraft_id in data:
        del data[aircraft_id]
        _write(data)


def apply_flight_defaults(flight: "Flight") -> None:
    """Seed a fresh BLUE flight's fuel + member properties from the saved default.

    Called from ``Flight.__init__`` (guarded to ``roster is None`` there).
    Everything is best-effort: a bad store, a missing entry, or an unexpected
    flight shape leaves the flight exactly as the engine built it.
    """
    try:
        if not flight.coalition.player.is_blue:
            return
        dcs_type = flight.unit_type.dcs_unit_type
        entry = _load().get(dcs_type.id)
        if not entry:
            return

        fuel = entry.get("fuel")
        if isinstance(fuel, (int, float)) and not isinstance(fuel, bool):
            flight.fuel = float(min(max(float(fuel), 0.0), float(dcs_type.fuel_max)))

        properties = entry.get("properties")
        if isinstance(properties, dict):
            for member in flight.roster.members:
                member.properties.update(properties)
    except Exception:
        logging.debug("Could not apply flight defaults", exc_info=True)
