import sys

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.db.base import Base
from app.services.database import engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def main() -> None:
    init_db()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
