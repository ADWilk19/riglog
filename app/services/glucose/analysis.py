from app.db.database import SessionLocal
from app.db.models import GlucoseReading


def get_all_glucose_readings():
    session = SessionLocal()

    try:
        return (
            session.query(GlucoseReading)
            .order_by(GlucoseReading.recorded_at.desc())
            .all()
        )
    finally:
        session.close()


def get_glucose_reading_by_id(reading_id: int) -> GlucoseReading | None:
    session = SessionLocal()

    try:
        return session.query(GlucoseReading).filter(GlucoseReading.id == reading_id).first()
    finally:
        session.close()


def update_glucose_note(reading_id: int, notes: str | None) -> None:
    session = SessionLocal()

    try:
        reading = session.query(GlucoseReading).filter(GlucoseReading.id == reading_id).first()

        if reading is None:
            return

        reading.notes = notes or None
        session.commit()
    finally:
        session.close()


def get_glucose_summary():
    session = SessionLocal()

    try:
        readings = session.query(GlucoseReading).all()

        if not readings:
            return None

        values = [r.glucose_value for r in readings]

        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }
    finally:
        session.close()
