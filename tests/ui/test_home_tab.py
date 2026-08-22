from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from app.ui.tabs.home_tab import HomeTab


def _card_texts(card) -> set[str]:
    """Return all visible label text contained in a SummaryCard."""
    return {
        label.text()
        for label in card.findChildren(QLabel)
        if label.text()
    }


def _mock_home_tab_services(mocker):
    session = mocker.Mock()
    mocker.patch(
        "app.ui.tabs.home_tab.SessionLocal",
        return_value=session,
    )

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

    return session


def test_home_tab_renders(qtbot, mocker):
    session = _mock_home_tab_services(mocker)

    tab = HomeTab()
    qtbot.addWidget(tab)

    assert tab.glucose_card is not None
    assert tab.activity_card is not None
    assert tab.workouts_card is not None
    assert tab.nutrition_card is not None

    session.close.assert_called_once_with()


def test_home_cards_render_service_layer_summaries(qtbot, mocker):
    _mock_home_tab_services(mocker)

    tab = HomeTab()
    qtbot.addWidget(tab)

    assert "5 / 7" in _card_texts(tab.activity_card)
    assert "7-day goal adherence" in _card_texts(tab.activity_card)

    assert "3 sessions" in _card_texts(tab.workouts_card)
    assert "1 this week • 12,500 kg" in _card_texts(tab.workouts_card)

    assert "4 meals" in _card_texts(tab.nutrition_card)
    assert "7d: 210.0g carbs • 180.0g/day" in _card_texts(
        tab.nutrition_card
    )


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


def test_home_tab_renders_only_enabled_module_cards(
    qtbot,
    mocker,
):
    session_local = mocker.patch(
        "app.ui.tabs.home_tab.SessionLocal",
    )
    glucose_refresh = mocker.patch(
        "app.ui.tabs.home_tab.HomeTab._refresh_glucose_card",
        autospec=True,
    )

    get_daily_activity = mocker.patch(
        "app.ui.tabs.home_tab.get_daily_activity",
        return_value=[
            {
                "date": "2026-07-28",
                "steps": 8500,
            }
        ],
    )
    get_activity_summary_cards = mocker.patch(
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
    get_workout_summary_metrics = mocker.patch(
        "app.ui.tabs.home_tab.get_workout_summary_metrics",
    )
    get_nutrition_summary_metrics = mocker.patch(
        "app.ui.tabs.home_tab.get_nutrition_summary_metrics",
        return_value={
            "total_meals": 4,
            "total_carbs_g": 210,
            "average_daily_carbs_g": 180,
        },
    )

    tab = HomeTab(
        enabled_module_keys=("activity", "nutrition"),
    )
    qtbot.addWidget(tab)

    assert set(tab.summary_cards) == {
        "activity",
        "nutrition",
    }

    assert tab.activity_card is tab.summary_cards["activity"]
    assert tab.nutrition_card is tab.summary_cards["nutrition"]

    assert not hasattr(tab, "glucose_card")
    assert not hasattr(tab, "workouts_card")

    session_local.assert_not_called()
    glucose_refresh.assert_not_called()
    get_workout_summary_metrics.assert_not_called()

    get_daily_activity.assert_called_once_with()
    get_activity_summary_cards.assert_called_once()
    get_nutrition_summary_metrics.assert_called_once_with(days=7)


def test_refresh_data_only_refreshes_enabled_modules(
    qtbot,
    mocker,
):
    mocker.patch(
        "app.ui.tabs.home_tab.SessionLocal",
    )
    refresh_glucose = mocker.patch(
        "app.ui.tabs.home_tab.HomeTab._refresh_glucose_card",
        autospec=True,
    )
    refresh_activity = mocker.patch(
        "app.ui.tabs.home_tab.HomeTab._refresh_activity_card",
        autospec=True,
    )
    refresh_workouts = mocker.patch(
        "app.ui.tabs.home_tab.HomeTab._refresh_workouts_card",
        autospec=True,
    )
    refresh_nutrition = mocker.patch(
        "app.ui.tabs.home_tab.HomeTab._refresh_nutrition_card",
        autospec=True,
    )

    tab = HomeTab(
        enabled_module_keys=("activity",),
    )
    qtbot.addWidget(tab)

    refresh_glucose.assert_not_called()
    refresh_workouts.assert_not_called()
    refresh_nutrition.assert_not_called()
    refresh_activity.assert_called_once_with(tab)

    refresh_activity.reset_mock()

    tab.refresh_data()

    refresh_activity.assert_called_once_with(tab)
    refresh_glucose.assert_not_called()
    refresh_workouts.assert_not_called()
    refresh_nutrition.assert_not_called()


def test_home_activity_card_uses_configured_step_target(qtbot, mocker):
    rows = [
        {
            "activity_date": "2026-07-28",
            "steps": 8500,
            "source": "fitbit",
        }
    ]

    mocker.patch(
        "app.ui.tabs.home_tab.get_daily_activity",
        return_value=rows,
    )

    get_activity_summary_cards = mocker.patch(
        "app.ui.tabs.home_tab.get_activity_summary_cards",
        return_value=[
            {
                "key": "goal_adherence",
                "title": "Goal Adherence",
                "value": "1 / 1",
                "subtitle": "100%",
                "variant": "success",
            }
        ],
    )

    tab = HomeTab(
        enabled_module_keys=("activity",),
        step_target=8_500,
    )
    qtbot.addWidget(tab)

    get_activity_summary_cards.assert_called_once_with(
        rows,
        target_steps=8_500,
    )
