from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Exercise, WorkoutRoutine, WorkoutSession, WorkoutSet
from app.services.workouts.analysis import (
    get_recent_workout_sessions,
    get_volume_by_exercise,
    get_volume_by_workout_type,
    get_workout_summary_metrics,
)


def create_test_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(bind=engine)
    return TestingSessionLocal()


def seed_workout_test_data(session):
    bench_press = Exercise(
        name="Barbell Bench Press",
        category="Compound",
        primary_muscle="Chest",
        equipment="Barbell",
    )
    squat = Exercise(
        name="Barbell Squat",
        category="Compound",
        primary_muscle="Quads & Glutes",
        equipment="Barbell",
    )
    push = WorkoutRoutine(name="Push")
    legs = WorkoutRoutine(name="Legs")

    session.add_all([bench_press, squat, push, legs])
    session.commit()

    recent_push_session = WorkoutSession(
        started_at=datetime(2026, 5, 20, 9, 0),
        ended_at=datetime(2026, 5, 20, 10, 0),
        routine_id=push.id,
        workout_type="Push",
        perceived_effort=7,
        notes="Good push session",
        source="test",
    )

    older_legs_session = WorkoutSession(
        started_at=datetime(2026, 5, 1, 9, 0),
        ended_at=datetime(2026, 5, 1, 9, 45),
        routine_id=legs.id,
        workout_type="Legs",
        perceived_effort=8,
        notes="Older legs session",
        source="test",
    )

    session.add_all([recent_push_session, older_legs_session])
    session.commit()

    session.add_all(
        [
            WorkoutSet(
                session_id=recent_push_session.id,
                exercise_id=bench_press.id,
                set_number=1,
                weight_kg=60,
                reps=8,
            ),
            WorkoutSet(
                session_id=recent_push_session.id,
                exercise_id=bench_press.id,
                set_number=2,
                weight_kg=65,
                reps=6,
            ),
            WorkoutSet(
                session_id=older_legs_session.id,
                exercise_id=squat.id,
                set_number=1,
                weight_kg=80,
                reps=5,
            ),
        ]
    )
    session.commit()


def test_get_workout_summary_metrics_returns_expected_values():
    session = create_test_session()

    try:
        seed_workout_test_data(session)

        metrics = get_workout_summary_metrics(
            session=session,
            reference_datetime=datetime(2026, 5, 20, 12, 0),
        )

        assert metrics["total_sessions"] == 2
        assert metrics["weekly_sessions"] == 1
        assert metrics["average_duration_minutes"] == 52.5
        assert metrics["total_sets"] == 3
        assert metrics["total_volume_kg"] == 1270.0

        assert metrics["most_recent_workout"]["workout_type"] == "Push"
        assert metrics["most_recent_workout"]["routine"] == "Push"
        assert metrics["most_recent_workout"]["perceived_effort"] == 7

    finally:
        session.close()


def test_get_workout_summary_metrics_handles_empty_database():
    session = create_test_session()

    try:
        metrics = get_workout_summary_metrics(
            session=session,
            reference_datetime=datetime(2026, 5, 20, 12, 0),
        )

        assert metrics == {
            "total_sessions": 0,
            "weekly_sessions": 0,
            "average_duration_minutes": None,
            "most_recent_workout": None,
            "total_sets": 0,
            "total_volume_kg": 0,
        }

    finally:
        session.close()


def test_get_volume_by_exercise_returns_sorted_volume_totals():
    session = create_test_session()

    try:
        seed_workout_test_data(session)

        results = get_volume_by_exercise(session=session)

        assert results == [
            {
                "exercise_id": 1,
                "exercise_name": "Barbell Bench Press",
                "total_sets": 2,
                "total_reps": 14,
                "total_volume_kg": 870.0,
            },
            {
                "exercise_id": 2,
                "exercise_name": "Barbell Squat",
                "total_sets": 1,
                "total_reps": 5,
                "total_volume_kg": 400.0,
            },
        ]

    finally:
        session.close()


def test_get_volume_by_workout_type_returns_sorted_volume_totals():
    session = create_test_session()

    try:
        seed_workout_test_data(session)

        results = get_volume_by_workout_type(session=session)

        assert results == [
            {
                "workout_type": "Push",
                "total_sessions": 1,
                "total_sets": 2,
                "total_reps": 14,
                "total_volume_kg": 870.0,
            },
            {
                "workout_type": "Legs",
                "total_sessions": 1,
                "total_sets": 1,
                "total_reps": 5,
                "total_volume_kg": 400.0,
            },
        ]

    finally:
        session.close()


def test_get_recent_workout_sessions_returns_limited_recent_sessions():
    session = create_test_session()

    try:
        seed_workout_test_data(session)

        results = get_recent_workout_sessions(limit=1, session=session)

        assert len(results) == 1

        recent = results[0]

        assert recent["workout_type"] == "Push"
        assert recent["routine"] == "Push"
        assert recent["duration_minutes"] == 60.0
        assert recent["perceived_effort"] == 7
        assert recent["set_count"] == 2
        assert recent["total_volume_kg"] == 870.0
        assert recent["notes"] == "Good push session"

    finally:
        session.close()
