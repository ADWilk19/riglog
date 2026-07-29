"""Definitions and validation for configurable RigLog modules."""

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class AppModule:
    """Metadata describing an optional RigLog health module."""

    key: str
    label: str
    description: str
    tab_class_path: str
    default_enabled: bool = True
    home_card_key: str | None = None
    dependencies: tuple[str, ...] = ()


# Preserve the application's current tab order.
MODULE_REGISTRY: tuple[AppModule, ...] = (
    AppModule(
        key="glucose",
        label="Glucose",
        description=(
            "Import and analyse glucose readings, time in range, "
            "variability, and meal-related patterns."
        ),
        tab_class_path=(
            "app.ui.tabs.glucose_tab.GlucoseTab"
        ),
        home_card_key="glucose",
    ),
    AppModule(
        key="activity",
        label="Activity",
        description=(
            "Review steps, goal adherence, streaks, and activity trends."
        ),
        tab_class_path=(
            "app.ui.tabs.activity_tab.ActivityTab"
        ),
        home_card_key="activity",
    ),
    AppModule(
        key="workouts",
        label="Workouts",
        description=(
            "Review workout history, training volume, progression, "
            "and session insights."
        ),
        tab_class_path=(
            "app.ui.tabs.workouts_tab.WorkoutTab"
        ),
        home_card_key="workouts",
    ),
    AppModule(
        key="nutrition",
        label="Nutrition",
        description=(
            "Manage foods and meals and review nutrition totals "
            "and meal patterns."
        ),
        tab_class_path=(
            "app.ui.tabs.nutrition_tab.NutritionTab"
        ),
        home_card_key="nutrition",
    ),
)

MODULES_BY_KEY: dict[str, AppModule] = {
    module.key: module for module in MODULE_REGISTRY
}

DEFAULT_ENABLED_MODULE_KEYS: tuple[str, ...] = tuple(
    module.key
    for module in MODULE_REGISTRY
    if module.default_enabled
)


def get_module(module_key: str) -> AppModule:
    """Return the module definition for a stable module key.

    Args:
        module_key: Module key such as ``"activity"``.

    Raises:
        KeyError: If the module key is not registered.
    """
    normalised_key = module_key.strip().lower()

    try:
        return MODULES_BY_KEY[normalised_key]
    except KeyError as exc:
        raise KeyError(f"Unknown RigLog module: {module_key!r}") from exc


def normalise_enabled_module_keys(
    module_keys: Iterable[str],
    *,
    require_one: bool = True,
) -> tuple[str, ...]:
    """Return valid module keys in stable registry order.

    Unknown keys, blank strings, duplicate keys, and non-string values are
    ignored. Input order does not affect the resulting application tab order.

    Args:
        module_keys: Candidate module keys from settings or user input.
        require_one: Whether an empty valid selection should raise an error.

    Raises:
        ValueError: If no valid module remains and ``require_one`` is true.
    """
    selected_keys = {
        module_key.strip().lower()
        for module_key in module_keys
        if isinstance(module_key, str) and module_key.strip()
    }

    enabled_keys = tuple(
        module.key
        for module in MODULE_REGISTRY
        if module.key in selected_keys
    )

    if require_one and not enabled_keys:
        raise ValueError("At least one RigLog health module must be enabled.")

    return enabled_keys
