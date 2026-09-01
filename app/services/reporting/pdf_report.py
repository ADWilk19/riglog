"""PDF report generation for RigLog."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable

from matplotlib.figure import Figure
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.report_sections import normalise_report_section_keys
from app.core.settings import DEFAULT_STEP_TARGET
from app.services.activity.analysis import (
    aggregate_weekly_steps,
    get_activity_insight_metrics,
    get_activity_summary_cards,
    get_daily_activity,
)


@dataclass(frozen=True, slots=True)
class PdfReportResult:
    """Result returned after generating a PDF report."""

    file_path: Path
    included_sections: tuple[str, ...]
    skipped_sections: tuple[str, ...]


def generate_pdf_report(
    file_path: str | Path,
    *,
    section_keys: Iterable[str],
    enabled_module_keys: Iterable[str],
    step_target: int = DEFAULT_STEP_TARGET,
) -> PdfReportResult:
    """Generate a RigLog PDF report for the selected sections.

    Args:
        file_path: Destination PDF path.
        section_keys: Requested report section keys.
        enabled_module_keys: Currently enabled health modules.
        step_target: Configured daily step target for activity metrics.

    Returns:
        Details of the generated report and included/skipped sections.
    """
    output_path = Path(file_path)

    selected_section_keys = normalise_report_section_keys(
        section_keys,
        enabled_module_keys,
        export_kind="pdf",
    )

    if not selected_section_keys:
        raise ValueError("At least one valid PDF report section is required.")

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        title="RigLog Health Report",
        author="RigLog",
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
    )

    styles = getSampleStyleSheet()
    content = [
        Paragraph("RigLog Health Report", styles["Title"]),
        Paragraph(
            f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            styles["Italic"],
        ),
        Spacer(1, 12),
    ]

    included_sections: list[str] = []
    skipped_sections: list[str] = []

    activity_rows: list[dict] | None = None

    def get_activity_rows_once() -> list[dict]:
        nonlocal activity_rows

        if activity_rows is None:
            activity_rows = get_daily_activity()

        return activity_rows

    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        for section_key in selected_section_keys:
            if section_key == "activity.summary_metrics":
                _append_activity_summary_section(
                    content,
                    styles,
                    get_activity_rows_once(),
                    step_target=step_target,
                )
                included_sections.append(section_key)

            elif section_key == "activity.daily_steps_chart":
                image_path = temp_path / "activity_daily_steps.png"
                _save_daily_steps_chart(
                    get_activity_rows_once(),
                    image_path,
                    step_target=step_target,
                )
                _append_chart_section(
                    content,
                    styles,
                    title="Daily Steps",
                    image_path=image_path,
                )
                included_sections.append(section_key)

            elif section_key == "activity.weekly_steps_chart":
                image_path = temp_path / "activity_weekly_steps.png"
                _save_weekly_steps_chart(
                    get_activity_rows_once(),
                    image_path,
                    step_target=step_target,
                )
                _append_chart_section(
                    content,
                    styles,
                    title="Weekly Steps",
                    image_path=image_path,
                )
                included_sections.append(section_key)

            elif section_key == "activity.daily_activity_table":
                _append_activity_table_section(
                    content,
                    styles,
                    get_activity_rows_once(),
                )
                included_sections.append(section_key)

            else:
                skipped_sections.append(section_key)

        doc.build(content)

    return PdfReportResult(
        file_path=output_path,
        included_sections=tuple(included_sections),
        skipped_sections=tuple(skipped_sections),
    )


def _append_activity_summary_section(
    content: list,
    styles,
    rows: list[dict],
    *,
    step_target: int,
) -> None:
    """Append Activity summary and insight metrics to the report."""
    content.append(Paragraph("Activity Summary", styles["Heading2"]))

    if not rows:
        content.append(Paragraph("No activity data available.", styles["Normal"]))
        content.append(Spacer(1, 12))
        return

    summary_cards = get_activity_summary_cards(
        rows,
        target_steps=step_target,
    )
    insight_metrics = get_activity_insight_metrics(
        rows,
        target_steps=step_target,
    )

    table_rows = [["Metric", "Value", "Detail"]]

    for card in summary_cards:
        table_rows.append(
            [
                card.get("title", ""),
                card.get("value", ""),
                card.get("subtitle", "") or "",
            ]
        )

    table_rows.extend(
        [
            [
                "Best Week",
                f"{insight_metrics['best_week_steps']:,}",
                insight_metrics["best_week_start"] or "",
            ],
            [
                "Worst Week",
                f"{insight_metrics['worst_week_steps']:,}",
                insight_metrics["worst_week_start"] or "",
            ],
            [
                "Consistency",
                insight_metrics["consistency_label"],
                (
                    f"CV {insight_metrics['step_cv_pct']:.1f}%"
                    if insight_metrics["step_cv_pct"] is not None
                    else ""
                ),
            ],
        ]
    )

    content.append(_build_table(table_rows, column_widths=[5.5 * cm, 4 * cm, 6 * cm]))
    content.append(Spacer(1, 14))


def _append_activity_table_section(
    content: list,
    styles,
    rows: list[dict],
) -> None:
    """Append daily activity rows to the report."""
    content.append(Paragraph("Daily Activity", styles["Heading2"]))

    if not rows:
        content.append(Paragraph("No activity data available.", styles["Normal"]))
        content.append(Spacer(1, 12))
        return

    table_rows = [["Date", "Steps", "Source"]]

    for row in rows:
        table_rows.append(
            [
                row["activity_date"].strftime("%Y-%m-%d"),
                f"{row['steps']:,}",
                row.get("source", ""),
            ]
        )

    content.append(_build_table(table_rows, column_widths=[5 * cm, 4 * cm, 5 * cm]))
    content.append(Spacer(1, 14))


def _append_chart_section(
    content: list,
    styles,
    *,
    title: str,
    image_path: Path,
) -> None:
    """Append a chart image section to the report."""
    content.append(Paragraph(title, styles["Heading2"]))
    content.append(Image(str(image_path), width=16 * cm, height=8.5 * cm))
    content.append(Spacer(1, 14))


def _save_daily_steps_chart(
    rows: list[dict],
    image_path: Path,
    *,
    step_target: int,
) -> None:
    """Render the daily steps chart to a PNG file."""
    fig = Figure(figsize=(8, 4.2))
    ax = fig.add_subplot(111)

    ax.set_title("Daily Steps")
    ax.set_ylabel("Steps")
    ax.grid(True, alpha=0.3)

    if not rows:
        ax.text(
            0.5,
            0.5,
            "No activity data available",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_axis_off()
    else:
        dates = [row["activity_date"] for row in rows]
        steps = [row["steps"] for row in rows]

        ax.plot(dates, steps, marker="o", label="Daily steps")
        ax.axhline(
            step_target,
            linestyle="--",
            linewidth=1.2,
            label=f"{step_target:,} target",
        )
        ax.legend()

    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(image_path, dpi=150)


def _save_weekly_steps_chart(
    rows: list[dict],
    image_path: Path,
    *,
    step_target: int,
) -> None:
    """Render the weekly steps chart to a PNG file."""
    fig = Figure(figsize=(8, 4.2))
    ax = fig.add_subplot(111)

    ax.set_title("Weekly Steps")
    ax.set_ylabel("Total steps")
    ax.grid(True, alpha=0.3)

    weekly_rows = aggregate_weekly_steps(rows)

    if not weekly_rows:
        ax.text(
            0.5,
            0.5,
            "No activity data available",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_axis_off()
    else:
        week_starts = [row["week_start"] for row in weekly_rows]
        steps = [row["steps"] for row in weekly_rows]

        ax.bar(week_starts, steps, width=5, label="Weekly total")
        ax.axhline(
            step_target * 7,
            linestyle="--",
            linewidth=1.2,
            label=f"{step_target:,}/day equivalent",
        )
        ax.legend()

    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(image_path, dpi=150)


def _build_table(
    rows: list[list[str]],
    *,
    column_widths: list[float],
) -> Table:
    """Create a consistently styled ReportLab table."""
    table = Table(
        rows,
        colWidths=column_widths,
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2F2F2F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    return table
