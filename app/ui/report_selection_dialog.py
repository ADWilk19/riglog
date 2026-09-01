"""Dialog for choosing sections to include in a RigLog PDF report."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.modules import get_module, normalise_enabled_module_keys
from app.core.report_sections import (
    get_default_report_section_keys,
    get_report_sections_for_modules,
    normalise_report_section_keys,
)


class ReportSelectionDialog(QDialog):
    """Allow the user to choose enabled-module sections for PDF export."""

    def __init__(
        self,
        enabled_module_keys: Iterable[str],
        selected_section_keys: Iterable[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("reportSelectionDialog")
        self.setWindowTitle("Export PDF Report")
        self.resize(520, 560)

        self.enabled_module_keys = normalise_enabled_module_keys(
            enabled_module_keys,
            require_one=False,
        )

        self.available_sections = get_report_sections_for_modules(
            self.enabled_module_keys,
            export_kind="pdf",
        )

        if selected_section_keys is None:
            selected_keys = set(
                get_default_report_section_keys(
                    self.enabled_module_keys,
                    export_kind="pdf",
                )
            )
        else:
            selected_keys = set(
                normalise_report_section_keys(
                    selected_section_keys,
                    self.enabled_module_keys,
                    export_kind="pdf",
                )
            )

        self.section_checkboxes: dict[str, QCheckBox] = {}

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Choose report sections")
        title.setObjectName("reportSelectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            """
            QLabel {
                font-size: 18px;
                font-weight: 700;
            }
            """
        )
        layout.addWidget(title)

        description = QLabel(
            "Select the visuals, tables, and summary sections to include "
            "in the PDF report. Only enabled modules are shown."
        )
        description.setObjectName("reportSelectionDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("reportSelectionScrollArea")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)

        for module_key in self.enabled_module_keys:
            module_sections = [
                section
                for section in self.available_sections
                if section.module_key == module_key
            ]

            if not module_sections:
                continue

            group = QGroupBox(get_module(module_key).label)
            group.setObjectName(f"reportSectionGroup_{module_key}")

            group_layout = QVBoxLayout(group)
            group_layout.setSpacing(8)

            for section in module_sections:
                checkbox = QCheckBox(section.label)
                checkbox.setObjectName(
                    f"reportSection_{section.key.replace('.', '_')}"
                )
                checkbox.setToolTip(section.description)
                checkbox.setChecked(section.key in selected_keys)
                checkbox.stateChanged.connect(
                    self._update_accept_button_state
                )

                self.section_checkboxes[section.key] = checkbox
                group_layout.addWidget(checkbox)

            scroll_layout.addWidget(group)

        scroll_layout.addStretch(1)
        scroll_area.setWidget(scroll_content)

        layout.addWidget(scroll_area, stretch=1)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.setObjectName("reportSelectionButtonBox")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.ok_button = self.button_box.button(
            QDialogButtonBox.StandardButton.Ok
        )
        self.ok_button.setObjectName("reportSelectionOkButton")
        self.ok_button.setText("Generate PDF")

        layout.addWidget(self.button_box)

        self._update_accept_button_state()

    def selected_section_keys(self) -> tuple[str, ...]:
        """Return checked section keys in registry order."""
        selected_keys = [
            section_key
            for section_key, checkbox in self.section_checkboxes.items()
            if checkbox.isChecked()
        ]

        return normalise_report_section_keys(
            selected_keys,
            self.enabled_module_keys,
            export_kind="pdf",
        )

    def _update_accept_button_state(self) -> None:
        """Enable report generation only when at least one section is selected."""
        self.ok_button.setEnabled(
            any(
                checkbox.isChecked()
                for checkbox in self.section_checkboxes.values()
            )
        )
