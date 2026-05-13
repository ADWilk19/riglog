from datetime import datetime, date

from app.services.cross_module.analysis import (
    calculate_activity_glucose_event_summary,
)


def test_activity_glucose_event_summary_handles_missing_glucose_rows():
    """Return activity rows with zero/null glucose metrics when no glucose exists."""

    activity_rows = [
        {
            "date": date(2026, 5, 12),
            "event_key": "pre_breakfast",
            "event_window": "Pre-Breakfast",
            "steps": 120,
            "calories_burned": 42.5,
            "interval_count": 8,
        }
    ]

    glucose_rows = []

    result = calculate_activity_glucose_event_summary(
        activity_rows=activity_rows,
        glucose_rows=glucose_rows,
    )

    assert result == [
        {
            "date": date(2026, 5, 12),
            "event_key": "pre_breakfast",
            "event_window": "Pre-Breakfast",
            "steps": 120,
            "calories_burned": 42.5,
            "interval_count": 8,
            "same_window_glucose_count": 0,
            "same_window_avg_glucose": None,
            "same_window_min_glucose": None,
            "same_window_max_glucose": None,
            "same_window_target_pct": None,
            "next_glucose_count": 0,
            "avg_next_glucose": None,
            "avg_glucose_delta_to_next": None,
        }
    ]


def test_activity_glucose_event_summary_joins_same_window_glucose():
    """Aggregate same-window glucose metrics onto matching activity event rows."""

    activity_rows = [
        {
            "date": date(2026, 5, 12),
            "event_key": "pre_breakfast",
            "event_window": "Pre-Breakfast",
            "steps": 120,
            "calories_burned": 42.5,
            "interval_count": 8,
        }
    ]

    glucose_rows = [
        {
            "id": 1,
            "recorded_at": datetime(2026, 5, 12, 7, 0),
            "glucose_value": 6.0,
            "meal_event": "pre_breakfast",
            "meal_event_label": "Pre-Breakfast",
        },
        {
            "id": 2,
            "recorded_at": datetime(2026, 5, 12, 7, 30),
            "glucose_value": 8.0,
            "meal_event": "pre_breakfast",
            "meal_event_label": "Pre-Breakfast",
        },
    ]

    result = calculate_activity_glucose_event_summary(
        activity_rows=activity_rows,
        glucose_rows=glucose_rows,
    )

    row = result[0]

    assert row["same_window_glucose_count"] == 2
    assert row["same_window_avg_glucose"] == 7.0
    assert row["same_window_min_glucose"] == 6.0
    assert row["same_window_max_glucose"] == 8.0
    assert row["same_window_target_pct"] == 100.0
    assert row["next_glucose_count"] == 1
    assert row["avg_next_glucose"] == 8.0
    assert row["avg_glucose_delta_to_next"] == 2.0

def test_activity_glucose_event_summary_preserves_meal_event_order():
    """Return event-window rows in chronological meal-event order."""

    activity_rows = [
        {
            "date": date(2026, 5, 12),
            "event_key": "post_lunch",
            "event_window": "Post-Lunch",
            "steps": 300,
            "calories_burned": 75.0,
            "interval_count": 12,
        },
        {
            "date": date(2026, 5, 12),
            "event_key": "pre_breakfast",
            "event_window": "Pre-Breakfast",
            "steps": 100,
            "calories_burned": 40.0,
            "interval_count": 8,
        },
        {
            "date": date(2026, 5, 12),
            "event_key": "pre_lunch",
            "event_window": "Pre-Lunch",
            "steps": 200,
            "calories_burned": 55.0,
            "interval_count": 8,
        },
    ]

    glucose_rows = []

    result = calculate_activity_glucose_event_summary(
        activity_rows=activity_rows,
        glucose_rows=glucose_rows,
    )

    assert [row["event_window"] for row in result] == [
        "Pre-Breakfast",
        "Pre-Lunch",
        "Post-Lunch",
    ]
