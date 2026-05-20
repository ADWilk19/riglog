from __future__ import annotations

from app.db.database import SessionLocal
from app.db.models import Exercise, WorkoutRoutine, WorkoutRoutineExercise


EXERCISES = [
    {
        "exercise_key": "barbell_squat",
        "name": "Barbell Squat",
        "category": "Compound",
        "primary_muscle": "Quads & Glutes",
        "equipment": "Barbell",
    },
    {
        "exercise_key": "barbell_bench_press",
        "name": "Barbell Bench Press",
        "category": "Compound",
        "primary_muscle": "Chest",
        "equipment": "Barbell",
    },
    {
        "exercise_key": "standing_overhead_press",
        "name": "Standing Overhead Press",
        "category": "Compound",
        "primary_muscle": "Shoulders",
        "equipment": "Barbell",
    },
    {
        "exercise_key": "incline_press",
        "name": "Incline Press",
        "category": "Compound",
        "primary_muscle": "Chest",
        "equipment": "Dumbbells",
    },
    {
        "exercise_key": "cable_lateral_raise",
        "name": "Cable Lateral Raise",
        "category": "Accessory",
        "primary_muscle": "Shoulders",
        "equipment": "Cables",
    },
    {
        "exercise_key": "face_pull",
        "name": "Face Pull",
        "category": "Accessory",
        "primary_muscle": "Upper Back",
        "equipment": "Cables",
    },
    {
        "exercise_key": "cable_triceps_pushdown",
        "name": "Cable Triceps Pushdown",
        "category": "Accessory",
        "primary_muscle": "Triceps",
        "equipment": "Cables",
    },
    {
        "exercise_key": "deadlift",
        "name": "Deadlift",
        "category": "Compound",
        "primary_muscle": "Glutes",
        "equipment": "Barbell",
    },
    {
        "exercise_key": "pull_up_lat_pulldown",
        "name": "Pull-up / Lat Pulldown",
        "category": "Accessory",
        "primary_muscle": "Latissimus Dorsi",
        "equipment": "Machine",
    },
    {
        "exercise_key": "barbell_row",
        "name": "Barbell Row",
        "category": "Compound",
        "primary_muscle": "Latissimus Dorsi",
        "equipment": "Barbell",
    },
    {
        "exercise_key": "kelso_shrugs",
        "name": "Kelso Shrugs",
        "category": "Accessory",
        "primary_muscle": "Posterior Deltoids",
        "equipment": "Dumbbells",
    },
    {
        "exercise_key": "barbell_curl",
        "name": "Barbell Curl",
        "category": "Accessory",
        "primary_muscle": "Biceps",
        "equipment": "Barbell",
    },
    {
        "exercise_key": "romanian_deadlift",
        "name": "Romanian Deadlift",
        "category": "Compound",
        "primary_muscle": "Hamstrings",
        "equipment": "Barbell",
    },
    {
        "exercise_key": "leg_press",
        "name": "Leg Press",
        "category": "Accessory",
        "primary_muscle": "Quads & Glutes",
        "equipment": "Machine",
    },
    {
        "exercise_key": "hamstring_curl",
        "name": "Hamstring Curl",
        "category": "Accessory",
        "primary_muscle": "Hamstrings",
        "equipment": "Machine",
    },
    {
        "exercise_key": "standing_calf_raise",
        "name": "Standing Calf Raise",
        "category": "Accessory",
        "primary_muscle": "Calves",
        "equipment": "Barbell",
    },
    {
        "exercise_key": "cable_crunch",
        "name": "Cable Crunch",
        "category": "Accessory",
        "primary_muscle": "Abs",
        "equipment": "Cables",
    },
]


ROUTINES = {
    "Push": [
        "barbell_squat",
        "barbell_bench_press",
        "standing_overhead_press",
        "incline_press",
        "cable_lateral_raise",
        "face_pull",
        "cable_triceps_pushdown",
    ],
    "Pull": [
        "deadlift",
        "pull_up_lat_pulldown",
        "barbell_row",
        "face_pull",
        "kelso_shrugs",
        "barbell_curl",
    ],
    "Legs": [
        "barbell_squat",
        "romanian_deadlift",
        "leg_press",
        "hamstring_curl",
        "standing_calf_raise",
        "cable_crunch",
    ],
}


def seed_workout_catalogue(session=None) -> dict[str, int]:
    """
    Seed the workout exercise catalogue and routine mappings.

    The function is idempotent:
    - existing exercises are reused
    - existing routines are reused
    - existing routine/exercise links are reused

    Args:
        session: Optional SQLAlchemy session. When omitted, a real app session
            is created. Supplying a session is useful for isolated tests.

    Returns:
        Counts of newly created records.
    """
    owns_session = session is None

    if owns_session:
        session = SessionLocal()

    created_counts = {
        "exercises": 0,
        "routines": 0,
        "routine_exercises": 0,
    }

    try:
        exercise_by_key: dict[str, Exercise] = {}

        for exercise_data in EXERCISES:
            exercise_key = exercise_data["exercise_key"]

            exercise = (
                session.query(Exercise)
                .filter(Exercise.name == exercise_data["name"])
                .first()
            )

            if exercise is None:
                exercise = Exercise(
                    name=exercise_data["name"],
                    category=exercise_data["category"],
                    primary_muscle=exercise_data["primary_muscle"],
                    equipment=exercise_data["equipment"],
                )
                session.add(exercise)
                session.flush()
                created_counts["exercises"] += 1

            exercise_by_key[exercise_key] = exercise

        for routine_name, exercise_keys in ROUTINES.items():
            routine = (
                session.query(WorkoutRoutine)
                .filter(WorkoutRoutine.name == routine_name)
                .first()
            )

            if routine is None:
                routine = WorkoutRoutine(name=routine_name)
                session.add(routine)
                session.flush()
                created_counts["routines"] += 1

            for display_order, exercise_key in enumerate(exercise_keys, start=1):
                exercise = exercise_by_key[exercise_key]

                existing_link = (
                    session.query(WorkoutRoutineExercise)
                    .filter(
                        WorkoutRoutineExercise.routine_id == routine.id,
                        WorkoutRoutineExercise.exercise_id == exercise.id,
                    )
                    .first()
                )

                if existing_link is not None:
                    continue

                routine_exercise = WorkoutRoutineExercise(
                    routine_id=routine.id,
                    exercise_id=exercise.id,
                    display_order=display_order,
                )
                session.add(routine_exercise)
                created_counts["routine_exercises"] += 1

        session.commit()
        return created_counts

    finally:
        if owns_session:
            session.close()


if __name__ == "__main__":
    counts = seed_workout_catalogue()
    print(f"Seeded workout catalogue: {counts}")
