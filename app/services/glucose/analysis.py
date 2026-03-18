from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Any
import math

import numpy as np
import pandas as pd

from app.db.database import SessionLocal
from app.db.models import GlucoseReading
from app.services.event_classifier import classify_meal_event
from collections import defaultdict


MEAL_EVENT_LABELS = {
    "pre_breakfast": "Pre-Breakfast",
    "post_breakfast": "Post-Breakfast",
    "pre_lunch": "Pre-Lunch",
    "post_lunch": "Post-Lunch",
    "pre_dinner": "Pre-Dinner",
    "post_dinner": "Post-Dinner",
    "before_bed": "Before Bed",
    "night": "Night",
}

STANDARD_RATIOS = {
    "Pre-Breakfast": 9.0,
    "Pre-Lunch": 10.0,
    "Post-Lunch": 9.0,
    "Pre-Dinner": 10.0,
    "Before Bed": 10.0,
}


def get_all_glucose_readings():
    session = SessionLocal()

    try:
        return (
            session.query(GlucoseReading)
            .order_by(GlucoseReading.recorded_at.desc())
            .all()
        )
    finally:
        session.close()


def get_all_glucose_readings_with_meal_event(days: int | None = None):
    readings = get_all_glucose_readings()

    if days is not None:
        cutoff = datetime.now() - timedelta(days=days)
        readings = [
            reading
            for reading in readings
            if reading.recorded_at >= cutoff
        ]

    enriched_readings = []

    for reading in readings:
        meal_event_key = classify_meal_event(reading.recorded_at)

        enriched_readings.append(
            {
                "id": reading.id,
                "glucose_value": reading.glucose_value,
                "recorded_at": reading.recorded_at,
                "source": reading.source,
                "notes": reading.notes,
                "carbs_g": reading.carbs_g,
                "humalog_u": reading.humalog_u,
                "tresiba_u": reading.tresiba_u,
                "meal_event": meal_event_key,
                "meal_event_label": MEAL_EVENT_LABELS[meal_event_key],
                }
        )

    return enriched_readings


def get_glucose_reading_by_id(reading_id: int) -> GlucoseReading | None:
    session = SessionLocal()

    try:
        return session.query(GlucoseReading).filter(GlucoseReading.id == reading_id).first()
    finally:
        session.close()


def glucose_records_to_df(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert glucose records into a clean DataFrame.

    Expected fields:
    - id
    - glucose_value
    - recorded_at
    - meal_event
    """
    df = pd.DataFrame(records).copy()

    if df.empty:
        return pd.DataFrame(
            columns=[
                "id",
                "glucose_value",
                "recorded_at",
                "meal_event",
                "time_of_day_hours",
                "time_bucket_minute",
                "date",
            ]
        )

    df["recorded_at"] = pd.to_datetime(df["recorded_at"], errors="coerce")
    df["glucose_value"] = pd.to_numeric(df["glucose_value"], errors="coerce")
    df = df.dropna(subset=["recorded_at", "glucose_value"]).copy()

    df["date"] = df["recorded_at"].dt.date
    df["time_of_day_hours"] = (
        df["recorded_at"].dt.hour
        + df["recorded_at"].dt.minute / 60
        + df["recorded_at"].dt.second / 3600
    )

    # Rounded to bucket for AGP/profile charts
    df["time_bucket_minute"] = (
        df["recorded_at"].dt.hour * 60
        + df["recorded_at"].dt.minute
    )

    return df.sort_values("recorded_at").reset_index(drop=True)


def calculate_agp(
    df: pd.DataFrame,
    bucket_minutes: int = 15
) -> pd.DataFrame:
    """
    Calculate AGP percentile bands by time of day.

    Returns a DataFrame with:
    - bucket_minute
    - time_label
    - hour_decimal
    - p10
    - p25
    - p50
    - p75
    - p90
    - count
    """
    if df.empty:
        return pd.DataFrame(
            columns=[
                "bucket_minute", "time_label", "hour_decimal",
                "p10", "p25", "p50", "p75", "p90", "count"
            ]
        )

    working = df.copy()

    raw_minutes = (
        working["recorded_at"].dt.hour * 60
        + working["recorded_at"].dt.minute
    )

    working["bucket_minute"] = (raw_minutes // bucket_minutes) * bucket_minutes

    grouped = working.groupby("bucket_minute")["glucose_value"]

    agp = grouped.agg(
        p10=lambda s: s.quantile(0.10),
        p25=lambda s: s.quantile(0.25),
        p50=lambda s: s.quantile(0.50),
        p75=lambda s: s.quantile(0.75),
        p90=lambda s: s.quantile(0.90),
        count="count",
    ).reset_index()

    agp["hour_decimal"] = agp["bucket_minute"] / 60.0
    agp["time_label"] = agp["bucket_minute"].apply(
        lambda m: f"{m // 60:02d}:{m % 60:02d}"
    )

    return agp.sort_values("bucket_minute").reset_index(drop=True)


def calculate_time_in_range_breakdown(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """
    Returns percentage and count for clinically useful glucose bands.
    Thresholds are in mmol/L.
    """
    if df.empty:
        return {
            "hypo": {"count": 0, "pct": 0.0},
            "low": {"count": 0, "pct": 0.0},
            "target": {"count": 0, "pct": 0.0},
            "high": {"count": 0, "pct": 0.0},
            "hyper": {"count": 0, "pct": 0.0},
        }

    values = df["glucose_value"]
    total = len(values)

    counts = {
        "hypo": int((values < 3.3).sum()),
        "low": int(((values >= 3.3) & (values < 4.0)).sum()),
        "target": int(((values >= 4.0) & (values <= 10.0)).sum()),
        "high": int(((values > 10.0) & (values <= 15.0)).sum()),
        "hyper": int((values > 15.0).sum()),
    }

    return {
        key: {
            "count": count,
            "pct": round((count / total) * 100, 1) if total else 0.0,
        }
        for key, count in counts.items()
    }


def calculate_glucose_variability_metrics(df: pd.DataFrame) -> Dict[str, float | None]:
    """
    Calculate standard glucose variability metrics.

    Returns:
    - mean_glucose
    - sd
    - cv_pct
    - gmi
    """
    if df.empty:
        return {
            "mean_glucose": None,
            "sd": None,
            "cv_pct": None,
            "gmi": None,
        }

    values = df["glucose_value"].dropna()

    if values.empty:
        return {
            "mean_glucose": None,
            "sd": None,
            "cv_pct": None,
            "gmi": None,
        }

    mean_glucose = float(values.mean())
    sd = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    cv_pct = float((sd / mean_glucose) * 100) if mean_glucose > 0 else None

    # International consensus GMI formula for glucose in mmol/L
    # GMI (%) = 3.31 + 0.02392 × mean glucose (mg/dL)
    # mmol/L -> mg/dL = mmol/L * 18
    mean_mgdl = mean_glucose * 18.0
    gmi = 3.31 + (0.02392 * mean_mgdl)

    return {
        "mean_glucose": round(mean_glucose, 2),
        "sd": round(sd, 2),
        "cv_pct": round(cv_pct, 1) if cv_pct is not None else None,
        "gmi": round(gmi, 2),
    }


def calculate_insulin_effectiveness(readings: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(readings)

    if df.empty:
        return pd.DataFrame()

    df = df.sort_values("recorded_at").copy()

    df["prev_carbs"] = df["carbs_g"].shift(1)
    df["prev_humalog"] = df["humalog_u"].shift(1)
    df["prev_event"] = df["meal_event_label"].shift(1)

    df = df[
        df["prev_carbs"].notna()
        & df["prev_humalog"].notna()
        & (df["prev_humalog"] > 0)
    ].copy()

    if df.empty:
        return pd.DataFrame()

    df["ratio_g_per_u"] = df["prev_carbs"] / df["prev_humalog"]

    result = (
        df.groupby("prev_event")
        .agg(
            avg_ratio_g_per_u=("ratio_g_per_u", "mean"),
            ratio_sd=("ratio_g_per_u", "std"),
            avg_outcome_glucose=("glucose_value", "mean"),
            count=("id", "count"),
        )
        .reset_index()
        .rename(columns={"prev_event": "meal_event_label"})
    )

    result["standard_ratio_g_per_u"] = result["meal_event_label"].map(STANDARD_RATIOS)

    return result


def calculate_glucose_dashboard_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "range_breakdown": calculate_time_in_range_breakdown(df),
        "variability": calculate_glucose_variability_metrics(df),
        "agp": calculate_agp(df),
    }


def update_glucose_note(reading_id: int, notes: str | None) -> None:
    session = SessionLocal()

    try:
        reading = session.query(GlucoseReading).filter(GlucoseReading.id == reading_id).first()

        if reading is None:
            return

        reading.notes = notes or None
        session.commit()
    finally:
        session.close()


def get_glucose_summary():
    session = SessionLocal()

    try:
        readings = session.query(GlucoseReading).all()

        if not readings:
            return None

        values = [r.glucose_value for r in readings]

        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }
    finally:
        session.close()


def get_daily_average_glucose(readings):
    daily = defaultdict(list)

    for r in readings:
        day = r["recorded_at"].date()
        daily[day].append(r["glucose_value"])

    results = []

    for day, values in sorted(daily.items()):
        results.append(
            {
                "date": day,
                "avg": sum(values) / len(values),
                "count": len(values),
            }
        )

    return results


def get_time_of_day_profile(
    readings: list[dict],
    bucket_minutes: int = 30,
) -> list[dict]:
    buckets: dict[int, list[float]] = {}

    for reading in readings:
        dt = reading["recorded_at"]
        minutes_since_midnight = dt.hour * 60 + dt.minute

        bucket_start = (minutes_since_midnight // bucket_minutes) * bucket_minutes
        buckets.setdefault(bucket_start, []).append(reading["glucose_value"])

    profile = []

    for bucket_start in sorted(buckets.keys()):
        values = buckets[bucket_start]
        hour = bucket_start // 60
        minute = bucket_start % 60

        profile.append(
            {
                "bucket_minutes": bucket_start,
                "time_label": f"{hour:02d}:{minute:02d}",
                "avg": sum(values) / len(values),
                "count": len(values),
                "values": values,
            }
        )

    return profile


def get_meal_event_boxplot_data(readings: list[dict]) -> list[dict]:
    meal_order = [
        "Pre-Breakfast",
        "Post-Breakfast",
        "Pre-Lunch",
        "Post-Lunch",
        "Pre-Dinner",
        "Post-Dinner",
    ]

    grouped = {meal: [] for meal in meal_order}

    for reading in readings:
        meal_event = reading["meal_event_label"]

        if meal_event in grouped:
            grouped[meal_event].append(reading["glucose_value"])

    results = []

    for meal in meal_order:
        values = grouped[meal]
        if values:
            results.append(
                {
                    "meal_event": meal,
                    "values": values,
                }
            )

    return results


def get_time_in_range_metrics(readings: list[dict]) -> dict[str, float | int]:
    total = len(readings)

    metrics = {
        "total": total,
        "hypo_count": 0,
        "low_count": 0,
        "target_count": 0,
        "high_count": 0,
        "hyper_count": 0,
        "hypo_pct": 0.0,
        "low_pct": 0.0,
        "target_pct": 0.0,
        "high_pct": 0.0,
        "hyper_pct": 0.0,
    }

    if total == 0:
        return metrics

    for reading in readings:
        value = reading["glucose_value"]

        if value < 3.3:
            metrics["hypo_count"] += 1
        elif value < 4:
            metrics["low_count"] += 1
        elif value <= 10:
            metrics["target_count"] += 1
        elif value <= 15:
            metrics["high_count"] += 1
        else:
            metrics["hyper_count"] += 1

    metrics["hypo_pct"] = metrics["hypo_count"] / total * 100
    metrics["low_pct"] = metrics["low_count"] / total * 100
    metrics["target_pct"] = metrics["target_count"] / total * 100
    metrics["high_pct"] = metrics["high_count"] / total * 100
    metrics["hyper_pct"] = metrics["hyper_count"] / total * 100

    return metrics


def update_glucose_field(reading_id: int, field_name: str, value: float | None) -> None:
    session = SessionLocal()

    try:
        reading = session.query(GlucoseReading).filter(GlucoseReading.id == reading_id).first()

        if reading is None:
            return

        setattr(reading, field_name, value)

        session.commit()
    finally:
        session.close()
