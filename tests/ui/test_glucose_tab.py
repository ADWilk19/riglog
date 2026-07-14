from PySide6.QtCore import Qt

from app.ui.tabs.glucose_tab import GlucoseTab


def _build_glucose_tab(qtbot, mocker):
    """Create GlucoseTab without loading real data or running analytics."""
    load_readings = mocker.patch.object(
        GlucoseTab,
        "load_readings",
    )

    tab = GlucoseTab()
    qtbot.addWidget(tab)

    # Ignore the initial refresh triggered by GlucoseTab.__init__.
    load_readings.reset_mock()

    return tab, load_readings


def test_glucose_tab_renders(qtbot, mocker):
    tab, load_readings = _build_glucose_tab(qtbot, mocker)

    assert tab.clear_filters_button.text() == "Clear Filters"
    assert tab.meal_event_filter.currentText() == "All"
    assert tab.time_filter.currentText() == "All Time"
    assert tab.selected_range_filter is None

    load_readings.assert_not_called()


def test_clear_filters_resets_range_and_meal_event(qtbot, mocker):
    tab, load_readings = _build_glucose_tab(qtbot, mocker)

    tab.selected_range_filter = "high"
    tab._update_range_card_selection_state()

    tab.meal_event_filter.setCurrentText("Post-Dinner")
    load_readings.reset_mock()

    qtbot.mouseClick(
        tab.clear_filters_button,
        Qt.MouseButton.LeftButton,
    )

    assert tab.selected_range_filter is None
    assert tab.meal_event_filter.currentText() == "All"
    assert tab.high_label.property("selected") is False
    assert tab.active_filter_label.text() == ""

    load_readings.assert_called_once()


def test_range_card_click_toggles_selected_range(qtbot, mocker):
    tab, load_readings = _build_glucose_tab(qtbot, mocker)

    qtbot.mouseClick(
        tab.low_label,
        Qt.MouseButton.LeftButton,
    )

    assert tab.selected_range_filter == "low"
    assert tab.low_label.property("selected") is True
    assert tab.active_filter_label.text() == "Filtered: Low"
    load_readings.assert_called_once()

    load_readings.reset_mock()

    qtbot.mouseClick(
        tab.low_label,
        Qt.MouseButton.LeftButton,
    )

    assert tab.selected_range_filter is None
    assert tab.low_label.property("selected") is False
    assert tab.active_filter_label.text() == ""
    load_readings.assert_called_once()


def test_meal_event_breakdown_click_updates_dropdown(qtbot, mocker):
    tab, load_readings = _build_glucose_tab(qtbot, mocker)

    tab.range_breakdown_chart.meal_event_clicked.emit("Pre-Lunch")

    assert tab.meal_event_filter.currentText() == "Pre-Lunch"
    load_readings.assert_called_once()

    load_readings.reset_mock()

    tab.range_breakdown_chart.meal_event_clicked.emit("Pre-Lunch")

    assert tab.meal_event_filter.currentText() == "All"
    load_readings.assert_called_once()
