from datetime import date, datetime

from app.services.environment.analysis import (
    calculate_daily_temperature_glucose_alignment,
    calculate_glucose_by_temperature_bucket,
    classify_temperature_bucket,
)


def test_temperature_bucket_classification():
    """Classify temperatures into cold, mild, warm, and hot buckets."""
    assert classify_temperature_bucket(7.9) == "cold"
    assert classify_temperature_bucket(8.0) == "mild"
    assert classify_temperature_bucket(14.9) == "mild"
    assert classify_temperature_bucket(15.0) == "warm"
    assert classify_temperature_bucket(21.9) == "warm"
    assert classify_temperature_bucket(22.0) == "hot"


def test_temperature_glucose_alignment_matches_by_date():
    """Align glucose readings onto matching daily temperature rows."""
    temperature_rows = [
        {
            "environment_date": date(2026, 5, 12),
            "avg_temperature_c": 12.0,
            "min_temperature_c": 8.0,
            "max_temperature_c": 16.0,
        }
    ]

    glucose_rows = [
        {
            "id": 1,
            "recorded_at": datetime(2026, 5, 12, 8, 0),
            "glucose_value": 6.0,
        },
        {
            "id": 2,
            "recorded_at": datetime(2026, 5, 12, 12, 0),
            "glucose_value": 8.0,
        },
    ]

    result = calculate_daily_temperature_glucose_alignment(
        temperature_rows=temperature_rows,
        glucose_rows=glucose_rows,
    )

    assert result == [
        {
            "date": date(2026, 5, 12),
            "avg_temperature_c": 12.0,
            "min_temperature_c": 8.0,
            "max_temperature_c": 16.0,
            "temperature_bucket": "mild",
            "temperature_bucket_label": "Mild",
            "glucose_count": 2,
            "avg_glucose": 7.0,
            "min_glucose": 6.0,
            "max_glucose": 8.0,
            "glucose_readings": glucose_rows,
        }
    ]


def test_temperature_glucose_alignment_handles_missing_glucose_rows():
    """Return temperature rows with null glucose metrics when no glucose matches."""
    temperature_rows = [
        {
            "environment_date": date(2026, 5, 12),
            "avg_temperature_c": 5.0,
            "min_temperature_c": 2.0,
            "max_temperature_c": 7.0,
        }
    ]

    result = calculate_daily_temperature_glucose_alignment(
        temperature_rows=temperature_rows,
        glucose_rows=[],
    )

    assert result == [
        {
            "date": date(2026, 5, 12),
            "avg_temperature_c": 5.0,
            "min_temperature_c": 2.0,
            "max_temperature_c": 7.0,
            "temperature_bucket": "cold",
            "temperature_bucket_label": "Cold",
            "glucose_count": 0,
            "avg_glucose": None,
            "min_glucose": None,
            "max_glucose": None,
            "glucose_readings": [],
        }
    ]


def test_glucose_by_temperature_bucket_calculates_average_glucose():
    """Aggregate average glucose by temperature bucket."""
    temperature_rows = [
        {
            "environment_date": date(2026, 5, 12),
            "avg_temperature_c": 12.0,
        },
        {
            "environment_date": date(2026, 5, 13),
            "avg_temperature_c": 18.0,
        },
    ]

    glucose_rows = [
        {
            "id": 1,
            "recorded_at": datetime(2026, 5, 12, 8, 0),
            "glucose_value": 6.0,
        },
        {
            "id": 2,
            "recorded_at": datetime(2026, 5, 12, 12, 0),
            "glucose_value": 8.0,
        },
        {
            "id": 3,
            "recorded_at": datetime(2026, 5, 13, 8, 0),
            "glucose_value": 10.0,
        },
    ]

    aligned_rows = calculate_daily_temperature_glucose_alignment(
        temperature_rows=temperature_rows,
        glucose_rows=glucose_rows,
    )

    result = calculate_glucose_by_temperature_bucket(aligned_rows)

    mild_row = result[1]
    warm_row = result[2]

    assert mild_row["temperature_bucket"] == "mild"
    assert mild_row["day_count"] == 1
    assert mild_row["glucose_count"] == 2
    assert mild_row["avg_temperature_c"] == 12.0
    assert mild_row["avg_glucose"] == 7.0

    assert warm_row["temperature_bucket"] == "warm"
    assert warm_row["day_count"] == 1
    assert warm_row["glucose_count"] == 1
    assert warm_row["avg_temperature_c"] == 18.0
    assert warm_row["avg_glucose"] == 10.0


def test_glucose_by_temperature_bucket_calculates_tir_breakdown():
    """Calculate time-in-range percentages per temperature bucket."""
    temperature_rows = [
        {
            "environment_date": date(2026, 5, 12),
            "avg_temperature_c": 24.0,
        }
    ]

    glucose_rows = [
        {
            "id": 1,
            "recorded_at": datetime(2026, 5, 12, 8, 0),
            "glucose_value": 3.0,
        },
        {
            "id": 2,
            "recorded_at": datetime(2026, 5, 12, 9, 0),
            "glucose_value": 3.5,
        },
        {
            "id": 3,
            "recorded_at": datetime(2026, 5, 12, 10, 0),
            "glucose_value": 7.0,
        },
        {
            "id": 4,
            "recorded_at": datetime(2026, 5, 12, 11, 0),
            "glucose_value": 12.0,
        },
        {
            "id": 5,
            "recorded_at": datetime(2026, 5, 12, 12, 0),
            "glucose_value": 16.0,
        },
    ]

    aligned_rows = calculate_daily_temperature_glucose_alignment(
        temperature_rows=temperature_rows,
        glucose_rows=glucose_rows,
    )

    result = calculate_glucose_by_temperature_bucket(aligned_rows)

    hot_row = result[3]

    assert hot_row["temperature_bucket"] == "hot"
    assert hot_row["glucose_count"] == 5
    assert hot_row["hypo_pct"] == 20.0
    assert hot_row["low_pct"] == 20.0
    assert hot_row["target_pct"] == 20.0
    assert hot_row["high_pct"] == 20.0
    assert hot_row["hyper_pct"] == 20.0


def test_glucose_by_temperature_bucket_preserves_bucket_order():
    """Return temperature buckets in cold, mild, warm, hot order."""
    temperature_rows = [
        {
            "environment_date": date(2026, 5, 12),
            "avg_temperature_c": 24.0,
        },
        {
            "environment_date": date(2026, 5, 13),
            "avg_temperature_c": 5.0,
        },
        {
            "environment_date": date(2026, 5, 14),
            "avg_temperature_c": 18.0,
        },
        {
            "environment_date": date(2026, 5, 15),
            "avg_temperature_c": 12.0,
        },
    ]

    aligned_rows = calculate_daily_temperature_glucose_alignment(
        temperature_rows=temperature_rows,
        glucose_rows=[],
    )

    result = calculate_glucose_by_temperature_bucket(aligned_rows)

    assert [row["temperature_bucket"] for row in result] == [
        "cold",
        "mild",
        "warm",
        "hot",
    ]
