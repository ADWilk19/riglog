from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QSizePolicy


class SummaryCard(QFrame):
    clicked = Signal()

    def __init__(
        self,
        title: str,
        value: str = "-",
        subtitle: str = "",
        on_click=None,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("summaryCard")
        self.setProperty("variant", "neutral")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(84)
        self.setMinimumWidth(220)
        
        self.title_label = QLabel(title)
        self.title_label.setObjectName("summaryCardTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("background: transparent;")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("summaryCardValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setStyleSheet("background: transparent;")

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("summaryCardSubtitle")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setVisible(bool(subtitle))
        self.subtitle_label.setStyleSheet("background: transparent;")

        self.on_click = on_click

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.subtitle_label)

        self.setLayout(layout)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_content(self, value: str, subtitle: str | None = None) -> None:
        self.value_label.setText(value)

        if subtitle is None:
            return

        self.subtitle_label.setText(subtitle)
        self.subtitle_label.setVisible(bool(subtitle))

    def set_variant(self, variant: str = "neutral") -> None:
        self.setProperty("variant", variant)
        self.style().unpolish(self)
        self.style().polish(self)

    def clear(self) -> None:
        self.value_label.setText("-")
        self.subtitle_label.clear()
        self.subtitle_label.setVisible(False)
        self.set_variant("neutral")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

            if self.on_click:
                self.on_click()

        super().mousePressEvent(event)
