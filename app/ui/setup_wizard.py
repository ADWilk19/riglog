"""First-run setup wizard for choosing initial RigLog modules."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.modules import (
    MODULE_REGISTRY,
    normalise_enabled_module_keys,
)
from app.core.settings import (
    DEFAULT_STEP_TARGET,
    AppSettings,
    get_default_settings,
)


class SetupWizard(QDialog):
    """Collect initial module and personalisation settings."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.base_settings = (
            settings
            if settings is not None
            else get_default_settings()
        )

        self.module_checkboxes: dict[str, QCheckBox] = {}

        self.setObjectName("setupWizard")
        self.setWindowTitle("Set up RigLog")
        self.setModal(True)
        self.resize(640, 520)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Set up RigLog")
        title.setObjectName("setupTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        intro = QLabel(
            "Choose the health modules you want to use. "
            "You can change these settings later."
        )
        intro.setObjectName("setupIntro")
        intro.setWordWrap(True)
        intro.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(intro)

        self._build_module_section(layout)
        self._build_activity_section(layout)

        layout.addStretch()

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        self.button_box.setObjectName("setupButtonBox")
        self.finish_button = self.button_box.button(
            QDialogButtonBox.StandardButton.Ok
        )
        self.finish_button.setText("Finish")
        self.finish_button.setObjectName("finishSetupButton")

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.button_box)

        self._update_activity_settings_visibility()
        self._update_finish_state()

    def _build_module_section(self, layout: QVBoxLayout) -> None:
        """Build module-selection checkboxes from the module registry."""
        section_title = QLabel("Modules")
        section_title.setObjectName("setupSectionTitle")

        layout.addWidget(section_title)

        selected_keys = set(self.base_settings.enabled_modules)

        for module in MODULE_REGISTRY:
            module_frame = QFrame()
            module_frame.setObjectName(f"moduleOption_{module.key}")

            module_layout = QVBoxLayout(module_frame)
            module_layout.setContentsMargins(12, 10, 12, 10)
            module_layout.setSpacing(4)

            checkbox = QCheckBox(module.label)
            checkbox.setObjectName(f"moduleCheckbox_{module.key}")
            checkbox.setChecked(module.key in selected_keys)
            checkbox.toggled.connect(self.handle_module_selection_changed)

            description = QLabel(module.description)
            description.setObjectName(f"moduleDescription_{module.key}")
            description.setWordWrap(True)

            module_layout.addWidget(checkbox)
            module_layout.addWidget(description)

            self.module_checkboxes[module.key] = checkbox
            layout.addWidget(module_frame)

    def _build_activity_section(self, layout: QVBoxLayout) -> None:
        """Build Activity-specific personalisation controls."""
        self.activity_settings_container = QFrame()
        self.activity_settings_container.setObjectName("activitySettingsContainer")

        activity_layout = QVBoxLayout(self.activity_settings_container)
        activity_layout.setContentsMargins(12, 10, 12, 10)
        activity_layout.setSpacing(8)

        title = QLabel("Activity settings")
        title.setObjectName("setupSectionTitle")

        row = QHBoxLayout()
        row.setSpacing(8)

        self.step_target_label = QLabel("Daily step target")
        self.step_target_label.setObjectName("stepTargetLabel")

        self.step_target_spin = QSpinBox()
        self.step_target_spin.setObjectName("stepTargetSpin")
        self.step_target_spin.setRange(1, 100_000)
        self.step_target_spin.setSingleStep(500)
        self.step_target_spin.setValue(
            self.base_settings.step_target or DEFAULT_STEP_TARGET
        )
        self.step_target_spin.setSuffix(" steps")

        row.addWidget(self.step_target_label)
        row.addWidget(self.step_target_spin)
        row.addStretch()

        activity_layout.addWidget(title)
        activity_layout.addLayout(row)

        layout.addWidget(self.activity_settings_container)

    def handle_module_selection_changed(self, _checked: bool = False) -> None:
        """Refresh dependent setup controls after module selection changes."""
        self._update_activity_settings_visibility()
        self._update_finish_state()

    def _activity_is_selected(self) -> bool:
        """Return whether the Activity module is currently selected."""
        checkbox = self.module_checkboxes.get("activity")
        return bool(checkbox is not None and checkbox.isChecked())

    def _update_activity_settings_visibility(self) -> None:
        """Show Activity personalisation only when Activity is selected."""
        activity_selected = self._activity_is_selected()
        self.activity_settings_container.setVisible(activity_selected)
        self.activity_settings_container.setEnabled(activity_selected)

    def _selected_module_keys_unvalidated(self) -> tuple[str, ...]:
        """Return selected module keys before final registry validation."""
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

    def _update_finish_state(self) -> None:
        """Disable Finish until at least one module is selected."""
        has_selection = bool(self._selected_module_keys_unvalidated())
        self.finish_button.setEnabled(has_selection)

    def to_settings(self) -> AppSettings:
        """Return completed application settings from the wizard state."""
        return AppSettings(
            setup_complete=True,
            enabled_modules=self.selected_module_keys(),
            step_target=self.step_target_spin.value(),
            extra_settings=dict(self.base_settings.extra_settings),
        )

    def accept(self) -> None:
        """Validate module selection before accepting the wizard."""
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
