from datetime import date, timedelta

from app.services.activity.analysis import (
    calculate_goal_adherence,
    get_activity_insight_metrics,
)


def make_rows(step_values: list[int]) -> list[dict]:
    start_date = date(2026, 4, 1)

    return [
        {
            "activity_date": start_date + timedelta(days=index),
            "steps": steps,
            "source": "fitbit",
        }
        for index, steps in enumerate(step_values)
    ]


def test_calculate_goal_adherence_for_latest_7_days():
    rows = make_rows([
        10000,
        9000,
        11000,
        8000,
        12000,
        10000,
        7000,
    ])

    result = calculate_goal_adherence(rows, days=7, target_steps=10_000)

    assert result == {
        "goal_days": 4,
        "total_days": 7,
        "goal_adherence_pct": 57.1,
    }


def test_calculate_goal_adherence_uses_latest_window():
    rows = make_rows([
        10000,
        10000,
        10000,
        10000,
        10000,
        10000,
        10000,
        5000,
        5000,
        5000,
    ])

    result = calculate_goal_adherence(rows, days=3, target_steps=10_000)

    assert result == {
        "goal_days": 0,
        "total_days": 3,
        "goal_adherence_pct": 0.0,
    }


def test_get_activity_insight_metrics_returns_7_and_14_day_adherence():
    rows = make_rows([
        10000,
        10000,
        5000,
        5000,
        10000,
        10000,
        10000,
        5000,
        5000,
        10000,
        10000,
        5000,
        10000,
        10000,
    ])

    result = get_activity_insight_metrics(rows, target_steps=10_000)

    assert result["goal_adherence_last_7"] == 57.1
    assert result["goal_days_last_7"] == 4
    assert result["total_days_last_7"] == 7

    assert result["goal_adherence_last_14"] == 64.3
    assert result["goal_days_last_14"] == 9
    assert result["total_days_last_14"] == 14
