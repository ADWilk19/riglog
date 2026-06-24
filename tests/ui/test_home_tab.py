from app.ui.tabs.home_tab import HomeTab


def test_home_tab_renders(qtbot, mocker):
    mocker.patch(
        "app.ui.tabs.home_tab.get_activity_summary_cards",
        return_value=[
            {
                "key": "goal_adherence",
                "title": "Goal Days",
                "value": "5 / 7",
                "subtitle": "71.4%",
                "variant": "success",
            },
            {
                "key": "avg_steps",
                "title": "Avg Steps",
                "value": "8,500",
                "subtitle": "Last 7 days",
                "variant": "neutral",
            },
            {
                "key": "best_day",
                "title": "Best Day",
                "value": "12,000",
                "subtitle": "steps",
                "variant": "neutral",
            },
            {
                "key": "current_streak",
                "title": "Current Streak",
                "value": "2",
                "subtitle": "days",
                "variant": "neutral",
            },
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

    tab = HomeTab()
    qtbot.addWidget(tab)

    assert tab is not None
