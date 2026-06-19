from datetime import datetime, time

from qt_ui.windows.mission.QPackageDialog import datetime_for_time_of_day


def test_tot_rolls_forward_across_midnight() -> None:
    current = datetime(2026, 6, 18, 23, 45)

    assert datetime_for_time_of_day(current, time(0, 15)) == datetime(
        2026, 6, 19, 0, 15
    )


def test_tot_rolls_backward_across_midnight() -> None:
    current = datetime(2026, 6, 18, 0, 15)

    assert datetime_for_time_of_day(current, time(23, 45)) == datetime(
        2026, 6, 17, 23, 45
    )


def test_tot_keeps_same_date_for_normal_adjustment() -> None:
    current = datetime(2026, 6, 18, 14, 0)

    assert datetime_for_time_of_day(current, time(15, 30)) == datetime(
        2026, 6, 18, 15, 30
    )
