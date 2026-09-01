from app.core.report_sections import (
    REPORT_SECTION_REGISTRY,
    get_default_report_section_keys,
    get_report_sections_for_modules,
    normalise_report_section_keys,
)


def test_report_section_keys_are_unique():
    keys = [
        section.key
        for section in REPORT_SECTION_REGISTRY
    ]

    assert len(keys) == len(set(keys))


def test_report_sections_are_filtered_to_enabled_modules():
    sections = get_report_sections_for_modules(
        ("activity",),
        export_kind="pdf",
    )

    assert sections
    assert {
        section.module_key
        for section in sections
    } == {"activity"}


def test_report_sections_ignore_disabled_modules():
    sections = get_report_sections_for_modules(
        ("nutrition",),
        export_kind="pdf",
    )

    keys = {
        section.key
        for section in sections
    }

    assert "nutrition.summary_metrics" in keys
    assert "activity.summary_metrics" not in keys
    assert "glucose.summary_metrics" not in keys


def test_report_sections_are_filtered_by_export_kind():
    sections = get_report_sections_for_modules(
        ("activity",),
        export_kind="csv",
    )

    keys = {
        section.key
        for section in sections
    }

    assert "activity.summary_metrics" in keys
    assert "activity.daily_activity_table" in keys
    assert "activity.daily_steps_chart" not in keys
    assert "activity.weekly_steps_chart" not in keys


def test_default_report_section_keys_follow_enabled_modules():
    keys = get_default_report_section_keys(
        ("glucose", "activity"),
        export_kind="pdf",
    )

    assert "glucose.summary_metrics" in keys
    assert "activity.summary_metrics" in keys
    assert "nutrition.summary_metrics" not in keys
    assert "workouts.summary_metrics" not in keys


def test_normalise_report_section_keys_ignores_unknown_disabled_and_wrong_export_keys():
    keys = normalise_report_section_keys(
        (
            "activity.weekly_steps_chart",
            "activity.summary_metrics",
            "glucose.summary_metrics",
            "unknown.section",
        ),
        enabled_module_keys=("activity",),
        export_kind="csv",
    )

    assert keys == ("activity.summary_metrics",)


def test_normalise_report_section_keys_uses_registry_order():
    keys = normalise_report_section_keys(
        (
            "activity.weekly_steps_chart",
            "activity.summary_metrics",
            "activity.daily_steps_chart",
        ),
        enabled_module_keys=("activity",),
        export_kind="pdf",
    )

    assert keys == (
        "activity.summary_metrics",
        "activity.daily_steps_chart",
        "activity.weekly_steps_chart",
    )
