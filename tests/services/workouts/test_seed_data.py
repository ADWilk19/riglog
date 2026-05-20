from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Exercise, WorkoutRoutine, WorkoutRoutineExercise
from app.services.workouts.seed_data import seed_workout_catalogue


def create_test_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(bind=engine)
    return TestingSessionLocal()


def test_seed_workout_catalogue_creates_expected_records():
    session = create_test_session()

    try:
        counts = seed_workout_catalogue(session=session)

        assert counts == {
            "exercises": 17,
            "routines": 3,
            "routine_exercises": 19,
        }

        assert session.query(Exercise).count() == 17
        assert session.query(WorkoutRoutine).count() == 3
        assert session.query(WorkoutRoutineExercise).count() == 19

    finally:
        session.close()


def test_seed_workout_catalogue_is_idempotent():
    session = create_test_session()

    try:
        first_counts = seed_workout_catalogue(session=session)
        second_counts = seed_workout_catalogue(session=session)

        assert first_counts == {
            "exercises": 17,
            "routines": 3,
            "routine_exercises": 19,
        }

        assert second_counts == {
            "exercises": 0,
            "routines": 0,
            "routine_exercises": 0,
        }

        assert session.query(Exercise).count() == 17
        assert session.query(WorkoutRoutine).count() == 3
        assert session.query(WorkoutRoutineExercise).count() == 19

    finally:
        session.close()


def test_seed_workout_catalogue_preserves_routine_order():
    session = create_test_session()

    try:
        seed_workout_catalogue(session=session)

        push = (
            session.query(WorkoutRoutine)
            .filter(WorkoutRoutine.name == "Push")
            .one()
        )

        push_links = (
            session.query(WorkoutRoutineExercise)
            .filter(WorkoutRoutineExercise.routine_id == push.id)
            .order_by(WorkoutRoutineExercise.display_order)
            .all()
        )

        push_exercises = [link.exercise.name for link in push_links]

        assert push_exercises == [
            "Barbell Squat",
            "Barbell Bench Press",
            "Standing Overhead Press",
            "Incline Press",
            "Cable Lateral Raise",
            "Face Pull",
            "Cable Triceps Pushdown",
        ]

    finally:
        session.close()
