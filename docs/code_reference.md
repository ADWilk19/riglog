# 🛠️ RigLog Code Reference

This document summarises the key classes, functions, services, UI components, and tests in the RigLog codebase.

Its purpose is to make debugging quicker by answering:

- What exists?
- Where does it live?
- What does it do?
- What does it read or write?
- Which tests are likely to fail if it changes?

---

## 🧭 Current App Shape

RigLog is a local desktop health-analysis app built around a small set of domain modules:

- **Glucose** — Diabetes:M import, glucose analytics, AGP, time-in-range, meal-event analysis, insulin/carb notes, PDF export.
- **Activity** — Fitbit daily and intraday activity import, summary metrics, goal adherence, step trends, activity/glucose alignment.
- **Environment** — daily weather import, Open-Meteo support, temperature/glucose alignment, location-aware weather rows.
- **Workouts** — exercise catalogue, Push/Pull/Legs routines, workout CSV import, volume/progression analytics, calorie alignment.
- **Nutrition** — food database, meal templates, meal logs, nutrition totals, CSV import, nutrition/glucose response analysis.

Primary architecture:

```text
app/ui      -> renders PySide6 tabs and widgets
app/services -> owns import, transformation, analytics, and pure-ish business logic
app/db      -> SQLAlchemy models/session/database setup
tests       -> service/model/importer regression tests
```

---

## 🧱 Database Models

Location: `app/db/models.py`

### `GlucoseReading`

**Type:** Class  
**Location:** `app/db/models.py`

Represents one glucose reading imported from Diabetes:M or another future glucose source.

**Key fields:**

- `glucose_value`
- `recorded_at`
- `source`
- `notes`
- `carbs_g`
- `humalog_u`
- `tresiba_u`

**Read/write usage:**

- Written by `app/services/glucose/importer.py`.
- Read by glucose analytics, glucose UI, nutrition/glucose response analysis, and cross-module overlays.
- Updated by glucose note and inline numeric-field editing helpers.

**Debugging notes:**

- `recorded_at` is the primary timestamp for daily averages, AGP, time-of-day profiles, meal-event classification, and cross-module alignment.
- `carbs_g`, `humalog_u`, and `tresiba_u` are optional contextual fields added after import.

---

### `DailyActivity`

**Type:** Class  
**Location:** `app/db/models.py`

Represents one daily activity summary, usually sourced from Fitbit.

**Key fields:**

- `activity_date`
- `steps`
- `calories_burned`
- `distance_km`
- `active_minutes`
- `source`

**Read/write usage:**

- Written by daily Fitbit import services.
- Read by Activity tab charts, Home dashboard cards, goal-adherence metrics, and daily glucose/activity overlays.

**Debugging notes:**

- Unique by `activity_date` and `source`.
- Daily-grain table; do not use for intraday step-density analysis.

---

### `IntradayActivity`

**Type:** Class  
**Location:** `app/db/models.py`

Represents intraday activity intervals such as 15-minute step-density and calorie-burn rows.

**Key fields:**

- `recorded_at`
- `steps`
- `calories_burned`
- `distance_km`
- `source`

**Read/write usage:**

- Written by Fitbit intraday importer.
- Read by intraday glucose/activity alignment and workout-session calorie analysis.

**Debugging notes:**

- Unique by `recorded_at` and `source`.
- This is the table to inspect when intraday overlays or workout calories look empty.

---

### `DailyEnvironment`

**Type:** Class  
**Location:** `app/db/models.py`

Represents daily weather/environment data for one date, location, and source.

**Key fields:**

- `environment_date`
- `location_label`
- `latitude`
- `longitude`
- `avg_temperature_c`
- `min_temperature_c`
- `max_temperature_c`
- `source`
- `notes`

**Read/write usage:**

- Written by manual environment CSV importer and Open-Meteo importer.
- Read by temperature/glucose alignment services and Glucose tab environment tables/charts.

**Debugging notes:**

- Unique by `environment_date`, `location_label`, and `source`.
- Location-aware design prevents multiple locations for the same date from accidentally being treated as duplicate temperature observations.

---

### `Exercise`

**Type:** Class  
**Location:** `app/db/models.py`

Represents one reusable exercise catalogue item.

**Key fields:**

- `exercise_key`
- `name`
- `category`
- `primary_muscle`
- `equipment`
- `notes`

**Relationships:**

- Linked to `WorkoutSet`.
- Linked to `WorkoutRoutineExercise`.

**Debugging notes:**

- `exercise_key` is the stable import identifier.
- Exercise names are user-facing labels and should not be treated as the only durable identifier.

---

### `WorkoutRoutine`

**Type:** Class  
**Location:** `app/db/models.py`

Represents a reusable workout routine/template, such as Push, Pull, or Legs.

**Key fields:**

- `name`
- `notes`

**Relationships:**

- Has many `WorkoutRoutineExercise` records.
- Has many `WorkoutSession` records.

**Debugging notes:**

- Used to connect imported sessions to seeded routine templates.

---

### `WorkoutRoutineExercise`

**Type:** Class  
**Location:** `app/db/models.py`

Links one exercise to one workout routine.

**Key fields:**

- `routine_id`
- `exercise_id`
- `display_order`

**Debugging notes:**

- Preserves exercise order within each routine.
- Unique by `routine_id` and `exercise_id`.

---

### `WorkoutSession`

**Type:** Class  
**Location:** `app/db/models.py`

Represents one completed workout occurrence.

**Key fields:**

- `started_at`
- `ended_at`
- `routine_id`
- `workout_type`
- `perceived_effort`
- `notes`
- `source`

**Relationships:**

- Belongs to `WorkoutRoutine`.
- Has many `WorkoutSet` records.

**Debugging notes:**

- Session-level grain only.
- Set-level fields such as weight, reps, and set number belong in `WorkoutSet`.
- Workout calorie analysis requires both `started_at` and `ended_at`.

---

### `WorkoutSet`

**Type:** Class  
**Location:** `app/db/models.py`

Represents one performed set within a workout session.

**Key fields:**

- `session_id`
- `exercise_id`
- `set_number` / `set_index`
- `weight_kg`
- `reps`
- `rir`
- `notes`

**Relationships:**

- Belongs to `WorkoutSession`.
- Belongs to `Exercise`.

**Debugging notes:**

- This is set-level grain.
- Unique by session, exercise, and set number/index.
- Most workout analytics derive from this table.

---

### `Food`

**Type:** Class  
**Location:** `app/db/models.py`

Represents one reusable food item with nutrition values stored per 100g.

**Key fields:**

- `food_key`
- `name`
- `brand`
- `serving_notes`
- `calories_per_100g`
- `carbs_per_100g`
- `protein_per_100g`
- `fat_per_100g`
- `fibre_per_100g`
- `salt_per_100g`
- `source`
- `notes`

**Debugging notes:**

- Nutrition calculations scale per-100g values by quantity in grams.
- Used by manual food entry, CSV import, meal templates, meal logs, and nutrition summary metrics.

---

### `MealTemplate`

**Type:** Class  
**Location:** `app/db/models.py`

Represents one reusable meal definition.

**Key fields:**

- `meal_key`
- `name`
- `meal_event`
- `source`
- `notes`

**Relationships:**

- Has many `MealTemplateItem` records.
- Referenced by `MealLog`.

**Debugging notes:**

- Template-level grain; it defines what a meal usually contains.
- Actual consumption time and portion multiplier belong in `MealLog`.

---

### `MealTemplateItem`

**Type:** Class  
**Location:** `app/db/models.py`

Links one food to one meal template with a gram quantity.

**Key fields:**

- `meal_template_id`
- `food_id`
- `quantity_g`
- `display_order`

**Debugging notes:**

- Meal template nutrition totals are calculated by summing each linked food scaled by `quantity_g`.

---

### `MealLog`

**Type:** Class  
**Location:** `app/db/models.py`

Represents one logged meal occurrence.

**Key fields:**

- `logged_at`
- `meal_template_id`
- `meal_event`
- `portion_multiplier`
- `source`
- `notes`

**Debugging notes:**

- Meal logs are the bridge between Nutrition and Glucose analysis.
- Post-meal glucose response services align this timestamp with subsequent glucose readings.

---

## 🍬 Glucose Services

### `add_glucose_reading`

**Type:** Function  
**Location:** `app/services/glucose/importer.py`

Creates and persists a single glucose reading.

**Inputs:**

- `glucose_value`
- `recorded_at`
- `source`
- `notes`

**Writes to:**

- `glucose_readings`

**Debugging notes:**

- Lightweight helper for manual/test insertion.
- Does not do duplicate detection.

---

### `import_diabetes_m_csv`

**Type:** Function  
**Location:** `app/services/glucose/importer.py`

Imports readings from a Diabetes:M CSV export.

**Expected input fields:**

- `glucose`
- `DateTimeFormatted`
- `notes`

**Outputs:**

- Integer count of newly inserted readings.

**Writes to:**

- `glucose_readings`

**Debugging notes:**

- Opens CSV with `utf-8-sig`.
- Skips the metadata row, then treats the next row as headers.
- Deduplicates by timestamp, glucose value, and source `diabetes_m`.
- Contains a Diabetes:M export workaround for observed bad years `2048` and `2049`, remapping them back by 23 years.
- Raises `ValueError` for dates outside the accepted range after correction.

---

### `get_all_glucose_readings`

**Type:** Function  
**Location:** `app/services/glucose/analysis.py`

Returns all stored glucose readings ordered newest first.

**Reads from:**

- `glucose_readings`

---

### `get_all_glucose_readings_with_meal_event`

**Type:** Function  
**Location:** `app/services/glucose/analysis.py`

Returns glucose readings enriched with meal-event keys and labels.

**Inputs:**

- `days`: optional lookback window.

**Outputs per reading:**

- `id`
- `glucose_value`
- `recorded_at`
- `source`
- `notes`
- `carbs_g`
- `humalog_u`
- `tresiba_u`
- `meal_event`
- `meal_event_label`

**Reads from:**

- `glucose_readings`

**Debugging notes:**

- Uses `classify_meal_event` from `app/services/event_classifier.py`.
- This is a major data source for Glucose tab tables, charts, filters, and dose analysis.

---

### `get_glucose_reading_by_id`

**Type:** Function  
**Location:** `app/services/glucose/analysis.py`

Fetches one glucose reading by database primary key.

**Reads from:**

- `glucose_readings`

---

### `glucose_records_to_df`

**Type:** Function  
**Location:** `app/services/glucose/analysis.py`

Converts enriched glucose dictionaries into a cleaned pandas DataFrame.

**Outputs columns include:**

- `id`
- `glucose_value`
- `recorded_at`
- `meal_event`
- `time_of_day_hours`
- `time_bucket_minute`
- `date`

**Debugging notes:**

- Use this when downstream calculations expect typed pandas columns rather than raw dictionaries.

---

### `calculate_agp`

**Type:** Function  
**Location:** `app/services/glucose/analysis.py`

Calculates AGP percentile bands by time of day.

**Inputs:**

- `df`
- `bucket_minutes`, default `15`

**Outputs columns:**

- `bucket_minute`
- `time_label`
- `hour_decimal`
- `p10`
- `p25`
- `p50`
- `p75`
- `p90`
- `count`

**Debugging notes:**

- If AGP is blank, inspect whether the DataFrame has valid `recorded_at` and `glucose_value` columns.

---

### `calculate_time_in_range_breakdown`

**Type:** Function  
**Location:** `app/services/glucose/analysis.py`

Returns glucose band counts and percentages.

**Bands:**

- `hypo`: `< 3.3`
- `low`: `3.3–4.0`
- `target`: `4.0–10.0`
- `high`: `10.0–15.0`
- `hyper`: `> 15.0`

**Debugging notes:**

- Used by summary cards and dashboard metrics.

---

### `calculate_glucose_variability_metrics`

**Type:** Function  
**Location:** `app/services/glucose/analysis.py`

Calculates core variability metrics.

**Outputs:**

- `mean_glucose`
- `sd`
- `cv_pct`
- `gmi`

**Debugging notes:**

- GMI is calculated by converting mmol/L to mg/dL and applying the consensus GMI formula.
- Empty inputs return `None` metrics rather than raising.

---

### `calculate_insulin_effectiveness`

**Type:** Function  
**Location:** `app/services/glucose/analysis.py`

Summarises dose effectiveness by previous meal event.

**How it works:**

- Sorts readings chronologically.
- Shifts previous `carbs_g`, `humalog_u`, and meal event onto the next reading.
- Treats the current glucose value as the outcome of the previous dose.

**Outputs:**

- `meal_event_label`
- `avg_ratio_g_per_u`
- `ratio_sd`
- `avg_outcome_glucose`
- `count`
- `standard_ratio_g_per_u`

**Debugging notes:**

- Requires populated carbs and Humalog values.
- Empty output usually means the glucose table has no dose/context values yet.

---

### `calculate_time_based_effectiveness`

**Type:** Function  
**Location:** `app/services/glucose/analysis.py`

Compares recent versus older dose outcomes by previous meal event.

**Inputs:**

- `readings`
- `days`, default `7`

**Outputs:**

- `meal_event_label`
- `older_avg`
- `recent_avg`
- `change`

**Debugging notes:**

- Returns empty when there is insufficient older or recent comparison data.

---

### `calculate_glucose_dashboard_metrics`

**Type:** Function  
**Location:** `app/services/glucose/analysis.py`

Bundles common dashboard analytics.

**Outputs:**

- `range_breakdown`
- `variability`
- `agp`

---

### `get_glucose_summary`

**Type:** Function  
**Location:** `app/services/glucose/analysis.py`

Returns simple aggregate statistics across all glucose readings.

**Outputs:**

- `count`
- `avg`
- `min`
- `max`

---

### `get_daily_average_glucose`

**Type:** Function  
**Location:** `app/services/glucose/analysis.py`

Aggregates readings into daily averages for charting.

**Outputs per date:**

- `date`
- `avg`
- `count`

---

### `get_time_of_day_profile`

**Type:** Function  
**Location:** `app/services/glucose/analysis.py`

Aggregates readings into time-of-day buckets.

**Inputs:**

- `readings`
- `bucket_minutes`, default `30`

**Outputs per bucket:**

- `bucket_minutes`
- `time_label`
- `avg`
- `count`
- `values`

---

### `get_meal_event_boxplot_data`

**Type:** Function  
**Location:** `app/services/glucose/analysis.py`

Groups glucose values by meal event for boxplot rendering.

**Debugging notes:**

- Current plotted order focuses on breakfast, lunch, and dinner pre/post windows.
- Night and before-bed readings may be visible elsewhere but are not always included in this boxplot helper.

---

### `get_time_in_range_metrics`

**Type:** Function  
**Location:** `app/services/glucose/analysis.py`

Calculates time-in-range counts and percentages from reading dictionaries.

**Outputs:**

- `total`
- `hypo_count`, `hypo_pct`
- `low_count`, `low_pct`
- `target_count`, `target_pct`
- `high_count`, `high_pct`
- `hyper_count`, `hyper_pct`

---

### `update_glucose_note`

**Type:** Function  
**Location:** `app/services/glucose/analysis.py`

Updates or clears the free-text note attached to a glucose reading.

**Writes to:**

- `glucose_readings.notes`

---

### `update_glucose_field`

**Type:** Function  
**Location:** `app/services/glucose/analysis.py`

Updates a numeric contextual glucose field.

**Supported UI fields:**

- `carbs_g`
- `humalog_u`
- `tresiba_u`

**Writes to:**

- `glucose_readings`

**Debugging notes:**

- Used by inline editing in the Glucose tab table.

---

## 🍬 Glucose UI

### `apply_chart_theme`

**Type:** Function  
**Location:** `app/ui/tabs/glucose_tab.py`

Applies the shared dark matplotlib chart theme.

**Debugging notes:**

- Used across Glucose tab figures.
- If chart colours look inconsistent, inspect this helper first.

---

### `NumericTableWidgetItem`

**Type:** Class  
**Location:** `app/ui/tabs/glucose_tab.py`

QTableWidget item that preserves numeric sorting for glucose values.

**Debugging notes:**

- Prevents table sorting glucose values lexicographically.

---

### `rolling_average`

**Type:** Function  
**Location:** `app/ui/tabs/glucose_tab.py`

Returns a trailing rolling average list for chart display.

**Default window:** `7`

---

### `draw_agp_figure`

**Type:** Function  
**Location:** `app/ui/tabs/glucose_tab.py`

Draws the AGP chart onto an existing matplotlib figure.

**Reads from:**

- AGP DataFrame returned by `calculate_agp`.

**Debugging notes:**

- Used by on-screen AGP and PDF export.

---

### `GlucoseTrendChart`

**Type:** Class  
**Location:** `app/ui/tabs/glucose_tab.py`

Matplotlib canvas for daily average glucose chart.

**Key method:**

- `plot_daily_average(daily_data)`

**Debugging notes:**

- Plots daily average plus 7-day rolling trend.
- Includes hypo/target/hyper background bands.

---

### `GlucoseProfileChart`

**Type:** Class  
**Location:** `app/ui/tabs/glucose_tab.py`

Matplotlib canvas for average glucose by time of day.

**Key method:**

- `plot_profile(profile_data)`

---

### `MealEventBoxPlotChart`

**Type:** Class  
**Location:** `app/ui/tabs/glucose_tab.py`

Matplotlib canvas for glucose distribution by meal event.

**Key method:**

- `plot_boxplot(boxplot_data)`

---

### `GlucoseTab`

**Type:** Class  
**Location:** `app/ui/tabs/glucose_tab.py`

Main glucose analytics tab for import, review, analysis, note editing, inline dose/context editing, and PDF export.

**Build methods:**

- `_build_toolbar`
- `_build_summary_panel`
- `_build_agp_chart`
- `_build_chart`
- `_build_profile_chart`
- `_build_meal_boxplot_chart`
- `_build_insulin_effectiveness_table`
- `_build_dose_effectiveness_chart`
- `_build_time_effectiveness_table`
- `_build_legend`
- `_build_table`
- `_build_notes_panel`

**Core behaviours:**

- Imports Diabetes:M CSVs.
- Filters by meal event and time range.
- Shows summary cards, AGP, daily trend, time-of-day profile, meal-event boxplot, dose-effectiveness analysis, time-based improvement table, readings table, and notes editor.
- Exports a PDF report with summary metrics and key charts.
- Persists notes and inline numeric edits.

**Important handlers:**

- `load_readings`
- `handle_import_csv`
- `handle_export_pdf`
- `handle_row_selection`
- `handle_save_note`
- `handle_cell_edit`

**Debugging notes:**

- `_get_filtered_readings` applies both meal-event and time-range filtering.
- `load_readings` is the refresh hub for charts, tables, and summary cards.
- Inline table edits only persist columns for carbs, Humalog, and Tresiba.

---

## 🏃 Activity Services

### Fitbit client/import flow

**Typical locations:**

- `app/services/activity/fitbit_client.py`
- `app/services/activity/importer.py`

**What it does:**

- Authenticates with Fitbit.
- Imports daily step summaries.
- Imports intraday activity intervals.
- Handles token refresh/retry behaviour.

**Writes to:**

- `daily_activity`
- `activity_intraday`

**Debugging notes:**

- Daily summaries power Activity tab trend charts and Home cards.
- Intraday rows power hourly charts, meal-window activity summaries, and workout calorie analysis.

---

### Activity analysis helpers

**Typical location:** `app/services/activity/analysis.py`

**Key functions:**

- `aggregate_weekly_steps`
- `calculate_goal_adherence`
- `calculate_step_streaks`
- `calculate_weekly_summary_metrics`
- `get_activity_summary`
- `get_activity_summary_cards`
- `get_activity_insight_metrics`
- `get_steps_by_hour`
- `get_steps_by_event_window`
- `get_intraday_activity_rows`

**Reads from:**

- `daily_activity`
- `activity_intraday`

**Debugging notes:**

- Daily functions should not be used where intraday precision is needed.
- If hourly/event-window analysis is empty, inspect `activity_intraday` first.

---

## 🔀 Cross-Module Activity ↔ Glucose Services

### Activity/glucose alignment helpers

**Typical location:** `app/services/activity/analysis.py` or cross-module analysis module.

**Key functions:**

- `get_activity_glucose_event_summary`
- `get_activity_glucose_correlations`
- `get_daily_activity_glucose_overlay`
- `get_intraday_activity_glucose_alignment`

**Reads from:**

- `glucose_readings`
- `daily_activity`
- `activity_intraday`

**Debugging notes:**

- Event-window summaries use the same meal-event windows as glucose classification.
- Daily overlay is date-grain.
- Intraday alignment is bucket-grain, commonly 30-minute buckets.
- Correlation outputs are exploratory, not clinical conclusions.

---

## 🌡️ Environment Services

### Manual environment CSV importer

**Typical location:** `app/services/environment/importer.py`

Imports daily environment/weather rows from CSV.

**Writes to:**

- `daily_environment`

**Debugging notes:**

- Useful fallback when Open-Meteo import is unavailable or when testing a single known date.

---

### Open-Meteo importer/client boundary

**Typical location:** `app/services/environment/importer.py`

**Key functions:**

- `normalise_open_meteo_daily_json`
- `import_open_meteo_historical_weather_for_location`

**Writes to:**

- `daily_environment`

**Debugging notes:**

- Location label is important when multiple weather locations exist.
- Normalisation should remain testable without network access.

---

### Environment/glucose analysis

**Typical location:** `app/services/environment/analysis.py`

**Key functions:**

- `get_daily_environment_rows`
- `calculate_daily_temperature_glucose_alignment`
- `get_daily_temperature_glucose_alignment`
- `get_temperature_glucose_bucket_summary`

**Reads from:**

- `daily_environment`
- `glucose_readings`

**Debugging notes:**

- Alignment is daily-grain.
- Bucket summaries are best interpreted only once enough dates exist per bucket.

---

## 🏋️ Workout Services

### `seed_workout_catalogue`

**Type:** Function  
**Location:** `app/services/workouts/seed_data.py`

Seeds the default workout exercise catalogue and Push/Pull/Legs routine mappings.

**Inputs:**

- `session`: optional SQLAlchemy session for test injection.

**Outputs:**

- `exercises`
- `routines`
- `routine_exercises`

**Writes to:**

- `exercises`
- `workout_routines`
- `workout_routine_exercises`

**Debugging notes:**

- Safe to run repeatedly.
- First run should create records.
- Second run should return zero created records.
- Exercises are matched by `exercise_key`.

---

### `import_workout_csv`

**Type:** Function  
**Location:** `app/services/workouts/importer.py`

Imports spreadsheet-style workout logs from CSV.

**Expected input columns:**

- `Date`
- `Workout`
- `Exercise`
- `Exercise ID`
- `Set #`
- `Weight`
- `Reps`
- `Notes`

**Optional timing columns:**

- `Start Time`
- `End Time`
- `Duration Minutes`
- `Duration`

**Outputs:**

- `sessions`
- `sets`
- `skipped_sets`

**Writes to:**

- `workout_sessions`
- `workout_sets`

**Debugging notes:**

- Resolves exercises by `Exercise ID` / `exercise_key` first.
- Falls back to exercise name where needed.
- Duplicate sets are skipped using session, exercise, and set number.
- If no start time is supplied, sessions default to `09:00` to preserve earlier importer behaviour.
- Session timing enables duration metrics and workout calorie analysis.

---

### `clear_imported_workout_data`

**Type:** Function  
**Location:** `app/services/workouts/maintenance.py`

Deletes imported workout sessions and associated sets for a given source.

**Inputs:**

- `source`, default `workout_csv`
- `session`: optional SQLAlchemy session for test injection.

**Outputs:**

- `sets`
- `sessions`

**Writes to:**

- `workout_sets`
- `workout_sessions`

**Preserves:**

- `exercises`
- `workout_routines`
- `workout_routine_exercises`

---

### Workout analysis functions

**Location:** `app/services/workouts/analysis.py`

#### `get_workout_summary_metrics`

Returns top-level workout dashboard metrics.

**Outputs:**

- `total_sessions`
- `weekly_sessions`
- `average_duration_minutes`
- `most_recent_workout`
- `total_sets`
- `total_volume_kg`

#### `get_volume_by_exercise`

Aggregates total training volume by exercise.

**Volume formula:**

```text
weight_kg * reps
```

#### `get_volume_by_workout_type`

Aggregates total training volume by workout type.

#### `get_recent_workout_sessions`

Returns recent sessions for table display.

#### `get_exercises_with_workout_data`

Returns exercises with at least one logged set.

#### `get_exercise_progression`

Returns selected-exercise progression by workout date.

#### `get_exercise_progression_summary`

Returns summary-card metrics for the selected exercise progression view.

#### `get_workout_session_calorie_analysis`

Aligns workout session time windows with intraday activity calorie burn.

**Reads from:**

- `workout_sessions`
- `workout_sets`
- `workout_routines`
- `exercises`
- `activity_intraday`

**Debugging notes:**

- Workout calorie analysis only includes sessions with both start and end timestamps.
- Calories are derived from activity intervals and are not persisted on workout sessions.

---

## 🏋️ Workout UI

### Workout tab

**Typical location:** `app/ui/tabs/workout_tab.py`

**What it does:**

- Displays workout summary metrics.
- Shows volume by exercise.
- Shows selected-exercise progression.
- Shows recent workout sessions and calorie analysis.
- Provides refresh/clear/import-style controls as implemented.

**Likely dependencies:**

- `get_workout_summary_metrics`
- `get_volume_by_exercise`
- `get_exercises_with_workout_data`
- `get_exercise_progression`
- `get_exercise_progression_summary`
- `get_workout_session_calorie_analysis`
- `clear_imported_workout_data`

**Debugging notes:**

- Empty progression dropdown usually means no `workout_sets` exist yet, even if the catalogue is seeded.
- Empty calorie table usually means missing workout session timing or missing intraday calories.

---

## 🍽️ Nutrition Services

### `calculate_food_totals`

**Type:** Function  
**Location:** `app/services/nutrition/analysis.py`

Calculates calories and macros for one food at a given quantity in grams.

**Inputs:**

- Food row/object.
- Quantity in grams.

**Outputs:**

- Calories.
- Carbs.
- Protein.
- Fat.
- Fibre.
- Salt.

**Debugging notes:**

- Core formula is per-100g value multiplied by `quantity_g / 100`.

---

### `calculate_meal_template_totals`

**Type:** Function  
**Location:** `app/services/nutrition/analysis.py`

Calculates total calories and macros for all foods in a meal template.

**Reads from:**

- `meal_templates`
- `meal_template_items`
- `foods`

---

### `calculate_logged_meal_totals`

**Type:** Function  
**Location:** `app/services/nutrition/analysis.py`

Calculates nutrition totals for a logged meal, applying `portion_multiplier`.

**Reads from:**

- `meal_logs`
- `meal_templates`
- `meal_template_items`
- `foods`

---

### `get_nutrition_summary_metrics`

**Type:** Function  
**Location:** `app/services/nutrition/analysis.py`

Returns summary-card metrics for Nutrition tab and Home dashboard.

**Likely outputs:**

- Logged meals.
- Average calories.
- Average carbs/macros.
- Recent meal/log totals.

---

### `get_recent_meal_logs`

**Type:** Function  
**Location:** `app/services/nutrition/analysis.py`

Returns recent logged meals for table display.

**Reads from:**

- `meal_logs`
- `meal_templates`

---

### `get_meal_template_totals_rows`

**Type:** Function  
**Location:** `app/services/nutrition/analysis.py`

Returns reusable meal template totals for the Nutrition tab.

**Reads from:**

- `meal_templates`
- `meal_template_items`
- `foods`

---

### `get_post_meal_glucose_response_rows`

**Type:** Function  
**Location:** `app/services/nutrition/analysis.py`

Aligns logged meals with subsequent glucose readings after the meal window.

**Reads from:**

- `meal_logs`
- `meal_templates`
- `foods`
- `glucose_readings`

**Debugging notes:**

- This is the key Nutrition ↔ Glucose payoff function.
- Empty output usually means either no logged meals exist, no later glucose readings exist, or the response window is too narrow.

---

### `get_macro_glucose_response_by_meal_event`

**Type:** Function  
**Location:** `app/services/nutrition/analysis.py`

Groups macro totals and post-meal glucose response by meal event.

**Debugging notes:**

- Useful for comparing breakfast/lunch/dinner response patterns.
- Treat as exploratory until enough logged meals exist per event.

---

### `get_meal_template_glucose_response_summary`

**Type:** Function  
**Location:** `app/services/nutrition/analysis.py`

Summarises typical glucose response by reusable meal template.

**Debugging notes:**

- Useful for identifying reusable meals associated with stable or elevated post-meal glucose responses.

---

### Nutrition demo seed

**Typical location:** `app/services/nutrition/demo_seed.py`

Seeds sample foods, meal templates, and meal logs for demo/testing use.

**Writes to:**

- `foods`
- `meal_templates`
- `meal_template_items`
- `meal_logs`

**Debugging notes:**

- Should be idempotent.
- Useful for UI screenshots and regression testing without personal data.

---

### Nutrition CSV importer

**Typical location:** `app/services/nutrition/importer.py`

Imports foods and/or nutrition data from CSV.

**Writes to:**

- `foods`
- potentially `meal_templates`, `meal_template_items`, and `meal_logs` depending on importer scope.

**Debugging notes:**

- Validate required columns before writing.
- Use stable keys where available to avoid name-only duplicate logic.

---

## 🍽️ Nutrition UI

### Nutrition tab

**Typical location:** `app/ui/tabs/nutrition_tab.py`

**What it does:**

- Displays nutrition summary cards.
- Shows recent meal logs.
- Shows meal template totals.
- Surfaces Nutrition ↔ Glucose response tables where implemented.

**Likely dependencies:**

- `get_nutrition_summary_metrics`
- `get_recent_meal_logs`
- `get_meal_template_totals_rows`
- `get_post_meal_glucose_response_rows`
- `get_macro_glucose_response_by_meal_event`
- `get_meal_template_glucose_response_summary`

**Debugging notes:**

- If the tab is empty, check demo seed/import status before changing UI code.
- If glucose response tables are empty, inspect meal log timestamps versus glucose reading timestamps.

---

## 🏠 Home UI

### Home tab

**Typical location:** `app/ui/tabs/home_tab.py`

**What it does:**

- Shows high-level app/dashboard cards.
- Surfaces glucose, activity, workout, and nutrition readiness/summary states.
- Refreshes after data import/sync events where wired.

**Debugging notes:**

- Home card values should generally come from service-layer functions, not duplicated UI calculations.

---

## 🧩 Shared UI Widgets

### `SummaryCard`

**Typical location:** `app/ui/widgets/summary_card.py`

Reusable card widget for dashboard metrics.

**Common methods:**

- `set_content(...)`
- `set_variant(...)`

**Debugging notes:**

- Used heavily by Glucose, Activity, Workout, Nutrition, and Home views.
- Variant styling controls success/warning/danger/neutral presentation.

---

## 🧪 Test Reference

### Glucose tests

**Typical locations:**

- `tests/services/glucose/test_importer.py`
- `tests/services/glucose/test_analysis.py`

**Likely coverage:**

- Diabetes:M CSV import.
- Duplicate handling.
- Date correction/validation.
- Time-in-range calculations.
- Variability metrics.
- AGP/dashboard analytics.
- Note/field update helpers where tested.

---

### Activity tests

**Typical locations:**

- `tests/services/activity/test_fitbit_client.py`
- `tests/services/activity/test_importer.py`
- `tests/services/activity/test_analysis.py`

**Likely coverage:**

- Fitbit retry/token behaviour.
- Daily import idempotency.
- Intraday import idempotency.
- Goal adherence.
- Weekly aggregation.
- Step streaks.
- Intraday/event-window analytics.

---

### Environment tests

**Typical locations:**

- `tests/services/environment/test_importer.py`
- `tests/services/environment/test_analysis.py`

**Likely coverage:**

- Manual CSV import.
- Open-Meteo normalisation.
- Missing-value handling.
- Location-aware daily environment rows.
- Temperature/glucose alignment.
- Temperature bucket summaries.

---

### Workout tests

#### `test_workout_models.py`

**Location:** `tests/db/test_workout_models.py`

Smoke-tests workout database model relationships.

**Covers:**

- Routine creation.
- Exercise creation.
- Session creation.
- Set creation.
- Relationship traversal.

#### `test_seed_data.py`

**Location:** `tests/services/workouts/test_seed_data.py`

Tests workout catalogue seeding.

**Covers:**

- Expected exercise, routine, and routine-exercise counts.
- Idempotency.
- Routine display order.
- Exercise key population.

#### `test_analysis.py`

**Location:** `tests/services/workouts/test_analysis.py`

Tests workout analysis service functions.

**Covers:**

- Summary metrics.
- Empty database behaviour.
- Volume by exercise.
- Volume by workout type.
- Recent workout session output.
- Exercises with logged workout data.
- Exercise progression by date.
- Exercise progression summary metrics.
- Workout session calorie analysis.

#### `test_importer.py`

**Location:** `tests/services/workouts/test_importer.py`

Tests workout CSV import.

**Covers:**

- Session and set creation.
- Idempotency.
- Unknown exercise handling.
- Missing required column handling.
- Exercise resolution by stable exercise ID.

#### `test_maintenance.py`

**Location:** `tests/services/workouts/test_maintenance.py`

Tests workout data maintenance utilities.

**Covers:**

- Clearing imported workout sessions.
- Clearing associated workout sets.
- Preserving exercises.
- Preserving workout routines.
- Preserving routine/exercise mappings.
- Returning zero counts when no matching source exists.

---

### Nutrition tests

**Typical locations:**

- `tests/services/nutrition/test_analysis.py`
- `tests/services/nutrition/test_demo_seed.py`
- `tests/services/nutrition/test_importer.py`

**Likely coverage:**

- Food total calculations.
- Meal template total calculations.
- Logged meal totals and portion multipliers.
- Demo seed creation/idempotency.
- Food CSV import validation/idempotency.
- Nutrition summary metrics.
- Recent meal log rows.
- Meal template total rows.
- Post-meal glucose response rows.
- Macro/glucose response grouped by meal event.
- Meal-template glucose response summaries.

---

## 🔍 Debugging Playbook

### If Glucose charts are empty

Check:

1. `glucose_readings` has rows.
2. `recorded_at` values are valid datetimes.
3. `_get_filtered_readings` is not excluding everything by meal event/time range.
4. `calculate_agp`, `get_daily_average_glucose`, and `get_time_of_day_profile` receive non-empty input.

---

### If dose-effectiveness tables are empty

Check:

1. Glucose rows have `carbs_g` and `humalog_u` populated.
2. Readings are sorted chronologically before shift logic.
3. There is a later glucose reading after each dose/context row.

---

### If Activity charts are empty

Check:

1. `daily_activity` contains rows for daily charts.
2. `activity_intraday` contains rows for hourly/intraday charts.
3. Fitbit token refresh has not failed.
4. Date filters are not excluding all imported data.

---

### If Environment alignment is empty

Check:

1. `daily_environment` contains rows.
2. `glucose_readings` contain readings on matching dates.
3. `location_label` filtering is not excluding all rows.
4. Weather dates and glucose dates use the same local-date interpretation.

---

### If Workout progression is empty

Check:

1. `exercises` catalogue has been seeded.
2. `workout_sessions` has imported sessions.
3. `workout_sets` has rows linked to exercise IDs.
4. The selected exercise has at least one logged set.

---

### If Workout calorie analysis is empty

Check:

1. `workout_sessions.started_at` and `workout_sessions.ended_at` are populated.
2. `activity_intraday.calories_burned` has values for the same time windows.
3. Session timestamps and activity timestamps are aligned to the same date/time basis.

---

### If Nutrition totals look wrong

Check:

1. Food values are per 100g.
2. Meal template item quantities are in grams.
3. Logged meal `portion_multiplier` is applied exactly once.
4. CSV import did not interpret blanks as zeros incorrectly.

---

### If Nutrition ↔ Glucose response is empty

Check:

1. `meal_logs` exist.
2. Meal logs have sensible `logged_at` timestamps.
3. Glucose readings exist after the meal time.
4. The post-meal response window is wide enough.
5. Demo/test data dates overlap.

---

## 🧾 Maintenance Notes

- Prefer service-layer calculations over UI-layer calculations.
- Keep importers idempotent where possible.
- Keep demo data free of personal glucose/activity data.
- Use stable keys (`exercise_key`, `food_key`, `meal_key`) instead of display names for imports and deduplication.
- Keep cross-module outputs explicitly labelled as exploratory health insights, not medical recommendations.
- When adding a new UI table/chart, add a pure service-layer function first where practical.

---

## 📌 Known High-Value Files to Review During Refactors

```text
app/db/models.py
app/db/database.py
app/main.py
app/services/event_classifier.py
app/services/glucose/importer.py
app/services/glucose/analysis.py
app/services/activity/importer.py
app/services/activity/analysis.py
app/services/environment/importer.py
app/services/environment/analysis.py
app/services/workouts/importer.py
app/services/workouts/analysis.py
app/services/workouts/maintenance.py
app/services/workouts/seed_data.py
app/services/nutrition/analysis.py
app/services/nutrition/demo_seed.py
app/services/nutrition/importer.py
app/ui/tabs/glucose_tab.py
app/ui/tabs/activity_tab.py
app/ui/tabs/workout_tab.py
app/ui/tabs/nutrition_tab.py
app/ui/tabs/home_tab.py
app/ui/widgets/summary_card.py
```

