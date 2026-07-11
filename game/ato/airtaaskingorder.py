from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List

from game.ato import FlightType
from game.ato.package import Package


@dataclass
class AirTaskingOrder:
    """The entire ATO for one coalition."""

    #: The set of all planned packages in the ATO.
    packages: List[Package] = field(default_factory=list)

    @property
    def has_awacs_package(self) -> bool:
        return any(
            [
                p
                for p in self.packages
                if any([f for f in p.flights if f.flight_type is FlightType.AEWC])
            ]
        )

    def add_package(self, package: Package) -> None:
        """Adds a package to the ATO."""
        self.packages.append(package)

    def remove_package(self, package: Package) -> None:
        """Removes a package from the ATO."""
        # Remove all the flights individually so the database gets updated.
        for flight in list(package.flights):
            package.remove_flight(flight)
        self.packages.remove(package)

    def clear(self) -> None:
        """Removes all packages from the ATO."""
        # Remove all packages individually so the database gets updated.
        for package in list(self.packages):
            self.remove_package(package)

    def shift_time(self, delta: timedelta) -> None:
        """Re-time every scheduled package by ``delta``.

        Flight timing (TOT, takeoff, startup, waypoint ETAs) is derived from the
        package TOT at read time (``FlightPlan.tot`` is ``package.time_over_target
        + tot_offset``), so shifting each package's TOT moves the whole ATO onto a
        new mission start without touching package/flight composition, rosters,
        loadouts, or routing. This lets the conditions dialog change the clock
        while preserving a hand-built frag, instead of wiping and re-planning it.

        Unscheduled packages (TOT still at the ``datetime.min`` sentinel) are left
        alone.
        """
        for package in self.packages:
            if package.time_over_target == datetime.min:
                continue
            package.time_over_target += delta
