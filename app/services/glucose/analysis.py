from datetime import time

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


def get_all_glucose_readings_with_meal_event():
    readings = get_all_glucose_readings()

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
