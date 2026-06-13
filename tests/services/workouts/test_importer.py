import csv
from pathlib import Path
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Exercise, WorkoutRoutine, WorkoutSession, WorkoutSet
from app.services.workouts.importer import import_workout_csv


def create_test_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(bind=engine)
    return TestingSessionLocal()


def seed_catalogue(session):
    push = WorkoutRoutine(name="Push")
    legs = WorkoutRoutine(name="Legs")

    bench = Exercise(
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

    session.add_all([push, legs, bench, squat])
    session.commit()


def write_workout_csv(path: Path, rows: list[dict]):
    fieldnames = [
        "Date",
        "Workout",
        "Start Time",
        "End Time",
        "Duration Minutes",
        "Exercise",
        "Exercise ID",
        "Set #",
        "Weight",
        "Reps",
        "Notes",
    ]

    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_import_workout_csv_creates_sessions_and_sets(tmp_path):
    session = create_test_session()

    try:
        seed_catalogue(session)

        csv_path = tmp_path / "workout_log.csv"
        write_workout_csv(
            csv_path,
            [
                {
                    "Date": "2026-05-20",
                    "Workout": "Push",
                    "Exercise": "Barbell Bench Press",
                    "Exercise ID": "barbell_bench_press",
                    "Set #": "1",
                    "Weight": "60",
                    "Reps": "8",
                    "Notes": "Comfortable",
                },
                {
                    "Date": "2026-05-20",
                    "Workout": "Push",
                    "Exercise": "Barbell Bench Press",
                    "Exercise ID": "barbell_bench_press",
                    "Set #": "2",
                    "Weight": "65",
                    "Reps": "6",
                    "Notes": "",
                },
                {
                    "Date": "2026-05-21",
                    "Workout": "Legs",
                    "Exercise": "Barbell Squat",
                    "Exercise ID": "barbell_squat",
                    "Set #": "1",
                    "Weight": "80",
                    "Reps": "5",
                    "Notes": "Solid",
                },
            ],
        )

        counts = import_workout_csv(str(csv_path), session=session)

        assert counts == {
            "sessions": 2,
            "sets": 3,
            "skipped_sets": 0,
        }

        assert session.query(WorkoutSession).count() == 2
        assert session.query(WorkoutSet).count() == 3

        push_session = (
            session.query(WorkoutSession)
            .filter(WorkoutSession.workout_type == "Push")
            .one()
        )

        assert push_session.routine.name == "Push"
        assert push_session.source == "workout_csv"
        assert len(push_session.sets) == 2

    finally:
        session.close()


def test_import_workout_csv_is_idempotent(tmp_path):
    session = create_test_session()

    try:
        seed_catalogue(session)

        csv_path = tmp_path / "workout_log.csv"
        write_workout_csv(
            csv_path,
            [
                {
                    "Date": "2026-05-20",
                    "Workout": "Push",
                    "Exercise": "Barbell Bench Press",
                    "Exercise ID": "barbell_bench_press",
                    "Set #": "1",
                    "Weight": "60",
                    "Reps": "8",
                    "Notes": "Comfortable",
                },
            ],
        )

        first_counts = import_workout_csv(str(csv_path), session=session)
        second_counts = import_workout_csv(str(csv_path), session=session)

        assert first_counts == {
            "sessions": 1,
            "sets": 1,
            "skipped_sets": 0,
        }

        assert second_counts == {
            "sessions": 0,
            "sets": 0,
            "skipped_sets": 1,
        }

        assert session.query(WorkoutSession).count() == 1
        assert session.query(WorkoutSet).count() == 1

    finally:
        session.close()


def test_import_workout_csv_raises_for_unknown_exercise(tmp_path):
    session = create_test_session()

    try:
        seed_catalogue(session)

        csv_path = tmp_path / "workout_log.csv"
        write_workout_csv(
            csv_path,
            [
                {
                    "Date": "2026-05-20",
                    "Workout": "Push",
                    "Exercise": "Unknown Exercise",
                    "Exercise ID": "unknown_exercise",
                    "Set #": "1",
                    "Weight": "60",
                    "Reps": "8",
                    "Notes": "",
                },
            ],
        )

        with pytest.raises(ValueError, match="Unknown exercise"):
            import_workout_csv(str(csv_path), session=session)

    finally:
        session.close()


def test_import_workout_csv_raises_for_missing_required_columns(tmp_path):
    session = create_test_session()

    try:
        seed_catalogue(session)

        csv_path = tmp_path / "bad_workout_log.csv"

        with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=["Date", "Workout"])
            writer.writeheader()
            writer.writerow({"Date": "2026-05-20", "Workout": "Push"})

        with pytest.raises(ValueError, match="missing required columns"):
            import_workout_csv(str(csv_path), session=session)

    finally:
        session.close()


def test_import_workout_csv_uses_start_and_end_time_when_present(tmp_path):
    session = create_test_session()

    try:
        seed_catalogue(session)

        csv_path = tmp_path / "workout_log.csv"
        write_workout_csv(
            csv_path,
            [
                {
                    "Date": "2026-05-20",
                    "Workout": "Push",
                    "Start Time": "18:30",
                    "End Time": "19:45",
                    "Exercise": "Barbell Bench Press",
                    "Exercise ID": "barbell_bench_press",
                    "Set #": "1",
                    "Weight": "60",
                    "Reps": "8",
                    "Notes": "",
                },
            ],
        )

        counts = import_workout_csv(str(csv_path), session=session)

        assert counts == {
            "sessions": 1,
            "sets": 1,
            "skipped_sets": 0,
        }

        workout_session = session.query(WorkoutSession).one()

        assert workout_session.started_at == datetime(2026, 5, 20, 18, 30)
        assert workout_session.ended_at == datetime(2026, 5, 20, 19, 45)

    finally:
        session.close()


def test_import_workout_csv_uses_duration_minutes_when_end_time_missing(tmp_path):
    session = create_test_session()

    try:
        seed_catalogue(session)

        csv_path = tmp_path / "workout_log.csv"
        write_workout_csv(
            csv_path,
            [
                {
                    "Date": "2026-05-20",
                    "Workout": "Push",
                    "Start Time": "18:30",
                    "Duration Minutes": "75",
                    "Exercise": "Barbell Bench Press",
                    "Exercise ID": "barbell_bench_press",
                    "Set #": "1",
                    "Weight": "60",
                    "Reps": "8",
                    "Notes": "",
                },
            ],
        )

        import_workout_csv(str(csv_path), session=session)

        workout_session = session.query(WorkoutSession).one()

        assert workout_session.started_at == datetime(2026, 5, 20, 18, 30)
        assert workout_session.ended_at == datetime(2026, 5, 20, 19, 45)

    finally:
        session.close()


def test_import_workout_csv_preserves_existing_default_time_behaviour(tmp_path):
    session = create_test_session()

    try:
        seed_catalogue(session)

        csv_path = tmp_path / "workout_log.csv"
        write_workout_csv(
            csv_path,
            [
                {
                    "Date": "2026-05-20",
                    "Workout": "Push",
                    "Exercise": "Barbell Bench Press",
                    "Exercise ID": "barbell_bench_press",
                    "Set #": "1",
                    "Weight": "60",
                    "Reps": "8",
                    "Notes": "",
                },
            ],
        )

        import_workout_csv(str(csv_path), session=session)

        workout_session = session.query(WorkoutSession).one()

        assert workout_session.started_at == datetime(2026, 5, 20, 9, 0)
        assert workout_session.ended_at is None

    finally:
        session.close()


def test_import_workout_csv_accepts_short_uk_dash_date(tmp_path):
    session = create_test_session()

    try:
        seed_catalogue(session)

        csv_path = tmp_path / "workout_log.csv"
        write_workout_csv(
            csv_path,
            [
                {
                    "Date": "11-6-26",
                    "Workout": "Push",
                    "Exercise": "Barbell Bench Press",
                    "Exercise ID": "barbell_bench_press",
                    "Set #": "1",
                    "Weight": "60",
                    "Reps": "8",
                    "Notes": "",
                },
            ],
        )

        counts = import_workout_csv(str(csv_path), session=session)

        assert counts == {
            "sessions": 1,
            "sets": 1,
            "skipped_sets": 0,
        }

        workout_session = session.query(WorkoutSession).one()
        assert workout_session.started_at == datetime(2026, 6, 11, 9, 0)

    finally:
        session.close()


def test_import_workout_csv_skips_duplicate_set_rows(tmp_path):
    session = create_test_session()

    try:
        seed_catalogue(session)

        csv_path = tmp_path / "workout_log.csv"
        write_workout_csv(
            csv_path,
            [
                {
                    "Date": "2026-06-12",
                    "Workout": "Push",
                    "Exercise": "Barbell Bench Press",
                    "Exercise ID": "barbell_bench_press",
                    "Set #": "1",
                    "Weight": "50",
                    "Reps": "8",
                    "Notes": "",
                },
                {
                    "Date": "2026-06-12",
                    "Workout": "Push",
                    "Exercise": "Barbell Bench Press",
                    "Exercise ID": "barbell_bench_press",
                    "Set #": "1",
                    "Weight": "50",
                    "Reps": "8",
                    "Notes": "",
                },
            ],
        )

        counts = import_workout_csv(str(csv_path), session=session)

        assert counts == {
            "sessions": 1,
            "sets": 1,
            "skipped_sets": 1,
        }

        assert session.query(WorkoutSet).count() == 1

    finally:
        session.close()
