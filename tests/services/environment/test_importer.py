from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import DailyEnvironment
from app.services.environment import importer
from app.services.environment.importer import import_daily_environment_csv


def _build_test_session_factory(tmp_path):
    """Create an isolated SQLite database for importer tests."""
    db_path = tmp_path / "test_environment.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=engine)

    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )


def test_import_daily_environment_csv_imports_valid_rows(tmp_path, monkeypatch):
    """Import valid daily environment rows from CSV."""
    TestSessionLocal = _build_test_session_factory(tmp_path)
    monkeypatch.setattr(importer, "SessionLocal", TestSessionLocal)

    csv_path = tmp_path / "weather.csv"
    csv_path.write_text(
        "\n".join(
            [
                "date,avg_temperature_c,min_temperature_c,max_temperature_c,source,notes",
                "2026-05-01,12.4,8.2,16.1,manual,Clear spring day",
                "2026-05-02,18.5,13.1,22.4,manual,Warm afternoon",
            ]
        ),
        encoding="utf-8",
    )

    imported_count = import_daily_environment_csv(str(csv_path))

    assert imported_count == 2

    session = TestSessionLocal()

    try:
        rows = (
            session.query(DailyEnvironment)
            .order_by(DailyEnvironment.environment_date.asc())
            .all()
        )

        assert len(rows) == 2

        assert rows[0].environment_date.isoformat() == "2026-05-01"
        assert rows[0].avg_temperature_c == 12.4
        assert rows[0].min_temperature_c == 8.2
        assert rows[0].max_temperature_c == 16.1
        assert rows[0].source == "manual"
        assert rows[0].notes == "Clear spring day"

        assert rows[1].environment_date.isoformat() == "2026-05-02"
        assert rows[1].avg_temperature_c == 18.5
        assert rows[1].min_temperature_c == 13.1
        assert rows[1].max_temperature_c == 22.4
        assert rows[1].source == "manual"
        assert rows[1].notes == "Warm afternoon"

        assert rows[0].location_label == "default"
        assert rows[0].latitude is None
        assert rows[0].longitude is None

    finally:
        session.close()


def test_import_daily_environment_csv_skips_duplicates(tmp_path, monkeypatch):
    """Skip duplicate daily environment rows by date and source."""
    TestSessionLocal = _build_test_session_factory(tmp_path)
    monkeypatch.setattr(importer, "SessionLocal", TestSessionLocal)

    csv_path = tmp_path / "weather.csv"
    csv_path.write_text(
        "\n".join(
            [
                "date,avg_temperature_c,min_temperature_c,max_temperature_c,source,notes",
                "2026-05-01,12.4,8.2,16.1,manual,First import",
            ]
        ),
        encoding="utf-8",
    )

    first_import_count = import_daily_environment_csv(str(csv_path))
    second_import_count = import_daily_environment_csv(str(csv_path))

    assert first_import_count == 1
    assert second_import_count == 0

    session = TestSessionLocal()

    try:
        rows = session.query(DailyEnvironment).all()

        assert len(rows) == 1
        assert rows[0].environment_date.isoformat() == "2026-05-01"
        assert rows[0].avg_temperature_c == 12.4
        assert rows[0].source == "manual"

    finally:
        session.close()


def test_import_daily_environment_csv_defaults_optional_fields(tmp_path, monkeypatch):
    """Default source to manual and optional numeric/text fields to None."""
    TestSessionLocal = _build_test_session_factory(tmp_path)
    monkeypatch.setattr(importer, "SessionLocal", TestSessionLocal)

    csv_path = tmp_path / "weather.csv"
    csv_path.write_text(
        "\n".join(
            [
                "date,avg_temperature_c,min_temperature_c,max_temperature_c,source,notes",
                "2026-05-01,12.4,,,,",
            ]
        ),
        encoding="utf-8",
    )

    imported_count = import_daily_environment_csv(str(csv_path))

    assert imported_count == 1

    session = TestSessionLocal()

    try:
        row = session.query(DailyEnvironment).one()

        assert row.environment_date.isoformat() == "2026-05-01"
        assert row.avg_temperature_c == 12.4
        assert row.min_temperature_c is None
        assert row.max_temperature_c is None
        assert row.source == "manual"
        assert row.notes is None

    finally:
        session.close()


def test_import_daily_environment_csv_skips_rows_missing_required_values(
    tmp_path,
    monkeypatch,
):
    """Skip rows without date or average temperature."""
    TestSessionLocal = _build_test_session_factory(tmp_path)
    monkeypatch.setattr(importer, "SessionLocal", TestSessionLocal)

    csv_path = tmp_path / "weather.csv"
    csv_path.write_text(
        "\n".join(
            [
                "date,avg_temperature_c,min_temperature_c,max_temperature_c,source,notes",
                ",12.4,8.2,16.1,manual,Missing date",
                "2026-05-01,,8.2,16.1,manual,Missing average temperature",
                "2026-05-02,15.0,10.0,19.0,manual,Valid row",
            ]
        ),
        encoding="utf-8",
    )

    imported_count = import_daily_environment_csv(str(csv_path))

    assert imported_count == 1

    session = TestSessionLocal()

    try:
        row = session.query(DailyEnvironment).one()

        assert row.environment_date.isoformat() == "2026-05-02"
        assert row.avg_temperature_c == 15.0

    finally:
        session.close()


def test_import_daily_environment_csv_allows_same_date_for_different_locations(
    tmp_path,
    monkeypatch,
):
    """Allow same date/source rows when location labels differ."""
    TestSessionLocal = _build_test_session_factory(tmp_path)
    monkeypatch.setattr(importer, "SessionLocal", TestSessionLocal)

    csv_path = tmp_path / "weather.csv"
    csv_path.write_text(
        "\n".join(
            [
                "date,location_label,latitude,longitude,avg_temperature_c,min_temperature_c,max_temperature_c,source,notes",
                "2026-05-01,home,50.1,-0.1,12.4,8.2,16.1,manual,Home row",
                "2026-05-01,partner,51.2,-0.2,11.0,7.5,15.0,manual,Partner row",
            ]
        ),
        encoding="utf-8",
    )

    imported_count = import_daily_environment_csv(str(csv_path))

    assert imported_count == 2

    session = TestSessionLocal()

    try:
        rows = (
            session.query(DailyEnvironment)
            .order_by(DailyEnvironment.location_label.asc())
            .all()
        )

        assert len(rows) == 2
        assert [row.location_label for row in rows] == ["home", "partner"]
        assert rows[0].environment_date.isoformat() == "2026-05-01"
        assert rows[0].latitude == 50.1
        assert rows[0].longitude == -0.1
        assert rows[1].environment_date.isoformat() == "2026-05-01"
        assert rows[1].latitude == 51.2
        assert rows[1].longitude == -0.2

    finally:
        session.close()
