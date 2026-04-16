from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QLabel,
)
from PySide6.QtGui import QIcon

from app.ui.tabs.glucose_tab import GlucoseTab
from app.ui.tabs.home_tab import HomeTab
from app.ui.tabs.activity_tab import ActivityTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        project_root = Path(__file__).resolve().parents[2]
        icon_path = project_root / "assets" / "branding" / "logo_full_detailed.png"
        
        self.setWindowTitle("RigLog")
        self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1400, 900)

        self.tabs = QTabWidget()

        self.tabs.addTab(HomeTab(), "Home")
        self.tabs.addTab(GlucoseTab(), "Glucose")
        self.tabs.addTab(ActivityTab(), "Activity")
        self.tabs.addTab(self._build_tab("Workouts"), "Workouts")

        self.setCentralWidget(self.tabs)

    def _build_tab(self, name: str) -> QWidget:
        tab = QWidget()

        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"{name} tab"))

        tab.setLayout(layout)

        return tab
