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

        grid = self._build_summary_grid()

        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addLayout(grid)
        container.setLayout(container_layout)

        container.setMaximumWidth(1000)
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        main_layout.addWidget(container)
        main_layout.addStretch()

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

        glucose_card = SummaryCard(
            title="Glucose",
            value="Ready",
            subtitle="Import and analyse readings",
            on_click=self.on_open_glucose,
        )
        activity_card = SummaryCard(
            title="Activity",
            value="Ready",
            subtitle="Sync Fitbit and review steps",
            on_click=self.on_open_activity,
        )
        workouts_card = SummaryCard(
            title="Workouts",
            value="Coming soon",
            subtitle="Track sessions and progression",
            on_click=self.on_open_workouts,
        )
        nutrition_card = SummaryCard(
            title="Nutrition",
            value="Coming soon",
            subtitle="Log meals and calorie trends",
        )

        glucose_card.set_variant("primary")
        activity_card.set_variant("primary")

        for card in (
            glucose_card,
            activity_card,
            workouts_card,
            nutrition_card,
        ):
            card.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            card.setMinimumHeight(90)

        activity_card.set_content(
            "8,412 steps",
            "7-day average"
        )

        glucose_card.set_content(
            "1,167 readings",
            "Last import: 2 days ago"
        )

        grid.addWidget(glucose_card, 0, 0)
        grid.addWidget(activity_card, 0, 1)
        grid.addWidget(workouts_card, 1, 0)
        grid.addWidget(nutrition_card, 1, 1)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        return grid
