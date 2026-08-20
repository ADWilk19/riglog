from app.core.modules import MODULE_REGISTRY
from app.core.settings import AppSettings
from app.ui.module_management_dialog import ModuleManagementDialog


def test_module_management_dialog_renders_registered_modules(qtbot):
    dialog = ModuleManagementDialog(
        settings=AppSettings(
            setup_complete=True,
            enabled_modules=("glucose", "activity"),
            step_target=8_000,
        )
    )
    qtbot.addWidget(dialog)

    assert set(dialog.module_checkboxes) == {
        module.key for module in MODULE_REGISTRY
    }

    for module in MODULE_REGISTRY:
        assert dialog.module_checkboxes[module.key].text() == module.label


def test_module_management_dialog_uses_current_settings_selection(qtbot):
    dialog = ModuleManagementDialog(
        settings=AppSettings(
            setup_complete=True,
            enabled_modules=("glucose", "nutrition"),
            step_target=8_000,
        )
    )
    qtbot.addWidget(dialog)

    assert dialog.module_checkboxes["glucose"].isChecked()
    assert not dialog.module_checkboxes["activity"].isChecked()
    assert not dialog.module_checkboxes["workouts"].isChecked()
    assert dialog.module_checkboxes["nutrition"].isChecked()


def test_module_management_dialog_disables_save_when_no_modules_selected(qtbot):
    dialog = ModuleManagementDialog(
        settings=AppSettings(
            setup_complete=True,
            enabled_modules=("glucose",),
        )
    )
    qtbot.addWidget(dialog)

    for checkbox in dialog.module_checkboxes.values():
        checkbox.setChecked(False)

    assert not dialog.save_button.isEnabled()


def test_module_management_dialog_enables_save_when_one_module_selected(qtbot):
    dialog = ModuleManagementDialog(
        settings=AppSettings(
            setup_complete=True,
            enabled_modules=("glucose",),
        )
    )
    qtbot.addWidget(dialog)

    for checkbox in dialog.module_checkboxes.values():
        checkbox.setChecked(False)

    dialog.module_checkboxes["nutrition"].setChecked(True)

    assert dialog.save_button.isEnabled()


def test_module_management_dialog_returns_updated_settings(qtbot):
    dialog = ModuleManagementDialog(
        settings=AppSettings(
            setup_complete=True,
            enabled_modules=("glucose", "activity"),
            step_target=9_500,
            extra_settings={"future_setting": "preserved"},
        )
    )
    qtbot.addWidget(dialog)

    dialog.module_checkboxes["activity"].setChecked(False)
    dialog.module_checkboxes["nutrition"].setChecked(True)
    dialog.module_checkboxes["workouts"].setChecked(False)

    updated_settings = dialog.to_settings()

    assert updated_settings.setup_complete is True
    assert updated_settings.enabled_modules == ("glucose", "nutrition")
    assert updated_settings.step_target == 9_500
    assert updated_settings.extra_settings == {"future_setting": "preserved"}
