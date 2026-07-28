"""Tests for RigLog application filesystem paths."""

from pathlib import Path

import pytest

from app.core import app_paths


def test_explicit_base_directory_builds_expected_paths(tmp_path):
    base_dir = tmp_path / "riglog-data"

    paths = app_paths.get_app_paths(base_dir)

    assert paths.data_dir == base_dir
    assert paths.settings_file == base_dir / "settings.json"
    assert paths.database_file == base_dir / "riglog.db"
    assert paths.fitbit_tokens_file == base_dir / "fitbit_tokens.json"
    assert paths.exports_dir == base_dir / "exports"


def test_explicit_base_directory_takes_precedence_over_environment(
    tmp_path,
    monkeypatch,
):
    explicit_dir = tmp_path / "explicit"
    environment_dir = tmp_path / "environment"

    monkeypatch.setenv(
        app_paths.DATA_DIR_ENV_VAR,
        str(environment_dir),
    )

    result = app_paths.get_app_data_dir(explicit_dir)

    assert result == explicit_dir


def test_environment_directory_is_used_when_no_explicit_path(
    tmp_path,
    monkeypatch,
):
    environment_dir = tmp_path / "environment"

    monkeypatch.setenv(
        app_paths.DATA_DIR_ENV_VAR,
        str(environment_dir),
    )

    result = app_paths.get_app_data_dir()

    assert result == environment_dir


def test_blank_environment_directory_is_ignored(
    tmp_path,
    monkeypatch,
):
    qt_root = tmp_path / "qt-data"

    monkeypatch.setenv(app_paths.DATA_DIR_ENV_VAR, "   ")
    monkeypatch.setattr(
        app_paths,
        "_get_qt_data_root",
        lambda: qt_root,
    )

    result = app_paths.get_app_data_dir()

    assert result == qt_root / app_paths.APP_DIRECTORY_NAME


def test_qt_data_directory_is_used_as_default(
    tmp_path,
    monkeypatch,
):
    qt_root = tmp_path / "qt-data"

    monkeypatch.delenv(
        app_paths.DATA_DIR_ENV_VAR,
        raising=False,
    )
    monkeypatch.setattr(
        app_paths,
        "_get_qt_data_root",
        lambda: qt_root,
    )

    result = app_paths.get_app_data_dir()

    assert result == qt_root / app_paths.APP_DIRECTORY_NAME


def test_get_app_paths_does_not_create_directories_by_default(
    tmp_path,
):
    base_dir = tmp_path / "riglog-data"

    app_paths.get_app_paths(base_dir)

    assert not base_dir.exists()


def test_get_app_paths_can_create_required_directories(
    tmp_path,
):
    base_dir = tmp_path / "riglog-data"

    paths = app_paths.get_app_paths(
        base_dir,
        create=True,
    )

    assert paths.data_dir.is_dir()
    assert paths.exports_dir.is_dir()
    assert not paths.settings_file.exists()
    assert not paths.database_file.exists()
    assert not paths.fitbit_tokens_file.exists()


def test_qt_data_root_raises_when_no_location_is_available(
    monkeypatch,
):
    monkeypatch.setattr(
        app_paths.QStandardPaths,
        "writableLocation",
        lambda _location_type: "",
    )

    with pytest.raises(
        RuntimeError,
        match="could not resolve a writable application data directory",
    ):
        app_paths._get_qt_data_root()
