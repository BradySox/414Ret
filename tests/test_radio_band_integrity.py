"""Radio band integrity for airframes whose radios cannot reach the UHF band.

Retribution allocates every inter-flight frequency -- departure ATC, AWACS,
JTAC, the package frequency, tankers, divert ATC -- out of a hardcoded 225-400
MHz UHF band (``RadioRegistry.alloc_uhf``), and allocates a player-crewed
flight's intra-flight channel from the airframe's own ``intra_flight`` radio
(``AircraftType.alloc_flight_radio``). Both assume the aircraft can actually
tune what it is handed. Most modern jets carry a UHF set, so this holds; a
handful of airframes do not, and each needs its data to say so honestly.

The established engine convention for a narrow-band airframe is to route
presets to a radio that can tune them, or -- where none can -- to decline the
assignment entirely. ``FarmerRadioChannelAllocator`` states it outright: "The
Farmer only has 6 preset channels. It also only has a VHF radio, and currently
our ATC data and AWACS are only in the UHF band." ``SCR522RadioChannelAllocator``
and ``ARC5RadioChannelAllocator`` likewise assign intra-flight plus ATC and
deliberately never assign the package frequency.

These tests pin the two airframes that were getting it wrong. Assertions are on
*bands* and *radio indices*, never on radio display names -- any entry covering
the right band is correct.
"""

from __future__ import annotations

import pytest

from game import persistency
from game.dcs.aircrafttype import AircraftType
from game.radio.channels import CommonRadioChannelAllocator
from game.radio.radios import MHz, RadioRegistry

#: The band alloc_uhf() draws every inter-flight frequency from.
UHF_LO = MHz(225)
UHF_HI = MHz(400)

#: The band the Grinnelli F-22A mod's HumanRadio block actually models.
F22A_LO = MHz(100)
F22A_HI = MHz(156)


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    # Aircraft data loading reads from the DCS saved-game folder, which is only
    # configured once the app boots. Point it at an empty temp dir so loading
    # falls back to the bundled resources/ definitions.
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


# ---------------------------------------------------------------------------
# F-22A -- intra-flight channel must stay inside the mod's VHF radio.
#
# The yaml used to declare the P-51's SCR-522, with an in-tree comment doubting
# it. The name was wrong; the band was not. The mod's own F-22A.lua declares
#
#     HumanRadio = { frequency = 127.5, editable = true,
#                    minFrequency = 100.000, maxFrequency = 156.000,
#                    modulation = MODULATION_AM }
#
# so the modelled cockpit tunes 100-156 MHz AM and nothing else. Repointing to
# the realistic AN/ARC-210 breaks the jet rather than fixing it: random_frequency
# only ever draws from ranges[0], which is 225-400 MHz for the ARC-210, so a
# player F-22A would spawn tuned to a frequency its radio cannot reach.
# ---------------------------------------------------------------------------


@pytest.fixture(name="f22a")
def f22a_fixture() -> AircraftType:
    return AircraftType.named("F-22A Raptor")


def test_f22a_intra_flight_radio_matches_the_mod_band(f22a: AircraftType) -> None:
    radio = f22a.intra_flight_radio
    assert radio is not None, "F-22A lost its intra_flight radio"
    for rng in radio.ranges:
        assert rng.minimum.hertz >= F22A_LO.hertz
        assert rng.maximum.hertz <= F22A_HI.hertz


def test_f22a_allocations_are_tunable_in_the_cockpit(f22a: AircraftType) -> None:
    # alloc_flight_radio is only consulted for player-crewed flights, which is
    # exactly the case that would be broken by a UHF radio here.
    registry = RadioRegistry()
    for _ in range(200):
        freq = f22a.alloc_flight_radio(registry)
        assert F22A_LO.hertz <= freq.hertz < F22A_HI.hertz


# ---------------------------------------------------------------------------
# CH-47F Block I -- inter-flight presets must land on the UHF radio.
#
# pydcs gives the Chinook three radios: 1 is VHF-FM (presets 30-79 MHz), 2 is
# UHF (presets 250-305 MHz), 3 is the narrow FM homing radio. The yaml pointed
# inter_flight_radio_index at radio 1, so every inter-flight preset was written
# to a set that cannot tune any of them while the UHF radio went unused.
# ---------------------------------------------------------------------------


@pytest.fixture(name="chinook")
def chinook_fixture() -> AircraftType:
    return AircraftType.named("CH-47F Block I")


def _preset_band(aircraft: AircraftType, radio_id: int) -> tuple[float, float]:
    """Returns the (min, max) default preset frequency in MHz for a radio."""
    panel_radio = aircraft.dcs_unit_type.panel_radio
    assert panel_radio is not None, f"{aircraft} has no panel_radio"
    channels = panel_radio[radio_id]["channels"]
    return min(channels.values()), max(channels.values())


def test_chinook_inter_flight_presets_go_to_the_uhf_radio(
    chinook: AircraftType,
) -> None:
    allocator = chinook.channel_allocator
    assert isinstance(allocator, CommonRadioChannelAllocator)
    radio_id = allocator.inter_flight_radio_index
    assert radio_id is not None

    # The radio the inter-flight presets land on must cover the band alloc_uhf
    # hands out, judged by that radio's own default presets.
    low, high = _preset_band(chinook, radio_id)
    assert low >= UHF_LO.mhz, f"radio {radio_id} presets start at {low} MHz, below UHF"
    assert high <= UHF_HI.mhz, f"radio {radio_id} presets reach {high} MHz, above UHF"


def test_chinook_intra_flight_stays_on_the_fm_radio(chinook: AircraftType) -> None:
    # The intra-flight channel is allocated from the airframe's own radio, so it
    # is free to stay on the VHF-FM set -- but it must not collide with the
    # inter-flight radio, or _assign_sequential starts inter presets at 2.
    allocator = chinook.channel_allocator
    assert isinstance(allocator, CommonRadioChannelAllocator)
    assert allocator.intra_flight_radio_index == 1
    assert allocator.inter_flight_radio_index != 1

    radio = chinook.intra_flight_radio
    assert radio is not None
    registry = RadioRegistry()
    for _ in range(100):
        freq = chinook.alloc_flight_radio(registry)
        assert any(
            rng.minimum.hertz <= freq.hertz < rng.maximum.hertz for rng in radio.ranges
        ), f"{freq} is outside the CH-47F's intra-flight radio"
