from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from dcs import Point

from game.utils import Distance, meters, nautical_miles

#: How far the pinned bullseye may sit from the point it would be re-derived at
#: before it is moved. Upstream re-derived the bullseye every turn, so it jumped
#: whenever the nearest opposing pair changed -- but a squadron memorizes one
#: bullseye and flies to it for weeks. Design note:
#: docs/dev/design/414th-bullseye-notes.md.
MAX_DRIFT: Distance = nautical_miles(80)


@dataclass
class Bullseye:
    position: Point

    def to_pydcs(self) -> Dict[str, float]:
        return {"x": self.position.x, "y": self.position.y}

    def drifted_from(self, candidate: Point) -> bool:
        """True when the fighting has moved far enough to re-anchor."""
        return meters(self.position.distance_to_point(candidate)) > MAX_DRIFT
