"""Tests for configurable RigLog module definitions."""

import pytest

from app.core.modules import (
    DEFAULT_ENABLED_MODULE_KEYS,
    MODULE_REGISTRY,
    MODULES_BY_KEY,
    get_module,
    normalise_enabled_module_keys,
)


def test_module_registry_contains_expected_modules_in_stable_order():
    assert tuple(module.key for module in MODULE_REGISTRY) == (
        "glucose",
        "activity",
        "workouts",
        "nutrition",
    )


def test_module_registry_keys_are_unique():
    module_keys = [module.key for module in MODULE_REGISTRY]

    assert len(module_keys) == len(set(module_keys))
    assert len(MODULES_BY_KEY) == len(MODULE_REGISTRY)


def test_all_current_modules_are_enabled_by_default():
    assert DEFAULT_ENABLED_MODULE_KEYS == (
        "glucose",
        "activity",
        "workouts",
        "nutrition",
    )


def test_get_module_normalises_key():
    module = get_module(" Activity ")

    assert module.key == "activity"
    assert module.label == "Activity"


def test_get_module_rejects_unknown_key():
    with pytest.raises(KeyError, match="Unknown RigLog module"):
        get_module("sleep")


def test_normalise_enabled_module_keys_returns_registry_order():
    result = normalise_enabled_module_keys(
        ["nutrition", "activity", "glucose"]
    )

    assert result == (
        "glucose",
        "activity",
        "nutrition",
    )


def test_normalise_enabled_module_keys_removes_duplicates():
    result = normalise_enabled_module_keys(
        ["activity", "activity", "nutrition"]
    )

    assert result == (
        "activity",
        "nutrition",
    )


def test_normalise_enabled_module_keys_ignores_unknown_and_invalid_values():
    result = normalise_enabled_module_keys(
        ["activity", "unknown", "", "   ", None, 10]
    )

    assert result == ("activity",)


def test_normalise_enabled_module_keys_requires_one_valid_module():
    with pytest.raises(
        ValueError,
        match="At least one RigLog health module must be enabled",
    ):
        normalise_enabled_module_keys(["unknown", ""])


def test_normalise_enabled_module_keys_can_allow_empty_selection():
    result = normalise_enabled_module_keys(
        [],
        require_one=False,
    )

    assert result == ()
