from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMessageBox

from app.ui.tabs.nutrition_tab import NutritionTab


def _card_texts(card) -> set[str]:
    """Return all non-empty label text contained in a SummaryCard."""
    return {
        label.text()
        for label in card.findChildren(QLabel)
        if label.text()
    }


def _mock_nutrition_services(mocker):
    """Mock NutritionTab service dependencies with deterministic data."""
    metrics = mocker.patch(
        "app.ui.tabs.nutrition_tab.get_nutrition_summary_metrics",
        return_value={
            "total_meals": 3,
            "total_calories": 1850.0,
            "total_carbs_g": 210.5,
            "total_protein_g": 125.0,
            "total_fat_g": 62.5,
            "average_daily_carbs_g": 105.25,
        },
    )

    food_options = mocker.patch(
        "app.ui.tabs.nutrition_tab.get_food_options",
        return_value=[
            {
                "id": 1,
                "display_name": "Porridge oats",
            }
        ],
    )

    meal_template_options = mocker.patch(
        "app.ui.tabs.nutrition_tab.get_meal_template_options",
        return_value=[
            {
                "id": 10,
                "display_name": "Porridge breakfast",
                "default_meal_event": "Pre-Breakfast",
            }
        ],
    )

    recent_meals = mocker.patch(
        "app.ui.tabs.nutrition_tab.get_recent_meal_logs",
        return_value=[
            {
                "logged_at": datetime(2026, 7, 17, 8, 0),
                "meal_name": "Porridge breakfast",
                "meal_event": "Pre-Breakfast",
                "portion_multiplier": 1.0,
                "calories": 420.0,
                "carbs_g": 62.0,
                "protein_g": 18.0,
                "fat_g": 10.0,
                "notes": "Before gym",
            }
        ],
    )

    template_totals = mocker.patch(
        "app.ui.tabs.nutrition_tab.get_meal_template_totals_rows",
        return_value=[
            {
                "name": "Porridge breakfast",
                "default_meal_event": "Pre-Breakfast",
                "calories": 420.0,
                "carbs_g": 62.0,
                "protein_g": 18.0,
                "fat_g": 10.0,
                "fibre_g": 8.0,
                "salt_g": 0.4,
            }
        ],
    )

    post_meal_response = mocker.patch(
        "app.ui.tabs.nutrition_tab.get_post_meal_glucose_response_rows",
        return_value=[],
    )

    macro_response = mocker.patch(
        "app.ui.tabs.nutrition_tab."
        "get_macro_glucose_response_by_meal_event",
        return_value=[],
    )

    template_response = mocker.patch(
        "app.ui.tabs.nutrition_tab."
        "get_meal_template_glucose_response_summary",
        return_value=[],
    )

    add_food = mocker.patch(
        "app.ui.tabs.nutrition_tab.add_food",
    )

    create_meal_template = mocker.patch(
        "app.ui.tabs.nutrition_tab.create_meal_template",
    )

    create_meal_log = mocker.patch(
        "app.ui.tabs.nutrition_tab.create_meal_log",
    )

    return {
        "metrics": metrics,
        "food_options": food_options,
        "meal_template_options": meal_template_options,
        "recent_meals": recent_meals,
        "template_totals": template_totals,
        "post_meal_response": post_meal_response,
        "macro_response": macro_response,
        "template_response": template_response,
        "add_food": add_food,
        "create_meal_template": create_meal_template,
        "create_meal_log": create_meal_log,
    }


def _build_nutrition_tab(qtbot, mocker):
    services = _mock_nutrition_services(mocker)

    tab = NutritionTab()
    qtbot.addWidget(tab)

    return tab, services


def test_nutrition_tab_renders_without_crashing(qtbot, mocker):
    tab, _ = _build_nutrition_tab(qtbot, mocker)

    assert tab.refresh_button.text() == "Refresh"
    assert tab.import_foods_button.text() == "Import Foods CSV"
    assert tab.save_food_button.text() == "Save Food"
    assert tab.save_meal_template_button.text() == "Save Meal Template"
    assert tab.save_meal_log_button.text() == "Save Meal Log"

    assert tab.recent_meals_table is not None
    assert tab.template_totals_table is not None
    assert tab.post_meal_response_table is not None


def test_nutrition_tab_populates_summary_cards_and_tables(qtbot, mocker):
    tab, _ = _build_nutrition_tab(qtbot, mocker)

    assert "3" in _card_texts(tab.total_meals_card)
    assert "1850" in _card_texts(tab.calories_card)
    assert "210.5" in _card_texts(tab.carbs_card)
    assert "125.0" in _card_texts(tab.protein_card)
    assert "62.5" in _card_texts(tab.fat_card)
    assert "105.2" in _card_texts(tab.avg_daily_carbs_card)

    assert tab.recent_meals_table.rowCount() == 1
    assert tab.recent_meals_table.item(0, 1).text() == "Porridge breakfast"
    assert tab.recent_meals_table.item(0, 2).text() == "Pre-Breakfast"
    assert tab.recent_meals_table.item(0, 5).text() == "62.0"
    assert tab.recent_meals_table.item(0, 8).text() == "Before gym"

    assert tab.template_totals_table.rowCount() == 1
    assert tab.template_totals_table.item(0, 0).text() == "Porridge breakfast"
    assert tab.template_totals_table.item(0, 1).text() == "Pre-Breakfast"
    assert tab.template_totals_table.item(0, 2).text() == "420.0"
    assert tab.template_totals_table.item(0, 6).text() == "8.0"


def test_add_food_form_displays_validation_error(qtbot, mocker):
    tab, services = _build_nutrition_tab(qtbot, mocker)

    services["add_food"].side_effect = ValueError("Food name is required.")

    warning = mocker.patch.object(
        QMessageBox,
        "warning",
        return_value=QMessageBox.StandardButton.Ok,
    )

    qtbot.mouseClick(
        tab.save_food_button,
        Qt.MouseButton.LeftButton,
    )

    services["add_food"].assert_called_once()
    warning.assert_called_once()

    assert warning.call_args.args[1] == "Invalid food"
    assert warning.call_args.args[2] == "Food name is required."


def test_save_food_refreshes_once_and_emits_update(qtbot, mocker):
    tab, services = _build_nutrition_tab(qtbot, mocker)

    tab.food_name_input.setText("Greek yoghurt")
    tab.food_calories_input.setValue(120.0)
    tab.food_protein_input.setValue(10.0)

    information = mocker.patch.object(
        QMessageBox,
        "information",
        return_value=QMessageBox.StandardButton.Ok,
    )

    with qtbot.waitSignal(tab.data_updated, timeout=1000):
        qtbot.mouseClick(
            tab.save_food_button,
            Qt.MouseButton.LeftButton,
        )

    services["add_food"].assert_called_once()

    assert information.call_count == 1
    assert information.call_args.args[1] == "Food saved"
    assert tab.food_name_input.text() == ""


def test_build_meal_form_adds_food_to_pending_items(qtbot, mocker):
    tab, _ = _build_nutrition_tab(qtbot, mocker)

    assert tab.meal_food_selector.currentData() == 1

    tab.meal_quantity_input.setValue(80.0)

    qtbot.mouseClick(
        tab.add_meal_item_button,
        Qt.MouseButton.LeftButton,
    )

    assert len(tab.pending_meal_items) == 1
    assert tab.pending_meal_items[0] == {
        "food_id": 1,
        "food_name": "Porridge oats",
        "quantity_g": 80.0,
        "display_order": 1,
    }

    assert tab.pending_items_table.rowCount() == 1
    assert tab.pending_items_table.item(0, 0).text() == "Porridge oats"
    assert tab.pending_items_table.item(0, 1).text() == "80.0"


def test_log_meal_saves_selected_template_and_emits_update(qtbot, mocker):
    tab, services = _build_nutrition_tab(qtbot, mocker)

    information = mocker.patch.object(
        QMessageBox,
        "information",
        return_value=QMessageBox.StandardButton.Ok,
    )

    tab.log_portion_multiplier_input.setValue(1.25)
    tab.log_meal_notes_input.setPlainText("Post-workout meal")

    with qtbot.waitSignal(tab.data_updated, timeout=1000):
        qtbot.mouseClick(
            tab.save_meal_log_button,
            Qt.MouseButton.LeftButton,
        )

    services["create_meal_log"].assert_called_once()

    call_kwargs = services["create_meal_log"].call_args.kwargs

    assert call_kwargs["meal_template_id"] == 10
    assert call_kwargs["meal_event"] == "Pre-Breakfast"
    assert call_kwargs["portion_multiplier"] == 1.25
    assert call_kwargs["notes"] == "Post-workout meal"
    assert isinstance(call_kwargs["logged_at"], datetime)

    information.assert_called_once()
    assert information.call_args.args[1] == "Meal logged"


def test_refresh_button_updates_summary_cards_and_tables(qtbot, mocker):
    tab, services = _build_nutrition_tab(qtbot, mocker)

    services["metrics"].return_value = {
        "total_meals": 4,
        "total_calories": 2200.0,
        "total_carbs_g": 250.0,
        "total_protein_g": 140.0,
        "total_fat_g": 70.0,
        "average_daily_carbs_g": 125.0,
    }

    services["recent_meals"].return_value = [
        {
            "logged_at": datetime(2026, 7, 17, 19, 0),
            "meal_name": "Chicken rice bowl",
            "meal_event": "Post-Dinner",
            "portion_multiplier": 1.0,
            "calories": 650.0,
            "carbs_g": 75.0,
            "protein_g": 45.0,
            "fat_g": 18.0,
            "notes": "",
        }
    ]

    qtbot.mouseClick(
        tab.refresh_button,
        Qt.MouseButton.LeftButton,
    )

    assert "4" in _card_texts(tab.total_meals_card)
    assert "2200" in _card_texts(tab.calories_card)
    assert "250.0" in _card_texts(tab.carbs_card)

    assert tab.recent_meals_table.rowCount() == 1
    assert tab.recent_meals_table.item(0, 1).text() == "Chicken rice bowl"
    assert tab.recent_meals_table.item(0, 2).text() == "Post-Dinner"

    assert services["metrics"].call_count == 2
    assert services["recent_meals"].call_count == 2
    assert services["template_totals"].call_count == 2
