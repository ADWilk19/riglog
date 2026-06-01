from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Food
import app.services.nutrition.importer as nutrition_importer
from app.services.nutrition.importer import import_foods_csv


@pytest.fixture
def test_session(monkeypatch):
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
        nutrition_importer,
        "SessionLocal",
        testing_session_local,
    )

    session = testing_session_local()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _write_csv(tmp_path: Path, content: str) -> Path:
    file_path = tmp_path / "foods.csv"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_import_foods_csv_imports_food_rows(test_session, tmp_path):
    file_path = _write_csv(
        tmp_path,
        """name,brand,serving_notes,calories_per_100g,carbs_per_100g,protein_per_100g,fat_per_100g,fibre_per_100g,salt_per_100g,source,notes
Broccoli,Generic,Raw broccoli,34,7,2.8,0.4,2.6,0.08,test_csv,Green vegetable
Carrot,Generic,Raw carrot,41,10,0.9,0.2,2.8,0.07,test_csv,Root vegetable
""",
    )

    imported_count = import_foods_csv(str(file_path))

    foods = test_session.query(Food).order_by(Food.name.asc()).all()

    assert imported_count == 2
    assert len(foods) == 2

    broccoli = foods[0]
    assert broccoli.name == "Broccoli"
    assert broccoli.brand == "Generic"
    assert broccoli.serving_notes == "Raw broccoli"
    assert broccoli.calories_per_100g == 34
    assert broccoli.carbs_per_100g == 7
    assert broccoli.protein_per_100g == 2.8
    assert broccoli.fat_per_100g == 0.4
    assert broccoli.fibre_per_100g == 2.6
    assert broccoli.salt_per_100g == 0.08
    assert broccoli.source == "test_csv"
    assert broccoli.notes == "Green vegetable"


def test_import_foods_csv_skips_duplicate_name_and_source(test_session, tmp_path):
    file_path = _write_csv(
        tmp_path,
        """name,brand,serving_notes,calories_per_100g,carbs_per_100g,protein_per_100g,fat_per_100g,fibre_per_100g,salt_per_100g,source,notes
Broccoli,Generic,Raw broccoli,34,7,2.8,0.4,2.6,0.08,test_csv,Green vegetable
Broccoli,Generic,Raw broccoli,34,7,2.8,0.4,2.6,0.08,test_csv,Duplicate row
""",
    )

    first_count = import_foods_csv(str(file_path))
    second_count = import_foods_csv(str(file_path))

    assert first_count == 1
    assert second_count == 0
    assert test_session.query(Food).count() == 1


def test_import_foods_csv_allows_same_name_from_different_source(test_session, tmp_path):
    file_path = _write_csv(
        tmp_path,
        """name,brand,serving_notes,calories_per_100g,carbs_per_100g,protein_per_100g,fat_per_100g,fibre_per_100g,salt_per_100g,source,notes
Broccoli,Generic,Raw broccoli,34,7,2.8,0.4,2.6,0.08,source_a,Green vegetable
Broccoli,Generic,Raw broccoli,35,7.2,2.9,0.4,2.7,0.08,source_b,Alternative source
""",
    )

    imported_count = import_foods_csv(str(file_path))

    assert imported_count == 2
    assert test_session.query(Food).count() == 2


def test_import_foods_csv_skips_rows_without_name(test_session, tmp_path):
    file_path = _write_csv(
        tmp_path,
        """name,brand,serving_notes,calories_per_100g,carbs_per_100g,protein_per_100g,fat_per_100g,fibre_per_100g,salt_per_100g,source,notes
,Generic,Missing name,34,7,2.8,0.4,2.6,0.08,test_csv,Should skip
Carrot,Generic,Raw carrot,41,10,0.9,0.2,2.8,0.07,test_csv,Root vegetable
""",
    )

    imported_count = import_foods_csv(str(file_path))

    assert imported_count == 1
    assert test_session.query(Food).count() == 1


def test_import_foods_csv_rejects_missing_required_columns(test_session, tmp_path):
    file_path = _write_csv(
        tmp_path,
        """name,brand,calories_per_100g
Broccoli,Generic,34
""",
    )

    with pytest.raises(ValueError) as exc:
        import_foods_csv(str(file_path))

    assert "Missing required columns:" in str(exc.value)
    assert "carbs_per_100g" in str(exc.value)


def test_import_foods_csv_rejects_invalid_numeric_value(test_session, tmp_path):
    file_path = _write_csv(
        tmp_path,
        """name,brand,serving_notes,calories_per_100g,carbs_per_100g,protein_per_100g,fat_per_100g,fibre_per_100g,salt_per_100g,source,notes
Broccoli,Generic,Raw broccoli,not-a-number,7,2.8,0.4,2.6,0.08,test_csv,Green vegetable
""",
    )

    with pytest.raises(ValueError) as exc:
        import_foods_csv(str(file_path))

    assert str(exc.value) == "Invalid numeric value for calories_per_100g: not-a-number"


def test_import_foods_csv_rejects_negative_numeric_value(test_session, tmp_path):
    file_path = _write_csv(
        tmp_path,
        """name,brand,serving_notes,calories_per_100g,carbs_per_100g,protein_per_100g,fat_per_100g,fibre_per_100g,salt_per_100g,source,notes
Broccoli,Generic,Raw broccoli,34,-7,2.8,0.4,2.6,0.08,test_csv,Green vegetable
""",
    )

    with pytest.raises(ValueError) as exc:
        import_foods_csv(str(file_path))

    assert str(exc.value) == "carbs_per_100g cannot be negative."
