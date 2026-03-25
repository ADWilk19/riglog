from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import DailyActivity


def get_daily_activity() -> list[dict[str, Any]]:
    """Return daily activity rows ordered by activity_date ascending."""
    db = SessionLocal()

    try:
        stmt = select(DailyActivity).order_by(DailyActivity.activity_date.asc())
        rows = db.execute(stmt).scalars().all()

        return [
            {
                "activity_date": row.activity_date,
                "steps": row.steps or 0,
                "source": row.source or "",
            }
            for row in rows
        ]
    finally:
        db.close()
