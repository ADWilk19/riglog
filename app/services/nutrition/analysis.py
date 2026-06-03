"""Nutrition calculation helpers for foods, meal templates, and meal logs."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.db.database import SessionLocal
from app.db.models import Food, GlucoseReading, MealLog, MealTemplate, MealTemplateItem

NUTRITION_FIELDS = [
    "calories",
    "carbs_g",
    "protein_g",
    "fat_g",
    "fibre_g",
    "salt_g",
]


def _empty_totals() -> dict[str, float]:
    """Return a zeroed nutrition totals dictionary."""
    return {field: 0.0 for field in NUTRITION_FIELDS}


def _round_totals(totals: dict[str, float]) -> dict[str, float]:
    """Round nutrition totals to one decimal place for stable display/tests."""
    return {
        field: round(value, 1)
        for field, value in totals.items()
    }


def calculate_food_totals(food: Any, quantity_g: float) -> dict[str, float]:
    """
    Calculate nutrition totals for a food quantity in grams.

    Food nutrition values are expected to be stored per 100g.

    Args:
        food: Object with per-100g nutrition attributes.
        quantity_g: Quantity consumed in grams.

    Returns:
        Dictionary containing calories and macro totals.
    """
    multiplier = quantity_g / 100

    totals = {
        "calories": (food.calories_per_100g or 0.0) * multiplier,
        "carbs_g": (food.carbs_per_100g or 0.0) * multiplier,
        "protein_g": (food.protein_per_100g or 0.0) * multiplier,
        "fat_g": (food.fat_per_100g or 0.0) * multiplier,
        "fibre_g": (food.fibre_per_100g or 0.0) * multiplier,
        "salt_g": (food.salt_per_100g or 0.0) * multiplier,
    }

    return _round_totals(totals)


def calculate_meal_template_totals(meal_template: Any) -> dict[str, float]:
    """
    Calculate total nutrition for a reusable meal template.

    Args:
        meal_template: Object with an ``items`` relationship. Each item must
            have ``food`` and ``quantity_g`` attributes.

    Returns:
        Dictionary containing summed calories and macro totals.
    """
    totals = _empty_totals()

    for item in meal_template.items:
        item_totals = calculate_food_totals(
            food=item.food,
            quantity_g=item.quantity_g,
        )

        for field in NUTRITION_FIELDS:
            totals[field] += item_totals[field]

    return _round_totals(totals)


def calculate_logged_meal_totals(meal_log: Any) -> dict[str, float]:
    """
    Calculate total nutrition for a logged meal.

    Applies the logged meal's portion multiplier to the reusable meal template
    totals.

    Args:
        meal_log: Object with ``meal_template`` and ``portion_multiplier``.

    Returns:
        Dictionary containing calories and macro totals for the logged portion.
    """
    template_totals = calculate_meal_template_totals(meal_log.meal_template)
    portion_multiplier = meal_log.portion_multiplier or 1.0

    totals = {
        field: value * portion_multiplier
        for field, value in template_totals.items()
    }

    return _round_totals(totals)


def get_meal_template_totals(meal_template_id: int) -> dict[str, float] | None:
    """
    Fetch a meal template by ID and calculate its nutrition totals.

    Args:
        meal_template_id: Database ID of the meal template.

    Returns:
        Nutrition totals dictionary, or ``None`` if the meal template is not found.
    """
    session = SessionLocal()

    try:
        meal_template = (
            session.query(MealTemplate)
            .filter(MealTemplate.id == meal_template_id)
            .first()
        )

        if meal_template is None:
            return None

        return calculate_meal_template_totals(meal_template)

    finally:
        session.close()


def get_logged_meal_totals(meal_log_id: int) -> dict[str, float] | None:
    """
    Fetch a logged meal by ID and calculate its portion-adjusted nutrition totals.

    Args:
        meal_log_id: Database ID of the logged meal.

    Returns:
        Nutrition totals dictionary, or ``None`` if the meal log is not found.
    """
    session = SessionLocal()

    try:
        meal_log = (
            session.query(MealLog)
            .filter(MealLog.id == meal_log_id)
            .first()
        )

        if meal_log is None:
            return None

        return calculate_logged_meal_totals(meal_log)

    finally:
        session.close()


def get_nutrition_summary_metrics(days: int | None = None) -> dict[str, Any]:
    """
    Calculate high-level nutrition summary metrics from logged meals.

    Args:
        days: Optional lookback window. When provided, only meal logs on or
            after ``now - days`` are included.

    Returns:
        Dictionary containing meal counts, nutrition totals, average daily
        carbs, and carbs grouped by meal event.
    """
    session = SessionLocal()

    try:
        query = session.query(MealLog).order_by(MealLog.logged_at.desc())

        if days is not None:
            cutoff = datetime.now() - timedelta(days=days)
            query = query.filter(MealLog.logged_at >= cutoff)

        meal_logs = query.all()

        summary = {
            "total_meals": len(meal_logs),
            "total_calories": 0.0,
            "total_carbs_g": 0.0,
            "total_protein_g": 0.0,
            "total_fat_g": 0.0,
            "average_daily_carbs_g": 0.0,
            "carbs_by_meal_event": {},
        }

        if not meal_logs:
            return summary

        carbs_by_date: dict[object, float] = {}

        for meal_log in meal_logs:
            totals = calculate_logged_meal_totals(meal_log)

            summary["total_calories"] += totals["calories"]
            summary["total_carbs_g"] += totals["carbs_g"]
            summary["total_protein_g"] += totals["protein_g"]
            summary["total_fat_g"] += totals["fat_g"]

            meal_date = meal_log.logged_at.date()
            carbs_by_date[meal_date] = (
                carbs_by_date.get(meal_date, 0.0) + totals["carbs_g"]
            )

            meal_event = meal_log.meal_event or "Uncategorised"
            summary["carbs_by_meal_event"][meal_event] = (
                summary["carbs_by_meal_event"].get(meal_event, 0.0)
                + totals["carbs_g"]
            )

        day_count = len(carbs_by_date)

        summary["total_calories"] = round(summary["total_calories"], 1)
        summary["total_carbs_g"] = round(summary["total_carbs_g"], 1)
        summary["total_protein_g"] = round(summary["total_protein_g"], 1)
        summary["total_fat_g"] = round(summary["total_fat_g"], 1)
        summary["average_daily_carbs_g"] = round(
            summary["total_carbs_g"] / day_count,
            1,
        )

        summary["carbs_by_meal_event"] = {
            meal_event: round(carbs_g, 1)
            for meal_event, carbs_g in summary["carbs_by_meal_event"].items()
        }

        return summary

    finally:
        session.close()


def get_recent_meal_logs(limit: int = 10) -> list[dict[str, Any]]:
    """
    Return recent logged meals with calculated nutrition totals.

    Args:
        limit: Maximum number of meal logs to return.

    Returns:
        List of dictionaries for UI display.
    """
    session = SessionLocal()

    try:
        meal_logs = (
            session.query(MealLog)
            .order_by(MealLog.logged_at.desc())
            .limit(limit)
            .all()
        )

        rows = []

        for meal_log in meal_logs:
            totals = calculate_logged_meal_totals(meal_log)

            rows.append(
                {
                    "id": meal_log.id,
                    "logged_at": meal_log.logged_at,
                    "meal_name": meal_log.meal_template.name,
                    "meal_event": meal_log.meal_event,
                    "portion_multiplier": meal_log.portion_multiplier,
                    "calories": totals["calories"],
                    "carbs_g": totals["carbs_g"],
                    "protein_g": totals["protein_g"],
                    "fat_g": totals["fat_g"],
                    "notes": meal_log.notes,
                }
            )

        return rows

    finally:
        session.close()


def get_meal_template_totals_rows() -> list[dict[str, Any]]:
    """
    Return all meal templates with calculated nutrition totals.

    Returns:
        List of dictionaries for UI display.
    """
    session = SessionLocal()

    try:
        meal_templates = (
            session.query(MealTemplate)
            .order_by(MealTemplate.name.asc())
            .all()
        )

        rows = []

        for meal_template in meal_templates:
            totals = calculate_meal_template_totals(meal_template)

            rows.append(
                {
                    "id": meal_template.id,
                    "name": meal_template.name,
                    "default_meal_event": meal_template.default_meal_event,
                    "calories": totals["calories"],
                    "carbs_g": totals["carbs_g"],
                    "protein_g": totals["protein_g"],
                    "fat_g": totals["fat_g"],
                    "fibre_g": totals["fibre_g"],
                    "salt_g": totals["salt_g"],
                }
            )

        return rows

    finally:
        session.close()


def get_meal_template_options() -> list[dict[str, Any]]:
    """
    Return reusable meal templates for UI selection.

    Returns:
        List of dictionaries containing meal template IDs and display labels.
    """
    session = SessionLocal()

    try:
        meal_templates = (
            session.query(MealTemplate)
            .order_by(MealTemplate.name.asc())
            .all()
        )

        return [
            {
                "id": meal_template.id,
                "name": meal_template.name,
                "default_meal_event": meal_template.default_meal_event,
                "display_name": meal_template.name,
            }
            for meal_template in meal_templates
        ]

    finally:
        session.close()


def create_meal_log(
    meal_template_id: int,
    logged_at: datetime,
    meal_event: str | None = None,
    portion_multiplier: float = 1.0,
    notes: str | None = None,
    source: str = "manual",
) -> MealLog:
    """
    Create and persist a logged meal from a reusable meal template.

    Args:
        meal_template_id: Database ID of the reusable meal template.
        logged_at: Timestamp when the meal was eaten.
        meal_event: Optional meal-event label.
        portion_multiplier: Portion multiplier applied to the meal template.
        notes: Optional notes.
        source: Source identifier.

    Returns:
        The created MealLog instance.
    """
    if portion_multiplier <= 0:
        raise ValueError("Portion multiplier must be greater than zero.")

    session = SessionLocal()

    try:
        meal_template = (
            session.query(MealTemplate)
            .filter(MealTemplate.id == meal_template_id)
            .first()
        )

        if meal_template is None:
            raise ValueError(f"Meal template ID {meal_template_id} was not found.")

        meal_log = MealLog(
            logged_at=logged_at,
            meal_template_id=meal_template_id,
            meal_event=meal_event.strip() if meal_event else None,
            portion_multiplier=portion_multiplier,
            notes=notes.strip() if notes else None,
            source=source,
        )

        session.add(meal_log)
        session.commit()
        session.refresh(meal_log)

        return meal_log

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def get_food_options() -> list[dict[str, Any]]:
    """
    Return reusable foods for UI selection.

    Returns:
        List of dictionaries containing food IDs and display labels.
    """
    session = SessionLocal()

    try:
        foods = session.query(Food).order_by(Food.name.asc()).all()

        return [
            {
                "id": food.id,
                "name": food.name,
                "brand": food.brand,
                "display_name": (
                    f"{food.name} ({food.brand})"
                    if food.brand
                    else food.name
                ),
            }
            for food in foods
        ]

    finally:
        session.close()


def create_meal_template(
    name: str,
    default_meal_event: str | None = None,
    description: str | None = None,
    notes: str | None = None,
    items: list[dict[str, float | int | str | None]] | None = None,
) -> MealTemplate:
    """
    Create a reusable meal template from selected foods.

    Args:
        name: Meal template name.
        default_meal_event: Optional default meal event.
        description: Optional description.
        notes: Optional notes.
        items: List of food item dictionaries. Each item should contain:
            - food_id
            - quantity_g
            - display_order, optional
            - notes, optional

    Returns:
        The created MealTemplate instance.
    """
    clean_name = name.strip()

    if not clean_name:
        raise ValueError("Meal name is required.")

    if not items:
        raise ValueError("At least one food item is required.")

    session = SessionLocal()

    try:
        meal_template = MealTemplate(
            name=clean_name,
            default_meal_event=(
                default_meal_event.strip()
                if default_meal_event
                else None
            ),
            description=description.strip() if description else None,
            notes=notes.strip() if notes else None,
        )

        session.add(meal_template)
        session.flush()

        for index, item in enumerate(items, start=1):
            food_id = int(item["food_id"])
            quantity_g = float(item["quantity_g"])

            if quantity_g <= 0:
                raise ValueError("Food quantity must be greater than zero.")

            food = session.query(Food).filter(Food.id == food_id).first()

            if food is None:
                raise ValueError(f"Food ID {food_id} was not found.")

            meal_item = MealTemplateItem(
                meal_template_id=meal_template.id,
                food_id=food_id,
                quantity_g=quantity_g,
                display_order=int(item.get("display_order") or index),
                notes=str(item.get("notes") or "").strip() or None,
            )

            session.add(meal_item)

        session.commit()
        session.refresh(meal_template)

        return meal_template

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def add_food(
    name: str,
    brand: str | None = None,
    serving_notes: str | None = None,
    calories_per_100g: float = 0.0,
    carbs_per_100g: float = 0.0,
    protein_per_100g: float = 0.0,
    fat_per_100g: float = 0.0,
    fibre_per_100g: float = 0.0,
    salt_per_100g: float = 0.0,
    source: str = "manual",
    notes: str | None = None,
) -> Food:
    """
    Create and persist a reusable food item.

    Args:
        name: Food name.
        brand: Optional brand.
        serving_notes: Optional serving description.
        calories_per_100g: Calories per 100g.
        carbs_per_100g: Carbohydrates per 100g.
        protein_per_100g: Protein per 100g.
        fat_per_100g: Fat per 100g.
        fibre_per_100g: Fibre per 100g.
        salt_per_100g: Salt per 100g.
        source: Source identifier.
        notes: Optional notes.

    Returns:
        The created Food instance.
    """
    clean_name = name.strip()

    if not clean_name:
        raise ValueError("Food name is required.")

    values = {
        "calories_per_100g": calories_per_100g,
        "carbs_per_100g": carbs_per_100g,
        "protein_per_100g": protein_per_100g,
        "fat_per_100g": fat_per_100g,
        "fibre_per_100g": fibre_per_100g,
        "salt_per_100g": salt_per_100g,
    }

    for field_name, value in values.items():
        if value < 0:
            raise ValueError(f"{field_name} cannot be negative.")

    session = SessionLocal()

    try:
        food = Food(
            name=clean_name,
            brand=brand.strip() if brand else None,
            serving_notes=serving_notes.strip() if serving_notes else None,
            calories_per_100g=calories_per_100g,
            carbs_per_100g=carbs_per_100g,
            protein_per_100g=protein_per_100g,
            fat_per_100g=fat_per_100g,
            fibre_per_100g=fibre_per_100g,
            salt_per_100g=salt_per_100g,
            source=source,
            notes=notes.strip() if notes else None,
        )

        session.add(food)
        session.commit()
        session.refresh(food)

        return food

    finally:
        session.close()


def _round_optional(value: float | None, digits: int = 1) -> float | None:
    """Round a numeric value when present, otherwise return None."""
    if value is None:
        return None

    return round(value, digits)


def _average(values: list[float]) -> float | None:
    """Return the average of a list of numeric values, or None when empty."""
    if not values:
        return None

    return sum(values) / len(values)


def _calculate_post_meal_response_for_log(
    meal_log: MealLog,
    glucose_readings: list[GlucoseReading],
    post_window_start_hours: int = 1,
    post_window_end_hours: int = 3,
) -> dict[str, Any]:
    """
    Calculate post-meal glucose response metrics for a single logged meal.

    The response window intentionally starts one hour after the meal and ends
    three hours after the meal, so immediate pre/post readings are not mixed
    into the post-meal response period.
    """
    totals = calculate_logged_meal_totals(meal_log)

    pre_meal_readings = [
        reading
        for reading in glucose_readings
        if reading.recorded_at <= meal_log.logged_at
    ]

    nearest_pre_meal = (
        max(pre_meal_readings, key=lambda reading: reading.recorded_at)
        if pre_meal_readings
        else None
    )

    post_window_start = meal_log.logged_at + timedelta(hours=post_window_start_hours)
    post_window_end = meal_log.logged_at + timedelta(hours=post_window_end_hours)

    post_meal_readings = [
        reading
        for reading in glucose_readings
        if post_window_start <= reading.recorded_at <= post_window_end
    ]

    post_values = [reading.glucose_value for reading in post_meal_readings]

    pre_meal_glucose = (
        nearest_pre_meal.glucose_value
        if nearest_pre_meal is not None
        else None
    )
    avg_post_meal_glucose = _average(post_values)
    peak_post_meal_glucose = max(post_values) if post_values else None

    glucose_delta = (
        avg_post_meal_glucose - pre_meal_glucose
        if avg_post_meal_glucose is not None and pre_meal_glucose is not None
        else None
    )

    return {
        "meal_log_id": meal_log.id,
        "logged_at": meal_log.logged_at,
        "meal_template_id": meal_log.meal_template_id,
        "meal_template_name": meal_log.meal_template.name,
        "meal_event": meal_log.meal_event,
        "portion_multiplier": meal_log.portion_multiplier,
        "calories": totals["calories"],
        "carbs_g": totals["carbs_g"],
        "protein_g": totals["protein_g"],
        "fat_g": totals["fat_g"],
        "fibre_g": totals["fibre_g"],
        "salt_g": totals["salt_g"],
        "pre_meal_glucose": _round_optional(pre_meal_glucose),
        "pre_meal_recorded_at": (
            nearest_pre_meal.recorded_at
            if nearest_pre_meal is not None
            else None
        ),
        "avg_post_meal_glucose": _round_optional(avg_post_meal_glucose),
        "peak_post_meal_glucose": _round_optional(peak_post_meal_glucose),
        "glucose_delta": _round_optional(glucose_delta),
        "reading_count": len(post_values),
    }


def get_post_meal_glucose_response_rows(
    days: int | None = None,
    post_window_start_hours: int = 1,
    post_window_end_hours: int = 3,
) -> list[dict[str, Any]]:
    """
    Return per-meal nutrition and post-meal glucose response rows.

    For each logged meal, this calculates:
    - nearest prior glucose reading
    - average glucose 1–3 hours after the meal
    - peak glucose 1–3 hours after the meal
    - glucose delta versus nearest prior reading
    - post-window reading count
    """
    session = SessionLocal()

    try:
        meal_query = session.query(MealLog).order_by(MealLog.logged_at.asc())

        if days is not None:
            cutoff = datetime.now() - timedelta(days=days)
            meal_query = meal_query.filter(MealLog.logged_at >= cutoff)

        meal_logs = meal_query.all()

        if not meal_logs:
            return []

        earliest_meal_time = min(meal_log.logged_at for meal_log in meal_logs)
        latest_meal_time = max(meal_log.logged_at for meal_log in meal_logs)

        glucose_readings = (
            session.query(GlucoseReading)
            .filter(
                GlucoseReading.recorded_at >= earliest_meal_time - timedelta(days=1),
                GlucoseReading.recorded_at <= (
                    latest_meal_time + timedelta(hours=post_window_end_hours)
                ),
            )
            .order_by(GlucoseReading.recorded_at.asc())
            .all()
        )

        return [
            _calculate_post_meal_response_for_log(
                meal_log=meal_log,
                glucose_readings=glucose_readings,
                post_window_start_hours=post_window_start_hours,
                post_window_end_hours=post_window_end_hours,
            )
            for meal_log in meal_logs
        ]

    finally:
        session.close()


def get_macro_glucose_response_by_meal_event(
    days: int | None = None,
) -> list[dict[str, Any]]:
    """
    Summarise nutrition and post-meal glucose response by meal event.

    Rows without post-meal glucose readings are excluded from the grouped
    response metrics.
    """
    rows = [
        row
        for row in get_post_meal_glucose_response_rows(days=days)
        if row["reading_count"] > 0
    ]

    grouped: dict[str, list[dict[str, Any]]] = {}

    for row in rows:
        meal_event = row["meal_event"] or "Uncategorised"
        grouped.setdefault(meal_event, []).append(row)

    results = []

    for meal_event, event_rows in grouped.items():
        deltas = [
            row["glucose_delta"]
            for row in event_rows
            if row["glucose_delta"] is not None
        ]

        results.append(
            {
                "meal_event": meal_event,
                "logged_count": len(event_rows),
                "average_calories": _round_optional(
                    _average([row["calories"] for row in event_rows])
                ),
                "average_carbs_g": _round_optional(
                    _average([row["carbs_g"] for row in event_rows])
                ),
                "average_protein_g": _round_optional(
                    _average([row["protein_g"] for row in event_rows])
                ),
                "average_fat_g": _round_optional(
                    _average([row["fat_g"] for row in event_rows])
                ),
                "average_fibre_g": _round_optional(
                    _average([row["fibre_g"] for row in event_rows])
                ),
                "average_post_meal_glucose": _round_optional(
                    _average([row["avg_post_meal_glucose"] for row in event_rows])
                ),
                "average_glucose_delta": _round_optional(_average(deltas)),
                "peak_post_meal_glucose": _round_optional(
                    max(row["peak_post_meal_glucose"] for row in event_rows)
                ),
                "total_reading_count": sum(row["reading_count"] for row in event_rows),
            }
        )

    return sorted(results, key=lambda row: row["meal_event"])


def get_meal_template_glucose_response_summary(
    days: int | None = None,
) -> list[dict[str, Any]]:
    """
    Summarise typical glucose response by reusable meal template.

    Rows without post-meal glucose readings are excluded from the grouped
    response metrics.
    """
    rows = [
        row
        for row in get_post_meal_glucose_response_rows(days=days)
        if row["reading_count"] > 0
    ]

    grouped: dict[int, list[dict[str, Any]]] = {}

    for row in rows:
        grouped.setdefault(row["meal_template_id"], []).append(row)

    results = []

    for meal_template_id, template_rows in grouped.items():
        deltas = [
            row["glucose_delta"]
            for row in template_rows
            if row["glucose_delta"] is not None
        ]

        results.append(
            {
                "meal_template_id": meal_template_id,
                "meal_template_name": template_rows[0]["meal_template_name"],
                "logged_count": len(template_rows),
                "average_carbs_g": _round_optional(
                    _average([row["carbs_g"] for row in template_rows])
                ),
                "average_calories": _round_optional(
                    _average([row["calories"] for row in template_rows])
                ),
                "average_post_meal_glucose": _round_optional(
                    _average([row["avg_post_meal_glucose"] for row in template_rows])
                ),
                "average_glucose_delta": _round_optional(_average(deltas)),
                "peak_post_meal_glucose": _round_optional(
                    max(row["peak_post_meal_glucose"] for row in template_rows)
                ),
                "total_reading_count": sum(
                    row["reading_count"] for row in template_rows
                ),
            }
        )

    return sorted(results, key=lambda row: row["meal_template_name"])
