import csv
from datetime import datetime

from app.db.database import SessionLocal
from app.db.models import GlucoseReading


def add_glucose_reading(
    glucose_value: float,
    recorded_at: datetime,
    source: str | None = None,
    notes: str | None = None,
) -> None:
    session = SessionLocal()

    try:
        reading = GlucoseReading(
            glucose_value=glucose_value,
            recorded_at=recorded_at,
            source=source,
            notes=notes,
        )
        session.add(reading)
        session.commit()
    finally:
        session.close()


def import_diabetes_m_csv(file_path: str) -> int:
    session = SessionLocal()
    imported_count = 0

    try:
        with open(file_path, "r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.reader(csv_file)

            # Skip Diabetes:M metadata row
            next(reader)

            # Read the actual header row
            header = next(reader)

            # Read remaining rows using that header
            dict_reader = csv.DictReader(csv_file, fieldnames=header)

            for row in dict_reader:
                glucose_text = (row.get("glucose") or "").strip()
                datetime_text = (row.get("DateTimeFormatted") or "").strip()
                notes_text = (row.get("notes") or "").strip()

                if not glucose_text or not datetime_text:
                    continue

                recorded_at = datetime.strptime(datetime_text, "%Y-%m-%d %H:%M:%S")
                glucose_value = float(glucose_text)

                existing = (
                    session.query(GlucoseReading)
                    .filter(
                        GlucoseReading.recorded_at == recorded_at,
                        GlucoseReading.glucose_value == glucose_value,
                        GlucoseReading.source == "diabetes_m",
                    )
                    .first()
                )

                if existing:
                    continue

                reading = GlucoseReading(
                    glucose_value=glucose_value,
                    recorded_at=recorded_at,
                    source="diabetes_m",
                    notes=notes_text or None,
                )

                session.add(reading)
                imported_count += 1

        session.commit()
        return imported_count

    finally:
        session.close()
