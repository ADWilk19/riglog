from datetime import datetime

from app.db.database import SessionLocal
from app.db.models import GlucoseReading


def add_glucose_reading(glucose_value: float, recorded_at: datetime, source: str = None, notes: str = None) -> None:
    session = SessionLocal()

    try:
        reading = GlucoseReading(
            glucose_value=glucose_value,
            recorded_at=recorded_at,
            source=source,
            notes=notes
        )
        session.add(reading)
        session.commit()
    finally:
        session.close()
