from typing import Any, cast

from game.theater.supply import (
    RECOVERY_MULTIPLIER,
    SupplyStatus,
    supply_status,
    supply_statuses,
)
from game.theater.transitnetwork import TransitNetwork


class FakeControlPoint:
    """Duck-typed stand-in: supply only reads `has_active_frontline`."""

    def __init__(self, name: str, in_contact: bool) -> None:
        self.name = name
        self.has_active_frontline = in_contact

    def __repr__(self) -> str:
        return self.name


def _cp(name: str, in_contact: bool) -> Any:
    return cast(Any, FakeControlPoint(name, in_contact))


def test_rear_base_supplies_itself() -> None:
    rear = _cp("rear", in_contact=False)
    assert supply_status(rear, TransitNetwork(), coalition_has_rear=True) is (
        SupplyStatus.SUPPLIED
    )


def test_road_route_to_the_rear_is_supplied() -> None:
    front = _cp("front", in_contact=True)
    rear = _cp("rear", in_contact=False)
    network = TransitNetwork()
    network.link_road(front, rear)

    assert supply_status(front, network, coalition_has_rear=True) is (
        SupplyStatus.SUPPLIED
    )


def test_route_through_another_front_base_still_reaches_the_rear() -> None:
    """The rear does not have to be adjacent -- only reachable over ground."""
    front = _cp("front", in_contact=True)
    middle = _cp("middle", in_contact=True)
    rear = _cp("rear", in_contact=False)
    network = TransitNetwork()
    network.link_road(front, middle)
    network.link_road(middle, rear)

    assert supply_status(front, network, coalition_has_rear=True) is (
        SupplyStatus.SUPPLIED
    )


def test_shipping_counts_as_ground_supply() -> None:
    island = _cp("island", in_contact=True)
    rear = _cp("rear", in_contact=False)
    network = TransitNetwork()
    network.link_shipping(island, rear)

    assert supply_status(island, network, coalition_has_rear=True) is (
        SupplyStatus.SUPPLIED
    )


def test_airlift_only_route_is_not_full_supply() -> None:
    """The whole point of rung A.

    TransitNetworkBuilder links every friendly airfield to every other one as a
    last resort, so a gate built on "is there a path" would read SUPPLIED here
    and the feature would do nothing. Cutting the road has to cost something.
    """
    pocket = _cp("pocket", in_contact=True)
    rear = _cp("rear", in_contact=False)
    network = TransitNetwork()
    network.link_airport(pocket, rear)

    assert supply_status(pocket, network, coalition_has_rear=True) is (
        SupplyStatus.AIRLIFTED
    )


def test_losing_the_road_neighbour_downgrades_a_base_that_keeps_its_airfield() -> None:
    """The scenario the feature exists for.

    The road link only exists while the intervening control point is friendly,
    so capturing it removes the road and leaves the airfield-to-airfield link
    the builder adds as a last resort. Same two bases, one rung lower.
    """
    pocket = _cp("pocket", in_contact=True)
    link = _cp("link", in_contact=True)
    rear = _cp("rear", in_contact=False)

    held = TransitNetwork()
    held.link_road(pocket, link)
    held.link_road(link, rear)

    lost = TransitNetwork()
    lost.link_airport(pocket, rear)

    assert supply_status(pocket, held, coalition_has_rear=True) is (
        SupplyStatus.SUPPLIED
    )
    assert supply_status(pocket, lost, coalition_has_rear=True) is (
        SupplyStatus.AIRLIFTED
    )


def test_a_pair_carries_one_link_type_and_road_wins() -> None:
    """`link_with` overwrites, and TransitNetworkBuilder relies on it.

    The builder adds roads first, then only adds shipping or airlift for a pair
    that has no link yet. A test that links a pair twice is modelling something
    the builder cannot produce.
    """
    a = _cp("a", in_contact=True)
    b = _cp("b", in_contact=False)
    network = TransitNetwork()
    network.link_road(a, b)

    assert network.has_link(a, b)
    assert supply_status(a, network, coalition_has_rear=True) is SupplyStatus.SUPPLIED


def test_encircled_base_is_isolated() -> None:
    pocket = _cp("pocket", in_contact=True)
    network = TransitNetwork()

    assert supply_status(pocket, network, coalition_has_rear=True) is (
        SupplyStatus.ISOLATED
    )


def test_pocket_of_front_bases_with_no_rear_link_is_isolated() -> None:
    """Connected to friends, but none of them is a rear area."""
    pocket_a = _cp("pocket_a", in_contact=True)
    pocket_b = _cp("pocket_b", in_contact=True)
    network = TransitNetwork()
    network.link_road(pocket_a, pocket_b)

    assert supply_status(pocket_a, network, coalition_has_rear=True) is (
        SupplyStatus.ISOLATED
    )


def test_campaign_with_no_rear_area_anywhere_is_not_starved() -> None:
    """Every base in contact means there is nothing to model.

    Small campaigns where the whole coalition sits on the line must not have
    their recovery silently zeroed -- that would be a balance change wearing a
    supply rule's clothes.
    """
    front_a = _cp("front_a", in_contact=True)
    front_b = _cp("front_b", in_contact=True)
    network = TransitNetwork()
    network.link_road(front_a, front_b)

    statuses = supply_statuses([front_a, front_b], network)

    assert statuses[front_a] is SupplyStatus.SUPPLIED
    assert statuses[front_b] is SupplyStatus.SUPPLIED


def test_supply_statuses_detects_the_rear_for_the_whole_coalition() -> None:
    front = _cp("front", in_contact=True)
    rear = _cp("rear", in_contact=False)
    encircled = _cp("encircled", in_contact=True)
    network = TransitNetwork()
    network.link_road(front, rear)

    statuses = supply_statuses([front, rear, encircled], network)

    assert statuses[front] is SupplyStatus.SUPPLIED
    assert statuses[rear] is SupplyStatus.SUPPLIED
    # A rear exists, so this one is genuinely cut off rather than degenerate.
    assert statuses[encircled] is SupplyStatus.ISOLATED


def test_recovery_multipliers_only_ever_reduce() -> None:
    """The gate can slow reinforcement, never accelerate it."""
    assert RECOVERY_MULTIPLIER[SupplyStatus.SUPPLIED] == 1.0
    assert 0.0 < RECOVERY_MULTIPLIER[SupplyStatus.AIRLIFTED] < 1.0
    assert RECOVERY_MULTIPLIER[SupplyStatus.ISOLATED] == 0.0
    assert all(0.0 <= value <= 1.0 for value in RECOVERY_MULTIPLIER.values())


def test_every_status_has_a_multiplier() -> None:
    assert set(RECOVERY_MULTIPLIER) == set(SupplyStatus)
