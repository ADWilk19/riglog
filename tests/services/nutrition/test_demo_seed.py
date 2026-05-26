from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Food, MealLog, MealTemplate, MealTemplateItem
import app.services.nutrition.demo_seed as demo_seed


def _build_test_session(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(
        demo_seed,
        "SessionLocal",
        testing_session_local,
    )

    return engine, testing_session_local


def test_seed_demo_nutrition_data_inserts_demo_rows(monkeypatch):
    engine, testing_session_local = _build_test_session(monkeypatch)

    result = demo_seed.seed_demo_nutrition_data(Path("data/demo"))

    session = testing_session_local()

    try:
        assert result == {
            "foods": 7,
            "meal_templates": 3,
            "meal_template_items": 8,
            "meal_logs": 3,
        }

        assert session.query(Food).count() == 7
        assert session.query(MealTemplate).count() == 3
        assert session.query(MealTemplateItem).count() == 8
        assert session.query(MealLog).count() == 3

    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_seed_demo_nutrition_data_is_idempotent(monkeypatch):
    engine, testing_session_local = _build_test_session(monkeypatch)

    first_result = demo_seed.seed_demo_nutrition_data(Path("data/demo"))
    second_result = demo_seed.seed_demo_nutrition_data(Path("data/demo"))

    session = testing_session_local()

    try:
        assert first_result == {
            "foods": 7,
            "meal_templates": 3,
            "meal_template_items": 8,
            "meal_logs": 3,
        }

        assert second_result == {
            "foods": 0,
            "meal_templates": 0,
            "meal_template_items": 0,
            "meal_logs": 0,
        }

        assert session.query(Food).count() == 7
        assert session.query(MealTemplate).count() == 3
        assert session.query(MealTemplateItem).count() == 8
        assert session.query(MealLog).count() == 3

    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_seed_demo_nutrition_data_creates_expected_relationships(monkeypatch):
    engine, testing_session_local = _build_test_session(monkeypatch)

    demo_seed.seed_demo_nutrition_data(Path("data/demo"))

    session = testing_session_local()

    try:
        porridge = (
            session.query(MealTemplate)
            .filter(MealTemplate.name == "Porridge breakfast")
            .first()
        )

        assert porridge is not None
        assert len(porridge.items) == 3
        assert [item.food.name for item in porridge.items] == [
            "Porridge oats",
            "Semi-skimmed milk",
            "Banana",
        ]

        meal_log = (
            session.query(MealLog)
            .filter(MealLog.meal_event == "Pre-Breakfast")
            .first()
        )

        assert meal_log is not None
        assert meal_log.meal_template.name == "Porridge breakfast"

    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
