"""Tests for RigLog startup decisions."""

from app.core.settings import AppSettings, should_show_setup


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
