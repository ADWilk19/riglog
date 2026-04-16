from PySide6.QtCore import QObject, Qt, QThread, Signal, QTimer
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
    QMessageBox,
    QInputDialog,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from datetime import date, datetime, timedelta
from statistics import mean
from pathlib import Path
import json

from app.services.activity.analysis import get_daily_activity, get_activity_summary

from app.services.activity.fitbit_exceptions import (
    FitbitAuthError,
    FitbitAPIError,
    FitbitNetworkError,
    FitbitRateLimitError,
)

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


def aggregate_weekly_steps(rows: list[dict]) -> list[dict]:
    """
    Aggregate daily activity rows into weekly totals.

    Weeks are labelled by their Monday start date.
    """
    if not rows:
        return []

    weekly_totals: dict[date, int] = {}

    for row in rows:
        activity_date = row["activity_date"]
        week_start = activity_date - timedelta(days=activity_date.weekday())
        weekly_totals[week_start] = weekly_totals.get(week_start, 0) + row["steps"]

    return [
        {
            "week_start": week_start,
            "steps": weekly_totals[week_start],
        }
        for week_start in sorted(weekly_totals)
    ]


class ActivityRefreshWorker(QObject):
    finished = Signal(int)
    auth_error = Signal()
    rate_limit_error = Signal()
    network_error = Signal()
    api_error = Signal(str)
    unexpected_error = Signal(str)

    def __init__(self, start_date: date, end_date: date) -> None:
        super().__init__()
        self.start_date = start_date
        self.end_date = end_date

    def run(self) -> None:
        from app.services.activity.fitbit_exceptions import (
            FitbitAPIError,
            FitbitAuthError,
            FitbitNetworkError,
            FitbitRateLimitError,
        )
        from app.services.activity.fitbit_importer import FitbitImporter

        try:
            importer = FitbitImporter()
            rows_written = importer.import_daily_steps(
                self.start_date,
                self.end_date,
            )
            self.finished.emit(rows_written)

        except FitbitAuthError:
            self.auth_error.emit()

        except FitbitRateLimitError:
            self.rate_limit_error.emit()

        except FitbitNetworkError:
            self.network_error.emit()

        except FitbitAPIError as exc:
            self.api_error.emit(str(exc))

        except Exception as exc:
            self.unexpected_error.emit(str(exc))


class ActivityTrendChart(FigureCanvasQTAgg):
    def __init__(self) -> None:
        self.figure = Figure(figsize=(6, 4.5))
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)

        self.scatter = None
        self.dates: list = []
        self.steps: list[int] = []
        self.annot = None
        self.bar_patches = []
        self.week_labels: list = []
        self.weekly_steps: list[int] = []
        self.hover_cid = self.mpl_connect("motion_notify_event", self._on_hover)

    def _on_hover(self, event) -> None:
        if self.annot is None:
            return

        if event.inaxes != self.ax:
            if self.annot.get_visible():
                self.annot.set_visible(False)

                if self.scatter is not None:
                    self.scatter.set_sizes([30] * len(self.steps))

                for bar in self.bar_patches:
                    bar.set_linewidth(0)

                self.draw_idle()
            return

        # --- daily mode: scatter hover ---
        if self.scatter is not None:
            contains, index_data = self.scatter.contains(event)

            if contains:
                index = index_data["ind"][0]
                hovered_date = self.dates[index]
                hovered_steps = self.steps[index]

                self.annot.xy = (hovered_date, hovered_steps)
                self.annot.set_text(
                    f"{hovered_date.strftime('%Y-%m-%d')}\n{hovered_steps:,} steps"
                )

                if event.x > self.figure.bbox.width * 0.75:
                    self.annot.set_position((-80, 10))
                else:
                    self.annot.set_position((10, 10))

                self.annot.set_visible(True)

                self.scatter.set_sizes([
                    55 if i == index else 30
                    for i in range(len(self.steps))
                ])

                self.draw_idle()
                return
            else:
                self.scatter.set_sizes([30] * len(self.steps))

        # --- weekly mode: bar hover ---
        for i, bar in enumerate(self.bar_patches):
            contains, _ = bar.contains(event)

            if contains:
                x = bar.get_x() + bar.get_width() / 2
                y = bar.get_height()

                week_start = self.week_labels[i]
                week_end = week_start + timedelta(days=6)
                weekly_total = self.weekly_steps[i]

                self.annot.xy = (x, y)
                self.annot.set_text(
                    f"{week_start.strftime('%d %b')}–{week_end.strftime('%d %b')}\n{weekly_total:,} steps"
                )

                top_threshold = self.ax.get_ylim()[1] * 0.75
                is_near_top = y > top_threshold
                is_near_right = event.x > self.figure.bbox.width * 0.75

                if is_near_right:
                    self.annot.set_position((-110, -40) if is_near_top else (-110, 10))
                else:
                    self.annot.set_position((10, -40) if is_near_top else (10, 10))

                self.annot.set_visible(True)

                for j, other_bar in enumerate(self.bar_patches):
                    if j == i:
                        other_bar.set_edgecolor("#FFFFFF")
                        other_bar.set_linewidth(1.2)
                    else:
                        other_bar.set_linewidth(0)

                self.draw_idle()
                return

        # --- nothing hovered ---
        if self.annot.get_visible():
            self.annot.set_visible(False)

            if self.scatter is not None:
                self.scatter.set_sizes([30] * len(self.steps))

            for bar in self.bar_patches:
                bar.set_linewidth(0)

            self.draw_idle()

    def plot_steps(self, activity_rows: list[dict], chart_view: str = "Daily") -> None:
        self.ax.clear()
        apply_chart_theme(self.figure, self.ax)

        self.scatter = None
        self.dates = []
        self.steps = []
        self.annot = None
        self.bar_patches = []
        self.week_labels = []
        self.weekly_steps = []

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

        if chart_view == "Weekly":
            self._plot_weekly_steps(activity_rows)
        else:
            self._plot_daily_steps(activity_rows)

        legend = self.ax.legend(facecolor=CHART_BG, edgecolor=CHART_SPINE)
        for text in legend.get_texts():
            text.set_color(CHART_TEXT)

        self.figure.autofmt_xdate()
        self.figure.subplots_adjust(bottom=0.20)
        self.draw()

    def _plot_daily_steps(self, activity_rows: list[dict]) -> None:
        self.ax.set_title("Daily Steps", color=CHART_TEXT)
        self.ax.set_ylabel("Steps", color=CHART_TEXT)

        self.dates = [row["activity_date"] for row in activity_rows]
        self.steps = [row["steps"] for row in activity_rows]

        rolling_avg = rolling_average(self.steps, window=7)

        colors = [
            ACCENT_GREEN if value >= 10000 else "#BBBBBB"
            for value in self.steps
        ]

        self.ax.plot(
            self.dates,
            self.steps,
            color="#888888",
            alpha=0.4,
            linewidth=1,
        )

        self.scatter = self.ax.scatter(
            self.dates,
            self.steps,
            c=colors,
            s=30,
            label="Daily Steps",
        )

        self.ax.plot(
            self.dates,
            rolling_avg,
            color="#FFFFFF",
            linewidth=2.5,
            alpha=0.95,
            label="7-Day Average",
        )

        self.ax.axhline(
            10000,
            color=ACCENT_GREEN,
            linestyle="--",
            linewidth=1.2,
            label="10k Target",
        )

        self.annot = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(10, 10),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="#2A2A2A", ec="#888888", alpha=0.95),
            color="#F0F0F0",
        )
        self.annot.set_visible(False)

    def _plot_weekly_steps(self, activity_rows: list[dict]) -> None:
        self.ax.set_title("Weekly Steps", color=CHART_TEXT)
        self.ax.set_ylabel("Total Steps", color=CHART_TEXT)

        weekly_rows = aggregate_weekly_steps(activity_rows)

        self.week_labels = [row["week_start"] for row in weekly_rows]
        self.weekly_steps = [row["steps"] for row in weekly_rows]

        colors = [
            ACCENT_GREEN if value >= 70000 else "#BBBBBB"
            for value in self.weekly_steps
        ]

        bars = self.ax.bar(
            self.week_labels,
            self.weekly_steps,
            color=colors,
            width=6,
            label="Weekly Total",
        )

        self.bar_patches = list(bars)

        self.ax.axhline(
            70000,
            color=ACCENT_GREEN,
            linestyle="--",
            linewidth=1.2,
            label="10k/day Equivalent",
        )

        self.annot = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(10, 10),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="#262626", ec="#888888", alpha=0.95),
            color="#F0F0F0",
        )
        self.annot.set_visible(False)


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

        self.sync_status_timer = QTimer(self)
        self.sync_status_timer.setSingleShot(True)
        self.sync_status_timer.timeout.connect(self._clear_sync_status)

        self.refresh_thread = None
        self.refresh_worker = None

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
        label.setMinimumHeight(84)
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

        self.sync_status_label = QLabel("")
        self.sync_status_label.setObjectName("statusLabel")
        self.sync_status_label.setMinimumWidth(140)
        self.sync_status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.chart_view_filter = QComboBox()
        self.chart_view_filter.addItems(["Daily", "Weekly"])
        self.chart_view_filter.currentIndexChanged.connect(self.load_activity)
        self.chart_view_filter.setFixedWidth(120)

        toolbar.addStretch()
        toolbar.addWidget(self.refresh_button)
        toolbar.addSpacing(12)

        toolbar.addWidget(self._create_toolbar_label("Chart View"))
        toolbar.addWidget(self.chart_view_filter)
        toolbar.addSpacing(12)

        toolbar.addWidget(self._create_toolbar_label("Time Range"))
        toolbar.addWidget(self.time_filter)
        toolbar.addSpacing(16)

        toolbar.addWidget(self.last_synced_label)
        toolbar.addWidget(self.sync_status_label)
        toolbar.addSpacing(12)
        toolbar.addStretch()

        self.layout.addLayout(toolbar)

    def _build_summary_panel(self) -> None:
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(12)
        summary_layout.setContentsMargins(0, 8, 0, 8)

        self.goal_days_label = self._create_summary_card("Goal Days (7d)\n-")
        self.goal_days_label.setToolTip(
            "Number of days in the last 7 recorded days where steps met or exceeded the 10,000-step target."
        )

        self.goal_adherence_label = self._create_summary_card("Goal Adherence\n-")
        self.goal_adherence_label.setToolTip(
            "Percentage of the last 7 recorded days where steps met or exceeded the 10,000-step target."
        )

        self.avg_steps_label = self._create_summary_card("Average Steps\n-")
        self.avg_steps_label.setToolTip(
            "Average daily step count across the last 7 recorded days."
        )

        self.change_label = self._create_summary_card("7-Day Change\n-")
        self.change_label.setToolTip(
            "Change in total steps for the last 7 recorded days compared with the previous 7 recorded days."
        )

        self.best_day_label = self._create_summary_card("Best Day\n-")
        self.best_day_label.setToolTip(
            "Highest single recorded daily step count in the current activity dataset."
        )

        self.current_streak_label = self._create_summary_card("Current Streak\n-")
        self.current_streak_label.setToolTip(
            "Number of consecutive recorded days, ending with the latest day, where steps met or exceeded the 10,000-step target."
        )

        self.longest_streak_label = self._create_summary_card("Longest Streak\n-")
        self.longest_streak_label.setToolTip(
            "Longest run of consecutive recorded days where steps met or exceeded the 10,000-step target."
        )

        cards = [
            self.goal_days_label,
            self.goal_adherence_label,
            self.avg_steps_label,
            self.change_label,
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
            self.goal_days_label.setText("Goal Days (7d)\n0")
            self.goal_adherence_label.setText("Goal Adherence\n-")
            self.avg_steps_label.setText("Average Steps\n-")
            self.best_day_label.setText("Best Day\n-")
            self.current_streak_label.setText("Current Streak\n0")
            self.longest_streak_label.setText("Longest Streak\n0")
            self.change_label.setText("7-Day Change\n-")
            self.goal_adherence_label.setStyleSheet("")
            self.change_label.setStyleSheet("")
            self.current_streak_label.setStyleSheet("")
            self.longest_streak_label.setStyleSheet("")
            return

        summary = get_activity_summary(target_steps=10000)

        if summary["has_previous_period"]:
            if summary["direction"] == "up":
                self.change_label.setText(
                    f"7-Day Change\n↑ {abs(summary['vs_previous_7_pct']):.1f}%"
                )
            elif summary["direction"] == "down":
                self.change_label.setText(
                    f"7-Day Change\n↓ {abs(summary['vs_previous_7_pct']):.1f}%"
                )
            else:
                self.change_label.setText("7-Day Change\nNo change")
        else:
            self.change_label.setText("7-Day Change\n-")

        if summary["has_previous_period"]:
            if summary["direction"] == "up":
                self.change_label.setStyleSheet(
                    self.CARD_BASE_STYLE + "background-color: #1B5E20; color: #F5F5F5;"
                )
            elif summary["direction"] == "down":
                self.change_label.setStyleSheet(
                    self.CARD_BASE_STYLE + "background-color: #7F1D1D; color: #F5F5F5;"
                )
            else:
                self.change_label.setStyleSheet("")
        else:
            self.change_label.setStyleSheet("")

        _, longest_streak = calculate_step_streaks(rows)

        self.goal_adherence_label.setText(
            f"Goal Adherence\n{summary['goal_days']} / 7 ({summary['goal_adherence_pct']:.1f}%)"
        )
        self.goal_days_label.setText(f"Goal Days (7d)\n{summary['goal_days']}")
        self.avg_steps_label.setText(
            f"Average Steps\n{summary['avg_steps_last_7']:,}"
        )
        self.best_day_label.setText(
            f"Best Day\n{summary['best_day_steps']:,}\n{summary['best_day_date']}"
        )
        self.current_streak_label.setText(
            f"Current Streak\n{summary['streak_days']}"
        )
        self.longest_streak_label.setText(f"Longest Streak\n{longest_streak}")

        if summary["goal_adherence_pct"] >= 70:
            self.goal_adherence_label.setStyleSheet(
                self.CARD_BASE_STYLE + "background-color: #1B5E20; color: #F5F5F5;"
            )
        else:
            self.goal_adherence_label.setStyleSheet("")

        if summary["streak_days"] > 0:
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

        chart_view = self.chart_view_filter.currentText()
        self.chart.plot_steps(rows, chart_view=chart_view)

        self._populate_table(rows)

    def handle_refresh_activity(self) -> None:
        """Start a background Fitbit refresh without blocking the UI."""
        if self.refresh_thread is not None and self.refresh_thread.isRunning():
            return

        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Refreshing...")

        self._set_sync_status("Refreshing...", "#BBBBBB", timeout_ms=0)

        self.refresh_thread = QThread()
        self.refresh_worker = ActivityRefreshWorker(start_date, end_date)
        self.refresh_worker.moveToThread(self.refresh_thread)

        self.refresh_thread.started.connect(self.refresh_worker.run)

        self.refresh_worker.finished.connect(self._on_refresh_success)
        self.refresh_worker.auth_error.connect(self._on_refresh_auth_error)
        self.refresh_worker.rate_limit_error.connect(self._on_refresh_rate_limit_error)
        self.refresh_worker.network_error.connect(self._on_refresh_network_error)
        self.refresh_worker.api_error.connect(self._on_refresh_api_error)
        self.refresh_worker.unexpected_error.connect(self._on_refresh_unexpected_error)

        self.refresh_worker.finished.connect(self.refresh_thread.quit)
        self.refresh_worker.auth_error.connect(self.refresh_thread.quit)
        self.refresh_worker.rate_limit_error.connect(self.refresh_thread.quit)
        self.refresh_worker.network_error.connect(self.refresh_thread.quit)
        self.refresh_worker.api_error.connect(self.refresh_thread.quit)
        self.refresh_worker.unexpected_error.connect(self.refresh_thread.quit)

        self.refresh_thread.finished.connect(self._cleanup_refresh_thread)

        self.refresh_thread.start()

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

    def _handle_fitbit_auth_error(self) -> None:
        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Warning)
        message_box.setWindowTitle("Fitbit connection expired")
        message_box.setText(
            "Your Fitbit session has expired or been revoked. "
            "Please reconnect Fitbit to continue syncing activity data."
        )

        reconnect_button = message_box.addButton("Reconnect Fitbit", QMessageBox.AcceptRole)
        message_box.addButton(QMessageBox.Cancel)
        message_box.exec()

        if message_box.clickedButton() is reconnect_button:
            self._reconnect_fitbit()

    def _show_fitbit_reconnect_instructions(self) -> None:
        QMessageBox.information(
            self,
            "Reconnect Fitbit",
            "Please run your Fitbit auth setup flow to reconnect the account, "
            "then return to RigLog and press Refresh again.",
        )

    def _reconnect_fitbit(self) -> None:
        import webbrowser
        from PySide6.QtWidgets import QInputDialog, QMessageBox

        from app.services.activity.fitbit_auth import (
            get_authorization_url,
            fetch_and_store_token,
        )

        auth_url = get_authorization_url()
        webbrowser.open(auth_url)

        redirect_url, ok = QInputDialog.getText(
            self,
            "Reconnect Fitbit",
            "After approving Fitbit access in your browser,\n"
            "paste the full redirect URL here:",
        )

        if not ok or not redirect_url.strip():
            return

        try:
            fetch_and_store_token(redirect_url.strip())

            QMessageBox.information(
                self,
                "Fitbit reconnected",
                "Fitbit was reconnected successfully. Sync will now retry.",
            )

            self.handle_refresh_activity()

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Reconnect failed",
                f"RigLog could not complete Fitbit reconnection:\n{exc}",
            )

    def _on_refresh_success(self, rows_written: int) -> None:
        self._set_last_synced_now()
        self.load_activity()
        self._set_sync_status("Sync complete", "#43A047")

    def _on_refresh_auth_error(self) -> None:
        self._set_sync_status("Reconnect required", "#FB8C00")
        self._handle_fitbit_auth_error()

    def _on_refresh_rate_limit_error(self) -> None:
        self._set_sync_status("Sync failed", "#E53935")
        QMessageBox.warning(
            self,
            "Fitbit temporarily unavailable",
            "Fitbit rate-limited the request. Please wait a moment and try again.",
        )

    def _on_refresh_network_error(self) -> None:
        self._set_sync_status("Sync failed", "#E53935")
        QMessageBox.warning(
            self,
            "Network error",
            "RigLog could not reach Fitbit. Check your connection and try again.",
        )

    def _on_refresh_api_error(self, message: str) -> None:
        self._set_sync_status("Sync failed", "#E53935")
        QMessageBox.critical(
            self,
            "Fitbit error",
            message,
        )

    def _on_refresh_unexpected_error(self, message: str) -> None:
        self._set_sync_status("Sync failed", "#E53935")
        QMessageBox.critical(
            self,
            "Activity refresh failed",
            f"An unexpected error occurred while refreshing activity data:\n{message}",
        )

    def _cleanup_refresh_thread(self) -> None:
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh")

        if self.refresh_worker is not None:
            self.refresh_worker.deleteLater()
            self.refresh_worker = None

        if self.refresh_thread is not None:
            self.refresh_thread.deleteLater()
            self.refresh_thread = None

    def _set_sync_status(
        self,
        message: str,
        colour: str = "#BBBBBB",
        timeout_ms: int = 4000,
    ) -> None:
        self.sync_status_label.setText(message)
        self.sync_status_label.setStyleSheet(
            f"color: {colour}; font-size: 13px; font-weight: 600;"
        )

        self.sync_status_timer.stop()
        if timeout_ms > 0:
            self.sync_status_timer.start(timeout_ms)

    def _clear_sync_status(self) -> None:
        self.sync_status_label.clear()
        self.sync_status_label.setStyleSheet("")
