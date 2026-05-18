import csv
from datetime import datetime

from app.db.database import SessionLocal
from app.db.models import DailyEnvironment


def import_daily_environment_csv(file_path: str) -> int:
    """
    Import daily environmental data from a manual CSV file.

    Expected columns:
    - date
    - avg_temperature_c

    Optional columns:
    - min_temperature_c
    - max_temperature_c
    - source
    - notes

    Duplicate rows are skipped using environment_date + source.
    """
    session = SessionLocal()
    imported_count = 0

    try:
        with open(file_path, "r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)

            for row in reader:
                date_text = (row.get("date") or "").strip()
                avg_temperature_text = (
                    row.get("avg_temperature_c") or ""
                ).strip()

                if not date_text or not avg_temperature_text:
                    continue

                environment_date = datetime.strptime(
                    date_text,
                    "%Y-%m-%d",
                ).date()

                avg_temperature_c = float(avg_temperature_text)

                min_temperature_c = _parse_optional_float(
                    row.get("min_temperature_c")
                )
                max_temperature_c = _parse_optional_float(
                    row.get("max_temperature_c")
                )

                location_label = (row.get("location_label") or "default").strip() or "default"
                latitude = _parse_optional_float(row.get("latitude"))
                longitude = _parse_optional_float(row.get("longitude"))
                source = (row.get("source") or "manual").strip() or "manual"
                notes = (row.get("notes") or "").strip() or None

                existing = (
                    session.query(DailyEnvironment)
                    .filter(
                        DailyEnvironment.environment_date == environment_date,
                        DailyEnvironment.location_label == location_label,
                        DailyEnvironment.source == source,
                    )
                    .first()
                )

                if existing:
                    continue

                environment_row = DailyEnvironment(
                    environment_date=environment_date,
                    location_label=location_label,
                    latitude=latitude,
                    longitude=longitude,
                    avg_temperature_c=avg_temperature_c,
                    min_temperature_c=min_temperature_c,
                    max_temperature_c=max_temperature_c,
                    source=source,
                    notes=notes,
                )

                session.add(environment_row)
                imported_count += 1



        session.commit()
        return imported_count

    finally:
        session.close()


def _parse_optional_float(value: str | None) -> float | None:
    """Parse an optional float value from CSV text."""
    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    return float(value)


def _get_optional_list_value(values: list, index: int):
    """Return a list value by index, or None when the index is missing."""
    if index >= len(values):
        return None

    return values[index]


def normalise_open_meteo_daily_json(
    payload: dict,
    location_label: str,
) -> list[dict]:
    """Normalise Open-Meteo daily JSON into DailyEnvironment row dictionaries."""
    daily = payload.get("daily", {})

    dates = daily.get("time", [])
    mean_temperatures = daily.get("temperature_2m_mean", [])
    min_temperatures = daily.get("temperature_2m_min", [])
    max_temperatures = daily.get("temperature_2m_max", [])

    latitude = payload.get("latitude")
    longitude = payload.get("longitude")

    rows = []

    for index, date_text in enumerate(dates):
        avg_temperature_c = mean_temperatures[index]

        if not date_text or avg_temperature_c is None:
            continue

        rows.append(
            {
                "date": datetime.strptime(date_text, "%Y-%m-%d").date(),
                "location_label": location_label,
                "latitude": latitude,
                "longitude": longitude,
                "avg_temperature_c": avg_temperature_c,
                "min_temperature_c": _get_optional_list_value(
                    min_temperatures,
                    index
                ),
                "max_temperature_c": _get_optional_list_value(
                    max_temperatures,
                    index
                ),
                "source": "open_meteo",
            }
        )

    return rows
