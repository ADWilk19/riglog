from __future__ import annotations

from datetime import date

import pytest

from app.services.reporting.pdf_report import generate_pdf_report


ACTIVITY_ROWS = [
    {
        "activity_date": date(2026, 8, 24),
        "steps": 8_000,
        "source": "fitbit",
    },
    {
        "activity_date": date(2026, 8, 25),
        "steps": 10_500,
        "source": "fitbit",
    },
    {
        "activity_date": date(2026, 8, 26),
        "steps": 12_000,
        "source": "fitbit",
    },
    {
        "activity_date": date(2026, 8, 27),
        "steps": 9_500,
        "source": "fitbit",
    },
    {
        "activity_date": date(2026, 8, 28),
        "steps": 11_000,
        "source": "fitbit",
    },
    {
        "activity_date": date(2026, 8, 29),
        "steps": 7_500,
        "source": "fitbit",
    },
    {
        "activity_date": date(2026, 8, 30),
        "steps": 13_250,
        "source": "fitbit",
    },
]


def test_generate_pdf_report_creates_activity_pdf(tmp_path, mocker):
    mocker.patch(
        "app.services.reporting.pdf_report.get_daily_activity",
        return_value=ACTIVITY_ROWS,
    )

    output_path = tmp_path / "riglog_report.pdf"

    result = generate_pdf_report(
        output_path,
        section_keys=(
            "activity.summary_metrics",
            "activity.daily_steps_chart",
            "activity.weekly_steps_chart",
            "activity.daily_activity_table",
        ),
        enabled_module_keys=("activity",),
        step_target=8_500,
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert result.file_path == output_path
    assert result.included_sections == (
        "activity.summary_metrics",
        "activity.daily_steps_chart",
        "activity.weekly_steps_chart",
        "activity.daily_activity_table",
    )
    assert result.skipped_sections == ()


def test_generate_pdf_report_ignores_disabled_module_sections(tmp_path, mocker):
    mocker.patch(
        "app.services.reporting.pdf_report.get_daily_activity",
        return_value=ACTIVITY_ROWS,
    )

    output_path = tmp_path / "riglog_report.pdf"

    result = generate_pdf_report(
        output_path,
        section_keys=(
            "glucose.summary_metrics",
            "activity.summary_metrics",
        ),
        enabled_module_keys=("activity",),
        step_target=8_500,
    )

    assert output_path.exists()
    assert result.included_sections == ("activity.summary_metrics",)
    assert result.skipped_sections == ()


def test_generate_pdf_report_records_unimplemented_enabled_sections(
    tmp_path,
    mocker,
):
    mocker.patch(
        "app.services.reporting.pdf_report.get_daily_activity",
        return_value=ACTIVITY_ROWS,
    )

    output_path = tmp_path / "riglog_report.pdf"

    result = generate_pdf_report(
        output_path,
        section_keys=(
            "activity.summary_metrics",
            "glucose.summary_metrics",
        ),
        enabled_module_keys=("activity", "glucose"),
        step_target=8_500,
    )

    assert output_path.exists()
    assert result.included_sections == ("activity.summary_metrics",)
    assert result.skipped_sections == ("glucose.summary_metrics",)


def test_generate_pdf_report_raises_for_no_valid_sections(tmp_path):
    output_path = tmp_path / "riglog_report.pdf"

    with pytest.raises(ValueError, match="At least one valid PDF report section"):
        generate_pdf_report(
            output_path,
            section_keys=("unknown.section",),
            enabled_module_keys=("activity",),
        )


def test_generate_pdf_report_handles_empty_activity_data(tmp_path, mocker):
    mocker.patch(
        "app.services.reporting.pdf_report.get_daily_activity",
        return_value=[],
    )

    output_path = tmp_path / "riglog_report.pdf"

    result = generate_pdf_report(
        output_path,
        section_keys=(
            "activity.summary_metrics",
            "activity.daily_steps_chart",
            "activity.weekly_steps_chart",
            "activity.daily_activity_table",
        ),
        enabled_module_keys=("activity",),
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert result.included_sections == (
        "activity.summary_metrics",
        "activity.daily_steps_chart",
        "activity.weekly_steps_chart",
        "activity.daily_activity_table",
    )
