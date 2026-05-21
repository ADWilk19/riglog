from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from app.services.workouts.analysis import (
    get_recent_workout_sessions,
    get_volume_by_exercise,
    get_workout_summary_metrics,
)
from app.services.workouts.importer import import_workout_csv
from app.services.workouts.maintenance import clear_imported_workout_data
from app.ui.widgets.summary_card import SummaryCard

CHART_BG = "#1E1E1E"
CHART_TEXT = "#F0F0F0"
CHART_GRID = "#444444"
CHART_SPINE = "#888888"
BAR_GREEN = "#43A047"


def apply_chart_theme(fig: Figure, ax) -> None:
    """Apply the shared dark chart theme."""
    fig.patch.set_facecolor(CHART_BG)
    ax.set_facecolor(CHART_BG)
    ax.tick_params(axis="x", colors=CHART_TEXT)
    ax.tick_params(axis="y", colors=CHART_TEXT)

    for spine in ax.spines.values():
        spine.set_color(CHART_SPINE)

    ax.grid(True, axis="x", color=CHART_GRID, alpha=0.5)


class WorkoutVolumeByExerciseChart(FigureCanvasQTAgg):
    """Matplotlib canvas for workout volume grouped by exercise."""

    def __init__(self) -> None:
        self.figure = Figure(figsize=(8, 4.5))
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)

    def plot_volume_by_exercise(self, volume_by_exercise: list[dict]) -> None:
        """Plot top exercises by total training volume."""
        self.ax.clear()
        apply_chart_theme(self.figure, self.ax)

        self.ax.set_title("Top Exercises by Volume", color=CHART_TEXT)
        self.ax.set_xlabel("Volume (kg)", color=CHART_TEXT)

        if not volume_by_exercise:
            self.ax.text(
                0.5,
                0.5,
                "No workout volume data available",
                ha="center",
                va="center",
                color=CHART_TEXT,
                transform=self.ax.transAxes,
            )
            self.ax.set_axis_off()
            self.figure.tight_layout()
            self.draw()
            return

        top_rows = volume_by_exercise[:10]

        exercise_names = [row["exercise_name"] for row in top_rows]
        volumes = [row["total_volume_kg"] for row in top_rows]

        # Reverse so the largest appears at the top of the horizontal chart.
        exercise_names = list(reversed(exercise_names))
        volumes = list(reversed(volumes))

        bars = self.ax.barh(
            exercise_names,
            volumes,
            color=BAR_GREEN,
            alpha=0.85,
        )

        max_volume = max(volumes) if volumes else 0
        label_offset = max_volume * 0.02 if max_volume else 1

        for bar, value in zip(bars, volumes):
            self.ax.text(
                value + label_offset,
                bar.get_y() + bar.get_height() / 2,
                f"{value:,.0f} kg",
                va="center",
                color=CHART_TEXT,
                fontsize=9,
            )

        self.ax.set_xlim(0, max_volume * 1.15 if max_volume else 1)
        self.figure.tight_layout()
        self.draw()


class WorkoutTab(QWidget):
    """Read-only workout analytics tab with CSV import support."""

    def __init__(self) -> None:
        super().__init__()

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        self.layout = QVBoxLayout(container)
        self.layout.setSpacing(20)
        self.layout.setContentsMargins(16, 16, 16, 24)

        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

        self._build_toolbar()
        self._build_summary_cards()
        self._build_volume_by_exercise_chart()
        self._build_recent_sessions_table()
        self._build_volume_by_exercise_table()

        self.refresh_data()

    def _create_section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def _build_toolbar(self) -> None:
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.import_button = QPushButton("Import Workout CSV")
        self.import_button.setObjectName("primaryAction")
        self.import_button.clicked.connect(self.handle_import_csv)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("secondaryAction")
        self.refresh_button.clicked.connect(self.refresh_data)

        self.clear_imported_button = QPushButton("Clear Imported Workouts")
        self.clear_imported_button.setObjectName("secondaryAction")
        self.clear_imported_button.clicked.connect(self.handle_clear_imported_workouts)

        toolbar.addStretch()
        toolbar.addWidget(self.import_button)
        toolbar.addWidget(self.refresh_button)
        toolbar.addWidget(self.clear_imported_button)
        toolbar.addStretch()

        self.layout.addLayout(toolbar)

    def _build_summary_cards(self) -> None:
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(12)

        self.total_sessions_card = SummaryCard("Total Sessions", "-")
        self.weekly_sessions_card = SummaryCard("Last 7 Days", "-")
        self.total_sets_card = SummaryCard("Total Sets", "-")
        self.total_volume_card = SummaryCard("Total Volume", "-")
        self.average_duration_card = SummaryCard("Avg Duration", "-")
        self.recent_workout_card = SummaryCard("Most Recent", "-")

        cards = [
            self.total_sessions_card,
            self.weekly_sessions_card,
            self.total_sets_card,
            self.total_volume_card,
            self.average_duration_card,
            self.recent_workout_card,
        ]

        summary_layout.addStretch()

        for card in cards:
            summary_layout.addWidget(card)

        summary_layout.addStretch()

        self.layout.addLayout(summary_layout)

    def _build_volume_by_exercise_chart(self) -> None:
        self.layout.addWidget(self._create_section_title("Volume by Exercise"))

        self.volume_by_exercise_chart = WorkoutVolumeByExerciseChart()
        self.volume_by_exercise_chart.setMinimumHeight(360)

        self.layout.addWidget(self.volume_by_exercise_chart)

    def _build_recent_sessions_table(self) -> None:
        self.layout.addWidget(self._create_section_title("Recent Workout Sessions"))

        self.recent_sessions_table = QTableWidget()
        self.recent_sessions_table.setObjectName("analysisTable")
        self.recent_sessions_table.setColumnCount(8)
        self.recent_sessions_table.setHorizontalHeaderLabels(
            [
                "Date",
                "Workout",
                "Routine",
                "Duration",
                "Effort",
                "Sets",
                "Volume",
                "Notes",
            ]
        )
        self.recent_sessions_table.verticalHeader().setVisible(False)
        self.recent_sessions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recent_sessions_table.setSelectionMode(QTableWidget.NoSelection)
        self.recent_sessions_table.setAlternatingRowColors(True)
        self.recent_sessions_table.setMinimumHeight(260)

        header = self.recent_sessions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.Stretch)

        self.layout.addWidget(self.recent_sessions_table)

    def _build_volume_by_exercise_table(self) -> None:
        self.layout.addWidget(self._create_section_title("Volume by Exercise Detail"))

        self.volume_by_exercise_table = QTableWidget()
        self.volume_by_exercise_table.setObjectName("analysisTable")
        self.volume_by_exercise_table.setColumnCount(4)
        self.volume_by_exercise_table.setHorizontalHeaderLabels(
            [
                "Exercise",
                "Sets",
                "Reps",
                "Volume",
            ]
        )
        self.volume_by_exercise_table.verticalHeader().setVisible(False)
        self.volume_by_exercise_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.volume_by_exercise_table.setSelectionMode(QTableWidget.NoSelection)
        self.volume_by_exercise_table.setAlternatingRowColors(True)
        self.volume_by_exercise_table.setMinimumHeight(260)

        header = self.volume_by_exercise_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.layout.addWidget(self.volume_by_exercise_table)

    def refresh_data(self) -> None:
        """Refresh workout summary cards and tables."""
        metrics = get_workout_summary_metrics()
        recent_sessions = get_recent_workout_sessions(limit=10)
        volume_by_exercise = get_volume_by_exercise()

        self._update_summary_cards(metrics)
        self.volume_by_exercise_chart.plot_volume_by_exercise(volume_by_exercise)
        self._update_recent_sessions_table(recent_sessions)
        self._update_volume_by_exercise_table(volume_by_exercise)

    def _update_summary_cards(self, metrics: dict) -> None:
        self.total_sessions_card.set_content(str(metrics["total_sessions"]))
        self.weekly_sessions_card.set_content(str(metrics["weekly_sessions"]))
        self.total_sets_card.set_content(str(metrics["total_sets"]))

        self.total_volume_card.set_content(
            f"{metrics['total_volume_kg']:.1f}",
            "kg",
        )

        average_duration = metrics["average_duration_minutes"]
        if average_duration is None:
            self.average_duration_card.set_content("-")
        else:
            self.average_duration_card.set_content(
                f"{average_duration:.1f}",
                "minutes",
            )

        most_recent = metrics["most_recent_workout"]
        if most_recent is None:
            self.recent_workout_card.set_content("-")
        else:
            workout_label = (
                most_recent.get("routine")
                or most_recent.get("workout_type")
                or "Workout"
            )
            started_at = most_recent["started_at"].strftime("%Y-%m-%d")
            self.recent_workout_card.set_content(workout_label, started_at)

        self.total_sessions_card.set_variant("neutral")
        self.weekly_sessions_card.set_variant("success")
        self.total_sets_card.set_variant("neutral")
        self.total_volume_card.set_variant("success")
        self.average_duration_card.set_variant("neutral")
        self.recent_workout_card.set_variant("neutral")

    def _update_recent_sessions_table(self, recent_sessions: list[dict]) -> None:
        self.recent_sessions_table.setRowCount(len(recent_sessions))

        for row_index, workout_session in enumerate(recent_sessions):
            started_at = workout_session["started_at"].strftime("%Y-%m-%d %H:%M")

            duration = workout_session["duration_minutes"]
            duration_text = "-" if duration is None else f"{duration:.1f} min"

            effort = workout_session["perceived_effort"]
            effort_text = "-" if effort is None else str(effort)

            volume = workout_session["total_volume_kg"]
            volume_text = f"{volume:.1f} kg"

            values = [
                started_at,
                workout_session["workout_type"] or "-",
                workout_session["routine"] or "-",
                duration_text,
                effort_text,
                str(workout_session["set_count"]),
                volume_text,
                workout_session["notes"] or "",
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                if column_index == 7:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft
                        | Qt.AlignmentFlag.AlignVCenter
                    )

                self.recent_sessions_table.setItem(
                    row_index,
                    column_index,
                    item,
                )

    def _update_volume_by_exercise_table(self, volume_by_exercise: list[dict]) -> None:
        self.volume_by_exercise_table.setRowCount(len(volume_by_exercise))

        for row_index, row in enumerate(volume_by_exercise):
            values = [
                row["exercise_name"],
                str(row["total_sets"]),
                str(row["total_reps"]),
                f"{row['total_volume_kg']:.1f} kg",
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)

                if column_index == 0:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                self.volume_by_exercise_table.setItem(
                    row_index,
                    column_index,
                    item,
                )

    def handle_import_csv(self) -> None:
        """Import workout CSV data and refresh the tab."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Workout CSV",
            str(Path.home()),
            "CSV Files (*.csv)",
        )

        if not file_path:
            return

        try:
            counts = import_workout_csv(file_path)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Import failed",
                f"Could not import workout CSV:\n{exc}",
            )
            return

        QMessageBox.information(
            self,
            "Import complete",
            (
                f"Imported {counts['sessions']} sessions and "
                f"{counts['sets']} sets.\n"
                f"Skipped {counts['skipped_sets']} duplicate sets."
            ),
        )

        self.refresh_data()

    def handle_clear_imported_workouts(self) -> None:
        """Clear imported workout sessions and sets after confirmation."""
        response = QMessageBox.warning(
            self,
            "Clear imported workouts",
            (
                "This will delete imported workout sessions and workout sets.\n\n"
                "Your exercise catalogue and workout routines will be kept.\n\n"
                "Continue?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if response != QMessageBox.Yes:
            return

        try:
            counts = clear_imported_workout_data()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Clear failed",
                f"Could not clear imported workout data:\n{exc}",
            )
            return

        QMessageBox.information(
            self,
            "Imported workouts cleared",
            (
                f"Deleted {counts['sessions']} imported sessions and "
                f"{counts['sets']} workout sets."
            ),
        )

        self.refresh_data()
