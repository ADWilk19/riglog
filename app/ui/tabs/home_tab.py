from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QSizePolicy,
)


class HomeTab(QWidget):
    def __init__(self) -> None:
        super().__init__()

        project_root = Path(__file__).resolve().parents[3]
        logo_path = project_root / "assets" / "branding" / "logo_full.png"

        layout = QVBoxLayout()
        layout.setContentsMargins(32, 40, 32, 40)
        layout.setSpacing(20)

        logo_label = QLabel()
        logo_label.setStyleSheet("background: transparent;")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        pixmap = QPixmap(str(logo_path))
        if not pixmap.isNull():
            logo_label.setPixmap(
                pixmap.scaled(
                    240,
                    240,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
        else:
            logo_label.setText("RigLog")

        title_label = QLabel("RigLog")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(
            """
            QLabel {
                font-size: 32px;
                font-weight: 700;
                color: #F5F5F5;
            }
            """
        )

        subtitle_label = QLabel("Personal health analytics")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet(
            """
            QLabel {
                font-size: 14px;
                color: #A0A0A0;
                margin-top: 4px;
            }
            """
        )

        intro_label = QLabel(
            "One app. Multiple health signals. Clearer decisions."
        )
        intro_label.setAlignment(Qt.AlignCenter)
        intro_label.setWordWrap(True)
        intro_label.setStyleSheet(
            """
            QLabel {
                font-size: 13px;
                color: #CFCFCF;
                margin-top: 6px;
            }
            """
        )

        title_label.setObjectName("title")
        subtitle_label.setObjectName("subtitle")
        intro_label.setObjectName("tagline")

        layout.addStretch()
        layout.addWidget(logo_label)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addWidget(intro_label)
        layout.addStretch()

        self.setLayout(layout)
