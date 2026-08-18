from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from game.missiongenerator.frontlineconflictdescription import (
    FrontLineConflictDescription,
)
from game.server.leaflet import LeafletPoint

if TYPE_CHECKING:
    from game import Game
    from game.theater import FrontLine, ConflictTheater


class FrontLineJs(BaseModel):
    id: UUID
    extents: list[LeafletPoint]

    class Config:
        title = "FrontLine"

    @staticmethod
    def for_front_line(theater: ConflictTheater, front_line: FrontLine) -> FrontLineJs:
        bounds = FrontLineConflictDescription.frontline_bounds(front_line, theater)
        # The whole trace, not just the two ends: §90 rung E bows the front, and
        # this is the map the player plans on. `polyline` is exactly the two
        # endpoints when the front has no sector depths, so a straight front is
        # byte-identical to what this sent before.
        return FrontLineJs(
            id=front_line.id,
            extents=[point.latlng() for point in bounds.polyline],
        )

    @staticmethod
    def all_in_game(game: Game) -> list[FrontLineJs]:
        return [
            FrontLineJs.for_front_line(game.theater, f)
            for f in game.theater.conflicts()
        ]
