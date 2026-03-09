from sqlalchemy import Column, Integer, Float, DateTime
from app.db.base import Base

class GlucoseReading(Base):
    __tablename__ = "glucose_readings"

    id = Column(Integer, primary_key=True, index=True)
    glucose_value = Column(Float, nullable=False)
    recorded_at = Column(DateTime, nullable=False)
