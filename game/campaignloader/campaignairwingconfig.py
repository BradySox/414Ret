from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING, Union

from game.ato.flighttype import FlightType
from game.theater.controlpoint import ControlPoint

if TYPE_CHECKING:
    from game.theater import ConflictTheater


DEFAULT_SQUADRON_SIZE = 12


@dataclass(frozen=True)
class SquadronConfig:
    primary: FlightType
    secondary: list[FlightType]
    aircraft: list[str]
    max_size: int

    name: Optional[str]
    nickname: Optional[str]
    female_pilot_percentage: Optional[int]
    aircraft_type: Optional[str]
    callsign: Optional[str]
    #: DCS country name (e.g. "USA") pinning the nation the squadron flies under
    #: (#627 voice/comms + pilot names). Under a CJTF faction the airframe-name
    #: preset pick is otherwise a random.choice across every nation's presets.
    #: A pinned country prefers same-nation presets and stamps generated defs.
    country: Optional[str]

    @property
    def auto_assignable(self) -> set[FlightType]:
        # TARPS and Escort Jammer are support/escort roles that no campaign config
        # lists explicitly and that the "air-to-ground" alias does not cover (neither
        # is an attack task). Offer each to every squadron actually capable of it (the
        # capability filter in Squadron.set_auto_assignable_mission_types drops it for
        # the rest), so the auto-planner can pair a recon bird -- or a dedicated EW jet
        # (EA-6B/EA-18G) that a campaign authored as a SEAD squadron -- into a package
        # without requiring per-campaign squadron edits. The Escort Jammer role is
        # still gated downstream (radar-SAM threat, the loose-tier setting, and the
        # per-side max_escort_jammers cap in PackageFulfiller.can_plan_escort).
        return (
            set(self.secondary)
            | {self.primary}
            | {FlightType.TARPS, FlightType.ESCORT_JAMMER}
        )

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> SquadronConfig:
        secondary_raw = data.get("secondary")
        if secondary_raw is None:
            secondary = []
        elif isinstance(secondary_raw, str):
            secondary = cls.expand_secondary_alias(secondary_raw)
        else:
            secondary = [FlightType(s) for s in secondary_raw]

        max_size = data.get("size", DEFAULT_SQUADRON_SIZE)

        return SquadronConfig(
            FlightType(data["primary"]),
            secondary,
            # `aircraft:` authored but left empty parses as None; treat it as "any
            # aircraft compatible with the primary task" (the find_squadron_for
            # fallback) instead of crashing DefaultSquadronAssigner at New Game.
            data.get("aircraft") or [],
            max_size,
            data.get("name", None),
            data.get("nickname", None),
            data.get("female_pilot_percentage", None),
            data.get("aircraft_type", None),
            data.get("callsign", None),
            data.get("country", None),
        )

    @staticmethod
    def expand_secondary_alias(alias: str) -> list[FlightType]:
        if alias == "any":
            return list(FlightType)
        elif alias == "air-to-air":
            return [t for t in FlightType if t.is_air_to_air]
        elif alias == "air-to-ground":
            return [t for t in FlightType if t.is_air_to_ground]
        raise KeyError(f"Unknown secondary mission type: {alias}")


@dataclass(frozen=True)
class CampaignAirWingConfig:
    by_location: dict[ControlPoint, list[SquadronConfig]]

    @classmethod
    def empty(cls) -> CampaignAirWingConfig:
        """An air-wing config with no preconfigured squadrons at any base.

        Backed by a ``defaultdict`` so ``by_location[cp]`` yields ``[]`` for bases
        with nothing configured (e.g. the blank-canvas campaign maker, where the
        player staffs bases by hand) instead of raising ``KeyError`` in
        ``DefaultSquadronAssigner``.
        """
        empty: dict[ControlPoint, list[SquadronConfig]] = defaultdict(list)
        return CampaignAirWingConfig(empty)

    @classmethod
    def from_campaign_data(
        cls, data: dict[Union[str, int], Any], theater: ConflictTheater
    ) -> CampaignAirWingConfig:
        by_location: dict[ControlPoint, list[SquadronConfig]] = defaultdict(list)
        carriers = theater.find_carriers()
        lhas = theater.find_lhas()
        for base_id, squadron_configs in data.items():
            base: Optional[ControlPoint] = None
            if isinstance(base_id, int):
                base = theater.find_control_point_by_airport_id(base_id)
            else:
                try:
                    base = theater.control_point_named(base_id)
                except:
                    logging.warning(
                        f"Control point {base_id} not found, trying to match by full name"
                    )
                if not base:
                    try:
                        base = theater.control_point_by_full_name(base_id)
                    except KeyError:
                        logging.error(f"Control point {base_id} not found, skipping")
            for squadron_data in squadron_configs:
                if base is None:
                    logging.warning(
                        f"Skipping squadron config for unknown base: {base_id}"
                    )
                else:
                    by_location[base].append(SquadronConfig.from_data(squadron_data))

        return CampaignAirWingConfig(by_location)
