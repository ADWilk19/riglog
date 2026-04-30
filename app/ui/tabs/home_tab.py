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

from app.db.database import SessionLocal
from app.db.models import GlucoseReading
from app.services.activity.analysis import (
    get_activity_summary_cards,
    get_daily_activity,
)
from app.ui.widgets.summary_card import SummaryCard


class HomeTab(QWidget):
    def __init__(
        self,
        on_open_glucose=None,
        on_open_activity=None,
        on_open_workouts=None,
    ) -> None:
        super().__init__()

        self.on_open_glucose = on_open_glucose
        self.on_open_activity = on_open_activity
        self.on_open_workouts = on_open_workouts

        project_root = Path(__file__).resolve().parents[3]
        logo_path = project_root / "assets" / "branding" / "logo_full.png"

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

        main_layout.addWidget(container, alignment=Qt.AlignHCenter)
        main_layout.addStretch(1)

        self._refresh_card_data()
        self.setLayout(main_layout)

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

        self.glucose_card = SummaryCard(
            title="Glucose",
            value="Loading...",
            subtitle="Checking readings",
            on_click=self.on_open_glucose,
        )
        self.activity_card = SummaryCard(
            title="Activity",
            value="Loading...",
            subtitle="Checking Fitbit data",
            on_click=self.on_open_activity,
        )
        self.workouts_card = SummaryCard(
            title="Workouts",
            value="Coming soon",
            subtitle="Track sessions and progression",
            on_click=self.on_open_workouts,
        )
        self.nutrition_card = SummaryCard(
            title="Nutrition",
            value="Coming soon",
            subtitle="Log meals and calorie trends",
        )

        self.glucose_card.set_variant("primary")
        self.activity_card.set_variant("primary")

        for card in (
            self.glucose_card,
            self.activity_card,
            self.workouts_card,
            self.nutrition_card,
        ):
            card.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            card.setMinimumHeight(110)

        grid.addWidget(self.glucose_card, 0, 0)
        grid.addWidget(self.activity_card, 0, 1)
        grid.addWidget(self.workouts_card, 1, 0)
        grid.addWidget(self.nutrition_card, 1, 1)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        return grid

    def _refresh_card_data(self) -> None:
        session = SessionLocal()

        try:
            self._refresh_glucose_card(session)
            self._refresh_activity_card()
        finally:
            session.close()

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

        cards_data = get_activity_summary_cards(rows)

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

    def refresh_data(self) -> None:
        self._refresh_card_data()
