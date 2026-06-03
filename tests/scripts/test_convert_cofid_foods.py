import csv

from scripts.convert_cofid_foods import convert_cofid_foods


def test_convert_cofid_foods_writes_normalised_and_riglog_outputs(tmp_path):
    input_path = tmp_path / "cofid.csv"
    normalised_output_path = tmp_path / "normalised_foods.csv"
    riglog_output_path = tmp_path / "riglog_foods.csv"

    input_path.write_text(
        """Food Code,Food Name,Description,Group,Energy (kcal) (kcal),Carbohydrate (g),Protein (g),Fat (g),AOAC fibre (g),Salt (g)
13-001,Broccoli,raw,Vegetables,34,7,2.8,0.4,2.6,0.08
14-001,Apple,raw,Fruit,52,14,0.3,0.2,2.4,0.0
""",
        encoding="utf-8",
    )

    result = convert_cofid_foods(
        input_path=input_path,
        normalised_output_path=normalised_output_path,
        riglog_output_path=riglog_output_path,
        source_name="cofid_test",
        food_group="Vegetables",
    )

    assert result == {
        "normalised_rows": 1,
        "riglog_rows": 1,
    }

    with normalised_output_path.open("r", encoding="utf-8", newline="") as csv_file:
        normalised_rows = list(csv.DictReader(csv_file))

    assert normalised_rows[0]["food_name"] == "Broccoli"
    assert normalised_rows[0]["food_group"] == "Vegetables"

    with riglog_output_path.open("r", encoding="utf-8", newline="") as csv_file:
        riglog_rows = list(csv.DictReader(csv_file))

    assert riglog_rows[0]["food_key"] == "broccoli"
    assert riglog_rows[0]["name"] == "Broccoli"
    assert riglog_rows[0]["source"] == "cofid_test"
    assert riglog_rows[0]["calories_per_100g"] == "34"
    assert riglog_rows[0]["carbs_per_100g"] == "7"
