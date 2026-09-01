"""Tests for settings-driven MainWindow tab construction."""

import pytest
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QAction

from app.core.settings import AppSettings
from app.ui import main_window as main_window_module
from app.ui.main_window import MainWindow


MODULE_KEYS = (
    "glucose",
    "activity",
    "workouts",
    "nutrition",
)


ACTIVITY_PDF_SECTION_KEYS = (
    "activity.summary_metrics",
    "activity.daily_steps_chart",
    "activity.weekly_steps_chart",
    "activity.daily_activity_table",
)

class FakeHomeTab(QWidget):
    """Lightweight HomeTab replacement for MainWindow tests."""

    def __init__(
        self,
        on_open_glucose=None,
        on_open_activity=None,
        on_open_workouts=None,
        on_open_nutrition=None,
        on_export_pdf=None,
        enabled_module_keys=None,
        step_target=10_000,
    ):
        super().__init__()

        self.on_open_glucose = on_open_glucose
        self.on_open_activity = on_open_activity
        self.on_open_workouts = on_open_workouts
        self.on_open_nutrition = on_open_nutrition
        self.on_export_pdf = on_export_pdf


        self.enabled_module_keys = tuple(enabled_module_keys)
        self.step_target = step_target

        self.navigation_callbacks = {
            "glucose": on_open_glucose,
            "activity": on_open_activity,
            "workouts": on_open_workouts,
            "nutrition": on_open_nutrition,
        }
        self.refresh_calls = 0

    def refresh_data(self):
        self.refresh_calls += 1

class FakeModuleTab(QWidget):
    """Lightweight configurable module tab."""

    data_updated = Signal()

    def __init__(self, module_key):
        super().__init__()
        self.module_key = module_key


@pytest.fixture
def fake_home_tab(monkeypatch):
    """Prevent MainWindow tests from loading real Home services."""
    monkeypatch.setattr(
        main_window_module,
        "HomeTab",
        FakeHomeTab,
    )


def make_tab_factories(created_modules):
    """Return recording factories for all configurable modules."""

    def make_factory(module_key):
        def factory():
            created_modules.append(module_key)
            return FakeModuleTab(module_key)

        return factory

    return {
        module_key: make_factory(module_key)
        for module_key in MODULE_KEYS
    }


def test_home_is_first_and_default_modules_use_registry_order(
    qtbot,
    fake_home_tab,
):
    created_modules = []
    window = MainWindow(
        settings=AppSettings(),
        tab_factories=make_tab_factories(created_modules),
    )
    qtbot.addWidget(window)

    assert [
        window.tabs.tabText(index)
        for index in range(window.tabs.count())
    ] == [
        "Home",
        "Glucose",
        "Activity",
        "Workouts",
        "Nutrition",
    ]

    assert created_modules == [
        "glucose",
        "activity",
        "workouts",
        "nutrition",
    ]


def test_only_enabled_module_tabs_are_instantiated(
    qtbot,
    fake_home_tab,
):
    created_modules = []
    window = MainWindow(
        settings=AppSettings(
            enabled_modules=("activity", "nutrition"),
        ),
        tab_factories=make_tab_factories(created_modules),
    )
    qtbot.addWidget(window)

    assert created_modules == [
        "activity",
        "nutrition",
    ]

    assert set(window.module_tabs) == {
        "activity",
        "nutrition",
    }

    assert [
        window.tabs.tabText(index)
        for index in range(window.tabs.count())
    ] == [
        "Home",
        "Activity",
        "Nutrition",
    ]

    assert window.home_tab.enabled_module_keys == (
        "activity",
        "nutrition",
    )

def test_enabled_modules_keep_existing_public_attributes(
    qtbot,
    fake_home_tab,
):
    window = MainWindow(
        settings=AppSettings(
            enabled_modules=("activity",),
        ),
        tab_factories=make_tab_factories([]),
    )
    qtbot.addWidget(window)

    assert window.activity_tab is window.module_tabs["activity"]
    assert not hasattr(window, "glucose_tab")
    assert not hasattr(window, "workouts_tab")
    assert not hasattr(window, "nutrition_tab")


def test_open_module_navigates_to_enabled_tab(
    qtbot,
    fake_home_tab,
):
    window = MainWindow(
        settings=AppSettings(
            enabled_modules=("activity", "nutrition"),
        ),
        tab_factories=make_tab_factories([]),
    )
    qtbot.addWidget(window)

    result = window.open_module("nutrition")

    assert result is True
    assert window.tabs.currentWidget() is window.nutrition_tab


def test_open_module_returns_false_for_disabled_module(
    qtbot,
    fake_home_tab,
):
    window = MainWindow(
        settings=AppSettings(
            enabled_modules=("activity",),
        ),
        tab_factories=make_tab_factories([]),
    )
    qtbot.addWidget(window)

    starting_widget = window.tabs.currentWidget()

    result = window.open_module("glucose")

    assert result is False
    assert window.tabs.currentWidget() is starting_widget


def test_home_navigation_callback_uses_dynamic_module_lookup(
    qtbot,
    fake_home_tab,
):
    window = MainWindow(
        settings=AppSettings(
            enabled_modules=("activity", "nutrition"),
        ),
        tab_factories=make_tab_factories([]),
    )
    qtbot.addWidget(window)

    window.home_tab.navigation_callbacks["activity"]()

    assert window.tabs.currentWidget() is window.activity_tab


def test_module_data_updated_signal_refreshes_home(
    qtbot,
    fake_home_tab,
):
    window = MainWindow(
        settings=AppSettings(
            enabled_modules=("activity",),
        ),
        tab_factories=make_tab_factories([]),
    )
    qtbot.addWidget(window)

    assert window.home_tab.refresh_calls == 0

    window.activity_tab.data_updated.emit()

    assert window.home_tab.refresh_calls == 1


def test_missing_enabled_module_factory_raises_clear_error(
    fake_home_tab,
):
    with pytest.raises(
        KeyError,
        match="No tab factory registered for module 'activity'",
    ):
        MainWindow(
            settings=AppSettings(
                enabled_modules=("activity",),
            ),
            tab_factories={},
        )


def test_default_factory_resolution_only_loads_enabled_modules(
    qtbot,
    fake_home_tab,
    monkeypatch,
):
    resolved_modules = []

    def fake_resolve_tab_factory(module):
        resolved_modules.append(module.key)

        return lambda: FakeModuleTab(module.key)

    monkeypatch.setattr(
        main_window_module,
        "resolve_tab_factory",
        fake_resolve_tab_factory,
    )

    window = MainWindow(
        settings=AppSettings(
            enabled_modules=("activity", "nutrition"),
        ),
    )
    qtbot.addWidget(window)

    assert resolved_modules == [
        "activity",
        "nutrition",
    ]

    assert set(window.module_tabs) == {
        "activity",
        "nutrition",
    }


def test_main_window_has_manage_modules_action(qtbot):
    window = MainWindow(
        settings=AppSettings(
            setup_complete=True,
            enabled_modules=("glucose", "activity"),
        )
    )
    qtbot.addWidget(window)

    action = window.findChild(QAction, "manageModulesAction")

    assert action is not None
    assert action.text() == "Manage Modules..."


def test_main_window_passes_step_target_to_home_and_activity_tab(
    qtbot,
    fake_home_tab,
    monkeypatch,
):
    class FakeActivityTab(FakeModuleTab):
        def __init__(self, step_target=10_000):
            super().__init__("activity")
            self.step_target = step_target

    def fake_resolve_tab_factory(module):
        if module.key == "activity":
            return FakeActivityTab

        return lambda: FakeModuleTab(module.key)

    monkeypatch.setattr(
        main_window_module,
        "resolve_tab_factory",
        fake_resolve_tab_factory,
    )

    window = MainWindow(
        settings=AppSettings(
            setup_complete=True,
            enabled_modules=("activity",),
            step_target=8_500,
        ),
    )
    qtbot.addWidget(window)

    assert window.home_tab.step_target == 8_500
    assert window.activity_tab.step_target == 8_500


def test_main_window_passes_export_callback_to_home(qtbot, mocker):
    handle_export = mocker.patch(
        "app.ui.main_window.MainWindow.handle_export_pdf_report",
        autospec=True,
    )

    window = MainWindow()
    qtbot.addWidget(window)

    qtbot.mouseClick(
        window.home_tab.export_pdf_button,
        Qt.MouseButton.LeftButton,
    )

    handle_export.assert_called_once_with(window)


def test_main_window_export_pdf_report_generates_selected_report(
        qtbot,
        mocker,
        tmp_path,
    ):
        output_path = tmp_path / "report.pdf"

        dialog = mocker.Mock()
        dialog.DialogCode.Accepted = 1
        dialog.exec.return_value = 1
        dialog.selected_section_keys.return_value = (
            "activity.summary_metrics",
        )

        dialog_class = mocker.patch(
            "app.ui.main_window.ReportSelectionDialog",
            return_value=dialog,
        )

        get_save_file_name = mocker.patch(
            "app.ui.main_window.QFileDialog.getSaveFileName",
            return_value=(str(output_path), "PDF Files (*.pdf)"),
        )

        generate_pdf_report = mocker.patch(
            "app.ui.main_window.generate_pdf_report",
            return_value=mocker.Mock(
                included_sections=("activity.summary_metrics",),
            ),
        )

        information = mocker.patch(
            "app.ui.main_window.QMessageBox.information",
        )


        save_settings = mocker.patch(
            "app.ui.main_window.save_settings",
        )

        window = MainWindow(
            settings=AppSettings(
                enabled_modules=("activity",),
                step_target=8_500,
            ),
        )
        qtbot.addWidget(window)

        window.handle_export_pdf_report()

        dialog_class.assert_called_once_with(
            enabled_module_keys=("activity",),
            selected_section_keys=ACTIVITY_PDF_SECTION_KEYS,
            parent=window,
        )
        get_save_file_name.assert_called_once()
        generate_pdf_report.assert_called_once_with(
            str(output_path),
            section_keys=("activity.summary_metrics",),
            enabled_module_keys=("activity",),
            step_target=8_500,
        )
        information.assert_called_once()
        save_settings.assert_called_once()
        saved_settings = save_settings.call_args.args[0]
        assert saved_settings.pdf_report_section_keys == (
            "activity.summary_metrics",
        )


def test_main_window_export_pdf_report_uses_saved_section_preferences(
    qtbot,
    mocker,
):
    dialog = mocker.Mock()
    dialog.DialogCode.Accepted = 1
    dialog.exec.return_value = dialog.DialogCode.Accepted
    dialog.selected_section_keys.return_value = (
        "activity.daily_activity_table",
    )

    dialog_class = mocker.patch(
        "app.ui.main_window.ReportSelectionDialog",
        return_value=dialog,
    )
    mocker.patch(
        "app.ui.main_window.save_settings",
    )
    mocker.patch(
        "app.ui.main_window.QFileDialog.getSaveFileName",
        return_value=("", ""),
    )

    window = MainWindow(
        settings=AppSettings(
            enabled_modules=("activity",),
            pdf_report_section_keys=(
                "activity.daily_activity_table",
            ),
        ),
    )
    qtbot.addWidget(window)

    window.handle_export_pdf_report()

    dialog_class.assert_called_once_with(
        enabled_module_keys=("activity",),
        selected_section_keys=(
            "activity.daily_activity_table",
        ),
        parent=window,
    )
