from pathlib import Path
from datetime import timedelta
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

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.glucose.analysis import (
    calculate_agp,
    calculate_glucose_variability_metrics,
    calculate_insulin_effectiveness,
    calculate_time_based_effectiveness,
    calculate_time_in_range_breakdown,
    get_all_glucose_readings_with_meal_event,
    get_daily_average_glucose,
    get_meal_event_boxplot_data,
    get_time_in_range_metrics,
    get_time_of_day_profile,
    update_glucose_field,
    update_glucose_note,
)
from app.services.glucose.importer import import_diabetes_m_csv


CHART_BG = "#1E1E1E"
CHART_TEXT = "#F0F0F0"
CHART_GRID = "#444444"
CHART_SPINE = "#888888"
HYPO_RED = "#DC5050"
LOW_AMBER = "#FFAA00"
TARGET_GREEN = "#43A047"
HIGH_YELLOW = "#FFD54F"
HYPER_PURPLE = "#B388FF"
LINE_RED = "#FF4D4D"
WHITE = "#FFFFFF"


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
    ax.axhline(15, color=HYPER_PURPLE, linestyle="--", linewidth=1)

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
        self.ax.axhline(15, color=HYPER_PURPLE, linestyle="--", linewidth=1)

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
        self.ax.axhline(15, color=HYPER_PURPLE, linestyle="--", linewidth=1)

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

        labels = [
            row.get("meal_event_label") or row.get("label", "")
            for row in boxplot_data
            ]
        series = [
            row.get("values", [])
            for row in boxplot_data
            if row.get("values")
        ]

        if not series:
            self.draw()
            return

        bp = self.ax.boxplot(series, patch_artist=True, labels=labels)

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


class GlucoseTab(QWidget):
    """Main glucose analytics tab for import, review, analysis, and export."""

    CARD_BASE_STYLE = """
        font-size: 15px;
        font-weight: 700;
        padding: 10px 16px;
        border: 1px solid #2F2F2F;
        border-radius: 10px;
    """

    def __init__(self) -> None:
        super().__init__()

        self.selected_reading_id: int | None = None

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

    def _create_summary_card(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("summaryCardNeutral")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumHeight(64)
        return label

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
        self.time_filter.addItems(
            [
                "All Time",
                "Last 7 Days",
                "Last 14 Days",
                "Last 30 Days",
                "Last 90 Days",
            ]
        )
        self.time_filter.currentIndexChanged.connect(self.load_readings)
        self.time_filter.setFixedWidth(140)

        toolbar.addStretch()
        toolbar.addWidget(self.import_button)
        toolbar.addWidget(self.refresh_button)
        toolbar.addWidget(self.export_pdf_button)
        toolbar.addSpacing(12)
        toolbar.addWidget(self._create_toolbar_label("Meal Event"))
        toolbar.addWidget(self.meal_event_filter)
        toolbar.addWidget(self._create_toolbar_label("Time Range"))
        toolbar.addWidget(self.time_filter)
        toolbar.addStretch()

        self.layout.addLayout(toolbar)

    def _build_summary_panel(self) -> None:
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(12)
        summary_layout.setContentsMargins(0, 8, 0, 8)

        self.count_label = self._create_summary_card("Readings\n-")
        self.avg_label = self._create_summary_card("Average\n-")
        self.min_label = self._create_summary_card("Lowest\n-")
        self.max_label = self._create_summary_card("Highest\n-")
        self.tir_label = self._create_summary_card("In Range\n-")
        self.hypo_label = self._create_summary_card("Hypo\n-")
        self.low_label = self._create_summary_card("Low\n-")
        self.target_label = self._create_summary_card("Target\n-")
        self.high_label = self._create_summary_card("High\n-")
        self.hyper_label = self._create_summary_card("Hyper\n-")
        self.sd_label = self._create_summary_card("SD\n-")
        self.cv_label = self._create_summary_card("CV\n-")
        self.gmi_label = self._create_summary_card("GMI\n-")

        cards = [
            self.count_label,
            self.avg_label,
            self.min_label,
            self.max_label,
            self.tir_label,
            self.hypo_label,
            self.low_label,
            self.target_label,
            self.high_label,
            self.hyper_label,
            self.sd_label,
            self.cv_label,
            self.gmi_label,
        ]

        summary_layout.addStretch()
        for card in cards:
            summary_layout.addWidget(card)
        summary_layout.addStretch()

        self.layout.addLayout(summary_layout)

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
            self._create_section_title("7-Day Improvement by Previous Meal Event")
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

    def _set_card_colour(
        self,
        label: QLabel,
        color: str,
        text_color: str = "#121212",
    ) -> None:
        label.setStyleSheet(
            self.CARD_BASE_STYLE
            + f"background-color: {color}; color: {text_color};"
        )

    def _reset_summary_card_styles(self) -> None:
        cards = [
            self.count_label,
            self.avg_label,
            self.min_label,
            self.max_label,
            self.tir_label,
            self.hypo_label,
            self.low_label,
            self.target_label,
            self.high_label,
            self.hyper_label,
            self.sd_label,
            self.cv_label,
            self.gmi_label,
        ]

        for label in cards:
            label.setStyleSheet("")

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

            if selected_time_range == "Last 7 Days":
                cutoff = latest_timestamp - timedelta(days=7)
            elif selected_time_range == "Last 14 Days":
                cutoff = latest_timestamp - timedelta(days=14)
            elif selected_time_range == "Last 30 Days":
                cutoff = latest_timestamp - timedelta(days=30)
            elif selected_time_range == "Last 90 Days":
                cutoff = latest_timestamp - timedelta(days=90)
            else:
                cutoff = None

            if cutoff is not None:
                readings = [
                    reading
                    for reading in readings
                    if reading["recorded_at"] >= cutoff
                ]

        return readings

    def _update_summary(self, readings: list[dict]) -> None:
        """Update the summary cards using the currently filtered readings."""
        self._reset_summary_card_styles()

        if not readings:
            self.count_label.setText("Readings\n0")
            self.avg_label.setText("Average\n-")
            self.min_label.setText("Lowest\n-")
            self.max_label.setText("Highest\n-")
            self.tir_label.setText("In Range\n-")
            self.hypo_label.setText("Hypo\n-")
            self.low_label.setText("Low\n-")
            self.target_label.setText("Target\n-")
            self.high_label.setText("High\n-")
            self.hyper_label.setText("Hyper\n-")
            self.sd_label.setText("SD\n-")
            self.cv_label.setText("CV\n-")
            self.gmi_label.setText("GMI\n-")
            return

        values = [reading["glucose_value"] for reading in readings]
        tir_metrics = get_time_in_range_metrics(readings)
        variability = calculate_glucose_variability_metrics(pd.DataFrame(readings))
        breakdown = calculate_time_in_range_breakdown(pd.DataFrame(readings))

        self.count_label.setText(f"Readings\n{len(values)}")
        self.avg_label.setText(f"Average\n{sum(values) / len(values):.1f} mmol/L")
        self.min_label.setText(f"Lowest\n{min(values):.1f} mmol/L")
        self.max_label.setText(f"Highest\n{max(values):.1f} mmol/L")
        self.tir_label.setText(f"In Range\n{tir_metrics['target_pct']:.1f}%")
        self.hypo_label.setText(f"Hypo\n{breakdown['hypo']['pct']:.1f}%")
        self.low_label.setText(f"Low\n{breakdown['low']['pct']:.1f}%")
        self.target_label.setText(f"Target\n{breakdown['target']['pct']:.1f}%")
        self.high_label.setText(f"High\n{breakdown['high']['pct']:.1f}%")
        self.hyper_label.setText(f"Hyper\n{breakdown['hyper']['pct']:.1f}%")
        self.sd_label.setText(f"SD\n{variability['sd']:.2f}")

        cv = variability["cv_pct"]
        self.cv_label.setText(f"CV\n{cv:.1f}%")

        if cv < 36:
            color = TARGET_GREEN
        elif cv < 50:
            color = LOW_AMBER
        else:
            color = HYPO_RED

        self._set_card_colour(self.cv_label, color)

        gmi = variability["gmi"]
        self.gmi_label.setText(f"GMI\n{gmi:.1f}%")

        if gmi < 7:
            color = TARGET_GREEN
        elif gmi < 8:
            color = LOW_AMBER
        else:
            color = HYPO_RED

        self._set_card_colour(self.gmi_label, color)
        self._set_card_colour(self.hypo_label, HYPO_RED)
        self._set_card_colour(self.low_label, LOW_AMBER)
        self._set_card_colour(self.target_label, TARGET_GREEN, "#F5F5F5")
        self._set_card_colour(self.high_label, HIGH_YELLOW)
        self._set_card_colour(self.hyper_label, HYPER_PURPLE)

    def load_readings(self) -> None:
        """Refresh all charts, tables, and summary cards from filtered readings."""
        readings = self._get_filtered_readings()

        agp_df = calculate_agp(pd.DataFrame(readings))
        draw_agp_figure(self.agp_figure, agp_df)
        self.agp_canvas.draw()

        self._update_summary(readings)

        daily_data = get_daily_average_glucose(readings)
        self.chart.plot_daily_average(daily_data)

        profile_data = get_time_of_day_profile(readings)
        self.profile_chart.plot_profile(profile_data)

        boxplot_data = get_meal_event_boxplot_data(readings)
        self.meal_boxplot_chart.plot_boxplot(boxplot_data)

        effectiveness_df = calculate_insulin_effectiveness(readings)

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
                    bar.set_color(HYPER_PURPLE)

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
