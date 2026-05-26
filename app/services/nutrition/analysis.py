"""Nutrition calculation helpers for foods, meal templates, and meal logs."""

from __future__ import annotations

from typing import Any


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
