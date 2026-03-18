from pathlib import Path
from datetime import timedelta
from statistics import mean
import pandas as pd

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QScrollArea,
)

from app.services.glucose.analysis import (
    calculate_agp,
    calculate_glucose_variability_metrics,
    get_all_glucose_readings_with_meal_event,
    calculate_time_in_range_breakdown,
    get_daily_average_glucose,
    get_meal_event_boxplot_data,
    get_time_of_day_profile,
    update_glucose_note,
    get_time_in_range_metrics,
)
from app.services.glucose.importer import import_diabetes_m_csv


class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, value: float) -> None:
        super().__init__(f"{value:.1f}")
        self.numeric_value = value

    def __lt__(self, other: object) -> bool:
        if isinstance(other, NumericTableWidgetItem):
            return self.numeric_value < other.numeric_value
        return super().__lt__(other)


def rolling_average(values: list[float], window: int = 7) -> list[float]:
    result = []

    for i in range(len(values)):
        start = max(0, i - window + 1)
        window_values = values[start:i + 1]
        result.append(mean(window_values))

    return result


def draw_agp_figure(fig: Figure, agp_df: pd.DataFrame) -> None:
    fig.clear()
    ax = fig.add_subplot(111)

    fig.patch.set_facecolor("#1e1e1e")
    ax.set_facecolor("#1e1e1e")

    ax.set_title("Ambulatory Glucose Profile (AGP)", color="#f0f0f0")
    ax.set_xlabel("Time of day", color="#f0f0f0")
    ax.set_ylabel("Glucose (mmol/L)", color="#f0f0f0")

    ax.tick_params(axis="x", colors="#f0f0f0")
    ax.tick_params(axis="y", colors="#f0f0f0")

    for spine in ax.spines.values():
        spine.set_color("#888888")

    ax.grid(True, color="#444444", alpha=0.5)

    if agp_df.empty:
        ax.text(0.5, 0.5, "No AGP data available", ha="center", va="center", color="#f0f0f0")
        ax.set_axis_off()
        fig.tight_layout()
        return

    x = agp_df["hour_decimal"].to_numpy()
    p10 = agp_df["p10"].to_numpy()
    p25 = agp_df["p25"].to_numpy()
    p50 = agp_df["p50"].to_numpy()
    p75 = agp_df["p75"].to_numpy()
    p90 = agp_df["p90"].to_numpy()

    ax.axhspan(4.0, 10.0, color="#43a047", alpha=0.18)

    ax.axhline(3.3, color="#ff6666", linestyle="--", linewidth=1)
    ax.axhline(4, color="#66bb6a", linestyle=":", linewidth=1)
    ax.axhline(10, color="#66bb6a", linestyle=":", linewidth=1)
    ax.axhline(15, color="#b388ff", linestyle="--", linewidth=1)

    ax.fill_between(x, p10, p90, color="#ff4d4d", alpha=0.15, label="10–90%")
    ax.fill_between(x, p25, p75, color="#ff4d4d", alpha=0.30, label="25–75%")
    ax.plot(x, p50, color="#ffffff", linewidth=2.2, label="Median")

    ax.set_xlim(0, 24)
    ax.set_ylim(0, 30)
    ax.set_yticks(range(0, 31, 5))
    ax.set_xticks([0, 4, 8, 12, 16, 20, 24])
    ax.set_xticklabels(["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "24:00"])

    legend = ax.legend(facecolor="#1e1e1e", edgecolor="#888888")
    for text in legend.get_texts():
        text.set_color("#f0f0f0")

    fig.tight_layout()


class GlucoseTrendChart(FigureCanvasQTAgg):
    def __init__(self) -> None:
        self.figure = Figure(figsize=(6, 4.5))
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)

    def plot_daily_average(self, daily_data: list[dict]) -> None:
        self.ax.clear()

        # dark theme
        self.figure.patch.set_facecolor("#1e1e1e")
        self.ax.set_facecolor("#1e1e1e")

        self.ax.set_title("Daily Average Glucose", color="#f0f0f0")
        self.ax.set_ylabel("mmol/L", color="#f0f0f0")

        self.ax.tick_params(axis="x", colors="#f0f0f0")
        self.ax.tick_params(axis="y", colors="#f0f0f0")

        for spine in self.ax.spines.values():
            spine.set_color("#888888")

        self.ax.grid(True, color="#444444", alpha=0.5)

        # shaded zones
        self.ax.axhspan(0, 3.3, color="#d32f2f", alpha=0.12)
        self.ax.axhspan(4, 10, color="#43a047", alpha=0.35)
        self.ax.axhspan(15, 25, color="#8e24aa", alpha=0.12)

        # threshold lines
        self.ax.axhline(3.3, color="#ff6666", linestyle="--", linewidth=1)
        self.ax.axhline(4, color="#66bb6a", linestyle=":", linewidth=1)
        self.ax.axhline(10, color="#66bb6a", linestyle=":", linewidth=1)
        self.ax.axhline(15, color="#b388ff", linestyle="--", linewidth=1)

        self.ax.set_ylim(0, 30)
        self.ax.set_yticks(range(0, 31, 5))

        if not daily_data:
            self.draw()
            return

        dates = [row["date"] for row in daily_data]
        averages = [row["avg"] for row in daily_data]
        rolling_avg = rolling_average(averages, window=7)

        # force x-axis to match the filtered date range
        if len(dates) == 1:
            self.ax.set_xlim(dates[0] - timedelta(days=1), dates[0] + timedelta(days=1))
        else:
            self.ax.set_xlim(min(dates), max(dates))
            self.ax.margins(x=0.02)

        # daily averages
        self.ax.plot(
            dates,
            averages,
            color="#ff4d4d",
            marker="o",
            markersize=5,
            linewidth=1.8,
            alpha=0.9,
            label="Daily Average",
        )

        # 7-day rolling average
        self.ax.plot(
            dates,
            rolling_avg,
            color="#ffffff",
            linewidth=2.5,
            alpha=0.9,
            label="7-Day Trend",
        )

        self.ax.legend(facecolor="#1e1e1e", edgecolor="#888888", labelcolor="#f0f0f0")
        self.figure.autofmt_xdate()
        self.figure.subplots_adjust(bottom=0.20)
        self.draw()


class GlucoseTab(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.selected_reading_id: int | None = None

        # Outer layout (holds the scroll area)
        outer_layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        # Inner container
        container = QWidget()
        self.layout = QVBoxLayout(container)

        scroll.setWidget(container)

        outer_layout.addWidget(scroll)

        self.layout.setSpacing(18)
        self.layout.setContentsMargins(10, 10, 10, 20)

        self._build_toolbar()
        self._build_summary_panel()
        self._build_agp_chart()
        self._build_chart()
        self._build_profile_chart()
        self._build_meal_boxplot_chart()
        self._build_legend()
        self._build_table()
        self._build_notes_panel()

        self.load_readings()

    def _create_summary_card(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumHeight(60)
        label.setStyleSheet(
            """
            QLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 10px 16px;
                border: 1px solid #555555;
                border-radius: 8px;
                background-color: #2f2f2f;
                color: #f0f0f0;
            }
            """
        )
        return label

    def _build_toolbar(self) -> None:
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.import_button = QPushButton("Import Diabetes:M CSV")
        self.import_button.clicked.connect(self.handle_import_csv)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_readings)

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
        toolbar.addSpacing(12)
        toolbar.addWidget(QLabel("Meal Event:"))
        toolbar.addWidget(self.meal_event_filter)
        toolbar.addWidget(QLabel("Time Range:"))
        toolbar.addWidget(self.time_filter)
        toolbar.addStretch()

        self.layout.addLayout(toolbar)

    def _build_summary_panel(self) -> None:
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(12)
        summary_layout.setContentsMargins(0, 10, 0, 10)

        self.count_label = self._create_summary_card("Readings: -")
        self.avg_label = self._create_summary_card("Average: -")
        self.min_label = self._create_summary_card("Lowest: -")
        self.max_label = self._create_summary_card("Highest: -")
        self.tir_label = self._create_summary_card("In Range: -")
        self.hypo_label = self._create_summary_card("Hypo: -")
        self.low_label = self._create_summary_card("Low: -")
        self.target_label = self._create_summary_card("Target: -")
        self.high_label = self._create_summary_card("High: -")
        self.hyper_label = self._create_summary_card("Hyper: -")
        self.sd_label = self._create_summary_card("SD: -")
        self.cv_label = self._create_summary_card("CV: -")
        self.gmi_label = self._create_summary_card("GMI: -")

        summary_layout.addStretch()
        summary_layout.addWidget(self.count_label)
        summary_layout.addWidget(self.avg_label)
        summary_layout.addWidget(self.min_label)
        summary_layout.addWidget(self.max_label)
        summary_layout.addWidget(self.tir_label)
        summary_layout.addWidget(self.hypo_label)
        summary_layout.addWidget(self.low_label)
        summary_layout.addWidget(self.target_label)
        summary_layout.addWidget(self.high_label)
        summary_layout.addWidget(self.hyper_label)
        summary_layout.addWidget(self.sd_label)
        summary_layout.addWidget(self.cv_label)
        summary_layout.addWidget(self.gmi_label)
        summary_layout.addStretch()

        self.layout.addLayout(summary_layout)

    def _build_chart(self) -> None:
        self.chart = GlucoseTrendChart()
        self.chart.setMinimumHeight(320)
        self.layout.addWidget(self.chart)

    def _build_agp_chart(self) -> None:
        title = QLabel("Ambulatory Glucose Profile")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            """
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #f0f0f0;
                margin-top: 8px;
                margin-bottom: 4px;
            }
            """
        )

        self.agp_figure = Figure(figsize=(8, 4))
        self.agp_canvas = FigureCanvasQTAgg(self.agp_figure)
        self.agp_canvas.setMinimumHeight(320)

        self.layout.addWidget(title)
        self.layout.addWidget(self.agp_canvas)

    def _build_profile_chart(self) -> None:
        self.profile_chart = GlucoseProfileChart()
        self.profile_chart.setMinimumHeight(320)
        self.layout.addWidget(self.profile_chart)

    def _build_meal_boxplot_chart(self) -> None:
        self.meal_boxplot_chart = MealEventBoxPlotChart()
        self.meal_boxplot_chart.setMinimumHeight(340)
        self.layout.addWidget(self.meal_boxplot_chart)

    def _build_table(self) -> None:
        self.table = QTableWidget()
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
        notes_layout = QVBoxLayout()

        self.notes_label = QLabel("Notes for selected reading:")
        self.notes_editor = QTextEdit()
        self.notes_editor.setPlaceholderText("Add contextual notes here...")

        self.save_note_button = QPushButton("Save Note")
        self.save_note_button.clicked.connect(self.handle_save_note)

        notes_layout.addWidget(self.notes_label)
        notes_layout.addWidget(self.notes_editor)
        notes_layout.addWidget(self.save_note_button)

        self.layout.addLayout(notes_layout)

    def _get_filtered_readings(self) -> list[dict]:
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
        self.cv_label.setText(f"CV\n{variability['cv_pct']:.1f}%")
        self.gmi_label.setText(f"GMI\n{variability['gmi']:.1f}%")

    def _build_legend(self) -> None:
        legend_layout = QHBoxLayout()
        legend_layout.setSpacing(10)
        legend_layout.setContentsMargins(0, 10, 0, 6)

        items = [
            ("Hypo (<3.3)", "#dc5050", "#1e1e1e"),
            ("Low (3.3–4)", "#ffaa00", "#1e1e1e"),
            ("Target (4–10)", "#43a047", "#f0f0f0"),
            ("High (10–15)", "#ffd250", "#1e1e1e"),
            ("Hyper (>15)", "#c88cff", "#1e1e1e"),
        ]

        legend_layout.addStretch()

        for text, bg_color, text_color in items:
            label = QLabel(text)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(
                f"""
                QLabel {{
                    background-color: {bg_color};
                    color: {text_color};
                    border-radius: 10px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                """
            )
            legend_layout.addWidget(label)

        legend_layout.addStretch()
        self.layout.addLayout(legend_layout)

    def load_readings(self) -> None:
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

        self.selected_reading_id = None
        self.notes_editor.clear()

    def handle_import_csv(self) -> None:
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

    def handle_row_selection(self) -> None:
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
        if self.table.item(row, 0) is None:
            return

        reading_id = int(self.table.item(row, 0).text())

        if column not in [4, 5, 6]:
            return

        item = self.table.item(row, column)
        value_text = item.text().strip() if item else ""

        try:
            value = float(value_text) if value_text else None
        except ValueError:
            QMessageBox.warning(self, "Invalid input", "Please enter a valid number.")
            return

        field_map = {
            4: "carbs_g",
            5: "humalog_u",
            6: "tresiba_u",
        }

        field_name = field_map[column]

        from app.services.glucose.analysis import update_glucose_field
        update_glucose_field(reading_id, field_name, value)

class GlucoseProfileChart(FigureCanvasQTAgg):
    def __init__(self) -> None:
        self.figure = Figure(figsize=(6, 4.5))
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)

    def plot_profile(self, profile_data: list[dict]) -> None:
        self.ax.clear()

        self.figure.patch.set_facecolor("#1e1e1e")
        self.ax.set_facecolor("#1e1e1e")

        self.ax.set_title("Daily Glucose Profile", color="#f0f0f0")
        self.ax.set_ylabel("mmol/L", color="#f0f0f0")
        self.ax.set_xlabel("Time of Day", color="#f0f0f0", labelpad=10)

        self.ax.tick_params(axis="x", colors="#f0f0f0")
        self.ax.tick_params(axis="y", colors="#f0f0f0")

        self.ax.set_ylim(0, 30)
        self.ax.set_yticks(range(0, 31, 5))

        for spine in self.ax.spines.values():
            spine.set_color("#888888")

        self.ax.grid(True, color="#444444", alpha=0.5)

        self.ax.axhspan(0, 3.3, color="#d32f2f", alpha=0.12)
        self.ax.axhspan(4, 10, color="#43a047", alpha=0.35)
        self.ax.axhspan(15, 30, color="#8e24aa", alpha=0.12)

        self.ax.axhline(3.3, color="#ff6666", linestyle="--", linewidth=1)
        self.ax.axhline(4, color="#66bb6a", linestyle=":", linewidth=1)
        self.ax.axhline(10, color="#66bb6a", linestyle=":", linewidth=1)
        self.ax.axhline(15, color="#b388ff", linestyle="--", linewidth=1)

        if not profile_data:
            self.draw()
            return

        x = [row["bucket_minutes"] / 60 for row in profile_data]
        y = [row["avg"] for row in profile_data]
        labels = [row["time_label"] for row in profile_data]

        self.ax.plot(
            x,
            y,
            color="#ff4d4d",
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

            if minutes % 120 == 0:  # every 2 hours
                tick_positions.append(minutes / 60)
                tick_labels.append(row["time_label"])

        self.ax.set_xticks(tick_positions)
        self.ax.set_xticklabels(tick_labels)

        self.ax.legend(
            facecolor="#1e1e1e",
            edgecolor="#888888",
            labelcolor="#f0f0f0",
        )

        self.figure.subplots_adjust(bottom=0.24)
        self.draw()


class MealEventBoxPlotChart(FigureCanvasQTAgg):
    def __init__(self) -> None:
        self.figure = Figure(figsize=(6, 4.5))
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)

    def plot_boxplot(self, boxplot_data: list[dict]) -> None:
        self.ax.clear()

        self.figure.patch.set_facecolor("#1e1e1e")
        self.ax.set_facecolor("#1e1e1e")

        self.ax.set_title("Glucose Distribution by Meal Event", color="#f0f0f0")
        self.ax.set_xlabel("Meal Event", color="#f0f0f0", labelpad=10)
        self.ax.set_ylabel("mmol/L", color="#f0f0f0")

        self.ax.tick_params(axis="x", colors="#f0f0f0", labelsize=9)
        self.ax.tick_params(axis="y", colors="#f0f0f0")

        for spine in self.ax.spines.values():
            spine.set_color("#888888")

        self.ax.grid(True, axis="y", color="#444444", alpha=0.5)

        self.ax.axhspan(0, 3.3, color="#d32f2f", alpha=0.12)
        self.ax.axhspan(4, 10, color="#43a047", alpha=0.35)
        self.ax.axhspan(15, 30, color="#8e24aa", alpha=0.12)

        self.ax.axhline(3.3, color="#ff6666", linestyle="--", linewidth=1)
        self.ax.axhline(4, color="#66bb6a", linestyle=":", linewidth=1)
        self.ax.axhline(10, color="#66bb6a", linestyle=":", linewidth=1)
        self.ax.axhline(15, color="#b388ff", linestyle="--", linewidth=1)

        self.ax.set_ylim(0, 30)
        self.ax.set_yticks(range(0, 31, 5))

        if not boxplot_data:
            self.draw()
            return

        labels = [row["meal_event"] for row in boxplot_data]
        values = [row["values"] for row in boxplot_data]

        box = self.ax.boxplot(
            values,
            labels=labels,
            patch_artist=True,
            widths=0.6,
        )

        for patch in box["boxes"]:
            patch.set(facecolor="#ff4d4d", alpha=0.35, edgecolor="#f0f0f0")

        for median in box["medians"]:
            median.set(color="#ffffff", linewidth=2)

        for whisker in box["whiskers"]:
            whisker.set(color="#dddddd")

        for cap in box["caps"]:
            cap.set(color="#dddddd")

        for flier in box["fliers"]:
            flier.set(
                marker="o",
                markerfacecolor="#ff9999",
                markeredgecolor="#ff9999",
                alpha=0.4,
                markersize=4,
            )

        self.figure.subplots_adjust(bottom=0.24)
        self.draw()
