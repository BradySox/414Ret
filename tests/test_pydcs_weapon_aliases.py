from dcs.weapons_data import Weapons


def test_legacy_pydcs_weapon_aliases_load_during_game_import() -> None:
    import game  # noqa: F401

    assert (
        Weapons.TER_9_A___3_x_Mk_82___500lb_GP_Bomb_LD
        is Weapons.TER_9A_with_3_x_Mk_82___500lb_GP_Bomb_LD
    )
    assert (
        Weapons.LAU_7___AIM_9B_Sidewinder_IR_AAM
        is Weapons.LAU_7_with_AIM_9B_Sidewinder_IR_AAM
    )
    assert (
        Weapons.BRU_42___1_x_ADM_141A_TALD
        is Weapons.BRU_42_with_ADM_141A_TALD
    )
    assert (
        Weapons.SUU_25___8_x_Illumination_Flare__LUU_2B
        is Weapons.SUU_25_x_8_LUU_2___Target_Marker_Flares
    )
