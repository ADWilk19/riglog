"""Read-only Nutrition tab for meal and macro summaries."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.nutrition.analysis import (
    get_meal_template_totals_rows,
    get_nutrition_summary_metrics,
    get_recent_meal_logs,
)
from app.ui.widgets.summary_card import SummaryCard


class NutritionTab(QWidget):
    """Read-only nutrition dashboard tab."""

    def __init__(self) -> None:
        super().__init__()

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setObjectName("nutritionScrollArea")
        scroll.setWidgetResizable(True)

        container = QWidget()
        container.setObjectName("nutritionContainer")

        self.layout = QVBoxLayout(container)
        self.layout.setSpacing(20)
        self.layout.setContentsMargins(16, 16, 16, 24)

        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

        self._build_toolbar()
        self._build_summary_panel()
        self._build_recent_meals_table()
        self._build_template_totals_table()

        self.load_data()

    def _create_section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def _build_toolbar(self) -> None:
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("secondaryAction")
        self.refresh_button.clicked.connect(self.load_data)

        toolbar.addStretch()
        toolbar.addWidget(self.refresh_button)
        toolbar.addStretch()

        self.layout.addLayout(toolbar)

    def _build_summary_panel(self) -> None:
        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)

        self.total_meals_card = SummaryCard(title="Meals Logged", value="-")
        self.calories_card = SummaryCard(title="Calories", value="-")
        self.carbs_card = SummaryCard(title="Carbs", value="-")
        self.protein_card = SummaryCard(title="Protein", value="-")
        self.fat_card = SummaryCard(title="Fat", value="-")
        self.avg_daily_carbs_card = SummaryCard(title="Avg Daily Carbs", value="-")

        summary_row.addStretch()
        for card in [
            self.total_meals_card,
            self.calories_card,
            self.carbs_card,
            self.protein_card,
            self.fat_card,
            self.avg_daily_carbs_card,
        ]:
            summary_row.addWidget(card)
        summary_row.addStretch()

        self.layout.addLayout(summary_row)

    def _build_recent_meals_table(self) -> None:
        self.layout.addWidget(self._create_section_title("Recent Meal Logs"))

        self.recent_meals_table = QTableWidget()
        self.recent_meals_table.setObjectName("nutritionTable")
        self.recent_meals_table.setColumnCount(9)
        self.recent_meals_table.setHorizontalHeaderLabels(
            [
                "Logged At",
                "Meal",
                "Meal Event",
                "Portion",
                "Calories",
                "Carbs (g)",
                "Protein (g)",
                "Fat (g)",
                "Notes",
            ]
        )
        self.recent_meals_table.verticalHeader().setVisible(False)
        self.recent_meals_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recent_meals_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.recent_meals_table.setAlternatingRowColors(True)
        self.recent_meals_table.setMinimumHeight(260)
        self.recent_meals_table.setSortingEnabled(True)

        header = self.recent_meals_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.Stretch)

        self.layout.addWidget(self.recent_meals_table)

    def _build_template_totals_table(self) -> None:
        self.layout.addWidget(self._create_section_title("Meal Template Totals"))

        self.template_totals_table = QTableWidget()
        self.template_totals_table.setObjectName("nutritionTable")
        self.template_totals_table.setColumnCount(8)
        self.template_totals_table.setHorizontalHeaderLabels(
            [
                "Meal Template",
                "Default Event",
                "Calories",
                "Carbs (g)",
                "Protein (g)",
                "Fat (g)",
                "Fibre (g)",
                "Salt (g)",
            ]
        )
        self.template_totals_table.verticalHeader().setVisible(False)
        self.template_totals_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.template_totals_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.template_totals_table.setAlternatingRowColors(True)
        self.template_totals_table.setMinimumHeight(260)
        self.template_totals_table.setSortingEnabled(True)

        header = self.template_totals_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)

        self.layout.addWidget(self.template_totals_table)

    def load_data(self) -> None:
        """Refresh summary cards and nutrition tables."""
        self._load_summary_cards()
        self._load_recent_meals_table()
        self._load_template_totals_table()

    def _load_summary_cards(self) -> None:
        metrics = get_nutrition_summary_metrics()

        self.total_meals_card.set_content(str(metrics["total_meals"]))
        self.calories_card.set_content(f"{metrics['total_calories']:.0f}", "kcal")
        self.carbs_card.set_content(f"{metrics['total_carbs_g']:.1f}", "g")
        self.protein_card.set_content(f"{metrics['total_protein_g']:.1f}", "g")
        self.fat_card.set_content(f"{metrics['total_fat_g']:.1f}", "g")
        self.avg_daily_carbs_card.set_content(
            f"{metrics['average_daily_carbs_g']:.1f}",
            "g/day",
        )

    def _load_recent_meals_table(self) -> None:
        rows = get_recent_meal_logs(limit=10)

        self.recent_meals_table.setSortingEnabled(False)
        self.recent_meals_table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            values = [
                row["logged_at"].strftime("%Y-%m-%d %H:%M"),
                row["meal_name"],
                row["meal_event"] or "-",
                f"{row['portion_multiplier']:.2f}",
                f"{row['calories']:.1f}",
                f"{row['carbs_g']:.1f}",
                f"{row['protein_g']:.1f}",
                f"{row['fat_g']:.1f}",
                row["notes"] or "",
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)

                if column_index in {3, 4, 5, 6, 7}:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                else:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft
                        | Qt.AlignmentFlag.AlignVCenter
                    )

                self.recent_meals_table.setItem(row_index, column_index, item)

        self.recent_meals_table.setSortingEnabled(True)
        self.recent_meals_table.sortItems(0, Qt.SortOrder.DescendingOrder)

    def _load_template_totals_table(self) -> None:
        rows = get_meal_template_totals_rows()

        self.template_totals_table.setSortingEnabled(False)
        self.template_totals_table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            values = [
                row["name"],
                row["default_meal_event"] or "-",
                f"{row['calories']:.1f}",
                f"{row['carbs_g']:.1f}",
                f"{row['protein_g']:.1f}",
                f"{row['fat_g']:.1f}",
                f"{row['fibre_g']:.1f}",
                f"{row['salt_g']:.1f}",
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)

                if column_index >= 2:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                else:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft
                        | Qt.AlignmentFlag.AlignVCenter
                    )

                self.template_totals_table.setItem(row_index, column_index, item)

        self.template_totals_table.setSortingEnabled(True)
        self.template_totals_table.sortItems(0, Qt.SortOrder.AscendingOrder)
        
