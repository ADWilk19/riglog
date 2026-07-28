"""Tests for settings-driven MainWindow tab construction."""

import pytest
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from app.core.settings import AppSettings
from app.ui import main_window as main_window_module
from app.ui.main_window import MainWindow


MODULE_KEYS = (
    "glucose",
    "activity",
    "workouts",
    "nutrition",
)


class FakeHomeTab(QWidget):
    """Lightweight HomeTab replacement for MainWindow tests."""

    def __init__(
        self,
        *,
        on_open_glucose,
        on_open_activity,
        on_open_workouts,
        on_open_nutrition,
    ):
        super().__init__()

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
