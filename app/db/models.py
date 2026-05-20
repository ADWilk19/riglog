from sqlalchemy import Column, Integer, Float, DateTime, String, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
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


class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = (
        UniqueConstraint("name", name="uq_exercise_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=True)
    primary_muscle = Column(String, nullable=True)
    equipment = Column(String, nullable=True)
    notes = Column(String, nullable=True)

    workout_sets = relationship("WorkoutSet", back_populates="exercise")
    routine_links = relationship("WorkoutRoutineExercise", back_populates="exercise")


class WorkoutRoutine(Base):
    __tablename__ = "workout_routines"
    __table_args__ = (
        UniqueConstraint("name", name="uq_workout_routine_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    notes = Column(String, nullable=True)

    exercise_links = relationship(
        "WorkoutRoutineExercise",
        back_populates="routine",
        cascade="all, delete-orphan",
    )
    sessions = relationship("WorkoutSession", back_populates="routine")


class WorkoutRoutineExercise(Base):
    __tablename__ = "workout_routine_exercises"
    __table_args__ = (
        UniqueConstraint(
            "routine_id",
            "exercise_id",
            name="uq_workout_routine_exercise",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    routine_id = Column(Integer, ForeignKey("workout_routines.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    display_order = Column(Integer, nullable=True)

    routine = relationship("WorkoutRoutine", back_populates="exercise_links")
    exercise = relationship("Exercise", back_populates="routine_links")


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, nullable=False, index=True)
    ended_at = Column(DateTime, nullable=True)
    routine_id = Column(Integer, ForeignKey("workout_routines.id"), nullable=True)
    workout_type = Column(String, nullable=True)
    perceived_effort = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)
    source = Column(String, nullable=True)

    routine = relationship("WorkoutRoutine", back_populates="sessions")
    sets = relationship(
        "WorkoutSet",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class WorkoutSet(Base):
    __tablename__ = "workout_sets"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "exercise_id",
            "set_number",
            name="uq_workout_set_session_exercise_set_number",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("workout_sessions.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    set_number = Column(Integer, nullable=False)
    weight_kg = Column(Float, nullable=True)
    reps = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)

    session = relationship("WorkoutSession", back_populates="sets")
    exercise = relationship("Exercise", back_populates="workout_sets")


class DailyEnvironment(Base):
    __tablename__ = "daily_environment"
    __table_args__ = (
        UniqueConstraint(
            "environment_date",
            "location_label",
            "source",
            name="uq_daily_environment_date_location_source",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    environment_date = Column(Date, nullable=False, index=True)

    location_label = Column(String, nullable=False, default="default")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    avg_temperature_c = Column(Float, nullable=False)
    min_temperature_c = Column(Float, nullable=True)
    max_temperature_c = Column(Float, nullable=True)

    source = Column(String, nullable=True)
    notes = Column(String, nullable=True)
