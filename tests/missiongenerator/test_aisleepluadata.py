"""Ground-AI-sleep emitter (dcsRetribution.aiSleep) -- the sleepable positive list.

Locks the safety contract the ``aisleep`` plugin depends on: only ``armor``-category
garrison groups with alive vehicles are emitted; the air-defense network, missile
sites, ships and building TGOs are never eligible; and the concealed/map-hidden set
(exactly the COIN / convoy-ambush scripted movers, whose routes a sleeping
controller would kill) is skipped. Gated by ``perf_ground_ai_sleep``.

``perf_aaa_site_sleep`` opens a second, narrower door for short-range gun sites --
the AAA-doctrine perf sink -- guarded by sensor reach and MANTIS ownership. Those
guards are what the second half of this file pins.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.aisleepluadata import (
    AAA_SLEEP_MAX_DETECTION,
    populate_ai_sleep_lua,
)
from game.missiongenerator.luagenerator import LuaData
from game.theater.iadsnetwork.iadsrole import IadsRole
from game.utils import Distance, meters


def _unit(
    alive: bool = True,
    vehicle: bool = True,
    detection: Distance | None = None,
) -> Any:
    unit = SimpleNamespace(alive=alive, is_vehicle=vehicle, is_static=not vehicle)
    if detection is not None:
        unit.detection_range = lambda viewer=None: detection
    return unit


def _tgo(
    category: str,
    group_name: str,
    units: list[Any] | None = None,
    *,
    concealed: bool = False,
    map_hidden: bool = False,
    iads_role: IadsRole = IadsRole.NO_BEHAVIOR,
) -> Any:
    return SimpleNamespace(
        category=category,
        groups=[
            SimpleNamespace(
                group_name=group_name,
                units=units or [_unit()],
                iads_role=iads_role,
            ),
        ],
        concealed=concealed,
        map_hidden=map_hidden,
    )


#: A Vietnam-era gun: reports 5 km, far inside the plugin's 10 NM wake floor.
def _gun(**kwargs: Any) -> Any:
    return _unit(detection=meters(5_000), **kwargs)


#: Anything that genuinely sees at range -- a search/track radar, or a Gepard.
def _radar(**kwargs: Any) -> Any:
    return _unit(detection=meters(160_000), **kwargs)


def _game(tgos: list[Any], *, on: bool = True, aaa: bool = False) -> Any:
    cp = SimpleNamespace(ground_objects=tgos)
    return SimpleNamespace(
        settings=SimpleNamespace(perf_ground_ai_sleep=on, perf_aaa_site_sleep=aaa),
        theater=SimpleNamespace(controlpoints=[cp]),
    )


def _groups(game: Any) -> list[str]:
    root = LuaData("dcsRetribution")
    populate_ai_sleep_lua(root, game)
    node = root.get_item("aiSleep")
    if node is None:
        return []
    values = node.value
    assert isinstance(values, list) and len(values) == 1
    assert values[0].key == "groups"
    return list(values[0].value)


def test_emits_each_live_garrison_group() -> None:
    a = _tgo("armor", "0100 | Garrison A")
    b = _tgo("armor", "0101 | Garrison B")
    assert _groups(_game([a, b])) == ["0100 | Garrison A", "0101 | Garrison B"]


def test_never_emits_air_defense_missiles_ships_or_buildings() -> None:
    sam = _tgo("aa", "0102 | SA-6")
    ewr = _tgo("ewr", "0103 | EWR")
    scud = _tgo("missile", "0104 | SCUD")
    coastal = _tgo("coastal", "0105 | Silkworm")
    ship = _tgo("ship", "0106 | Grisha")
    ammo = _tgo("ammo", "0107 | Cache", [_unit(vehicle=False)])
    motorpool = _tgo("motorpool", "0108 | Depot")
    assert _groups(_game([sam, ewr, scud, coastal, ship, ammo, motorpool])) == []


def test_skips_the_scripted_movers_concealed_and_map_hidden() -> None:
    cell = _tgo("armor", "0109 | COIN cell", concealed=True)
    ambush = _tgo("armor", "0110 | Ambush team", map_hidden=True)
    plain = _tgo("armor", "0111 | Garrison")
    assert _groups(_game([cell, ambush, plain])) == ["0111 | Garrison"]


def test_skips_dead_and_statics_only_groups() -> None:
    dead = _tgo("armor", "0112 | Dead garrison", [_unit(alive=False)])
    statics = _tgo("armor", "0113 | Revetments", [_unit(vehicle=False)])
    assert _groups(_game([dead, statics])) == []


def test_gated_off_by_the_setting() -> None:
    garrison = _tgo("armor", "0114 | Garrison")
    assert _groups(_game([garrison], on=False)) == []


def test_no_eligible_groups_emits_no_node() -> None:
    root = LuaData("dcsRetribution")
    populate_ai_sleep_lua(root, _game([]))
    assert root.get_item("aiSleep") is None


class TestAaaSiteSleep:
    """``perf_aaa_site_sleep``: the gun sites, and only the ones that can't see far.

    The safety argument is that a gun whose detection range is well inside the
    plugin's wake radius is switched back on long before anything reaches the edge
    of its own sensor envelope -- so its IADS contribution and its trigger moment
    are unchanged, and only the frame time moves. Every guard below exists to keep
    a unit that *can* see at range from ever being switched off.
    """

    def test_short_range_gun_site_sleeps_when_enabled(self) -> None:
        battery = _tgo("aa", "0200 | AAA site", [_gun(), _gun()])
        assert _groups(_game([battery], aaa=True)) == ["0200 | AAA site"]

    def test_gun_site_stays_awake_while_the_toggle_is_off(self) -> None:
        battery = _tgo("aa", "0201 | AAA site", [_gun()])
        assert _groups(_game([battery], aaa=False)) == []

    def test_one_far_seeing_unit_keeps_the_whole_group_awake(self) -> None:
        """A gun site with a radar attached is a radar site; the group is the unit
        of sleep, so a single long-sighted member vetoes the lot."""
        mixed = _tgo("aa", "0202 | Guns + radar", [_gun(), _gun(), _radar()])
        assert _groups(_game([mixed], aaa=True)) == []

    def test_detection_exactly_at_the_threshold_still_sleeps(self) -> None:
        edge = _tgo("aa", "0203 | Edge", [_unit(detection=AAA_SLEEP_MAX_DETECTION)])
        assert _groups(_game([edge], aaa=True)) == ["0203 | Edge"]

    def test_a_metre_over_the_threshold_stays_awake(self) -> None:
        over = _tgo(
            "aa",
            "0204 | Over",
            [_unit(detection=AAA_SLEEP_MAX_DETECTION + meters(1))],
        )
        assert _groups(_game([over], aaa=True)) == []

    def test_unknown_detection_range_stays_awake(self) -> None:
        """Fail safe: a unit we can't measure is assumed to see, not assumed blind."""
        unknown = _tgo("aa", "0205 | Mystery", [_unit()])
        assert _groups(_game([unknown], aaa=True)) == []

    def test_dedicated_early_warning_sites_are_never_eligible(self) -> None:
        """Even a hypothetical short-sighted EWR: the category is the whole point of
        the site, and `ewr` is deliberately absent from the eligible set."""
        ewr = _tgo("ewr", "0206 | EWR", [_gun()])
        assert _groups(_game([ewr], aaa=True)) == []

    def test_roles_mantis_drives_are_never_slept(self) -> None:
        """MANTIS writes alarm state / EMCON to these; a switched-off controller
        would fight it, however short-sighted the guns are."""
        for role in (IadsRole.SAM, IadsRole.SAM_AS_EWR, IadsRole.POINT_DEFENSE):
            site = _tgo("aa", f"0207 | {role.value}", [_gun()], iads_role=role)
            assert _groups(_game([site], aaa=True)) == [], role

    def test_ewr_role_gun_site_is_eligible(self) -> None:
        """MANTIS only *reads* detection from EWR-role nodes, and a 5 km gun has
        nothing to contribute at the wake radius -- this is the case that carries
        the win on an AAA-doctrine campaign."""
        site = _tgo("aa", "0208 | Flak belt", [_gun()], iads_role=IadsRole.EWR)
        assert _groups(_game([site], aaa=True)) == ["0208 | Flak belt"]

    def test_concealed_gun_site_is_still_skipped(self) -> None:
        hidden = _tgo("aa", "0209 | Hidden", [_gun()], concealed=True)
        assert _groups(_game([hidden], aaa=True)) == []

    def test_armor_still_sleeps_alongside_the_guns(self) -> None:
        garrison = _tgo("armor", "0210 | Garrison")
        battery = _tgo("aa", "0211 | AAA site", [_gun()])
        assert _groups(_game([garrison, battery], aaa=True)) == [
            "0210 | Garrison",
            "0211 | AAA site",
        ]

    def test_master_toggle_off_beats_the_aaa_toggle(self) -> None:
        battery = _tgo("aa", "0212 | AAA site", [_gun()])
        assert _groups(_game([battery], on=False, aaa=True)) == []

    def test_the_toggle_widens_nothing_but_gun_sites(self) -> None:
        """Regression guard for the categories the AAA door must NOT open. The
        missile/coastal sites in particular are the mobilemissiles scoot movers
        (§49), whose routes a sleeping controller would kill -- and their launchers
        report a detection range of 0, so only the category check stops them."""
        scud = _tgo("missile", "0213 | SCUD", [_gun()])
        coastal = _tgo("coastal", "0214 | Silkworm", [_gun()])
        ship = _tgo("ship", "0215 | Grisha", [_gun()])
        motorpool = _tgo("motorpool", "0216 | Depot", [_gun()])
        assert _groups(_game([scud, coastal, ship, motorpool], aaa=True)) == []
