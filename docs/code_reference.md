# 🛠️ RigLog Code Reference

This document summarises key classes, methods, and functions in the RigLog codebase.

Its purpose is to make debugging quicker by answering:

- What exists?

- Where does it live?

- What does it do?

- What does it read or write?

---

## 🧱 Database Models

Location: `app/db/models.py`

### `GlucoseReading`

**Type:**
Class

**Location:**
`app/db/models.py`

**What it does:**
Represents one glucose reading imported from Diabetes:M or another future glucose source.

**Key fields:**

- `glucose_value`

- `recorded_at`

- `source`

- `notes`

- `carbs_g`

- `humalog_u`

- `tresiba_u`

**Debugging notes:**

- Used heavily by glucose analysis and import services.

- `recorded_at` is the core timestamp used for daily, AGP, and meal-event analysis.

---

### `DailyActivity`

**Type:**
Class

**Location:**
`app/db/models.py`

**What it does:**
Represents one daily activity summary, usually sourced from Fitbit.

**Key fields:**

- `activity_date`

- `steps`

- `calories_burned`

- `distance_km`

- `active_minutes`

- `source`

**Debugging notes:**

- Unique by `activity_date` and `source`.

- Used for daily activity charts, goal adherence, and daily glucose/activity comparison.

---

### `IntradayActivity`

**Type:**
Class

**Location:**
`app/db/models.py`

**What it does:**
Represents intraday activity data such as step-density and calorie burn intervals.

**Key fields:**

- `recorded_at`

- `steps`

- `calories_burned`

- `distance_km`

- `source`

**Debugging notes:**

- Unique by `recorded_at` and `source`.

- Used for intraday glucose/activity alignment.

---

### `DailyEnvironment`

**Type:**
Class

**Location:**
`app/db/models.py`

**What it does:**
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

**Debugging notes:**

- Unique by `environment_date`, `location_label`, and `source`.

- Location-aware design prevents double-counting glucose readings when multiple locations exist for the same date.

---

### `Exercise`

**Type:**
Class

**Location:**
`app/db/models.py`

**What it does:**
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

- `exercise_key` is the stable identifier used by workout imports.

- Exercise names are human-readable labels and should not be treated as the only durable identifier.

---

### `WorkoutRoutine`

**Type:**
Class

**Location:**
`app/db/models.py`

**What it does:**
Represents a reusable workout routine/template, such as Push, Pull, or Legs.

**Key fields:**

- `name`

- `notes`

**Relationships:**

- Has many `WorkoutRoutineExercise` records.

- Has many `WorkoutSession` records.

**Debugging notes:**

- Used to connect imported workout sessions to seeded routine templates.

---

### `WorkoutRoutineExercise`

**Type:**
Class

**Location:**
`app/db/models.py`

**What it does:**
Links one exercise to one workout routine.

**Key fields:**

- `routine_id`

- `exercise_id`

- `display_order`

**Debugging notes:**

- Preserves the order exercises should appear in each routine.

- Unique by `routine_id` and `exercise_id`.

---

### `WorkoutSession`

**Type:**
Class

**Location:**
`app/db/models.py`

**What it does:**
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

- This is session-level grain.

- It should not contain set-level fields such as weight, reps, or set number.

---

### `WorkoutSet`

**Type:**
Class

**Location:**
`app/db/models.py`

**What it does:**
Represents one performed set within a workout session.

**Key fields:**

- `session_id`

- `exercise_id`

- `set_number`

- `weight_kg`

- `reps`

- `notes`

**Relationships:**

- Belongs to `WorkoutSession`.

- Belongs to `Exercise`.

**Debugging notes:**

- This is set-level grain.

- Unique by `session_id`, `exercise_id`, and `set_number`.

---

## 🏋️ Workout Services

### `seed_workout_catalogue`

**Type:**
Function

**Location:**
`app/services/workouts/seed_data.py`

**What it does:**
Seeds the default workout exercise catalogue and Push / Pull / Legs routine mappings.

**Inputs:**

- `session`: optional SQLAlchemy session for test injection.

**Outputs:**

- Dictionary with created counts:

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

**Type:**
Function

**Location:**
`app/services/workouts/importer.py`

**What it does:**
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

**Inputs:**

- `file_path`: path to the workout CSV.

- `session`: optional SQLAlchemy session for test injection.

**Outputs:**

- Dictionary with import counts:

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

- If timing columns are present, the importer populates `WorkoutSession.started_at` and `WorkoutSession.ended_at`.

- If no start time is supplied, imported sessions default to `09:00` to preserve earlier importer behaviour.

- Session timing enables average duration metrics and workout calorie analysis.

---

### `clear_imported_workout_data`

**Type:**
Function

**Location:**
`app/services/workouts/maintenance.py`

**What it does:**
Deletes imported workout sessions and their associated sets for a given source.

**Inputs:**

- `source`: source value to clear. Defaults to `workout_csv`.

- `session`: optional SQLAlchemy session for test injection.

**Outputs:**

- Dictionary with deleted counts:

  - `sets`

  - `sessions`

**Writes to:**

- `workout_sets`

- `workout_sessions`

**Preserves:**

- `exercises`

- `workout_routines`

- `workout_routine_exercises`

**Debugging notes:**

- Used by the Workout tab clear-imported-data action.

- Designed to remove demo/imported workout logs without deleting the seeded exercise catalogue or routine templates.

---

### `get_workout_summary_metrics`

**Type:**
Function

**Location:**
`app/services/workouts/analysis.py`

**What it does:**
Returns top-level workout dashboard metrics.

**Inputs:**

- `session`: optional SQLAlchemy session for test injection.

- `reference_datetime`: optional anchor datetime for weekly calculations.

**Outputs:**

- `total_sessions`

- `weekly_sessions`

- `average_duration_minutes`

- `most_recent_workout`

- `total_sets`

- `total_volume_kg`

**Reads from:**

- `workout_sessions`

- `workout_sets`

- `workout_routines`

**Debugging notes:**

- Useful for future Workout summary cards.

- Duration is only calculated when both `started_at` and `ended_at` exist.

---

### `get_volume_by_exercise`

**Type:**
Function

**Location:**
`app/services/workouts/analysis.py`

**What it does:**
Aggregates total training volume by exercise.

**Volume formula:**

```text
weight_kg * reps
```

**Inputs:**

- `session`: optional SQLAlchemy session for test injection.

**Outputs per exercise:**

- `exercise_id`

- `exercise_name`

- `total_sets`

- `total_reps`

- `total_volume_kg`

**Reads from:**

- `workout_sets`

- `exercises`

**Debugging notes:**

- Results are sorted by `total_volume_kg` descending.

- Useful for future volume-by-exercise charts.

---

### `get_volume_by_workout_type`

**Type:**
Function

**Location:**
`app/services/workouts/analysis.py`

**What it does:**
Aggregates total training volume by workout type.

**Inputs:**

- `session`: optional SQLAlchemy session for test injection.

**Outputs per workout type:**

- `workout_type`

- `total_sessions`

- `total_sets`

- `total_reps`

- `total_volume_kg`

**Reads from:**

- `workout_sessions`

- `workout_sets`

**Debugging notes:**

- Uses `workout_type` as the grouping field.

- Falls back to `Uncategorised` where no workout type exists.

---

### `get_recent_workout_sessions`

**Type:**
Function

**Location:**
`app/services/workouts/analysis.py`

**What it does:**
Returns recent workout sessions for table display.

**Inputs:**

- `limit`: maximum number of sessions to return.

- `session`: optional SQLAlchemy session for test injection.

**Outputs per session:**

- `id`

- `started_at`

- `ended_at`

- `duration_minutes`

- `workout_type`

- `routine`

- `perceived_effort`

- `set_count`

- `total_volume_kg`

- `notes`

**Reads from:**

- `workout_sessions`

- `workout_sets`

- `workout_routines`

**Debugging notes:**

- Intended for the future read-only Workout tab.

- Returns newest sessions first.

---

### `get_exercises_with_workout_data`

**Type:**
Function

**Location:**
`app/services/workouts/analysis.py`

**What it does:**
Returns exercises that have at least one logged workout set.

**Inputs:**

- `session`: optional SQLAlchemy session for test injection.

**Outputs per exercise:**

- `exercise_id`

- `exercise_key`

- `exercise_name`

**Reads from:**

- `exercises`

- `workout_sets`

**Debugging notes:**

- Used to populate the Exercise Progression dropdown in the Workout tab.

- Excludes catalogue exercises that have not yet appeared in logged workout data.

---

### `get_exercise_progression`

**Type:**
Function

**Location:**
`app/services/workouts/analysis.py`

**What it does:**
Returns selected-exercise progression by workout date.

**Inputs:**

- `exercise_id`: database ID of the selected exercise.

- `session`: optional SQLAlchemy session for test injection.

**Outputs per date:**

- `date`

- `exercise_id`

- `exercise_name`

- `max_weight_kg`

- `reps_at_max_weight`

- `workout_type`

- `set_count`

- `total_reps`

- `total_volume_kg`

**Reads from:**

- `workout_sets`

- `workout_sessions`

- `exercises`

**Debugging notes:**

- Used by the Exercise Progression chart.

- Groups records by workout date.

- Tracks the heaviest set for the selected exercise on each date.

---

### `get_exercise_progression_summary`

**Type:**
Function

**Location:**
`app/services/workouts/analysis.py`

**What it does:**
Returns summary-card metrics for the selected exercise progression view.

**Inputs:**

- `exercise_id`: database ID of the selected exercise.

- `session`: optional SQLAlchemy session for test injection.

**Outputs:**

- `exercise_id`

- `exercise_name`

- `max_weight_kg`

- `reps_at_max_weight`

- `date_of_max_weight`

- `max_reps`

**Reads from:**

- `workout_sets`

- `workout_sessions`

- `exercises`

**Debugging notes:**

- Powers the Workout tab cards beneath the exercise dropdown.

- Returns empty/null-style values when no sets exist for the selected exercise.

---

### `get_workout_session_calorie_analysis`

**Type:**
Function

**Location:**
`app/services/workouts/analysis.py`

**What it does:**
Returns workout session calorie analysis by aligning workout session time windows with intraday activity calorie burn.

**Inputs:**

- `session`: optional SQLAlchemy session for test injection.

**Outputs per workout session:**

- `session_id`

- `workout_type`

- `started_at`

- `ended_at`

- `duration_minutes`

- `total_sets`

- `total_reps`

- `total_volume_kg`

- `average_load_per_rep`

- `max_weight_kg`

- `calories_burned`

- `calories_per_minute`

- `calories_per_kg_lifted`

**Reads from:**

- `workout_sessions`

- `workout_sets`

- `activity_intraday`

**Debugging notes:**

- Only sessions with both `started_at` and `ended_at` are included.

- Calories are derived from `IntradayActivity.calories_burned` between the workout start and end timestamps.

- The function does not persist calorie values; it returns derived insight data.

- Used by the Workout Calorie Analysis table.

---

## 🧪 Workout Tests

### `test_workout_models.py`

**Type:**
Test module

**Location:**
`tests/db/test_workout_models.py`

**What it does:**
Smoke-tests the workout database model relationships.

**Covers:**

- Routine creation.

- Exercise creation.

- Session creation.

- Set creation.

- Relationship traversal.

---

### `test_seed_data.py`

**Type:**
Test module

**Location:**
`tests/services/workouts/test_seed_data.py`

**What it does:**
Tests workout catalogue seeding.

**Covers:**

- Expected exercise, routine, and routine-exercise counts.

- Idempotency.

- Routine display order.

- Exercise key population.

---

### `test_analysis.py`

**Type:**
Test module

**Location:**
`tests/services/workouts/test_analysis.py`

**What it does:**
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

---

### `test_importer.py`

**Type:**
Test module

**Location:**
`tests/services/workouts/test_importer.py`

**What it does:**
Tests spreadsheet-style workout CSV import.

**Covers:**

- Session and set creation.

- Idempotency.

- Unknown exercise handling.

- Missing required column handling.

- Exercise resolution by stable exercise ID.

---

### `test_maintenance.py`

**Type:**
Test module

**Location:**
`tests/services/workouts/test_maintenance.py`

**What it does:**
Tests workout data maintenance utilities.

**Covers:**

- Clearing imported workout sessions.

- Clearing associated workout sets.

- Preserving exercises.

- Preserving workout routines.

- Preserving routine/exercise mappings.

- Returning zero counts when no matching source exists.

---

## 📝 Expansion Notes

This reference currently covers:

- Database models.

- Workout services.

- Workout maintenance utilities.

- Workout tests.

Future sections should add:

- Glucose services.

- Activity services.

- Environment services.

- Cross-module services.

- UI tab classes.

- Chart classes.

- Shared widgets.
