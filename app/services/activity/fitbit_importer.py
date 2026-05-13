from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from app.db.database import SessionLocal
from app.db.models import DailyActivity, IntradayActivity
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

    def import_daily_steps(self, start_date: str, end_date: str, db=None) -> int:
        df = self.fetch_daily_steps(start_date=start_date, end_date=end_date)
        if df.empty:
            return 0

        own_session = db is None
        db = db or SessionLocal()

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
            if own_session:
                db.close()

    def fetch_intraday_activity(
    self,
    activity_date: str,
    detail_level: str = "15min",
) -> pd.DataFrame:
        """
        Fetch Fitbit intraday steps and calories for one date.

        Args:
            activity_date: Date string in YYYY-MM-DD format.
            detail_level: Fitbit detail level, e.g. "1min" or "15min".

        Returns:
            DataFrame with recorded_at, steps, calories_burned, and source.
        """
        client = FitbitClient()

        steps_rows = client.get_intraday_activity(
            resource="steps",
            activity_date=activity_date,
            detail_level=detail_level,
        )

        calories_rows = client.get_intraday_activity(
            resource="calories",
            activity_date=activity_date,
            detail_level=detail_level,
        )

        steps_df = pd.DataFrame(steps_rows)
        calories_df = pd.DataFrame(calories_rows)

        if steps_df.empty and calories_df.empty:
            return pd.DataFrame(
                columns=[
                    "recorded_at",
                    "steps",
                    "calories_burned",
                    "source",
                ]
            )

        if not steps_df.empty:
            steps_df = steps_df.rename(columns={"value": "steps"})
            steps_df["recorded_at"] = pd.to_datetime(
                activity_date + " " + steps_df["time"]
            )
            steps_df["steps"] = (
                pd.to_numeric(steps_df["steps"], errors="coerce")
                .fillna(0)
                .astype(int)
            )
            steps_df = steps_df[["recorded_at", "steps"]]
        else:
            steps_df = pd.DataFrame(columns=["recorded_at", "steps"])

        if not calories_df.empty:
            calories_df = calories_df.rename(columns={"value": "calories_burned"})
            calories_df["recorded_at"] = pd.to_datetime(
                activity_date + " " + calories_df["time"]
            )
            calories_df["calories_burned"] = pd.to_numeric(
                calories_df["calories_burned"],
                errors="coerce",
            )
            calories_df = calories_df[["recorded_at", "calories_burned"]]
        else:
            calories_df = pd.DataFrame(columns=["recorded_at", "calories_burned"])

        df = pd.merge(
            steps_df,
            calories_df,
            on="recorded_at",
            how="outer",
        ).sort_values("recorded_at")

        df["source"] = "fitbit"

        return df[
            [
                "recorded_at",
                "steps",
                "calories_burned",
                "source",
            ]
        ]

    def import_intraday_activity(
    self,
    start_date: str,
    end_date: str,
    detail_level: str = "15min",
    db=None,
) -> int:
        """
        Import Fitbit intraday activity rows idempotently.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.
            detail_level: Fitbit detail level, e.g. "1min" or "15min".
            db: Optional existing SQLAlchemy session.

        Returns:
            Number of rows inserted or updated.
        """
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        frames = []
        current = start

        while current <= end:
            frames.append(
                self.fetch_intraday_activity(
                    activity_date=current.isoformat(),
                    detail_level=detail_level,
                )
            )
            current += timedelta(days=1)

        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

        if df.empty:
            return 0

        own_session = db is None
        db = db or SessionLocal()

        rows_written = 0

        try:
            for row in df.itertuples(index=False):
                existing = (
                    db.query(IntradayActivity)
                    .filter(IntradayActivity.recorded_at == row.recorded_at)
                    .filter(IntradayActivity.source == row.source)
                    .first()
                )

                steps = None if pd.isna(row.steps) else int(row.steps)
                calories_burned = (
                    None
                    if pd.isna(row.calories_burned)
                    else float(row.calories_burned)
                )

                if existing:
                    existing.steps = steps
                    existing.calories_burned = calories_burned
                else:
                    db.add(
                        IntradayActivity(
                            recorded_at=row.recorded_at,
                            steps=steps,
                            calories_burned=calories_burned,
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
            if own_session:
                db.close()
