from datetime import date, timedelta

from app.services.activity.analysis import (
    calculate_goal_adherence,
    calculate_weekly_summary_metrics,
    get_activity_insight_metrics,
)


def make_rows(
    step_values: list[int],
    start_date: date = date(2026, 4, 1),
) -> list[dict]:
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
    rows = make_rows(
        [
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
        ],
        start_date=date(2026, 4, 6),
    )

    result = get_activity_insight_metrics(rows, target_steps=10_000)

    assert result["goal_adherence_last_7"] == 57.1
    assert result["goal_days_last_7"] == 4
    assert result["total_days_last_7"] == 7

    assert result["goal_adherence_last_14"] == 64.3
    assert result["goal_days_last_14"] == 9
    assert result["total_days_last_14"] == 14

    assert result["best_week_steps"] == 60000
    assert result["best_week_start"] == "2026-04-06"
    assert result["worst_week_steps"] == 55000
    assert result["worst_week_start"] == "2026-04-13"

def test_calculate_weekly_summary_metrics_returns_best_and_worst_week():
    rows = make_rows(
        [
            10000,
            10000,
            10000,
            10000,
            10000,
            10000,
            10000,  # week 1 = 70,000
            5000,
            5000,
            5000,
            5000,
            5000,
            5000,
            5000,  # week 2 = 35,000
        ],
        start_date=date(2026, 4, 6),
    )

    result = calculate_weekly_summary_metrics(rows)

    assert result == {
        "best_week_steps": 70000,
        "best_week_start": "2026-04-06",
        "worst_week_steps": 35000,
        "worst_week_start": "2026-04-13",
    }

def test_calculate_weekly_summary_metrics_handles_empty_rows():
    result = calculate_weekly_summary_metrics([])

    assert result == {
        "best_week_steps": 0,
        "best_week_start": None,
        "worst_week_steps": 0,
        "worst_week_start": None,
    }
