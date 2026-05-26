from __future__ import annotations

from datetime import datetime, timedelta

from app.db.database import SessionLocal
from app.db.models import (
    Exercise,
    IntradayActivity,
    WorkoutRoutine,
    WorkoutSession,
    WorkoutSet,
)


def _get_session_duration_minutes(workout_session: WorkoutSession) -> float | None:
    """Return workout duration in minutes when both start and end times exist."""
    if workout_session.started_at is None or workout_session.ended_at is None:
        return None

    duration = workout_session.ended_at - workout_session.started_at
    return duration.total_seconds() / 60


def get_workout_summary_metrics(
    session=None,
    reference_datetime: datetime | None = None,
) -> dict:
    """
    Return top-level workout summary metrics.

    Args:
        session: Optional SQLAlchemy session for test injection.
        reference_datetime: Optional anchor datetime for last-7-days metrics.

    Returns:
        Dictionary containing:
        - total_sessions
        - weekly_sessions
        - average_duration_minutes
        - most_recent_workout
        - total_sets
        - total_volume_kg
    """
    owns_session = session is None

    if owns_session:
        session = SessionLocal()

    if reference_datetime is None:
        reference_datetime = datetime.now()

    week_cutoff = reference_datetime - timedelta(days=7)

    try:
        workout_sessions = (
            session.query(WorkoutSession)
            .order_by(WorkoutSession.started_at.desc())
            .all()
        )

        workout_sets = session.query(WorkoutSet).all()

        total_sessions = len(workout_sessions)

        weekly_sessions = sum(
            1
            for workout_session in workout_sessions
            if workout_session.started_at >= week_cutoff
        )

        durations = [
            duration
            for duration in (
                _get_session_duration_minutes(workout_session)
                for workout_session in workout_sessions
            )
            if duration is not None
        ]

        average_duration_minutes = (
            round(sum(durations) / len(durations), 1)
            if durations
            else None
        )

        most_recent = workout_sessions[0] if workout_sessions else None

        most_recent_workout = None
        if most_recent is not None:
            routine_name = most_recent.routine.name if most_recent.routine else None

            most_recent_workout = {
                "id": most_recent.id,
                "started_at": most_recent.started_at,
                "ended_at": most_recent.ended_at,
                "workout_type": most_recent.workout_type,
                "routine": routine_name,
                "perceived_effort": most_recent.perceived_effort,
                "notes": most_recent.notes,
            }

        total_sets = len(workout_sets)

        total_volume_kg = sum(
            (workout_set.weight_kg or 0) * (workout_set.reps or 0)
            for workout_set in workout_sets
        )

        return {
            "total_sessions": total_sessions,
            "weekly_sessions": weekly_sessions,
            "average_duration_minutes": average_duration_minutes,
            "most_recent_workout": most_recent_workout,
            "total_sets": total_sets,
            "total_volume_kg": round(total_volume_kg, 1),
        }

    finally:
        if owns_session:
            session.close()


def get_volume_by_exercise(session=None) -> list[dict]:
    """
    Return total training volume grouped by exercise.

    Volume is calculated as:

        weight_kg * reps

    Returns:
        List of dictionaries containing:
        - exercise_id
        - exercise_name
        - total_sets
        - total_reps
        - total_volume_kg
    """
    owns_session = session is None

    if owns_session:
        session = SessionLocal()

    try:
        workout_sets = (
            session.query(WorkoutSet)
            .join(Exercise, WorkoutSet.exercise_id == Exercise.id)
            .all()
        )

        grouped: dict[int, dict] = {}

        for workout_set in workout_sets:
            exercise = workout_set.exercise

            if exercise.id not in grouped:
                grouped[exercise.id] = {
                    "exercise_id": exercise.id,
                    "exercise_name": exercise.name,
                    "total_sets": 0,
                    "total_reps": 0,
                    "total_volume_kg": 0.0,
                }

            reps = workout_set.reps or 0
            weight = workout_set.weight_kg or 0

            grouped[exercise.id]["total_sets"] += 1
            grouped[exercise.id]["total_reps"] += reps
            grouped[exercise.id]["total_volume_kg"] += weight * reps

        results = list(grouped.values())

        for row in results:
            row["total_volume_kg"] = round(row["total_volume_kg"], 1)

        return sorted(
            results,
            key=lambda row: row["total_volume_kg"],
            reverse=True,
        )

    finally:
        if owns_session:
            session.close()


def get_volume_by_workout_type(session=None) -> list[dict]:
    """
    Return total training volume grouped by workout type.

    Returns:
        List of dictionaries containing:
        - workout_type
        - total_sessions
        - total_sets
        - total_reps
        - total_volume_kg
    """
    owns_session = session is None

    if owns_session:
        session = SessionLocal()

    try:
        workout_sets = (
            session.query(WorkoutSet)
            .join(WorkoutSession, WorkoutSet.session_id == WorkoutSession.id)
            .all()
        )

        grouped: dict[str, dict] = {}

        for workout_set in workout_sets:
            workout_session = workout_set.session
            workout_type = workout_session.workout_type or "Uncategorised"

            if workout_type not in grouped:
                grouped[workout_type] = {
                    "workout_type": workout_type,
                    "session_ids": set(),
                    "total_sets": 0,
                    "total_reps": 0,
                    "total_volume_kg": 0.0,
                }

            reps = workout_set.reps or 0
            weight = workout_set.weight_kg or 0

            grouped[workout_type]["session_ids"].add(workout_session.id)
            grouped[workout_type]["total_sets"] += 1
            grouped[workout_type]["total_reps"] += reps
            grouped[workout_type]["total_volume_kg"] += weight * reps

        results = []

        for row in grouped.values():
            results.append(
                {
                    "workout_type": row["workout_type"],
                    "total_sessions": len(row["session_ids"]),
                    "total_sets": row["total_sets"],
                    "total_reps": row["total_reps"],
                    "total_volume_kg": round(row["total_volume_kg"], 1),
                }
            )

        return sorted(
            results,
            key=lambda row: row["total_volume_kg"],
            reverse=True,
        )

    finally:
        if owns_session:
            session.close()


def get_recent_workout_sessions(limit: int = 10, session=None) -> list[dict]:
    """
    Return recent workout sessions for table display.

    Args:
        limit: Maximum number of sessions to return.
        session: Optional SQLAlchemy session for test injection.

    Returns:
        List of dictionaries containing session summary data.
    """
    owns_session = session is None

    if owns_session:
        session = SessionLocal()

    try:
        workout_sessions = (
            session.query(WorkoutSession)
            .order_by(WorkoutSession.started_at.desc())
            .limit(limit)
            .all()
        )

        results = []

        for workout_session in workout_sessions:
            duration = _get_session_duration_minutes(workout_session)

            set_count = len(workout_session.sets)
            total_volume = sum(
                (workout_set.weight_kg or 0) * (workout_set.reps or 0)
                for workout_set in workout_session.sets
            )

            routine_name = (
                workout_session.routine.name
                if workout_session.routine
                else None
            )

            results.append(
                {
                    "id": workout_session.id,
                    "started_at": workout_session.started_at,
                    "ended_at": workout_session.ended_at,
                    "duration_minutes": round(duration, 1) if duration is not None else None,
                    "workout_type": workout_session.workout_type,
                    "routine": routine_name,
                    "perceived_effort": workout_session.perceived_effort,
                    "set_count": set_count,
                    "total_volume_kg": round(total_volume, 1),
                    "notes": workout_session.notes,
                }
            )

        return results

    finally:
        if owns_session:
            session.close()

def get_exercises_with_workout_data(session=None) -> list[dict]:
    """
    Return exercises that have at least one logged workout set.

    Intended for populating an exercise dropdown in the Workout tab.

    Returns:
        List of dictionaries containing:
        - exercise_id
        - exercise_key
        - exercise_name
    """
    owns_session = session is None

    if owns_session:
        session = SessionLocal()

    try:
        exercises = (
            session.query(Exercise)
            .join(WorkoutSet, WorkoutSet.exercise_id == Exercise.id)
            .distinct()
            .order_by(Exercise.name.asc())
            .all()
        )

        return [
            {
                "exercise_id": exercise.id,
                "exercise_key": exercise.exercise_key,
                "exercise_name": exercise.name,
            }
            for exercise in exercises
        ]

    finally:
        if owns_session:
            session.close()


def get_exercise_progression(
    exercise_id: int,
    session=None,
) -> list[dict]:
    """
    Return selected-exercise progression by workout date.

    For each date, the function returns the heaviest set for that exercise,
    plus useful context for future chart tooltips/cards.

    Args:
        exercise_id: Database ID of the exercise.
        session: Optional SQLAlchemy session for test injection.

    Returns:
        List of dictionaries containing:
        - date
        - exercise_id
        - exercise_name
        - max_weight_kg
        - reps_at_max_weight
        - workout_type
        - set_count
        - total_reps
        - total_volume_kg
    """
    owns_session = session is None

    if owns_session:
        session = SessionLocal()

    try:
        workout_sets = (
            session.query(WorkoutSet)
            .join(WorkoutSession, WorkoutSet.session_id == WorkoutSession.id)
            .join(Exercise, WorkoutSet.exercise_id == Exercise.id)
            .filter(WorkoutSet.exercise_id == exercise_id)
            .order_by(WorkoutSession.started_at.asc(), WorkoutSet.set_number.asc())
            .all()
        )

        grouped: dict = {}

        for workout_set in workout_sets:
            workout_session = workout_set.session
            exercise = workout_set.exercise
            workout_date = workout_session.started_at.date()

            if workout_date not in grouped:
                grouped[workout_date] = {
                    "date": workout_date,
                    "exercise_id": exercise.id,
                    "exercise_name": exercise.name,
                    "max_weight_kg": None,
                    "reps_at_max_weight": None,
                    "workout_type": workout_session.workout_type,
                    "set_count": 0,
                    "total_reps": 0,
                    "total_volume_kg": 0.0,
                }

            row = grouped[workout_date]

            weight = workout_set.weight_kg or 0
            reps = workout_set.reps or 0

            row["set_count"] += 1
            row["total_reps"] += reps
            row["total_volume_kg"] += weight * reps

            current_max = row["max_weight_kg"]

            if current_max is None or weight > current_max:
                row["max_weight_kg"] = weight
                row["reps_at_max_weight"] = reps
                row["workout_type"] = workout_session.workout_type

        results = []

        for row in grouped.values():
            row["total_volume_kg"] = round(row["total_volume_kg"], 1)
            results.append(row)

        return sorted(results, key=lambda row: row["date"])

    finally:
        if owns_session:
            session.close()


def get_exercise_progression_summary(
    exercise_id: int,
    session=None,
) -> dict:
    """
    Return summary cards for a selected exercise progression view.

    Intended future cards:
    - Most Weight Lifted
    - Most Reps Lifted
    - Date Lifted

    Args:
        exercise_id: Database ID of the exercise.
        session: Optional SQLAlchemy session for test injection.

    Returns:
        Dictionary containing:
        - exercise_id
        - exercise_name
        - max_weight_kg
        - reps_at_max_weight
        - date_of_max_weight
        - max_reps
    """
    owns_session = session is None

    if owns_session:
        session = SessionLocal()

    try:
        workout_sets = (
            session.query(WorkoutSet)
            .join(WorkoutSession, WorkoutSet.session_id == WorkoutSession.id)
            .join(Exercise, WorkoutSet.exercise_id == Exercise.id)
            .filter(WorkoutSet.exercise_id == exercise_id)
            .order_by(WorkoutSession.started_at.asc(), WorkoutSet.set_number.asc())
            .all()
        )

        if not workout_sets:
            return {
                "exercise_id": exercise_id,
                "exercise_name": None,
                "max_weight_kg": None,
                "reps_at_max_weight": None,
                "date_of_max_weight": None,
                "max_reps": None,
            }

        exercise = workout_sets[0].exercise

        max_weight_set = max(
            workout_sets,
            key=lambda workout_set: (
                workout_set.weight_kg or 0,
                workout_set.session.started_at,
            ),
        )

        max_reps = max(
            workout_set.reps or 0
            for workout_set in workout_sets
        )

        return {
            "exercise_id": exercise.id,
            "exercise_name": exercise.name,
            "max_weight_kg": max_weight_set.weight_kg,
            "reps_at_max_weight": max_weight_set.reps,
            "date_of_max_weight": max_weight_set.session.started_at.date(),
            "max_reps": max_reps,
        }

    finally:
        if owns_session:
            session.close()


def get_workout_session_calorie_analysis(session=None) -> list[dict]:
    """
    Return workout session calorie analysis by aligning workout windows
    with intraday activity calorie burn.

    Only sessions with both started_at and ended_at are included.
    """
    owns_session = session is None

    if owns_session:
        session = SessionLocal()

    try:
        workout_sessions = (
            session.query(WorkoutSession)
            .filter(WorkoutSession.ended_at.isnot(None))
            .order_by(WorkoutSession.started_at.asc())
            .all()
        )

        results = []

        for workout_session in workout_sessions:
            duration = _get_session_duration_minutes(workout_session)

            if duration is None or duration <= 0:
                continue

            workout_sets = workout_session.sets

            total_sets = len(workout_sets)
            total_reps = sum(workout_set.reps or 0 for workout_set in workout_sets)
            total_volume_kg = sum(
                (workout_set.weight_kg or 0) * (workout_set.reps or 0)
                for workout_set in workout_sets
            )
            max_weight_kg = max(
                [(workout_set.weight_kg or 0) for workout_set in workout_sets],
                default=0,
            )

            calories_burned = (
                session.query(IntradayActivity)
                .filter(
                    IntradayActivity.recorded_at >= workout_session.started_at,
                    IntradayActivity.recorded_at <= workout_session.ended_at,
                )
                .with_entities(IntradayActivity.calories_burned)
                .all()
            )

            total_calories = sum(
                row.calories_burned or 0
                for row in calories_burned
            )

            average_load_per_rep = (
                total_volume_kg / total_reps
                if total_reps > 0
                else None
            )

            calories_per_minute = (
                total_calories / duration
                if duration > 0
                else None
            )

            calories_per_kg_lifted = (
                total_calories / total_volume_kg
                if total_volume_kg > 0
                else None
            )

            results.append(
                {
                    "session_id": workout_session.id,
                    "workout_type": workout_session.workout_type,
                    "started_at": workout_session.started_at,
                    "ended_at": workout_session.ended_at,
                    "duration_minutes": round(duration, 1),
                    "total_sets": total_sets,
                    "total_reps": total_reps,
                    "total_volume_kg": round(total_volume_kg, 1),
                    "average_load_per_rep": (
                        round(average_load_per_rep, 1)
                        if average_load_per_rep is not None
                        else None
                    ),
                    "max_weight_kg": round(max_weight_kg, 1),
                    "calories_burned": round(total_calories, 2),
                    "calories_per_minute": (
                        round(calories_per_minute, 2)
                        if calories_per_minute is not None
                        else None
                    ),
                    "calories_per_kg_lifted": (
                        round(calories_per_kg_lifted, 4)
                        if calories_per_kg_lifted is not None
                        else None
                    ),
                }
            )

        return results

    finally:
        if owns_session:
            session.close()
