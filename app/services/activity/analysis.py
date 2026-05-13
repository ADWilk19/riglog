from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from statistics import mean, stdev

import pandas as pd

from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import DailyActivity, IntradayActivity
from app.services.event_classifier import classify_meal_event

ACTIVITY_EVENT_LABELS = {
    "pre_breakfast": "Pre-Breakfast",
    "post_breakfast": "Post-Breakfast",
    "pre_lunch": "Pre-Lunch",
    "post_lunch": "Post-Lunch",
    "pre_dinner": "Pre-Dinner",
    "post_dinner": "Post-Dinner",
    "before_bed": "Before Bed",
    "night": "Night",
}

ACTIVITY_EVENT_ORDER = [
    "Pre-Breakfast",
    "Post-Breakfast",
    "Pre-Lunch",
    "Post-Lunch",
    "Pre-Dinner",
    "Post-Dinner",
    "Before Bed",
    "Night",
]

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


def aggregate_weekly_steps(rows: list[dict]) -> list[dict]:
    """
    Aggregate daily activity rows into weekly totals.

    Weeks are labelled by their Monday start date.
    """
    if not rows:
        return []

    weekly_totals: dict[date, int] = {}

    for row in rows:
        activity_date = row["activity_date"]
        week_start = activity_date - timedelta(days=activity_date.weekday())
        weekly_totals[week_start] = weekly_totals.get(week_start, 0) + row["steps"]

    return [
        {
            "week_start": week_start,
            "steps": weekly_totals[week_start],
        }
        for week_start in sorted(weekly_totals)
    ]


def calculate_weekly_summary_metrics(rows: list[dict]) -> dict[str, int | str | None]:
    """
    Return best and worst weekly step totals from daily activity rows.

    Weeks are based on Monday start dates, matching aggregate_weekly_steps().
    """
    weekly_rows = aggregate_weekly_steps(rows)

    if not weekly_rows:
        return {
            "best_week_steps": 0,
            "best_week_start": None,
            "worst_week_steps": 0,
            "worst_week_start": None,
        }

    best_week = max(weekly_rows, key=lambda row: row["steps"])
    worst_week = min(weekly_rows, key=lambda row: row["steps"])

    return {
        "best_week_steps": best_week["steps"],
        "best_week_start": best_week["week_start"].isoformat(),
        "worst_week_steps": worst_week["steps"],
        "worst_week_start": worst_week["week_start"].isoformat(),
    }


def calculate_step_consistency_metrics(rows: list[dict]) -> dict[str, float | str | None]:
    """
    Return step consistency metrics from daily activity rows.

    Uses standard deviation and coefficient of variation to describe how
    variable daily step counts are.
    """
    if not rows:
        return {
            "step_mean": None,
            "step_sd": None,
            "step_cv_pct": None,
            "consistency_label": "No data",
        }

    step_values = [row["steps"] for row in rows]

    if len(step_values) == 1:
        return {
            "step_mean": float(step_values[0]),
            "step_sd": 0.0,
            "step_cv_pct": 0.0,
            "consistency_label": "Consistent",
        }

    step_mean = mean(step_values)
    step_sd = stdev(step_values)
    step_cv_pct = (step_sd / step_mean) * 100 if step_mean > 0 else 0.0

    if step_cv_pct < 25:
        consistency_label = "Consistent"
    elif step_cv_pct < 50:
        consistency_label = "Variable"
    else:
        consistency_label = "Highly variable"

    return {
        "step_mean": round(step_mean, 1),
        "step_sd": round(step_sd, 1),
        "step_cv_pct": round(step_cv_pct, 1),
        "consistency_label": consistency_label,
    }


def calculate_goal_adherence(
    rows: list[dict],
    days: int,
    target_steps: int = 10_000,
) -> dict[str, int | float]:
    """
    Calculate goal adherence for the latest N-day window in the supplied rows.

    The window is based on the latest recorded activity date, not today's date.
    """
    if not rows:
        return {
            "goal_days": 0,
            "total_days": 0,
            "goal_adherence_pct": 0.0,
        }

    sorted_rows = sorted(rows, key=lambda row: row["activity_date"])
    latest_date = sorted_rows[-1]["activity_date"]
    start_date = latest_date - timedelta(days=days - 1)

    window_rows = [
        row
        for row in sorted_rows
        if start_date <= row["activity_date"] <= latest_date
    ]

    if not window_rows:
        return {
            "goal_days": 0,
            "total_days": 0,
            "goal_adherence_pct": 0.0,
        }

    goal_days = sum(1 for row in window_rows if row["steps"] >= target_steps)

    return {
        "goal_days": goal_days,
        "total_days": len(window_rows),
        "goal_adherence_pct": round((goal_days / len(window_rows)) * 100, 1),
    }


def get_activity_insight_metrics(
    rows: list[dict],
    target_steps: int = 10_000,
) -> dict[str, Any]:
    """Return Phase 2 activity insight metrics."""
    adherence_last_7 = calculate_goal_adherence(
        rows,
        days=7,
        target_steps=target_steps,
    )
    adherence_last_14 = calculate_goal_adherence(
        rows,
        days=14,
        target_steps=target_steps,
    )

    weekly_summary = calculate_weekly_summary_metrics(rows)

    consistency = calculate_step_consistency_metrics(rows)

    return {
        "goal_adherence_last_7": adherence_last_7["goal_adherence_pct"],
        "goal_days_last_7": adherence_last_7["goal_days"],
        "total_days_last_7": adherence_last_7["total_days"],
        "goal_adherence_last_14": adherence_last_14["goal_adherence_pct"],
        "goal_days_last_14": adherence_last_14["goal_days"],
        "total_days_last_14": adherence_last_14["total_days"],
        "best_week_steps": weekly_summary["best_week_steps"],
        "best_week_start": weekly_summary["best_week_start"],
        "worst_week_steps": weekly_summary["worst_week_steps"],
        "worst_week_start": weekly_summary["worst_week_start"],
        "step_mean": consistency["step_mean"],
        "step_sd": consistency["step_sd"],
        "step_cv_pct": consistency["step_cv_pct"],
        "consistency_label": consistency["consistency_label"],
    }


def get_activity_summary(
    rows: list[dict],
    target_steps: int = 10000,
) -> dict[str, Any]:
    """
    Return summary metrics derived from daily activity data.

    Metrics include:
    - average daily steps for the last 7 recorded days
    - total steps for the last 7 recorded days
    - best single day across all recorded activity
    - current streak of days meeting the target
    - change in total steps vs the previous 7-day window
    """
    daily_activity = sorted(rows, key=lambda row: row["activity_date"])

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
            "has_previous_period": False,
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


def get_activity_summary_from_db(
    target_steps: int = 10000,
) -> dict[str, Any]:
    """Load daily activity rows from the database and return summary metrics."""
    rows = get_daily_activity()
    return get_activity_summary(rows, target_steps=target_steps)


def get_activity_summary_cards(
    rows: list[dict],
    target_steps: int = 10000,
) -> list[dict]:
    summary = get_activity_summary(rows, target_steps=target_steps)

    if summary["has_previous_period"]:
        if summary["direction"] == "up":
            change_value = f"↑ {abs(summary['vs_previous_7_pct']):.1f}%"
            change_variant = "success"
        elif summary["direction"] == "down":
            change_value = f"↓ {abs(summary['vs_previous_7_pct']):.1f}%"
            change_variant = "danger"
        else:
            change_value = "No change"
            change_variant = "neutral"
    else:
        change_value = "-"
        change_variant = "neutral"

    current_streak, longest_streak = calculate_step_streaks(
        rows,
        goal_steps=target_steps,
    )

    return [
        {
            "key": "goal_days",
            "title": "Goal Days (7d)",
            "value": str(summary["goal_days"]),
            "subtitle": f"{summary['goal_days']} / 7",
            "variant": "neutral",
        },
        {
            "key": "goal_adherence",
            "title": "Goal Adherence",
            "value": f"{summary['goal_adherence_pct']:.0f}%",
            "subtitle": f"{summary['goal_days']} / 7",
            "variant": (
                "success"
                if summary["goal_adherence_pct"] >= 70
                else "neutral"
            ),
        },
        {
            "key": "average_steps",
            "title": "Average Steps",
            "value": f"{summary['avg_steps_last_7']:,}",
            "variant": "neutral",
        },
        {
            "key": "seven_day_change",
            "title": "7-Day Change",
            "value": change_value,
            "subtitle": "vs previous 7d" if summary["has_previous_period"] else "",
            "variant": change_variant,
        },
        {
            "key": "best_day",
            "title": "Best Day",
            "value": f"{summary['best_day_steps']:,}",
            "subtitle": str(summary["best_day_date"]),
            "variant": "neutral",
        },
        {
            "key": "current_streak",
            "title": "Current Streak",
            "value": str(current_streak),
            "variant": "success" if current_streak > 0 else "neutral",
        },
        {
            "key": "longest_streak",
            "title": "Longest Streak",
            "value": str(longest_streak),
            "variant": "success" if longest_streak >= 7 else "neutral",
        },
    ]


def calculate_step_streaks(
    rows: list[dict],
    goal_steps: int = 10_000,
) -> tuple[int, int]:
    """
    Return (current_streak, longest_streak) for consecutive days meeting the goal.

    Assumes at most one row per day and uses activity_date.
    """
    if not rows:
        return 0, 0

    sorted_rows = sorted(rows, key=lambda row: row["activity_date"])
    qualifying_dates = [
        row["activity_date"]
        for row in sorted_rows
        if row["steps"] >= goal_steps
    ]

    if not qualifying_dates:
        return 0, 0

    longest_streak = 0
    current_run = 0
    previous_date = None

    for activity_date in qualifying_dates:
        if previous_date is None:
            current_run = 1
        elif (activity_date - previous_date).days == 1:
            current_run += 1
        else:
            current_run = 1

        longest_streak = max(longest_streak, current_run)
        previous_date = activity_date

    latest_date = sorted_rows[-1]["activity_date"]
    current_streak = 0
    qualifying_set = set(qualifying_dates)

    check_date = latest_date
    while check_date in qualifying_set:
        current_streak += 1
        check_date = check_date - timedelta(days=1)

    return current_streak, longest_streak


def get_intraday_activity_rows(
    start_date=None,
    end_date=None,
) -> list[dict]:
    """
    Return intraday activity rows ordered by timestamp.

    Args:
        start_date: Optional datetime/date lower bound.
        end_date: Optional datetime/date upper bound.

    Returns:
        List of dictionaries for service/UI consumption.
    """
    session = SessionLocal()

    try:
        query = session.query(IntradayActivity)

        if start_date is not None:
            query = query.filter(IntradayActivity.recorded_at >= start_date)

        if end_date is not None:
            query = query.filter(IntradayActivity.recorded_at <= end_date)

        rows = query.order_by(IntradayActivity.recorded_at.asc()).all()

        return [
            {
                "id": row.id,
                "recorded_at": row.recorded_at,
                "steps": row.steps,
                "calories_burned": row.calories_burned,
                "distance_km": row.distance_km,
                "source": row.source,
            }
            for row in rows
        ]

    finally:
        session.close()


def get_steps_by_hour(
    start_date=None,
    end_date=None,
) -> list[dict]:
    """
    Aggregate intraday activity into hourly step totals.

    Args:
        start_date: Optional datetime/date lower bound.
        end_date: Optional datetime/date upper bound.

    Returns:
        List of dictionaries containing date, hour, steps, and calories_burned.
    """
    rows = get_intraday_activity_rows(
        start_date=start_date,
        end_date=end_date,
    )

    if not rows:
        return []

    df = pd.DataFrame(rows)

    df["recorded_at"] = pd.to_datetime(df["recorded_at"], errors="coerce")
    df["steps"] = pd.to_numeric(df["steps"], errors="coerce").fillna(0)
    df["calories_burned"] = pd.to_numeric(
        df["calories_burned"],
        errors="coerce",
    ).fillna(0)

    df = df.dropna(subset=["recorded_at"]).copy()
    df["date"] = df["recorded_at"].dt.date
    df["hour"] = df["recorded_at"].dt.hour

    grouped = (
        df.groupby(["date", "hour"], as_index=False)
        .agg(
            steps=("steps", "sum"),
            calories_burned=("calories_burned", "sum"),
        )
        .sort_values(["date", "hour"])
    )

    grouped["calories_burned"] = grouped["calories_burned"].round(2)

    return grouped.to_dict(orient="records")


def get_steps_by_event_window(
    start_date=None,
    end_date=None,
) -> list[dict]:
    """
    Aggregate intraday activity into glucose-style event windows.

    Uses the shared meal-event classifier so activity and glucose can be
    aligned by the same time windows.

    Args:
        start_date: Optional datetime/date lower bound.
        end_date: Optional datetime/date upper bound.

    Returns:
        List of dictionaries containing date, event window, steps,
        calories_burned, and interval count.
    """
    rows = get_intraday_activity_rows(
        start_date=start_date,
        end_date=end_date,
    )

    if not rows:
        return []

    df = pd.DataFrame(rows)

    df["recorded_at"] = pd.to_datetime(df["recorded_at"], errors="coerce")
    df["steps"] = pd.to_numeric(df["steps"], errors="coerce").fillna(0)
    df["calories_burned"] = pd.to_numeric(
        df["calories_burned"],
        errors="coerce",
    ).fillna(0)

    df = df.dropna(subset=["recorded_at"]).copy()

    df["date"] = df["recorded_at"].dt.date
    df["event_key"] = df["recorded_at"].apply(classify_meal_event)
    df["event_window"] = df["event_key"].map(ACTIVITY_EVENT_LABELS)

    grouped = (
        df.groupby(["date", "event_key", "event_window"], as_index=False)
        .agg(
            steps=("steps", "sum"),
            calories_burned=("calories_burned", "sum"),
            interval_count=("id", "count"),
        )
    )

    grouped["event_order"] = grouped["event_window"].map(
        {label: index for index, label in enumerate(ACTIVITY_EVENT_ORDER)}
    )

    grouped = grouped.sort_values(["date", "event_order"])

    grouped["calories_burned"] = grouped["calories_burned"].round(2)

    return grouped[
        [
            "date",
            "event_key",
            "event_window",
            "steps",
            "calories_burned",
            "interval_count",
        ]
    ].to_dict(orient="records")
