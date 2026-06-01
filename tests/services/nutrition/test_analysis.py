from types import SimpleNamespace

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Food, MealLog, MealTemplate, MealTemplateItem
import app.services.nutrition.analysis as nutrition_analysis

from app.services.nutrition.analysis import (
    add_food,
    calculate_food_totals,
    calculate_logged_meal_totals,
    calculate_meal_template_totals,
    get_logged_meal_totals,
    get_meal_template_totals,
    get_meal_template_totals_rows,
    get_nutrition_summary_metrics,
    get_recent_meal_logs,
    create_meal_template,
    get_food_options,
)


@pytest.fixture
def test_session(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(
        nutrition_analysis,
        "SessionLocal",
        TestingSessionLocal,
    )

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


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


def test_get_meal_template_totals_returns_totals_from_database(test_session):
    oats = Food(
        name="Porridge oats",
        calories_per_100g=370,
        carbs_per_100g=60,
        protein_per_100g=12,
        fat_per_100g=8,
        fibre_per_100g=6,
        salt_per_100g=0.1,
        source="test",
    )

    milk = Food(
        name="Semi-skimmed milk",
        calories_per_100g=50,
        carbs_per_100g=5,
        protein_per_100g=3.5,
        fat_per_100g=1.8,
        fibre_per_100g=0,
        salt_per_100g=0.1,
        source="test",
    )

    meal_template = MealTemplate(
        name="Porridge breakfast",
        default_meal_event="Pre-Breakfast",
    )

    meal_template.items = [
        MealTemplateItem(
            food=oats,
            quantity_g=50,
            display_order=1,
        ),
        MealTemplateItem(
            food=milk,
            quantity_g=200,
            display_order=2,
        ),
    ]

    test_session.add(meal_template)
    test_session.commit()

    result = get_meal_template_totals(meal_template.id)

    assert result == {
        "calories": 285.0,
        "carbs_g": 40.0,
        "protein_g": 13.0,
        "fat_g": 7.6,
        "fibre_g": 3.0,
        "salt_g": 0.3,
    }


def test_get_meal_template_totals_returns_none_for_missing_template(test_session):
    result = get_meal_template_totals(999)

    assert result is None


def test_get_logged_meal_totals_applies_portion_multiplier_from_database(test_session):
    rice = Food(
        name="Cooked rice",
        calories_per_100g=130,
        carbs_per_100g=28,
        protein_per_100g=2.7,
        fat_per_100g=0.3,
        fibre_per_100g=0.4,
        salt_per_100g=0.0,
        source="test",
    )

    meal_template = MealTemplate(
        name="Rice bowl",
        default_meal_event="Pre-Dinner",
    )

    meal_template.items = [
        MealTemplateItem(
            food=rice,
            quantity_g=250,
            display_order=1,
        ),
    ]

    meal_log = MealLog(
        logged_at=datetime(2026, 5, 26, 18, 30),
        meal_template=meal_template,
        meal_event="Pre-Dinner",
        portion_multiplier=0.5,
        source="test",
    )

    test_session.add(meal_log)
    test_session.commit()

    result = get_logged_meal_totals(meal_log.id)

    assert result == {
        "calories": 162.5,
        "carbs_g": 35.0,
        "protein_g": 3.4,
        "fat_g": 0.4,
        "fibre_g": 0.5,
        "salt_g": 0.0,
    }


def test_get_logged_meal_totals_returns_none_for_missing_log(test_session):
    result = get_logged_meal_totals(999)

    assert result is None


def test_get_nutrition_summary_metrics_returns_empty_summary(test_session):
    result = get_nutrition_summary_metrics()

    assert result == {
        "total_meals": 0,
        "total_calories": 0.0,
        "total_carbs_g": 0.0,
        "total_protein_g": 0.0,
        "total_fat_g": 0.0,
        "average_daily_carbs_g": 0.0,
        "carbs_by_meal_event": {},
    }


def test_get_nutrition_summary_metrics_summarises_logged_meals(test_session):
    oats = Food(
        name="Porridge oats",
        calories_per_100g=370,
        carbs_per_100g=60,
        protein_per_100g=12,
        fat_per_100g=8,
        fibre_per_100g=6,
        salt_per_100g=0.1,
        source="test",
    )

    rice = Food(
        name="Cooked rice",
        calories_per_100g=130,
        carbs_per_100g=28,
        protein_per_100g=2.7,
        fat_per_100g=0.3,
        fibre_per_100g=0.4,
        salt_per_100g=0.0,
        source="test",
    )

    breakfast = MealTemplate(
        name="Porridge breakfast",
        default_meal_event="Pre-Breakfast",
    )
    breakfast.items = [
        MealTemplateItem(
            food=oats,
            quantity_g=50,
            display_order=1,
        )
    ]

    dinner = MealTemplate(
        name="Rice bowl",
        default_meal_event="Pre-Dinner",
    )
    dinner.items = [
        MealTemplateItem(
            food=rice,
            quantity_g=250,
            display_order=1,
        )
    ]

    test_session.add_all(
        [
            MealLog(
                logged_at=datetime(2026, 5, 25, 8, 0),
                meal_template=breakfast,
                meal_event="Pre-Breakfast",
                portion_multiplier=1.0,
                source="test",
            ),
            MealLog(
                logged_at=datetime(2026, 5, 25, 18, 30),
                meal_template=dinner,
                meal_event="Pre-Dinner",
                portion_multiplier=1.0,
                source="test",
            ),
            MealLog(
                logged_at=datetime(2026, 5, 26, 8, 0),
                meal_template=breakfast,
                meal_event="Pre-Breakfast",
                portion_multiplier=0.5,
                source="test",
            ),
        ]
    )
    test_session.commit()

    result = get_nutrition_summary_metrics()

    assert result == {
        "total_meals": 3,
        "total_calories": 602.5,
        "total_carbs_g": 115.0,
        "total_protein_g": 15.8,
        "total_fat_g": 6.8,
        "average_daily_carbs_g": 57.5,
        "carbs_by_meal_event": {
            "Pre-Breakfast": 45.0,
            "Pre-Dinner": 70.0,
        },
    }


def test_get_nutrition_summary_metrics_filters_by_days(test_session):
    food = Food(
        name="Test food",
        calories_per_100g=100,
        carbs_per_100g=20,
        protein_per_100g=5,
        fat_per_100g=2,
        fibre_per_100g=1,
        salt_per_100g=0.1,
        source="test",
    )

    meal_template = MealTemplate(
        name="Test meal",
        default_meal_event="Pre-Lunch",
    )
    meal_template.items = [
        MealTemplateItem(
            food=food,
            quantity_g=100,
            display_order=1,
        )
    ]

    recent_log = MealLog(
        logged_at=datetime.now() - timedelta(days=1),
        meal_template=meal_template,
        meal_event="Pre-Lunch",
        portion_multiplier=1.0,
        source="test",
    )

    old_log = MealLog(
        logged_at=datetime.now() - timedelta(days=30),
        meal_template=meal_template,
        meal_event="Pre-Lunch",
        portion_multiplier=1.0,
        source="test",
    )

    test_session.add_all([recent_log, old_log])
    test_session.commit()

    result = get_nutrition_summary_metrics(days=7)

    assert result == {
        "total_meals": 1,
        "total_calories": 100.0,
        "total_carbs_g": 20.0,
        "total_protein_g": 5.0,
        "total_fat_g": 2.0,
        "average_daily_carbs_g": 20.0,
        "carbs_by_meal_event": {
            "Pre-Lunch": 20.0,
        },
    }


def test_get_nutrition_summary_metrics_groups_missing_meal_event_as_uncategorised(
    test_session,
):
    food = Food(
        name="Test food",
        calories_per_100g=100,
        carbs_per_100g=20,
        protein_per_100g=5,
        fat_per_100g=2,
        fibre_per_100g=1,
        salt_per_100g=0.1,
        source="test",
    )

    meal_template = MealTemplate(
        name="Test meal",
        default_meal_event=None,
    )
    meal_template.items = [
        MealTemplateItem(
            food=food,
            quantity_g=100,
            display_order=1,
        )
    ]

    meal_log = MealLog(
        logged_at=datetime(2026, 5, 26, 12, 30),
        meal_template=meal_template,
        meal_event=None,
        portion_multiplier=1.0,
        source="test",
    )

    test_session.add(meal_log)
    test_session.commit()

    result = get_nutrition_summary_metrics()

    assert result["carbs_by_meal_event"] == {
        "Uncategorised": 20.0,
    }


def test_get_recent_meal_logs_returns_display_rows(test_session):
    food = Food(
        name="Test food",
        calories_per_100g=200,
        carbs_per_100g=30,
        protein_per_100g=10,
        fat_per_100g=5,
        fibre_per_100g=4,
        salt_per_100g=0.2,
        source="test",
    )

    meal_template = MealTemplate(
        name="Test meal",
        default_meal_event="Pre-Lunch",
    )
    meal_template.items = [
        MealTemplateItem(
            food=food,
            quantity_g=100,
            display_order=1,
        )
    ]

    meal_log = MealLog(
        logged_at=datetime(2026, 5, 26, 12, 30),
        meal_template=meal_template,
        meal_event="Pre-Lunch",
        portion_multiplier=1.5,
        notes="Test meal log",
        source="test",
    )

    test_session.add(meal_log)
    test_session.commit()

    result = get_recent_meal_logs()

    assert result == [
        {
            "id": meal_log.id,
            "logged_at": datetime(2026, 5, 26, 12, 30),
            "meal_name": "Test meal",
            "meal_event": "Pre-Lunch",
            "portion_multiplier": 1.5,
            "calories": 300.0,
            "carbs_g": 45.0,
            "protein_g": 15.0,
            "fat_g": 7.5,
            "notes": "Test meal log",
        }
    ]


def test_get_recent_meal_logs_respects_limit(test_session):
    food = Food(
        name="Test food",
        calories_per_100g=100,
        carbs_per_100g=10,
        protein_per_100g=5,
        fat_per_100g=2,
        fibre_per_100g=1,
        salt_per_100g=0.1,
        source="test",
    )

    meal_template = MealTemplate(
        name="Test meal",
        default_meal_event="Pre-Lunch",
    )
    meal_template.items = [
        MealTemplateItem(
            food=food,
            quantity_g=100,
            display_order=1,
        )
    ]

    test_session.add_all(
        [
            MealLog(
                logged_at=datetime(2026, 5, 24, 12, 0),
                meal_template=meal_template,
                meal_event="Pre-Lunch",
                portion_multiplier=1.0,
                source="test",
            ),
            MealLog(
                logged_at=datetime(2026, 5, 25, 12, 0),
                meal_template=meal_template,
                meal_event="Pre-Lunch",
                portion_multiplier=1.0,
                source="test",
            ),
            MealLog(
                logged_at=datetime(2026, 5, 26, 12, 0),
                meal_template=meal_template,
                meal_event="Pre-Lunch",
                portion_multiplier=1.0,
                source="test",
            ),
        ]
    )
    test_session.commit()

    result = get_recent_meal_logs(limit=2)

    assert len(result) == 2
    assert [row["logged_at"] for row in result] == [
        datetime(2026, 5, 26, 12, 0),
        datetime(2026, 5, 25, 12, 0),
    ]


def test_get_meal_template_totals_rows_returns_display_rows(test_session):
    food = Food(
        name="Test food",
        calories_per_100g=150,
        carbs_per_100g=20,
        protein_per_100g=8,
        fat_per_100g=4,
        fibre_per_100g=3,
        salt_per_100g=0.2,
        source="test",
    )

    meal_template = MealTemplate(
        name="Template meal",
        default_meal_event="Pre-Dinner",
    )
    meal_template.items = [
        MealTemplateItem(
            food=food,
            quantity_g=200,
            display_order=1,
        )
    ]

    test_session.add(meal_template)
    test_session.commit()

    result = get_meal_template_totals_rows()

    assert result == [
        {
            "id": meal_template.id,
            "name": "Template meal",
            "default_meal_event": "Pre-Dinner",
            "calories": 300.0,
            "carbs_g": 40.0,
            "protein_g": 16.0,
            "fat_g": 8.0,
            "fibre_g": 6.0,
            "salt_g": 0.4,
        }
    ]


def test_add_food_creates_manual_food(test_session):
    food = add_food(
        name="Test cereal",
        brand="Test Brand",
        serving_notes="Nutrition values from packet label",
        calories_per_100g=380,
        carbs_per_100g=70,
        protein_per_100g=8,
        fat_per_100g=4,
        fibre_per_100g=5,
        salt_per_100g=0.3,
        notes="Manual test food",
    )

    stored_food = test_session.query(Food).filter(Food.id == food.id).first()

    assert stored_food is not None
    assert stored_food.name == "Test cereal"
    assert stored_food.brand == "Test Brand"
    assert stored_food.serving_notes == "Nutrition values from packet label"
    assert stored_food.calories_per_100g == 380
    assert stored_food.carbs_per_100g == 70
    assert stored_food.protein_per_100g == 8
    assert stored_food.fat_per_100g == 4
    assert stored_food.fibre_per_100g == 5
    assert stored_food.salt_per_100g == 0.3
    assert stored_food.source == "manual"
    assert stored_food.notes == "Manual test food"


def test_add_food_strips_text_fields(test_session):
    food = add_food(
        name="  Greek yoghurt  ",
        brand="  Test Brand  ",
        serving_notes="  Per label  ",
        notes="  Useful staple  ",
    )

    stored_food = test_session.query(Food).filter(Food.id == food.id).first()

    assert stored_food.name == "Greek yoghurt"
    assert stored_food.brand == "Test Brand"
    assert stored_food.serving_notes == "Per label"
    assert stored_food.notes == "Useful staple"


def test_add_food_requires_name(test_session):
    try:
        add_food(name="   ")
    except ValueError as exc:
        assert str(exc) == "Food name is required."
    else:
        raise AssertionError("Expected ValueError")


def test_add_food_rejects_negative_nutrition_values(test_session):
    try:
        add_food(
            name="Invalid food",
            carbs_per_100g=-1,
        )
    except ValueError as exc:
        assert str(exc) == "carbs_per_100g cannot be negative."
    else:
        raise AssertionError("Expected ValueError")


def test_get_food_options_returns_foods_for_selection(test_session):
    food_a = Food(
        name="Banana",
        brand=None,
        calories_per_100g=89,
        carbs_per_100g=23,
        protein_per_100g=1.1,
        fat_per_100g=0.3,
        fibre_per_100g=2.6,
        salt_per_100g=0,
        source="test",
    )

    food_b = Food(
        name="Greek yoghurt",
        brand="Demo",
        calories_per_100g=95,
        carbs_per_100g=3.8,
        protein_per_100g=9,
        fat_per_100g=5,
        fibre_per_100g=0,
        salt_per_100g=0.1,
        source="test",
    )

    test_session.add_all([food_b, food_a])
    test_session.commit()

    result = get_food_options()

    assert result == [
        {
            "id": food_a.id,
            "name": "Banana",
            "brand": None,
            "display_name": "Banana",
        },
        {
            "id": food_b.id,
            "name": "Greek yoghurt",
            "brand": "Demo",
            "display_name": "Greek yoghurt (Demo)",
        },
    ]


def test_create_meal_template_creates_template_with_items(test_session):
    oats = Food(
        name="Porridge oats",
        calories_per_100g=370,
        carbs_per_100g=60,
        protein_per_100g=12,
        fat_per_100g=8,
        fibre_per_100g=6,
        salt_per_100g=0.1,
        source="test",
    )

    milk = Food(
        name="Semi-skimmed milk",
        calories_per_100g=50,
        carbs_per_100g=5,
        protein_per_100g=3.5,
        fat_per_100g=1.8,
        fibre_per_100g=0,
        salt_per_100g=0.1,
        source="test",
    )

    test_session.add_all([oats, milk])
    test_session.commit()

    meal_template = create_meal_template(
        name="Porridge breakfast",
        default_meal_event="Pre-Breakfast",
        description="Oats and milk",
        notes="Manual meal template",
        items=[
            {
                "food_id": oats.id,
                "quantity_g": 50,
                "display_order": 1,
            },
            {
                "food_id": milk.id,
                "quantity_g": 200,
                "display_order": 2,
            },
        ],
    )

    stored_template = (
        test_session.query(MealTemplate)
        .filter(MealTemplate.id == meal_template.id)
        .first()
    )

    assert stored_template is not None
    assert stored_template.name == "Porridge breakfast"
    assert stored_template.default_meal_event == "Pre-Breakfast"
    assert stored_template.description == "Oats and milk"
    assert stored_template.notes == "Manual meal template"
    assert len(stored_template.items) == 2

    assert [
        (item.food.name, item.quantity_g, item.display_order)
        for item in stored_template.items
    ] == [
        ("Porridge oats", 50, 1),
        ("Semi-skimmed milk", 200, 2),
    ]


def test_create_meal_template_requires_name(test_session):
    food = Food(
        name="Banana",
        calories_per_100g=89,
        carbs_per_100g=23,
        protein_per_100g=1.1,
        fat_per_100g=0.3,
        fibre_per_100g=2.6,
        salt_per_100g=0,
        source="test",
    )
    test_session.add(food)
    test_session.commit()

    try:
        create_meal_template(
            name="   ",
            items=[
                {
                    "food_id": food.id,
                    "quantity_g": 100,
                }
            ],
        )
    except ValueError as exc:
        assert str(exc) == "Meal name is required."
    else:
        raise AssertionError("Expected ValueError")


def test_create_meal_template_requires_at_least_one_food_item(test_session):
    try:
        create_meal_template(
            name="Empty meal",
            items=[],
        )
    except ValueError as exc:
        assert str(exc) == "At least one food item is required."
    else:
        raise AssertionError("Expected ValueError")


def test_create_meal_template_rejects_zero_or_negative_quantity(test_session):
    food = Food(
        name="Banana",
        calories_per_100g=89,
        carbs_per_100g=23,
        protein_per_100g=1.1,
        fat_per_100g=0.3,
        fibre_per_100g=2.6,
        salt_per_100g=0,
        source="test",
    )
    test_session.add(food)
    test_session.commit()

    try:
        create_meal_template(
            name="Invalid meal",
            items=[
                {
                    "food_id": food.id,
                    "quantity_g": 0,
                }
            ],
        )
    except ValueError as exc:
        assert str(exc) == "Food quantity must be greater than zero."
    else:
        raise AssertionError("Expected ValueError")


def test_create_meal_template_rejects_missing_food(test_session):
    try:
        create_meal_template(
            name="Invalid meal",
            items=[
                {
                    "food_id": 999,
                    "quantity_g": 100,
                }
            ],
        )
    except ValueError as exc:
        assert str(exc) == "Food ID 999 was not found."
    else:
        raise AssertionError("Expected ValueError")
