from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List
from unittest.mock import MagicMock

from dcs.vehicles import AirDefence

from game.data.units import UnitClass
from game.missiongenerator.kneeboard import (
    ThreatIntelBriefPage,
    build_threat_intel_cards,
)
from game.theater.theatergroundobject import EwrGroundObject, SamGroundObject
from game.utils import meters, nautical_miles


class _DummyPosition:
    x = 0.0
    y = 0.0

    def heading_between_point(self, other: Any) -> float:
        return 0.0

    def distance_to_point(self, other: Any) -> float:
        return 0.0


class _UnitType:
    """Hashable stand-in for a unit type (SimpleNamespace is unhashable, and
    ``_greatest_alive_threat`` keys a dict on the unit type)."""

    def __init__(self, display_name: str, unit_class: Any = None) -> None:
        self.display_name = display_name
        self.unit_class = unit_class


def _bullseye() -> Any:
    return SimpleNamespace(position=_DummyPosition())


def _sam(
    *,
    friendly: bool,
    known: bool,
    band: str,
    mez_nm: float = 0.0,
    dead: bool = False,
    coded_unit_id: str | None = None,
    system: str = "SA-6 Kub",
    spec: type = SamGroundObject,
) -> Any:
    """A fake SAM/EWR ground object configured for the recon-fog branches."""
    tgo = MagicMock(spec=spec)
    tgo.is_friendly.return_value = friendly
    tgo.known_for.return_value = known
    tgo.air_defense_band = band
    tgo.position = _DummyPosition()
    tgo.max_threat_range.return_value = nautical_miles(mez_nm)
    tgo.max_detection_range.return_value = nautical_miles(mez_nm)
    tgo.is_dead.return_value = dead
    # _greatest_alive_threat walks groups -> units; give it one live, named unit.
    unit = SimpleNamespace(
        alive=True,
        unit_type=_UnitType(system),
        type=SimpleNamespace(id=coded_unit_id),
    )
    tgo.groups = [SimpleNamespace(units=[unit])]
    tgo.units = [unit]
    return tgo


def _multi_unit_sam(
    *,
    band: str,
    mez_nm: float,
    units: List[tuple[str, Any, str | None]],
) -> Any:
    """A known SAM site whose group holds several unit types (radar + launcher).

    ``units`` is a list of ``(display_name, unit_class, coded_unit_id)`` in the order
    they appear in the group, so a test can place the search radar first and prove the
    card still names from the weapon system.
    """
    tgo = MagicMock(spec=SamGroundObject)
    tgo.is_friendly.return_value = False
    tgo.known_for.return_value = True
    tgo.air_defense_band = band
    tgo.position = _DummyPosition()
    tgo.max_threat_range.return_value = nautical_miles(mez_nm)
    tgo.max_detection_range.return_value = nautical_miles(mez_nm)
    tgo.is_dead.return_value = False
    built = [
        SimpleNamespace(
            alive=True,
            unit_type=_UnitType(display_name, unit_class),
            type=SimpleNamespace(id=coded_id),
        )
        for display_name, unit_class, coded_id in units
    ]
    tgo.groups = [SimpleNamespace(units=built)]
    tgo.units = built
    return tgo


def _game(ground_objects: List[Any]) -> Any:
    return SimpleNamespace(
        theater=SimpleNamespace(ground_objects=ground_objects),
        coalition_for=lambda player: SimpleNamespace(bullseye=_bullseye()),
    )


def _flight() -> Any:
    return SimpleNamespace(friendly=object(), callsign="Colt 1", custom_name=None)


def test_known_site_card_carries_live_data_and_curated_reference() -> None:
    sam = _sam(
        friendly=False,
        known=True,
        band="Medium-range SAM",
        mez_nm=23,
        coded_unit_id=AirDefence.Kub_1S91_str.id,  # ALIC 108, SA-6 reference
        system="SA-6 Kub",
    )
    cards, unidentified = build_threat_intel_cards(_game([sam]), _flight())

    assert unidentified == 0
    assert len(cards) == 1
    card = cards[0]
    # Live data from the campaign model.
    assert card.system == "SA-6 Kub"
    assert card.identified
    assert card.mez_nm == "23"
    assert card.harm == "108"
    assert card.band == "MERAD"
    assert card.live == 1 and card.dead == 0
    assert card.cues == ["000/0"]
    # Curated v2 enrichment from game.data.threat_reference.
    assert "Straight Flush" in card.guidance
    assert card.ceiling == "40,000 ft"
    assert card.defeat  # a non-empty "how to defeat" note


def test_card_names_weapon_system_not_co_located_search_radar() -> None:
    # An SA-5 site holds an acquisition radar (ST-68U "Tin Shield SR", which maps to the
    # weaponless EWR reference) AND the lethal Square Pair track radar. The card must be
    # named for — and described as — the SA-5 weapon system, not the search radar that
    # would otherwise hijack the heading and report "no weapons" despite the 138 nm MEZ.
    sa5 = _multi_unit_sam(
        band="Long-range SAM",
        mez_nm=138,
        units=[
            # Search radar deliberately first to prove ordering wins over insertion.
            (
                'SAM SA-5 S-200 ST-68U "Tin Shield" SR',
                UnitClass.SEARCH_RADAR,
                AirDefence.RLS_19J6.id,
            ),
            (
                'SAM SA-5 S-200 "Square Pair" TR',
                UnitClass.TRACK_RADAR,
                AirDefence.RPC_5N62V.id,
            ),
        ],
    )
    cards, _ = build_threat_intel_cards(_game([sa5]), _flight())

    assert len(cards) == 1
    card = cards[0]
    assert card.system == 'SAM SA-5 S-200 "Square Pair" TR'
    assert "SR" not in card.system.split()  # not the "... Tin Shield SR" search radar
    # Curated reference resolves to the SA-5, not the EWR ("no weapons") entry.
    assert "Square Pair" in card.guidance
    assert "No weapons" not in card.defeat
    assert card.mez_nm == "138"


def test_bare_search_radar_still_names_itself() -> None:
    # With nothing lethal co-located, a standalone search/EW radar honestly names its own
    # card — the weapon-preference must not invent a SAM that isn't there.
    radar = _multi_unit_sam(
        band="Early-warning radar",
        mez_nm=0,
        units=[
            (
                'SAM SA-10 S-300 "Grumble" Big Bird SR',
                UnitClass.SEARCH_RADAR,
                AirDefence.S_300PS_64H6E_sr.id,
            ),
        ],
    )
    radar.max_detection_range.return_value = nautical_miles(86)
    cards, _ = build_threat_intel_cards(_game([radar]), _flight())

    assert len(cards) == 1
    assert cards[0].system == 'SAM SA-10 S-300 "Grumble" Big Bird SR'


def test_undiscovered_site_is_fogged_to_its_band() -> None:
    # Recon fog: an unidentified site leaks neither system, range, HARM nor defeat
    # note — only its intel-tier band — and bumps the "fly TARPS" count.
    sam = _sam(friendly=False, known=False, band="Long-range SAM", mez_nm=40)
    cards, unidentified = build_threat_intel_cards(_game([sam]), _flight())

    assert unidentified == 1
    assert len(cards) == 1
    card = cards[0]
    assert card.system == "Unidentified LORAD"
    assert not card.identified
    assert card.mez_nm == "—" and card.harm == "—" and card.defeat == ""
    assert card.live == 1


def test_friendly_air_defenses_are_excluded() -> None:
    friendly = _sam(friendly=True, known=True, band="Long-range SAM", mez_nm=40)
    cards, unidentified = build_threat_intel_cards(_game([friendly]), _flight())

    assert cards == []
    assert unidentified == 0


def test_sites_of_the_same_system_aggregate_into_one_card() -> None:
    def sa6() -> Any:
        return _sam(
            friendly=False,
            known=True,
            band="Medium-range SAM",
            mez_nm=23,
            coded_unit_id=AirDefence.Kub_1S91_str.id,
            system="SA-6 Kub",
        )

    cards, _ = build_threat_intel_cards(_game([sa6(), sa6()]), _flight())

    assert len(cards) == 1
    assert cards[0].live == 2
    assert cards[0].cues == ["000/0", "000/0"]


def test_cards_sort_live_most_lethal_then_unidentified() -> None:
    short = _sam(
        friendly=False, known=True, band="Short-range SAM", mez_nm=8, system="SA-8 Osa"
    )
    long_range = _sam(
        friendly=False,
        known=True,
        band="Long-range SAM",
        mez_nm=40,
        system="SA-10 Grumble",
    )
    unknown = _sam(friendly=False, known=False, band="Medium-range SAM", mez_nm=23)

    cards, _ = build_threat_intel_cards(_game([short, unknown, long_range]), _flight())

    assert [c.system for c in cards] == [
        "SA-10 Grumble",
        "SA-8 Osa",
        "Unidentified MERAD",
    ]


def test_ewr_card_reports_detection_range_and_defeat_note() -> None:
    ewr = _sam(
        friendly=False,
        known=True,
        band="Early-warning radar",
        coded_unit_id=AirDefence.x_1L13_EWR.id,  # ALIC 101, EWR reference
        system="1L13 EWR",
        spec=EwrGroundObject,
    )
    # EWR has no weapon engagement zone; the Rng/MEZ is blank, detection is shown.
    ewr.max_threat_range.return_value = meters(0)
    ewr.max_detection_range.return_value = nautical_miles(80)
    cards, _ = build_threat_intel_cards(_game([ewr]), _flight())

    assert len(cards) == 1
    card = cards[0]
    assert card.system == "1L13 EWR"
    assert card.mez_nm == "—"
    assert card.detect_nm == "80"
    assert card.harm == "101"
    assert "blind" in card.defeat.lower()


def test_intro_calls_for_recon_only_when_sites_are_unidentified() -> None:
    flight = _flight()
    with_unknowns = ThreatIntelBriefPage(flight, [], 3, False)
    assert "fly TARPS recon to ID" in with_unknowns._intro()
    assert "3 site(s)" in with_unknowns._intro()

    none_unknown = ThreatIntelBriefPage(flight, [], 0, False)
    assert "TARPS" not in none_unknown._intro()


def test_title_includes_custom_name_and_continuation_marker() -> None:
    flight = SimpleNamespace(friendly=object(), callsign="Colt 1", custom_name="Weasel")
    page = ThreatIntelBriefPage(flight, [], 0, False)  # type: ignore[arg-type]
    assert page._title() == 'Colt 1 Threat Intel Brief ("Weasel")'

    cont = ThreatIntelBriefPage(flight, [], 0, False, continued=True)  # type: ignore[arg-type]
    assert cont._title().endswith("(cont.)")
