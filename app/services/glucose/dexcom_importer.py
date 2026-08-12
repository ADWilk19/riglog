import csv
from datetime import datetime

from app.db.database import SessionLocal
from app.db.models import GlucoseReading


DEXCOM_SOURCE = "dexcom_clarity"
MG_DL_TO_MMOL_L = 18.0


TIMESTAMP_COLUMNS = [
    "Timestamp (YYYY-MM-DDThh:mm:ss)",
    "Timestamp",
    "Display Time",
    "displayTime",
    "systemTime",
]

GLUCOSE_COLUMNS = [
    "Glucose Value (mg/dL)",
    "Glucose Value",
    "Value",
    "value",
    "mg/dL",
]

EVENT_COLUMNS = [
    "Event Type",
    "eventType",
    "type",
]


def _first_value(row: dict[str, str], columns: list[str]) -> tuple[str | None, str | None]:
    """
    Return the first non-empty value found in the supplied candidate columns.

    Returns:
        Tuple containing the matched column name and stripped value.
        Returns (None, None) if no candidate contains a value.
    """
    for column in columns:
        value = row.get(column)

        if value is not None and value.strip():
            return column, value.strip()

    return None, None


def _parse_timestamp(value: str) -> datetime:
    """
    Parse a Dexcom timestamp into a naive datetime.

    Dexcom Clarity exports can vary slightly in timestamp formatting, so
    several common formats are accepted.
    """
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S.%f",
        "%m/%d/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
    ]

    for timestamp_format in formats:
        try:
            return datetime.strptime(value, timestamp_format)
        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

        # RigLog currently stores naive datetimes.
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)

        return parsed

    except ValueError as exc:
        raise ValueError(f"Unsupported Dexcom timestamp: {value}") from exc


def _parse_glucose_value(column: str, value: str) -> float:
    """
    Parse and normalise a Dexcom glucose value to mmol/L.

    Dexcom Clarity commonly exports glucose in mg/dL. If the matched column
    explicitly identifies mg/dL, the value is converted to mmol/L.
    """
    glucose_value = float(value)

    if "mg/dl" in column.lower():
        glucose_value /= MG_DL_TO_MMOL_L

    return round(glucose_value, 2)


def _is_glucose_event(row: dict[str, str]) -> bool:
    """
    Return True when a Dexcom row represents a glucose reading.

    Some Clarity exports contain additional event rows such as insulin,
    carbohydrates, calibration, or device events. If no event-type column
    exists, the presence of a glucose value is sufficient.
    """
    _, event_value = _first_value(row, EVENT_COLUMNS)

    if event_value is None:
        return True

    event_text = event_value.strip().lower()

    return event_text in {
        "egv",
        "glucose",
        "sensor glucose",
        "estimated glucose value",
    }


def import_dexcom_clarity_csv(file_path: str) -> int:
    """
    Import glucose readings from a Dexcom Clarity CSV export.

    The importer:

    - identifies common Dexcom timestamp and glucose column variants;
    - ignores non-glucose event rows;
    - converts mg/dL readings to mmol/L;
    - stores readings with source ``dexcom_clarity``;
    - skips readings already present with the same timestamp, glucose value,
      and source.

    Args:
        file_path: Path to the Dexcom Clarity CSV export.

    Returns:
        Number of newly inserted glucose readings.
    """
    session = SessionLocal()
    imported_count = 0

    try:
        with open(file_path, "r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)

            if not reader.fieldnames:
                raise ValueError("Dexcom CSV does not contain a header row.")

            for row in reader:
                if not _is_glucose_event(row):
                    continue

                timestamp_column, timestamp_text = _first_value(
                    row,
                    TIMESTAMP_COLUMNS,
                )
                glucose_column, glucose_text = _first_value(
                    row,
                    GLUCOSE_COLUMNS,
                )

                if timestamp_column is None or timestamp_text is None:
                    continue

                if glucose_column is None or glucose_text is None:
                    continue

                try:
                    recorded_at = _parse_timestamp(timestamp_text)
                    glucose_value = _parse_glucose_value(
                        glucose_column,
                        glucose_text,
                    )
                except (TypeError, ValueError):
                    continue

                if glucose_value <= 0:
                    continue

                existing = (
                    session.query(GlucoseReading)
                    .filter(
                        GlucoseReading.recorded_at == recorded_at,
                        GlucoseReading.glucose_value == glucose_value,
                        GlucoseReading.source == DEXCOM_SOURCE,
                    )
                    .first()
                )

                if existing:
                    continue

                reading = GlucoseReading(
                    glucose_value=glucose_value,
                    recorded_at=recorded_at,
                    source=DEXCOM_SOURCE,
                )

                session.add(reading)
                imported_count += 1

        session.commit()
        return imported_count

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()
