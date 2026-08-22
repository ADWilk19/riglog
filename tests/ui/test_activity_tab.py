from datetime import date

from app.ui.tabs.activity_tab import ActivityTab, ActivityTrendChart


def test_activity_tab_uses_configured_step_target_for_summary_calls(
    qtbot,
    mocker,
):
    rows = [
        {
            "activity_date": date(2026, 8, 1),
            "steps": 8_600,
            "source": "fitbit",
        }
    ]

    mocker.patch(
        "app.ui.tabs.activity_tab.QTimer.singleShot",
    )
    mocker.patch(
        "app.ui.tabs.activity_tab.load_activity_last_synced",
        return_value=None,
    )
    mocker.patch(
        "app.ui.tabs.activity_tab.get_daily_activity",
        return_value=rows,
    )
    get_activity_summary_cards = mocker.patch(
        "app.ui.tabs.activity_tab.get_activity_summary_cards",
        return_value=[],
    )
    get_activity_insight_metrics = mocker.patch(
        "app.ui.tabs.activity_tab.get_activity_insight_metrics",
        return_value={
            "best_week_steps": 0,
            "best_week_start": None,
            "worst_week_steps": 0,
            "worst_week_start": None,
            "consistency_label": "No data",
            "step_cv_pct": None,
        },
    )

    tab = ActivityTab(step_target=8_500)
    qtbot.addWidget(tab)

    get_activity_summary_cards.assert_called_once_with(
        rows,
        target_steps=8_500,
    )
    get_activity_insight_metrics.assert_called_once_with(
        rows,
        target_steps=8_500,
    )


def test_activity_tab_selected_day_uses_configured_step_target(
    qtbot,
    mocker,
):
    selected_date = date(2026, 8, 1)

    mocker.patch(
        "app.ui.tabs.activity_tab.QTimer.singleShot",
    )
    mocker.patch(
        "app.ui.tabs.activity_tab.load_activity_last_synced",
        return_value=None,
    )
    mocker.patch(
        "app.ui.tabs.activity_tab.get_daily_activity",
        return_value=[
            {
                "activity_date": selected_date,
                "steps": 8_600,
                "source": "fitbit",
            }
        ],
    )

    tab = ActivityTab(step_target=8_500)
    qtbot.addWidget(tab)

    tab._handle_day_selected(0, selected_date)

    assert tab.selected_day_goal_label.text() == "Goal: Yes"


def test_activity_chart_uses_configured_daily_target(qtbot):
    chart = ActivityTrendChart()
    qtbot.addWidget(chart)

    chart.plot_steps(
        [
            {
                "activity_date": date(2026, 8, 1),
                "steps": 8_600,
                "source": "fitbit",
            }
        ],
        chart_view="Daily",
        target_steps=8_500,
    )

    labels = [
        line.get_label()
        for line in chart.ax.lines
    ]

    assert "8,500 Target" in labels


def test_activity_chart_uses_configured_weekly_target(qtbot):
    chart = ActivityTrendChart()
    qtbot.addWidget(chart)

    chart.plot_steps(
        [
            {
                "activity_date": date(2026, 8, 1),
                "steps": 8_600,
                "source": "fitbit",
            }
        ],
        chart_view="Weekly",
        target_steps=8_500,
    )

    labels = [
        line.get_label()
        for line in chart.ax.lines
    ]

    assert "8,500/day Equivalent" in labels
