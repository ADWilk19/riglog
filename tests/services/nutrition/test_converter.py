import csv

import pytest

from app.services.nutrition.converter import (
    RIGLOG_FOOD_COLUMNS,
    convert_normalised_foods_csv_to_riglog_csv,
    slugify_food_key,
)


def test_slugify_food_key_returns_stable_key():
    assert slugify_food_key("  Red Onion, raw  ") == "red_onion_raw"


def test_convert_normalised_foods_csv_to_riglog_csv_writes_riglog_format(tmp_path):
    input_path = tmp_path / "normalised_foods.csv"
    output_path = tmp_path / "riglog_foods.csv"

    input_path.write_text(
        """food_name,brand,serving_notes,food_group,calories_kcal_per_100g,carbs_g_per_100g,protein_g_per_100g,fat_g_per_100g,fibre_g_per_100g,salt_g_per_100g,notes
Broccoli,,Raw vegetable,Vegetables,34,7,2.8,0.4,2.6,0.08,Starter value
Carrot,,Raw vegetable,Vegetables,41,10,0.9,0.2,2.8,0.07,Starter value
""",
        encoding="utf-8",
    )

    converted_count = convert_normalised_foods_csv_to_riglog_csv(
        input_path=input_path,
        output_path=output_path,
        source_name="test_external_dataset",
    )

    assert converted_count == 2

    with output_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    assert reader.fieldnames == RIGLOG_FOOD_COLUMNS

    assert rows[0] == {
        "food_key": "broccoli",
        "name": "Broccoli",
        "brand": "",
        "serving_notes": "Raw vegetable",
        "calories_per_100g": "34",
        "carbs_per_100g": "7",
        "protein_per_100g": "2.8",
        "fat_per_100g": "0.4",
        "fibre_per_100g": "2.6",
        "salt_per_100g": "0.08",
        "source": "test_external_dataset",
        "notes": "Starter value | Food group: Vegetables",
    }

    assert rows[1]["food_key"] == "carrot"
    assert rows[1]["name"] == "Carrot"


def test_convert_normalised_foods_csv_filters_by_food_group(tmp_path):
    input_path = tmp_path / "normalised_foods.csv"
    output_path = tmp_path / "riglog_foods.csv"

    input_path.write_text(
        """food_name,brand,serving_notes,food_group,calories_kcal_per_100g,carbs_g_per_100g,protein_g_per_100g,fat_g_per_100g,fibre_g_per_100g,salt_g_per_100g,notes
Broccoli,,Raw vegetable,Vegetables,34,7,2.8,0.4,2.6,0.08,Starter value
Apple,,Raw fruit,Fruit,52,14,0.3,0.2,2.4,0.0,Starter value
""",
        encoding="utf-8",
    )

    converted_count = convert_normalised_foods_csv_to_riglog_csv(
        input_path=input_path,
        output_path=output_path,
        source_name="test_external_dataset",
        food_group_filter="Vegetables",
    )

    assert converted_count == 1

    with output_path.open("r", encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert rows[0]["name"] == "Broccoli"


def test_convert_normalised_foods_csv_skips_rows_without_food_name(tmp_path):
    input_path = tmp_path / "normalised_foods.csv"
    output_path = tmp_path / "riglog_foods.csv"

    input_path.write_text(
        """food_name,brand,serving_notes,food_group,calories_kcal_per_100g,carbs_g_per_100g,protein_g_per_100g,fat_g_per_100g,fibre_g_per_100g,salt_g_per_100g,notes
,,Missing name,Vegetables,34,7,2.8,0.4,2.6,0.08,Should skip
Carrot,,Raw vegetable,Vegetables,41,10,0.9,0.2,2.8,0.07,Starter value
""",
        encoding="utf-8",
    )

    converted_count = convert_normalised_foods_csv_to_riglog_csv(
        input_path=input_path,
        output_path=output_path,
        source_name="test_external_dataset",
    )

    assert converted_count == 1

    with output_path.open("r", encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert rows[0]["name"] == "Carrot"


def test_convert_normalised_foods_csv_uses_default_serving_notes(tmp_path):
    input_path = tmp_path / "normalised_foods.csv"
    output_path = tmp_path / "riglog_foods.csv"

    input_path.write_text(
        """food_name,brand,serving_notes,food_group,calories_kcal_per_100g,carbs_g_per_100g,protein_g_per_100g,fat_g_per_100g,fibre_g_per_100g,salt_g_per_100g,notes
Broccoli,,,Vegetables,34,7,2.8,0.4,2.6,0.08,
""",
        encoding="utf-8",
    )

    convert_normalised_foods_csv_to_riglog_csv(
        input_path=input_path,
        output_path=output_path,
        source_name="test_external_dataset",
    )

    with output_path.open("r", encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert rows[0]["serving_notes"] == "External dataset values per 100g"


def test_convert_normalised_foods_csv_rejects_missing_columns(tmp_path):
    input_path = tmp_path / "normalised_foods.csv"
    output_path = tmp_path / "riglog_foods.csv"

    input_path.write_text(
        """food_name,calories_kcal_per_100g
Broccoli,34
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc:
        convert_normalised_foods_csv_to_riglog_csv(
            input_path=input_path,
            output_path=output_path,
            source_name="test_external_dataset",
        )

    assert "Missing required source columns:" in str(exc.value)
    assert "carbs_g_per_100g" in str(exc.value)


def test_convert_normalised_foods_csv_rejects_invalid_numeric_value(tmp_path):
    input_path = tmp_path / "normalised_foods.csv"
    output_path = tmp_path / "riglog_foods.csv"

    input_path.write_text(
        """food_name,brand,serving_notes,food_group,calories_kcal_per_100g,carbs_g_per_100g,protein_g_per_100g,fat_g_per_100g,fibre_g_per_100g,salt_g_per_100g,notes
Broccoli,,Raw vegetable,Vegetables,not-a-number,7,2.8,0.4,2.6,0.08,Starter value
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc:
        convert_normalised_foods_csv_to_riglog_csv(
            input_path=input_path,
            output_path=output_path,
            source_name="test_external_dataset",
        )

    assert str(exc.value) == (
        "Invalid numeric value for calories_kcal_per_100g: not-a-number"
    )


def test_convert_normalised_foods_csv_rejects_negative_numeric_value(tmp_path):
    input_path = tmp_path / "normalised_foods.csv"
    output_path = tmp_path / "riglog_foods.csv"

    input_path.write_text(
        """food_name,brand,serving_notes,food_group,calories_kcal_per_100g,carbs_g_per_100g,protein_g_per_100g,fat_g_per_100g,fibre_g_per_100g,salt_g_per_100g,notes
Broccoli,,Raw vegetable,Vegetables,34,-7,2.8,0.4,2.6,0.08,Starter value
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc:
        convert_normalised_foods_csv_to_riglog_csv(
            input_path=input_path,
            output_path=output_path,
            source_name="test_external_dataset",
        )

    assert str(exc.value) == "carbs_g_per_100g cannot be negative."
