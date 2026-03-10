from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QLabel,
)

from app.ui.tabs.glucose_tab import GlucoseTab

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("RigLog")
        self.resize(1000, 700)

        self.tabs = QTabWidget()

        self.tabs.addTab(self._build_tab("Home"), "Home")
        self.tabs.addTab(GlucoseTab(), "Glucose")
        self.tabs.addTab(self._build_tab("Activity"), "Activity")
        self.tabs.addTab(self._build_tab("Workouts"), "Workouts")

        self.setCentralWidget(self.tabs)

    def _build_tab(self, name: str) -> QWidget:
        tab = QWidget()

        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"{name} tab"))

        tab.setLayout(layout)

        return tab
