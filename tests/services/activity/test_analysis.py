from datetime import date, timedelta

from app.services.activity.analysis import (
    calculate_goal_adherence,
    calculate_step_consistency_metrics,
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

    assert result["step_mean"] is not None
    assert result["step_sd"] is not None
    assert result["step_cv_pct"] is not None
    assert result["consistency_label"] in {
        "Consistent",
        "Variable",
        "Highly variable",
        "No data",
    }


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


def test_calculate_step_consistency_metrics_for_consistent_steps():
    rows = make_rows(
        [
            9800,
            10000,
            10200,
            9900,
            10100,
            10050,
            9950,
        ],
        start_date=date(2026, 4, 6),
    )

    result = calculate_step_consistency_metrics(rows)

    assert result["step_mean"] == 10000.0
    assert result["step_sd"] == 132.3
    assert result["step_cv_pct"] == 1.3
    assert result["consistency_label"] == "Consistent"


def test_calculate_step_consistency_metrics_for_variable_steps():
    rows = make_rows(
        [
            2000,
            15000,
            3000,
            14000,
            4000,
            16000,
            5000,
        ],
        start_date=date(2026, 4, 6),
    )

    result = calculate_step_consistency_metrics(rows)

    assert result["consistency_label"] in {"Variable", "Highly variable"}
    assert result["step_cv_pct"] >= 25.0


def test_calculate_step_consistency_metrics_handles_empty_rows():
    result = calculate_step_consistency_metrics([])

    assert result == {
        "step_mean": None,
        "step_sd": None,
        "step_cv_pct": None,
        "consistency_label": "No data",
    }


def test_calculate_step_consistency_metrics_handles_single_day():
    rows = make_rows([12000], start_date=date(2026, 4, 6))

    result = calculate_step_consistency_metrics(rows)

    assert result == {
        "step_mean": 12000.0,
        "step_sd": 0.0,
        "step_cv_pct": 0.0,
        "consistency_label": "Consistent",
    }
