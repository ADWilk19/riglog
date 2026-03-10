from app.db.database import SessionLocal
from app.db.models import GlucoseReading


def get_all_glucose_readings():
    session = SessionLocal()

    try:
        return session.query(GlucoseReading).order_by(GlucoseReading.recorded_at.desc()).all()
    finally:
        session.close()
