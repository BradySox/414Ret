"""SP Pilot Mode -- the aircraft-first sortie board.

The board's contract is small and load-bearing: the **airframe** is the primary
axis (the player's variety choice), the **role** comes from the air war, and the
player takes exactly **one seat** with AI wingmen, as in MP. These drive the
real ``airframe_options`` / ``sortie_options`` / ``seat_player_in`` against
duck-typed wing and ATO objects.
"""

from __future__ import annotations

from typing import Any, List, Optional

from game.fourteenth.sp_pilot_mode import (
    AirframeOption,
    SortieOption,
    airframe_options,
    enabled,
    seat_player_in,
    sortie_options,
    take_seat,
)


class FakePilot:
    def __init__(self, name: str, player: bool = False) -> None:
        self.name = name
        self.player = player

    def __repr__(self) -> str:
        return f"<{self.name}{' (player)' if self.player else ''}>"


class FakeRoster:
    def __init__(self, size: int = 2) -> None:
        self.max_size = size
        self.seated: dict[int, FakePilot] = {}

    def set_pilot(self, index: int, pilot: FakePilot) -> None:
        self.seated[index] = pilot


class FakeSquadron:
    def __init__(
        self,
        name: str,
        aircraft: str,
        location: str = "Nordholz",
        untasked: int = 4,
        player_pilots: int = 1,
    ) -> None:
        self.name = name
        self.aircraft = aircraft
        self.location = location
        self.untasked_aircraft = untasked
        self.available_pilots: List[FakePilot] = [
            FakePilot(f"{name}-{i}", player=i < player_pilots) for i in range(3)
        ]


class FakeFlight:
    def __init__(
        self,
        squadron: FakeSquadron,
        flight_type: str,
        client_count: int = 0,
        roster_size: int = 2,
    ) -> None:
        self.squadron = squadron
        self.flight_type = flight_type
        self.client_count = client_count
        self.roster = FakeRoster(roster_size)


class FakePackage:
    def __init__(self, target: str, flights: Optional[List[FakeFlight]] = None) -> None:
        self.target = target
        self.flights = flights or []
        self.time_over_target = "07:42"

    @property
    def primary_flight(self) -> Optional[FakeFlight]:
        return self.flights[0] if self.flights else None


class FakeAto:
    def __init__(self, packages: Optional[List[FakePackage]] = None) -> None:
        self.packages = packages or []


class FakeAirWing:
    def __init__(self, squadrons: List[FakeSquadron]) -> None:
        self._squadrons = squadrons

    def iter_squadrons(self) -> List[FakeSquadron]:
        return self._squadrons


class FakeCoalition:
    def __init__(self, squadrons: List[FakeSquadron], ato: FakeAto) -> None:
        self.air_wing = FakeAirWing(squadrons)
        self.ato = ato


class FakeSettings:
    def __init__(self, on: bool = True) -> None:
        self.sp_pilot_mode = on


class FakeGame:
    def __init__(
        self,
        squadrons: Optional[List[FakeSquadron]] = None,
        packages: Optional[List[FakePackage]] = None,
        on: bool = True,
    ) -> None:
        self.settings = FakeSettings(on)
        self.blue = FakeCoalition(squadrons or [], FakeAto(packages))


# ------------------------------------------------------------------ the gate


def test_the_mode_is_gated() -> None:
    assert enabled(FakeGame(on=True))  # type: ignore[arg-type]
    assert not enabled(FakeGame(on=False))  # type: ignore[arg-type]


# ------------------------------------------------- step 1: pick the airframe


def test_every_airframe_in_the_wing_is_offered() -> None:
    """Not filtered by what the commander planned -- the whole point of choosing
    the jet first is that the choice belongs to the player."""
    game = FakeGame(
        squadrons=[
            FakeSquadron("VF-154", "F-14A"),
            FakeSquadron("414th Voodoo", "F-16CM"),
        ],
        packages=[],  # the commander planned nothing at all
    )

    options = airframe_options(game)  # type: ignore[arg-type]

    assert [o.name for o in options] == ["F-14A", "F-16CM"]


def test_airframes_are_sorted_stably() -> None:
    game = FakeGame(
        squadrons=[
            FakeSquadron("c", "F-16CM"),
            FakeSquadron("a", "A-10C"),
            FakeSquadron("b", "F-14A"),
        ]
    )
    assert [o.name for o in airframe_options(game)] == [  # type: ignore[arg-type]
        "A-10C",
        "F-14A",
        "F-16CM",
    ]


def test_squadrons_of_one_type_are_grouped() -> None:
    game = FakeGame(
        squadrons=[
            FakeSquadron("VFA-1", "F/A-18C", location="CVN-75", untasked=6),
            FakeSquadron("VFA-2", "F/A-18C", location="Hamburg", untasked=4),
        ]
    )

    (option,) = airframe_options(game)  # type: ignore[arg-type]

    assert option.ready_airframes == 10
    assert option.bases == ["CVN-75", "Hamburg"]


def test_a_grounded_airframe_is_still_listed() -> None:
    """A type with no spare jets is worth showing -- it is either an arrival to
    look forward to or a base that needs retaking."""
    game = FakeGame(squadrons=[FakeSquadron("VF-154", "F-14A", untasked=0)])

    (option,) = airframe_options(game)  # type: ignore[arg-type]

    assert option.name == "F-14A"
    assert not option.has_spare_airframes


def test_a_fully_tasked_type_can_still_be_flown_by_taking_a_seat() -> None:
    """has_spare_airframes is not "can I fly it": every jet being tasked is
    exactly the case rung 1 exists for."""
    squadron = FakeSquadron("414th Voodoo", "F-16CM", untasked=0)
    package = FakePackage("Haina", [FakeFlight(squadron, "DEAD")])
    game = FakeGame(squadrons=[squadron], packages=[package])

    (option,) = airframe_options(game)  # type: ignore[arg-type]
    assert not option.has_spare_airframes
    assert [o.rung for o in sortie_options(game, "F-16CM")] == [1]  # type: ignore[arg-type]


# --------------------------------------------------- step 2: pick the sortie


def test_rung_one_offers_a_seat_in_an_existing_flight() -> None:
    squadron = FakeSquadron("414th Voodoo", "F-16CM")
    package = FakePackage("Haina", [FakeFlight(squadron, "DEAD")])
    game = FakeGame(squadrons=[squadron], packages=[package])

    options = sortie_options(game, "F-16CM")  # type: ignore[arg-type]

    seats = [o for o in options if o.rung == 1]
    assert len(seats) == 1
    assert seats[0].task == "DEAD"
    assert seats[0].target == "Haina"
    assert seats[0].flight is not None


def test_a_flight_that_already_has_a_client_is_not_offered() -> None:
    """One seat: a flight carrying a client is somebody else's, or already
    yours."""
    squadron = FakeSquadron("414th Voodoo", "F-16CM")
    package = FakePackage("Haina", [FakeFlight(squadron, "DEAD", client_count=1)])
    game = FakeGame(squadrons=[squadron], packages=[package])

    assert [o for o in sortie_options(game, "F-16CM") if o.rung == 1] == []  # type: ignore[arg-type]


def test_another_airframes_flight_is_not_offered() -> None:
    viper = FakeSquadron("Voodoo", "F-16CM")
    tomcat = FakeSquadron("VF-154", "F-14A")
    package = FakePackage("Haina", [FakeFlight(viper, "DEAD")])
    game = FakeGame(squadrons=[viper, tomcat], packages=[package])

    assert [o for o in sortie_options(game, "F-14A") if o.rung == 1] == []  # type: ignore[arg-type]


def test_rung_two_offers_the_role_the_package_is_missing() -> None:
    """The air war picks the job. A strike package with no escort of any kind
    offers all three escort roles."""
    squadron = FakeSquadron("VF-154", "F-14A")
    package = FakePackage("Haina", [FakeFlight(squadron, "Strike")])
    game = FakeGame(squadrons=[squadron], packages=[package])

    joins = [o for o in sortie_options(game, "F-14A") if o.rung == 2]  # type: ignore[arg-type]

    assert {o.task for o in joins} == {"Escort", "SEAD Escort", "Escort Jammer"}


def test_rung_two_does_not_offer_a_role_the_package_already_fields() -> None:
    squadron = FakeSquadron("VF-154", "F-14A")
    package = FakePackage(
        "Haina",
        [FakeFlight(squadron, "Strike"), FakeFlight(squadron, "Escort")],
    )
    game = FakeGame(squadrons=[squadron], packages=[package])

    joins = [o for o in sortie_options(game, "F-14A") if o.rung == 2]  # type: ignore[arg-type]

    assert "Escort" not in {o.task for o in joins}


def test_no_join_is_offered_without_a_spare_airframe() -> None:
    squadron = FakeSquadron("VF-154", "F-14A", untasked=0)
    package = FakePackage("Haina", [FakeFlight(squadron, "Strike")])
    game = FakeGame(squadrons=[squadron], packages=[package])

    assert [o for o in sortie_options(game, "F-14A") if o.rung == 2] == []  # type: ignore[arg-type]


def test_an_unknown_airframe_yields_nothing() -> None:
    game = FakeGame(squadrons=[FakeSquadron("VF-154", "F-14A")])
    assert sortie_options(game, "Su-27") == []  # type: ignore[arg-type]


def test_the_description_leads_with_the_role() -> None:
    """Role and package are the news; the target is context. A join says so."""
    seat = SortieOption(
        rung=1, task="DEAD", target="Haina", squadron=None, tot="07:42"  # type: ignore[arg-type]
    )
    join = SortieOption(
        rung=2, task="Escort", target="Haina", squadron=None  # type: ignore[arg-type]
    )

    assert seat.description.startswith("DEAD on Haina")
    assert "TOT 07:42" in seat.description
    assert "(joining)" in join.description
    assert "(joining)" not in seat.description


# ------------------------------------------------------------ taking a seat


def test_seating_claims_exactly_one_player_pilot() -> None:
    squadron = FakeSquadron("414th Voodoo", "F-16CM", player_pilots=1)
    flight = FakeFlight(squadron, "DEAD")
    game = FakeGame(squadrons=[squadron])

    seated = seat_player_in(game, flight)  # type: ignore[arg-type]

    assert seated is not None, "a free player pilot should have been seated"
    assert list(flight.roster.seated) == [0]
    assert flight.roster.seated[0].player is True


def test_seating_refuses_when_no_player_pilot_is_free() -> None:
    """Not an error -- the squadron simply has none, and the caller should offer
    another sortie."""
    squadron = FakeSquadron("414th Voodoo", "F-16CM", player_pilots=0)
    flight = FakeFlight(squadron, "DEAD")
    game = FakeGame(squadrons=[squadron])

    assert seat_player_in(game, flight) is None  # type: ignore[arg-type]
    assert flight.roster.seated == {}


def test_take_seat_on_a_rung_one_option_seats_that_flight() -> None:
    squadron = FakeSquadron("414th Voodoo", "F-16CM")
    flight = FakeFlight(squadron, "DEAD")
    option = SortieOption(
        rung=1, task="DEAD", target="Haina", squadron=squadron, flight=flight  # type: ignore[arg-type]
    )
    game = FakeGame(squadrons=[squadron])

    assert take_seat(game, option) is not None  # type: ignore[arg-type]
    assert list(flight.roster.seated) == [0]


def test_take_seat_never_silently_mutates_the_ato_for_a_join() -> None:
    """Rung 2 builds a flight through the ATO's own add-flight path, owned by
    the caller -- so the board can be rendered and abandoned without touching
    anything."""
    squadron = FakeSquadron("VF-154", "F-14A")
    option = SortieOption(rung=2, task="Escort", target="Haina", squadron=squadron)  # type: ignore[arg-type]
    game = FakeGame(squadrons=[squadron])

    assert take_seat(game, option) is None  # type: ignore[arg-type]


def test_a_seating_failure_is_swallowed() -> None:
    squadron = FakeSquadron("414th Voodoo", "F-16CM")
    flight = FakeFlight(squadron, "DEAD")

    def boom(index: int, pilot: Any) -> None:
        raise RuntimeError("roster is having a day")

    flight.roster.set_pilot = boom  # type: ignore[method-assign]
    game = FakeGame(squadrons=[squadron])

    assert seat_player_in(game, flight) is None  # type: ignore[arg-type]


# ------------------------------------------------------------------ shapes


def test_airframe_option_reports_no_bases_without_squadrons() -> None:
    option = AirframeOption(aircraft="F-14A", squadrons=[])  # type: ignore[arg-type]
    assert option.bases == []
    assert option.ready_airframes == 0
    assert not option.has_spare_airframes
