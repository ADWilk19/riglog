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
from app.services.workouts.maintenance import clear_imported_workout_data


def create_test_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(bind=engine)
    return TestingSessionLocal()


def seed_workout_data(session):
    exercise = Exercise(
        exercise_key="barbell_bench_press",
        name="Barbell Bench Press",
        category="Compound",
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

    imported_session = WorkoutSession(
        started_at=datetime(2026, 5, 20, 9, 0),
        routine_id=routine.id,
        workout_type="Push",
        source="workout_csv",
    )

    manual_session = WorkoutSession(
        started_at=datetime(2026, 5, 21, 9, 0),
        routine_id=routine.id,
        workout_type="Push",
        source="manual",
    )

    session.add_all([routine_exercise, imported_session, manual_session])
    session.commit()

    imported_set = WorkoutSet(
        session_id=imported_session.id,
        exercise_id=exercise.id,
        set_number=1,
        weight_kg=60,
        reps=8,
    )

    manual_set = WorkoutSet(
        session_id=manual_session.id,
        exercise_id=exercise.id,
        set_number=1,
        weight_kg=65,
        reps=6,
    )

    session.add_all([imported_set, manual_set])
    session.commit()


def test_clear_imported_workout_data_deletes_only_imported_sessions_and_sets():
    session = create_test_session()

    try:
        seed_workout_data(session)

        counts = clear_imported_workout_data(
            source="workout_csv",
            session=session,
        )

        assert counts == {
            "sets": 1,
            "sessions": 1,
        }

        remaining_sessions = session.query(WorkoutSession).all()
        remaining_sets = session.query(WorkoutSet).all()

        assert len(remaining_sessions) == 1
        assert len(remaining_sets) == 1

        assert remaining_sessions[0].source == "manual"
        assert remaining_sets[0].session.source == "manual"

    finally:
        session.close()


def test_clear_imported_workout_data_preserves_catalogue_and_routines():
    session = create_test_session()

    try:
        seed_workout_data(session)

        clear_imported_workout_data(
            source="workout_csv",
            session=session,
        )

        assert session.query(Exercise).count() == 1
        assert session.query(WorkoutRoutine).count() == 1
        assert session.query(WorkoutRoutineExercise).count() == 1

    finally:
        session.close()


def test_clear_imported_workout_data_returns_zero_counts_when_no_matching_source():
    session = create_test_session()

    try:
        seed_workout_data(session)

        counts = clear_imported_workout_data(
            source="unknown_source",
            session=session,
        )

        assert counts == {
            "sets": 0,
            "sessions": 0,
        }

        assert session.query(WorkoutSession).count() == 2
        assert session.query(WorkoutSet).count() == 2

    finally:
        session.close()
