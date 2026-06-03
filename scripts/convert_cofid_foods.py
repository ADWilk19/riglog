"""Convert a CoFID-style food CSV into RigLog-compatible food CSV output.

This script does not write to the RigLog database. It creates reviewable CSV
files that can then be imported through the Nutrition tab.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.services.nutrition.converter import (
    convert_cofid_csv_to_normalised_csv,
    convert_normalised_foods_csv_to_riglog_csv,
)


def convert_cofid_foods(
    input_path: str | Path,
    normalised_output_path: str | Path,
    riglog_output_path: str | Path,
    source_name: str = "cofid",
    food_group: str | None = None,
) -> dict[str, int]:
    """
    Convert a CoFID-style CSV into normalised and RigLog-compatible CSV files.

    Args:
        input_path: Source CoFID-style CSV export.
        normalised_output_path: Destination normalised CSV path.
        riglog_output_path: Destination RigLog-compatible food CSV path.
        source_name: Source label written into the RigLog CSV.
        food_group: Optional CoFID food group filter.

    Returns:
        Dictionary containing conversion counts.
    """
    normalised_count = convert_cofid_csv_to_normalised_csv(
        input_path=input_path,
        output_path=normalised_output_path,
        food_group_filter=food_group,
    )

    riglog_count = convert_normalised_foods_csv_to_riglog_csv(
        input_path=normalised_output_path,
        output_path=riglog_output_path,
        source_name=source_name,
    )

    return {
        "normalised_rows": normalised_count,
        "riglog_rows": riglog_count,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Convert a CoFID-style CSV export into RigLog-compatible food CSV."
        )
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to the CoFID-style input CSV.",
    )
    parser.add_argument(
        "--normalised-output",
        required=True,
        help="Path to write the intermediate normalised CSV.",
    )
    parser.add_argument(
        "--riglog-output",
        required=True,
        help="Path to write the final RigLog-compatible foods CSV.",
    )
    parser.add_argument(
        "--source-name",
        default="cofid",
        help="Source label written into the RigLog CSV. Default: cofid.",
    )
    parser.add_argument(
        "--food-group",
        default=None,
        help="Optional food group filter, e.g. Vegetables.",
    )

    return parser


def main() -> None:
    """Run the CoFID conversion script."""
    parser = build_parser()
    args = parser.parse_args()

    counts = convert_cofid_foods(
        input_path=args.input,
        normalised_output_path=args.normalised_output,
        riglog_output_path=args.riglog_output,
        source_name=args.source_name,
        food_group=args.food_group,
    )

    print("CoFID conversion complete")
    print(f"Normalised rows written: {counts['normalised_rows']}")
    print(f"RigLog rows written: {counts['riglog_rows']}")
    print(f"Normalised output: {args.normalised_output}")
    print(f"RigLog output: {args.riglog_output}")


if __name__ == "__main__":
    main()
