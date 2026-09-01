"""Report-section registry for configurable RigLog exports."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from app.core.modules import normalise_enabled_module_keys


ExportKind = Literal["pdf", "csv"]


@dataclass(frozen=True, slots=True)
class ReportSection:
    """Metadata describing a reportable RigLog section."""

    key: str
    module_key: str
    label: str
    description: str
    supports_pdf: bool = True
    supports_csv: bool = False
    default_pdf: bool = True

    def supports_export(self, export_kind: ExportKind) -> bool:
        """Return whether the section supports the requested export kind."""
        if export_kind == "pdf":
            return self.supports_pdf

        if export_kind == "csv":
            return self.supports_csv

        return False


REPORT_SECTION_REGISTRY: tuple[ReportSection, ...] = (
    ReportSection(
        key="glucose.summary_metrics",
        module_key="glucose",
        label="Glucose summary metrics",
        description="Reading count, average, high, low, variability, and time-in-range metrics.",
    ),
    ReportSection(
        key="glucose.agp_chart",
        module_key="glucose",
        label="Ambulatory Glucose Profile",
        description="AGP percentile bands by time of day.",
    ),
    ReportSection(
        key="glucose.daily_average_chart",
        module_key="glucose",
        label="Daily average glucose chart",
        description="Daily average glucose trend with rolling average.",
    ),
    ReportSection(
        key="glucose.time_of_day_profile",
        module_key="glucose",
        label="Time-of-day glucose profile",
        description="Average glucose grouped by time-of-day bucket.",
    ),
    ReportSection(
        key="activity.summary_metrics",
        module_key="activity",
        label="Activity summary metrics",
        description="Goal adherence, average steps, best day, and streak metrics.",
        supports_csv=True,
    ),
    ReportSection(
        key="activity.daily_steps_chart",
        module_key="activity",
        label="Daily steps chart",
        description="Daily step trend with rolling average and target line.",
    ),
    ReportSection(
        key="activity.weekly_steps_chart",
        module_key="activity",
        label="Weekly steps chart",
        description="Weekly step totals with target-equivalent reference line.",
    ),
    ReportSection(
        key="activity.daily_activity_table",
        module_key="activity",
        label="Daily activity table",
        description="Date-level activity records for review or export.",
        supports_csv=True,
    ),
    ReportSection(
        key="workouts.summary_metrics",
        module_key="workouts",
        label="Workout summary metrics",
        description="Total sessions, weekly sessions, volume, and recent workout metrics.",
        supports_csv=True,
    ),
    ReportSection(
        key="workouts.volume_by_exercise_chart",
        module_key="workouts",
        label="Volume by exercise chart",
        description="Training volume ranked by exercise.",
    ),
    ReportSection(
        key="workouts.recent_sessions_table",
        module_key="workouts",
        label="Recent workout sessions table",
        description="Recent workout history and session-level details.",
        supports_csv=True,
    ),
    ReportSection(
        key="nutrition.summary_metrics",
        module_key="nutrition",
        label="Nutrition summary metrics",
        description="Logged meals, calories, carbohydrates, protein, fat, and average daily carbs.",
        supports_csv=True,
    ),
    ReportSection(
        key="nutrition.recent_meals_table",
        module_key="nutrition",
        label="Recent meals table",
        description="Recent logged meals with calories and macros.",
        supports_csv=True,
    ),
    ReportSection(
        key="nutrition.meal_template_totals_table",
        module_key="nutrition",
        label="Meal template totals table",
        description="Reusable meal templates with calories and macro totals.",
        supports_csv=True,
    ),
    ReportSection(
        key="nutrition.meal_glucose_response_table",
        module_key="nutrition",
        label="Meal glucose response table",
        description="Post-meal glucose response summaries by logged meal or template.",
        supports_csv=True,
    ),
)


REPORT_SECTIONS_BY_KEY: dict[str, ReportSection] = {
    section.key: section
    for section in REPORT_SECTION_REGISTRY
}


def get_report_sections_for_modules(
    enabled_module_keys: Iterable[str],
    *,
    export_kind: ExportKind = "pdf",
) -> tuple[ReportSection, ...]:
    """Return exportable report sections for enabled modules in registry order."""
    enabled_keys = set(
        normalise_enabled_module_keys(
            enabled_module_keys,
            require_one=False,
        )
    )

    return tuple(
        section
        for section in REPORT_SECTION_REGISTRY
        if section.module_key in enabled_keys
        and section.supports_export(export_kind)
    )


def get_default_report_section_keys(
    enabled_module_keys: Iterable[str],
    *,
    export_kind: ExportKind = "pdf",
) -> tuple[str, ...]:
    """Return default selected section keys for enabled modules."""
    return tuple(
        section.key
        for section in get_report_sections_for_modules(
            enabled_module_keys,
            export_kind=export_kind,
        )
        if export_kind != "pdf" or section.default_pdf
    )


def normalise_report_section_keys(
    section_keys: Iterable[str],
    enabled_module_keys: Iterable[str],
    *,
    export_kind: ExportKind = "pdf",
) -> tuple[str, ...]:
    """Return valid selected section keys in registry order."""
    selected_keys = {
        section_key.strip()
        for section_key in section_keys
        if isinstance(section_key, str) and section_key.strip()
    }

    return tuple(
        section.key
        for section in get_report_sections_for_modules(
            enabled_module_keys,
            export_kind=export_kind,
        )
        if section.key in selected_keys
    )
