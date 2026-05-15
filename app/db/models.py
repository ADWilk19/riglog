from sqlalchemy import Column, Integer, Float, DateTime, String, Date, UniqueConstraint
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


class DailyActivity(Base):
    __tablename__ = "daily_activity"
    __table_args__ = (
        UniqueConstraint("activity_date", "source", name="uq_daily_activity_date_source"),
    )

    id = Column(Integer, primary_key=True, index=True)
    activity_date = Column(Date, nullable=False, index=True)
    steps = Column(Integer, nullable=True)
    calories_burned = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=True)
    active_minutes = Column(Integer, nullable=True)
    source = Column(String, nullable=True)


class IntradayActivity(Base):
    __tablename__ = "activity_intraday"
    __table_args__ = (
        UniqueConstraint(
            "recorded_at",
            "source",
            name="uq_intraday_activity_time_source"
            ),
    )

    id = Column(Integer, primary_key=True, index=True)
    recorded_at = Column(DateTime, nullable=False, index=True)
    steps = Column(Integer, nullable=True)
    calories_burned = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=True)
    source = Column(String, nullable=True)


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, nullable=False, index=True)
    ended_at = Column(DateTime, nullable=True)
    exercise = Column(String, nullable=False)
    sets = Column(Integer, nullable=True)
    reps = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    notes = Column(String, nullable=True)
    source = Column(String, nullable=True)


class DailyEnvironment(Base):
    __tablename__ = "daily_environment"
    __table_args__ = (
        UniqueConstraint(
            "environment_date",
            "source",
            name="uq_daily_environment_date_source",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    environment_date = Column(Date, nullable=False, index=True)
    avg_temperature_c = Column(Float, nullable=False)
    min_temperature_c = Column(Float, nullable=True)
    max_temperature_c = Column(Float, nullable=True)
    source = Column(String, nullable=True)
    notes = Column(String, nullable=True)
