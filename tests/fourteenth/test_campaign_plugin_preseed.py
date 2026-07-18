"""Campaign plugin preseeds: features that depend on a plugin runtime must ship it.

The generic frontline-artillery harassment (``artillery_base_harassment``) emits its
config into ``dcsRetribution.VietnamOps`` -- the *vietnamops plugin* owns the barrage
runtime. A player whose saved defaults disabled "Vietnam Ops" (perfectly reasonable on
a conventional-campaign squadron) would otherwise silently lose the feature: the
emitter emits, nothing consumes. Red Tide preseeds the plugin ON through its campaign
``settings.plugins`` block, which the New Game wizard layers OVER the player's saved
defaults (see ``QNewGameSettings._load_campaign_settings``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from game.campaignloader.campaign import Campaign
from game.settings import Settings

RED_TIDE = "resources/campaigns/red_tide.yaml"


def _campaign_settings() -> dict[str, Any]:
    with open(RED_TIDE, encoding="utf-8") as f:
        return yaml.safe_load(f)["settings"]


def test_red_tide_preseeds_the_vietnamops_plugin_for_artillery_harassment() -> None:
    settings = _campaign_settings()
    assert settings["artillery_base_harassment"] is True
    # The feature's runtime lives in the vietnamops plugin -- the campaign must
    # carry the plugin ON or a player default of off silently kills the feature.
    assert settings["plugins"]["vietnamops"] is True


def test_red_tide_preseeds_the_commsjam_plugin_for_enemy_comms_jamming() -> None:
    settings = _campaign_settings()
    assert settings["enemy_comms_jamming"] is True
    # §51's runtime lives in the commsjam plugin -- same saved-default-off trap
    # as the vietnamops harassment above.
    assert settings["plugins"]["commsjam"] is True


def test_red_tide_preseeds_the_mobilemissiles_plugin_for_the_scud_hunt() -> None:
    settings = _campaign_settings()
    # §49 relocates the red SS-1C Scud-B batteries in-mission; the runtime lives in
    # the mobilemissiles plugin -- same saved-default-off trap as the others.
    assert settings["mobile_missile_relocation"] is True
    assert settings["plugins"]["mobilemissiles"] is True


def test_red_tide_preseeds_the_redscramble_plugin_for_the_host_menu() -> None:
    settings = _campaign_settings()
    # §61's runtime lives in the redscramble plugin -- same saved-default-off trap
    # as the others. Preseeded ahead of the Friday 2026-07-17 regeneration so the
    # host's "give the boys something to shoot" button is armed for MP events.
    assert settings["host_red_scramble"] is True
    assert settings["plugins"]["redscramble"] is True
    # The menu is gated to the host's static name tag: 414th names run
    # "<flight> 1-x | Flash" with a changing prefix, and hostPlayers is a
    # substring match, so the tag alone covers every event's prefix.
    assert settings["plugins"]["redscramble.hostPlayers"] == "Flash"


def test_red_tide_preseeds_the_combatsar_plugin_for_the_jam_intel_gate() -> None:
    settings = _campaign_settings()
    # §51 rides the DEFAULT intel gate (comms_jam_requires_capture, default ON), which
    # arms only off a captured aircrew -- and combat_sar_captures has exactly one writer
    # in the tree: the combatsar plugin. Disabled, it injects nothing, the Lua global
    # stays {}, the jam loop's type check still passes, and red never jams: silent, no
    # error. The pin also protects all rescue and the POW->will feed.
    assert settings["enemy_comms_jamming"] is True
    assert "comms_jam_requires_capture" not in settings  # rides the default-ON gate
    assert settings["plugins"]["combatsar"] is True


def test_red_tide_preseeds_the_mantisiads_plugin_for_advanced_iads() -> None:
    # advanced_iads is a campaign-level key, NOT a setting -- so it is read from the
    # document root while the plugin pin lives under settings.plugins.
    with open(RED_TIDE, encoding="utf-8") as f:
        campaign = yaml.safe_load(f)
    assert campaign["advanced_iads"] is True
    # mantisiads owns that whole runtime -- MANTIS ships inside the bundled MOOSE, so
    # the plugin is the only consumer of the emitted IADS table. Off, generation skips
    # the IADS command unit AND the auto-planner drops IADS buildings as strike targets.
    assert campaign["settings"]["plugins"]["mantisiads"] is True


def test_red_tide_preseeds_the_convoyambush_plugin() -> None:
    settings = _campaign_settings()
    # §50's spring/cue runtime lives in the convoyambush plugin -- same trap as the rest.
    assert settings["convoy_ambush"] is True
    assert settings["plugins"]["convoyambush"] is True


def test_red_tide_preseeds_the_minefields_plugin() -> None:
    settings = _campaign_settings()
    # §57 is the ONLY preseeded plugin whose own defaultValue is false, so this pin is
    # load-bearing for every host regardless of their saved defaults -- not insurance.
    assert settings["air_droppable_minefields"] is True
    assert settings["auto_plan_minefields"] is True
    assert settings["plugins"]["minefields"] is True


def test_red_tide_preseeded_plugin_option_keys_are_declared() -> None:
    """Every ``<plugin>.<option>`` preseed must name a real declared option.

    A typo'd option key is silently ignored -- the plugin just runs its default. This
    walks each dotted preseed back to the owning plugin.json's specificOptions.
    """
    import json

    settings = _campaign_settings()
    for key, value in settings["plugins"].items():
        if "." not in key:
            continue
        plugin_name, option = key.split(".", 1)
        manifest = Path(f"resources/plugins/{plugin_name}/plugin.json")
        assert manifest.exists(), f"{key} names a plugin with no manifest"
        with manifest.open(encoding="utf-8") as f:
            declared = {o["mnemonic"] for o in json.load(f).get("specificOptions", [])}
        assert option in declared, f"{key} is not a declared option of {plugin_name}"


def test_red_tide_preseeds_c2_decapitation_effects() -> None:
    settings = _campaign_settings()
    # §52 is default OFF; Red Tide's per-base command-center network is the fit, so
    # the campaign flips it ON (pure turn-model, no plugin dependency).
    assert settings["c2_decapitation_effects"] is True


def test_red_tide_preseeds_red_intent() -> None:
    settings = _campaign_settings()
    # §55 is default OFF; Red Tide is a peer fight where red has real offensive agency,
    # and with war_economy also ON the supply->posture loop closes (a starved red digs
    # in), so the campaign flips it ON (pure turn-model, no plugin dependency).
    assert settings["red_intent"] is True


def test_red_tide_preseeds_the_opfor_qra_reserve() -> None:
    settings = _campaign_settings()
    # The Cold-War Soviet defensive posture depends on red holding a QRA alert reserve.
    # The standard default is 0; preseed it here so it survives a player resetting their
    # saved defaults toward standard (without it, red goes quiet AND passive, and the §1
    # QRA forward-defense layer has nothing to scramble to the front).
    assert settings["opfor_default_qra_reserve"] == 4


def test_red_tide_preseeds_the_era_weapon_gate() -> None:
    settings = _campaign_settings()
    # Red Tide is 1988; the era gate keeps the period jets off post-era weapons. Default
    # off and covered by no other campaign setting, so it must be preseeded to survive a
    # reset to standard defaults.
    assert settings["restrict_weapons_by_date"] is True


def test_red_tide_preseeds_the_era_property_gate() -> None:
    settings = _campaign_settings()
    # §24's property gate rode on restrict_weapons_by_date until #598 split it onto its
    # own default-off toggle, which silently dropped Red Tide's clamp (the M1-flown build
    # still had it). Both gates are preseeded here deliberately; #598 split them so either
    # can be enforced alone, so this asserts Red Tide's choice -- it is NOT a general rule
    # that the two must move together.
    assert settings["restrict_props_by_date"] is True


def test_red_tide_preseeds_the_f4e_expanded_weapons_mod() -> None:
    settings = _campaign_settings()
    # §71: the Mods-page checkboxes read the same campaign settings namespace
    # (QGeneratorSettings.update_settings). Preseeded ON so the wing's Phantoms
    # default to the AGM-88 "(XW)" SEAD fits; unchecking the box (or lacking the
    # mod) falls back to the stock Shrike fits via the loadout pylon gate.
    assert settings["f4e_expanded_weapons"] is True


def test_red_tide_preseeds_munitions_scarcity() -> None:
    settings = _campaign_settings()
    # §54 is the air axis of the war economy (also preseeded): out-of-stock scarce
    # munitions degrade at load. Default off and covered by no other campaign setting.
    assert settings["restrict_weapons_by_stock"] is True
    assert settings["war_economy"] is True


def test_red_tide_fields_the_two_scud_batteries_for_the_hunt() -> None:
    # §49 only has something to relocate if the .miz actually places missile-category
    # TGOs. Red Tide's laydown carries two SS-1C Scud-B batteries; a future miz edit
    # must not silently drop them (the preseed above would then be a dead toggle).
    campaign = Campaign.from_file(Path(RED_TIDE))
    theater = campaign.load_theater(advanced_iads=True)
    missile_cps = sorted(
        cp.name
        for cp in theater.controlpoints
        for _ in cp.preset_locations.missile_sites
    )
    assert missile_cps == ["Haina", "Wittstock"]


def test_the_plugin_preseed_survives_deserialization_and_wins_the_layering() -> None:
    deserialized = Settings.deserialize_state_dict(dict(_campaign_settings()))
    campaign_plugins = deserialized.get("plugins", {})
    assert campaign_plugins.get("vietnamops") is True
    # The wizard layers the campaign's plugins dict over the player's saved
    # defaults -- a saved "vietnamops: False" must lose to the campaign preseed.
    saved_defaults = {"vietnamops": False, "vietnamops.harassGraceS": 300}
    merged = {**saved_defaults, **campaign_plugins}
    assert merged["vietnamops"] is True
    assert merged["vietnamops.harassGraceS"] == 300  # options untouched


def test_red_tide_preseeds_the_m1_tuning_batch() -> None:
    """The flown M1 (2026-07-11) tuning findings, preseeded so a NEW game gets them.

    - aewc/tanker buffers 30/25 NM: the AI depth push (2.5x) at the 80/70 defaults
      parked the red A-50/IL-78 200/175 NM back over Berlin, leaving the P-14 line
      as red's whole detection net.
    - BARCAP 45 min: a Schonefeld MiG-29 flamed out dry at ~75 min airborne; 60 min
      on-station is a whole Fulcrum+tank fuel load at the AI's patrol speed.
    """
    settings = _campaign_settings()
    assert settings["aewc_threat_buffer_min_distance"] == 30
    assert settings["tanker_threat_buffer_min_distance"] == 25
    assert settings["desired_barcap_mission_duration"] == 45


def test_red_tide_keeps_civilian_air_traffic() -> None:
    # Squadron call 2026-07-12, reversing the first M1 tuning cut: Red Tide KEEPS
    # the civilian layer (the ambient life is worth the occasional Aeroflot
    # incident; BVR discrimination past the FLOT is on the shooter). The campaign
    # must NOT preseed the gate at all -- the generic default (ON) applies.
    settings = _campaign_settings()
    assert "civilian_air_traffic" not in settings


def test_barcap_duration_preseed_deserializes_to_a_timedelta() -> None:
    # Campaign yaml carries minutes as an int; deserialize_state_dict must coerce
    # the timedelta-typed field or every patrol_duration consumer breaks.
    from datetime import timedelta

    deserialized = Settings.deserialize_state_dict(dict(_campaign_settings()))
    assert deserialized["desired_barcap_mission_duration"] == timedelta(minutes=45)


def test_civilian_traffic_gate_defaults_on_and_gates_generate() -> None:
    # The generic gate: default ON (every other campaign byte-identical), and
    # CivilianTrafficGenerator.generate() early-returns when off.
    from types import SimpleNamespace

    from game.missiongenerator.civiliantraffic import CivilianTrafficGenerator

    assert Settings().civilian_air_traffic is True

    gen: CivilianTrafficGenerator = CivilianTrafficGenerator.__new__(
        CivilianTrafficGenerator
    )
    calls: list[str] = []
    gen.game = SimpleNamespace(  # type: ignore[assignment]
        settings=SimpleNamespace(civilian_air_traffic=False)
    )
    gen.mission = SimpleNamespace(  # type: ignore[assignment]
        country=lambda name: calls.append(name)
    )
    gen.generate()
    assert calls == []  # early-returned before touching the mission
