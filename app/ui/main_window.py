from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
)
from PySide6.QtGui import QIcon

from app.ui.tabs.glucose_tab import GlucoseTab
from app.ui.tabs.home_tab import HomeTab
from app.ui.tabs.activity_tab import ActivityTab
from app.ui.tabs.workouts_tab import WorkoutTab
from app.ui.tabs.nutrition_tab import NutritionTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        project_root = Path(__file__).resolve().parents[2]
        icon_path = project_root / "assets" / "branding" / "logo_full_detailed.png"

        self.setWindowTitle("RigLog")
        self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1400, 900)

        self.tabs = QTabWidget()

        self.glucose_tab = GlucoseTab()
        self.activity_tab = ActivityTab()
        self.workouts_tab = WorkoutTab()
        self.nutrition_tab = NutritionTab()

        self.home_tab = HomeTab(
            on_open_glucose=lambda: self.tabs.setCurrentWidget(self.glucose_tab),
            on_open_activity=lambda: self.tabs.setCurrentWidget(self.activity_tab),
            on_open_workouts=lambda: self.tabs.setCurrentWidget(self.workouts_tab),
            on_open_nutrition=lambda: self.tabs.setCurrentWidget(self.nutrition_tab),
        )

        self.activity_tab.data_updated.connect(self.home_tab.refresh_data)

        self.tabs.addTab(self.home_tab, "Home")
        self.tabs.addTab(self.glucose_tab, "Glucose")
        self.tabs.addTab(self.activity_tab, "Activity")
        self.tabs.addTab(self.workouts_tab, "Workouts")
        self.tabs.addTab(self.nutrition_tab, "Nutrition")

        self.setCentralWidget(self.tabs)
