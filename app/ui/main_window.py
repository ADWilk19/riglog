"""Main application window and configurable module-tab construction."""

from collections.abc import Callable, Mapping
from pathlib import Path
from importlib import import_module

import inspect

from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QWidget,
)

from app.core.modules import (
    AppModule,
    get_module,
    normalise_enabled_module_keys,
)
from app.core.settings import (
    AppSettings,
    get_default_settings,
    save_settings,
)
from app.ui.tabs.home_tab import HomeTab
from app.ui.module_management_dialog import ModuleManagementDialog


TabFactory = Callable[[], QWidget]


def resolve_tab_factory(module: AppModule) -> TabFactory:
    """Resolve a module's tab factory from its registered import path."""
    module_path, separator, class_name = (
        module.tab_class_path.rpartition(".")
    )

    if not separator or not module_path or not class_name:
        raise ValueError(
            f"Invalid tab class path for module {module.key!r}: "
            f"{module.tab_class_path!r}"
        )

    imported_module = import_module(module_path)

    try:
        tab_factory = getattr(imported_module, class_name)
    except AttributeError as exc:
        raise ImportError(
            f"Could not resolve tab class "
            f"{module.tab_class_path!r}."
        ) from exc

    if not callable(tab_factory):
        raise TypeError(
            f"Registered tab factory for module "
            f"{module.key!r} is not callable."
        )

    return tab_factory


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
            else None
        )

        self.setWindowTitle("RigLog")
        self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1400, 900)

        self.tabs = QTabWidget()

        self.module_tabs: dict[str, QWidget] = {}
        self._create_enabled_module_tabs()

        self.home_tab = HomeTab(
            enabled_module_keys=self.enabled_module_keys,
            step_target=self.settings.step_target,
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

        self._build_settings_menu()

    def _get_tab_factory(
        self,
        module_key: str,
    ) -> TabFactory:
        """Return an injected or registry-backed module tab factory."""
        if self._tab_factories is not None:
            try:
                return self._tab_factories[module_key]
            except KeyError as exc:
                raise KeyError(
                    f"No tab factory registered for module "
                    f"{module_key!r}."
                ) from exc

        module = get_module(module_key)
        return resolve_tab_factory(module)

    def _create_enabled_module_tabs(self) -> None:
        """Instantiate only the configured health-module tabs."""
        for module_key in self.enabled_module_keys:
            tab_factory = self._get_tab_factory(module_key)
            module_tab = self._create_module_tab(module_key, tab_factory)

            self.module_tabs[module_key] = module_tab

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

    def _build_settings_menu(self) -> None:
        """Build application settings menu actions."""
        settings_menu = self.menuBar().addMenu("Settings")

        manage_modules_action = QAction("Manage Modules...", self)
        manage_modules_action.setObjectName("manageModulesAction")
        manage_modules_action.triggered.connect(self.handle_manage_modules)

        settings_menu.addAction(manage_modules_action)

    def handle_manage_modules(self) -> None:
        """Open module-management dialog and persist accepted changes."""
        dialog = ModuleManagementDialog(settings=self.settings, parent=self)

        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        updated_settings = dialog.to_settings()
        save_settings(updated_settings)
        self.settings = updated_settings

        QMessageBox.information(
            self,
            "Modules updated",
            "Your module settings have been saved. "
            "Restart RigLog for the changes to take effect.",
        )

    def _create_module_tab(
            self,
            module_key: str,
            tab_factory: TabFactory,
        ) -> QWidget:
        """Create a module tab, passing supported configuration where available."""
        if module_key != "activity":
            return tab_factory()

        try:
            signature = inspect.signature(tab_factory)
        except (TypeError, ValueError):
            return tab_factory()

        parameters = signature.parameters

        accepts_step_target = (
            "step_target" in parameters
            or any(
                parameter.kind == inspect.Parameter.VAR_KEYWORD
                for parameter in parameters.values()
            )
        )

        if accepts_step_target:
            return tab_factory(step_target=self.settings.step_target)

        return tab_factory()
