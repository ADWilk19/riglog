from datetime import date, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMessageBox

from app.ui.tabs.workouts_tab import WorkoutTab


def _card_texts(card) -> set[str]:
    """Return all non-empty label text contained in a SummaryCard."""
    return {
        label.text()
        for label in card.findChildren(QLabel)
        if label.text()
    }


def _mock_workout_services(mocker):
    """Mock WorkoutTab service dependencies with deterministic test data."""
    metrics = mocker.patch(
        "app.ui.tabs.workouts_tab.get_workout_summary_metrics",
        return_value={
            "total_sessions": 3,
            "weekly_sessions": 1,
            "total_sets": 12,
            "total_volume_kg": 4250.5,
            "average_duration_minutes": 52.5,
            "most_recent_workout": {
                "routine": "Pull",
                "workout_type": "Strength",
                "started_at": datetime(2026, 7, 16, 18, 30),
            },
        },
    )

    recent_sessions = mocker.patch(
        "app.ui.tabs.workouts_tab.get_recent_workout_sessions",
        return_value=[
            {
                "started_at": datetime(2026, 7, 16, 18, 30),
                "workout_type": "Strength",
                "routine": "Pull",
                "duration_minutes": 52.5,
                "perceived_effort": 8,
                "set_count": 4,
                "total_volume_kg": 1650.0,
                "notes": "Deadlifts and rows",
            }
        ],
    )

    volume_by_exercise = mocker.patch(
        "app.ui.tabs.workouts_tab.get_volume_by_exercise",
        return_value=[
            {
                "exercise_name": "Deadlift",
                "total_sets": 4,
                "total_reps": 20,
                "total_volume_kg": 1650.0,
            },
            {
                "exercise_name": "Seated Row",
                "total_sets": 3,
                "total_reps": 30,
                "total_volume_kg": 1200.0,
            },
        ],
    )

    calorie_analysis = mocker.patch(
        "app.ui.tabs.workouts_tab.get_workout_session_calorie_analysis",
        return_value=[
            {
                "started_at": datetime(2026, 7, 16, 18, 30),
                "workout_type": "Strength",
                "duration_minutes": 52.5,
                "total_sets": 4,
                "total_reps": 20,
                "total_volume_kg": 1650.0,
                "average_load_per_rep": 82.5,
                "max_weight_kg": 120.0,
                "calories_burned": 310.25,
                "calories_per_minute": 5.91,
                "calories_per_kg_lifted": 0.1880,
            }
        ],
    )

    exercises = mocker.patch(
        "app.ui.tabs.workouts_tab.get_exercises_with_workout_data",
        return_value=[
            {
                "exercise_id": 1,
                "exercise_name": "Deadlift",
            }
        ],
    )

    progression = mocker.patch(
        "app.ui.tabs.workouts_tab.get_exercise_progression",
        return_value=[
            {
                "date": date(2026, 7, 16),
                "max_weight_kg": 120.0,
            }
        ],
    )

    progression_summary = mocker.patch(
        "app.ui.tabs.workouts_tab.get_exercise_progression_summary",
        return_value={
            "max_weight_kg": 120.0,
            "reps_at_max_weight": 5,
            "date_of_max_weight": date(2026, 7, 16),
        },
    )

    # Keep the tests focused on widget state rather than Matplotlib rendering.
    mocker.patch(
        "app.ui.tabs.workouts_tab."
        "WorkoutVolumeByExerciseChart.plot_volume_by_exercise",
    )
    mocker.patch(
        "app.ui.tabs.workouts_tab."
        "WorkoutExerciseProgressionChart.plot_progression",
    )

    return {
        "metrics": metrics,
        "recent_sessions": recent_sessions,
        "volume_by_exercise": volume_by_exercise,
        "calorie_analysis": calorie_analysis,
        "exercises": exercises,
        "progression": progression,
        "progression_summary": progression_summary,
    }


def _build_workout_tab(qtbot, mocker):
    services = _mock_workout_services(mocker)

    tab = WorkoutTab()
    qtbot.addWidget(tab)

    return tab, services


def test_workout_tab_renders_without_crashing(qtbot, mocker):
    tab, _ = _build_workout_tab(qtbot, mocker)

    assert tab.import_button.text() == "Import Workout CSV"
    assert tab.refresh_button.text() == "Refresh"
    assert tab.clear_imported_button.text() == "Clear Imported Workouts"

    assert tab.total_sessions_card is not None
    assert tab.recent_sessions_table is not None
    assert tab.volume_by_exercise_table is not None
    assert tab.workout_calorie_table is not None


def test_workout_tab_populates_summary_cards_and_tables(qtbot, mocker):
    tab, _ = _build_workout_tab(qtbot, mocker)

    assert "3" in _card_texts(tab.total_sessions_card)
    assert "1" in _card_texts(tab.weekly_sessions_card)
    assert "12" in _card_texts(tab.total_sets_card)
    assert "4250.5" in _card_texts(tab.total_volume_card)
    assert "52.5" in _card_texts(tab.average_duration_card)
    assert "Pull" in _card_texts(tab.recent_workout_card)

    assert tab.recent_sessions_table.rowCount() == 1
    assert tab.recent_sessions_table.item(0, 1).text() == "Strength"
    assert tab.recent_sessions_table.item(0, 2).text() == "Pull"
    assert tab.recent_sessions_table.item(0, 6).text() == "1650.0 kg"
    assert tab.recent_sessions_table.item(0, 7).text() == "Deadlifts and rows"

    assert tab.volume_by_exercise_table.rowCount() == 2
    assert tab.volume_by_exercise_table.item(0, 0).text() == "Deadlift"
    assert tab.volume_by_exercise_table.item(0, 1).text() == "4"
    assert tab.volume_by_exercise_table.item(0, 2).text() == "20"
    assert tab.volume_by_exercise_table.item(0, 3).text() == "1650.0 kg"

    assert tab.workout_calorie_table.rowCount() == 1
    assert tab.workout_calorie_table.item(0, 8).text() == "310.25"
    assert tab.workout_calorie_table.item(0, 9).text() == "5.91"


def test_refresh_button_updates_summary_cards(qtbot, mocker):
    tab, services = _build_workout_tab(qtbot, mocker)

    services["metrics"].return_value = {
        "total_sessions": 4,
        "weekly_sessions": 2,
        "total_sets": 16,
        "total_volume_kg": 5100.0,
        "average_duration_minutes": 55.0,
        "most_recent_workout": {
            "routine": "Legs",
            "workout_type": "Strength",
            "started_at": datetime(2026, 7, 17, 12, 0),
        },
    }

    qtbot.mouseClick(
        tab.refresh_button,
        Qt.MouseButton.LeftButton,
    )

    assert "4" in _card_texts(tab.total_sessions_card)
    assert "2" in _card_texts(tab.weekly_sessions_card)
    assert "16" in _card_texts(tab.total_sets_card)
    assert "5100.0" in _card_texts(tab.total_volume_card)
    assert "Legs" in _card_texts(tab.recent_workout_card)

    assert services["metrics"].call_count == 2
    assert services["recent_sessions"].call_count == 2
    assert services["volume_by_exercise"].call_count == 2
    assert services["calorie_analysis"].call_count == 2


def test_csv_import_success_refreshes_workout_data(qtbot, mocker):
    tab, _ = _build_workout_tab(qtbot, mocker)

    mocker.patch(
        "app.ui.tabs.workouts_tab.QFileDialog.getOpenFileName",
        return_value=("/tmp/workouts.csv", "CSV Files (*.csv)"),
    )

    import_workout_csv = mocker.patch(
        "app.ui.tabs.workouts_tab.import_workout_csv",
        return_value={
            "sessions": 2,
            "sets": 10,
            "skipped_sets": 1,
        },
    )

    information = mocker.patch.object(
        QMessageBox,
        "information",
        return_value=QMessageBox.StandardButton.Ok,
    )

    refresh_data = mocker.patch.object(
        tab,
        "refresh_data",
    )

    qtbot.mouseClick(
        tab.import_button,
        Qt.MouseButton.LeftButton,
    )

    import_workout_csv.assert_called_once_with("/tmp/workouts.csv")
    information.assert_called_once()

    assert information.call_args.args[1] == "Import complete"
    assert "Imported 2 sessions and 10 sets" in information.call_args.args[2]
    assert "Skipped 1 duplicate sets" in information.call_args.args[2]

    refresh_data.assert_called_once()


def test_csv_import_failure_shows_error_without_refreshing(qtbot, mocker):
    tab, _ = _build_workout_tab(qtbot, mocker)

    mocker.patch(
        "app.ui.tabs.workouts_tab.QFileDialog.getOpenFileName",
        return_value=("/tmp/broken.csv", "CSV Files (*.csv)"),
    )

    import_workout_csv = mocker.patch(
        "app.ui.tabs.workouts_tab.import_workout_csv",
        side_effect=ValueError("Invalid exercise key"),
    )

    critical = mocker.patch.object(
        QMessageBox,
        "critical",
        return_value=QMessageBox.StandardButton.Ok,
    )

    refresh_data = mocker.patch.object(
        tab,
        "refresh_data",
    )

    qtbot.mouseClick(
        tab.import_button,
        Qt.MouseButton.LeftButton,
    )

    import_workout_csv.assert_called_once_with("/tmp/broken.csv")
    critical.assert_called_once()

    assert critical.call_args.args[1] == "Import failed"
    assert "Invalid exercise key" in critical.call_args.args[2]

    refresh_data.assert_not_called()
