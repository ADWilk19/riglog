from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from app.services.glucose.analysis import (
    get_all_glucose_readings_with_meal_event,
    get_glucose_summary,
    update_glucose_note,
)
from app.services.glucose.importer import import_diabetes_m_csv


class GlucoseTab(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.selected_reading_id: int | None = None

        self.layout = QVBoxLayout(self)

        self._build_toolbar()
        self._build_summary_panel()
        self._build_table()
        self._build_notes_panel()

        self.load_readings()

    def _build_toolbar(self) -> None:
        toolbar = QHBoxLayout()

        self.import_button = QPushButton("Import Diabetes:M CSV")
        self.import_button.clicked.connect(self.handle_import_csv)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_readings)

        toolbar.addWidget(self.import_button)
        toolbar.addWidget(self.refresh_button)
        toolbar.addStretch()

        self.layout.addLayout(toolbar)

    def _build_table(self) -> None:
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Recorded At", "Glucose", "Meal Event", "Notes"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self.handle_row_selection)
        self.table.setColumnHidden(0, True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)

        self.layout.addWidget(self.table)

    def _build_notes_panel(self) -> None:
        notes_layout = QVBoxLayout()

        self.notes_label = QLabel("Notes for selected reading:")
        self.notes_editor = QTextEdit()
        self.notes_editor.setPlaceholderText("Add contextual notes here...")

        self.save_note_button = QPushButton("Save Note")
        self.save_note_button.clicked.connect(self.handle_save_note)

        notes_layout.addWidget(self.notes_label)
        notes_layout.addWidget(self.notes_editor)
        notes_layout.addWidget(self.save_note_button)

        self.layout.addLayout(notes_layout)

    def _build_summary_panel(self) -> None:
        summary_layout = QHBoxLayout()

        self.count_label = QLabel("Readings: -")
        self.avg_label = QLabel("Average: -")
        self.min_label = QLabel("Lowest: -")
        self.max_label = QLabel("Highest: -")

        summary_layout.addWidget(self.count_label)
        summary_layout.addWidget(self.avg_label)
        summary_layout.addWidget(self.min_label)
        summary_layout.addWidget(self.max_label)
        summary_layout.addStretch()

        self.layout.addLayout(summary_layout)

    def load_readings(self) -> None:
        summary = get_glucose_summary()

        if summary is None:
            self.count_label.setText("Readings: 0")
            self.avg_label.setText("Average: -")
            self.min_label.setText("Lowest: -")
            self.max_label.setText("Highest: -")
        else:
            self.count_label.setText(f"Readings: {summary['count']}")
            self.avg_label.setText(f"Average: {summary['avg']:.1f} mmol/L")
            self.min_label.setText(f"Lowest: {summary['min']:.1f} mmol/L")
            self.max_label.setText(f"Highest: {summary['max']:.1f} mmol/L")

        readings = get_all_glucose_readings_with_meal_event()

        self.table.setRowCount(len(readings))

        for row_index, reading in enumerate(readings):
            id_item = QTableWidgetItem(str(reading["id"]))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            recorded_at_item = QTableWidgetItem(
                reading["recorded_at"].strftime("%Y-%m-%d %H:%M")
            )

            glucose_item = QTableWidgetItem(f"{reading['glucose_value']:.1f}")
            glucose_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            meal_event_item = QTableWidgetItem(reading["meal_event_label"])
            meal_event_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            notes_item = QTableWidgetItem(reading["notes"] or "")

            self.table.setItem(row_index, 0, id_item)
            self.table.setItem(row_index, 1, recorded_at_item)
            self.table.setItem(row_index, 2, glucose_item)
            self.table.setItem(row_index, 3, meal_event_item)
            self.table.setItem(row_index, 4, notes_item)

        self.selected_reading_id = None
        self.notes_editor.clear()

    def handle_import_csv(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Diabetes:M CSV",
            str(Path.home()),
            "CSV Files (*.csv)",
        )

        if not file_path:
            return

        try:
            imported_count = import_diabetes_m_csv(file_path)
        except Exception as exc:
            QMessageBox.critical(self, "Import failed", f"Could not import file:\n{exc}")
            return

        QMessageBox.information(
            self,
            "Import complete",
            f"Imported {imported_count} new readings.",
        )
        self.load_readings()

    def handle_row_selection(self) -> None:
        selected_items = self.table.selectedItems()

        if not selected_items:
            self.selected_reading_id = None
            self.notes_editor.clear()
            return

        row = selected_items[0].row()

        reading_id_item = self.table.item(row, 0)
        notes_item = self.table.item(row, 4)

        if reading_id_item is None:
            self.selected_reading_id = None
            self.notes_editor.clear()
            return

        self.selected_reading_id = int(reading_id_item.text())
        self.notes_editor.setPlainText(notes_item.text() if notes_item else "")

    def handle_save_note(self) -> None:
        if self.selected_reading_id is None:
            QMessageBox.warning(self, "No selection", "Please select a reading first.")
            return

        notes_text = self.notes_editor.toPlainText().strip()

        try:
            update_glucose_note(self.selected_reading_id, notes_text or None)
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", f"Could not save note:\n{exc}")
            return

        QMessageBox.information(self, "Saved", "Note updated successfully.")
        self.load_readings()
