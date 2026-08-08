"""§88 — kill-tracking proxies on map-scenery strike targets.

The scenery kill path that ships today hangs on DCS's MapObjectIsDead condition,
which the sim evaluates against the terrain and which fails in ways Retribution
cannot see (map updates, non-destructible objects, ED's 2.9.7 scenery
S_EVENT_DEAD regression). The proxy is a real, registered static whose death is
name-matched at debrief exactly like a spawned building.

What these pin, and what breaks if the code drifts:

* The proxy is registered in the unit map. Drop the registration and the kill
  lands in `debriefing.py`'s `untracked` bucket and vanishes — the exact failure
  `generate_iads_command_unit` already has (notes doc §3.3).
* The proxy's DCS unit name does not collide with the IADS soldier's. Name the
  group `unit.unit_name` instead of `"... proxy"` and `add_theater_unit_mapping`
  raises on a C2 scenery node.
* The MapObjectIsDead trigger is still generated. The two are a union; replacing
  the trigger rather than adding to it would be a regression.
* A dead scenery unit gets no proxy. A proxy spawned dead can never fire an
  event, so it would be pure clutter on a worn-down campaign.

The culling exemption — a culled proxy loses the kill for the same reason a
culled trigger zone does — is pinned in `tests/test_culling.py`, which owns that
contract for the whole scenery apparatus.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from dcs.statics import Fortification

from game.missiongenerator.tgogenerator import GroundObjectGenerator
from game.theater.theatergroup import SceneryUnit
from game.utils import Heading


def _scenery_unit(*, alive: bool = True, unit_id: int = 123) -> SceneryUnit:
    """A SceneryUnit without its heavy __init__ (which needs a live TGO graph)."""
    unit = object.__new__(SceneryUnit)
    unit.id = unit_id
    unit.name = "Power Plant"
    unit.alive = alive
    # is_static reads .type before the SceneryUnit isinstance check. Any
    # StaticType does; this is not the proxy's type.
    unit.type = Fortification.Workshop_A
    unit.position = SimpleNamespace(  # type: ignore[assignment]
        x=1000.0, y=2000.0, heading=Heading.from_degrees(45)
    )
    return unit


def _generator(*, proxies: bool = True, mantis: bool = False) -> Any:
    game = SimpleNamespace(
        settings=SimpleNamespace(
            scenery_kill_proxies=proxies,
            plugin_option=lambda name: mantis,
        ),
        iads_considerate_culling=lambda tgo: False,
    )
    gen = GroundObjectGenerator(None, None, game, None, None)  # type: ignore[arg-type]
    gen.m = MagicMock()
    gen.country = MagicMock()
    gen.unit_map = MagicMock()
    return gen


def _spawned_kwargs(gen: Any) -> dict[str, Any]:
    return gen.m.static_group.call_args.kwargs


def test_proxy_is_a_hidden_power_box_at_the_scenery_position() -> None:
    gen = _generator()
    unit = _scenery_unit()

    gen.generate_scenery_kill_proxy(unit)

    kwargs = _spawned_kwargs(gen)
    assert kwargs["_type"] is Fortification.Electric_power_box
    assert kwargs["position"] is unit.position
    assert kwargs["heading"] == 45
    # Bookkeeping, not scenery: the objective already draws its own F10 zone.
    assert kwargs["hidden"] is True


def test_proxy_name_does_not_collide_with_the_iads_stand_in() -> None:
    gen = _generator()
    unit = _scenery_unit()

    gen.generate_scenery_kill_proxy(unit)

    # pydcs names the unit "<group name> object", so the group name has to differ
    # from generate_iads_command_unit's, which is unit_name verbatim.
    assert _spawned_kwargs(gen)["name"] == "0123 | Power Plant proxy"
    assert _spawned_kwargs(gen)["name"] != unit.unit_name


def test_proxy_is_registered_in_the_unit_map() -> None:
    gen = _generator()
    unit = _scenery_unit()

    gen.generate_scenery_kill_proxy(unit)

    spawned = gen.m.static_group.return_value
    gen.unit_map.add_theater_unit_mapping.assert_called_once_with(
        unit, spawned.units[0]
    )


def test_dead_scenery_unit_gets_no_proxy() -> None:
    gen = _generator()

    gen.generate_scenery_kill_proxy(_scenery_unit(alive=False))

    gen.m.static_group.assert_not_called()
    gen.unit_map.add_theater_unit_mapping.assert_not_called()


def _generate_with_one_scenery_unit(gen: Any, unit: SceneryUnit) -> None:
    gen.ground_object = SimpleNamespace(
        groups=[SimpleNamespace(units=[unit], group_name="Power Plant")]
    )
    gen.add_trigger_zone_for_scenery = MagicMock()
    gen.generate()


def test_generate_spawns_a_proxy_when_the_setting_is_on() -> None:
    gen = _generator(proxies=True)
    gen.generate_scenery_kill_proxy = MagicMock()
    unit = _scenery_unit()

    _generate_with_one_scenery_unit(gen, unit)

    gen.generate_scenery_kill_proxy.assert_called_once_with(unit)
    # Union, not replacement: the terrain-evaluated trigger still goes in.
    gen.add_trigger_zone_for_scenery.assert_called_once_with(unit)


def test_generate_skips_the_proxy_when_the_setting_is_off() -> None:
    gen = _generator(proxies=False)
    gen.generate_scenery_kill_proxy = MagicMock()
    unit = _scenery_unit()

    _generate_with_one_scenery_unit(gen, unit)

    gen.generate_scenery_kill_proxy.assert_not_called()
    gen.add_trigger_zone_for_scenery.assert_called_once_with(unit)
