import sys
from datetime import datetime

from PySide6.QtWidgets import QApplication

from app.db import models
from app.db.base import Base
from app.db.database import engine
from app.services.glucose.importer import add_glucose_reading
from app.services.glucose.importer import import_diabetes_m_csv
from app.ui.main_window import MainWindow

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
