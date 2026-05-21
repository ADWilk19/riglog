from __future__ import annotations

from app.db.database import SessionLocal
from app.db.models import WorkoutSession, WorkoutSet


def clear_imported_workout_data(
    source: str = "workout_csv",
    session=None,
) -> dict[str, int]:
    """
    Delete imported workout sessions and their sets for a given source.

    This preserves:
    - exercises
    - workout routines
    - workout routine/exercise mappings

    Args:
        source: WorkoutSession.source value to clear.
        session: Optional SQLAlchemy session for isolated tests.

    Returns:
        Dictionary containing deleted counts:
        - sets
        - sessions
    """
    owns_session = session is None

    if owns_session:
        session = SessionLocal()

    try:
        imported_sessions = (
            session.query(WorkoutSession)
            .filter(WorkoutSession.source == source)
            .all()
        )

        imported_session_ids = [
            workout_session.id
            for workout_session in imported_sessions
        ]

        deleted_sets = 0
        deleted_sessions = 0

        if imported_session_ids:
            deleted_sets = (
                session.query(WorkoutSet)
                .filter(WorkoutSet.session_id.in_(imported_session_ids))
                .delete(synchronize_session=False)
            )

            deleted_sessions = (
                session.query(WorkoutSession)
                .filter(WorkoutSession.id.in_(imported_session_ids))
                .delete(synchronize_session=False)
            )

        session.commit()

        return {
            "sets": deleted_sets,
            "sessions": deleted_sessions,
        }

    finally:
        if owns_session:
            session.close()
