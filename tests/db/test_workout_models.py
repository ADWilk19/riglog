from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import (
    Exercise,
    WorkoutRoutine,
    WorkoutRoutineExercise,
    WorkoutSession,
    WorkoutSet,
)


def test_workout_models_can_create_related_records():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()

    try:
        exercise = Exercise(
            name="Barbell Bench Press",
            category="Strength",
            primary_muscle="Chest",
            equipment="Barbell",
        )

        routine = WorkoutRoutine(name="Push")

        session.add_all([exercise, routine])
        session.commit()

        routine_exercise = WorkoutRoutineExercise(
            routine_id=routine.id,
            exercise_id=exercise.id,
            display_order=1,
        )

        workout_session = WorkoutSession(
            started_at=datetime(2026, 5, 20, 9, 30),
            ended_at=datetime(2026, 5, 20, 10, 15),
            routine_id=routine.id,
            workout_type="Push",
            perceived_effort=7,
            notes="Solid first test session",
            source="manual",
        )

        session.add_all([routine_exercise, workout_session])
        session.commit()

        workout_set = WorkoutSet(
            session_id=workout_session.id,
            exercise_id=exercise.id,
            set_number=1,
            weight_kg=60.0,
            reps=8,
            notes="Felt comfortable",
        )

        session.add(workout_set)
        session.commit()

        saved_session = session.query(WorkoutSession).first()
        saved_set = session.query(WorkoutSet).first()

        assert saved_session is not None
        assert saved_session.routine.name == "Push"
        assert saved_session.workout_type == "Push"
        assert saved_session.perceived_effort == 7

        assert saved_set is not None
        assert saved_set.exercise.name == "Barbell Bench Press"
        assert saved_set.session.id == saved_session.id
        assert saved_set.weight_kg == 60.0
        assert saved_set.reps == 8

    finally:
        session.close()
