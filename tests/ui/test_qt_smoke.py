from PySide6.QtWidgets import QLabel


def test_qt_widget_renders(qtbot):
    label = QLabel("RigLog")

    qtbot.addWidget(label)
    label.show()

    assert label.text() == "RigLog"
    assert label.isVisible()
