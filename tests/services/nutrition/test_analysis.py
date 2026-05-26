from types import SimpleNamespace

from app.services.nutrition.analysis import (
    calculate_food_totals,
    calculate_logged_meal_totals,
    calculate_meal_template_totals,
)


def test_calculate_food_totals_by_quantity():
    food = SimpleNamespace(
        calories_per_100g=370,
        carbs_per_100g=60,
        protein_per_100g=12,
        fat_per_100g=8,
        fibre_per_100g=6,
        salt_per_100g=0.1,
    )

    result = calculate_food_totals(food, quantity_g=50)

    assert result == {
        "calories": 185.0,
        "carbs_g": 30.0,
        "protein_g": 6.0,
        "fat_g": 4.0,
        "fibre_g": 3.0,
        "salt_g": 0.1,
    }


def test_calculate_food_totals_treats_missing_values_as_zero():
    food = SimpleNamespace(
        calories_per_100g=100,
        carbs_per_100g=None,
        protein_per_100g=5,
        fat_per_100g=None,
        fibre_per_100g=2,
        salt_per_100g=None,
    )

    result = calculate_food_totals(food, quantity_g=100)

    assert result == {
        "calories": 100.0,
        "carbs_g": 0.0,
        "protein_g": 5.0,
        "fat_g": 0.0,
        "fibre_g": 2.0,
        "salt_g": 0.0,
    }


def test_calculate_meal_template_totals_sums_food_items():
    oats = SimpleNamespace(
        calories_per_100g=370,
        carbs_per_100g=60,
        protein_per_100g=12,
        fat_per_100g=8,
        fibre_per_100g=6,
        salt_per_100g=0.1,
    )

    milk = SimpleNamespace(
        calories_per_100g=50,
        carbs_per_100g=5,
        protein_per_100g=3.5,
        fat_per_100g=1.8,
        fibre_per_100g=0,
        salt_per_100g=0.1,
    )

    meal_template = SimpleNamespace(
        items=[
            SimpleNamespace(food=oats, quantity_g=50),
            SimpleNamespace(food=milk, quantity_g=200),
        ]
    )

    result = calculate_meal_template_totals(meal_template)

    assert result == {
        "calories": 285.0,
        "carbs_g": 40.0,
        "protein_g": 13.0,
        "fat_g": 7.6,
        "fibre_g": 3.0,
        "salt_g": 0.3,
    }


def test_calculate_logged_meal_totals_applies_portion_multiplier():
    food = SimpleNamespace(
        calories_per_100g=200,
        carbs_per_100g=30,
        protein_per_100g=10,
        fat_per_100g=5,
        fibre_per_100g=4,
        salt_per_100g=0.2,
    )

    meal_template = SimpleNamespace(
        items=[
            SimpleNamespace(food=food, quantity_g=100),
        ]
    )

    meal_log = SimpleNamespace(
        meal_template=meal_template,
        portion_multiplier=1.5,
    )

    result = calculate_logged_meal_totals(meal_log)

    assert result == {
        "calories": 300.0,
        "carbs_g": 45.0,
        "protein_g": 15.0,
        "fat_g": 7.5,
        "fibre_g": 6.0,
        "salt_g": 0.3,
    }


def test_calculate_logged_meal_totals_defaults_missing_multiplier_to_one():
    food = SimpleNamespace(
        calories_per_100g=120,
        carbs_per_100g=20,
        protein_per_100g=4,
        fat_per_100g=2,
        fibre_per_100g=3,
        salt_per_100g=0.1,
    )

    meal_template = SimpleNamespace(
        items=[
            SimpleNamespace(food=food, quantity_g=100),
        ]
    )

    meal_log = SimpleNamespace(
        meal_template=meal_template,
        portion_multiplier=None,
    )

    result = calculate_logged_meal_totals(meal_log)

    assert result == {
        "calories": 120.0,
        "carbs_g": 20.0,
        "protein_g": 4.0,
        "fat_g": 2.0,
        "fibre_g": 3.0,
        "salt_g": 0.1,
    }
