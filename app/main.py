"""RigLog application entry point."""

import sys
from pathlib import Path

from dotenv import load_dotenv
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.core.settings import load_settings


def init_db() -> None:
    """Create any database tables that do not already exist."""
    # Import models explicitly so SQLAlchemy metadata is populated before
    # create_all() runs.
    from app.db import models  # noqa: F401
    from app.db.base import Base
    from app.db.database import engine

    Base.metadata.create_all(bind=engine)


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

    window = MainWindow(settings=settings)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
