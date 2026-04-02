from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from datetime import date, datetime, timedelta
from statistics import mean
from pathlib import Path
import json

from app.services.activity.analysis import get_daily_activity

CHART_BG = "#1E1E1E"
CHART_TEXT = "#F0F0F0"
CHART_GRID = "#444444"
CHART_SPINE = "#888888"
LINE_COLOUR = "#F5F5F5"
ACCENT_GREEN = "#43A047"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ACTIVITY_SYNC_PATH = PROJECT_ROOT / "data" / "activity_sync.json"


def save_activity_last_synced(timestamp: datetime) -> None:
    """Persist the most recent successful activity sync timestamp."""
    ACTIVITY_SYNC_PATH.parent.mkdir(parents=True, exist_ok=True)
    ACTIVITY_SYNC_PATH.write_text(
        json.dumps({"last_synced": timestamp.isoformat()}, indent=2),
        encoding="utf-8",
    )


def load_activity_last_synced() -> datetime | None:
    """Load the most recent successful activity sync timestamp, if present."""
    if not ACTIVITY_SYNC_PATH.exists():
        return None

    try:
        payload = json.loads(ACTIVITY_SYNC_PATH.read_text(encoding="utf-8"))
        raw_value = payload.get("last_synced")

        if not raw_value:
            return None

        return datetime.fromisoformat(raw_value)

    except (json.JSONDecodeError, ValueError, TypeError):
        return None

def apply_chart_theme(fig: Figure, ax) -> None:
    fig.patch.set_facecolor(CHART_BG)
    ax.set_facecolor(CHART_BG)
    ax.tick_params(axis="x", colors=CHART_TEXT)
    ax.tick_params(axis="y", colors=CHART_TEXT)

    for spine in ax.spines.values():
        spine.set_color(CHART_SPINE)

    ax.grid(True, color=CHART_GRID, alpha=0.5)


def rolling_average(values: list[float], window: int = 7) -> list[float]:
    result = []

    for i in range(len(values)):
        start = max(0, i - window + 1)
        window_values = values[start : i + 1]
        result.append(mean(window_values))

    return result


def calculate_step_streaks(
    rows: list[dict],
    goal_steps: int = 10_000,
) -> tuple[int, int]:
    """
    Return (current_streak, longest_streak) for consecutive days meeting the goal.

    Assumes at most one row per day and uses activity_date.
    """
    if not rows:
        return 0, 0

    sorted_rows = sorted(rows, key=lambda row: row["activity_date"])
    qualifying_dates = [
        row["activity_date"]
        for row in sorted_rows
        if row["steps"] >= goal_steps
    ]

    if not qualifying_dates:
        return 0, 0

    longest_streak = 0
    current_run = 0
    previous_date = None

    for activity_date in qualifying_dates:
        if previous_date is None:
            current_run = 1
        elif (activity_date - previous_date).days == 1:
            current_run += 1
        else:
            current_run = 1

        longest_streak = max(longest_streak, current_run)
        previous_date = activity_date

    latest_date = sorted_rows[-1]["activity_date"]
    current_streak = 0
    qualifying_set = set(qualifying_dates)

    check_date = latest_date
    while check_date in qualifying_set:
        current_streak += 1
        check_date = check_date - timedelta(days=1)

    return current_streak, longest_streak


def format_relative_timestamp(timestamp: datetime, now: datetime | None = None) -> str:
    """Return a human-friendly relative time string."""
    now = now or datetime.now()
    delta = now - timestamp

    total_seconds = int(delta.total_seconds())

    if total_seconds < 0:
        return "just now"

    if total_seconds < 60:
        return "just now"

    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"

    hours = minutes // 60
    if hours < 24:
        return f"{hours} hr ago"

    days = hours // 24
    if days < 7:
        return f"{days} day{'s' if days != 1 else ''} ago"

    return timestamp.strftime("%Y-%m-%d")


class ActivityTrendChart(FigureCanvasQTAgg):
    def __init__(self) -> None:
        self.figure = Figure(figsize=(6, 4.5))
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)

    def plot_steps(self, activity_rows: list[dict]) -> None:
        self.ax.clear()
        apply_chart_theme(self.figure, self.ax)

        self.ax.set_title("Daily Steps", color=CHART_TEXT)
        self.ax.set_ylabel("Steps", color=CHART_TEXT)

        if not activity_rows:
            self.ax.text(
                0.5,
                0.5,
                "No activity data available",
                ha="center",
                va="center",
                color=CHART_TEXT,
            )
            self.ax.set_axis_off()
            self.draw()
            return

        dates = [row["activity_date"] for row in activity_rows]
        steps = [row["steps"] for row in activity_rows]

        rolling_avg = rolling_average(steps, window=7)

        # --- main line ---
        colors = [
            ACCENT_GREEN if value >= 10000 else "#BBBBBB"
            for value in steps
        ]

        # subtle baseline line
        self.ax.plot(
            dates,
            steps,
            color="#888888",
            alpha=0.4,
            linewidth=1,
        )

        # coloured points
        self.ax.scatter(
            dates,
            steps,
            c=colors,
            s=30,
            label="Daily Steps",
        )

        # --- rolling average ---
        self.ax.plot(
            dates,
            rolling_avg,
            color="#FFFFFF",
            linewidth=2.5,
            alpha=0.95,
            label="7-Day Average",
        )

        # --- 10k goal line ---
        self.ax.axhline(
            10000,
            color=ACCENT_GREEN,
            linestyle="--",
            linewidth=1.2,
            label="10k Target",
        )

        legend = self.ax.legend(facecolor=CHART_BG, edgecolor=CHART_SPINE)
        for text in legend.get_texts():
            text.set_color(CHART_TEXT)

        self.figure.autofmt_xdate()
        self.figure.subplots_adjust(bottom=0.20)
        self.draw()

class ActivityTab(QWidget):
    CARD_BASE_STYLE = """
        font-size: 15px;
        font-weight: 700;
        padding: 10px 16px;
        border: 1px solid #2F2F2F;
        border-radius: 10px;
    """

    def __init__(self) -> None:
        super().__init__()

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(20)
        self.layout.setContentsMargins(16, 16, 16, 24)

        self._build_toolbar()
        self._build_summary_panel()
        self._build_chart()
        self._build_table()

        self._set_last_synced_label(load_activity_last_synced())
        self.load_activity()

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

    def _build_toolbar(self) -> None:
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("secondaryAction")
        self.refresh_button.clicked.connect(self.handle_refresh_activity)

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
        self.time_filter.currentIndexChanged.connect(self.load_activity)
        self.time_filter.setFixedWidth(140)

        self.last_synced_label = QLabel("Last synced: Never")
        self.last_synced_label.setObjectName("statusLabel")

        toolbar.addStretch()
        toolbar.addWidget(self.refresh_button)
        toolbar.addSpacing(12)
        toolbar.addWidget(self._create_toolbar_label("Time Range"))
        toolbar.addWidget(self.time_filter)
        toolbar.addSpacing(16)
        toolbar.addWidget(self.last_synced_label)
        toolbar.addStretch()

        self.layout.addLayout(toolbar)

    def _build_summary_panel(self) -> None:
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(12)
        summary_layout.setContentsMargins(0, 8, 0, 8)

        self.goal_days_label = self._create_summary_card("10k Goal Days\n-")
        self.avg_steps_label = self._create_summary_card("Average Steps\n-")
        self.best_day_label = self._create_summary_card("Best Day\n-")
        self.current_streak_label = self._create_summary_card("Current Streak\n-")
        self.longest_streak_label = self._create_summary_card("Longest Streak\n-")

        cards = [
            self.goal_days_label,
            self.avg_steps_label,
            self.best_day_label,
            self.current_streak_label,
            self.longest_streak_label,
        ]

        summary_layout.addStretch()
        for card in cards:
            summary_layout.addWidget(card)
        summary_layout.addStretch()

        self.layout.addLayout(summary_layout)

    def _build_chart(self) -> None:
        self.chart = ActivityTrendChart()
        self.chart.setMinimumHeight(320)
        self.layout.addWidget(self.chart)

    def _build_table(self) -> None:
        self.layout.addWidget(self._create_section_title("Daily Activity"))

        self.table = QTableWidget()
        self.table.setObjectName("analysisTable")
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Date", "Steps", "Source"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setMinimumHeight(260)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.layout.addWidget(self.table)

    def _get_activity_rows(self) -> list[dict]:
        """Fetch daily activity rows from the activity service."""
        return get_daily_activity()

    def _filter_activity_rows(self, rows: list[dict]) -> list[dict]:
        if not rows:
            return rows

        selected_time_range = self.time_filter.currentText()
        if selected_time_range == "All Time":
            return rows

        latest_date = max(row["activity_date"] for row in rows)

        if selected_time_range == "Last 7 Days":
            cutoff = latest_date - timedelta(days=7)
        elif selected_time_range == "Last 14 Days":
            cutoff = latest_date - timedelta(days=14)
        elif selected_time_range == "Last 30 Days":
            cutoff = latest_date - timedelta(days=30)
        elif selected_time_range == "Last 90 Days":
            cutoff = latest_date - timedelta(days=90)
        else:
            return rows

        return [row for row in rows if row["activity_date"] >= cutoff]

    def _update_summary(self, rows: list[dict]) -> None:
        if not rows:
            self.goal_days_label.setText("10k Goal Days\n0")
            self.avg_steps_label.setText("Average Steps\n-")
            self.best_day_label.setText("Best Day\n-")
            self.current_streak_label.setText("Current Streak\n0")
            self.longest_streak_label.setText("Longest Streak\n0")
            return

        total_steps = sum(row["steps"] for row in rows)
        avg_steps = total_steps / len(rows)
        best_day = max(row["steps"] for row in rows)
        goal_days = sum(1 for row in rows if row["steps"] >= 10000)
        current_streak, longest_streak = calculate_step_streaks(rows)

        self.goal_days_label.setText(f"10k Goal Days\n{goal_days}")
        self.avg_steps_label.setText(f"Average Steps\n{avg_steps:,.0f}")
        self.best_day_label.setText(f"Best Day\n{best_day:,.0f}")
        self.current_streak_label.setText(f"Current Streak\n{current_streak}")
        self.longest_streak_label.setText(f"Longest Streak\n{longest_streak}")

        if current_streak > 0:
            self.current_streak_label.setStyleSheet(
                self.CARD_BASE_STYLE + "background-color: #43A047; color: #F5F5F5;"
            )
        else:
            self.current_streak_label.setStyleSheet("")

        if longest_streak >= 7:
            self.longest_streak_label.setStyleSheet(
                self.CARD_BASE_STYLE + "background-color: #C62828; color: #F5F5F5;"
            )
        else:
            self.longest_streak_label.setStyleSheet("")

    def _populate_table(self, rows: list[dict]) -> None:
        self.table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            date_item = QTableWidgetItem(row["activity_date"].strftime("%Y-%m-%d"))
            steps_item = QTableWidgetItem(f"{row['steps']:,}")
            source_item = QTableWidgetItem(str(row["source"]))

            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            steps_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row_index, 0, date_item)
            self.table.setItem(row_index, 1, steps_item)
            self.table.setItem(row_index, 2, source_item)

    def load_activity(self) -> None:
        rows = self._get_activity_rows()
        rows = self._filter_activity_rows(rows)

        self._update_summary(rows)
        self.chart.plot_steps(rows)
        self._populate_table(rows)

    def handle_refresh_activity(self) -> None:
        """Pull latest Fitbit activity into the database, then refresh the UI."""
        try:
            from app.services.activity.fitbit_importer import FitbitImporter

            importer = FitbitImporter()

            end_date = date.today()
            start_date = end_date - timedelta(days=30)

            importer.import_daily_steps(start_date, end_date)

            self._set_last_synced_now()
            self.load_activity()

        except Exception as exc:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(
                self,
                "Activity refresh failed",
                f"Could not refresh Fitbit activity:\n{exc}",
            )

    def _set_last_synced_label(self, timestamp: datetime | None) -> None:
        """Render the last synced label from a timestamp or fallback state."""
        if timestamp is None:
            self.last_synced_label.setText("Last synced: Never")
            self.last_synced_label.setToolTip("")
            return

        relative_text = format_relative_timestamp(timestamp)
        full_text = timestamp.strftime("%Y-%m-%d %H:%M")

        self.last_synced_label.setText(f"Last synced: {relative_text}")
        self.last_synced_label.setToolTip(full_text)


    def _set_last_synced_now(self) -> None:
        """Persist and display the current local timestamp as last synced."""
        timestamp = datetime.now()
        save_activity_last_synced(timestamp)
        self._set_last_synced_label(timestamp)
