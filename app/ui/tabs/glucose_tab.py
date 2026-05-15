from pathlib import Path
from datetime import datetime, timedelta
from statistics import mean
import tempfile

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.cross_module.analysis import (
    get_available_intraday_activity_dates,
    get_daily_activity_glucose_overlay,
    get_intraday_activity_glucose_alignment
)

from app.services.environment.analysis import get_temperature_glucose_bucket_summary

from app.services.glucose.analysis import (
    calculate_agp,
    calculate_glucose_variability_metrics,
    calculate_insulin_effectiveness,
    calculate_time_based_effectiveness,
    calculate_time_in_range_breakdown,
    get_all_glucose_readings_with_meal_event,
    get_daily_average_glucose,
    get_glucose_summary_cards,
    get_meal_event_boxplot_data,
    get_time_in_range_metrics,
    get_time_of_day_profile,
    update_glucose_field,
    update_glucose_note,
)

from app.services.glucose.importer import import_diabetes_m_csv

from app.ui.widgets.summary_card import SummaryCard

CHART_BG = "#1E1E1E"
CHART_TEXT = "#F0F0F0"
CHART_GRID = "#444444"
CHART_SPINE = "#888888"
HYPO_RED = "#7F1D1D"
LOW_AMBER = "#FFAA00"
TARGET_GREEN = "#1F7A34"
HIGH_YELLOW = "#FFAA00"
HYPER_DANGER = "#7F1D1D"
LINE_RED = "#FF4D4D"
WHITE = "#FFFFFF"
ACTIVITY_TEAL = "#4DB6AC"

TIME_FILTER_DAYS = {
    "Last 7 Days": 7,
    "Last 14 Days": 14,
    "Last 30 Days": 30,
    "Last 90 Days": 90,
}

def apply_chart_theme(fig: Figure, ax) -> None:
    """Apply the shared dark chart theme."""
    fig.patch.set_facecolor(CHART_BG)
    ax.set_facecolor(CHART_BG)
    ax.tick_params(axis="x", colors=CHART_TEXT)
    ax.tick_params(axis="y", colors=CHART_TEXT)

    for spine in ax.spines.values():
        spine.set_color(CHART_SPINE)

    ax.grid(True, color=CHART_GRID, alpha=0.5)


class NumericTableWidgetItem(QTableWidgetItem):
    """Table item that preserves numeric ordering for glucose values."""

    def __init__(self, value: float) -> None:
        super().__init__(f"{value:.1f}")
        self.numeric_value = value

    def __lt__(self, other: object) -> bool:
        if isinstance(other, NumericTableWidgetItem):
            return self.numeric_value < other.numeric_value
        return super().__lt__(other)


def rolling_average(values: list[float], window: int = 7) -> list[float]:
    """Return a simple trailing rolling average for a list of values."""
    result = []

    for i in range(len(values)):
        start = max(0, i - window + 1)
        window_values = values[start : i + 1]
        result.append(mean(window_values))

    return result


def draw_agp_figure(fig: Figure, agp_df: pd.DataFrame) -> None:
    """Draw the AGP chart onto an existing matplotlib figure."""
    fig.clear()
    ax = fig.add_subplot(111)

    apply_chart_theme(fig, ax)

    ax.set_title("Ambulatory Glucose Profile (AGP)", color=CHART_TEXT)
    ax.set_xlabel("Time of day", color=CHART_TEXT)
    ax.set_ylabel("Glucose (mmol/L)", color=CHART_TEXT)

    if agp_df.empty:
        ax.text(
            0.5,
            0.5,
            "No AGP data available",
            ha="center",
            va="center",
            color=CHART_TEXT,
        )
        ax.set_axis_off()
        fig.tight_layout()
        return

    x = agp_df["hour_decimal"].to_numpy()
    p10 = agp_df["p10"].to_numpy()
    p25 = agp_df["p25"].to_numpy()
    p50 = agp_df["p50"].to_numpy()
    p75 = agp_df["p75"].to_numpy()
    p90 = agp_df["p90"].to_numpy()

    ax.axhspan(4.0, 10.0, color=TARGET_GREEN, alpha=0.18)
    ax.axhline(3.3, color="#FF6666", linestyle="--", linewidth=1)
    ax.axhline(4, color="#66BB6A", linestyle=":", linewidth=1)
    ax.axhline(10, color="#66BB6A", linestyle=":", linewidth=1)
    ax.axhline(15, color=HYPER_DANGER, linestyle="--", linewidth=1)

    ax.fill_between(x, p10, p90, color=LINE_RED, alpha=0.15, label="10–90%")
    ax.fill_between(x, p25, p75, color=LINE_RED, alpha=0.30, label="25–75%")
    ax.plot(x, p50, color=WHITE, linewidth=2.2, label="Median")

    ax.set_xlim(0, 24)
    ax.set_ylim(0, 30)
    ax.set_yticks(range(0, 31, 5))
    ax.set_xticks([0, 4, 8, 12, 16, 20, 24])
    ax.set_xticklabels(
        ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "24:00"]
    )

    legend = ax.legend(facecolor=CHART_BG, edgecolor=CHART_SPINE)
    for text in legend.get_texts():
        text.set_color(CHART_TEXT)

    fig.tight_layout()


class GlucoseTrendChart(FigureCanvasQTAgg):
    """Matplotlib canvas for the daily average glucose chart."""

    def __init__(self) -> None:
        self.figure = Figure(figsize=(6, 4.5))
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)

    def plot_daily_average(self, daily_data: list[dict]) -> None:
        """Plot daily average glucose values and a 7-day rolling trend."""
        self.ax.clear()
        apply_chart_theme(self.figure, self.ax)

        self.ax.set_title("Daily Average Glucose", color=CHART_TEXT)
        self.ax.set_ylabel("mmol/L", color=CHART_TEXT)

        self.ax.axhspan(0, 3.3, color="#D32F2F", alpha=0.12)
        self.ax.axhspan(4, 10, color=TARGET_GREEN, alpha=0.35)
        self.ax.axhspan(15, 25, color="#8E24AA", alpha=0.12)

        self.ax.axhline(3.3, color="#FF6666", linestyle="--", linewidth=1)
        self.ax.axhline(4, color="#66BB6A", linestyle=":", linewidth=1)
        self.ax.axhline(10, color="#66BB6A", linestyle=":", linewidth=1)
        self.ax.axhline(15, color=HYPER_DANGER, linestyle="--", linewidth=1)

        self.ax.set_ylim(0, 30)
        self.ax.set_yticks(range(0, 31, 5))

        if not daily_data:
            self.draw()
            return

        dates = [row["date"] for row in daily_data]
        averages = [row["avg"] for row in daily_data]
        rolling_avg = rolling_average(averages, window=7)

        if len(dates) == 1:
            self.ax.set_xlim(
                dates[0] - timedelta(days=1),
                dates[0] + timedelta(days=1),
            )
        else:
            self.ax.set_xlim(min(dates), max(dates))
            self.ax.margins(x=0.02)

        self.ax.plot(
            dates,
            averages,
            color=LINE_RED,
            marker="o",
            markersize=5,
            linewidth=1.8,
            alpha=0.9,
            label="Daily Average",
        )

        self.ax.plot(
            dates,
            rolling_avg,
            color=WHITE,
            linewidth=2.5,
            alpha=0.9,
            label="7-Day Trend",
        )

        self.ax.legend(
            facecolor=CHART_BG,
            edgecolor=CHART_SPINE,
            labelcolor=CHART_TEXT,
        )
        self.figure.autofmt_xdate()
        self.figure.subplots_adjust(bottom=0.20)
        self.draw()


class DailyActivityGlucoseOverlayChart(FigureCanvasQTAgg):
    """Stacked daily chart comparing average glucose with daily steps."""

    def __init__(self) -> None:
        self.figure = Figure(figsize=(6, 5.2))
        self.glucose_ax = self.figure.add_subplot(211)
        self.steps_ax = self.figure.add_subplot(212, sharex=self.glucose_ax)
        super().__init__(self.figure)

    def plot_overlay(self, overlay_rows: list[dict]) -> None:
        """Plot daily average glucose above daily steps using a shared date axis."""
        self.figure.clear()

        self.glucose_ax = self.figure.add_subplot(211)
        self.steps_ax = self.figure.add_subplot(212, sharex=self.glucose_ax)

        apply_chart_theme(self.figure, self.glucose_ax)
        apply_chart_theme(self.figure, self.steps_ax)

        self.glucose_ax.set_title(
            "Daily Glucose vs Steps",
            color=CHART_TEXT,
        )
        self.glucose_ax.set_ylabel("Glucose (mmol/L)", color=CHART_TEXT)
        self.steps_ax.set_ylabel("Steps", color=CHART_TEXT)

        self.glucose_ax.axhspan(4.0, 10.0, color=TARGET_GREEN, alpha=0.25)
        self.glucose_ax.axhline(4.0, color="#66BB6A", linestyle=":", linewidth=1)
        self.glucose_ax.axhline(10.0, color="#66BB6A", linestyle=":", linewidth=1)
        self.glucose_ax.axhline(3.3, color="#FF6666", linestyle="--", linewidth=1)
        self.glucose_ax.axhline(15.0, color=HYPER_DANGER, linestyle="--", linewidth=1)

        if not overlay_rows:
            self.glucose_ax.text(
                0.5,
                0.5,
                "No daily glucose/activity data available",
                ha="center",
                va="center",
                color=CHART_TEXT,
                transform=self.glucose_ax.transAxes,
            )
            self.steps_ax.set_axis_off()
            self.figure.tight_layout()
            self.draw()
            return

        rows_with_glucose = [
            row
            for row in overlay_rows
            if row.get("avg_glucose") is not None
        ]

        dates = [row["date"] for row in overlay_rows]
        steps = [row["steps"] for row in overlay_rows]

        if rows_with_glucose:
            glucose_dates = [row["date"] for row in rows_with_glucose]
            avg_glucose = [row["avg_glucose"] for row in rows_with_glucose]

            self.glucose_ax.plot(
                glucose_dates,
                avg_glucose,
                marker="o",
                markersize=4,
                linewidth=1.8,
                color=LINE_RED,
                label="Daily avg glucose",
            )
            self.glucose_ax.legend(
                facecolor=CHART_BG,
                edgecolor=CHART_SPINE,
                labelcolor=CHART_TEXT,
            )
        else:
            self.glucose_ax.text(
                0.5,
                0.5,
                "No glucose readings for activity dates",
                ha="center",
                va="center",
                color=CHART_TEXT,
                transform=self.glucose_ax.transAxes,
            )

        self.steps_ax.bar(
            dates,
            steps,
            color=ACTIVITY_TEAL,
            alpha=0.60,
            label="Steps",
        )
        self.steps_ax.legend(
            facecolor=CHART_BG,
            edgecolor=CHART_SPINE,
            labelcolor=CHART_TEXT,
        )

        self.steps_ax.set_xlabel("Date", color=CHART_TEXT, labelpad=2)

        if len(dates) == 1:
            self.glucose_ax.set_xlim(
                dates[0] - timedelta(days=1),
                dates[0] + timedelta(days=1),
            )
        else:
            self.glucose_ax.set_xlim(min(dates), max(dates))

        self.figure.autofmt_xdate()
        self.figure.subplots_adjust(hspace=0.30, bottom=0.22)
        self.draw()


class GlucoseProfileChart(FigureCanvasQTAgg):
    """Matplotlib canvas for the time-of-day glucose profile chart."""

    def __init__(self) -> None:
        self.figure = Figure(figsize=(6, 4.5))
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)

    def plot_profile(self, profile_data: list[dict]) -> None:
        """Plot average glucose by time-of-day bucket."""
        self.ax.clear()
        apply_chart_theme(self.figure, self.ax)

        self.ax.set_title("Average Glucose by Time of Day", color=CHART_TEXT)
        self.ax.set_xlabel("Time of day", color=CHART_TEXT, labelpad=10)
        self.ax.set_ylabel("mmol/L", color=CHART_TEXT)

        self.ax.axhspan(0, 3.3, color="#D32F2F", alpha=0.12)
        self.ax.axhspan(4, 10, color=TARGET_GREEN, alpha=0.35)
        self.ax.axhspan(15, 30, color="#8E24AA", alpha=0.12)

        self.ax.axhline(3.3, color="#FF6666", linestyle="--", linewidth=1)
        self.ax.axhline(4, color="#66BB6A", linestyle=":", linewidth=1)
        self.ax.axhline(10, color="#66BB6A", linestyle=":", linewidth=1)
        self.ax.axhline(15, color=HYPER_DANGER, linestyle="--", linewidth=1)

        if not profile_data:
            self.draw()
            return

        x = [row["bucket_minutes"] / 60 for row in profile_data]
        y = [row["avg"] for row in profile_data]

        self.ax.plot(
            x,
            y,
            color=LINE_RED,
            marker="o",
            markersize=4,
            linewidth=2,
            alpha=0.9,
            label="Average by Time of Day",
        )

        tick_positions = []
        tick_labels = []

        for row in profile_data:
            minutes = row["bucket_minutes"]
            if minutes % 120 == 0:
                tick_positions.append(minutes / 60)
                tick_labels.append(row["time_label"])

        self.ax.set_xticks(tick_positions)
        self.ax.set_xticklabels(tick_labels)

        self.ax.legend(
            facecolor=CHART_BG,
            edgecolor=CHART_SPINE,
            labelcolor=CHART_TEXT,
        )

        self.figure.subplots_adjust(bottom=0.24)
        self.draw()


class IntradayActivityGlucoseAlignmentChart(FigureCanvasQTAgg):
    """Stacked intraday chart comparing glucose with step density."""

    def __init__(self) -> None:
        self.figure = Figure(figsize=(6, 5.2))
        self.glucose_ax = self.figure.add_subplot(211)
        self.steps_ax = self.figure.add_subplot(212, sharex=self.glucose_ax)
        super().__init__(self.figure)

    def plot_alignment(self, alignment_rows: list[dict]) -> None:
        """Plot glucose and steps using shared intraday time buckets."""
        self.figure.clear()

        self.glucose_ax = self.figure.add_subplot(211)
        self.steps_ax = self.figure.add_subplot(212, sharex=self.glucose_ax)

        apply_chart_theme(self.figure, self.glucose_ax)
        apply_chart_theme(self.figure, self.steps_ax)

        self.glucose_ax.set_title(
            "Intraday Glucose Readings vs Step Density",
            color=CHART_TEXT,
        )
        self.glucose_ax.set_ylabel("Glucose (mmol/L)", color=CHART_TEXT)
        self.steps_ax.set_ylabel("Steps", color=CHART_TEXT)

        self.glucose_ax.axhspan(4.0, 10.0, color=TARGET_GREEN, alpha=0.25)
        self.glucose_ax.axhline(4.0, color="#66BB6A", linestyle=":", linewidth=1)
        self.glucose_ax.axhline(10.0, color="#66BB6A", linestyle=":", linewidth=1)
        self.glucose_ax.axhline(3.3, color="#FF6666", linestyle="--", linewidth=1)
        self.glucose_ax.axhline(15.0, color=HYPER_DANGER, linestyle="--", linewidth=1)

        if not alignment_rows:
            self.glucose_ax.text(
                0.5,
                0.5,
                "No intraday glucose/activity data available",
                ha="center",
                va="center",
                color=CHART_TEXT,
                transform=self.glucose_ax.transAxes,
            )
            self.steps_ax.set_axis_off()
            self.figure.tight_layout()
            self.draw()
            return

        rows_with_glucose = [
            row for row in alignment_rows
            if row.get("avg_glucose") is not None
        ]

        bucket_starts = [row["bucket_start"] for row in alignment_rows]
        steps = [row["steps"] for row in alignment_rows]

        if rows_with_glucose:
            glucose_bucket_starts = [
                row["bucket_start"] for row in rows_with_glucose
            ]
            avg_glucose = [
                row["avg_glucose"] for row in rows_with_glucose
            ]

            self.glucose_ax.scatter(
                glucose_bucket_starts,
                avg_glucose,
                s=36,
                color=LINE_RED,
                label="Avg glucose",
                zorder=3,
            )
        else:
            self.glucose_ax.text(
                0.5,
                0.5,
                "No glucose readings in matched activity buckets",
                ha="center",
                va="center",
                color=CHART_TEXT,
                transform=self.glucose_ax.transAxes,
            )

        self.steps_ax.bar(
            bucket_starts,
            steps,
            width=0.018,
            color=ACTIVITY_TEAL,
            alpha=0.60,
            label="Steps",
        )
        self.steps_ax.legend(
            facecolor=CHART_BG,
            edgecolor=CHART_SPINE,
            labelcolor=CHART_TEXT,
        )
        self.steps_ax.set_xlabel("Time bucket", color=CHART_TEXT, labelpad=2)

        if len(bucket_starts) == 1:
            self.glucose_ax.set_xlim(
                bucket_starts[0] - timedelta(hours=1),
                bucket_starts[0] + timedelta(hours=1),
            )
        else:
            self.glucose_ax.set_xlim(min(bucket_starts), max(bucket_starts))

        self.figure.autofmt_xdate()
        self.figure.subplots_adjust(hspace=0.30, bottom=0.22)
        self.draw()


class MealEventBoxPlotChart(FigureCanvasQTAgg):
    """Matplotlib canvas for glucose distribution by meal event."""

    def __init__(self) -> None:
        self.figure = Figure(figsize=(6, 4.5))
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)

    def plot_boxplot(self, boxplot_data: list[dict]) -> None:
        """Plot glucose distributions for each meal event as a boxplot."""
        self.ax.clear()
        apply_chart_theme(self.figure, self.ax)

        self.ax.set_title("Glucose Distribution by Meal Event", color=CHART_TEXT)
        self.ax.set_xlabel("Meal Event", color=CHART_TEXT, labelpad=10)
        self.ax.set_ylabel("mmol/L", color=CHART_TEXT)

        self.ax.tick_params(axis="x", colors=CHART_TEXT, labelsize=9)

        self.ax.axhspan(0, 3.3, color="#D32F2F", alpha=0.12)
        self.ax.axhspan(4, 10, color=TARGET_GREEN, alpha=0.35)
        self.ax.axhspan(15, 30, color="#8E24AA", alpha=0.12)

        if not boxplot_data:
            self.draw()
            return

        labels = []
        series = []

        for row in boxplot_data:
            values = row.get("values", [])
            if not values:
                continue

            label = (
                row.get("meal_event_label")
                or row.get("meal_event")
                or row.get("label")
                or ""
            )

            labels.append(label)
            series.append(values)

        if not series:
            self.draw()
            return

        bp = self.ax.boxplot(series, patch_artist=True, labels=labels)

        self.ax.set_xticks(range(1, len(labels) + 1))
        self.ax.set_xticklabels(
            labels,
            rotation=20,
            ha="right",
            color=CHART_TEXT,
        )
        self.ax.tick_params(axis="x", colors=CHART_TEXT, labelsize=9)

        for box in bp["boxes"]:
            box.set(facecolor="#303030", edgecolor=WHITE)

        for whisker in bp["whiskers"]:
            whisker.set(color=WHITE)

        for cap in bp["caps"]:
            cap.set(color=WHITE)

        for median in bp["medians"]:
            median.set(color=LINE_RED, linewidth=2)

        self.figure.subplots_adjust(bottom=0.24)
        self.draw()


class RangeBreakdownChart(FigureCanvasQTAgg):
    """Matplotlib canvas for selected glucose range breakdown by meal event."""
    meal_event_clicked = Signal(str)

    def __init__(self) -> None:
        self.figure = Figure(figsize=(6, 2.4))
        self.ax = self.figure.add_subplot(111)
        self.bars = []
        self.bar_labels = []
        self.mpl_connect("button_press_event", self._on_click)
        super().__init__(self.figure)

    def plot_breakdown(
        self,
        breakdown_items: list[tuple[str, int]],
        selected_range: str | None,
        ) -> None:
        self.ax.clear()
        apply_chart_theme(self.figure, self.ax)
        self.ax.grid(False)

        for spine in self.ax.spines.values():
            spine.set_visible(False)

        self.ax.tick_params(axis="x", length=0)
        self.ax.tick_params(axis="y", length=0)
        self.ax.xaxis.set_visible(False)

        if not breakdown_items:
            self.ax.text(
                0.5,
                0.5,
                "Select a range card to see meal-event breakdown",
                ha="center",
                va="center",
                color=CHART_TEXT,
            )
            self.ax.set_axis_off()
            self.draw()
            return

        labels = [label for label, _ in breakdown_items]
        counts = [count for _, count in breakdown_items]

        color = self._get_range_color(selected_range)
        bars = self.ax.barh(labels, counts, color=color)
        self.bars = list(bars)
        self.bar_labels = labels

        self.ax.invert_yaxis()
        self.ax.xaxis.set_visible(False)
        self.ax.set_title("Selected Range by Meal Event", color=CHART_TEXT)

        max_count = max(counts)
        self.ax.set_xlim(0, max_count + 1)

        for bar, count in zip(bars, counts):
            self.ax.text(
                count + (max_count * 0.01),
                bar.get_y() + bar.get_height() / 2,
                f"{count}",
                va="center",
                color=CHART_TEXT,
                fontsize=9,
            )

        self.figure.tight_layout()
        self.draw()

    def _get_range_color(self, selected_range: str | None) -> str:
        if selected_range == "hypo":
            return HYPO_RED
        if selected_range == "low":
            return LOW_AMBER
        if selected_range == "target":
            return TARGET_GREEN
        if selected_range == "high":
            return HIGH_YELLOW
        if selected_range == "hyper":
            return HYPO_RED
        return LINE_RED

    def _on_click(self, event) -> None:
        if event.inaxes != self.ax:
            return

        for index, bar in enumerate(self.bars):
            contains, _ = bar.contains(event)

            if contains:
                self.meal_event_clicked.emit(self.bar_labels[index])
                return


class GlucoseTab(QWidget):
    """Main glucose analytics tab for import, review, analysis, and export."""
    MEAL_EVENT_ORDER = [
        "Pre-Breakfast",
        "Post-Breakfast",
        "Pre-Lunch",
        "Post-Lunch",
        "Pre-Dinner",
        "Post-Dinner",
        "Before Bed",
        "Night",
    ]

    def __init__(self) -> None:
        super().__init__()

        self.selected_reading_id: int | None = None
        self.selected_range_filter: str | None = None

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setObjectName("glucoseScrollArea")
        scroll.setWidgetResizable(True)

        container = QWidget()
        container.setObjectName("glucoseContainer")

        self.layout = QVBoxLayout(container)
        self.layout.setSpacing(20)
        self.layout.setContentsMargins(16, 16, 16, 24)

        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

        self._build_toolbar()
        self._build_summary_panel()
        self._build_agp_chart()
        self._build_chart()
        self._build_daily_activity_glucose_overlay_chart()
        self._build_intraday_activity_date_selector()
        self._build_intraday_activity_glucose_alignment_chart()
        self._build_temperature_glucose_table()
        self._build_profile_chart()
        self._build_meal_boxplot_chart()
        self._build_insulin_effectiveness_table()
        self._build_dose_effectiveness_chart()
        self._build_time_effectiveness_table()
        self._build_legend()
        self._build_table()
        self._build_notes_panel()

        self.load_readings()

    def _create_section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def _create_toolbar_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    def _add_summary_cards(
        self,
        parent_layout: QVBoxLayout,
        title: str,
        cards: list[SummaryCard],
        columns: int,
    ) -> None:
        parent_layout.addWidget(self._create_section_title(title))

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        for card in cards:
            card.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            card.setMinimumWidth(0)

        for index, card in enumerate(cards):
            row = index // columns
            column = index % columns
            grid.addWidget(card, row, column)

        for column in range(columns):
            grid.setColumnStretch(column, 1)

        parent_layout.addLayout(grid)

    def _create_analysis_table(
        self,
        column_count: int,
        headers: list[str],
    ) -> QTableWidget:
        table = QTableWidget()
        table.setObjectName("analysisTable")
        table.setColumnCount(column_count)
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setAlternatingRowColors(True)
        table.setMinimumHeight(220)
        return table

    def _build_toolbar(self) -> None:
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.import_button = QPushButton("Import Diabetes:M CSV")
        self.import_button.setObjectName("primaryAction")
        self.import_button.clicked.connect(self.handle_import_csv)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("secondaryAction")
        self.refresh_button.clicked.connect(self.load_readings)

        self.clear_filters_button = QPushButton("Clear Filters")
        self.clear_filters_button.setObjectName("secondaryAction")
        self.clear_filters_button.clicked.connect(self.handle_clear_filters)

        self.export_pdf_button = QPushButton("Export PDF")
        self.export_pdf_button.setObjectName("secondaryAction")
        self.export_pdf_button.clicked.connect(self.handle_export_pdf)

        self.meal_event_filter = QComboBox()
        self.meal_event_filter.addItems(
            [
                "All",
                "Pre-Breakfast",
                "Post-Breakfast",
                "Pre-Lunch",
                "Post-Lunch",
                "Pre-Dinner",
                "Post-Dinner",
                "Before Bed",
                "Night",
            ]
        )
        self.meal_event_filter.currentIndexChanged.connect(self.load_readings)
        self.meal_event_filter.setFixedWidth(180)

        self.time_filter = QComboBox()
        self.time_filter.addItems(["All Time", *TIME_FILTER_DAYS.keys()])
        self.time_filter.currentIndexChanged.connect(self.load_readings)
        self.time_filter.setFixedWidth(140)

        self.active_filter_label = QLabel("")
        self.active_filter_label.setObjectName("statusLabel")

        toolbar.addStretch()
        toolbar.addWidget(self.import_button)
        toolbar.addWidget(self.refresh_button)
        toolbar.addWidget(self.clear_filters_button)
        toolbar.addWidget(self.export_pdf_button)
        toolbar.addSpacing(12)
        toolbar.addWidget(self._create_toolbar_label("Meal Event"))
        toolbar.addWidget(self.meal_event_filter)
        toolbar.addWidget(self._create_toolbar_label("Time Range"))
        toolbar.addWidget(self.time_filter)
        toolbar.addSpacing(12)
        toolbar.addWidget(self.active_filter_label)
        toolbar.addStretch()

        self.layout.addLayout(toolbar)

    def _build_summary_panel(self) -> None:
        summary_panel = QVBoxLayout()
        summary_panel.setSpacing(12)
        summary_panel.setContentsMargins(0, 8, 0, 8)

        self.count_label = SummaryCard(title="Readings", value="-")
        self.avg_label = SummaryCard(title="Average", value="-")
        self.min_label = SummaryCard(title="Lowest", value="-")
        self.max_label = SummaryCard(title="Highest", value="-")
        # self.tir_label = SummaryCard(title="In Range", value="-")

        self.hypo_label = SummaryCard(
            title="Hypo",
            value="-",
            on_click=lambda: self.handle_range_card_click("hypo"),
        )
        self.low_label = SummaryCard(
            title="Low",
            value="-",
            on_click=lambda: self.handle_range_card_click("low"),
        )
        self.tir_label = SummaryCard(
            title="In Range",
            value="-",
            on_click=lambda: self.handle_range_card_click("target"),
        )
        self.high_label = SummaryCard(
            title="High",
            value="-",
            on_click=lambda: self.handle_range_card_click("high"),
        )
        self.hyper_label = SummaryCard(
            title="Hyper",
            value="-",
            on_click=lambda: self.handle_range_card_click("hyper"),
        )

        self.sd_label = SummaryCard(title="SD", value="-")
        self.cv_label = SummaryCard(title="CV", value="-")
        self.gmi_label = SummaryCard(title="GMI", value="-")

        self.summary_cards = {
            "count": self.count_label,
            "average": self.avg_label,
            "minimum": self.min_label,
            "maximum": self.max_label,
            "hypo": self.hypo_label,
            "low": self.low_label,
            "target": self.tir_label,
            "high": self.high_label,
            "hyper": self.hyper_label,
            "sd": self.sd_label,
            "cv": self.cv_label,
            "gmi": self.gmi_label,
        }

        self._add_summary_cards(
            summary_panel,
            "Overview",
            [
                self.count_label,
                self.avg_label,
                self.min_label,
                self.max_label,
            ],
            columns=4,
)

        summary_panel.addWidget(self._create_section_title("Time in Range"))

        time_range_grid = QGridLayout()
        time_range_grid.setHorizontalSpacing(12)
        time_range_grid.setVerticalSpacing(12)

        time_range_cards = [
            self.hypo_label,
            self.low_label,
            self.tir_label,
            self.high_label,
            self.hyper_label,
        ]

        for card in time_range_cards:
            card.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            card.setMinimumWidth(0)

        time_range_grid.addWidget(self.hypo_label, 0, 0)
        time_range_grid.addWidget(self.low_label, 0, 1)
        time_range_grid.addWidget(self.tir_label, 0, 2, 1, 2)

        time_range_grid.addWidget(self.high_label, 1, 0)
        time_range_grid.addWidget(self.hyper_label, 1, 1)

        for column in range(4):
            time_range_grid.setColumnStretch(column, 1)

        summary_panel.addLayout(time_range_grid)

        self._add_summary_cards(
            summary_panel,
            "Variability",
            [
                self.sd_label,
                self.cv_label,
                self.gmi_label,
            ],
            columns=3,
        )

        self.range_breakdown_chart = RangeBreakdownChart()
        self.range_breakdown_chart.meal_event_clicked.connect(
            self.handle_breakdown_meal_event_click
        )
        self.range_breakdown_chart.setMinimumHeight(260)
        summary_panel.addWidget(self.range_breakdown_chart)

        self.layout.addLayout(summary_panel)
        self._update_range_card_selection_state()

    def _build_chart(self) -> None:
        self.chart = GlucoseTrendChart()
        self.chart.setMinimumHeight(320)
        self.layout.addWidget(self.chart)

    def _build_agp_chart(self) -> None:
        self.agp_figure = Figure(figsize=(8, 4))
        self.agp_canvas = FigureCanvasQTAgg(self.agp_figure)
        self.agp_canvas.setMinimumHeight(320)
        self.layout.addWidget(self.agp_canvas)

    def _build_profile_chart(self) -> None:
        self.profile_chart = GlucoseProfileChart()
        self.profile_chart.setMinimumHeight(320)
        self.layout.addWidget(self.profile_chart)

    def _build_meal_boxplot_chart(self) -> None:
        self.meal_boxplot_chart = MealEventBoxPlotChart()
        self.meal_boxplot_chart.setMinimumHeight(340)
        self.layout.addWidget(self.meal_boxplot_chart)

    def _build_daily_activity_glucose_overlay_chart(self) -> None:
        self.daily_activity_glucose_overlay_chart = DailyActivityGlucoseOverlayChart()
        self.daily_activity_glucose_overlay_chart.setMinimumHeight(420)
        self.layout.addWidget(self.daily_activity_glucose_overlay_chart)

    def _build_intraday_activity_glucose_alignment_chart(self) -> None:
        self.intraday_activity_glucose_alignment_chart = (
            IntradayActivityGlucoseAlignmentChart()
        )
        self.intraday_activity_glucose_alignment_chart.setMinimumHeight(420)
        self.layout.addWidget(self.intraday_activity_glucose_alignment_chart)

    def _build_insulin_effectiveness_table(self) -> None:
        self.layout.addWidget(
            self._create_section_title("Dose Effectiveness by Previous Meal Event")
        )

        self.insulin_effectiveness_table = self._create_analysis_table(
            7,
            [
                "Meal Event",
                "Standard Ratio (g/u)",
                "Actual Ratio (g/u)",
                "Avg Outcome Glucose",
                "Status",
                "Suggestion",
                "Count",
            ],
        )

        header = self.insulin_effectiveness_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        self.layout.addWidget(self.insulin_effectiveness_table)

    def _build_dose_effectiveness_chart(self) -> None:
        self.dose_effectiveness_chart = FigureCanvasQTAgg(Figure(figsize=(6, 4.5)))
        self.dose_effectiveness_chart.setMinimumHeight(320)
        self.layout.addWidget(self.dose_effectiveness_chart)

    def _build_time_effectiveness_table(self) -> None:
        self.layout.addWidget(
            self._create_section_title("7-Day Change by Previous Meal Event")
        )

        self.time_effectiveness_table = self._create_analysis_table(
            4,
            ["Meal Event", "Older Avg", "Recent Avg", "Change"],
        )

        header = self.time_effectiveness_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.layout.addWidget(self.time_effectiveness_table)

    def _build_legend(self) -> None:
        legend_layout = QHBoxLayout()
        legend_layout.setSpacing(10)
        legend_layout.setContentsMargins(0, 6, 0, 6)

        items = [
            ("Hypo (<3.3)", HYPO_RED, "#121212"),
            ("Low (3.3–4)", LOW_AMBER, "#121212"),
            ("Target (4–10)", TARGET_GREEN, "#F5F5F5"),
            ("High (10–15)", "#FFD250", "#121212"),
            ("Hyper (>15)", "#C88CFF", "#121212"),
        ]

        legend_layout.addStretch()

        for text, bg_color, text_color in items:
            label = QLabel(text)
            label.setObjectName("legendChip")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(
                f"background-color: {bg_color}; color: {text_color};"
            )
            legend_layout.addWidget(label)

        legend_layout.addStretch()
        self.layout.addLayout(legend_layout)

    def _build_table(self) -> None:
        self.table = QTableWidget()
        self.table.setObjectName("glucoseTable")
        self.table.setColumnCount(8)
        self.table.setMinimumHeight(350)
        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "Recorded At",
                "Glucose",
                "Meal Event",
                "Carbs (g)",
                "Humalog (u)",
                "Tresiba (u)",
                "Notes",
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(
            QTableWidget.DoubleClicked | QTableWidget.SelectedClicked
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self.handle_row_selection)
        self.table.cellChanged.connect(self.handle_cell_edit)
        self.table.setColumnHidden(0, True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.Stretch)

        self.layout.addWidget(self.table)

    def _build_notes_panel(self) -> None:
        self.notes_label = self._create_section_title("Notes for selected reading")
        self.layout.addWidget(self.notes_label)

        self.notes_editor = QTextEdit()
        self.notes_editor.setObjectName("notesEditor")
        self.notes_editor.setPlaceholderText("Add contextual notes here...")
        self.notes_editor.setMinimumHeight(120)
        self.layout.addWidget(self.notes_editor)

        self.save_note_button = QPushButton("Save Note")
        self.save_note_button.setObjectName("primaryAction")
        self.save_note_button.clicked.connect(self.handle_save_note)
        self.layout.addWidget(
            self.save_note_button,
            alignment=Qt.AlignmentFlag.AlignRight,
        )

    def _build_intraday_activity_date_selector(self) -> None:
        """Build date selector for the intraday activity/glucose chart."""
        selector_layout = QHBoxLayout()
        selector_layout.setSpacing(12)

        selector_layout.addStretch()
        selector_layout.addWidget(self._create_toolbar_label("Intraday Date"))

        self.intraday_activity_date_filter = QComboBox()
        self.intraday_activity_date_filter.setFixedWidth(140)

        available_dates = get_available_intraday_activity_dates()

        for activity_date in available_dates:
            self.intraday_activity_date_filter.addItem(
                activity_date.isoformat(),
                activity_date,
            )

        if available_dates:
            self.intraday_activity_date_filter.setCurrentIndex(
                len(available_dates) - 1
            )

        self.intraday_activity_date_filter.currentIndexChanged.connect(
            self.load_readings
        )

        selector_layout.addWidget(self.intraday_activity_date_filter)
        selector_layout.addStretch()

        self.layout.addLayout(selector_layout)

    def _build_temperature_glucose_table(self) -> None:
        """Build environmental temperature vs glucose summary table."""
        self.layout.addWidget(
            self._create_section_title("Temperature vs Glucose")
        )

        self.temperature_glucose_table = self._create_analysis_table(
            8,
            [
                "Bucket",
                "Days",
                "Readings",
                "Avg Temp",
                "Avg Glucose",
                "Target %",
                "Hypo %",
                "Hyper %",
            ],
        )

        header = self.temperature_glucose_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)

        self.layout.addWidget(self.temperature_glucose_table)

    def _get_filtered_readings(self) -> list[dict]:
        """Return readings filtered by the selected meal event and time range."""
        readings = get_all_glucose_readings_with_meal_event(days=365)

        selected_meal_event = self.meal_event_filter.currentText()
        if selected_meal_event != "All":
            readings = [
                reading
                for reading in readings
                if reading["meal_event_label"] == selected_meal_event
            ]

        selected_time_range = self.time_filter.currentText()

        if selected_time_range != "All Time" and readings:
            latest_timestamp = max(reading["recorded_at"] for reading in readings)

            days = TIME_FILTER_DAYS.get(selected_time_range)
            cutoff = latest_timestamp - timedelta(days=days) if days is not None else None

            if cutoff is not None:
                readings = [
                    reading
                    for reading in readings
                    if reading["recorded_at"] >= cutoff
                ]

        readings = self._apply_range_filter(readings)
        return readings

    def _update_summary(self, readings: list[dict]) -> None:
        """Update the summary cards using the currently filtered readings."""
        if not readings:
            for card in self.summary_cards.values():
                card.clear()

            self.count_label.set_content("0")
            return

        cards_data = get_glucose_summary_cards(readings)
        card_map = {card["key"]: card for card in cards_data}

        for key, summary_card in self.summary_cards.items():
            data = card_map.get(key)

            if data is None:
                summary_card.clear()
                continue

            summary_card.set_content(
                data.get("value", "-"),
                data.get("subtitle"),
            )
            summary_card.set_variant(data.get("variant", "neutral"))

    def load_readings(self) -> None:
        """Refresh all charts, tables, and summary cards from filtered readings."""
        readings = self._get_filtered_readings()

        agp_df = calculate_agp(pd.DataFrame(readings))
        draw_agp_figure(self.agp_figure, agp_df)
        self.agp_canvas.draw()

        self._update_summary(readings)
        self._update_range_breakdown(readings)

        daily_data = get_daily_average_glucose(readings)
        self.chart.plot_daily_average(daily_data)

        overlay_rows = get_daily_activity_glucose_overlay(glucose_days=365)
        self.daily_activity_glucose_overlay_chart.plot_overlay(overlay_rows)

        selected_date = self.intraday_activity_date_filter.currentData()

        if selected_date is not None:
            start_datetime = datetime.combine(selected_date, datetime.min.time())
            end_datetime = (
                start_datetime
                + timedelta(days=1)
                - timedelta(microseconds=1)
            )

            alignment_rows = get_intraday_activity_glucose_alignment(
                start_date=start_datetime,
                end_date=end_datetime,
                glucose_days=365,
                bucket_minutes=30,
            )
        else:
            alignment_rows = []

        self.intraday_activity_glucose_alignment_chart.plot_alignment(alignment_rows)

        self._update_temperature_glucose_table()

        profile_data = get_time_of_day_profile(readings)
        self.profile_chart.plot_profile(profile_data)

        boxplot_data = get_meal_event_boxplot_data(readings)
        self.meal_boxplot_chart.plot_boxplot(boxplot_data)

        effectiveness_df = calculate_insulin_effectiveness(readings)

        meal_event_order = [
            "Pre-Breakfast",
            "Post-Breakfast",
            "Pre-Lunch",
            "Post-Lunch",
            "Pre-Dinner",
            "Post-Dinner",
            "Before Bed",
            "Night",
        ]

        if not effectiveness_df.empty:
            effectiveness_df["meal_event_label"] = pd.Categorical(
                effectiveness_df["meal_event_label"],
                categories=meal_event_order,
                ordered=True,
            )
            effectiveness_df = effectiveness_df.sort_values("meal_event_label")

        if effectiveness_df.empty:
            self.insulin_effectiveness_table.setRowCount(0)
        else:
            self.insulin_effectiveness_table.setRowCount(len(effectiveness_df))

        for row_index, (_, row) in enumerate(effectiveness_df.iterrows()):
            meal_event_item = QTableWidgetItem(str(row["meal_event_label"]))
            standard_ratio_item = QTableWidgetItem(
                f"{row['standard_ratio_g_per_u']:.1f}"
            )
            actual_ratio_item = QTableWidgetItem(f"{row['avg_ratio_g_per_u']:.1f}")
            count_item = QTableWidgetItem(str(int(row["count"])))

            outcome_value = row["avg_outcome_glucose"]
            outcome_item = QTableWidgetItem(f"{outcome_value:.1f}")
            outcome_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if outcome_value < 4:
                outcome_item.setForeground(QColor(220, 80, 80))
            elif outcome_value <= 10:
                outcome_item.setForeground(QColor(102, 204, 102))
            elif outcome_value <= 15:
                outcome_item.setForeground(QColor(255, 210, 80))
            else:
                outcome_item.setForeground(QColor(200, 140, 255))

            if outcome_value < 4:
                status_text = "Running low"
            elif outcome_value <= 10:
                status_text = "In range"
            elif outcome_value <= 15:
                status_text = "Running high"
            else:
                status_text = "Very high"

            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if outcome_value < 4:
                status_item.setForeground(QColor(220, 80, 80))
            elif outcome_value <= 10:
                status_item.setForeground(QColor(102, 204, 102))
            elif outcome_value <= 15:
                status_item.setForeground(QColor(255, 210, 80))
            else:
                status_item.setForeground(QColor(200, 140, 255))

            if outcome_value < 4:
                suggestion_text = "Consider weaker ratio"
            elif outcome_value <= 10:
                suggestion_text = "Keep current ratio"
            else:
                suggestion_text = "Consider stronger ratio"

            suggestion_item = QTableWidgetItem(suggestion_text)
            suggestion_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if outcome_value < 4:
                suggestion_item.setForeground(QColor(220, 80, 80))
            elif outcome_value <= 10:
                suggestion_item.setForeground(QColor(102, 204, 102))
            else:
                suggestion_item.setForeground(QColor(255, 210, 80))

            meal_event_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            standard_ratio_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            actual_ratio_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            standard = row["standard_ratio_g_per_u"]
            actual = row["avg_ratio_g_per_u"]

            if abs(actual - standard) >= 1:
                font = actual_ratio_item.font()
                font.setBold(True)
                actual_ratio_item.setFont(font)
                actual_ratio_item.setForeground(QColor(255, 170, 0))

            self.insulin_effectiveness_table.setItem(row_index, 0, meal_event_item)
            self.insulin_effectiveness_table.setItem(
                row_index, 1, standard_ratio_item
            )
            self.insulin_effectiveness_table.setItem(row_index, 2, actual_ratio_item)
            self.insulin_effectiveness_table.setItem(row_index, 3, outcome_item)
            self.insulin_effectiveness_table.setItem(row_index, 4, status_item)
            self.insulin_effectiveness_table.setItem(row_index, 5, suggestion_item)
            self.insulin_effectiveness_table.setItem(row_index, 6, count_item)

        fig = self.dose_effectiveness_chart.figure
        fig.clear()
        ax = fig.add_subplot(111)
        apply_chart_theme(fig, ax)

        if effectiveness_df.empty:
            ax.text(
                0.5,
                0.5,
                "No effectiveness data",
                ha="center",
                va="center",
                color=CHART_TEXT,
            )
            ax.set_axis_off()
        else:
            events = effectiveness_df["meal_event_label"]
            glucose = effectiveness_df["avg_outcome_glucose"]

            bars = ax.bar(events, glucose)
            max_val = max(glucose)
            ax.set_ylim(0, max_val + 2)
            ax.axhspan(4, 10, color=TARGET_GREEN, alpha=0.12)
            ax.axhline(4, color="#66BB6A", linestyle=":", linewidth=1)
            ax.axhline(10, color="#66BB6A", linestyle=":", linewidth=1)

            for bar, value in zip(bars, glucose):
                if value < 4:
                    bar.set_color(HYPO_RED)
                elif value <= 10:
                    bar.set_color(TARGET_GREEN)
                elif value <= 15:
                    bar.set_color(HIGH_YELLOW)
                else:
                    bar.set_color(HYPER_DANGER)

            for bar, value in zip(bars, glucose):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    value + 0.3,
                    f"{value:.1f}",
                    ha="center",
                    va="bottom",
                    color=CHART_TEXT,
                    fontsize=9,
                )

            ax.set_title("Dose Effectiveness (Outcome Glucose)", color=CHART_TEXT)
            ax.set_ylabel("Glucose (mmol/L)", color=CHART_TEXT)
            ax.grid(True, color=CHART_GRID, alpha=0.3)

        self.dose_effectiveness_chart.draw()

        time_df = calculate_time_based_effectiveness(readings, days=7)

        if not time_df.empty:
            time_df["meal_event_label"] = pd.Categorical(
                time_df["meal_event_label"],
                categories=meal_event_order,
                ordered=True,
            )
            time_df = time_df.sort_values("meal_event_label")

        if time_df.empty:
            self.time_effectiveness_table.setRowCount(0)
        else:
            self.time_effectiveness_table.setRowCount(len(time_df))

            for row_index, (_, row) in enumerate(time_df.iterrows()):
                meal_event_item = QTableWidgetItem(str(row["meal_event_label"]))
                older_item = QTableWidgetItem(f"{row['older_avg']:.1f}")
                recent_item = QTableWidgetItem(f"{row['recent_avg']:.1f}")
                change_item = QTableWidgetItem(f"{row['change']:+.1f}")

                meal_event_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                older_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                recent_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                change_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                self.time_effectiveness_table.setItem(row_index, 0, meal_event_item)
                self.time_effectiveness_table.setItem(row_index, 1, older_item)
                self.time_effectiveness_table.setItem(row_index, 2, recent_item)
                self.time_effectiveness_table.setItem(row_index, 3, change_item)

        self.table.blockSignals(True)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(readings))

        for row_index, reading in enumerate(readings):
            id_item = QTableWidgetItem(str(reading["id"]))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            recorded_at_text = reading["recorded_at"].strftime("%Y-%m-%d %H:%M")
            recorded_at_item = QTableWidgetItem(recorded_at_text)

            glucose_value = reading["glucose_value"]
            glucose_item = NumericTableWidgetItem(glucose_value)
            glucose_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

            if glucose_value < 3.3:
                glucose_item.setForeground(QColor(220, 80, 80))
                font = glucose_item.font()
                font.setBold(True)
                glucose_item.setFont(font)
            elif glucose_value < 4:
                glucose_item.setForeground(QColor(255, 170, 0))
            elif glucose_value <= 10:
                glucose_item.setForeground(QColor(102, 204, 102))
            elif glucose_value <= 15:
                glucose_item.setForeground(QColor(255, 210, 80))
            else:
                glucose_item.setForeground(QColor(200, 140, 255))
                font = glucose_item.font()
                font.setBold(True)
                glucose_item.setFont(font)

            meal_event_item = QTableWidgetItem(reading["meal_event_label"])
            meal_event_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            notes_item = QTableWidgetItem(reading["notes"] or "")
            carbs_item = QTableWidgetItem(str(reading.get("carbs_g") or ""))
            humalog_item = QTableWidgetItem(str(reading.get("humalog_u") or ""))
            tresiba_item = QTableWidgetItem(str(reading.get("tresiba_u") or ""))

            self.table.setItem(row_index, 0, id_item)
            self.table.setItem(row_index, 1, recorded_at_item)
            self.table.setItem(row_index, 2, glucose_item)
            self.table.setItem(row_index, 3, meal_event_item)
            self.table.setItem(row_index, 4, carbs_item)
            self.table.setItem(row_index, 5, humalog_item)
            self.table.setItem(row_index, 6, tresiba_item)
            self.table.setItem(row_index, 7, notes_item)

        self.table.setSortingEnabled(True)
        self.table.sortItems(1, Qt.SortOrder.DescendingOrder)
        self.table.blockSignals(False)

        self.selected_reading_id = None
        self.notes_editor.clear()

        # --- Update active filter label ---
        meal_event = self.meal_event_filter.currentText()

        if self.selected_range_filter and meal_event != "All":
            self.active_filter_label.setText(
                f"Filtered: {self.selected_range_filter.capitalize()} • {meal_event}"
            )
        elif self.selected_range_filter:
            self.active_filter_label.setText(
                f"Filtered: {self.selected_range_filter.capitalize()}"
            )
        elif meal_event != "All":
            self.active_filter_label.setText(
                f"Filtered: {meal_event}"
            )
        else:
            self.active_filter_label.setText("")

    def handle_import_csv(self) -> None:
        """Import a Diabetes:M CSV file and refresh the tab on success."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Diabetes:M CSV",
            str(Path.home()),
            "CSV Files (*.csv)",
        )

        if not file_path:
            return

        try:
            imported_count = import_diabetes_m_csv(file_path)
        except Exception as exc:
            QMessageBox.critical(self, "Import failed", f"Could not import file:\n{exc}")
            return

        QMessageBox.information(
            self,
            "Import complete",
            f"Imported {imported_count} new readings.",
        )
        self.load_readings()

    def handle_export_pdf(self) -> None:
        """Export a PDF report containing summary metrics and key charts."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF",
            "riglog_glucose_report.pdf",
            "PDF Files (*.pdf)",
        )

        if not file_path:
            return

        doc = SimpleDocTemplate(
            file_path,
            title="RigLog Report",
            author="RigLog",
        )
        styles = getSampleStyleSheet()

        content = []
        content.append(Paragraph("RigLog Glucose Report", styles["Title"]))
        content.append(Paragraph("Personal Glucose Analysis Report", styles["Italic"]))
        content.append(Spacer(1, 12))

        readings = self._get_filtered_readings()

        content.append(Paragraph("Summary Stats", styles["Heading2"]))
        content.append(Paragraph(f"Total readings: {len(readings)}", styles["Normal"]))

        metrics = calculate_glucose_variability_metrics(pd.DataFrame(readings))

        if metrics["mean_glucose"] is not None:
            content.append(
                Paragraph(
                    f"Average glucose: {metrics['mean_glucose']} mmol/L",
                    styles["Normal"],
                )
            )
            content.append(Paragraph(f"SD: {metrics['sd']}", styles["Normal"]))
            content.append(Paragraph(f"CV: {metrics['cv_pct']}%", styles["Normal"]))
            content.append(Paragraph(f"GMI: {metrics['gmi']}%", styles["Normal"]))

        agp_df = calculate_agp(pd.DataFrame(readings))

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
            draw_agp_figure(self.agp_figure, agp_df)
            self.agp_figure.savefig(tmpfile.name)
            content.append(Spacer(1, 13))
            content.append(Paragraph("AGP", styles["Heading2"]))
            content.append(Image(tmpfile.name, width=500, height=210))

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
            self.dose_effectiveness_chart.figure.savefig(tmpfile.name)
            content.append(Spacer(1, 12))
            content.append(
                KeepTogether(
                    [
                        Paragraph("Dose Effectiveness", styles["Heading2"]),
                        Spacer(1, 8),
                        Image(tmpfile.name, width=500, height=210),
                    ]
                )
            )

        doc.build(content)
        QMessageBox.information(self, "Export PDF", "PDF exported successfully.")

    def handle_row_selection(self) -> None:
        """Load notes for the currently selected reading into the editor."""
        selected_items = self.table.selectedItems()

        if not selected_items:
            self.selected_reading_id = None
            self.notes_editor.clear()
            return

        row = selected_items[0].row()

        reading_id_item = self.table.item(row, 0)
        notes_item = self.table.item(row, 7)

        if reading_id_item is None:
            self.selected_reading_id = None
            self.notes_editor.clear()
            return

        self.selected_reading_id = int(reading_id_item.text())
        self.notes_editor.setPlainText(notes_item.text() if notes_item else "")

    def handle_save_note(self) -> None:
        """Persist the edited note for the selected glucose reading."""
        if self.selected_reading_id is None:
            QMessageBox.warning(self, "No selection", "Please select a reading first.")
            return

        notes_text = self.notes_editor.toPlainText().strip()

        try:
            update_glucose_note(self.selected_reading_id, notes_text or None)
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", f"Could not save note:\n{exc}")
            return

        QMessageBox.information(self, "Saved", "Note updated successfully.")
        self.load_readings()

    def handle_cell_edit(self, row: int, column: int) -> None:
        """Persist inline edits for carbs and insulin fields back to the database."""
        if self.table.item(row, 0) is None:
            return

        if column not in [4, 5, 6]:
            return

        reading_id = int(self.table.item(row, 0).text())
        item = self.table.item(row, column)
        value_text = item.text().strip() if item else ""

        try:
            value = float(value_text) if value_text else None
        except ValueError:
            QMessageBox.warning(self, "Invalid input", "Please enter a valid number.")
            self.load_readings()
            return

        field_map = {
            4: "carbs_g",
            5: "humalog_u",
            6: "tresiba_u",
        }

        field_name = field_map[column]

        try:
            update_glucose_field(reading_id, field_name, value)
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", f"Could not save field:\n{exc}")
            self.load_readings()

    def _apply_range_filter(self, readings: list[dict]) -> list[dict]:
        """Filter readings by the selected glucose range card."""
        if self.selected_range_filter is None:
            return readings

        if self.selected_range_filter == "hypo":
            return [r for r in readings if r["glucose_value"] < 3.3]

        if self.selected_range_filter == "low":
            return [r for r in readings if 3.3 <= r["glucose_value"] < 4.0]

        if self.selected_range_filter == "target":
            return [r for r in readings if 4.0 <= r["glucose_value"] <= 10.0]

        if self.selected_range_filter == "high":
            return [r for r in readings if 10.0 < r["glucose_value"] <= 15.0]

        if self.selected_range_filter == "hyper":
            return [r for r in readings if r["glucose_value"] > 15.0]

        return readings

    def handle_range_card_click(self, range_name: str) -> None:
        """Toggle a glucose range card filter and refresh the tab."""
        if self.selected_range_filter == range_name:
            self.selected_range_filter = None
        else:
            self.selected_range_filter = range_name

        self._update_range_card_selection_state()
        if self.selected_range_filter:
            self.active_filter_label.setText(
                f"Filtered: {self.selected_range_filter.capitalize()}"
            )
        else:
            self.active_filter_label.setText("")
        self.load_readings()

    def handle_clear_filters(self) -> None:
        """Clear active glucose filters and refresh the tab."""
        self.selected_range_filter = None

        self.meal_event_filter.blockSignals(True)
        self.meal_event_filter.setCurrentIndex(0)  # All
        self.meal_event_filter.blockSignals(False)

        self._update_range_card_selection_state()
        self.load_readings()

    def _update_range_card_selection_state(self) -> None:
        """Visually mark the active glucose range filter card."""
        range_cards = {
            "hypo": self.hypo_label,
            "low": self.low_label,
            "target": self.tir_label,
            "high": self.high_label,
            "hyper": self.hyper_label,
        }

        for range_name, card in range_cards.items():
            card.setProperty(
                "selected",
                self.selected_range_filter == range_name,
            )
            card.style().unpolish(card)
            card.style().polish(card)

    def _update_range_breakdown(self, readings: list[dict]) -> None:
        """Update selected range breakdown chart by meal event."""
        if not self.selected_range_filter or not readings:
            self.range_breakdown_chart.plot_breakdown([], None)
            return

        breakdown: dict[str, int] = {}

        for reading in readings:
            label = reading["meal_event_label"]
            breakdown[label] = breakdown.get(label, 0) + 1

        sorted_items = sorted(
            breakdown.items(),
            key=lambda x: self.MEAL_EVENT_ORDER.index(x[0])
            if x[0] in self.MEAL_EVENT_ORDER
            else 999,
        )

        self.range_breakdown_chart.plot_breakdown(
            sorted_items,
            self.selected_range_filter,
        )

    def _update_temperature_glucose_table(self) -> None:
        """Populate the temperature vs glucose summary table."""
        summary_rows = get_temperature_glucose_bucket_summary(days=365)

        self.temperature_glucose_table.setRowCount(len(summary_rows))

        for row_index, row in enumerate(summary_rows):
            bucket_item = QTableWidgetItem(row["temperature_bucket_label"])
            days_item = QTableWidgetItem(str(row["day_count"]))
            readings_item = QTableWidgetItem(str(row["glucose_count"]))

            avg_temp = row["avg_temperature_c"]
            avg_glucose = row["avg_glucose"]

            avg_temp_item = QTableWidgetItem(
                f"{avg_temp:.1f} °C" if avg_temp is not None else "-"
            )
            avg_glucose_item = QTableWidgetItem(
                f"{avg_glucose:.1f}" if avg_glucose is not None else "-"
            )
            target_item = QTableWidgetItem(f"{row['target_pct']:.1f}%")
            hypo_item = QTableWidgetItem(f"{row['hypo_pct']:.1f}%")
            hyper_item = QTableWidgetItem(f"{row['hyper_pct']:.1f}%")

            items = [
                bucket_item,
                days_item,
                readings_item,
                avg_temp_item,
                avg_glucose_item,
                target_item,
                hypo_item,
                hyper_item,
            ]

            for item in items:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if avg_glucose is not None:
                if avg_glucose < 4:
                    avg_glucose_item.setForeground(QColor(220, 80, 80))
                elif avg_glucose <= 10:
                    avg_glucose_item.setForeground(QColor(102, 204, 102))
                elif avg_glucose <= 15:
                    avg_glucose_item.setForeground(QColor(255, 210, 80))
                else:
                    avg_glucose_item.setForeground(QColor(200, 140, 255))

            if row["target_pct"] >= 70:
                target_item.setForeground(QColor(102, 204, 102))
            elif row["target_pct"] > 0:
                target_item.setForeground(QColor(255, 210, 80))

            if row["hypo_pct"] > 0:
                hypo_item.setForeground(QColor(220, 80, 80))

            if row["hyper_pct"] > 0:
                hyper_item.setForeground(QColor(200, 140, 255))

            self.temperature_glucose_table.setItem(row_index, 0, bucket_item)
            self.temperature_glucose_table.setItem(row_index, 1, days_item)
            self.temperature_glucose_table.setItem(row_index, 2, readings_item)
            self.temperature_glucose_table.setItem(row_index, 3, avg_temp_item)
            self.temperature_glucose_table.setItem(row_index, 4, avg_glucose_item)
            self.temperature_glucose_table.setItem(row_index, 5, target_item)
            self.temperature_glucose_table.setItem(row_index, 6, hypo_item)
            self.temperature_glucose_table.setItem(row_index, 7, hyper_item)

    def handle_breakdown_meal_event_click(self, meal_event_label: str) -> None:
        """Toggle the clicked meal event filter from the breakdown chart."""
        current_text = self.meal_event_filter.currentText()

        if current_text == meal_event_label:
            self.meal_event_filter.setCurrentIndex(0)  # All
            return

        index = self.meal_event_filter.findText(meal_event_label)

        if index == -1:
            return

        self.meal_event_filter.setCurrentIndex(index)
