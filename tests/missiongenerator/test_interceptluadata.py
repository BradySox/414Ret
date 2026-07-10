from game.missiongenerator.interceptluadata import (
    DISENGAGE_MARGIN_NM,
    QRA_FORWARD_REACH_NM,
    DefenseZoneEntry,
    InterceptEntry,
    PlayerAlertEntry,
    dispatcher_tuning,
    populate_intercept_lua,
)
from game.missiongenerator.luagenerator import LuaData


def _entry(**kw: object) -> InterceptEntry:
    base = dict(
        squadron_id="sq-1",
        squadron_name="12th FS",
        airbase_name="Batumi",
        template_prefix="Intercept|Batumi|sq-1",
        coalition="BLUE",
        resource_count=4,
        grouping=2,
        engagement_range_nm=60,
        gci_max_radius_nm=100,
        comms_enabled=True,
        country_id=2,
        backstop_ewr_type="FPS-117",
    )
    base.update(kw)
    return InterceptEntry(**base)  # type: ignore[arg-type]


def test_empty_entries_creates_blue_and_red_buckets() -> None:
    root = LuaData("dcsRetribution")
    populate_intercept_lua(root, [])
    serialized = root.serialize()
    assert "Intercept" in serialized
    assert "BLUE" in serialized
    assert "RED" in serialized


def test_entry_is_grouped_under_its_coalition() -> None:
    root = LuaData("dcsRetribution")
    populate_intercept_lua(root, [_entry(coalition="RED")])

    intercept = root.get_item("Intercept")
    assert isinstance(intercept, LuaData)
    red_bucket = intercept.get_item("RED")
    blue_bucket = intercept.get_item("BLUE")
    assert isinstance(red_bucket, LuaData)
    assert isinstance(blue_bucket, LuaData)

    # Entry must land in the RED bucket, not in BLUE.
    assert len(red_bucket.objects) == 1
    assert len(blue_bucket.objects) == 0

    # Spot-check the record's content via the bucket's own serialization.
    red_serialized = red_bucket.serialize()
    assert "Intercept|Batumi|sq-1" in red_serialized
    assert "12th FS" in red_serialized


def test_resource_count_and_ranges_are_serialized() -> None:
    root = LuaData("dcsRetribution")
    populate_intercept_lua(root, [_entry(resource_count=4, engagement_range_nm=60)])
    serialized = root.serialize()
    assert "resourceCount" in serialized
    assert "engagementRangeNm" in serialized
    assert "gciMaxRadiusNm" in serialized
    assert "commsEnabled" in serialized


def test_grouping_is_serialized() -> None:
    root = LuaData("dcsRetribution")
    populate_intercept_lua(root, [_entry(grouping=1)])
    serialized = root.serialize()
    assert "grouping" in serialized


def test_country_id_is_serialized() -> None:
    root = LuaData("dcsRetribution")
    populate_intercept_lua(root, [_entry(country_id=82)])
    serialized = root.serialize()
    assert "countryId" in serialized
    assert "82" in serialized


def test_backstop_ewr_type_is_serialized() -> None:
    root = LuaData("dcsRetribution")
    populate_intercept_lua(root, [_entry(backstop_ewr_type="55G6 EWR")])
    serialized = root.serialize()
    assert "backstopEwrType" in serialized
    assert "55G6 EWR" in serialized


def test_empty_entries_creates_player_alert_bucket() -> None:
    root = LuaData("dcsRetribution")
    populate_intercept_lua(root, [])
    intercept = root.get_item("Intercept")
    assert isinstance(intercept, LuaData)
    alerts = intercept.get_item("PLAYER_ALERT")
    assert isinstance(alerts, LuaData)
    assert len(alerts.objects) == 0


def test_player_alert_entry_is_serialized() -> None:
    root = LuaData("dcsRetribution")
    populate_intercept_lua(
        root,
        [],
        [
            PlayerAlertEntry(
                airbase_name="Batumi", coalition="BLUE", scramble_radius_nm=60
            )
        ],
    )
    intercept = root.get_item("Intercept")
    assert isinstance(intercept, LuaData)
    alerts = intercept.get_item("PLAYER_ALERT")
    assert isinstance(alerts, LuaData)
    assert len(alerts.objects) == 1
    serialized = alerts.serialize()
    assert "Batumi" in serialized
    assert "scrambleRadiusNm" in serialized


def test_ambush_posture_is_serialized() -> None:
    # W5 GCI-ambush: the flag rides each record so the Lua can leash the
    # coalition's defenders; default (no ambush) serializes false.
    root = LuaData("dcsRetribution")
    populate_intercept_lua(root, [_entry(ambush=True)])
    serialized = root.serialize()
    assert 'ambushPosture = "true"' in serialized

    root_default = LuaData("dcsRetribution")
    populate_intercept_lua(root_default, [_entry()])
    assert 'ambushPosture = "false"' in root_default.serialize()


# --- QRA forward defense (border zones + reach) ---------------------------------


class _FakeDoctrine:
    gci_ambush = False


def test_forward_defense_opens_reach_and_disengage_leash() -> None:
    tuning = dispatcher_tuning(_FakeDoctrine(), 38, 60, forward_defense=True)  # type: ignore[arg-type]
    assert tuning.scramble_nm == QRA_FORWARD_REACH_NM
    # Moose aborts a defender past DisengageRadius from home, so the leash must
    # cover a transit to the far edge of the reach plus the engagement itself.
    assert tuning.disengage_nm == QRA_FORWARD_REACH_NM + 38 + DISENGAGE_MARGIN_NM
    assert tuning.disengage_nm > tuning.scramble_nm
    assert tuning.ambush is False


def test_forward_defense_never_narrows_an_explicit_setting() -> None:
    # A user who set a wider radius than the default reach keeps it.
    tuning = dispatcher_tuning(_FakeDoctrine(), 38, 350, forward_defense=True)  # type: ignore[arg-type]
    assert tuning.scramble_nm == 350


def test_forward_defense_off_is_byte_identical() -> None:
    tuning = dispatcher_tuning(_FakeDoctrine(), 38, 60, forward_defense=False)  # type: ignore[arg-type]
    assert (tuning.engage_nm, tuning.scramble_nm, tuning.disengage_nm) == (38, 60, 0)


def test_disengage_radius_is_serialized() -> None:
    root = LuaData("dcsRetribution")
    populate_intercept_lua(root, [_entry(disengage_radius_nm=258)])
    assert 'disengageRadiusNm = "258"' in root.serialize()

    # Absent => 0 => the Lua leaves Moose's default alone.
    root_default = LuaData("dcsRetribution")
    populate_intercept_lua(root_default, [_entry()])
    assert 'disengageRadiusNm = "0"' in root_default.serialize()


def test_zones_bucket_always_exists_so_the_lua_can_iterate() -> None:
    root = LuaData("dcsRetribution")
    populate_intercept_lua(root, [])
    assert "ZONES" in root.serialize()


def test_defense_zones_are_grouped_under_their_coalition() -> None:
    root = LuaData("dcsRetribution")
    populate_intercept_lua(
        root,
        [_entry()],
        [],
        [
            DefenseZoneEntry("QRA Defense Haina", "RED", 1000.0, -2000.0, 111120.0),
            DefenseZoneEntry("QRA Defense Fulda", "BLUE", 5.0, 6.0, 7.0),
        ],
    )
    serialized = root.serialize()
    assert 'name = "QRA Defense Haina"' in serialized
    assert 'radiusM = "111120.0"' in serialized
    assert 'x = "1000.0"' in serialized
    assert 'y = "-2000.0"' in serialized
    # Both coalitions' zones are present; the Lua picks its own bucket by name.
    assert 'name = "QRA Defense Fulda"' in serialized
