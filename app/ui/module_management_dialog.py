"""Dialog for enabling or disabling RigLog health modules."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from app.core.modules import MODULE_REGISTRY, normalise_enabled_module_keys
from app.core.settings import AppSettings


class ModuleManagementDialog(QDialog):
    """Allow users to manage enabled RigLog modules after setup."""

    def __init__(
        self,
        settings: AppSettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.base_settings = settings
        self.module_checkboxes: dict[str, QCheckBox] = {}

        self.setObjectName("moduleManagementDialog")
        self.setWindowTitle("Manage Modules")
        self.setModal(True)
        self.resize(640, 520)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Manage Modules")
        title.setObjectName("moduleManagementTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        intro = QLabel(
            "Choose which health modules are available in RigLog. "
            "Disabling a module hides it from the app, but does not delete its data. "
            "Changes apply after restarting RigLog."
        )
        intro.setObjectName("moduleManagementIntro")
        intro.setWordWrap(True)
        intro.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(intro)

        self._build_module_options(layout)

        layout.addStretch()

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        self.button_box.setObjectName("moduleManagementButtonBox")

        self.save_button = self.button_box.button(
            QDialogButtonBox.StandardButton.Save
        )
        self.save_button.setObjectName("saveModuleSettingsButton")

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.button_box)

        self._update_save_state()

    def _build_module_options(self, layout: QVBoxLayout) -> None:
        """Build one checkbox per registered module."""
        selected_keys = set(self.base_settings.enabled_modules)

        for module in MODULE_REGISTRY:
            module_frame = QFrame()
            module_frame.setObjectName(f"moduleManagementOption_{module.key}")

            module_layout = QVBoxLayout(module_frame)
            module_layout.setContentsMargins(12, 10, 12, 10)
            module_layout.setSpacing(4)

            checkbox = QCheckBox(module.label)
            checkbox.setObjectName(f"moduleManagementCheckbox_{module.key}")
            checkbox.setChecked(module.key in selected_keys)
            checkbox.toggled.connect(self.handle_module_selection_changed)

            description = QLabel(module.description)
            description.setObjectName(f"moduleManagementDescription_{module.key}")
            description.setWordWrap(True)

            module_layout.addWidget(checkbox)
            module_layout.addWidget(description)

            self.module_checkboxes[module.key] = checkbox
            layout.addWidget(module_frame)

    def handle_module_selection_changed(self, _checked: bool = False) -> None:
        """Refresh save-state validation after module selection changes."""
        self._update_save_state()

    def _selected_module_keys_unvalidated(self) -> tuple[str, ...]:
        """Return selected module keys before registry validation."""
        return tuple(
            module_key
            for module_key, checkbox in self.module_checkboxes.items()
            if checkbox.isChecked()
        )

    def selected_module_keys(self) -> tuple[str, ...]:
        """Return selected module keys normalised into registry order."""
        return normalise_enabled_module_keys(
            self._selected_module_keys_unvalidated()
        )

    def _update_save_state(self) -> None:
        """Disable Save until at least one module is selected."""
        self.save_button.setEnabled(
            bool(self._selected_module_keys_unvalidated())
        )

    def to_settings(self) -> AppSettings:
        """Return updated settings preserving non-module preferences."""
        return AppSettings(
            setup_complete=self.base_settings.setup_complete,
            enabled_modules=self.selected_module_keys(),
            step_target=self.base_settings.step_target,
            extra_settings=dict(self.base_settings.extra_settings),
        )

    def accept(self) -> None:
        """Validate module selection before accepting the dialog."""
        try:
            self.selected_module_keys()
        except ValueError:
            QMessageBox.warning(
                self,
                "Select a module",
                "Please select at least one RigLog health module.",
            )
            return

        super().accept()
