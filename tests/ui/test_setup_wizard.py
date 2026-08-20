from app.core.modules import MODULE_REGISTRY
from app.core.settings import AppSettings
from app.ui.setup_wizard import SetupWizard


def test_setup_wizard_renders_registered_modules(qtbot):
    wizard = SetupWizard(
        settings=AppSettings(
            setup_complete=False,
            enabled_modules=("glucose", "activity"),
            step_target=8_000,
        )
    )
    qtbot.addWidget(wizard)

    assert set(wizard.module_checkboxes) == {
        module.key for module in MODULE_REGISTRY
    }

    for module in MODULE_REGISTRY:
        assert wizard.module_checkboxes[module.key].text() == module.label


def test_setup_wizard_uses_settings_selection(qtbot):
    wizard = SetupWizard(
        settings=AppSettings(
            setup_complete=False,
            enabled_modules=("glucose", "nutrition"),
            step_target=8_000,
        )
    )
    qtbot.addWidget(wizard)

    assert wizard.module_checkboxes["glucose"].isChecked()
    assert not wizard.module_checkboxes["activity"].isChecked()
    assert not wizard.module_checkboxes["workouts"].isChecked()
    assert wizard.module_checkboxes["nutrition"].isChecked()


def test_setup_wizard_disables_finish_when_no_modules_selected(qtbot):
    wizard = SetupWizard(
        settings=AppSettings(
            setup_complete=False,
            enabled_modules=("glucose",),
        )
    )
    qtbot.addWidget(wizard)

    for checkbox in wizard.module_checkboxes.values():
        checkbox.setChecked(False)

    assert not wizard.finish_button.isEnabled()


def test_setup_wizard_enables_finish_when_one_module_selected(qtbot):
    wizard = SetupWizard(
        settings=AppSettings(
            setup_complete=False,
            enabled_modules=("glucose",),
        )
    )
    qtbot.addWidget(wizard)

    for checkbox in wizard.module_checkboxes.values():
        checkbox.setChecked(False)

    wizard.module_checkboxes["nutrition"].setChecked(True)

    assert wizard.finish_button.isEnabled()


def test_setup_wizard_shows_activity_settings_only_when_activity_selected(qtbot):
    wizard = SetupWizard(
        settings=AppSettings(
            setup_complete=False,
            enabled_modules=("glucose", "activity"),
            step_target=12_000,
        )
    )
    qtbot.addWidget(wizard)

    assert not wizard.activity_settings_container.isHidden()
    assert wizard.activity_settings_container.isEnabled()

    wizard.module_checkboxes["activity"].setChecked(False)

    assert wizard.activity_settings_container.isHidden()
    assert not wizard.activity_settings_container.isEnabled()

    wizard.module_checkboxes["activity"].setChecked(True)

    assert not wizard.activity_settings_container.isHidden()
    assert wizard.activity_settings_container.isEnabled()


def test_setup_wizard_returns_completed_settings(qtbot):
    wizard = SetupWizard(
        settings=AppSettings(
            setup_complete=False,
            enabled_modules=("glucose",),
            step_target=8_000,
            extra_settings={"future_setting": "preserved"},
        )
    )
    qtbot.addWidget(wizard)

    wizard.module_checkboxes["activity"].setChecked(True)
    wizard.module_checkboxes["workouts"].setChecked(False)
    wizard.module_checkboxes["nutrition"].setChecked(False)
    wizard.step_target_spin.setValue(9_500)

    completed_settings = wizard.to_settings()

    assert completed_settings.setup_complete is True
    assert completed_settings.enabled_modules == ("glucose", "activity")
    assert completed_settings.step_target == 9_500
    assert completed_settings.extra_settings == {"future_setting": "preserved"}
