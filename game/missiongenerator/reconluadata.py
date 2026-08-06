"""Recon -> BDA capture bridge (``dcsRetribution.Recon``).

One mechanism, both crews. This replaces the previous split where a player's
recon ran through MOOSE ``Ops.TARS`` (an F10 "film" menu, event-driven) while AI
recon ran through a geometric overflight check -- two unrelated implementations
answering one question ("what did we actually see this mission?"), which could not
agree by construction and failed differently.

The MOOSE path was cut on 2026-08-05. What it contributed to the campaign was a
unit *name* scraped off a ``Snapshot`` object whose schema was never confirmed --
``snap.name or snap.unitName or snap.UnitName`` sat under a comment saying the
one-time ``env.info`` dump existed "so the exact Snapshot schema can be confirmed
in-game". If none of those three fields was right, the player path recorded
nothing, silently, forever, while the AI path kept working. The geometric approach
needs no MOOSE, is testable headlessly, and is identical for both crews.

Recon is therefore **automatic on overfly** (DM call): fly the recon profile over
the target and it confirms. There is no film menu and no per-sortie film limit.

**What feeds it.** A TARPS-tasked flight of any airframe, and **any drone
regardless of task** -- the 414th "a drone is always filming" rule: a UAV is a
sensor first, so it banks BDA whether it is on a solo recon, riding a strike as
the JTAC, or working CAS. A manned combat jet only feeds it when actually tasked
TARPS. BLUE only: the AI opponent plans on ground truth (the §3 ``viewer=None``
discipline) and needs no recon ledger.

**Sensor and weather shape the take** rather than a flat radius. Each flight
carries an effective sensor radius, and the plugin degrades it with altitude (a
high fast pass resolves less than a proper recon profile) and with the campaign's
own cloud cover (§47/§67 already model the sky; recon previously ignored it
entirely). See ``resources/plugins/recon/recon-config.lua`` for the runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.ato import FlightType
from game.data.units import UAV_DCS_IDS
from game.theater import Player

if TYPE_CHECKING:
    from game import Game

    from .aircraft.flightdata import FlightData
    from .luagenerator import LuaData
    from .missiondata import MissionData

#: Effective sensor radius (NM) by sensor class. A dedicated recon pod out-ranges a
#: drone's EO/IR ball, which out-ranges an aircrew looking out of the canopy. These
#: are deliberately coarse -- the point is that the kit matters, not that it is
#: modelled to the metre.
TARPS_POD_RADIUS_NM = 3.0
DRONE_SENSOR_RADIUS_NM = 2.0

#: A flight must close within this of the target for the pass to count at all.
TRIGGER_RANGE_NM = 5.0


def _sensor_radius_nm(flight: "FlightData") -> float:
    """The effective sensor radius this flight brings to the target.

    A TARPS tasking means the aircraft is carrying (and pointing) a recon pod, so it
    reads wider than a drone's ball -- even when the drone is the one that always
    films. A drone flying TARPS gets the pod figure, which is the intended reading:
    it is the tasking that says "this sortie is a recon sortie".
    """
    if flight.flight_type is FlightType.TARPS:
        return TARPS_POD_RADIUS_NM
    return DRONE_SENSOR_RADIUS_NM


def feeds_recon(flight: "FlightData") -> bool:
    """Whether this flight banks BDA when it overflies its target.

    A TARPS-tasked flight (any airframe) always does; a drone always does whatever
    it was tasked with. Manned combat flights do not -- they are not sensors.
    """
    if flight.flight_type is FlightType.TARPS:
        return True
    return flight.aircraft_type.dcs_unit_type.id in UAV_DCS_IDS


def _cloud_factor(game: "Game") -> float:
    """How much of the sensor's reach the weather leaves it, in ``[0.25, 1.0]``.

    Recon is the one mission the sky most obviously governs, and it was the one
    place the fork's own weather model was not consulted. Broken cloud costs some
    of the take; overcast costs most of it. Never zero -- a recon flight that
    reaches its target in filthy weather should come home with *something*, and a
    hard zero would read as the feature being broken rather than as bad weather.
    """
    conditions = getattr(game, "conditions", None)
    clouds = getattr(getattr(conditions, "weather", None), "clouds", None)
    if clouds is None:
        return 1.0
    # pydcs clouds carry an 0-10 density; treat it as the coverage proxy.
    density = getattr(clouds, "density", None)
    if density is None:
        return 1.0
    try:
        fraction = max(0.0, min(1.0, float(density) / 10.0))
    except (TypeError, ValueError):
        return 1.0
    return 1.0 - 0.75 * fraction


def populate_recon_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Emit one record per BLUE recon-capable flight + its target.

    Player-crewed flights are emitted alongside AI ones -- that is the whole point
    of the rebuild, and it is load-bearing: the MOOSE film menu that used to serve
    players is gone, so if they were still excluded here a human recon sortie would
    confirm nothing at all.

    Emits nothing (no ``Recon`` node) when no such flight exists, so the plugin
    no-ops.
    """
    flights: list[tuple[str, str, str, float, float, float]] = []
    for flight in mission_data.flights:
        if not feeds_recon(flight):
            continue
        if flight.friendly is not Player.BLUE:
            continue  # only the human coalition's recon feeds the BDA ledger
        target = flight.package.target
        position = getattr(target, "position", None)
        if position is None:
            continue
        # Human-readable identity for the coalition BDA cue: two identical
        # "recon flight confirmed BDA" popups minutes apart are indistinguishable
        # without naming the flight and where it was looking.
        label = f"{flight.callsign} ({flight.aircraft_type.display_name})"
        flights.append(
            (
                flight.group_name,
                label,
                target.name,
                position.x,
                position.y,
                _sensor_radius_nm(flight),
            )
        )

    if not flights:
        return

    recon = root.add_item("Recon")
    # NOTE: scalars on a node that ALSO has child items must be emitted as named
    # child items, not add_key_value -- LuaData.serialize silently drops the
    # key/value entries in that case (the §81 finding, where `stagger`/`metered`
    # never reached the miz). `flights` below is a child item, so `cloudFactor`
    # has to be one too.
    recon.add_item("cloudFactor").set_value(str(round(_cloud_factor(game), 3)))
    flights_item = recon.add_item("flights")
    for group_name, label, target_name, x, y, sensor_nm in flights:
        record = flights_item.add_item()
        record.add_key_value("group", group_name)
        record.add_key_value("label", label)
        record.add_key_value("target", target_name)
        # pydcs Point: x = north, y = east. The Lua maps these onto the DCS world.
        record.add_key_value("x", str(x))
        record.add_key_value("y", str(y))
        record.add_key_value("sensorNm", str(sensor_nm))
