"""RigLog application entry point."""

import sys
from pathlib import Path

from dotenv import load_dotenv
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog

from app.core.settings import (
    AppSettings,
    load_settings,
    save_settings,
    should_show_setup
)


def init_db() -> None:
    """Create any database tables that do not already exist."""
    # Import models explicitly so SQLAlchemy metadata is populated before
    # create_all() runs.
    from app.db import models  # noqa: F401
    from app.db.base import Base
    from app.db.database import engine

    Base.metadata.create_all(bind=engine)


def resolve_startup_settings(settings: AppSettings) -> AppSettings | None:
    """
    Return settings to use for MainWindow startup.

    If setup is incomplete, run the setup wizard. Returning None means startup
    should stop, usually because the user cancelled setup.
    """
    if not should_show_setup(settings):
        return settings

    # Delay the UI import until after .env has been loaded.
    from app.ui.setup_wizard import SetupWizard

    setup_wizard = SetupWizard(settings=settings)

    if setup_wizard.exec() != QDialog.DialogCode.Accepted:
        return None

    completed_settings = setup_wizard.to_settings()
    save_settings(completed_settings)

    return completed_settings


def create_main_window(settings: AppSettings):
    """Create, show, and return the main application window."""
    # Delay the UI import until after .env has been loaded.
    from app.ui.main_window import MainWindow

    window = MainWindow(settings=settings)
    window.show()

    return window


def main() -> None:
    """Initialise and launch RigLog."""
    project_root = Path(__file__).resolve().parents[1]
    env_path = project_root / ".env"

    # Environment configuration must be loaded before importing modules that
    # initialise database connections or other environment-backed services.
    load_dotenv(env_path)

    app = QApplication(sys.argv)
    app.setApplicationName("RigLog")
    app.setOrganizationName("RigLog")

    settings = load_settings()

    init_db()

    # Delay the UI import until after .env has been loaded.
    from app.ui.main_window import MainWindow
    from app.ui.setup_wizard import SetupWizard

    qss_path = project_root / "assets" / "branding" / "theme.qss"
    icon_path = (
        project_root
        / "assets"
        / "branding"
        / "logo_full_detailed.png"
    )

    with qss_path.open("r", encoding="utf-8") as qss_file:
        app.setStyleSheet(qss_file.read())

    app.setWindowIcon(QIcon(str(icon_path)))

    settings = resolve_startup_settings(settings)

    if not settings:
        return

    window = create_main_window(settings)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
