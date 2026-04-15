from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import DailyActivity


def get_daily_activity() -> list[dict[str, Any]]:
    """Return daily activity rows ordered by activity_date ascending."""
    db = SessionLocal()

    try:
        stmt = select(DailyActivity).order_by(DailyActivity.activity_date.asc())
        rows = db.execute(stmt).scalars().all()

        return [
            {
                "activity_date": row.activity_date,
                "steps": row.steps or 0,
                "source": row.source or "",
            }
            for row in rows
        ]
    finally:
        db.close()


def get_activity_summary(target_steps: int = 10000) -> dict[str, Any]:
    """
    Return summary metrics derived from daily activity data.

    Metrics include:
    - average daily steps for the last 7 recorded days
    - total steps for the last 7 recorded days
    - best single day across all recorded activity
    - current streak of days meeting the target
    - change in total steps vs the previous 7-day window
    """
    daily_activity = get_daily_activity()

    if not daily_activity:
        return {
            "avg_steps_last_7": 0,
            "total_steps_last_7": 0,
            "best_day_steps": 0,
            "best_day_date": None,
            "streak_days": 0,
            "vs_previous_7_abs": 0,
            "vs_previous_7_pct": 0.0,
            "direction": "flat",
            "goal_days": 0,
            "goal_adherence_pct": 0.0,
        }

    latest_date = daily_activity[-1]["activity_date"]
    last_7_start = latest_date - timedelta(days=6)
    previous_7_start = latest_date - timedelta(days=13)
    previous_7_end = latest_date - timedelta(days=7)

    last_7_days = [
        row for row in daily_activity
        if last_7_start <= row["activity_date"] <= latest_date
    ]

    goal_days = sum(1 for row in last_7_days if row["steps"] >= target_steps)

    goal_adherence_pct = round((goal_days / len(last_7_days)) * 100, 1) if last_7_days else 0.0

    previous_7_days = [
        row for row in daily_activity
        if previous_7_start <= row["activity_date"] <= previous_7_end
    ]

    total_steps_last_7 = sum(row["steps"] for row in last_7_days)
    avg_steps_last_7 = round(total_steps_last_7 / len(last_7_days)) if last_7_days else 0

    total_steps_previous_7 = sum(row["steps"] for row in previous_7_days)
    vs_previous_7_abs = total_steps_last_7 - total_steps_previous_7

    if previous_7_days:
        if total_steps_previous_7 > 0:
            vs_previous_7_pct = round((vs_previous_7_abs / total_steps_previous_7) * 100, 1)
        else:
            vs_previous_7_pct = 0.0

        if vs_previous_7_abs > 0:
            direction = "up"
        elif vs_previous_7_abs < 0:
            direction = "down"
        else:
            direction = "flat"
    else:
        vs_previous_7_pct = 0.0
        direction = "flat"

    best_day = max(daily_activity, key=lambda row: row["steps"])

    streak_days = 0
    for row in reversed(daily_activity):
        if row["steps"] >= target_steps:
            streak_days += 1
        else:
            break

    return {
        "avg_steps_last_7": avg_steps_last_7,
        "total_steps_last_7": total_steps_last_7,
        "best_day_steps": best_day["steps"],
        "best_day_date": best_day["activity_date"].isoformat(),
        "streak_days": streak_days,
        "vs_previous_7_abs": vs_previous_7_abs,
        "vs_previous_7_pct": vs_previous_7_pct,
        "direction": direction,
        "has_previous_period": bool(previous_7_days),
        "goal_days": goal_days,
        "goal_adherence_pct": goal_adherence_pct
    }
