from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


READING_TIMES = [
    ("07:00", 6.6, "Pre-breakfast reading"),
    ("09:15", 8.7, "Post-breakfast reading"),
    ("12:15", 6.8, "Pre-lunch reading"),
    ("14:30", 8.9, "Post-lunch reading"),
    ("18:00", 7.0, "Pre-dinner reading"),
    ("20:30", 9.2, "Post-dinner reading"),
    ("22:30", 7.8, "Before bed reading"),
]


def clamp(value: float, lower: float = 2.8, upper: float = 18.5) -> float:
    return max(lower, min(upper, value))


def generate_value(base: float, day_index: int) -> float:
    weekly_pattern = 0.4 if day_index % 7 in {5, 6} else 0.0
    random_noise = random.gauss(0, 0.9)

    value = base + weekly_pattern + random_noise

    # Occasional realistic excursions
    roll = random.random()
    if roll < 0.03:
        value -= random.uniform(1.8, 3.0)
    elif roll > 0.97:
        value += random.uniform(5.0, 8.0)
    elif roll > 0.90:
        value += random.uniform(2.5, 5.0)

    return round(clamp(value), 1)


def generate_rows(start_date: datetime, days: int) -> list[dict[str, str]]:
    rows = []

    for day_index in range(days):
        current_day = start_date + timedelta(days=day_index)

        for time_text, base, note in READING_TIMES:
            hour, minute = map(int, time_text.split(":"))

            recorded_at = current_day.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0,
            )

            glucose = generate_value(base, day_index)

            rows.append(
                {
                    "DateTimeFormatted": recorded_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "glucose": f"{glucose:.1f}",
                    "notes": note,
                }
            )

    return rows


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.writer(csv_file)

        writer.writerow(["Synthetic Diabetes:M export generated for RigLog demo"])
        writer.writerow(["DateTimeFormatted", "glucose", "notes"])

        for row in rows:
            writer.writerow(
                [
                    row["DateTimeFormatted"],
                    row["glucose"],
                    row["notes"],
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="data/demo/demo_glucose.csv",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )
    parser.add_argument(
        "--start-date",
        default=None,
        help="YYYY-MM-DD. Defaults to today minus --days.",
    )

    args = parser.parse_args()

    random.seed(args.seed)

    if args.start_date:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    else:
        start_date = datetime.now() - timedelta(days=args.days)

    rows = generate_rows(start_date=start_date, days=args.days)
    write_csv(rows, Path(args.output))

    print(f"Wrote {len(rows)} synthetic readings to {args.output}")


if __name__ == "__main__":
    main()
