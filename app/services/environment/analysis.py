from __future__ import annotations

from datetime import date, datetime, timedelta

from app.db.database import SessionLocal
from app.db.models import DailyEnvironment
from app.services.glucose.analysis import (
    get_all_glucose_readings_with_meal_event,
    calculate_time_in_range_breakdown,
    )

from statistics import mean
from typing import Any

import pandas as pd


TEMPERATURE_BUCKET_ORDER = ["cold", "mild", "warm", "hot"]

TEMPERATURE_BUCKET_LABELS = {
    "cold": "Cold",
    "mild": "Mild",
    "warm": "Warm",
    "hot": "Hot",
}


def classify_temperature_bucket(avg_temperature_c: float) -> str:
    """
    Classify an average daily temperature into a broad temperature bucket.

    Buckets are intentionally simple for the first environmental hypothesis:
    - cold: < 8°C
    - mild: 8°C to < 15°C
    - warm: 15°C to < 22°C
    - hot: >= 22°C
    """
    if avg_temperature_c < 8:
        return "cold"

    if avg_temperature_c < 15:
        return "mild"

    if avg_temperature_c < 22:
        return "warm"

    return "hot"


def calculate_daily_temperature_glucose_alignment(
    temperature_rows: list[dict[str, Any]],
    glucose_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Align daily temperature rows with glucose readings by calendar date.

    Args:
        temperature_rows: Daily environment rows containing at least:
            ``environment_date`` and ``avg_temperature_c``.
        glucose_rows: Glucose reading rows containing at least:
            ``recorded_at`` and ``glucose_value``.

    Returns:
        One row per temperature day, with glucose readings aggregated onto
        the matching date.
    """
    glucose_by_date: dict[date, list[dict[str, Any]]] = {}

    for glucose_row in glucose_rows:
        recorded_at = glucose_row["recorded_at"]
        glucose_date = recorded_at.date()
        glucose_by_date.setdefault(glucose_date, []).append(glucose_row)

    aligned_rows = []

    for temperature_row in sorted(
        temperature_rows,
        key=lambda row: row["environment_date"],
    ):
        environment_date = temperature_row["environment_date"]
        avg_temperature_c = temperature_row["avg_temperature_c"]
        matching_glucose_rows = glucose_by_date.get(environment_date, [])
        glucose_values = [
            row["glucose_value"]
            for row in matching_glucose_rows
        ]

        temperature_bucket = classify_temperature_bucket(avg_temperature_c)

        if glucose_values:
            avg_glucose = round(mean(glucose_values), 2)
            min_glucose = min(glucose_values)
            max_glucose = max(glucose_values)
        else:
            avg_glucose = None
            min_glucose = None
            max_glucose = None

        aligned_rows.append(
            {
                "date": environment_date,
                "avg_temperature_c": avg_temperature_c,
                "min_temperature_c": temperature_row.get("min_temperature_c"),
                "max_temperature_c": temperature_row.get("max_temperature_c"),
                "temperature_bucket": temperature_bucket,
                "temperature_bucket_label": TEMPERATURE_BUCKET_LABELS[
                    temperature_bucket
                ],
                "glucose_count": len(glucose_values),
                "avg_glucose": avg_glucose,
                "min_glucose": min_glucose,
                "max_glucose": max_glucose,
                "glucose_readings": matching_glucose_rows,
            }
        )

    return aligned_rows


def calculate_glucose_by_temperature_bucket(
    aligned_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Aggregate aligned daily temperature/glucose rows by temperature bucket.

    Returns average glucose and time-in-range percentages per bucket.
    """
    rows_by_bucket: dict[str, list[dict[str, Any]]] = {
        bucket: []
        for bucket in TEMPERATURE_BUCKET_ORDER
    }

    for row in aligned_rows:
        bucket = row["temperature_bucket"]

        if bucket not in rows_by_bucket:
            continue

        rows_by_bucket[bucket].append(row)

    results = []

    for bucket in TEMPERATURE_BUCKET_ORDER:
        bucket_rows = rows_by_bucket[bucket]

        glucose_readings = [
            glucose_row
            for row in bucket_rows
            for glucose_row in row["glucose_readings"]
        ]

        glucose_values = [
            row["glucose_value"]
            for row in glucose_readings
        ]

        temperatures = [
            row["avg_temperature_c"]
            for row in bucket_rows
        ]

        if glucose_values:
            avg_glucose = round(mean(glucose_values), 2)
        else:
            avg_glucose = None

        if temperatures:
            avg_temperature_c = round(mean(temperatures), 2)
        else:
            avg_temperature_c = None

        tir_breakdown = calculate_time_in_range_breakdown(
            pd.DataFrame(glucose_readings)
        )

        results.append(
            {
                "temperature_bucket": bucket,
                "temperature_bucket_label": TEMPERATURE_BUCKET_LABELS[bucket],
                "day_count": len(bucket_rows),
                "glucose_count": len(glucose_values),
                "avg_temperature_c": avg_temperature_c,
                "avg_glucose": avg_glucose,
                "hypo_pct": tir_breakdown["hypo"]["pct"],
                "low_pct": tir_breakdown["low"]["pct"],
                "target_pct": tir_breakdown["target"]["pct"],
                "high_pct": tir_breakdown["high"]["pct"],
                "hyper_pct": tir_breakdown["hyper"]["pct"],
            }
        )

    return results


def get_daily_environment_rows(days: int | None = None) -> list[dict[str, Any]]:
    """
    Return persisted daily environment rows ordered by date.

    Args:
        days: Optional lookback window. When provided, only rows on or after
            today - days are included.

    Returns:
        List of dictionaries suitable for environmental analysis functions.
    """
    session = SessionLocal()

    try:
        query = session.query(DailyEnvironment)

        if days is not None:
            cutoff = (datetime.now() - timedelta(days=days)).date()
            query = query.filter(DailyEnvironment.environment_date >= cutoff)

        rows = query.order_by(DailyEnvironment.environment_date.asc()).all()

        return [
            {
                "id": row.id,
                "environment_date": row.environment_date,
                "avg_temperature_c": row.avg_temperature_c,
                "min_temperature_c": row.min_temperature_c,
                "max_temperature_c": row.max_temperature_c,
                "source": row.source,
                "notes": row.notes,
            }
            for row in rows
        ]

    finally:
        session.close()


def get_temperature_glucose_bucket_summary(
    days: int | None = 365,
) -> list[dict[str, Any]]:
    """
    Return glucose metrics grouped by daily temperature bucket.

    This is the database-backed entry point for the UI/reporting layer.
    """
    temperature_rows = get_daily_environment_rows(days=days)
    glucose_rows = get_all_glucose_readings_with_meal_event(days=days)

    aligned_rows = calculate_daily_temperature_glucose_alignment(
        temperature_rows=temperature_rows,
        glucose_rows=glucose_rows,
    )

    return calculate_glucose_by_temperature_bucket(aligned_rows)


def get_daily_temperature_glucose_alignment(
    days: int | None = 365,
) -> list[dict[str, Any]]:
    """
    Return daily temperature rows aligned with same-date glucose readings.

    This is useful for future charting/debugging where the UI needs the
    day-level aligned rows rather than bucket-level aggregates.
    """
    temperature_rows = get_daily_environment_rows(days=days)
    glucose_rows = get_all_glucose_readings_with_meal_event(days=days)

    return calculate_daily_temperature_glucose_alignment(
        temperature_rows=temperature_rows,
        glucose_rows=glucose_rows,
    )
