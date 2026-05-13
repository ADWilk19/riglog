from datetime import datetime, date

from app.services.cross_module.analysis import (
    calculate_activity_glucose_correlations,
    calculate_activity_glucose_event_summary,
    get_ranked_correlation_insights,
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


def test_activity_glucose_correlations_returns_empty_contract_without_rows():
    """Return a stable empty correlation contract when no rows are supplied."""
    result = calculate_activity_glucose_correlations([])

    assert result == {
        "row_count": 0,
        "steps_vs_avg_next_glucose": None,
        "calories_vs_avg_next_glucose": None,
        "steps_vs_glucose_delta": None,
        "calories_vs_glucose_delta": None,
        "interpretations": {
            "steps_vs_avg_next_glucose": {
                "correlation": None,
                "strength": "insufficient_data",
                "direction": "insufficient_data",
                "summary": "Not enough paired activity and glucose data yet.",
            },
            "calories_vs_avg_next_glucose": {
                "correlation": None,
                "strength": "insufficient_data",
                "direction": "insufficient_data",
                "summary": "Not enough paired activity and glucose data yet.",
            },
            "steps_vs_glucose_delta": {
                "correlation": None,
                "strength": "insufficient_data",
                "direction": "insufficient_data",
                "summary": "Not enough paired activity and glucose data yet.",
            },
            "calories_vs_glucose_delta": {
                "correlation": None,
                "strength": "insufficient_data",
                "direction": "insufficient_data",
                "summary": "Not enough paired activity and glucose data yet.",
            },
        },
    }


def test_activity_glucose_correlations_requires_at_least_two_paired_rows():
    """Return null correlations when fewer than two paired rows are available."""
    rows = [
        {
            "steps": 100,
            "calories_burned": 25.0,
            "avg_next_glucose": 8.0,
            "avg_glucose_delta_to_next": 1.0,
        }
    ]

    result = calculate_activity_glucose_correlations(rows)

    assert result == {
        "row_count": 1,
        "steps_vs_avg_next_glucose": None,
        "calories_vs_avg_next_glucose": None,
        "steps_vs_glucose_delta": None,
        "calories_vs_glucose_delta": None,
        "interpretations": {
            "steps_vs_avg_next_glucose": {
                "correlation": None,
                "strength": "insufficient_data",
                "direction": "insufficient_data",
                "summary": "Not enough paired activity and glucose data yet.",
            },
            "calories_vs_avg_next_glucose": {
                "correlation": None,
                "strength": "insufficient_data",
                "direction": "insufficient_data",
                "summary": "Not enough paired activity and glucose data yet.",
            },
            "steps_vs_glucose_delta": {
                "correlation": None,
                "strength": "insufficient_data",
                "direction": "insufficient_data",
                "summary": "Not enough paired activity and glucose data yet.",
            },
            "calories_vs_glucose_delta": {
                "correlation": None,
                "strength": "insufficient_data",
                "direction": "insufficient_data",
                "summary": "Not enough paired activity and glucose data yet.",
            },
        },
    }


def test_activity_glucose_correlations_calculates_paired_metrics():
    """Calculate correlations from paired activity and glucose outcome rows."""
    rows = [
        {
            "steps": 100,
            "calories_burned": 20.0,
            "avg_next_glucose": 9.0,
            "avg_glucose_delta_to_next": 2.0,
        },
        {
            "steps": 200,
            "calories_burned": 40.0,
            "avg_next_glucose": 8.0,
            "avg_glucose_delta_to_next": 1.0,
        },
        {
            "steps": 300,
            "calories_burned": 60.0,
            "avg_next_glucose": 7.0,
            "avg_glucose_delta_to_next": 0.0,
        },
    ]

    result = calculate_activity_glucose_correlations(rows)

    assert result == {
        "row_count": 3,
        "steps_vs_avg_next_glucose": -1.0,
        "calories_vs_avg_next_glucose": -1.0,
        "steps_vs_glucose_delta": -1.0,
        "calories_vs_glucose_delta": -1.0,
        "interpretations": {
            "steps_vs_avg_next_glucose": {
                "correlation": -1.0,
                "strength": "very_strong",
                "direction": "negative",
                "summary": "Higher steps values tend to align with lower glucose outcomes.",
            },
            "calories_vs_avg_next_glucose": {
                "correlation": -1.0,
                "strength": "very_strong",
                "direction": "negative",
                "summary": (
                    "Higher calories burned values tend to align with lower glucose outcomes."
                ),
            },
            "steps_vs_glucose_delta": {
                "correlation": -1.0,
                "strength": "very_strong",
                "direction": "negative",
                "summary": "Higher steps values tend to align with lower glucose outcomes.",
            },
            "calories_vs_glucose_delta": {
                "correlation": -1.0,
                "strength": "very_strong",
                "direction": "negative",
                "summary": (
                    "Higher calories burned values tend to align with lower glucose outcomes."
                ),
            },
        },
    }


def test_ranked_correlation_insights_orders_by_absolute_strength():
    """Return correlation insights ordered by strongest absolute coefficient."""
    metrics = {
        "interpretations": {
            "steps_vs_avg_next_glucose": {
                "correlation": -0.25,
                "strength": "weak",
                "direction": "negative",
                "summary": "Weak negative relationship.",
            },
            "calories_vs_glucose_delta": {
                "correlation": 0.75,
                "strength": "strong",
                "direction": "positive",
                "summary": "Strong positive relationship.",
            },
            "steps_vs_glucose_delta": {
                "correlation": None,
                "strength": "insufficient_data",
                "direction": "insufficient_data",
                "summary": "Not enough paired activity and glucose data yet.",
            },
        }
    }

    result = get_ranked_correlation_insights(metrics)

    assert [row["key"] for row in result] == [
        "calories_vs_glucose_delta",
        "steps_vs_avg_next_glucose",
        "steps_vs_glucose_delta",
    ]

    assert result[0] == {
        "key": "calories_vs_glucose_delta",
        "title": "Calories burned vs glucose change",
        "correlation": 0.75,
        "strength": "strong",
        "direction": "positive",
        "summary": "Strong positive relationship.",
    }
