"""Main application window and configurable module-tab construction."""

from collections.abc import Callable, Mapping
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QWidget,
)

from app.core.modules import (
    get_module,
    normalise_enabled_module_keys,
)
from app.core.settings import (
    AppSettings,
    get_default_settings,
)
from app.ui.tabs.activity_tab import ActivityTab
from app.ui.tabs.glucose_tab import GlucoseTab
from app.ui.tabs.home_tab import HomeTab
from app.ui.tabs.nutrition_tab import NutritionTab
from app.ui.tabs.workouts_tab import WorkoutTab


TabFactory = Callable[[], QWidget]


def get_default_tab_factories() -> dict[str, TabFactory]:
    """Return factories for each configurable RigLog module tab."""
    return {
        "glucose": GlucoseTab,
        "activity": ActivityTab,
        "workouts": WorkoutTab,
        "nutrition": NutritionTab,
    }


class MainWindow(QMainWindow):
    """Top-level window containing Home and enabled health modules."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        *,
        tab_factories: Mapping[str, TabFactory] | None = None,
    ) -> None:
        super().__init__()

        project_root = Path(__file__).resolve().parents[2]
        icon_path = (
            project_root
            / "assets"
            / "branding"
            / "logo_full_detailed.png"
        )

        self.settings = (
            settings
            if settings is not None
            else get_default_settings()
        )

        self.enabled_module_keys = normalise_enabled_module_keys(
            self.settings.enabled_modules
        )

        self._tab_factories = (
            dict(tab_factories)
            if tab_factories is not None
            else get_default_tab_factories()
        )

        self.setWindowTitle("RigLog")
        self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1400, 900)

        self.tabs = QTabWidget()

        self.module_tabs: dict[str, QWidget] = {}
        self._create_enabled_module_tabs()

        self.home_tab = HomeTab(
            on_open_glucose=lambda: self.open_module("glucose"),
            on_open_activity=lambda: self.open_module("activity"),
            on_open_workouts=lambda: self.open_module("workouts"),
            on_open_nutrition=lambda: self.open_module("nutrition"),
        )

        self._connect_home_refresh_signals()

        self.tabs.addTab(self.home_tab, "Home")

        for module_key in self.enabled_module_keys:
            module = get_module(module_key)
            module_tab = self.module_tabs[module_key]
            self.tabs.addTab(module_tab, module.label)

        self.tabs.currentChanged.connect(self.handle_tab_changed)

        self.setCentralWidget(self.tabs)

    def _create_enabled_module_tabs(self) -> None:
        """Instantiate only the configured health-module tabs."""
        for module_key in self.enabled_module_keys:
            try:
                tab_factory = self._tab_factories[module_key]
            except KeyError as exc:
                raise KeyError(
                    f"No tab factory registered for module "
                    f"{module_key!r}."
                ) from exc

            module_tab = tab_factory()

            self.module_tabs[module_key] = module_tab

            # Preserve existing public attributes for enabled modules, such as
            # ``activity_tab`` and ``nutrition_tab``.
            setattr(
                self,
                f"{module_key}_tab",
                module_tab,
            )

    def _connect_home_refresh_signals(self) -> None:
        """Refresh Home when an enabled module reports updated data."""
        for module_tab in self.module_tabs.values():
            data_updated = getattr(
                module_tab,
                "data_updated",
                None,
            )

            if (
                data_updated is not None
                and hasattr(data_updated, "connect")
            ):
                data_updated.connect(
                    self.home_tab.refresh_data
                )

    def open_module(self, module_key: str) -> bool:
        """Navigate to an enabled module.

        Returns:
            ``True`` when the requested module is enabled and opened;
            otherwise ``False``.
        """
        module_tab = self.module_tabs.get(module_key)

        if module_tab is None:
            return False

        self.tabs.setCurrentWidget(module_tab)
        return True

    def handle_tab_changed(self, index: int) -> None:
        """Refresh Home cards whenever the Home tab is selected."""
        if self.tabs.widget(index) == self.home_tab:
            self.home_tab.refresh_data()
