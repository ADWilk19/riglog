"""Tests for RigLog application settings."""

import json

import pytest

from app.core.modules import DEFAULT_ENABLED_MODULE_KEYS
from app.core.settings import (
    DEFAULT_STEP_TARGET,
    AppSettings,
    should_show_setup,
    get_default_settings,
    load_settings,
    save_settings,
)


def test_default_settings_preserve_existing_full_app_experience():
    settings = get_default_settings()

    assert settings.setup_complete is True
    assert settings.enabled_modules == DEFAULT_ENABLED_MODULE_KEYS
    assert settings.step_target == DEFAULT_STEP_TARGET


def test_missing_settings_file_returns_defaults(tmp_path):
    settings_file = tmp_path / "missing-settings.json"

    settings = load_settings(settings_file)

    assert settings == get_default_settings()


def test_settings_can_be_saved_and_reloaded(tmp_path):
    settings_file = tmp_path / "settings.json"
    expected = AppSettings(
        setup_complete=False,
        enabled_modules=("activity", "nutrition"),
        step_target=7_500,
    )

    save_settings(expected, settings_file)
    actual = load_settings(settings_file)

    assert actual == expected


def test_save_creates_parent_directory(tmp_path):
    settings_file = tmp_path / "nested" / "config" / "settings.json"

    save_settings(get_default_settings(), settings_file)

    assert settings_file.is_file()


def test_enabled_modules_are_normalised_to_registry_order(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps(
            {
                "setup_complete": True,
                "enabled_modules": [
                    "nutrition",
                    "unknown",
                    "activity",
                    "nutrition",
                ],
                "step_target": 10_000,
            }
        ),
        encoding="utf-8",
    )

    settings = load_settings(settings_file)

    assert settings.enabled_modules == (
        "activity",
        "nutrition",
    )


def test_no_valid_enabled_modules_falls_back_to_defaults(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps(
            {
                "enabled_modules": ["sleep", "unknown"],
            }
        ),
        encoding="utf-8",
    )

    settings = load_settings(settings_file)

    assert settings.enabled_modules == DEFAULT_ENABLED_MODULE_KEYS


def test_non_list_enabled_modules_fall_back_to_defaults(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps(
            {
                "enabled_modules": "activity",
            }
        ),
        encoding="utf-8",
    )

    settings = load_settings(settings_file)

    assert settings.enabled_modules == DEFAULT_ENABLED_MODULE_KEYS


@pytest.mark.parametrize(
    "invalid_step_target",
    [
        0,
        -1,
        True,
        "10000",
        None,
    ],
)
def test_invalid_step_target_falls_back_to_default(
    tmp_path,
    invalid_step_target,
):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps(
            {
                "step_target": invalid_step_target,
            }
        ),
        encoding="utf-8",
    )

    settings = load_settings(settings_file)

    assert settings.step_target == DEFAULT_STEP_TARGET


def test_invalid_setup_complete_value_falls_back_to_default(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps(
            {
                "setup_complete": "yes",
            }
        ),
        encoding="utf-8",
    )

    settings = load_settings(settings_file)

    assert settings.setup_complete is True


def test_malformed_json_returns_defaults(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        '{"enabled_modules": [',
        encoding="utf-8",
    )

    settings = load_settings(settings_file)

    assert settings == get_default_settings()


def test_non_object_json_returns_defaults(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        '["activity", "nutrition"]',
        encoding="utf-8",
    )

    settings = load_settings(settings_file)

    assert settings == get_default_settings()


def test_unknown_settings_are_preserved_across_round_trip(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps(
            {
                "setup_complete": True,
                "enabled_modules": ["activity"],
                "step_target": 8_000,
                "future_setting": {
                    "enabled": True,
                },
            }
        ),
        encoding="utf-8",
    )

    settings = load_settings(settings_file)

    assert settings.extra_settings == {
        "future_setting": {
            "enabled": True,
        }
    }

    save_settings(settings, settings_file)

    saved_payload = json.loads(
        settings_file.read_text(encoding="utf-8")
    )

    assert saved_payload["future_setting"] == {
        "enabled": True,
    }


def test_saved_settings_use_readable_json_format(tmp_path):
    settings_file = tmp_path / "settings.json"

    save_settings(
        AppSettings(
            enabled_modules=("activity",),
            step_target=9_000,
        ),
        settings_file,
    )

    content = settings_file.read_text(encoding="utf-8")

    assert content.endswith("\n")
    assert '"enabled_modules": [' in content
    assert '"step_target": 9000' in content


def test_atomic_save_leaves_no_temporary_file(tmp_path):
    settings_file = tmp_path / "settings.json"

    save_settings(get_default_settings(), settings_file)

    temporary_files = list(
        tmp_path.glob(f".{settings_file.name}.*.tmp")
    )

    assert temporary_files == []


def test_setup_is_required_when_setup_is_incomplete():
    settings = AppSettings(
        setup_complete=False,
    )

    assert should_show_setup(settings) is True


def test_setup_is_not_required_when_setup_is_complete():
    settings = AppSettings(
        setup_complete=True,
    )

    assert should_show_setup(settings) is False
