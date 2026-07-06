from __future__ import annotations

from dataclasses import dataclass, field
from enum import unique, Enum

from faker import Faker


@dataclass
class PilotRecord:
    missions_flown: int = field(default=0)


@unique
class PilotStatus(Enum):
    Active = "Active"
    OnLeave = "On leave"
    Dead = "Dead"
    #: Captured by an enemy snatch party after ejecting (the §15/§21 Combat SAR
    #: capture race). Held alive as a POW (``PendingPowRecovery`` on the losing
    #: coalition): repatriated if the holding field is retaken or the war is won,
    #: written off (killed) if the hold clock runs out or the war is lost. A POW
    #: is NOT Active, so the squadron never schedules them while captive.
    POW = "POW"


@dataclass
class Pilot:
    name: str
    player: bool = field(default=False)
    status: PilotStatus = field(default=PilotStatus.Active)
    record: PilotRecord = field(default_factory=PilotRecord)

    @property
    def alive(self) -> bool:
        return self.status is not PilotStatus.Dead

    @property
    def on_leave(self) -> bool:
        return self.status is PilotStatus.OnLeave

    @property
    def captured(self) -> bool:
        return self.status is PilotStatus.POW

    def capture(self) -> None:
        """Take this pilot prisoner (Active -> POW). Idempotent for a pilot
        already held; a dead pilot cannot be captured."""
        if self.status is PilotStatus.Dead:
            return
        self.status = PilotStatus.POW

    def repatriate(self) -> None:
        """Return a POW to the active roster (POW -> Active). No-op otherwise."""
        if self.status is PilotStatus.POW:
            self.status = PilotStatus.Active

    def send_on_leave(self) -> None:
        if self.status is not PilotStatus.Active:
            raise RuntimeError("Only active pilots may be sent on leave")
        self.status = PilotStatus.OnLeave

    def return_from_leave(self) -> None:
        if self.status is not PilotStatus.OnLeave:
            raise RuntimeError("Only pilots on leave may be returned from leave")
        self.status = PilotStatus.Active

    def kill(self) -> None:
        self.status = PilotStatus.Dead

    @classmethod
    def random(cls, faker: Faker) -> Pilot:
        return Pilot(faker.name())
