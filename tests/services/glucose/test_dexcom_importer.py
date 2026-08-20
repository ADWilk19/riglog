from datetime import datetime

import pytest

from app.db.database import SessionLocal
from app.db.models import GlucoseReading
from app.services.glucose.dexcom_importer import (
    DEXCOM_SOURCE,
    import_dexcom_clarity_csv,
)


@pytest.fixture(autouse=True)
def clear_dexcom_readings():
    """Remove Dexcom readings before and after each test."""
    session = SessionLocal()

    try:
        (
            session.query(GlucoseReading)
            .filter(GlucoseReading.source == DEXCOM_SOURCE)
            .delete(synchronize_session=False)
        )
        session.commit()
    finally:
        session.close()

    yield

    session = SessionLocal()

    try:
        (
            session.query(GlucoseReading)
            .filter(GlucoseReading.source == DEXCOM_SOURCE)
            .delete(synchronize_session=False)
        )
        session.commit()
    finally:
        session.close()


def test_import_dexcom_clarity_csv_imports_glucose_reading(tmp_path):
    csv_path = tmp_path / "dexcom.csv"

    csv_path.write_text(
        "Timestamp (YYYY-MM-DDThh:mm:ss),Glucose Value (mg/dL),Event Type\n"
        "2026-08-12T10:15:00,108,EGV\n",
        encoding="utf-8",
    )

    imported_count = import_dexcom_clarity_csv(str(csv_path))

    assert imported_count == 1

    session = SessionLocal()

    try:
        reading = (
            session.query(GlucoseReading)
            .filter(GlucoseReading.source == DEXCOM_SOURCE)
            .one()
        )

        assert reading.recorded_at == datetime(2026, 8, 12, 10, 15)
        assert reading.glucose_value == pytest.approx(6.0)
        assert reading.source == DEXCOM_SOURCE
    finally:
        session.close()


def test_import_dexcom_clarity_csv_converts_mg_dl_to_mmol_l(tmp_path):
    csv_path = tmp_path / "dexcom.csv"

    csv_path.write_text(
        "Timestamp (YYYY-MM-DDThh:mm:ss),Glucose Value (mg/dL)\n"
        "2026-08-12T11:00:00,180\n",
        encoding="utf-8",
    )

    imported_count = import_dexcom_clarity_csv(str(csv_path))

    assert imported_count == 1

    session = SessionLocal()

    try:
        reading = (
            session.query(GlucoseReading)
            .filter(GlucoseReading.source == DEXCOM_SOURCE)
            .one()
        )

        assert reading.glucose_value == pytest.approx(10.0)
    finally:
        session.close()


def test_import_dexcom_clarity_csv_is_idempotent(tmp_path):
    csv_path = tmp_path / "dexcom.csv"

    csv_path.write_text(
        "Timestamp (YYYY-MM-DDThh:mm:ss),Glucose Value (mg/dL)\n"
        "2026-08-12T12:00:00,126\n",
        encoding="utf-8",
    )

    first_import = import_dexcom_clarity_csv(str(csv_path))
    second_import = import_dexcom_clarity_csv(str(csv_path))

    assert first_import == 1
    assert second_import == 0

    session = SessionLocal()

    try:
        count = (
            session.query(GlucoseReading)
            .filter(GlucoseReading.source == DEXCOM_SOURCE)
            .count()
        )

        assert count == 1
    finally:
        session.close()


def test_import_dexcom_clarity_csv_ignores_non_glucose_events(tmp_path):
    csv_path = tmp_path / "dexcom.csv"

    csv_path.write_text(
        "Timestamp (YYYY-MM-DDThh:mm:ss),Glucose Value (mg/dL),Event Type\n"
        "2026-08-12T13:00:00,108,Insulin\n"
        "2026-08-12T13:05:00,117,EGV\n",
        encoding="utf-8",
    )

    imported_count = import_dexcom_clarity_csv(str(csv_path))

    assert imported_count == 1

    session = SessionLocal()

    try:
        readings = (
            session.query(GlucoseReading)
            .filter(GlucoseReading.source == DEXCOM_SOURCE)
            .all()
        )

        assert len(readings) == 1
        assert readings[0].recorded_at == datetime(2026, 8, 12, 13, 5)
    finally:
        session.close()


def test_import_dexcom_clarity_csv_supports_display_time_column(tmp_path):
    csv_path = tmp_path / "dexcom.csv"

    csv_path.write_text(
        "Display Time,Glucose Value (mg/dL)\n"
        "2026-08-12 14:30:00,144\n",
        encoding="utf-8",
    )

    imported_count = import_dexcom_clarity_csv(str(csv_path))

    assert imported_count == 1

    session = SessionLocal()

    try:
        reading = (
            session.query(GlucoseReading)
            .filter(GlucoseReading.source == DEXCOM_SOURCE)
            .one()
        )

        assert reading.recorded_at == datetime(2026, 8, 12, 14, 30)
        assert reading.glucose_value == pytest.approx(8.0)
    finally:
        session.close()


def test_import_dexcom_clarity_csv_skips_invalid_glucose_values(tmp_path):
    csv_path = tmp_path / "dexcom.csv"

    csv_path.write_text(
        "Timestamp (YYYY-MM-DDThh:mm:ss),Glucose Value (mg/dL)\n"
        "2026-08-12T15:00:00,High\n"
        "2026-08-12T15:05:00,\n"
        "2026-08-12T15:10:00,90\n",
        encoding="utf-8",
    )

    imported_count = import_dexcom_clarity_csv(str(csv_path))

    assert imported_count == 1


def test_import_dexcom_clarity_csv_returns_zero_for_header_only_file(tmp_path):
    csv_path = tmp_path / "dexcom.csv"

    csv_path.write_text(
        "Timestamp (YYYY-MM-DDThh:mm:ss),Glucose Value (mg/dL)\n",
        encoding="utf-8",
    )

    imported_count = import_dexcom_clarity_csv(str(csv_path))

    assert imported_count == 0


def test_import_dexcom_clarity_csv_imports_mmol_l_values_without_conversion(tmp_path):
    csv_path = tmp_path / "dexcom.csv"

    csv_path.write_text(
        "Timestamp (YYYY-MM-DDThh:mm:ss),Glucose Value (mmol/L),Event Type\n"
        "2026-08-12T16:00:00,6.7,EGV\n",
        encoding="utf-8",
    )

    imported_count = import_dexcom_clarity_csv(str(csv_path))

    assert imported_count == 1

    session = SessionLocal()

    try:
        reading = (
            session.query(GlucoseReading)
            .filter(GlucoseReading.source == DEXCOM_SOURCE)
            .one()
        )

        assert reading.recorded_at == datetime(2026, 8, 12, 16, 0)
        assert reading.glucose_value == pytest.approx(6.7)
    finally:
        session.close()


def test_import_dexcom_clarity_csv_skips_low_and_dash_glucose_values(tmp_path):
    csv_path = tmp_path / "dexcom.csv"

    csv_path.write_text(
        "Timestamp (YYYY-MM-DDThh:mm:ss),Glucose Value (mg/dL),Event Type\n"
        "2026-08-12T17:00:00,Low,EGV\n"
        "2026-08-12T17:05:00,--,EGV\n"
        "2026-08-12T17:10:00,108,EGV\n",
        encoding="utf-8",
    )

    imported_count = import_dexcom_clarity_csv(str(csv_path))

    assert imported_count == 1

    session = SessionLocal()

    try:
        reading = (
            session.query(GlucoseReading)
            .filter(GlucoseReading.source == DEXCOM_SOURCE)
            .one()
        )

        assert reading.recorded_at == datetime(2026, 8, 12, 17, 10)
        assert reading.glucose_value == pytest.approx(6.0)
    finally:
        session.close()
