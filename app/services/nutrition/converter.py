"""Converters for external nutrition datasets.

Converters produce RigLog-compatible food CSV files. They do not write directly
to the database.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path


RIGLOG_FOOD_COLUMNS = [
    "food_key",
    "name",
    "brand",
    "serving_notes",
    "calories_per_100g",
    "carbs_per_100g",
    "protein_per_100g",
    "fat_per_100g",
    "fibre_per_100g",
    "salt_per_100g",
    "source",
    "notes",
]


NORMALISED_SOURCE_COLUMNS = {
    "food_name",
    "calories_kcal_per_100g",
    "carbs_g_per_100g",
    "protein_g_per_100g",
    "fat_g_per_100g",
    "fibre_g_per_100g",
    "salt_g_per_100g",
}


def slugify_food_key(value: str) -> str:
    """Return a stable lowercase key for a food name."""
    cleaned = value.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    return cleaned.strip("_")


def _clean_text(value: str | None) -> str:
    """Return stripped text or an empty string."""
    if value is None:
        return ""

    return value.strip()


def _parse_float(value: str | None, column_name: str) -> float:
    """Parse a required non-negative numeric value."""
    if value is None or value.strip() == "":
        raise ValueError(f"Missing required numeric value for {column_name}.")

    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid numeric value for {column_name}: {value}") from exc

    if parsed < 0:
        raise ValueError(f"{column_name} cannot be negative.")

    return parsed


def _format_float(value: float) -> str:
    """Format a float for stable CSV output."""
    rounded = round(value, 2)

    if rounded.is_integer():
        return str(int(rounded))

    return str(rounded)


def validate_normalised_source_columns(fieldnames: list[str] | None) -> None:
    """Validate that the source CSV contains the expected normalised columns."""
    if fieldnames is None:
        raise ValueError("Source CSV file has no header row.")

    missing_columns = NORMALISED_SOURCE_COLUMNS - set(fieldnames)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required source columns: {missing_text}")


def convert_normalised_foods_csv_to_riglog_csv(
    input_path: str | Path,
    output_path: str | Path,
    source_name: str,
    food_group_filter: str | None = None,
) -> int:
    """
    Convert a normalised external food CSV into RigLog food CSV format.

    The input is expected to be a source-normalised CSV, not a raw provider
    export. Provider-specific adapters can be added later.

    Required input columns:
    - food_name
    - calories_kcal_per_100g
    - carbs_g_per_100g
    - protein_g_per_100g
    - fat_g_per_100g
    - fibre_g_per_100g
    - salt_g_per_100g

    Optional input columns:
    - brand
    - serving_notes
    - food_group
    - notes
    """
    input_file = Path(input_path)
    output_file = Path(output_path)

    converted_rows: list[dict[str, str]] = []

    with input_file.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        validate_normalised_source_columns(reader.fieldnames)

        for row in reader:
            food_name = _clean_text(row.get("food_name"))

            if not food_name:
                continue

            food_group = _clean_text(row.get("food_group"))

            if food_group_filter is not None:
                if food_group.lower() != food_group_filter.strip().lower():
                    continue

            calories = _parse_float(
                row.get("calories_kcal_per_100g"),
                "calories_kcal_per_100g",
            )
            carbs = _parse_float(row.get("carbs_g_per_100g"), "carbs_g_per_100g")
            protein = _parse_float(
                row.get("protein_g_per_100g"),
                "protein_g_per_100g",
            )
            fat = _parse_float(row.get("fat_g_per_100g"), "fat_g_per_100g")
            fibre = _parse_float(row.get("fibre_g_per_100g"), "fibre_g_per_100g")
            salt = _parse_float(row.get("salt_g_per_100g"), "salt_g_per_100g")

            notes_parts = []

            source_notes = _clean_text(row.get("notes"))
            if source_notes:
                notes_parts.append(source_notes)

            if food_group:
                notes_parts.append(f"Food group: {food_group}")

            converted_rows.append(
                {
                    "food_key": slugify_food_key(food_name),
                    "name": food_name,
                    "brand": _clean_text(row.get("brand")),
                    "serving_notes": (
                        _clean_text(row.get("serving_notes"))
                        or "External dataset values per 100g"
                    ),
                    "calories_per_100g": _format_float(calories),
                    "carbs_per_100g": _format_float(carbs),
                    "protein_per_100g": _format_float(protein),
                    "fat_per_100g": _format_float(fat),
                    "fibre_per_100g": _format_float(fibre),
                    "salt_per_100g": _format_float(salt),
                    "source": source_name,
                    "notes": " | ".join(notes_parts),
                }
            )

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=RIGLOG_FOOD_COLUMNS)
        writer.writeheader()
        writer.writerows(converted_rows)

    return len(converted_rows)
