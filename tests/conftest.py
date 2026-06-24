from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base


@pytest.fixture(scope="session")
def qapp():
    """Provide a QApplication instance for widget tests."""
    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


@pytest.fixture
def db_session(tmp_path: Path):
    db_path = tmp_path / "test_riglog.db"
    engine = create_engine(f"sqlite:///{db_path}")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
