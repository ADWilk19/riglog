import csv
import json
from datetime import date, datetime
from urllib.parse import urlencode
from urllib.request import urlopen
import os

from app.db.database import SessionLocal
from app.db.models import DailyEnvironment

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

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


def build_open_meteo_archive_url(
    *,
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> str:
    """
    Build an Open-Meteo historical daily weather API URL.

    This function is pure: it performs no network I/O.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": ",".join(
            [
                "temperature_2m_mean",
                "temperature_2m_min",
                "temperature_2m_max",
            ]
        ),
        "temperature_unit": "celsius",
        "timezone": "auto",
    }

    return f"{OPEN_METEO_ARCHIVE_URL}?{urlencode(params)}"


def fetch_open_meteo_daily_json(
    *,
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
    timeout_seconds: int = 20,
) -> dict:
    """
    Fetch historical daily weather JSON from Open-Meteo.

    Network I/O is isolated here so normalisation remains pure and testable.
    """
    url = build_open_meteo_archive_url(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
    )

    with urlopen(url, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def import_open_meteo_historical_weather(
    *,
    location_label: str,
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> int:
    """
    Fetch, normalise, and persist Open-Meteo historical daily weather rows.
    """
    payload = fetch_open_meteo_daily_json(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
    )

    rows = normalise_open_meteo_daily_json(
        payload,
        location_label=location_label,
    )

    return import_open_meteo_daily_rows(rows)


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
        avg_temperature_c = _get_optional_list_value(mean_temperatures, index)

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


def import_open_meteo_daily_rows(rows: list[dict]) -> int:
    """Persist normalised Open-Meteo daily rows into DailyEnvironment."""
    session = SessionLocal()
    imported_count = 0

    try:
        for row in rows:
            environment_date = row["date"]
            location_label = row.get("location_label") or "default"
            source = row.get("source") or "open_meteo"

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
                latitude=row.get("latitude"),
                longitude=row.get("longitude"),
                avg_temperature_c=row["avg_temperature_c"],
                min_temperature_c=row.get("min_temperature_c"),
                max_temperature_c=row.get("max_temperature_c"),
                source=source,
                notes=None,
            )

            session.add(environment_row)
            imported_count += 1

        session.commit()
        return imported_count

    finally:
        session.close()


def get_open_meteo_location_config(
    location_label: str,
    environ: dict[str, str] | None = None,
) -> dict:
    """
    Load Open-Meteo location config from environment variables.

    Expected variable pattern for location_label="home":

    RIGLOG_OPEN_METEO_HOME_LATITUDE
    RIGLOG_OPEN_METEO_HOME_LONGITUDE

    The label is normalised to uppercase and hyphens/spaces become underscores.
    """
    environ = environ or os.environ

    env_label = (
        location_label
        .strip()
        .upper()
        .replace("-", "_")
        .replace(" ", "_")
    )

    latitude_key = f"RIGLOG_OPEN_METEO_{env_label}_LATITUDE"
    longitude_key = f"RIGLOG_OPEN_METEO_{env_label}_LONGITUDE"

    latitude_text = environ.get(latitude_key)
    longitude_text = environ.get(longitude_key)

    if not latitude_text or not longitude_text:
        raise ValueError(
            "Missing Open-Meteo location config for "
            f"{location_label!r}. Expected {latitude_key} and {longitude_key}."
        )

    return {
        "location_label": location_label,
        "latitude": float(latitude_text),
        "longitude": float(longitude_text),
    }


def import_open_meteo_historical_weather_for_location(
    *,
    location_label: str,
    start_date: date,
    end_date: date,
    environ: dict[str, str] | None = None,
) -> int:
    """
    Import Open-Meteo historical weather using coordinates from environment config.
    """
    location_config = get_open_meteo_location_config(
        location_label=location_label,
        environ=environ,
    )

    return import_open_meteo_historical_weather(
        location_label=location_config["location_label"],
        latitude=location_config["latitude"],
        longitude=location_config["longitude"],
        start_date=start_date,
        end_date=end_date,
    )
