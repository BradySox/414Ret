"""Neutral border defense -> Lua config bridge (``dcsRetribution.neutralBorder``).

§96: campaign-authored neutral countries defend their own airspace. The
generator (``NeutralBorderGenerator``) builds late-activation alert templates at
each neutral field and records what it actually built here; this module only
serializes that record. A zone whose templates could not be built never reaches
the Lua, so the plugin needs no missing-template handling.

All values are emitted as Lua strings (the ``LuaItem`` contract); the plugin
``tonumber()``s the numerics once at load. Border vertices are terrain XY —
pydcs ``Point.x``/``.y`` = DCS ``x``/``z`` — which the plugin compares against
``unit:getPoint().x``/``.z``.

Emits nothing when the setting is off or no zone was built; such missions carry
no ``neutralBorder`` node and the plugin no-ops.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData


@dataclass(frozen=True)
class NeutralBorderLuaZone:
    """One neutral country's zone, as actually built into the miz."""

    country: str
    floor_ft: int
    #: "neutral", "blue" or "red" -- who owns the airspace, which picks the
    #: colour family. Only a neutral that refuses transit carries templates and
    #: is scanned; everything else is map information.
    posture: str = "neutral"
    #: Per-side transit consent, resolved from the campaign date against the
    #: posture table (or the campaign's override). A country may be open to one
    #: bloc and closed to the other, so this is two flags, not one.
    overflight_blue: bool = False
    overflight_red: bool = False
    #: Exact .miz group name of the late-activation fighter template.
    fighter_template: str | None = None
    #: Exact .miz group name of the late-activation SAM template, or None.
    sam_template: str | None = None
    #: pydcs country ids present in the mission, one per side: the clone spawns
    #: under whichever opposes the intruder.
    red_country_id: int = 0
    blue_country_id: int = 0
    #: Exact map airbase name (``AIRBASE:FindByName``), or None for a zone whose
    #: neutral has no airfield on the map (Afghanistan's neighbours).
    airfield: str | None = None
    #: Terrain XY + altitude the alert flight air-spawns at, when there is no
    #: airfield. Mutually exclusive with ``airfield``.
    spawn: tuple[float, float] | None = None
    spawn_alt_m: float = 0.0
    #: What the map tooltip calls the alert flight's source.
    origin_label: str = ""
    #: Terrain XY vertices (pydcs Point.x/.y = DCS x/z), implicit closure.
    border: list[tuple[float, float]] = field(default_factory=list)

    @property
    def enforces(self) -> bool:
        """True when this border intercepts anyone at all."""
        return self.posture == "neutral" and not (
            self.overflight_blue and self.overflight_red
        )


def populate_neutral_border_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Build the ``dcsRetribution.neutralBorder`` subtree."""
    if not getattr(game.settings, "neutral_border_defense", False):
        return
    zones = mission_data.neutral_border_zones
    if not zones:
        return

    node = root.add_item("neutralBorder")
    zones_node = node.get_or_create_item("zones")
    for zone in zones:
        record = zones_node.add_item()
        record.add_key_value("country", zone.country)
        record.add_key_value("posture", zone.posture)
        # Per side: the Lua checks the intruder's own coalition against its own
        # flag, so a country open to blue and closed to red behaves correctly
        # for both. The client renders the blue view.
        record.add_key_value(
            "overflightBlue", "true" if zone.overflight_blue else "false"
        )
        record.add_key_value(
            "overflightRed", "true" if zone.overflight_red else "false"
        )
        record.add_key_value("originLabel", zone.origin_label)
        if zone.enforces:
            # Exactly one of field / spawn is present -- the Lua branches on it.
            if zone.airfield is not None:
                record.add_key_value("field", zone.airfield)
            if zone.spawn is not None:
                record.add_key_value("spawnX", f"{zone.spawn[0]:.1f}")
                record.add_key_value("spawnZ", f"{zone.spawn[1]:.1f}")
                record.add_key_value("spawnAltM", f"{zone.spawn_alt_m:.1f}")
            record.add_key_value("floorFt", str(zone.floor_ft))
            assert zone.fighter_template is not None
            record.add_key_value("fighterTemplate", zone.fighter_template)
            if zone.sam_template is not None:
                record.add_key_value("samTemplate", zone.sam_template)
            record.add_key_value("redCountryId", str(zone.red_country_id))
            record.add_key_value("blueCountryId", str(zone.blue_country_id))
        border_node = record.get_or_create_item("border")
        for x, y in zone.border:
            vertex = border_node.add_item()
            vertex.add_key_value("x", f"{x:.1f}")
            vertex.add_key_value("y", f"{y:.1f}")
