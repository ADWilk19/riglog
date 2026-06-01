"""CSV import helpers for Nutrition data."""

from __future__ import annotations

import csv

from app.db.database import SessionLocal
from app.db.models import Food


REQUIRED_FOOD_COLUMNS = {
    "name",
    "calories_per_100g",
    "carbs_per_100g",
    "protein_per_100g",
    "fat_per_100g",
    "fibre_per_100g",
    "salt_per_100g",
}


def _clean_text(value: str | None) -> str | None:
    """Return stripped text or None for blank values."""
    if value is None:
        return None

    stripped = value.strip()
    return stripped or None


def _parse_float(value: str | None, column_name: str) -> float:
    """Parse a required numeric CSV value."""
    if value is None or value.strip() == "":
        raise ValueError(f"Missing required numeric value for {column_name}.")

    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid numeric value for {column_name}: {value}") from exc

    if parsed < 0:
        raise ValueError(f"{column_name} cannot be negative.")

    return parsed


def _validate_required_columns(fieldnames: list[str] | None) -> None:
    """Validate that the food CSV contains required columns."""
    if fieldnames is None:
        raise ValueError("CSV file has no header row.")

    missing_columns = REQUIRED_FOOD_COLUMNS - set(fieldnames)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required columns: {missing_text}")


def import_foods_csv(file_path: str) -> int:
    """
    Import reusable foods from a CSV file.

    Duplicate foods are skipped using name + source.

    Args:
        file_path: Path to the food CSV file.

    Returns:
        Number of newly inserted foods.
    """
    session = SessionLocal()
    imported_count = 0
    seen_food_keys: set[tuple[str, str]] = set()

    try:
        with open(file_path, "r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            _validate_required_columns(reader.fieldnames)

            for row in reader:
                name = _clean_text(row.get("name"))

                if not name:
                    continue

                source = _clean_text(row.get("source")) or "manual_csv"

                food_key = (name, source)

                if food_key in seen_food_keys:
                    continue

                existing_food = (
                    session.query(Food)
                    .filter(
                        Food.name == name,
                        Food.source == source,
                    )
                    .first()
                )

                if existing_food is not None:
                    continue

                seen_food_keys.add(food_key)

                food = Food(
                    name=name,
                    brand=_clean_text(row.get("brand")),
                    serving_notes=_clean_text(row.get("serving_notes")),
                    calories_per_100g=_parse_float(
                        row.get("calories_per_100g"),
                        "calories_per_100g",
                    ),
                    carbs_per_100g=_parse_float(
                        row.get("carbs_per_100g"),
                        "carbs_per_100g",
                    ),
                    protein_per_100g=_parse_float(
                        row.get("protein_per_100g"),
                        "protein_per_100g",
                    ),
                    fat_per_100g=_parse_float(
                        row.get("fat_per_100g"),
                        "fat_per_100g",
                    ),
                    fibre_per_100g=_parse_float(
                        row.get("fibre_per_100g"),
                        "fibre_per_100g",
                    ),
                    salt_per_100g=_parse_float(
                        row.get("salt_per_100g"),
                        "salt_per_100g",
                    ),
                    source=source,
                    notes=_clean_text(row.get("notes")),
                )

                session.add(food)
                imported_count += 1

        session.commit()
        return imported_count

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()
