from datetime import date

import pandas as pd

from app.db.models import DailyActivity
from app.services.activity.fitbit_importer import FitbitImporter


def test_import_returns_zero_when_no_data(mocker, db_session):
    importer = FitbitImporter()

    mocker.patch.object(
        importer,
        "fetch_daily_steps",
        return_value=pd.DataFrame(columns=["activity_date", "steps", "source"]),
    )

    rows_written = importer.import_daily_steps(
        start_date="2026-04-01",
        end_date="2026-04-01",
        db=db_session,
    )

    assert rows_written == 0
    assert db_session.query(DailyActivity).count() == 0


def test_import_inserts_new_rows(mocker, db_session):
    importer = FitbitImporter()

    df = pd.DataFrame(
        [
            {
                "activity_date": date(2026, 4, 1),
                "steps": 12345,
                "source": "fitbit",
            },
            {
                "activity_date": date(2026, 4, 2),
                "steps": 9000,
                "source": "fitbit",
            },
        ]
    )

    mocker.patch.object(importer, "fetch_daily_steps", return_value=df)

    rows_written = importer.import_daily_steps(
        start_date="2026-04-01",
        end_date="2026-04-02",
        db=db_session,
    )

    assert rows_written == 2

    rows = (
        db_session.query(DailyActivity)
        .order_by(DailyActivity.activity_date.asc())
        .all()
    )

    assert len(rows) == 2
    assert rows[0].activity_date == date(2026, 4, 1)
    assert rows[0].steps == 12345
    assert rows[0].source == "fitbit"
    assert rows[1].activity_date == date(2026, 4, 2)
    assert rows[1].steps == 9000


def test_import_updates_existing_row(mocker, db_session):
    existing = DailyActivity(
        activity_date=date(2026, 4, 1),
        steps=5000,
        source="fitbit",
    )
    db_session.add(existing)
    db_session.commit()

    importer = FitbitImporter()

    df = pd.DataFrame(
        [
            {
                "activity_date": date(2026, 4, 1),
                "steps": 11000,
                "source": "fitbit",
            }
        ]
    )

    mocker.patch.object(importer, "fetch_daily_steps", return_value=df)

    rows_written = importer.import_daily_steps(
        start_date="2026-04-01",
        end_date="2026-04-01",
        db=db_session,
    )

    assert rows_written == 1

    row = (
        db_session.query(DailyActivity)
        .filter(DailyActivity.activity_date == date(2026, 4, 1))
        .filter(DailyActivity.source == "fitbit")
        .first()
    )

    assert row is not None
    assert row.steps == 11000
    assert db_session.query(DailyActivity).count() == 1

def test_import_rolls_back_on_failure(mocker, db_session):
    from datetime import date
    import pandas as pd
    from app.db.models import DailyActivity
    from app.services.activity.fitbit_importer import FitbitImporter

    importer = FitbitImporter()

    df = pd.DataFrame(
        [
            {
                "activity_date": date(2026, 4, 1),
                "steps": 10000,
                "source": "fitbit",
            }
        ]
    )

    mocker.patch.object(importer, "fetch_daily_steps", return_value=df)

    # Force failure during insert
    def broken_add(*args, **kwargs):
        raise Exception("DB write failure")

    mocker.patch.object(db_session, "add", side_effect=broken_add)

    import pytest

    with pytest.raises(Exception):
        importer.import_daily_steps(
            start_date="2026-04-01",
            end_date="2026-04-01",
            db=db_session,
        )

    # DB should still be empty (rollback worked)
    assert db_session.query(DailyActivity).count() == 0
