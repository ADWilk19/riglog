from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.activity.analysis import (
    ACTIVITY_EVENT_ORDER,
    get_steps_by_event_window,
)
from app.services.glucose.analysis import (
    get_all_glucose_readings_with_meal_event,
    get_time_in_range_metrics,
)


def _empty_cross_module_rows() -> list[dict[str, Any]]:
    return []


def _prepare_activity_event_df(activity_rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Return activity rows at date + meal-event grain."""
    if not activity_rows:
        return pd.DataFrame(
            columns=[
                "date",
                "event_key",
                "event_window",
                "steps",
                "calories_burned",
                "interval_count",
            ]
        )

    df = pd.DataFrame(activity_rows).copy()

    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["steps"] = pd.to_numeric(df["steps"], errors="coerce").fillna(0)
    df["calories_burned"] = pd.to_numeric(
        df["calories_burned"],
        errors="coerce",
    ).fillna(0)
    df["interval_count"] = pd.to_numeric(
        df["interval_count"],
        errors="coerce",
    ).fillna(0)

    return df


def _prepare_glucose_event_df(glucose_rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Return glucose rows enriched for same-window and next-reading outcomes."""
    if not glucose_rows:
        return pd.DataFrame(
            columns=[
                "date",
                "event_key",
                "event_window",
                "recorded_at",
                "glucose_value",
                "next_glucose_value",
                "glucose_delta_to_next",
            ]
        )

    df = pd.DataFrame(glucose_rows).copy()

    df["recorded_at"] = pd.to_datetime(df["recorded_at"], errors="coerce")
    df["glucose_value"] = pd.to_numeric(
        df["glucose_value"],
        errors="coerce",
    )

    df = df.dropna(subset=["recorded_at", "glucose_value"]).copy()

    df["date"] = df["recorded_at"].dt.date
    df["event_key"] = df["meal_event"]
    df["event_window"] = df["meal_event_label"]

    df = df.sort_values("recorded_at").reset_index(drop=True)

    df["next_glucose_value"] = df["glucose_value"].shift(-1)
    df["next_recorded_at"] = df["recorded_at"].shift(-1)
    df["glucose_delta_to_next"] = (
        df["next_glucose_value"] - df["glucose_value"]
    )

    return df


def _summarise_same_window_glucose(
    glucose_df: pd.DataFrame,
) -> pd.DataFrame:
    """Summarise glucose readings within each date + meal-event window."""
    if glucose_df.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "event_key",
                "same_window_glucose_count",
                "same_window_avg_glucose",
                "same_window_min_glucose",
                "same_window_max_glucose",
                "same_window_target_pct",
            ]
        )

    grouped_rows = []

    for (event_date, event_key), group in glucose_df.groupby(["date", "event_key"]):
        readings = group.to_dict(orient="records")
        tir = get_time_in_range_metrics(readings)

        grouped_rows.append(
            {
                "date": event_date,
                "event_key": event_key,
                "same_window_glucose_count": len(group),
                "same_window_avg_glucose": round(group["glucose_value"].mean(), 2),
                "same_window_min_glucose": round(group["glucose_value"].min(), 2),
                "same_window_max_glucose": round(group["glucose_value"].max(), 2),
                "same_window_target_pct": round(tir["target_pct"], 1),
            }
        )

    return pd.DataFrame(grouped_rows)


def _summarise_next_glucose_outcomes(
    glucose_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Summarise the next glucose reading after readings in each event window.

    This gives the first cross-module outcome contract:

        date + event window -> average next glucose reading
    """
    if glucose_df.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "event_key",
                "next_glucose_count",
                "avg_next_glucose",
                "avg_glucose_delta_to_next",
            ]
        )

    outcome_df = glucose_df.dropna(
        subset=["next_glucose_value", "glucose_delta_to_next"]
    ).copy()

    if outcome_df.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "event_key",
                "next_glucose_count",
                "avg_next_glucose",
                "avg_glucose_delta_to_next",
            ]
        )

    grouped = (
        outcome_df.groupby(["date", "event_key"], as_index=False)
        .agg(
            next_glucose_count=("next_glucose_value", "count"),
            avg_next_glucose=("next_glucose_value", "mean"),
            avg_glucose_delta_to_next=("glucose_delta_to_next", "mean"),
        )
    )

    grouped["avg_next_glucose"] = grouped["avg_next_glucose"].round(2)
    grouped["avg_glucose_delta_to_next"] = grouped[
        "avg_glucose_delta_to_next"
    ].round(2)

    return grouped


def calculate_activity_glucose_event_summary(
    activity_rows: list[dict[str, Any]],
    glucose_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Join activity and glucose data at date + meal-event grain.

    Returns one row per activity event window with same-window glucose metrics
    and next-reading glucose outcome metrics.
    """
    activity_df = _prepare_activity_event_df(activity_rows)
    glucose_df = _prepare_glucose_event_df(glucose_rows)

    if activity_df.empty:
        return _empty_cross_module_rows()

    same_window_df = _summarise_same_window_glucose(glucose_df)
    next_outcome_df = _summarise_next_glucose_outcomes(glucose_df)

    result = activity_df.merge(
        same_window_df,
        on=["date", "event_key"],
        how="left",
    ).merge(
        next_outcome_df,
        on=["date", "event_key"],
        how="left",
    )

    event_order = {
        event_window: index
        for index, event_window in enumerate(ACTIVITY_EVENT_ORDER)
    }

    result["event_order"] = result["event_window"].map(event_order)

    count_columns = [
        "same_window_glucose_count",
        "next_glucose_count",
    ]

    nullable_metric_columns = [
        "same_window_avg_glucose",
        "same_window_min_glucose",
        "same_window_max_glucose",
        "same_window_target_pct",
        "avg_next_glucose",
        "avg_glucose_delta_to_next",
    ]

    for column in count_columns:
        if column not in result.columns:
            result[column] = 0
        result[column] = result[column].fillna(0).astype(int)

    for column in nullable_metric_columns:
        if column not in result.columns:
            result[column] = None
        else:
            result[column] = result[column].astype(object)
            result[column] = result[column].where(
                pd.notna(result[column]),
                None,
            )

    result = result.sort_values(["date", "event_order"]).reset_index(drop=True)

    output_columns = [
        "date",
        "event_key",
        "event_window",
        "steps",
        "calories_burned",
        "interval_count",
        "same_window_glucose_count",
        "same_window_avg_glucose",
        "same_window_min_glucose",
        "same_window_max_glucose",
        "same_window_target_pct",
        "next_glucose_count",
        "avg_next_glucose",
        "avg_glucose_delta_to_next",
    ]

    return result[output_columns].to_dict(orient="records")


def get_activity_glucose_event_summary(
    start_date=None,
    end_date=None,
    glucose_days: int | None = 365,
) -> list[dict[str, Any]]:
    """
    DB-backed cross-module summary.

    This is the first public service-layer contract for Activity ↔ Glucose
    integration. Keep UI code away from this until the output has been tested.
    """
    activity_rows = get_steps_by_event_window(
        start_date=start_date,
        end_date=end_date,
    )
    glucose_rows = get_all_glucose_readings_with_meal_event(days=glucose_days)

    return calculate_activity_glucose_event_summary(
        activity_rows=activity_rows,
        glucose_rows=glucose_rows,
    )
