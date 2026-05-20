from __future__ import annotations

import csv
from datetime import datetime, time
from pathlib import Path

from app.db.database import SessionLocal
from app.db.models import Exercise, WorkoutRoutine, WorkoutSession, WorkoutSet


REQUIRED_COLUMNS = {
    "Date",
    "Workout",
    "Exercise",
    "Set #",
    "Weight",
    "Reps",
}


def _clean_text(value: object) -> str:
    """Return stripped text for CSV values."""
    return str(value or "").strip()


def _parse_date(value: str):
    """Parse supported workout date formats."""
    value = _clean_text(value)

    for date_format in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue

    raise ValueError(f"Invalid workout date: {value}")


def _parse_int(value: str, field_name: str) -> int:
    """Parse a required integer field."""
    value = _clean_text(value)

    try:
        return int(float(value))
    except ValueError as exc:
        raise ValueError(f"Invalid {field_name}: {value}") from exc


def _parse_float(value: str, field_name: str) -> float:
    """Parse a required float field."""
    value = _clean_text(value)

    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {field_name}: {value}") from exc


def _get_or_create_workout_session(
    session,
    workout_date,
    workout_name: str,
) -> tuple[WorkoutSession, bool]:
    """Return an existing workout session for date/workout or create one."""
    started_at = datetime.combine(workout_date, time(hour=9))

    existing = (
        session.query(WorkoutSession)
        .filter(
            WorkoutSession.started_at == started_at,
            WorkoutSession.workout_type == workout_name,
            WorkoutSession.source == "workout_csv",
        )
        .first()
    )

    if existing is not None:
        return existing, False

    routine = (
        session.query(WorkoutRoutine)
        .filter(WorkoutRoutine.name == workout_name)
        .first()
    )

    workout_session = WorkoutSession(
        started_at=started_at,
        routine_id=routine.id if routine else None,
        workout_type=workout_name,
        source="workout_csv",
    )

    session.add(workout_session)
    session.flush()

    return workout_session, True


def _get_exercise_by_name(session, exercise_name: str) -> Exercise:
    """Resolve an exercise by name."""
    exercise = (
        session.query(Exercise)
        .filter(Exercise.name == exercise_name)
        .first()
    )

    if exercise is None:
        raise ValueError(f"Unknown exercise: {exercise_name}")

    return exercise


def import_workout_csv(file_path: str, session=None) -> dict[str, int]:
    """
    Import workout sessions and sets from a spreadsheet-style CSV.

    Expected columns:
    - Date
    - Workout
    - Exercise
    - Exercise ID optional / currently ignored
    - Set #
    - Weight
    - Reps
    - Notes optional

    The importer is idempotent by skipping existing sets with the same:
    - workout session
    - exercise
    - set number

    Args:
        file_path: Path to exported workout CSV.
        session: Optional SQLAlchemy session for isolated tests.

    Returns:
        Dictionary containing imported counts:
        - sessions
        - sets
        - skipped_sets
    """
    owns_session = session is None

    if owns_session:
        session = SessionLocal()

    counts = {
        "sessions": 0,
        "sets": 0,
        "skipped_sets": 0,
    }

    try:
        path = Path(file_path)

        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)

            if reader.fieldnames is None:
                raise ValueError("Workout CSV is missing a header row.")

            missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames)
            if missing_columns:
                missing_text = ", ".join(sorted(missing_columns))
                raise ValueError(f"Workout CSV is missing required columns: {missing_text}")

            for row in reader:
                date_text = _clean_text(row.get("Date"))
                workout_name = _clean_text(row.get("Workout"))
                exercise_name = _clean_text(row.get("Exercise"))

                if not date_text and not workout_name and not exercise_name:
                    continue

                workout_date = _parse_date(date_text)
                set_number = _parse_int(row.get("Set #"), "Set #")
                weight_kg = _parse_float(row.get("Weight"), "Weight")
                reps = _parse_int(row.get("Reps"), "Reps")
                notes = _clean_text(row.get("Notes")) or None

                workout_session, created_session = _get_or_create_workout_session(
                    session=session,
                    workout_date=workout_date,
                    workout_name=workout_name,
                )

                if created_session:
                    counts["sessions"] += 1

                exercise = _get_exercise_by_name(session, exercise_name)

                existing_set = (
                    session.query(WorkoutSet)
                    .filter(
                        WorkoutSet.session_id == workout_session.id,
                        WorkoutSet.exercise_id == exercise.id,
                        WorkoutSet.set_number == set_number,
                    )
                    .first()
                )

                if existing_set is not None:
                    counts["skipped_sets"] += 1
                    continue

                workout_set = WorkoutSet(
                    session_id=workout_session.id,
                    exercise_id=exercise.id,
                    set_number=set_number,
                    weight_kg=weight_kg,
                    reps=reps,
                    notes=notes,
                )

                session.add(workout_set)
                counts["sets"] += 1

        session.commit()

        return counts

    finally:
        if owns_session:
            session.close()
