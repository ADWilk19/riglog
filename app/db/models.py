from sqlalchemy import Column, Integer, Float, DateTime, String
from app.db.base import Base


class GlucoseReading(Base):
    __tablename__ = "glucose_readings"

    id = Column(Integer, primary_key=True, index=True)
    glucose_value = Column(Float, nullable=False)
    recorded_at = Column(DateTime, nullable=False)
    source = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    carbs_g = Column(Float, nullable=True)
    humalog_u = Column(Float, nullable=True)
    tresiba_u = Column(Float, nullable=True)
