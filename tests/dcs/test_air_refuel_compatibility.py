"""Tests for AircraftType air-to-air refueling compatibility (can_refuel_from).

The compatibility check is intentionally permissive: an untagged receiver or an
untagged tanker is always compatible so the boom/probe restriction is opt-in and
never regresses campaigns whose aircraft data hasn't been classified yet.
"""

from types import SimpleNamespace

from game.dcs.aircrafttype import AircraftType, AirRefuelType


def _receiver(
    air_refuel_type: object = None, helicopter: bool = False
) -> SimpleNamespace:
    return SimpleNamespace(air_refuel_type=air_refuel_type, helicopter=helicopter)


def _tanker(
    provides: frozenset[AirRefuelType] = frozenset(), helicopters: bool = False
) -> SimpleNamespace:
    return SimpleNamespace(
        tanker_refuel_types=provides, tanker_refuels_helicopters=helicopters
    )


def _can_refuel(receiver: object, tanker: object) -> bool:
    # Call the unbound method so we can pass lightweight duck-typed stand-ins instead
    # of building a fully-populated frozen AircraftType.
    return AircraftType.can_refuel_from(receiver, tanker)  # type: ignore[arg-type]


def test_untagged_receiver_is_compatible_with_anything() -> None:
    assert _can_refuel(_receiver(None), _tanker(frozenset({AirRefuelType.BOOM})))


def test_tagged_receiver_is_compatible_with_untagged_tanker() -> None:
    # A tanker that advertises no methods is treated permissively (legacy behavior).
    assert _can_refuel(_receiver(AirRefuelType.BOOM), _tanker(frozenset()))


def test_boom_receiver_matches_boom_tanker_only() -> None:
    boom = _receiver(AirRefuelType.BOOM)
    assert _can_refuel(boom, _tanker(frozenset({AirRefuelType.BOOM})))
    assert not _can_refuel(boom, _tanker(frozenset({AirRefuelType.PROBE})))


def test_probe_receiver_matches_probe_tanker_only() -> None:
    probe = _receiver(AirRefuelType.PROBE)
    assert _can_refuel(probe, _tanker(frozenset({AirRefuelType.PROBE})))
    assert not _can_refuel(probe, _tanker(frozenset({AirRefuelType.BOOM})))


def test_multi_method_tanker_serves_both() -> None:
    both = _tanker(frozenset({AirRefuelType.BOOM, AirRefuelType.PROBE}))
    assert _can_refuel(_receiver(AirRefuelType.BOOM), both)
    assert _can_refuel(_receiver(AirRefuelType.PROBE), both)


def test_helicopter_needs_a_slow_capable_tanker() -> None:
    helo = _receiver(AirRefuelType.PROBE, helicopter=True)
    # A fast drogue tanker (e.g. KC-135 MPRS) can't service a helo...
    assert not _can_refuel(helo, _tanker(frozenset({AirRefuelType.PROBE})))
    # ...but a slow-capable one (e.g. KC-130) can.
    assert _can_refuel(
        helo, _tanker(frozenset({AirRefuelType.PROBE}), helicopters=True)
    )
