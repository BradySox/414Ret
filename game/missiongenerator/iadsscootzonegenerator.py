"""Generated displacement zones for MANTIS point-defense shoot-and-scoot.

MOOSE's SHORAD class can displace a point-defense group to a nearby trigger
zone whenever it wakes, is shot at, or goes back to sleep
(``SHORAD:onafterShootAndScoot``). It needs a ``SET_ZONE`` of candidate
destinations, which MANTIS receives via ``MANTIS:AddScootZones``. Nothing in
DCS creates those zones -- a hand-built mission authors them in the editor, one
by one, near every site that should be able to move.

Retribution generates its missions, so it can emit them instead. For every
point-defense group that the MANTIS bridge will hand to SHORAD, this generator
rings the group with a handful of small hidden trigger zones on driveable land.
The bridge then builds a ``SET_ZONE`` from the shared name prefix and passes it
to ``AddScootZones``.

Two contracts this module has to keep in step with MOOSE and with the bridge:

* ``SHORAD:onafterShootAndScoot`` only considers zones between
  ``minscootdist`` and ``maxscootdist`` of the group's *current* position. Zones
  outside that window are silently never used, so the ring radii here and the
  distances the bridge writes onto the SHORAD object are derived from the same
  ``scootRadiusNm`` option, clamped identically at both ends.
* The bridge's ``collect_pd`` only scans the ``Sam`` and ``SamAsEwr`` node
  lists, so a point defense hanging off any other node role is not in the SHORAD
  set and must not get zones here either.

See docs/dev/design/414th-mantis-iads-HANDOFF.md.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator

from dcs.mission import Mission
from dcs.mapping import Point

from game.theater.iadsnetwork.iadsrole import IadsRole
from game.theater.theatergroup import IadsGroundGroup
from game.utils import Distance, meters, nautical_miles

if TYPE_CHECKING:
    from game.game import Game

#: Name prefix shared with the MANTIS bridge's ``SET_ZONE:FilterPrefixes`` call.
#: Deliberately free of Lua pattern metacharacters -- MOOSE matches set prefixes
#: with ``string.find`` without the plain flag, so a name with "(" or "-" in it
#: would be read as a pattern (the same trap ``escape_prefix`` works around for
#: group names in mantis-config.lua).
SCOOT_ZONE_PREFIX = "RetributionScoot"

#: Radius of each emitted zone. SHORAD picks a random point inside the chosen
#: zone (``GetRandomCoordinate`` restricted to LAND/ROAD surfaces), so a small
#: but non-zero radius gives the destination some spread without letting a group
#: wander outside the ring this generator validated.
ZONE_RADIUS = meters(120)

#: MOOSE's own floor for a scoot leg (``SHORAD.minscootdist``). A zone closer
#: than this to the group is never selected, so never emit one inside it.
MOOSE_MIN_SCOOT_DISTANCE = meters(100)

#: Fraction of the outer radius used as the inner radius of the ring. Keeps
#: every emitted zone a meaningful drive away without pushing them all out to
#: the maximum, which would make the displacement conspicuously uniform.
INNER_RADIUS_FRACTION = 0.35

#: Attempts per zone to find a land position before giving up on that slot. A
#: coastal or mountainside site legitimately has fewer usable directions, so a
#: partial ring is a normal outcome, not an error.
PLACEMENT_ATTEMPTS = 12


@dataclass(frozen=True)
class ScootSite:
    """One point-defense group that should be able to displace."""

    group_name: str
    position: Point


class IadsScootZoneGenerator:
    """Emits SHORAD displacement zones around each point-defense group."""

    def __init__(self, mission: Mission, game: Game) -> None:
        self.mission = mission
        self.game = game

    @property
    def enabled(self) -> bool:
        """True when the bridge will actually consume the zones.

        Scooting rides on the SHORAD object the bridge builds under
        ``shoradLink``; with that off there is no SHORAD to displace anything,
        so emitting zones would just add dead trigger zones to the miz.
        """
        settings = self.game.settings
        try:
            if not settings.plugin_option("mantisiads"):
                return False
            if not settings.plugin_option("mantisiads.shoradLink"):
                return False
            return bool(settings.plugin_option("mantisiads.shoradScoot"))
        except KeyError:
            # Plugin absent from this save's settings: behave as pre-feature.
            return False

    @property
    def zones_per_site(self) -> int:
        try:
            return max(
                1, int(self.game.settings.plugin_option("mantisiads.scootZones"))
            )
        except (KeyError, TypeError, ValueError):
            return 4

    @property
    def outer_radius(self) -> Distance:
        try:
            radius = nautical_miles(
                float(self.game.settings.plugin_option("mantisiads.scootRadiusNm"))
            )
        except (KeyError, TypeError, ValueError):
            radius = nautical_miles(1.3)
        # Anything at or below MOOSE's floor would produce zones it can never
        # select. Clamp rather than emit unusable geometry.
        floor = MOOSE_MIN_SCOOT_DISTANCE * 2
        return radius if radius > floor else floor

    @property
    def inner_radius(self) -> Distance:
        inner = self.outer_radius * INNER_RADIUS_FRACTION
        return inner if inner > MOOSE_MIN_SCOOT_DISTANCE else MOOSE_MIN_SCOOT_DISTANCE

    def point_defense_sites(self) -> Iterator[ScootSite]:
        """Every point-defense group the MANTIS bridge will hand to SHORAD.

        Mirrors ``collect_pd`` in mantis-config.lua: only point defenses hanging
        off a SAM or SAM-as-EWR node are in the SHORAD set, and a group attached
        to several SAMs is one site, not several.
        """
        seen: set[str] = set()
        network = self.game.theater.iads_network
        for node in network.nodes:
            if node.group.iads_role not in (IadsRole.SAM, IadsRole.SAM_AS_EWR):
                continue
            if self.game.iads_considerate_culling(node.group.ground_object):
                continue
            for connection in node.connections.values():
                if connection.iads_role is not IadsRole.POINT_DEFENSE:
                    continue
                if not self._is_live(connection):
                    continue
                if self.game.iads_considerate_culling(connection.ground_object):
                    continue
                name = connection.group_name
                if name in seen:
                    continue
                seen.add(name)
                yield ScootSite(name, connection.position)

    @staticmethod
    def _is_live(group: IadsGroundGroup) -> bool:
        return any(unit.alive for unit in group.units)

    def _ring_positions(self, site: ScootSite) -> list[Point]:
        """Land positions ringing a site, evenly spread with jitter.

        Seeded from the group name so a regenerated turn places the same zones:
        the campaign map, the threat rings, and any screenshot taken of the
        previous generation all stay honest.
        """
        rng = random.Random(site.group_name)
        count = self.zones_per_site
        inner = self.inner_radius.meters
        outer = self.outer_radius.meters
        sector = 360.0 / count
        positions: list[Point] = []
        for index in range(count):
            base_heading = sector * index
            for _ in range(PLACEMENT_ATTEMPTS):
                heading = base_heading + rng.uniform(-sector / 2, sector / 2)
                distance = rng.uniform(inner, outer)
                candidate = site.position.point_from_heading(heading, distance)
                if self.game.theater.is_on_land(candidate):
                    positions.append(candidate)
                    break
        return positions

    def generate(self) -> int:
        """Emit the zones. Returns how many were added."""
        if not self.enabled:
            return 0

        emitted = 0
        sites = 0
        for site in self.point_defense_sites():
            sites += 1
            for position in self._ring_positions(site):
                emitted += 1
                self.mission.triggers.add_triggerzone(
                    position,
                    radius=ZONE_RADIUS.meters,
                    hidden=True,
                    name=f"{SCOOT_ZONE_PREFIX}-{emitted}",
                )

        if sites and not emitted:
            logging.warning(
                "MANTIS scoot: %d point-defense site(s) but no usable land "
                "position within %.0f m; point defenses will not displace.",
                sites,
                self.outer_radius.meters,
            )
        elif emitted:
            logging.info(
                "MANTIS scoot: %d displacement zone(s) for %d point-defense site(s)",
                emitted,
                sites,
            )
        return emitted
