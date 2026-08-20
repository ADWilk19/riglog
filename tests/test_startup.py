"""Tests for RigLog startup decisions."""

from app.core.settings import AppSettings, should_show_setup

import sys
from types import SimpleNamespace

from PySide6.QtWidgets import QDialog

from app import main as app_main
from app.core.settings import AppSettings


def test_completed_setup_routes_to_main_window():
    settings = AppSettings(
        setup_complete=True,
    )

    assert should_show_setup(settings) is False


def test_incomplete_setup_routes_to_setup_flow():
    settings = AppSettings(
        setup_complete=False,
    )

    assert should_show_setup(settings) is True


def test_resolve_startup_settings_returns_existing_settings_when_setup_complete(
    monkeypatch,
):
    settings = AppSettings(
        setup_complete=True,
        enabled_modules=("glucose", "activity"),
        step_target=8_000,
    )
    saved_settings = []

    monkeypatch.setattr(app_main, "save_settings", saved_settings.append)

    result = app_main.resolve_startup_settings(settings)

    assert result is settings
    assert saved_settings == []


def test_resolve_startup_settings_runs_wizard_and_saves_completed_settings(
    monkeypatch,
):
    initial_settings = AppSettings(
        setup_complete=False,
        enabled_modules=("glucose",),
        step_target=8_000,
    )
    completed_settings = AppSettings(
        setup_complete=True,
        enabled_modules=("glucose", "activity"),
        step_target=9_500,
    )
    observed = {}
    saved_settings = []

    class FakeSetupWizard:
        def __init__(self, settings):
            observed["settings"] = settings

        def exec(self):
            return QDialog.DialogCode.Accepted

        def to_settings(self):
            return completed_settings

    monkeypatch.setitem(
        sys.modules,
        "app.ui.setup_wizard",
        SimpleNamespace(SetupWizard=FakeSetupWizard),
    )
    monkeypatch.setattr(app_main, "save_settings", saved_settings.append)

    result = app_main.resolve_startup_settings(initial_settings)

    assert observed["settings"] is initial_settings
    assert result is completed_settings
    assert saved_settings == [completed_settings]


def test_resolve_startup_settings_returns_none_when_setup_is_cancelled(
    monkeypatch,
):
    initial_settings = AppSettings(
        setup_complete=False,
        enabled_modules=("glucose",),
        step_target=8_000,
    )
    saved_settings = []

    class FakeSetupWizard:
        def __init__(self, settings):
            self.settings = settings

        def exec(self):
            return QDialog.DialogCode.Rejected

        def to_settings(self):
            raise AssertionError("Cancelled setup should not produce settings.")

    monkeypatch.setitem(
        sys.modules,
        "app.ui.setup_wizard",
        SimpleNamespace(SetupWizard=FakeSetupWizard),
    )
    monkeypatch.setattr(app_main, "save_settings", saved_settings.append)

    result = app_main.resolve_startup_settings(initial_settings)

    assert result is None
    assert saved_settings == []


def test_create_main_window_passes_settings_and_shows_window(monkeypatch):
    settings = AppSettings(
        setup_complete=True,
        enabled_modules=("nutrition",),
        step_target=10_000,
    )

    class FakeMainWindow:
        def __init__(self, settings):
            self.settings = settings
            self.was_shown = False

        def show(self):
            self.was_shown = True

    monkeypatch.setitem(
        sys.modules,
        "app.ui.main_window",
        SimpleNamespace(MainWindow=FakeMainWindow),
    )

    window = app_main.create_main_window(settings)

    assert window.settings is settings
    assert window.was_shown is True
