from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QSizePolicy,
)

from collections.abc import Iterable

from app.core.modules import (
    DEFAULT_ENABLED_MODULE_KEYS,
    normalise_enabled_module_keys,
)

from app.core.settings import DEFAULT_STEP_TARGET

from app.db.database import SessionLocal
from app.db.models import GlucoseReading
from app.services.activity.analysis import (
    get_activity_summary_cards,
    get_daily_activity,
)
from app.services.workouts.analysis import get_workout_summary_metrics
from app.services.nutrition.analysis import get_nutrition_summary_metrics
from app.ui.widgets.summary_card import SummaryCard


class HomeTab(QWidget):
    def __init__(
            self,
            on_open_glucose=None,
            on_open_activity=None,
            on_open_workouts=None,
            on_open_nutrition=None,
            enabled_module_keys: Iterable[str] | None = None,
            step_target: int = DEFAULT_STEP_TARGET,
        ) -> None:
        super().__init__()

        self.on_open_glucose = on_open_glucose
        self.on_open_activity = on_open_activity
        self.on_open_workouts = on_open_workouts
        self.on_open_nutrition = on_open_nutrition

        self.step_target = step_target

        self.enabled_module_keys = (
            DEFAULT_ENABLED_MODULE_KEYS
            if enabled_module_keys is None
            else normalise_enabled_module_keys(enabled_module_keys)
        )

        self.summary_cards: dict[str, SummaryCard] = {}

        project_root = Path(__file__).resolve().parents[3]
        logo_path = (
            project_root
            / "assets"
            / "branding"
            / "logo_full.png"
        )

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(32, 28, 32, 32)
        main_layout.setSpacing(16)

        main_layout.addLayout(self._build_header(logo_path))
        main_layout.addSpacing(72)

        grid = self._build_summary_grid()

        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addLayout(grid)
        container.setLayout(container_layout)

        container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        container.setMaximumWidth(1600)

        main_layout.addWidget(
            container,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )
        main_layout.addStretch(1)

        self.setLayout(main_layout)
        self._refresh_card_data()

    def _build_header(self, logo_path: Path) -> QHBoxLayout:
        header_layout = QHBoxLayout()
        header_layout.setSpacing(20)

        logo_label = QLabel()
        logo_label.setStyleSheet("background: transparent;")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setFixedSize(110, 110)

        pixmap = QPixmap(str(logo_path))
        if not pixmap.isNull():
            logo_label.setPixmap(
                pixmap.scaled(
                    96,
                    96,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
        else:
            logo_label.setText("RigLog")

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        title_label = QLabel("RigLog")
        title_label.setStyleSheet(
            """
            QLabel {
                font-size: 28px;
                font-weight: 700;
                color: #F5F5F5;
            }
            """
        )

        subtitle_label = QLabel("Personal health analytics")
        subtitle_label.setStyleSheet(
            """
            QLabel {
                font-size: 14px;
                color: #A0A0A0;
            }
            """
        )

        tagline_label = QLabel(
            "One app. Multiple health signals. Clearer decisions."
        )
        tagline_label.setWordWrap(True)
        tagline_label.setStyleSheet(
            """
            QLabel {
                font-size: 13px;
                color: #CFCFCF;
                margin-top: 4px;
            }
            """
        )

        text_layout.addWidget(title_label)
        text_layout.addWidget(subtitle_label)
        text_layout.addWidget(tagline_label)
        text_layout.addStretch()

        header_layout.addWidget(logo_label, alignment=Qt.AlignTop)
        header_layout.addLayout(text_layout, stretch=1)

        return header_layout

    def _build_summary_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)

        card_definitions = {
            "glucose": {
                "title": "Glucose",
                "subtitle": "Checking readings",
                "callback": self.on_open_glucose,
            },
            "activity": {
                "title": "Activity",
                "subtitle": "Checking activity data",
                "callback": self.on_open_activity,
            },
            "workouts": {
                "title": "Workouts",
                "subtitle": "Checking workout data",
                "callback": self.on_open_workouts,
            },
            "nutrition": {
                "title": "Nutrition",
                "subtitle": "Checking meal logs",
                "callback": self.on_open_nutrition,
            },
        }

        enabled_count = len(self.enabled_module_keys)

        for index, module_key in enumerate(self.enabled_module_keys):
            definition = card_definitions[module_key]

            card = SummaryCard(
                title=definition["title"],
                value="Loading...",
                subtitle=definition["subtitle"],
                on_click=definition["callback"],
            )
            card.set_variant("primary")
            card.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            card.setMinimumHeight(110)

            self.summary_cards[module_key] = card

            # Preserve existing public attributes for enabled cards.
            setattr(
                self,
                f"{module_key}_card",
                card,
            )

            if enabled_count == 1:
                grid.addWidget(card, 0, 0, 1, 2)
            else:
                row = index // 2
                column = index % 2
                grid.addWidget(card, row, column)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        return grid

    def _refresh_card_data(self) -> None:
        if "glucose" in self.enabled_module_keys:
            session = SessionLocal()

            try:
                self._refresh_glucose_card(session)
            finally:
                session.close()

        if "activity" in self.enabled_module_keys:
            self._refresh_activity_card()

        if "workouts" in self.enabled_module_keys:
            self._refresh_workouts_card()

        if "nutrition" in self.enabled_module_keys:
            self._refresh_nutrition_card()

    def _refresh_glucose_card(self, session) -> None:
        reading_count = session.query(GlucoseReading).count()

        latest_reading = (
            session.query(GlucoseReading)
            .order_by(GlucoseReading.recorded_at.desc())
            .first()
        )

        if reading_count == 0 or latest_reading is None:
            self.glucose_card.set_content(
                "No readings",
                "Import Diabetes:M data"
            )
            return

        latest_date = latest_reading.recorded_at.strftime("%d %b %Y")

        self.glucose_card.set_content(
            f"{reading_count:,} readings",
            f"Latest reading: {latest_date}"
        )

    def _refresh_activity_card(self) -> None:
        rows = get_daily_activity()

        if not rows:
            self.activity_card.set_content(
                "No activity",
                "Sync Fitbit data",
            )
            return

        cards_data = get_activity_summary_cards(
            rows,
            target_steps=self.step_target,
        )

        card_map = {card["key"]: card for card in cards_data}
        goal_adherence_card = card_map.get("goal_adherence")

        if goal_adherence_card is None:
            self.activity_card.set_content(
                "Activity ready",
                "Open Activity dashboard",
            )
            return

        self.activity_card.set_content(
            goal_adherence_card.get("value", "-"),
            "7-day goal adherence",
        )

    def _refresh_workouts_card(self) -> None:
        metrics = get_workout_summary_metrics()

        total_sessions = metrics["total_sessions"]

        if total_sessions == 0:
            self.workouts_card.set_content(
                "No workouts",
                "Import workout CSV",
            )
            return

        weekly_sessions = metrics["weekly_sessions"]
        total_volume = metrics["total_volume_kg"]

        self.workouts_card.set_content(
            f"{total_sessions:,} sessions",
            f"{weekly_sessions} this week • {total_volume:,.0f} kg",
        )

    def _refresh_nutrition_card(self) -> None:
        metrics = get_nutrition_summary_metrics(days=7)

        total_meals = metrics["total_meals"]

        if total_meals == 0:
            self.nutrition_card.set_content(
                "No meals",
                "Add foods and build meals",
            )
            return

        total_carbs = metrics["total_carbs_g"]
        average_daily_carbs = metrics["average_daily_carbs_g"]

        self.nutrition_card.set_content(
            f"{total_meals:,} meals",
            f"7d: {total_carbs:.1f}g carbs • {average_daily_carbs:.1f}g/day",
        )

    def refresh_data(self) -> None:
        self._refresh_card_data()
