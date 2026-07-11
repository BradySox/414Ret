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
    #: Downed behind the lines and still EVADING at mission end (the §21
    #: persistent-evader ledger, ``game.downed_pilots``, 2026-07-10): they respawn
    #: at their last known position next mission and either get rescued
    #: (-> Active), get captured in-mission or by the depth-weighted turn roll
    #: (-> POW), or walk home off friendly ground (-> Active). Deliberately no
    #: death clock. MIA is NOT Active, so the squadron never schedules them.
    MIA = "MIA"


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

    @property
    def missing(self) -> bool:
        return self.status is PilotStatus.MIA

    def capture(self) -> None:
        """Take this pilot prisoner (Active/MIA -> POW). Idempotent for a pilot
        already held; a dead pilot cannot be captured."""
        if self.status is PilotStatus.Dead:
            return
        self.status = PilotStatus.POW

    def go_missing(self) -> None:
        """Mark this pilot down behind the lines, still evading (Active -> MIA).
        A dead pilot cannot go missing; a POW stays a POW."""
        if self.status in (PilotStatus.Dead, PilotStatus.POW):
            return
        self.status = PilotStatus.MIA

    def repatriate(self) -> None:
        """Return a POW or a recovered evader to the active roster. No-op
        otherwise."""
        if self.status in (PilotStatus.POW, PilotStatus.MIA):
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
