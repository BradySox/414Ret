from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game


class FactionTurnMetadata:
    """
    Store metadata about a faction
    """

    aircraft_count: int = 0
    vehicles_count: int = 0
    sam_count: int = 0
    #: Political will at the start of this turn (Vietnam campaign layer W1).
    #: None outside vietnam_political_will campaigns; the class-level default
    #: covers pre-feature pickled turns (no __setstate__ here by design).
    political_will: Optional[float] = None

    def __init__(self) -> None:
        self.aircraft_count = 0
        self.vehicles_count = 0
        self.sam_count = 0
        self.political_will = None


class GameTurnMetadata:
    """
    Store metadata about a game turn
    """

    allied_units: FactionTurnMetadata
    enemy_units: FactionTurnMetadata

    def __init__(self) -> None:
        self.allied_units = FactionTurnMetadata()
        self.enemy_units = FactionTurnMetadata()


class GameStats:
    """
    Store statistics for the current game
    """

    def __init__(self) -> None:
        self.data_per_turn: List[GameTurnMetadata] = []

    def update(self, game: Game) -> None:
        """
        Save data for current turn
        :param game: Game we want to save the data about
        """

        # Remove the current turn if its just an update for this turn
        if 0 < game.turn < len(self.data_per_turn):
            del self.data_per_turn[-1]

        turn_data = GameTurnMetadata()

        # Political will rides the same per-turn series the stats window charts
        # (one source of truth for trends; the client sparkline reads it too).
        if getattr(game.settings, "vietnam_political_will", False):
            turn_data.allied_units.political_will = getattr(
                game.blue, "political_will", None
            )
            turn_data.enemy_units.political_will = getattr(
                game.red, "political_will", None
            )

        for cp in game.theater.controlpoints:
            if cp.captured.is_blue:
                for squadron in cp.squadrons:
                    turn_data.allied_units.aircraft_count += squadron.owned_aircraft
                turn_data.allied_units.vehicles_count += sum(cp.base.armor.values())
            else:
                for squadron in cp.squadrons:
                    turn_data.enemy_units.aircraft_count += squadron.owned_aircraft
                turn_data.enemy_units.vehicles_count += sum(cp.base.armor.values())

        self.data_per_turn.append(turn_data)
