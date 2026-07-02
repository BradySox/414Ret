"""Regression test for Coalition.refund_outstanding_orders' side gate.

``Coalition.player`` is a ``Player`` enum, which is always truthy, so the old
``if self.player and not ...automate_aircraft_reinforcements`` guard skipped the
refund for RED (and any non-blue coalition) whenever the BLUE-intent setting was
off -- the AI never cancelled/refunded its undelivered orders before re-planning
procurement (2026-07-01 audit finding F1; the bug is shared with upstream).

Only the human-managed BLUE coalition should keep its manual orders; the AI
always refunds. Invoked unbound on duck-typed fakes, matching how the existing
Retribution-object fakes are annotated (see CLAUDE-ci.md).
"""

from types import SimpleNamespace
from typing import Any

from game.coalition import Coalition
from game.theater import Player


def _fake_coalition(player: Player, automate: bool) -> Any:
    squadron = SimpleNamespace(refunded=False)

    def refund_orders() -> None:
        squadron.refunded = True

    squadron.refund_orders = refund_orders

    cp = SimpleNamespace(
        ground_unit_orders=SimpleNamespace(refund_all=lambda coalition: None)
    )
    return SimpleNamespace(
        player=player,
        game=SimpleNamespace(
            settings=SimpleNamespace(automate_aircraft_reinforcements=automate),
            theater=SimpleNamespace(control_points_for=lambda player: [cp]),
        ),
        air_wing=SimpleNamespace(iter_squadrons=lambda: [squadron]),
        squadron=squadron,
    )


def test_red_refunds_outstanding_orders_even_with_automation_off() -> None:
    # The AI coalition must always refund; the automation setting only governs
    # the human-managed BLUE side.
    fake = _fake_coalition(Player.RED, automate=False)
    Coalition.refund_outstanding_orders(fake)
    assert fake.squadron.refunded


def test_blue_keeps_manual_orders_when_automation_is_off() -> None:
    fake = _fake_coalition(Player.BLUE, automate=False)
    Coalition.refund_outstanding_orders(fake)
    assert not fake.squadron.refunded


def test_blue_refunds_when_automation_is_on() -> None:
    fake = _fake_coalition(Player.BLUE, automate=True)
    Coalition.refund_outstanding_orders(fake)
    assert fake.squadron.refunded
