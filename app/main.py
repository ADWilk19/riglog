import sys
from pathlib import Path

from dotenv import load_dotenv
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.db.base import Base
from app.db.database import engine
from app.ui.main_window import MainWindow


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]

    import os

    project_root = Path(__file__).resolve().parents[1]
    env_path = project_root / ".env"

    load_dotenv(env_path)

    init_db()

    app = QApplication(sys.argv)

    qss_path = project_root / "assets" / "branding" / "theme.qss"
    icon_path = project_root / "assets" / "branding" / "logo_full_detailed.png"

    with open(qss_path, "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())

    app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
