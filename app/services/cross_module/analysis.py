from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.activity.analysis import (
    ACTIVITY_EVENT_ORDER,
    get_intraday_activity_rows,
    get_steps_by_event_window,
)
from app.services.glucose.analysis import (
    get_all_glucose_readings_with_meal_event,
    get_time_in_range_metrics,
)

CORRELATION_METRIC_LABELS = {
    "steps_vs_avg_next_glucose": "Steps vs average next glucose",
    "calories_vs_avg_next_glucose": "Calories burned vs average next glucose",
    "steps_vs_glucose_delta": "Steps vs glucose change",
    "calories_vs_glucose_delta": "Calories burned vs glucose change",
}

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


def calculate_daily_activity_glucose_overlay(
    activity_rows: list[dict[str, Any]],
    glucose_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Join daily activity totals with daily average glucose.

    Returns one row per date where activity data exists. Glucose metrics are
    nullable so activity-only days can still be displayed safely.
    """
    if not activity_rows:
        return []

    activity_df = pd.DataFrame(activity_rows).copy()

    activity_df["date"] = pd.to_datetime(
        activity_df["activity_date"],
        errors="coerce",
    ).dt.date
    activity_df["steps"] = pd.to_numeric(
        activity_df["steps"],
        errors="coerce",
    ).fillna(0)
    if "calories_burned" not in activity_df.columns:
        activity_df["calories_burned"] = 0

    activity_df["calories_burned"] = pd.to_numeric(
        activity_df["calories_burned"],
        errors="coerce",
    ).fillna(0)

    activity_df = activity_df.dropna(subset=["date"]).copy()

    if activity_df.empty:
        return []

    glucose_df = pd.DataFrame(glucose_rows).copy()

    if glucose_df.empty:
        glucose_daily_df = pd.DataFrame(
            columns=[
                "date",
                "avg_glucose",
                "glucose_count",
                "min_glucose",
                "max_glucose",
            ]
        )
    else:
        glucose_df["recorded_at"] = pd.to_datetime(
            glucose_df["recorded_at"],
            errors="coerce",
        )
        glucose_df["glucose_value"] = pd.to_numeric(
            glucose_df["glucose_value"],
            errors="coerce",
        )

        glucose_df = glucose_df.dropna(
            subset=["recorded_at", "glucose_value"],
        ).copy()

        glucose_df["date"] = glucose_df["recorded_at"].dt.date

        glucose_daily_df = (
            glucose_df.groupby("date", as_index=False)
            .agg(
                avg_glucose=("glucose_value", "mean"),
                glucose_count=("glucose_value", "count"),
                min_glucose=("glucose_value", "min"),
                max_glucose=("glucose_value", "max"),
            )
        )

        glucose_daily_df["avg_glucose"] = glucose_daily_df["avg_glucose"].round(2)
        glucose_daily_df["min_glucose"] = glucose_daily_df["min_glucose"].round(2)
        glucose_daily_df["max_glucose"] = glucose_daily_df["max_glucose"].round(2)

    result = activity_df.merge(
        glucose_daily_df,
        on="date",
        how="left",
    )

    count_columns = ["glucose_count"]
    nullable_metric_columns = [
        "avg_glucose",
        "min_glucose",
        "max_glucose",
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

    result = result.sort_values("date").reset_index(drop=True)

    output_columns = [
        "date",
        "avg_glucose",
        "glucose_count",
        "min_glucose",
        "max_glucose",
        "steps",
        "calories_burned",
    ]

    return result[output_columns].to_dict(orient="records")


def calculate_intraday_activity_glucose_alignment(
    activity_rows: list[dict[str, Any]],
    glucose_rows: list[dict[str, Any]],
    bucket_minutes: int = 30,
) -> list[dict[str, Any]]:
    """
    Align intraday activity and glucose readings into shared time buckets.

    Returns one row per activity bucket. Glucose metrics are nullable so
    activity-only buckets can still be displayed safely.
    """
    if not activity_rows:
        return []

    activity_df = pd.DataFrame(activity_rows).copy()

    activity_df["recorded_at"] = pd.to_datetime(
        activity_df["recorded_at"],
        errors="coerce",
    )
    activity_df["steps"] = pd.to_numeric(
        activity_df["steps"],
        errors="coerce",
    ).fillna(0)

    if "calories_burned" not in activity_df.columns:
        activity_df["calories_burned"] = 0

    activity_df["calories_burned"] = pd.to_numeric(
        activity_df["calories_burned"],
        errors="coerce",
    ).fillna(0)

    activity_df = activity_df.dropna(subset=["recorded_at"]).copy()

    if activity_df.empty:
        return []

    activity_df["bucket_start"] = activity_df["recorded_at"].apply(
        lambda timestamp: _floor_timestamp_to_bucket(
            timestamp,
            bucket_minutes=bucket_minutes,
        )
    )

    activity_bucket_df = (
        activity_df.groupby("bucket_start", as_index=False)
        .agg(
            steps=("steps", "sum"),
            calories_burned=("calories_burned", "sum"),
            activity_interval_count=("recorded_at", "count"),
        )
    )

    glucose_df = pd.DataFrame(glucose_rows).copy()

    if glucose_df.empty:
        glucose_bucket_df = pd.DataFrame(
            columns=[
                "bucket_start",
                "glucose_count",
                "avg_glucose",
                "min_glucose",
                "max_glucose",
            ]
        )
    else:
        glucose_df["recorded_at"] = pd.to_datetime(
            glucose_df["recorded_at"],
            errors="coerce",
        )
        glucose_df["glucose_value"] = pd.to_numeric(
            glucose_df["glucose_value"],
            errors="coerce",
        )

        glucose_df = glucose_df.dropna(
            subset=["recorded_at", "glucose_value"],
        ).copy()

        if glucose_df.empty:
            glucose_bucket_df = pd.DataFrame(
                columns=[
                    "bucket_start",
                    "glucose_count",
                    "avg_glucose",
                    "min_glucose",
                    "max_glucose",
                ]
            )
        else:
            glucose_df["bucket_start"] = glucose_df["recorded_at"].apply(
                lambda timestamp: _floor_timestamp_to_bucket(
                    timestamp,
                    bucket_minutes=bucket_minutes,
                )
            )

            glucose_bucket_df = (
                glucose_df.groupby("bucket_start", as_index=False)
                .agg(
                    glucose_count=("glucose_value", "count"),
                    avg_glucose=("glucose_value", "mean"),
                    min_glucose=("glucose_value", "min"),
                    max_glucose=("glucose_value", "max"),
                )
            )

            glucose_bucket_df["avg_glucose"] = glucose_bucket_df[
                "avg_glucose"
            ].round(2)
            glucose_bucket_df["min_glucose"] = glucose_bucket_df[
                "min_glucose"
            ].round(2)
            glucose_bucket_df["max_glucose"] = glucose_bucket_df[
                "max_glucose"
            ].round(2)

    result = activity_bucket_df.merge(
        glucose_bucket_df,
        on="bucket_start",
        how="left",
    )

    result["date"] = pd.to_datetime(result["bucket_start"]).dt.date
    result["bucket_label"] = pd.to_datetime(
        result["bucket_start"]
    ).dt.strftime("%H:%M")

    count_columns = ["glucose_count"]
    nullable_metric_columns = [
        "avg_glucose",
        "min_glucose",
        "max_glucose",
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

    result["calories_burned"] = result["calories_burned"].round(2)

    result = result.sort_values("bucket_start").reset_index(drop=True)

    output_columns = [
        "date",
        "bucket_start",
        "bucket_label",
        "steps",
        "calories_burned",
        "activity_interval_count",
        "glucose_count",
        "avg_glucose",
        "min_glucose",
        "max_glucose",
    ]

    result["bucket_start"] = pd.to_datetime(
        result["bucket_start"],
        errors="coerce",
    ).dt.to_pydatetime()

    return result[output_columns].to_dict(orient="records")


def get_available_intraday_activity_dates() -> list:
    """Return available intraday activity dates ordered ascending."""
    rows = get_intraday_activity_rows()

    dates = sorted(
        {
            row["recorded_at"].date()
            for row in rows
            if row.get("recorded_at") is not None
        }
    )

    return dates


def get_intraday_activity_glucose_alignment(
    start_date=None,
    end_date=None,
    glucose_days: int | None = 365,
    bucket_minutes: int = 30,
) -> list[dict[str, Any]]:
    """
    DB-backed intraday activity/glucose alignment contract.
    """
    activity_rows = get_intraday_activity_rows(
        start_date=start_date,
        end_date=end_date,
    )
    glucose_rows = get_all_glucose_readings_with_meal_event(days=glucose_days)

    return calculate_intraday_activity_glucose_alignment(
        activity_rows=activity_rows,
        glucose_rows=glucose_rows,
        bucket_minutes=bucket_minutes,
    )


def get_daily_activity_glucose_overlay(
    glucose_days: int | None = 365,
) -> list[dict[str, Any]]:
    """
    DB-backed daily overlay contract for glucose/activity charting.
    """
    from app.services.activity.analysis import get_daily_activity

    activity_rows = get_daily_activity()
    glucose_rows = get_all_glucose_readings_with_meal_event(days=glucose_days)

    return calculate_daily_activity_glucose_overlay(
        activity_rows=activity_rows,
        glucose_rows=glucose_rows,
    )


def _floor_timestamp_to_bucket(
    timestamp,
    bucket_minutes: int,
):
    """Floor a timestamp to the nearest lower time bucket."""
    ts = pd.Timestamp(timestamp)

    total_minutes = ts.hour * 60 + ts.minute
    bucket_start_minutes = (total_minutes // bucket_minutes) * bucket_minutes

    return ts.replace(
        hour=bucket_start_minutes // 60,
        minute=bucket_start_minutes % 60,
        second=0,
        microsecond=0,
    ).to_pydatetime()


def classify_correlation_strength(correlation: float | None) -> str:
    """Return a simple strength label for a correlation coefficient."""
    if correlation is None:
        return "insufficient_data"

    absolute_value = abs(correlation)

    if absolute_value < 0.2:
        return "very_weak"
    if absolute_value < 0.4:
        return "weak"
    if absolute_value < 0.6:
        return "moderate"
    if absolute_value < 0.8:
        return "strong"

    return "very_strong"


def classify_correlation_direction(correlation: float | None) -> str:
    """Return the direction label for a correlation coefficient."""
    if correlation is None:
        return "insufficient_data"

    if correlation > 0:
        return "positive"
    if correlation < 0:
        return "negative"

    return "none"


def describe_correlation(
    label: str,
    correlation: float | None,
) -> dict[str, Any]:
    """Return a UI-ready interpretation for one correlation metric."""
    strength = classify_correlation_strength(correlation)
    direction = classify_correlation_direction(correlation)

    if correlation is None:
        summary = "Not enough paired activity and glucose data yet."
    elif correlation > 0:
        summary = f"Higher {label} values tend to align with higher glucose outcomes."
    elif correlation < 0:
        summary = f"Higher {label} values tend to align with lower glucose outcomes."
    else:
        summary = f"{label.title()} values do not show a clear directional relationship."

    return {
        "correlation": correlation,
        "strength": strength,
        "direction": direction,
        "summary": summary,
    }


def _empty_correlation_contract(row_count: int = 0) -> dict[str, Any]:
    """Return the empty/default correlation metrics contract."""
    return {
        "row_count": row_count,
        "steps_vs_avg_next_glucose": None,
        "calories_vs_avg_next_glucose": None,
        "steps_vs_glucose_delta": None,
        "calories_vs_glucose_delta": None,
        "interpretations": {
            "steps_vs_avg_next_glucose": describe_correlation("steps", None),
            "calories_vs_avg_next_glucose": describe_correlation(
                "calories burned",
                None,
            ),
            "steps_vs_glucose_delta": describe_correlation("steps", None),
            "calories_vs_glucose_delta": describe_correlation(
                "calories burned",
                None,
            ),
        },
    }


def get_ranked_correlation_insights(
    correlation_metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Return correlation interpretations ordered by strongest absolute relationship.

    This produces a UI-ready list while keeping analytical formatting in the
    service layer.
    """
    interpretations = correlation_metrics.get("interpretations", {})

    insight_rows = []

    for key, interpretation in interpretations.items():
        correlation = interpretation.get("correlation")

        insight_rows.append(
            {
                "key": key,
                "title": CORRELATION_METRIC_LABELS.get(key, key),
                "correlation": correlation,
                "strength": interpretation.get("strength"),
                "direction": interpretation.get("direction"),
                "summary": interpretation.get("summary"),
            }
        )

    return sorted(
        insight_rows,
        key=lambda row: (
            row["correlation"] is None,
            -abs(row["correlation"]) if row["correlation"] is not None else 0,
            row["title"],
        ),
    )


def calculate_activity_glucose_correlations(
    event_summary_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate simple correlation metrics from activity/glucose event summaries.

    Uses only rows with enough paired activity and glucose outcome data.
    """
    if not event_summary_rows:
        return _empty_correlation_contract()

    df = pd.DataFrame(event_summary_rows).copy()

    required_columns = [
        "steps",
        "calories_burned",
        "avg_next_glucose",
        "avg_glucose_delta_to_next",
    ]

    for column in required_columns:
        if column not in df.columns:
            return _empty_correlation_contract()

    for column in required_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    paired_df = df.dropna(subset=required_columns).copy()

    if len(paired_df) < 2:
        return _empty_correlation_contract(row_count=len(paired_df))

    steps_vs_avg_next_glucose = round(
        paired_df["steps"].corr(paired_df["avg_next_glucose"]),
        3,
    )
    calories_vs_avg_next_glucose = round(
        paired_df["calories_burned"].corr(paired_df["avg_next_glucose"]),
        3,
    )
    steps_vs_glucose_delta = round(
        paired_df["steps"].corr(paired_df["avg_glucose_delta_to_next"]),
        3,
    )
    calories_vs_glucose_delta = round(
        paired_df["calories_burned"].corr(
            paired_df["avg_glucose_delta_to_next"]
        ),
        3,
    )

    return {
        "row_count": len(paired_df),
        "steps_vs_avg_next_glucose": steps_vs_avg_next_glucose,
        "calories_vs_avg_next_glucose": calories_vs_avg_next_glucose,
        "steps_vs_glucose_delta": steps_vs_glucose_delta,
        "calories_vs_glucose_delta": calories_vs_glucose_delta,
        "interpretations": {
            "steps_vs_avg_next_glucose": describe_correlation(
                "steps",
                steps_vs_avg_next_glucose,
            ),
            "calories_vs_avg_next_glucose": describe_correlation(
                "calories burned",
                calories_vs_avg_next_glucose,
            ),
            "steps_vs_glucose_delta": describe_correlation(
                "steps",
                steps_vs_glucose_delta,
            ),
            "calories_vs_glucose_delta": describe_correlation(
                "calories burned",
                calories_vs_glucose_delta,
            ),
        },
    }


def get_activity_glucose_correlations(
    start_date=None,
    end_date=None,
    glucose_days: int | None = 365,
) -> dict[str, Any]:
    """
    DB-backed correlation metrics for Activity ↔ Glucose analysis.
    """
    event_summary_rows = get_activity_glucose_event_summary(
        start_date=start_date,
        end_date=end_date,
        glucose_days=glucose_days,
    )

    metrics = calculate_activity_glucose_correlations(event_summary_rows)
    metrics["ranked_insights"] = get_ranked_correlation_insights(metrics)

    return metrics
