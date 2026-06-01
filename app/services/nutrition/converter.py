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


NORMALISED_FOOD_COLUMNS = [
    "food_name",
    "brand",
    "serving_notes",
    "food_group",
    "calories_kcal_per_100g",
    "carbs_g_per_100g",
    "protein_g_per_100g",
    "fat_g_per_100g",
    "fibre_g_per_100g",
    "salt_g_per_100g",
    "notes",
]


COFID_COLUMN_ALIASES = {
    "food_name": [
        "Food Name",
        "Food name",
        "food_name",
        "Name",
    ],
    "food_group": [
        "Group",
        "Food Group",
        "Food group",
        "food_group",
    ],
    "description": [
        "Description",
        "description",
    ],
    "energy_kcal": [
        "Energy (kcal) (kcal)",
        "Energy (kcal)",
        "Energy kcal",
        "energy_kcal",
    ],
    "carbs": [
        "Carbohydrate (g)",
        "Carbohydrate",
        "Carbohydrates (g)",
        "carbs_g_per_100g",
    ],
    "protein": [
        "Protein (g)",
        "Protein",
        "protein_g_per_100g",
    ],
    "fat": [
        "Fat (g)",
        "Fat",
        "fat_g_per_100g",
    ],
    "fibre": [
        "AOAC fibre (g)",
        "Fibre (g)",
        "Fiber (g)",
        "fibre_g_per_100g",
    ],
    "salt": [
        "Salt (g)",
        "salt_g_per_100g",
    ],
    "sodium_mg": [
        "Sodium (mg)",
        "Na (mg)",
        "sodium_mg",
    ],
    "food_code": [
        "Food Code",
        "Food code",
        "food_code",
    ],
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


def _get_first_available_value(
    row: dict[str, str],
    aliases: list[str],
) -> str | None:
    """Return the first non-empty value for a list of possible source columns."""
    for alias in aliases:
        value = row.get(alias)

        if value is not None and value.strip() != "":
            return value

    return None


def _get_required_alias_value(
    row: dict[str, str],
    canonical_name: str,
) -> str:
    """Return a required value using configured CoFID column aliases."""
    value = _get_first_available_value(row, COFID_COLUMN_ALIASES[canonical_name])

    if value is None:
        alias_text = ", ".join(COFID_COLUMN_ALIASES[canonical_name])
        raise ValueError(
            f"Missing required CoFID value for {canonical_name}. "
            f"Tried columns: {alias_text}"
        )

    return value


def _get_optional_alias_value(
    row: dict[str, str],
    canonical_name: str,
) -> str:
    """Return an optional value using configured CoFID column aliases."""
    value = _get_first_available_value(row, COFID_COLUMN_ALIASES[canonical_name])
    return _clean_text(value)


def _derive_salt_g_from_cofid_row(row: dict[str, str]) -> float:
    """
    Return salt in grams from a CoFID-style row.

    Prefer direct salt in grams where available. If only sodium in mg is
    available, convert sodium to salt using salt = sodium × 2.5.
    """
    salt_value = _get_first_available_value(row, COFID_COLUMN_ALIASES["salt"])

    if salt_value is not None:
        return _parse_float(salt_value, "Salt (g)")

    sodium_value = _get_first_available_value(row, COFID_COLUMN_ALIASES["sodium_mg"])

    if sodium_value is None:
        return 0.0

    sodium_mg = _parse_float(sodium_value, "Sodium (mg)")
    return sodium_mg * 2.5 / 1000


def convert_cofid_csv_to_normalised_csv(
    input_path: str | Path,
    output_path: str | Path,
    food_group_filter: str | None = None,
) -> int:
    """
    Convert a CoFID-style CSV export into RigLog's normalised food CSV format.

    This adapter does not write directly to the database. It prepares an
    intermediate normalised CSV that can then be passed to
    ``convert_normalised_foods_csv_to_riglog_csv``.

    Args:
        input_path: CoFID-style CSV export.
        output_path: Destination normalised food CSV.
        food_group_filter: Optional case-insensitive food group filter.

    Returns:
        Number of converted rows written.
    """
    input_file = Path(input_path)
    output_file = Path(output_path)

    converted_rows: list[dict[str, str]] = []

    with input_file.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)

        if reader.fieldnames is None:
            raise ValueError("CoFID CSV file has no header row.")

        for row in reader:
            food_name = _clean_text(
                _get_first_available_value(
                    row,
                    COFID_COLUMN_ALIASES["food_name"],
                )
            )

            if not food_name:
                continue

            food_group = _get_optional_alias_value(row, "food_group")

            if food_group_filter is not None:
                if food_group.lower() != food_group_filter.strip().lower():
                    continue

            food_code = _get_optional_alias_value(row, "food_code")
            description = _get_optional_alias_value(row, "description")

            calories = _parse_float(
                _get_required_alias_value(row, "energy_kcal"),
                "Energy (kcal)",
            )
            carbs = _parse_float(
                _get_required_alias_value(row, "carbs"),
                "Carbohydrate (g)",
            )
            protein = _parse_float(
                _get_required_alias_value(row, "protein"),
                "Protein (g)",
            )
            fat = _parse_float(
                _get_required_alias_value(row, "fat"),
                "Fat (g)",
            )
            fibre = _parse_float(
                _get_required_alias_value(row, "fibre"),
                "AOAC fibre (g)",
            )
            salt = _derive_salt_g_from_cofid_row(row)

            notes_parts = ["Converted from CoFID-style source data"]

            if food_code:
                notes_parts.append(f"Food code: {food_code}")

            converted_rows.append(
                {
                    "food_name": food_name,
                    "brand": "",
                    "serving_notes": description or "CoFID values per 100g",
                    "food_group": food_group,
                    "calories_kcal_per_100g": _format_float(calories),
                    "carbs_g_per_100g": _format_float(carbs),
                    "protein_g_per_100g": _format_float(protein),
                    "fat_g_per_100g": _format_float(fat),
                    "fibre_g_per_100g": _format_float(fibre),
                    "salt_g_per_100g": _format_float(salt),
                    "notes": " | ".join(notes_parts),
                }
            )

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=NORMALISED_FOOD_COLUMNS)
        writer.writeheader()
        writer.writerows(converted_rows)

    return len(converted_rows)
