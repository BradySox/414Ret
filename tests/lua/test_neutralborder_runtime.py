"""Headless runtime checks for the neutralborder plugin (§98).

Pins the "script errors and the feature silently never starts" invariant plus
the behaviour contract of the border watch: a group inside the polygon below the
floor is warned and shadowed (the shadow spawning on the intruder's OPPOSING
coalition at return-fire); a player who stays past the engage dwell, or who
releases a weapon inside the border after the warning, is engaged via a hard
AttackGroup task on the raw controller and the SAM template wakes; AI intruders
are shadowed but never engaged; a high transit trips nothing; leaving before
escalation stands the shadow down. The DCS AI's actual shadow/attack flying is
in-game-only (checklist B120/B121).
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/neutralborder/neutralborder-config.lua"

RED_COUNTRY = 34
BLUE_COUNTRY = 2

# A 20 km square with the neutral field at its center. Vertices are terrain XY
# strings, the emitter contract (the plugin tonumber()s everything).
SQUARE = [
    {"x": "0", "y": "0"},
    {"x": "20000", "y": "0"},
    {"x": "20000", "y": "20000"},
    {"x": "0", "y": "20000"},
]


def _config(
    battery: bool = True, floor_ft: str = "10000", engage_ai: bool = False
) -> dict[str, Any]:
    zone: dict[str, Any] = {
        "country": "Lebanon",
        "field": "Rayak",
        "floorFt": floor_ft,
        "redCountryId": str(RED_COUNTRY),
        "blueCountryId": str(BLUE_COUNTRY),
        "border": SQUARE,
        # Where the F10 map writes the country's name. The emitter takes it
        # from the polygon's representative point; the square's is its middle.
        "labelX": "10000",
        "labelZ": "10000",
        # What the emitter actually sends for a defending zone. It used to name
        # the alert field; nothing launches from one since 2026-09-09.
        "originLabel": "surface-to-air batteries inside the border",
        # Refuses both sides: this fixture is the interception case.
        "overflightBlue": "false",
        "overflightRed": "false",
    }
    if battery:
        zone["samGroups"] = [{"name": SAM_GROUP}]
    return {
        "plugins": {
            "neutralborder": {
                "warnDwellS": 30,
                "engageDwellS": 180,
                "scanIntervalS": 10,
                "vectorIntervalS": 45,
                "maxShadows": 2,
                "drawBorders": False,
                "engageAi": engage_ai,
            }
        },
        "neutralBorder": {"zones": [zone]},
    }


def _intruder(
    name: str,
    gid: int,
    side: int,
    player: str | None = "Brady",
    x: float = 5000,
    z: float = 5000,
    alt: float = 2000,
) -> dict[str, Any]:
    return {
        "name": name,
        "id": gid,
        "side": side,
        "category": 0,  # AIRPLANE
        "units": [
            {
                "name": name + "-1",
                "type": "FA-18C_hornet",
                "x": x,
                "z": z,
                "alt": alt,
                "airborne": True,
                "playerName": player,
            }
        ],
    }


#: The standing battery's group name, matching the generator's
#: ``NeutralBorder|<country>|<system>``. It is a LIVE group from mission start,
#: not a template -- the plugin swaps its coalition rather than cloning it.
SAM_GROUP = "NeutralBorder|Lebanon|SA-3"


def _setup(cfg: dict[str, Any], with_battery: bool = True) -> DcsPluginHarness:
    h = DcsPluginHarness()
    h.add_airbase({"name": "Rayak", "x": 10000, "z": 10000, "elev": 900, "side": 0})
    if with_battery:
        # On the ground, on the NEUTRAL coalition from the start, deep inside
        # the border. Side 0 is neutral, which is why it cannot fire until
        # swapped. Category 2 is GROUND, so the airborne scan never sees it.
        h.add_group(
            {
                "name": SAM_GROUP,
                "id": 900,
                "side": 0,
                "category": 2,
                "units": [
                    {
                        "name": SAM_GROUP + "-1",
                        "type": "p-19 s-125 sr",
                        "x": 10000,
                        "z": 10000,
                        "alt": 900,
                        "airborne": False,
                    }
                ],
            }
        )
    h.lua.globals().dcsRetribution = h.to_lua(cfg)
    return h


def _swaps(h: DcsPluginHarness) -> list[dict[str, Any]]:
    """Coalition swaps: the only way a neutral battery ever becomes able to fire."""
    return [r for r in h.records("coalitionSwaps") if isinstance(r, dict)]


def _texts(h: DcsPluginHarness) -> list[str]:
    return [str(r.get("text", "")) for r in h.records("texts") if isinstance(r, dict)]


def _hails(h: DcsPluginHarness) -> list[str]:
    """The entry call -- what says the border noticed you."""
    return [t for t in _texts(h) if "violating" in t]


def _advisories(h: DcsPluginHarness) -> list[str]:
    """The second call at warnDwellS -- the last warning before the swap."""
    return [t for t in _texts(h) if "tracking you" in t]


def _sam_spawns(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return [r for r in h.records("spawns") if r.get("base") == "template"]


def _attack_tasks(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return [
        r
        for r in h.records("controllerTasks")
        if isinstance(r, dict) and r.get("taskId") == "AttackGroup"
    ]


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.set_retribution_config(plugin_options={"neutralborder": {"warnDwellS": 30}})
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    assert h.records("spawns") == []
    h.assert_no_lua_errors()


def test_a_blue_player_is_warned_and_nothing_is_launched() -> None:
    """The patrol is already flying. Crossing gets you talked to, not chased.

    Scrambling was tried and measured 2026-08-28/29: 270 s cold, still behind
    from a runway start, and unable to hold a standoff once airborne because the
    closing geometry belongs to the intruder. Nothing is spawned here now.
    """
    h = _setup(_config())
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(45)

    assert _hails(h), "no radio call on entry"
    assert _advisories(h), "the second call never came at the dwell"
    # Nothing has become hostile yet: no swap, no attack task, no SAM.
    assert _swaps(h) == [], "the patrol turned hostile before the engage dwell"
    assert _attack_tasks(h) == []
    assert _sam_spawns(h) == []
    h.assert_no_lua_errors()


def test_the_patrol_swaps_onto_the_side_opposing_the_intruder() -> None:
    """A neutral cannot fire, so engaging means changing which side it is on --
    the coalition OPPOSING whoever violated."""
    h = _setup(_config())
    h.add_group(_intruder("Viper 1-1", 42, side=2))  # BLUE intruder
    h.load_plugin_script(PLUGIN)
    h.advance_to(200)

    swaps = _swaps(h)
    assert len(swaps) == 1, "the patrol did not swap on escalation"
    assert swaps[0]["group"] == SAM_GROUP
    assert swaps[0]["coalitionId"] == 1, "a BLUE intruder must be opposed by RED"
    assert swaps[0]["countryId"] == RED_COUNTRY
    assert swaps[0]["reset"] is True, (
        "Respawn must be told to copy the live positions -- without Reset the "
        "patrol teleports back to where it started the mission"
    )
    h.assert_no_lua_errors()


def test_a_zone_with_no_patrol_says_so_instead_of_going_quiet() -> None:
    """If the standing group is missing or dead there is nothing to swap, and a
    silent return would look exactly like a ladder that never ran."""
    h = _setup(_config(), with_battery=False)
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(200)

    assert _swaps(h) == []
    assert _hails(h), "the border should still talk even with no patrol up"
    h.assert_no_lua_errors()


def test_player_dwell_turns_the_battery_hostile() -> None:
    """The swap IS the escalation: a true neutral cannot fire, so nothing else
    the plugin does matters until the battery stops being one."""
    h = _setup(_config())
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(200)

    swaps = _swaps(h)
    assert len(swaps) == 1, "the standing battery never swapped"
    assert swaps[0]["coalitionId"] == 1, "the battery joined the escalator's own side"
    roe = [r for r in h.records("roe") if isinstance(r, dict)]
    assert any(r.get("option") == "WeaponFree" for r in roe)
    # No attack task, and none is wanted -- a SAM acquires for itself.
    assert _attack_tasks(h) == []
    h.assert_no_lua_errors()


def test_an_ai_intruder_earns_nothing_by_default() -> None:
    """DM call: only a human earns the attack. An AI that strays draws no radio
    call either -- both gates read one predicate, so neither can drift from the
    other. `engageAi` lifts this for testing; see the override tests below."""
    h = _setup(_config())
    h.add_group(_intruder("Strike 9-1", 60, side=2, player=None))
    h.load_plugin_script(PLUGIN)
    h.advance_to(400)

    assert _swaps(h) == [], "an AI intruder turned a neutral country hostile"
    assert _hails(h) == [], "an AI intruder was hailed"
    roe = [r for r in h.records("roe") if isinstance(r, dict)]
    assert not any(r.get("option") == "WeaponFree" for r in roe)
    assert _attack_tasks(h) == []
    assert _sam_spawns(h) == []
    h.assert_no_lua_errors()


def test_high_transit_above_the_floor_trips_nothing() -> None:
    """Only a floored (contested) zone grants a safe altitude."""
    cfg = _config()
    cfg["neutralBorder"]["zones"][0]["floorBlueFt"] = "10000"
    cfg["neutralBorder"]["zones"][0]["floorRedFt"] = "10000"
    h = _setup(cfg)
    # 10,000 ft floor = 3048 m; the transit crosses at 5000 m.
    h.add_group(_intruder("Heavy 7-1", 70, side=2, alt=5000))
    h.load_plugin_script(PLUGIN)
    h.advance_to(400)

    assert h.records("spawns") == []
    h.assert_no_lua_errors()


def test_weapon_release_inside_escalates_after_warning() -> None:
    h = _setup(_config())
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(45)  # warned + shadowed, not yet engaged
    assert _attack_tasks(h) == []

    h.fire_shot(
        {
            "weapon": {
                "typeName": "AGM-65D",
                "x": 5000,
                "z": 5000,
                "alt": 2000,
                "velocity": 300,
                "vanishAt": 999,
            },
            "initiator": "Viper 1-1",
        }
    )
    h.advance_to(60)

    assert len(_swaps(h)) == 1, "a weapon released inside did not turn the battery"
    h.assert_no_lua_errors()


def test_leaving_before_escalation_costs_you_nothing() -> None:
    """Turn round in time and the border forgets you. There is no recall to do:
    the patrol never left its orbit, which is why it can be forgotten cheaply."""
    h = _setup(_config())
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(45)
    assert _hails(h), "the border never noticed the crossing"

    h.update_unit("Viper 1-1", {"x": 90000, "z": 90000})
    h.advance_to(45 + 130 + 10)  # exit grace (120 s) + a scan

    assert _swaps(h) == [], "the patrol went hostile over someone who left"
    assert _attack_tasks(h) == []
    assert _sam_spawns(h) == []
    h.assert_no_lua_errors()


def _consent_run(blue_may_cross: bool) -> "DcsPluginHarness":
    cfg = _config()
    zone = cfg["neutralBorder"]["zones"][0]
    zone["overflightBlue"] = "true" if blue_may_cross else "false"
    zone["overflightRed"] = "false" if blue_may_cross else "true"
    h = _setup(cfg)
    h.add_group(_intruder("Viper 1-1", 42, side=2))  # the BLUE player
    h.load_plugin_script(PLUGIN)
    h.advance_to(60)
    return h


def test_a_side_that_is_permitted_transit_is_never_challenged() -> None:
    """Per-side consent: a country open to blue and closed to red waves one
    through and challenges the other. Turkey in 2022 is exactly this.

    Tested from both sides of the same border rather than with two intruders:
    with a standing patrol and AI-never-engaged, a refused AI produces no
    observable at all, so only the player's own consent is visible.
    """
    assert not _hails(
        _consent_run(blue_may_cross=True)
    ), "a side the country lets through was challenged anyway"
    assert _hails(
        _consent_run(blue_may_cross=False)
    ), "a side the country refuses was waved through"


def test_a_zone_open_to_everyone_never_scans() -> None:
    cfg = _config(battery=False)
    zone = cfg["neutralBorder"]["zones"][0]
    zone["overflightBlue"] = "true"
    zone["overflightRed"] = "true"

    h = _setup(cfg)
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(400)

    assert h.records("spawns") == []
    assert _attack_tasks(h) == []
    h.assert_no_lua_errors()


def test_a_zone_with_no_floor_intercepts_at_any_altitude() -> None:
    """ "If they are hostile then they are hostile" (DM, 2026-08-25). A floor
    means high transit is tolerated; a closed country grants no such height, so
    a zone emitted without one must trip a transit at any altitude."""
    h = _setup(_config())  # the fixture emits no floorBlueFt/floorRedFt
    h.add_group(_intruder("Heavy 7-1", 70, side=2, alt=9000))  # ~30,000 ft
    h.load_plugin_script(PLUGIN)
    h.advance_to(60)

    assert _hails(h), "a closed border let a high transit pass unremarked"
    h.assert_no_lua_errors()


def test_the_warning_does_not_offer_an_altitude_that_does_not_exist() -> None:
    """A floorless zone must not radio 'climb above it' -- there is no above."""
    h = _setup(_config())
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(45)

    texts = [str(r.get("text", "")) for r in h.records("texts") if isinstance(r, dict)]
    warned = [t for t in texts if "violating" in t]
    assert warned, "no warning was issued"
    assert not any("below" in t or "Climb" in t for t in warned)
    h.assert_no_lua_errors()


def test_one_sides_floor_is_never_applied_to_the_other() -> None:
    """A per-side floor is two facts, and `cond and a or b` cannot carry them.

    Every other floor test sets floorBlueFt and floorRedFt to the SAME value,
    which is why this survived: the Lua read
    `is_blue and zone.floor_blue_m or zone.floor_red_m`, and when blue's floor
    is nil -- the no-safe-altitude case, and the common one -- that idiom falls
    straight through to RED's floor. Blue would then be judged against a height
    nobody authored for it.

    Here blue has no floor (trip at any altitude) and red has a high one. The
    blue transit is well above red's floor, so if red's number leaks across,
    nothing launches.
    """
    cfg = _config()
    cfg["neutralBorder"]["zones"][0]["floorRedFt"] = "10000"  # blue's stays unset
    h = _setup(cfg)
    h.add_group(_intruder("Viper 1-1", 42, side=2, alt=9000))  # ~30,000 ft
    h.load_plugin_script(PLUGIN)
    h.advance_to(60)

    assert _hails(h), "blue was judged against RED's floor"
    h.assert_no_lua_errors()


def test_the_warning_quotes_this_sides_floor_not_the_other_sides() -> None:
    """The radio call is the same bug's user-visible face: a blue player with no
    floor must not be told to climb above a number that is red's."""
    cfg = _config()
    cfg["neutralBorder"]["zones"][0]["floorRedFt"] = "10000"
    h = _setup(cfg)
    h.add_group(_intruder("Viper 1-1", 42, side=2, alt=9000))
    h.load_plugin_script(PLUGIN)
    h.advance_to(45)

    texts = [str(r.get("text", "")) for r in h.records("texts") if isinstance(r, dict)]
    warned = [t for t in texts if "violating" in t]
    assert warned, "no warning was issued"
    assert not any(
        "below" in t or "Climb" in t for t in warned
    ), "the warning offered blue a safe altitude taken from red's floor"
    h.assert_no_lua_errors()


# -- the F10 draw --------------------------------------------------------------


def _drawn(cfg: dict[str, Any]) -> DcsPluginHarness:
    cfg["plugins"]["neutralborder"]["drawBorders"] = True
    h = _setup(cfg)
    h.load_plugin_script(PLUGIN)
    return h


def test_the_border_is_filled_by_triangles_not_by_the_freeform() -> None:
    """DCS draws a concave freeform's outline and refuses its fill, and a
    national border is about as concave as a shape gets -- every zone came out a
    bare line on the Iraq map. The fill is MOOSE's triangulation; the freeform
    carries only the outline, and must ask for no fill of its own."""
    h = _drawn(_config())
    fills = h.records("zoneFills")
    assert len(fills) == 1, "the border was never filled"
    assert fills[0]["alpha"] > 0
    assert fills[0]["coalition"] == -1, "fill must be visible to both sides"
    assert len(fills[0]["points"]) == len(SQUARE)
    outlines = [r for r in h.records("markups") if r["shape"] == 7]
    assert len(outlines) == 1
    assert outlines[0]["fill"] is not None and outlines[0]["fill"][3] == 0.0


def test_the_outline_does_not_repeat_its_first_vertex() -> None:
    """DCS closes a freeform itself. Repeating vertex one adds a zero-length
    edge, which is the other half of why the fill never rendered."""
    h = _drawn(_config())
    outline = [r for r in h.records("markups") if r["shape"] == 7][0]
    assert len(outline["points"]) == len(SQUARE)
    first, last = outline["points"][0], outline["points"][-1]
    assert (first["x"], first["z"]) != (last["x"], last["z"])


def test_an_open_neutral_and_a_closed_one_do_not_draw_alike() -> None:
    """Shade answers "will this intercept me", so the one that will is the one
    that gets a real fill."""
    closed = _drawn(_config())
    cfg = _config()
    cfg["neutralBorder"]["zones"][0]["overflightBlue"] = "true"
    cfg["neutralBorder"]["zones"][0]["overflightRed"] = "true"
    permits = _drawn(cfg)
    assert closed.records("zoneFills")[0]["alpha"] > (
        permits.records("zoneFills")[0]["alpha"]
    )


# -- the F10 map says what a border IS without a hover -------------------------


def test_each_border_is_named_on_the_map() -> None:
    """A drawn polygon with no label is a shape a pilot has to guess at. The
    label carries the country and what its airspace does, in the same hue as
    its border so the two read as one thing."""
    h = _drawn(_config())
    texts = h.records("mapTexts")
    assert len(texts) == 1, "the border was drawn without a name"
    assert (
        texts[0]["text"]
        == "LEBANON\nCLOSED - surface-to-air batteries inside the border"
    )
    assert texts[0]["coalition"] == -1, "both sides see the border they may cross"
    # Same hue as the enforced border, and not the cyan the §45 support orbits use.
    outline = [r for r in h.records("markups") if r["shape"] == 7][0]
    assert texts[0]["color"][:3] == outline["color"][:3]


def test_the_label_sits_inside_its_own_border() -> None:
    """It is placed from the polygon's representative point, not its centroid:
    a country is usually concave and a centroid lands in the neighbour."""
    h = _drawn(_config())
    text = h.records("mapTexts")[0]
    xs = [float(v["x"]) for v in SQUARE]
    zs = [float(v["y"]) for v in SQUARE]
    assert min(xs) <= text["x"] <= max(xs)
    assert min(zs) <= text["z"] <= max(zs)


def test_a_country_you_may_cross_says_so() -> None:
    cfg = _config()
    cfg["neutralBorder"]["zones"][0]["overflightBlue"] = "true"
    cfg["neutralBorder"]["zones"][0]["overflightRed"] = "true"
    h = _drawn(cfg)
    assert h.records("mapTexts")[0]["text"] == "LEBANON\ntransit permitted"


def test_no_labels_when_the_draw_is_switched_off() -> None:
    h = _setup(_config())
    h.load_plugin_script(PLUGIN)
    assert h.records("mapTexts") == []


def test_the_label_does_not_say_the_country_twice() -> None:
    """The country's name is already the line above. The shipped label never
    starts with it, but a campaign may author one that does."""
    cfg = _config()
    zone = cfg["neutralBorder"]["zones"][0]
    del zone["field"]
    zone["spawnX"], zone["spawnZ"] = "9000", "9000"
    zone["originLabel"] = "Lebanon air defense district"
    h = _drawn(cfg)
    assert h.records("mapTexts")[0]["text"] == "LEBANON\nCLOSED - air defense district"


# -- the radio call is immediate; the interceptor is not -----------------------


def test_the_hail_lands_on_entry_not_at_the_shadow_launch() -> None:
    """Flown 2026-08-28: "good text, pop it immediately on entry to airspace".

    The hail used to wait for warnDwellS along with the shadow, which put the
    call half a minute after the crossing that caused it and made the whole
    ladder feel disconnected from what the player did. Being told is instant now;
    being intercepted still costs the dwell.
    """
    h = _setup(_config())
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(12)  # one scan, well inside warnDwellS of 30

    texts = [str(r.get("text", "")) for r in h.records("texts") if isinstance(r, dict)]
    assert any("violating" in t for t in texts), "no hail on entry"
    assert not _advisories(h), "the patrol was advised before its dwell"
    h.assert_no_lua_errors()


def test_the_second_call_still_waits_for_its_dwell() -> None:
    """The control for the test above: an immediate hail must not drag the
    advisory forward with it."""
    h = _setup(_config())
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(45)
    assert _advisories(h), "the second call never came at the dwell"
    h.assert_no_lua_errors()


def test_a_zone_with_no_sam_says_so_instead_of_going_quiet() -> None:
    """Flown 2026-08-28: "No sam spawn?" -- escalation fired and nothing woke.

    The template had never been built (sam was authored-only and the terrain
    files that are now the only source of borders never set it), and wake_sam
    returned silently, so a mission where the ladder ran correctly looked
    identical to one where it had not run at all.
    """
    cfg = _config(battery=False)
    h = _setup(cfg)
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(200)

    assert not _sam_spawns(h), "a zone with no template spawned a SAM"
    h.assert_no_lua_errors()


# -- more than one incursion into the same country ------------------------------


def _second_batteries(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return [
        r
        for r in h.records("spawns")
        if isinstance(r, dict) and str(r.get("alias", "")).startswith("NEUTRAL SAM2")
    ]


def test_the_other_side_gets_a_second_battery_not_a_re_swap() -> None:
    """A battery can only be on one coalition, and once swapped it is an ALLY of
    the other side. DM call 2026-08-29, carried over from the patrol: the
    country puts a second site up rather than flipping allegiance mid-fight.
    """
    h = _setup(_config())
    h.add_group(_intruder("Viper 1-1", 42, side=2))  # BLUE player
    h.load_plugin_script(PLUGIN)
    h.advance_to(200)
    assert len(_swaps(h)) == 1, "the standing battery never swapped"
    assert _second_batteries(h) == [], "a second site went up too early"

    # Now the OTHER side violates the same airspace.
    h.add_group(_intruder("Bandit 1", 50, side=1))  # RED player
    h.advance_to(400)

    second = _second_batteries(h)
    assert len(second) == 1, "the other side was never answered"
    assert len(_swaps(h)) == 1, "the first battery changed sides mid-fight"
    h.assert_no_lua_errors()


def test_a_zone_with_no_battery_never_claims_to_defend() -> None:
    """The plugin drops an enforcing zone that carries no battery rather than
    hail a player it has nothing to back the hail with."""
    h = _setup(_config(battery=False), with_battery=False)
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(400)

    assert _swaps(h) == []
    assert _hails(h) == [], "a zone with nothing to enforce with still challenged"
    h.assert_no_lua_errors()


#: A country stands one battery per stretch of war-facing frontier, so the
#: multi-battery case is the normal one -- a single site is the small country.
MANY_GROUPS = [f"NeutralBorder|Lebanon|SA-3|{n}" for n in (1, 2, 3)]


def _setup_many(cfg: dict[str, Any]) -> DcsPluginHarness:
    h = DcsPluginHarness()
    h.add_airbase({"name": "Rayak", "x": 10000, "z": 10000, "elev": 900, "side": 0})
    for index, name in enumerate(MANY_GROUPS):
        h.add_group(
            {
                "name": name,
                "id": 900 + index,
                "side": 0,
                "category": 2,
                "units": [
                    {
                        "name": name + "-1",
                        "type": "p-19 s-125 sr",
                        "x": 5000 + index * 4000,
                        "z": 5000 + index * 4000,
                        "alt": 900,
                        "airborne": False,
                    }
                ],
            }
        )
    h.lua.globals().dcsRetribution = h.to_lua(cfg)
    return h


def test_the_whole_country_escalates_not_just_the_site_you_flew_past() -> None:
    """A country stands several batteries and every one of them swaps together.
    Swapping only the nearest would leave the rest of the border a neutral the
    player could keep crossing after being declared hostile."""
    cfg = _config()
    cfg["neutralBorder"]["zones"][0]["samGroups"] = [
        {"name": name} for name in MANY_GROUPS
    ]
    h = _setup_many(cfg)
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(200)

    swaps = _swaps(h)
    assert sorted(s["group"] for s in swaps) == sorted(MANY_GROUPS)
    assert all(
        s["coalitionId"] == 1 for s in swaps
    ), "a BLUE intruder must be opposed by RED at every site"
    h.assert_no_lua_errors()


def test_the_second_side_is_answered_at_every_site_too() -> None:
    """The clone set mirrors the standing set, or the other side's intruder
    faces a fraction of the border the first one faced."""
    cfg = _config()
    cfg["neutralBorder"]["zones"][0]["samGroups"] = [
        {"name": name} for name in MANY_GROUPS
    ]
    h = _setup_many(cfg)
    h.add_group(_intruder("Viper 1-1", 42, side=2))  # BLUE player
    h.load_plugin_script(PLUGIN)
    h.advance_to(200)
    assert len(_swaps(h)) == len(MANY_GROUPS)

    h.add_group(_intruder("Bandit 1", 50, side=1))  # RED player
    h.advance_to(400)

    assert len(_second_batteries(h)) == len(MANY_GROUPS)
    assert len(_swaps(h)) == len(MANY_GROUPS), "a battery changed sides mid-fight"
    h.assert_no_lua_errors()


# -- the testing override ------------------------------------------------------
# Only a human earns the attack (DM call). `engageAi` lifts that so the ladder
# can be exercised without flying a whole profile to trip one border.


def test_engage_ai_holds_an_ai_flight_to_the_players_ladder() -> None:
    """With it ticked an AI stray runs the whole ladder, which is the point --
    a player has to fly a full profile to trip a border once."""
    h = _setup(_config(engage_ai=True))
    h.add_group(_intruder("Strike 9-1", 60, side=2, player=None))
    h.load_plugin_script(PLUGIN)
    h.advance_to(400)

    assert _hails(h), "the AI intruder was never hailed"
    swaps = _swaps(h)
    assert swaps, "the AI intruder never turned the country hostile"
    assert swaps[0]["coalitionId"] == 1, "a BLUE intruder must be opposed by RED"
    h.assert_no_lua_errors()


def test_the_override_reaches_every_gate_not_half_of_them() -> None:
    """A gate left on is_player would warn an AI and then never engage it, or
    engage without warning. Both halves move together or the ladder is broken."""
    from pathlib import Path

    script = Path(PLUGIN).read_text(encoding="utf-8")
    assert "state.is_player and" not in script
    assert "not state.is_player" not in script
