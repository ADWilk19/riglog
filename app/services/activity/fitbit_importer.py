from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from app.db.database import SessionLocal
from app.db.models import DailyActivity
from app.services.activity.fitbit_auth import get_fitbit_session
from app.services.activity.fitbit_client import FitbitClient


class FitbitImporter:
    BASE_URL = "https://api.fitbit.com/1/user/-"

    def fetch_daily_steps(self, start_date: str, end_date: str) -> pd.DataFrame:
        client = FitbitClient()
        rows = client.get_daily_steps(start_date, end_date)

        df = pd.DataFrame(rows)
        df = df.rename(columns={"dateTime": "activity_date", "value": "steps"})
        df["activity_date"] = pd.to_datetime(df["activity_date"]).dt.date
        df["steps"] = pd.to_numeric(df["steps"], errors="coerce").fillna(0).astype(int)
        df["source"] = "fitbit"

        return df[["activity_date", "steps", "source"]]

    def import_daily_steps(self, start_date: str, end_date: str) -> int:
        df = self.fetch_daily_steps(start_date=start_date, end_date=end_date)
        if df.empty:
            return 0

        db = SessionLocal()
        rows_written = 0

        try:
            for row in df.itertuples(index=False):
                existing = (
                    db.query(DailyActivity)
                    .filter(DailyActivity.activity_date == row.activity_date)
                    .filter(DailyActivity.source == row.source)
                    .first()
                )

                if existing:
                    existing.steps = row.steps
                else:
                    db.add(
                        DailyActivity(
                            activity_date=row.activity_date,
                            steps=row.steps,
                            source=row.source,
                        )
                    )

                rows_written += 1

            db.commit()
            return rows_written
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
