from PySide6.QtCore import Qt

from app.ui.tabs.home_tab import HomeTab


def _mock_home_tab_services(mocker):
    mocker.patch(
        "app.ui.tabs.home_tab.HomeTab._refresh_glucose_card",
        autospec=True,
        return_value=None,
    )

    mocker.patch(
        "app.ui.tabs.home_tab.get_daily_activity",
        return_value=[
            {
                "date": "2026-06-24",
                "steps": 8500,
            }
        ],
    )

    mocker.patch(
        "app.ui.tabs.home_tab.get_activity_summary_cards",
        return_value=[
            {
                "key": "goal_adherence",
                "title": "Goal Adherence",
                "value": "5 / 7",
                "subtitle": "71.4%",
                "variant": "success",
            }
        ],
    )

    mocker.patch(
        "app.ui.tabs.home_tab.get_workout_summary_metrics",
        return_value={
            "total_sessions": 3,
            "weekly_sessions": 1,
            "total_volume_kg": 12500,
        },
    )

    mocker.patch(
        "app.ui.tabs.home_tab.get_nutrition_summary_metrics",
        return_value={
            "total_meals": 4,
            "total_calories": 1800,
            "total_carbs_g": 210,
            "total_protein_g": 120,
            "total_fat_g": 60,
            "average_daily_carbs_g": 180,
        },
    )


def test_home_tab_renders(qtbot, mocker):
    _mock_home_tab_services(mocker)

    tab = HomeTab()
    qtbot.addWidget(tab)

    assert tab is not None


def test_home_summary_cards_call_navigation_callbacks(qtbot, mocker):
    _mock_home_tab_services(mocker)

    on_open_glucose = mocker.Mock()
    on_open_activity = mocker.Mock()
    on_open_workouts = mocker.Mock()
    on_open_nutrition = mocker.Mock()

    tab = HomeTab(
        on_open_glucose=on_open_glucose,
        on_open_activity=on_open_activity,
        on_open_workouts=on_open_workouts,
        on_open_nutrition=on_open_nutrition,
    )
    qtbot.addWidget(tab)

    qtbot.mouseClick(tab.glucose_card, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(tab.activity_card, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(tab.workouts_card, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(tab.nutrition_card, Qt.MouseButton.LeftButton)

    on_open_glucose.assert_called_once_with()
    on_open_activity.assert_called_once_with()
    on_open_workouts.assert_called_once_with()
    on_open_nutrition.assert_called_once_with()
