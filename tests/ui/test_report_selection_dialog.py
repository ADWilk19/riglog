from app.ui.report_selection_dialog import ReportSelectionDialog


def test_report_selection_dialog_shows_enabled_module_sections_only(qtbot):
    dialog = ReportSelectionDialog(
        enabled_module_keys=("activity",),
    )
    qtbot.addWidget(dialog)

    keys = set(dialog.section_checkboxes)

    assert "activity.summary_metrics" in keys
    assert "activity.daily_steps_chart" in keys
    assert "glucose.summary_metrics" not in keys
    assert "nutrition.summary_metrics" not in keys
    assert "workouts.summary_metrics" not in keys


def test_report_selection_dialog_defaults_to_checked_pdf_sections(qtbot):
    dialog = ReportSelectionDialog(
        enabled_module_keys=("activity",),
    )
    qtbot.addWidget(dialog)

    assert dialog.selected_section_keys() == (
        "activity.summary_metrics",
        "activity.daily_steps_chart",
        "activity.weekly_steps_chart",
        "activity.daily_activity_table",
    )


def test_report_selection_dialog_respects_initial_selection(qtbot):
    dialog = ReportSelectionDialog(
        enabled_module_keys=("activity",),
        selected_section_keys=(
            "activity.weekly_steps_chart",
            "activity.summary_metrics",
        ),
    )
    qtbot.addWidget(dialog)

    assert dialog.selected_section_keys() == (
        "activity.summary_metrics",
        "activity.weekly_steps_chart",
    )


def test_report_selection_dialog_ignores_disabled_initial_selection(qtbot):
    dialog = ReportSelectionDialog(
        enabled_module_keys=("activity",),
        selected_section_keys=(
            "glucose.summary_metrics",
            "activity.summary_metrics",
        ),
    )
    qtbot.addWidget(dialog)

    assert dialog.selected_section_keys() == (
        "activity.summary_metrics",
    )


def test_report_selection_dialog_disables_ok_when_nothing_is_selected(qtbot):
    dialog = ReportSelectionDialog(
        enabled_module_keys=("activity",),
        selected_section_keys=(),
    )
    qtbot.addWidget(dialog)

    assert not dialog.ok_button.isEnabled()

    dialog.section_checkboxes["activity.summary_metrics"].setChecked(True)

    assert dialog.ok_button.isEnabled()
