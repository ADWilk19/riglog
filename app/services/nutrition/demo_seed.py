"""Seed demo nutrition data from CSV files."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from app.db.database import SessionLocal
from app.db.models import Food, MealLog, MealTemplate, MealTemplateItem


DEMO_SOURCE = "demo_nutrition"
DEFAULT_DEMO_DATA_DIR = Path("data/demo")


def _read_csv_rows(file_path: Path) -> list[dict[str, str]]:
    """Read CSV rows from a file path."""
    with file_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def _to_float(value: str | None, default: float = 0.0) -> float:
    """Convert a CSV value to float, falling back to a default."""
    if value is None or value == "":
        return default

    return float(value)


def _to_int(value: str | None, default: int = 0) -> int:
    """Convert a CSV value to int, falling back to a default."""
    if value is None or value == "":
        return default

    return int(value)


def seed_demo_nutrition_data(
    demo_data_dir: Path | str = DEFAULT_DEMO_DATA_DIR,
) -> dict[str, int]:
    """
    Seed demo nutrition data from CSV files.

    The seed is idempotent for the demo dataset:
    - foods are matched by name + source
    - meal templates are matched by name
    - template items are only inserted when a template has no items
    - meal logs are matched by logged_at + meal_template_id + source

    Args:
        demo_data_dir: Directory containing the nutrition demo CSV files.

    Returns:
        Counts of newly inserted rows.
    """
    demo_data_path = Path(demo_data_dir)

    foods_path = demo_data_path / "nutrition_foods.csv"
    meal_templates_path = demo_data_path / "nutrition_meal_templates.csv"
    meal_template_items_path = demo_data_path / "nutrition_meal_template_items.csv"
    meal_logs_path = demo_data_path / "nutrition_meal_logs.csv"

    food_rows = _read_csv_rows(foods_path)
    meal_template_rows = _read_csv_rows(meal_templates_path)
    meal_template_item_rows = _read_csv_rows(meal_template_items_path)
    meal_log_rows = _read_csv_rows(meal_logs_path)

    inserted_counts = {
        "foods": 0,
        "meal_templates": 0,
        "meal_template_items": 0,
        "meal_logs": 0,
    }

    session = SessionLocal()

    try:
        foods_by_key: dict[str, Food] = {}
        templates_by_key: dict[str, MealTemplate] = {}

        for row in food_rows:
            source = row.get("source") or DEMO_SOURCE

            food = (
                session.query(Food)
                .filter(
                    Food.name == row["name"],
                    Food.source == source,
                )
                .first()
            )

            if food is None:
                food = Food(
                    name=row["name"],
                    brand=row.get("brand") or None,
                    serving_notes=row.get("serving_notes") or None,
                    calories_per_100g=_to_float(row.get("calories_per_100g")),
                    carbs_per_100g=_to_float(row.get("carbs_per_100g")),
                    protein_per_100g=_to_float(row.get("protein_per_100g")),
                    fat_per_100g=_to_float(row.get("fat_per_100g")),
                    fibre_per_100g=_to_float(row.get("fibre_per_100g")),
                    salt_per_100g=_to_float(row.get("salt_per_100g")),
                    source=source,
                    notes=row.get("notes") or None,
                )
                session.add(food)
                session.flush()
                inserted_counts["foods"] += 1

            foods_by_key[row["food_key"]] = food

        for row in meal_template_rows:
            meal_template = (
                session.query(MealTemplate)
                .filter(MealTemplate.name == row["name"])
                .first()
            )

            if meal_template is None:
                meal_template = MealTemplate(
                    name=row["name"],
                    description=row.get("description") or None,
                    default_meal_event=row.get("default_meal_event") or None,
                    notes=row.get("notes") or None,
                )
                session.add(meal_template)
                session.flush()
                inserted_counts["meal_templates"] += 1

            templates_by_key[row["meal_template_key"]] = meal_template

        template_has_items = {
            template_key: (
                session.query(MealTemplateItem)
                .filter(MealTemplateItem.meal_template_id == template.id)
                .count()
                > 0
            )
            for template_key, template in templates_by_key.items()
        }

        for row in meal_template_item_rows:
            template_key = row["meal_template_key"]

            if template_has_items[template_key]:
                continue

            item = MealTemplateItem(
                meal_template_id=templates_by_key[template_key].id,
                food_id=foods_by_key[row["food_key"]].id,
                quantity_g=_to_float(row.get("quantity_g")),
                display_order=_to_int(row.get("display_order")),
                notes=row.get("notes") or None,
            )
            session.add(item)
            inserted_counts["meal_template_items"] += 1

        for row in meal_log_rows:
            meal_template = templates_by_key[row["meal_template_key"]]
            logged_at = datetime.strptime(row["logged_at"], "%Y-%m-%d %H:%M:%S")
            source = row.get("source") or DEMO_SOURCE

            existing_log = (
                session.query(MealLog)
                .filter(
                    MealLog.logged_at == logged_at,
                    MealLog.meal_template_id == meal_template.id,
                    MealLog.source == source,
                )
                .first()
            )

            if existing_log is not None:
                continue

            meal_log = MealLog(
                logged_at=logged_at,
                meal_template_id=meal_template.id,
                meal_event=row.get("meal_event") or None,
                portion_multiplier=_to_float(row.get("portion_multiplier"), 1.0),
                source=source,
                notes=row.get("notes") or None,
            )
            session.add(meal_log)
            inserted_counts["meal_logs"] += 1

        session.commit()
        return inserted_counts

    finally:
        session.close()
