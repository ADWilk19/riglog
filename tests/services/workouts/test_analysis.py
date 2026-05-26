from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import (
    Exercise,
    IntradayActivity,
    WorkoutRoutine,
    WorkoutSession,
    WorkoutSet,
)
from app.services.workouts.analysis import (
    get_exercise_progression,
    get_exercise_progression_summary,
    get_exercises_with_workout_data,
    get_recent_workout_sessions,
    get_volume_by_exercise,
    get_volume_by_workout_type,
    get_workout_summary_metrics,
    get_workout_session_calorie_analysis,
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


def test_get_exercises_with_workout_data_returns_only_logged_exercises():
    session = create_test_session()

    try:
        seed_workout_test_data(session)

        unused_exercise = Exercise(
            name="Unused Exercise",
            category="Accessory",
            primary_muscle="Shoulders",
            equipment="Dumbbells",
        )
        session.add(unused_exercise)
        session.commit()

        results = get_exercises_with_workout_data(session=session)

        exercise_names = [row["exercise_name"] for row in results]

        assert exercise_names == [
            "Barbell Bench Press",
            "Barbell Squat",
        ]

    finally:
        session.close()


def test_get_exercise_progression_returns_max_weight_by_date():
    session = create_test_session()

    try:
        seed_workout_test_data(session)

        bench = (
            session.query(Exercise)
            .filter(Exercise.name == "Barbell Bench Press")
            .one()
        )

        results = get_exercise_progression(
            exercise_id=bench.id,
            session=session,
        )

        assert results == [
            {
                "date": datetime(2026, 5, 20).date(),
                "exercise_id": bench.id,
                "exercise_name": "Barbell Bench Press",
                "max_weight_kg": 65,
                "reps_at_max_weight": 6,
                "workout_type": "Push",
                "set_count": 2,
                "total_reps": 14,
                "total_volume_kg": 870.0,
            }
        ]

    finally:
        session.close()


def test_get_exercise_progression_tracks_same_exercise_across_workout_types():
    session = create_test_session()

    try:
        seed_workout_test_data(session)

        squat = (
            session.query(Exercise)
            .filter(Exercise.name == "Barbell Squat")
            .one()
        )

        push = (
            session.query(WorkoutRoutine)
            .filter(WorkoutRoutine.name == "Push")
            .one()
        )

        push_squat_session = WorkoutSession(
            started_at=datetime(2026, 5, 20, 11, 0),
            ended_at=datetime(2026, 5, 20, 11, 45),
            routine_id=push.id,
            workout_type="Push",
            perceived_effort=8,
            source="test",
        )
        session.add(push_squat_session)
        session.commit()

        session.add(
            WorkoutSet(
                session_id=push_squat_session.id,
                exercise_id=squat.id,
                set_number=1,
                weight_kg=120,
                reps=1,
            )
        )
        session.commit()

        results = get_exercise_progression(
            exercise_id=squat.id,
            session=session,
        )

        assert results == [
            {
                "date": datetime(2026, 5, 1).date(),
                "exercise_id": squat.id,
                "exercise_name": "Barbell Squat",
                "max_weight_kg": 80,
                "reps_at_max_weight": 5,
                "workout_type": "Legs",
                "set_count": 1,
                "total_reps": 5,
                "total_volume_kg": 400.0,
            },
            {
                "date": datetime(2026, 5, 20).date(),
                "exercise_id": squat.id,
                "exercise_name": "Barbell Squat",
                "max_weight_kg": 120,
                "reps_at_max_weight": 1,
                "workout_type": "Push",
                "set_count": 1,
                "total_reps": 1,
                "total_volume_kg": 120.0,
            },
        ]

    finally:
        session.close()


def test_get_exercise_progression_summary_returns_card_metrics():
    session = create_test_session()

    try:
        seed_workout_test_data(session)

        bench = (
            session.query(Exercise)
            .filter(Exercise.name == "Barbell Bench Press")
            .one()
        )

        summary = get_exercise_progression_summary(
            exercise_id=bench.id,
            session=session,
        )

        assert summary == {
            "exercise_id": bench.id,
            "exercise_name": "Barbell Bench Press",
            "max_weight_kg": 65,
            "reps_at_max_weight": 6,
            "date_of_max_weight": datetime(2026, 5, 20).date(),
            "max_reps": 8,
        }

    finally:
        session.close()


def test_get_exercise_progression_summary_handles_unknown_exercise():
    session = create_test_session()

    try:
        summary = get_exercise_progression_summary(
            exercise_id=999,
            session=session,
        )

        assert summary == {
            "exercise_id": 999,
            "exercise_name": None,
            "max_weight_kg": None,
            "reps_at_max_weight": None,
            "date_of_max_weight": None,
            "max_reps": None,
        }

    finally:
        session.close()


def test_get_workout_session_calorie_analysis_aligns_intraday_calories():
    session = create_test_session()

    try:
        seed_workout_test_data(session)

        session.add_all(
            [
                IntradayActivity(
                    recorded_at=datetime(2026, 5, 20, 9, 0),
                    calories_burned=5.0,
                    source="fitbit",
                ),
                IntradayActivity(
                    recorded_at=datetime(2026, 5, 20, 9, 30),
                    calories_burned=7.5,
                    source="fitbit",
                ),
                IntradayActivity(
                    recorded_at=datetime(2026, 5, 20, 10, 0),
                    calories_burned=6.0,
                    source="fitbit",
                ),
                IntradayActivity(
                    recorded_at=datetime(2026, 5, 20, 10, 30),
                    calories_burned=99.0,
                    source="fitbit",
                ),
            ]
        )
        session.commit()

        results = get_workout_session_calorie_analysis(session=session)

        push_result = [
            row for row in results
            if row["workout_type"] == "Push"
        ][0]

        assert push_result["duration_minutes"] == 60.0
        assert push_result["total_sets"] == 2
        assert push_result["total_reps"] == 14
        assert push_result["total_volume_kg"] == 870.0
        assert push_result["average_load_per_rep"] == 62.1
        assert push_result["max_weight_kg"] == 65
        assert push_result["calories_burned"] == 18.5
        assert push_result["calories_per_minute"] == 0.31
        assert push_result["calories_per_kg_lifted"] == 0.0213

    finally:
        session.close()


def test_get_workout_session_calorie_analysis_skips_sessions_without_end_time():
    session = create_test_session()

    try:
        exercise = Exercise(
            name="Barbell Bench Press",
            category="Compound",
            primary_muscle="Chest",
            equipment="Barbell",
        )
        routine = WorkoutRoutine(name="Push")

        session.add_all([exercise, routine])
        session.commit()

        workout_session = WorkoutSession(
            started_at=datetime(2026, 5, 20, 9, 0),
            ended_at=None,
            routine_id=routine.id,
            workout_type="Push",
            source="test",
        )
        session.add(workout_session)
        session.commit()

        session.add(
            WorkoutSet(
                session_id=workout_session.id,
                exercise_id=exercise.id,
                set_number=1,
                weight_kg=60,
                reps=8,
            )
        )
        session.commit()

        results = get_workout_session_calorie_analysis(session=session)

        assert results == []

    finally:
        session.close()
