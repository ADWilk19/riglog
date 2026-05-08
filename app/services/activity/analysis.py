from __future__ import annotations

from datetime import date, timedelta
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
